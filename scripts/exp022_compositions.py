"""EXP-022 : archive de XI prématch et contrôles de rotation, sans entraînement.

Captures éditoriales (SportsGambler/PianetaFanta) : fiche structurée de faits
effectivement lus, avec URL et heure de collecte réelles. Pas d'antidatage.
Les CSV Sofascore/Apify/ESPN/API-Football peuvent être convertis sans réseau,
mais les deux derniers nécessitent les champs domicile/exterieur vérifiés.

    python scripts/exp022_compositions.py ajouter --fiche /tmp/fiche.json --archive /tmp/xi.jsonl
    python scripts/exp022_compositions.py importer-externes --dossier /tmp/externe --archive /tmp/xi.jsonl
    python scripts/exp022_compositions.py analyser --archive /tmp/xi.jsonl --match-id 'sofa:123' --au '2026-11-14T13:00:00Z'
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from megatron import compositions_prematch as compos  # noqa: E402


def _instant(iso: str) -> datetime:
    return compos._instant(iso, "collecte_le")


def convertir_sofascore(lignes: list[dict], *, canal: str) -> dict | None:
    """Conversion stricte : 2 XI de 11, identité des équipes et KO cohérents."""
    if not lignes:
        return None
    dates, ids = {r.get("coup_envoi") for r in lignes}, {r.get("event_id") for r in lignes}
    collectes = {r.get("collecte_le") for r in lignes}
    if len(dates) != 1 or len(ids) != 1 or len(collectes) != 1:
        raise ValueError("instantané Sofascore à plusieurs identités")
    premiere = lignes[0]
    home, away = premiere.get("domicile"), premiere.get("exterieur")
    if not home or not away or any((r.get("domicile"), r.get("exterieur")) != (home, away) for r in lignes):
        raise ValueError("équipes contradictoires")
    if any(str(r.get("compo_confirmee")).lower() not in ("true", "1") for r in lignes):
        return None
    groupes = {}
    for cote, nom in (("H", home), ("A", away)):
        rows = [r for r in lignes if r.get("cote") == cote and r.get("equipe") == nom]
        if not rows:
            return None
        titulaires = [{"nom": r["joueur"], "id": r.get("joueur_id"), "poste": r.get("poste")}
                      for r in rows if r.get("statut") == "titulaire"]
        if len(titulaires) != 11:
            return None
        groupes[cote] = {"titulaires": titulaires,
                        "banc": [{"nom": r["joueur"], "id": r.get("joueur_id"), "poste": r.get("poste")}
                                 for r in rows if r.get("statut") == "remplacant"],
                        "absents": [{"nom": r["joueur"], "id": r.get("joueur_id"), "poste": r.get("poste")}
                                    for r in rows if r.get("statut") == "absent"]}
    event_id = premiere["event_id"]
    return {"match_id": f"sofa:{event_id}", "domicile": home, "exterieur": away,
            "competition": premiere.get("division") or "", "coup_envoi": premiere["coup_envoi"],
            "collecte_le": premiere["collecte_le"], "publie_le": None,
            "source": "sofascore", "source_url": f"https://api.sofascore.com/api/v1/event/{event_id}/lineups",
            "statut": "confirmee_fournisseur", "canal": canal, "equipes": groupes}


def convertir_compos(lignes: list[dict], *, canal: str) -> dict | None:
    """ESPN/API-Football : ne jamais inventer le côté H/A à partir de l'ordre des lignes."""
    if not lignes:
        return None
    ident = "event_id" if canal == "espn/compos" else "fixture_id"
    if len({(r.get(ident), r.get("coup_envoi"), r.get("collecte_le")) for r in lignes}) != 1:
        raise ValueError("captures de plusieurs événements")
    ligne = lignes[0]
    home, away = ligne.get("domicile"), ligne.get("exterieur")
    if not home or not away or any((r.get("domicile"), r.get("exterieur")) != (home, away) for r in lignes):
        return None  # anciens CSV sans domicile/exterieur : rejet, jamais supposition
    equipes = {}
    for cote, equipe in (("H", home), ("A", away)):
        rows = [r for r in lignes if r.get("equipe") == equipe]
        starters = [{"nom": r.get("joueur"), "id": r.get("joueur_id"), "poste": r.get("poste")}
                    for r in rows if r.get("statut") == "titulaire"]
        if len(starters) != 11:
            return None
        equipes[cote] = {"titulaires": starters, "banc": [
            {"nom": r.get("joueur"), "id": r.get("joueur_id"), "poste": r.get("poste")}
            for r in rows if r.get("statut") == "remplacant"],
            "formation": rows[0].get("formation") if rows else ""}
    id_match = ligne[ident]
    if canal == "espn/compos":
        source, prefix = "espn", "espn"
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{ligne['ligue']}/summary?event={id_match}"
    else:
        source, prefix = "api-football", "apifootball"
        url = f"https://v3.football.api-sports.io/fixtures/lineups?fixture={id_match}"
    return {"match_id": f"{prefix}:{id_match}", "domicile": home, "exterieur": away,
            "competition": ligne.get("division") or ligne.get("ligue") or "",
            "coup_envoi": ligne["coup_envoi"], "collecte_le": ligne["collecte_le"], "publie_le": None,
            "source": source, "source_url": url, "statut": "confirmee_fournisseur",
            "canal": canal, "equipes": equipes}


def importer_externes(dossier: Path, archive: Path, *, au: str,
                      sources=("sofascore", "sofascore_apify", "espn/compos", "apifootball/compos")) -> dict:
    """Importer exclusivement des XI complets datés strictement avant KO."""
    if not dossier.is_dir():
        raise ValueError("dossier externe absent")
    compte = {"fichiers": 0, "ajoutes": 0, "doublons": 0, "sans_orientation": 0,
              "incomplets": 0, "tardifs": 0, "erreurs": 0, "par_canal": {}}
    for canal in sources:
        compte["par_canal"][canal] = {"fichiers": 0, "groupes": 0, "importes": 0}
        for fichier in sorted((dossier / canal).glob("*/*.csv")):
            compte["fichiers"] += 1
            compte["par_canal"][canal]["fichiers"] += 1
            try:
                with fichier.open(encoding="utf-8", newline="") as h:
                    rows = list(csv.DictReader(h))
                groupes = defaultdict(list)
                for r in rows:
                    id_colonne = "fixture_id" if canal == "apifootball/compos" else "event_id"
                    groupes[(r.get(id_colonne), r.get("collecte_le"), r.get("ligue"))].append(r)
                for lignes in groupes.values():
                    compte["par_canal"][canal]["groupes"] += 1
                    if canal in ("espn/compos", "apifootball/compos") and not (lignes[0].get("domicile") and lignes[0].get("exterieur")):
                        compte["sans_orientation"] += 1
                        continue
                    obs = convertir_sofascore(lignes, canal=canal) if canal.startswith("sofascore") else convertir_compos(lignes, canal=canal)
                    if obs is None:
                        compte["incomplets"] += 1
                        continue
                    if _instant(obs["collecte_le"]) >= _instant(obs["coup_envoi"]) or _instant(obs["collecte_le"]) > _instant(au):
                        compte["tardifs"] += 1
                        continue
                    result = compos.ajouter(archive, obs, au=au)
                    compte["ajoutes" if result["statut"] == "ajoute" else "doublons"] += 1
                    if result["statut"] == "ajoute":
                        compte["par_canal"][canal]["importes"] += 1
            except (ValueError, KeyError, OSError, UnicodeError, csv.Error):
                compte["erreurs"] += 1  # un fichier invalide n'empêche pas les autres
    return {"experience": "EXP-022", "import": compte,
            "limites": "XI complets uniquement ; anciens CSV ESPN/API-Football sans identité H/A exclus ; aucun calcul probabiliste"}


def importer_sofascore(dossier: Path, archive: Path, *, au: str) -> dict:
    """Compatibilité avec le premier prototype EXP-022."""
    return importer_externes(dossier, archive, au=au, sources=("sofascore", "sofascore_apify"))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = p.add_subparsers(dest="commande", required=True)
    a = sp.add_parser("ajouter", help="ajouter une fiche observée sur un site (JSON)")
    a.add_argument("--fiche", type=Path, required=True)
    a.add_argument("--archive", type=Path, required=True)
    a.add_argument("--au", help="instant d'analyse ; défaut = maintenant en UTC")
    imp = sp.add_parser("importer-externes", help="convertir des CSV existants, sans accès réseau")
    imp.add_argument("--dossier", type=Path, required=True)
    imp.add_argument("--archive", type=Path, required=True)
    imp.add_argument("--au", help="date d'audit ; défaut = maintenant en UTC")
    an = sp.add_parser("analyser", help="comparer le XI au dernier historique confirmé")
    an.add_argument("--archive", type=Path, required=True)
    an.add_argument("--match-id", required=True)
    an.add_argument("--au", required=True)
    args = p.parse_args(argv)
    au = getattr(args, "au", None) or datetime.now(timezone.utc).isoformat()
    try:
        if args.commande == "ajouter":
            result = compos.ajouter(args.archive, json.loads(args.fiche.read_text(encoding="utf-8")), au=au)
        elif args.commande == "importer-externes":
            result = importer_externes(args.dossier, args.archive, au=au)
        else:
            result = compos.analyser(compos.charger(args.archive), args.match_id, au)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"EXP-022 : {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
