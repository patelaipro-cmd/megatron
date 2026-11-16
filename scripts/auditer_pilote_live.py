"""Audit en lecture seule de la couverture XI pour un pilote LIVE T+15.

Ne transforme jamais des archives de compositions en prévisions prospectives :
la disponibilité d'un XI ESPN ne prouve ni une source officielle primaire,
ni un score T+15, ni une baseline V1/V2 calibrée au direct.

Exemples :
    python scripts/auditer_pilote_live.py --git-ref FETCH_HEAD
    python scripts/auditer_pilote_live.py --dossier-externe ../megatron-externe/externe
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


# La collecte ESPN a changé de schéma en novembre 2026 : les anciens CSV
# n'avaient ni les colonnes domicile/exterieur, ni parfois « source ».
# Leurs deux XI sont auditables mais l'orientation H/A ne peut être inférée.
CHAMPS_ESPN = {"event_id", "ligue", "coup_envoi", "collecte_le", "equipe",
               "joueur", "joueur_id", "statut"}


def instant(texte: str) -> datetime:
    if not isinstance(texte, str) or not texte:
        raise ValueError("horodatage absent")
    try:
        result = datetime.fromisoformat(texte.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("horodatage ISO invalide") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("horodatage sans fuseau")
    return result


def charger_git(ref: str) -> tuple[list[tuple[str, bytes]], dict]:
    """Lit les blobs d'une branche externe par Git, sans checkout ni écriture."""
    noms = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ref, "--", "externe/espn/compos"],
        check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    fichiers = [(nom, subprocess.run(["git", "show", f"{ref}:{nom}"],
                                       check=True, capture_output=True).stdout)
                for nom in noms if nom.endswith(".csv")]
    manifeste = subprocess.run(
        ["git", "show", f"{ref}:externe/manifeste.json"],
        check=True, capture_output=True,
    ).stdout
    return fichiers, json.loads(manifeste)


def charger_dossier(dossier: Path) -> tuple[list[tuple[str, bytes]], dict]:
    if not dossier.is_dir():
        raise ValueError("dossier externe introuvable")
    fichiers = [(str(f.relative_to(dossier)), f.read_bytes())
                for f in sorted((dossier / "espn" / "compos").rglob("*.csv"))]
    return fichiers, json.loads((dossier / "manifeste.json").read_text(encoding="utf-8"))


def auditer(fichiers: list[tuple[str, bytes]], manifeste: dict, *, au: str,
            cible: int = 50) -> dict:
    """Compte uniquement les XI observés complets et datés, jamais des WATCH.

    Les fichiers peuvent contenir plusieurs rencontres. Un même match présent
    dans plusieurs captures n'est compté qu'une fois, sur sa dernière capture
    valide strictement antérieure au coup d'envoi et à l'audit.
    """
    if type(cible) is not int or cible <= 0:
        raise ValueError("cible positive requise")
    audit_le = instant(au)
    snapshots = defaultdict(list)
    refus = Counter()
    for chemin, contenu in fichiers:
        try:
            reader = csv.DictReader(io.StringIO(contenu.decode("utf-8-sig")))
            if not CHAMPS_ESPN.issubset(set(reader.fieldnames or [])):
                raise ValueError("colonnes ESPN manquantes")
            lignes = list(reader)
            if not lignes:
                raise ValueError("CSV vide")
            for ligne in lignes:
                if not ligne["event_id"] or not ligne["collecte_le"]:
                    raise ValueError("identifiant ou date manquante")
                snapshots[(chemin, ligne["event_id"], ligne["collecte_le"])].append(ligne)
        except (UnicodeError, csv.Error, ValueError) as exc:
            refus[f"CSV incorrect : {exc}"] += 1

    valides = {}
    captures_valides = 0
    for (_, evenement, capture), lignes in snapshots.items():
        try:
            collectee, ko = instant(capture), instant(lignes[0]["coup_envoi"])
            if collectee >= ko:
                raise ValueError("XI collecté après le coup d'envoi")
            if collectee > audit_le:
                raise ValueError("XI futur au moment de l'audit")
            m = lignes[0]
            for ligne in lignes:
                if any(ligne[k] != m[k] for k in
                       ("event_id", "ligue", "coup_envoi", "domicile", "exterieur", "source")
                       if k in m):
                    raise ValueError("identité du match incohérente")
                if "source" in m and ligne["source"] != "espn":
                    raise ValueError("source ESPN incohérente")
            noms_equipes = {r["equipe"] for r in lignes}
            if not m["ligue"] or len(noms_equipes) != 2 or not all(noms_equipes):
                raise ValueError("rencontre non identifiable")
            oriente = "domicile" in m and "exterieur" in m
            if oriente:
                equipes = (m["domicile"], m["exterieur"])
                if set(equipes) != noms_equipes:
                    raise ValueError("domicile/exterieur incohérents avec les XI")
            else:
                equipes = tuple(sorted(noms_equipes))
            compositions = {}
            for equipe in equipes:
                titulaires = [r for r in lignes if r["equipe"] == equipe and r["statut"] == "titulaire"]
                if len(titulaires) != 11:
                    raise ValueError("XI incomplet")
                identifiants = [(r["joueur_id"].strip() or r["joueur"].casefold().strip())
                                for r in titulaires]
                if not all(r["joueur"].strip() for r in titulaires) or len(set(identifiants)) != 11:
                    raise ValueError("XI doublonné ou sans nom")
                compositions[equipe] = True
            if any(r["equipe"] not in compositions for r in lignes):
                raise ValueError("équipe supplémentaire inattendue")
            cle = (m["ligue"], evenement)
            courant = {"id": f"espn:{m['ligue']}:{evenement}", "match": " – ".join(equipes),
                       "coup_envoi": ko.isoformat(), "xi_collecte_le": collectee.isoformat(),
                       "statut_xi": "FOURNISSEUR_ESPN_NON_PRIMAIRE",
                       "orientation_HA_verifiee": oriente,
                       "source_colonne_csv": "source" in m}
            precedent = valides.get(cle)
            if precedent and precedent["coup_envoi"] != courant["coup_envoi"]:
                raise ValueError("identifiant réutilisé pour deux matchs")
            if precedent and precedent["orientation_HA_verifiee"] and oriente and precedent["match"] != courant["match"]:
                raise ValueError("équipes incompatibles pour un même match")
            if precedent is None or (oriente, collectee) > (precedent["orientation_HA_verifiee"], instant(precedent["xi_collecte_le"])):
                valides[cle] = courant
            captures_valides += 1
        except ValueError as exc:
            refus[str(exc)] += 1

    matches = sorted(valides.values(), key=lambda m: (m["coup_envoi"], m["id"]))
    passés = [m for m in matches if instant(m["coup_envoi"]) <= audit_le]
    futurs = [m for m in matches if instant(m["coup_envoi"]) > audit_le and m["orientation_HA_verifiee"]]
    sources = manifeste.get("sources") or {}
    etats = {s: (v.get("statut") if isinstance(v, dict) else "inconnu")
             for s, v in sources.items()}
    return {
        "version": "AUDIT_PILOTE_LIVE_50_V1", "au": audit_le.isoformat(),
        "cible_prospective": cible, "manifeste_execution_le": manifeste.get("execution_le"),
        "statuts_collecte": etats, "fichiers_espn_lus": len(fichiers),
        "captures_xi_valides": captures_valides,
        "matchs_xi_historiques_uniques": len(passés),
        "matchs_xi_historiques_orientes": sum(m["orientation_HA_verifiee"] for m in passés),
        "matchs_xi_futurs_uniques": len(futurs),
        "matchs_reellement_prets_t15": 0, "watch_live": 0,
        "progression_pilote": f"0/{cible}", "decision": "REFUS",
        "raison": "Aucun flux de scores T+15 authentifié multi-source, aucun XI de source primaire vérifié, aucune baseline live calibrée dans ces archives ESPN",
        "anomalies_captures": dict(sorted(refus.items())),
        "exemples_historiques": passés[-5:],
        "candidats_xi_futurs": futurs[:cible],
        "note": "Couverture rétrospective seulement : aucune prévision antidatée ni modification des poids ou de memoire/.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    origine = parser.add_mutually_exclusive_group(required=True)
    origine.add_argument("--git-ref", help="Référence Git donnees-externes, lue sans checkout")
    origine.add_argument("--dossier-externe", type=Path, help="Dossier externe/ déjà collecté")
    parser.add_argument("--au", help="Instant d'audit ISO horodaté (UTC par défaut)")
    parser.add_argument("--cible", type=int, default=50)
    args = parser.parse_args(argv)
    fichiers, manifeste = (charger_git(args.git_ref) if args.git_ref else charger_dossier(args.dossier_externe))
    maintenant = args.au or datetime.now(timezone.utc).isoformat()
    resultat = auditer(fichiers, manifeste, au=maintenant, cible=args.cible)
    if args.git_ref:
        resultat["revision_externe"] = subprocess.run(
            ["git", "rev-parse", "--verify", f"{args.git_ref}^{{commit}}"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    print(json.dumps(resultat, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
