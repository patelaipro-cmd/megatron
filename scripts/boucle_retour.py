"""Boucle de retour : confronte les prévisions du registre d'une fenêtre aux vrais résultats.

Lecture seule (n'écrit jamais dans le registre) :
  python scripts/boucle_retour.py --registre memoire --admis <admis.csv> --du 2026-11-06 --au 2026-11-08 \
      [--provisoire <quarantaine.csv>] [--cotes <externe/cotes>] [--sortie docs/boucle/2026-11-06_08]

- Prévisions : celles du registre (`pred:` 1X2 de chaque version, marges du favori, décisions SYNDICATE
  initial / T-30 / T-5), enregistrées avant le coup d'envoi par le workflow registre-prospectif.
- Résultats officiels : `--admis` (sortie de scripts/verifier_resultats.py, deux familles d'accord).
  `--provisoire` (quarantaine du même script) ajoute les scores à SOURCE UNIQUE, marqués `provisoire` :
  jamais saisis dans le registre, chiffres indicatifs seulement.
- Bookmakers (marge retirée par normalisation) : `bookmaker-b365` = cotes Bet365 des résultats admis
  (football-data) ; `bookmaker-dk` = dernière capture DraftKings (ESPN, collecteur `cotes`) avant le coup
  d'envoi, noms ESPN reliés par docs/resultats-2026-27/audit.json. Aucune cote reconstituée.
- Leçons : constats chiffrés seulement. Aucun poids n'est modifié ici : un changement de modèle exige
  une expérience pré-enregistrée (EXP-014 : validation 2026/27 à >= 1000 matchs).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from megatron.ledger import DOMAIN, OUTCOMES, market_of, score  # noqa: E402
from megatron.store import MemoryStore  # noqa: E402

NOMS = ROOT / "docs" / "resultats-2026-27" / "audit.json"
ORDRE_MOMENTS = ("initial", "T-30", "T-5")
SEUIL_CONCLUSION = 300  # en dessous : constats descriptifs, aucune conclusion de modèle


def issue(h: int, a: int) -> str:
    return "H" if h > a else "A" if a > h else "D"


def lire_resultats(admis: Path | None, provisoire: Path | None) -> dict[tuple, dict]:
    """(division, domicile, extérieur) → score, date, statut et cotes Bet365 éventuelles."""
    out: dict[tuple, dict] = {}
    if provisoire and provisoire.exists():
        with provisoire.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                s = (r.get("score_espn") or "").split("-")
                if len(s) == 2 and all(x.strip().isdigit() for x in s):
                    out[(r["Division"], r["HomeTeam"], r["AwayTeam"])] = {
                        "score": (int(s[0]), int(s[1])), "date": r.get("date_espn"), "statut": "provisoire", "cotes": None}
    if admis and admis.exists():
        with admis.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                try:
                    cotes = normaliser({k: float(r[c]) for k, c in (("H", "OddHome"), ("D", "OddDraw"), ("A", "OddAway"))})
                except (KeyError, ValueError):
                    cotes = None
                out[(r["Division"], r["HomeTeam"], r["AwayTeam"])] = {
                    "score": (int(r["FTHome"]), int(r["FTAway"])), "date": r["MatchDate"], "statut": "officiel", "cotes": cotes}
    return out


def normaliser(cotes: dict[str, float]) -> dict[str, float] | None:
    if not all(v > 1 for v in cotes.values()):
        return None
    inv = {k: 1 / v for k, v in cotes.items()}
    return {k: v / sum(inv.values()) for k, v in inv.items()}


def lire_cotes_dk(dossier: Path | None, du: date, au: date, noms: dict) -> dict[tuple, dict]:
    """(division, domicile, extérieur) → probabilités de la dernière ligne DraftKings capturée avant le coup d'envoi."""
    out: dict[tuple, tuple] = {}
    if not (dossier and (dossier / "espn").exists()):
        return {}
    for f in sorted((dossier / "espn").glob("*/*.csv")):
        with f.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("marche", "1X2") != "1X2" or r.get("type_ligne") != "courante":
                    continue
                ko = datetime.fromisoformat(r["coup_envoi"])
                if not (du <= ko.date() <= au) or datetime.fromisoformat(r["collecte_le"]) >= ko:
                    continue
                table = noms.get(f"espn:{r['division']}", {})
                h, a = table.get(r["domicile"]), table.get(r["exterieur"])
                if not (h and a):
                    continue
                try:
                    p = normaliser({k: float(r[f"cote_{k}"]) for k in OUTCOMES})
                except ValueError:
                    continue
                cle = (r["division"], h, a)
                if p and (cle not in out or r["collecte_le"] > out[cle][0]):
                    out[cle] = (r["collecte_le"], p)
    return {k: v[1] for k, v in out.items()}


def decouper(match_id: str) -> tuple[str, str, str, str]:
    div, jour, equipes = match_id.split(":", 2)
    if equipes.count("-") != 1:
        raise ValueError(f"équipes ambiguës : {equipes!r}")  # aucun nom de data/ à tiret à ce jour
    home, away = equipes.split("-")
    return div, jour, home, away


def cohorte(store: MemoryStore, du: date, au: date) -> dict[str, dict]:
    """match_id → prévisions 1X2 par version, marges, décisions SYNDICATE par moment."""
    out: dict[str, dict] = {}

    def fiche(mid: str) -> dict | None:
        div, jour, home, away = decouper(mid)
        if not (du <= date.fromisoformat(jour) <= au):
            return None
        return out.setdefault(mid, {"division": div, "jour": jour, "home": home, "away": away,
                                    "x12": {}, "marges": {}, "syndicate": {}})

    for e in store.active(DOMAIN):
        if not e.key.startswith("pred:"):
            continue
        f = fiche(e.value["match_id"])
        if f is None:
            continue
        m = market_of(e.value)
        if m == "1X2":
            f["x12"][e.value["model_version"]] = e.value["probs"]
        elif "MARGE" in m:
            f["marges"][m] = e.value["probs"]["oui"]
    for e in store.active("football"):
        if not e.key.startswith("syndicate:"):
            continue
        f = fiche(e.value["match_id"])
        if f is not None:
            f["syndicate"][e.value["moment"]] = e.value["resume"]
    return out


def bilan(fiches: dict[str, dict], resultats: dict[tuple, dict], cotes_dk: dict[tuple, dict] | None = None) -> dict:
    lignes, absents = [], []
    for mid, f in sorted(fiches.items()):
        r = resultats.get((f["division"], f["home"], f["away"]))
        if r is None:
            absents.append(mid)
            continue
        h, a = r["score"]
        y = issue(h, a)
        dernier = next((f["syndicate"][m] for m in reversed(ORDRE_MOMENTS) if m in f["syndicate"]), None)
        lignes.append({"match_id": mid, "score": f"{h}-{a}", "issue": y, "statut": r["statut"], "x12": f["x12"],
                       "bookmakers": {k: v for k, v in (("bookmaker-b365", r["cotes"]),
                                      ("bookmaker-dk", (cotes_dk or {}).get((f["division"], f["home"], f["away"])))) if v}, "marges": f["marges"],
                       "syndicate_initial": (f["syndicate"].get("initial") or {}).get("decision"),
                       "syndicate_final": dernier and dernier.get("decision"),
                       "favori": dernier and (dernier.get("niveaux") or {}).get("favori"),
                       "p_favori": dernier and ((dernier.get("niveaux") or {}).get("probabilites") or {}).get("victoire_simple"),
                       "p_favori_2plus": dernier and ((dernier.get("niveaux") or {}).get("probabilites") or {}).get("victoire_par_2_ou_plus"),
                       "marge": h - a})
    versions = sorted({v for ln in lignes for v in ln["x12"]})
    modeles = {}
    livres = sorted({b for ln in lignes for b in ln["bookmakers"]})
    proba = lambda ln, v: ln["bookmakers"].get(v) if v.startswith("bookmaker") else ln["x12"].get(v)  # noqa: E731
    for v in versions + livres:
        paires = [(proba(ln, v), ln["issue"]) for ln in lignes]
        paires = [(p, y) for p, y in paires if p]
        s = score(paires)
        if paires:
            s["reussite_choix"] = round(sum(max(p, key=p.get) == y for p, y in paires) / len(paires), 4)
            s["p_nul_moyenne"] = round(sum(p["D"] for p, _ in paires) / len(paires), 4)
            s["frequence_nul"] = round(sum(y == "D" for _, y in paires) / len(paires), 4)
        modeles[v] = s
    comparaison = {}
    for livre in livres:
        communs = [ln for ln in lignes if livre in ln["bookmakers"] and all(v in ln["x12"] for v in versions)]
        if communs:
            comparaison[livre] = {"n": len(communs), "log_loss": {
                v: score([(proba(ln, v), ln["issue"]) for ln in communs])["log_loss"] for v in versions + [livre]}}
    syn = {}
    for cle in ("syndicate_initial", "syndicate_final"):
        par = {}
        for ln in lignes:
            d = ln[cle]
            if not d or not ln["favori"]:
                continue
            g = par.setdefault(d, {"n": 0, "favori_gagne": 0, "favori_par_2": 0, "p_favori_moyenne": 0.0, "p_2plus_moyenne": 0.0})
            signe = 1 if ln["favori"] == "H" else -1
            g["n"] += 1
            g["favori_gagne"] += ln["issue"] == ln["favori"]
            g["favori_par_2"] += signe * ln["marge"] >= 2
            g["p_favori_moyenne"] += ln["p_favori"] or 0
            g["p_2plus_moyenne"] += ln["p_favori_2plus"] or 0
        for g in par.values():
            g["p_favori_moyenne"] = round(g["p_favori_moyenne"] / g["n"], 4)
            g["p_2plus_moyenne"] = round(g["p_2plus_moyenne"] / g["n"], 4)
        syn[cle] = par
    ref = "poisson-v5-cal"
    erreurs = sorted((ln for ln in lignes if ref in ln["x12"]), key=lambda ln: ln["x12"][ref][ln["issue"]])[:8]
    return {
        "n_predits": len(fiches), "n_resolus": len(lignes),
        "n_officiels": sum(ln["statut"] == "officiel" for ln in lignes),
        "n_provisoires": sum(ln["statut"] == "provisoire" for ln in lignes),
        "sans_resultat": absents, "modeles": modeles, "communs_avec_bookmakers": comparaison, "syndicate": syn,
        "plus_grosses_surprises": [{"match_id": ln["match_id"], "score": ln["score"], "statut": ln["statut"],
                                    f"p_{ref}_issue": round(ln["x12"][ref][ln["issue"]], 3),
                                    "syndicate_final": ln["syndicate_final"]} for ln in erreurs],
        "lecons": lecons(modeles, comparaison, syn, len(lignes)),
        "lignes": lignes,
    }


def lecons(modeles: dict, comparaison: dict, syn: dict, n: int) -> list[str]:
    out = []
    if n < SEUIL_CONCLUSION:
        out.append(f"n={n} < {SEUIL_CONCLUSION} : constats descriptifs, aucun poids modifié (EXP-014 à >= 1000).")
    for livre, c in comparaison.items():
        for v, x in c["log_loss"].items():
            if v != livre:
                out.append(f"{v} vs {livre} (matchs communs n={c['n']}) : {x - c['log_loss'][livre]:+.4f} log-loss.")
    for v, s in modeles.items():
        if s.get("n") and s["n"] >= 20 and abs(s["p_nul_moyenne"] - s["frequence_nul"]) >= 0.08:
            sens = "sous-estimés" if s["frequence_nul"] > s["p_nul_moyenne"] else "surestimés"
            out.append(f"{v} : nuls {sens} ({s['p_nul_moyenne']:.0%} prévu, {s['frequence_nul']:.0%} observé, n={s['n']}).")
    for d, g in (syn.get("syndicate_final") or {}).items():
        taux = g["favori_gagne"] / g["n"]
        out.append(f"SYNDICATE {d} (final) : favori gagne {g['favori_gagne']}/{g['n']} ({taux:.0%}, prévu {g['p_favori_moyenne']:.0%}),"
                   f" par 2+ {g['favori_par_2']}/{g['n']} (prévu {g['p_2plus_moyenne']:.0%}).")
    return out


def markdown(b: dict, titre: str) -> str:
    t = [f"# {titre}", "", f"Prédits {b['n_predits']} · résolus {b['n_resolus']} (officiels {b['n_officiels']},"
         f" provisoires {b['n_provisoires']}) · sans résultat {len(b['sans_resultat'])}", "",
         "| modèle | n | log-loss | RPS | réussite choix | nul prévu / observé |", "|---|---|---|---|---|---|"]
    for v, s in b["modeles"].items():
        if s.get("n"):
            t.append(f"| {v} | {s['n']} | {s['log_loss']:.4f} | {s['rps']:.4f} | {s['reussite_choix']:.0%} |"
                     f" {s['p_nul_moyenne']:.0%} / {s['frequence_nul']:.0%} |")
    t += ["", "## Leçons", ""] + [f"- {x}" for x in b["lecons"]]
    t += ["", "## Plus grosses surprises (poisson-v5-cal)", ""]
    t += [f"- {e['match_id']} {e['score']} : p={e['p_poisson-v5-cal_issue']} ({e['statut']}, SYNDICATE {e['syndicate_final']})"
          for e in b["plus_grosses_surprises"]]
    return "\n".join(t) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--registre", type=Path, required=True)
    p.add_argument("--admis", type=Path, default=None)
    p.add_argument("--provisoire", type=Path, default=None)
    p.add_argument("--du", required=True)
    p.add_argument("--au", required=True)
    p.add_argument("--cotes", type=Path, default=None, help="dossier externe/cotes (DraftKings via ESPN)")
    p.add_argument("--sortie", type=Path, default=None)
    a = p.parse_args(argv)
    du, au = date.fromisoformat(a.du), date.fromisoformat(a.au)
    noms = json.loads(NOMS.read_text(encoding="utf-8"))["noms"]
    b = bilan(cohorte(MemoryStore(a.registre), du, au), lire_resultats(a.admis, a.provisoire),
              lire_cotes_dk(a.cotes, du, au, noms))
    if a.sortie:
        a.sortie.mkdir(parents=True, exist_ok=True)
        (a.sortie / "bilan.json").write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
        (a.sortie / "bilan.md").write_text(markdown(b, f"Boucle de retour {a.du} → {a.au}"), encoding="utf-8")
    print(json.dumps({k: v for k, v in b.items() if k != "lignes"}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
