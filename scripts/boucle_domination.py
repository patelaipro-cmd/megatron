"""Exécute la boucle sur un instantané local de cotes ESPN, sans recherche web."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from megatron import boucle, data, externe, syndicate  # noqa: E402
from megatron.store import parse_dt  # noqa: E402


def resoudre_nom(nom, noms, division, audit):
    """Noms exacts ou correspondances de l'audit de résultats, jamais d'inclusion floue."""
    mapped = audit.get("noms", {}).get("espn:" + division, {}).get(nom)
    if mapped in noms:
        return mapped
    if nom in noms:
        return nom
    declared = [canonical for canonical, aliases in externe.charger_alias().items()
                if nom in aliases and canonical in noms]
    if len(declared) == 1:
        return declared[0]
    return None


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--instantane", type=Path, required=True)
    p.add_argument("--dossier-externe", type=Path)
    p.add_argument("--complement", type=Path, help="Résultats préalablement recoupés par verifier_resultats.py")
    p.add_argument("--audit-resultats", type=Path, help="Audit du même complément, pour les noms ESPN recoupés")
    p.add_argument("--horizon-heures", type=int, default=72)
    p.add_argument("--objectif", type=int, default=5)
    p.add_argument("--lot", type=int, default=10)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args(argv)
    if a.horizon_heures < 1:
        p.error("horizon positif requis")
    now = datetime.now(timezone.utc)
    paths = (data.CURRENT[:2] + (a.complement,)) if a.complement else data.CURRENT
    history = data.load(paths)
    audit = json.loads(a.audit_resultats.read_text()) if a.audit_resultats else {}
    rows = list(csv.DictReader(a.instantane.open(encoding="utf-8")))
    fixtures, excluded = {}, []
    for row in rows:
        if row.get("type_ligne") != "courante":
            continue
        ko, collected = parse_dt(row["coup_envoi"]), parse_dt(row["collecte_le"])
        if not now < ko <= now + timedelta(hours=a.horizon_heures) or collected > now or collected >= ko:
            continue
        ident = f"{row['division']}:{row['evenement_id']}"
        if now - collected > timedelta(hours=1):
            excluded.append({"id": ident, "raison": "INSTANTANE_PERIME_1H"})
            continue
        if "srl" in (row["domicile"] + row["exterieur"]).casefold():
            excluded.append({"id": ident, "raison": "MATCH_SIMULE"})
            continue
        fixtures[ident] = {"id": ident, "division": row["division"], "domicile": row["domicile"],
                          "exterieur": row["exterieur"], "coup_envoi": row["coup_envoi"],
                          "collecte_le": row["collecte_le"], "source": row["url"],
                          "cotes": [{"collecte_le": row["collecte_le"], "source": row["url"],
                                     "H": float(row["cote_H"]), "D": float(row["cote_D"]), "A": float(row["cote_A"])}]}

    def evaluer(f):
        hist = [m for m in history if m.division == f["division"] and m.day < parse_dt(f["coup_envoi"]).date()]
        names = {t for m in hist for t in (m.home, m.away)}
        mapped = [resoudre_nom(f[k], names, f["division"], audit) for k in ("domicile", "exterieur")]
        if any(name is None for name in mapped):
            raise ValueError("NOMS_NON_RESOLUS_SANS_AMBIGUITE : " + str(mapped))
        r = syndicate.evaluer(f["division"], mapped[0], mapped[1], f["coup_envoi"],
                             at=now, history=hist, dossier_externe=a.dossier_externe, cotes=f["cotes"])
        return {"analyse_le": r["analyse_le"], "noms_modele": mapped,
                "niveaux": r["niveaux"], "decision": r["decision"],
                "h2h_championnat": r["fiche"]["rubriques"]["confrontations"],
                "dernier_resultat_par_equipe": {team: (forme["matchs"][-1]["date"] if forme["matchs"] else None)
                    for team, forme in r["fiche"]["rubriques"]["forme"]["equipes"].items()},
                "ajustement_probabilites": r["ajustement_probabilites"]}

    result = boucle.boucler(sorted(fixtures.values(), key=lambda f: (f["coup_envoi"], f["id"])),
                            evaluer, objectif=a.objectif, lot=a.lot)
    result.update({"execute_le": now.isoformat(), "horizon_heures": a.horizon_heures,
                   "instantane": str(a.instantane), "sha256_instantane": hashlib.sha256(a.instantane.read_bytes()).hexdigest(),
                   "exclus": excluded, "audit_resultats": str(a.audit_resultats) if a.audit_resultats else None,
                   "historique": [{"fichier": str(f), "sha256": hashlib.sha256(Path(f).read_bytes()).hexdigest()} for f in paths]})
    a.sortie.parent.mkdir(parents=True, exist_ok=True)
    a.sortie.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("execute_le", "objectif", "confirmes", "manquants", "statut", "blocages_globaux", "passages")}, ensure_ascii=False))
    return 0 if result["statut"] == "OBJECTIF_ATTEINT" else 2


if __name__ == "__main__":
    sys.exit(main())
