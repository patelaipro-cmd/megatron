"""Registre prospectif : enregistre les évaluations SYNDICATE avant chaque match suivi, puis les résultats.

Lancé par le workflow `registre-prospectif` (GitHub Actions) sur la branche dédiée du même nom :
  python scripts/registre_prospectif.py --registre registre --externe donnees/externe \
      [--resultats-admis <csv>] [--maintenant <ISO>]

- Matchs suivis : calendrier ESPN des cinq championnats (jour UTC et lendemain), noms ramenés à
  ceux de data/ par la table reliée sur matchs communs (`docs/resultats-2026-27/audit.json`).
- Moment : `initial` entre 300 et 35 min avant le coup d'envoi (une fois), puis `T-30` et `T-5`
  dans leurs fenêtres (`controles.MOMENTS`) ; une fenêtre manquée est notée, jamais rattrapée.
- Enregistrés à l'initial : marges 2+ et 3+ du favori (`controles.enregistrer`) et 1X2
  `poisson-v5-cal`, avec l'heure d'enregistrement ; l'heure du commit GitHub en fait foi.
- Résultats : seulement ceux confirmés par deux familles (`--resultats-admis`, sortie de
  scripts/verifier_resultats.py), jamais un score à source unique.
- Jeton du registre : détenteur `claude` (décision de Luloki du 29/10/2026). Aucun GO déclenché.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from megatron import controles, data, jeton, syndicate  # noqa: E402
from megatron.data import Match  # noqa: E402
from megatron.ledger import DOMAIN, Ledger, pred_key  # noqa: E402
from megatron.store import MemoryStore, parse_dt  # noqa: E402

ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard?dates={jour}"
LIGUES = {"E0": "eng.1", "F1": "fra.1", "D1": "ger.1", "SP1": "esp.1", "I1": "ita.1"}
NOMS = ROOT / "docs" / "resultats-2026-27" / "audit.json"
SOURCE = "workflow registre-prospectif"
VERSION_1X2 = "poisson-v5-cal"


def lire_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "MEGATRON-registre/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def calendrier(maintenant: datetime, noms: dict, lire=lire_json) -> tuple[list[dict], list[str]]:
    """Matchs à venir (non commencés) des 5 ligues, aujourd'hui et demain (UTC), noms de data/."""
    out, notes = [], []
    for div, slug in LIGUES.items():
        for jour in (maintenant, maintenant + timedelta(days=1)):
            url = ESPN.format(slug=slug, jour=jour.strftime("%Y%m%d"))
            try:
                evs = lire(url).get("events") or []
            except Exception as exc:
                notes.append(f"{div} {jour:%Y-%m-%d} : calendrier indisponible ({type(exc).__name__})")
                continue
            for ev in evs:
                comp = (ev.get("competitions") or [{}])[0]
                etat = ((comp.get("status") or ev.get("status") or {}).get("type") or {}).get("state")
                cotes = {c.get("homeAway"): (c.get("team") or {}).get("displayName") for c in comp.get("competitors") or []}
                if etat != "pre" or set(cotes) != {"home", "away"}:
                    continue
                table = noms.get(f"espn:{div}", {})
                h, a = table.get(cotes["home"]), table.get(cotes["away"])
                if not (h and a):
                    notes.append(f"{div} : nom non relié {[n for n in cotes.values() if n not in table]}")
                    continue
                out.append({"division": div, "home": h, "away": a, "coup_envoi": parse_dt(ev.get("date") or comp.get("date")),
                            "espn_id": str(ev.get("id"))})
    vus = {}
    for m in out:
        vus.setdefault((m["division"], m["home"], m["away"], m["coup_envoi"]), m)
    return sorted(vus.values(), key=lambda m: m["coup_envoi"]), notes


def moment_du(store: MemoryStore, match_id: str, minutes: float) -> str | None:
    faits = {e.key.split(":")[-1] for e in controles.historique(store, match_id)}
    for moment, (lo, hi) in controles.MOMENTS.items():
        if lo <= minutes <= hi and moment not in faits and (moment == "initial" or "initial" in faits):
            return moment
    return None


def historique(resultats_admis: Path | None) -> list[Match]:
    chemins = list(data.CURRENT) + ([resultats_admis] if resultats_admis and resultats_admis.exists() else [])
    base = data.load(chemins[:len(data.CURRENT)])
    if len(chemins) == len(data.CURRENT):
        return base
    connus = {m.match_id for m in base}  # le complément du workflow peut recouvrir data/ : seuls les nouveaux comptent
    return sorted(base + [m for m in data.load(chemins[-1]) if m.match_id not in connus], key=lambda m: (m.kickoff, m.match_id))


def jeton_actif(store: MemoryStore) -> str:
    st = jeton.statut(store)
    if not st["initialise"]:
        return jeton.initialiser(store, "claude", source=f"{SOURCE} (décision de Luloki du 29/10/2026)").id
    if st["detenteur"] != "claude":
        raise jeton.JetonError(f"jeton détenu par {st['detenteur']} : aucune écriture")
    return st["id"]


def executer(registre: Path, externe: Path | None, maintenant: datetime, resultats_admis: Path | None = None,
             lire=lire_json, noms: dict | None = None) -> dict:
    noms = noms if noms is not None else json.loads(NOMS.read_text(encoding="utf-8"))["noms"]
    store = MemoryStore(registre)
    jid = jeton_actif(store)
    hist = historique(resultats_admis)
    matchs, notes = calendrier(maintenant, noms, lire)
    faits = []
    for m in matchs:
        minutes = (m["coup_envoi"] - maintenant) / timedelta(minutes=1)
        match_id = f"{m['division']}:{m['coup_envoi'].date().isoformat()}:{m['home']}-{m['away']}"
        moment = moment_du(store, match_id, minutes)
        if moment is None:
            continue
        try:
            ev = syndicate.evaluer(m["division"], m["home"], m["away"], m["coup_envoi"], at=maintenant,
                                   history=[x for x in hist if x.division == m["division"]],
                                   dossier_externe=externe, moment=moment)
            if moment == "initial" and not store.active(DOMAIN, pred_key(match_id, VERSION_1X2)):
                p = ev["reference_1x2_v5cal"]  # arrondi à 4 décimales : renormalisé pour sommer à 1
                Ledger(store, acces="claude", jeton_id=jid).predict(
                    match_id, m["coup_envoi"], {k: v / sum(p.values()) for k, v in p.items()}, model_version=VERSION_1X2,
                    source=SOURCE, recorded_at=maintenant, data_cutoff=ev["analyse_le"])
            r = controles.enregistrer(store, match_id, ev, moment, now=maintenant, source=SOURCE, acces="claude", jeton_id=jid)
            faits.append({"match_id": match_id, "moment": moment, "decision": r["decision"],
                          "minutes": round(minutes, 1), "changements": r["changements"]})
        except ValueError as exc:
            notes.append(f"{match_id} {moment} : {exc}")
    resultats = saisir_resultats(store, jid, resultats_admis, maintenant)
    return {"maintenant": maintenant.isoformat(), "jeton": jid, "matchs_a_venir": len(matchs), "enregistres": faits,
            "resultats_saisis": resultats, "notes": notes, "activation_automatique": syndicate.ACTIVATION_AUTOMATIQUE}


def saisir_resultats(store: MemoryStore, jid: str, resultats_admis: Path | None, maintenant: datetime) -> list[str]:
    if not (resultats_admis and resultats_admis.exists()):
        return []
    with resultats_admis.open(newline="", encoding="utf-8") as fh:
        scores = {f"{r['Division']}:{r['MatchDate']}:{r['HomeTeam']}-{r['AwayTeam']}": (int(r["FTHome"]), int(r["FTAway"]))
                  for r in csv.DictReader(fh)}
    predits = {e.value["match_id"] for e in store.active(DOMAIN) if e.key.startswith("pred:")}
    ledger, saisis = Ledger(store, acces="claude", jeton_id=jid), []
    for mid in sorted(predits):
        if mid in scores and not store.active(DOMAIN, f"result:{mid}"):
            h, a = scores[mid]
            ledger.result(mid, "H" if h > a else "A" if a > h else "D", goals=(h, a), observed_at=maintenant,
                          source=f"{SOURCE} : résultat confirmé par deux familles")
            saisis.append(mid)
    return saisis


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--registre", type=Path, required=True)
    p.add_argument("--externe", type=Path, default=None)
    p.add_argument("--resultats-admis", type=Path, default=None)
    p.add_argument("--maintenant", default=None)
    a = p.parse_args(argv)
    maintenant = parse_dt(a.maintenant) if a.maintenant else datetime.now(timezone.utc)
    out = executer(a.registre, a.externe if a.externe and a.externe.exists() else None, maintenant, a.resultats_admis)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
