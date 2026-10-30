"""État de préparation des entraînements : ce qui est admissible, ce qui manque. N'entraîne rien.

Usage : python scripts/preparer_entrainement.py [--dossier-externe <externe/ de donnees-externes>]
        [--memoire memoire] [--au AAAA-MM-JJ] [--sortie docs/entrainement/etat.json]

Chaque candidat a des seuils fixés dans docs/entrainement/PREPARATION.md avant toute exécution.
Le script compte les données, compare aux seuils et rend ADMISSIBLE ou NON_ADMISSIBLE avec les
raisons. Il n'ajuste aucun paramètre, n'écrit ni dans data/ ni dans la mémoire.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from megatron import data  # noqa: E402
from megatron.externe import _lire, instantanes  # noqa: E402
from megatron.store import MemoryStore, parse_dt  # noqa: E402

SAISON = "2026/27"
SEUILS = {
    "fraicheur_jours": 10,             # dernier résultat confirmé au plus 10 jours avant la date d'audit
    "validation_2026_27_matchs": 1000,  # EXP-014 : matchs 2026/27 confirmés, jamais vus par les calibrations
    "validation_2026_27_ligues": 5,
    "absences_matchs": 1500,           # EXP-013 : matchs avec absents et compo collectés avant le coup d'envoi
    "absences_ligues": 3,
    "absences_mois": 4,
    "prospectif_predictions": 500,     # cohorte prospective : prévisions du registre avec résultat saisi
}


def couverture_data(au: date) -> dict:
    ms = [m for m in data.load(data.CURRENT) if m.day <= au]
    saison = [m for m in ms if data.season_of(m.day) == SAISON]
    dernier = max(m.day for m in ms)
    return {"matchs": len(ms), "dernier_resultat": dernier.isoformat(), "age_jours": (au - dernier).days,
            "saison_en_cours": {"matchs": len(saison), "par_ligue": dict(sorted(Counter(m.division for m in saison).items())),
                                "avec_cotes": sum(1 for m in saison if m.odds), "avec_tirs": sum(1 for m in saison if m.shots)}}


def couverture_externe(dossier: Path | None, avant: datetime) -> dict:
    if dossier is None or not Path(dossier).exists():
        return {"disponible": False}
    par_source, jours = {}, set()
    sans_identifiant = 0
    for source in ("apifootball/compos", "espn/compos"):  # comptés par source : les noms de ligue diffèrent
        matchs, ligues = set(), set()
        for snap in instantanes(dossier, source, avant):
            for l in snap:
                if l.get("coup_envoi") and parse_dt(l["collecte_le"]) < min(avant, parse_dt(l["coup_envoi"])):
                    identifiant = l.get("fixture_id") or l.get("event_id")
                    if not identifiant:
                        sans_identifiant += 1
                        continue
                    matchs.add(identifiant)
                    ligues.add(l.get("ligue"))
                    jours.add(l["coup_envoi"][:10])
        par_source[source] = {"matchs": len(matchs), "ligues": len(ligues - {None, ""})}
    blessures = sum(1 for f in (Path(dossier) / "apifootball" / "blessures").glob("*/*.csv")) if (Path(dossier) / "apifootball").exists() else 0
    lignes_compos = sum(len(_lire(f)) for s in ("apifootball/compos", "espn/compos") for f in (Path(dossier) / s).glob("*/*.csv"))
    return {"disponible": True, "instantanes_blessures": blessures, "lignes_compos": lignes_compos,
            "lignes_compos_sans_identifiant": sans_identifiant,
            "par_source": par_source, "matchs_compo_avant_coup_envoi": max(v["matchs"] for v in par_source.values()),
            "ligues": max(v["ligues"] for v in par_source.values()),
            "premier_jour": min(jours) if jours else None, "dernier_jour": max(jours) if jours else None}


def cohorte_prospective(memoire: Path) -> dict:
    store = MemoryStore(memoire)
    preds = [e for e in store.active("performances") if e.key.startswith("pred:")]
    resultats = {e.value["match_id"] for e in store.active("performances") if e.key.startswith("result:")}
    avec = {e.value["match_id"] for e in preds}
    return {"predictions": len(preds), "matchs_predits": len(avec),
            "matchs_avec_resultat": sum(1 for m in avec if m in resultats)}


def verdicts(d: dict, ext: dict, pro: dict) -> dict:
    out = {}
    raisons = []
    if d["age_jours"] > SEUILS["fraicheur_jours"]:
        raisons.append(f"dernier résultat il y a {d['age_jours']} j (> {SEUILS['fraicheur_jours']})")
    out["donnees_fraiches"] = raisons
    s = d["saison_en_cours"]
    raisons = []
    if s["matchs"] < SEUILS["validation_2026_27_matchs"]:
        raisons.append(f"{s['matchs']} matchs {SAISON} (< {SEUILS['validation_2026_27_matchs']})")
    if len(s["par_ligue"]) < SEUILS["validation_2026_27_ligues"]:
        raisons.append(f"{len(s['par_ligue'])} ligues (< {SEUILS['validation_2026_27_ligues']})")
    out["EXP-014_validation_calibrations_2026_27"] = raisons
    raisons = []
    if not ext.get("disponible"):
        raisons.append("collecte externe non fournie (--dossier-externe)")
    else:
        if ext["matchs_compo_avant_coup_envoi"] < SEUILS["absences_matchs"]:
            raisons.append(f"{ext['matchs_compo_avant_coup_envoi']} matchs avec compo collectée avant le coup d'envoi (< {SEUILS['absences_matchs']})")
        if ext["ligues"] < SEUILS["absences_ligues"]:
            raisons.append(f"{ext['ligues']} ligues (< {SEUILS['absences_ligues']})")
        if ext["premier_jour"]:
            mois = (date.fromisoformat(ext["dernier_jour"]) - date.fromisoformat(ext["premier_jour"])).days / 30.4
            if mois < SEUILS["absences_mois"]:
                raisons.append(f"{mois:.1f} mois de collecte (< {SEUILS['absences_mois']})")
    out["EXP-013_ponderation_absences"] = raisons
    raisons = []
    if pro["matchs_avec_resultat"] < SEUILS["prospectif_predictions"]:
        raisons.append(f"{pro['matchs_avec_resultat']} prévisions réelles avec résultat (< {SEUILS['prospectif_predictions']})")
    out["cohorte_prospective"] = raisons
    return {k: {"statut": "NON_ADMISSIBLE" if v else "ADMISSIBLE", "raisons": v} for k, v in out.items()}


def preparer(au: date, dossier_externe: Path | None, memoire: Path) -> dict:
    avant = datetime(au.year, au.month, au.day, 23, 59, tzinfo=timezone.utc)
    d, ext, pro = couverture_data(au), couverture_externe(dossier_externe, avant), cohorte_prospective(memoire)
    return {"au": au.isoformat(), "seuils": SEUILS, "donnees": d, "externe": ext, "prospectif": pro,
            "candidats": verdicts(d, ext, pro), "entrainement_lance": False}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dossier-externe", type=Path, default=None)
    p.add_argument("--memoire", type=Path, default=ROOT / "memoire")
    p.add_argument("--au", type=date.fromisoformat, default=datetime.now(timezone.utc).date())
    p.add_argument("--sortie", type=Path, default=None)
    a = p.parse_args(argv)
    etat = preparer(a.au, a.dossier_externe, a.memoire)
    texte = json.dumps(etat, indent=2, ensure_ascii=False) + "\n"
    if a.sortie:
        a.sortie.parent.mkdir(parents=True, exist_ok=True)
        a.sortie.write_text(texte, encoding="utf-8")
    print(texte, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
