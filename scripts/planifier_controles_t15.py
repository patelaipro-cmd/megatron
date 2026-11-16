"""Fabrique un plan de contrôles daté à partir d'une découverte ESPN réelle.

Ce plan n'est PAS un ordonnanceur. Il ne collecte pas de scores, n'émet aucune
probabilité et n'écrit pas dans le registre de prévisions MEGATRON.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.collecter_score_t15_espn import (
    BASE,
    COMPETITIONS_INTERNATIONALES,
    CONFIG,
    ROOT,
    instant,
    valider_fixtures,
)


KINS = ZoneInfo("Africa/Kinshasa")
ETAPES = (("T-3h", -180), ("T-90", -90), ("T-60", -60),
          ("T-30", -30), ("T-5", -5), ("T+15", 15))
TAILLE_LOT = 5


def planifier(document: dict, *, au: datetime) -> dict:
    """Refuse le rétrospectif et conserve la preuve de calendrier par fixture."""
    if au.tzinfo is None or au.utcoffset() is None:
        raise ValueError("instant de planification sans fuseau")
    if not isinstance(document, dict) or document.get("statut") != "LISTE_PROSPECTIVE_ESPN_NON_VALIDEE_MULTI_SOURCE":
        raise ValueError("document de découverte ESPN non reconnu")
    if document.get("erreurs") or document.get("tronques"):
        raise ValueError("découverte incomplète, en erreur ou tronquée")
    sources = document.get("sources_capturees")
    if not isinstance(sources, list) or not sources:
        raise ValueError("preuves brutes ESPN manquantes")
    decouverte = instant(document.get("decouverte_le"))
    if decouverte > au:
        raise ValueError("découverte datée dans le futur")
    ligues = json.loads(CONFIG.read_text(encoding="utf-8"))
    permis = {r["slug"] for r in ligues["espn"]} | COMPETITIONS_INTERNATIONALES
    fixtures = valider_fixtures(document, permis)
    if document.get("matchs_trouves") != len(fixtures):
        raise ValueError("dénombrement des fixtures contradictoire")

    sources_valides = {}
    for src in sources:
        if not isinstance(src, dict):
            raise ValueError("métadonnée de source invalide")
        url, sha = src.get("url"), src.get("sha256")
        if not isinstance(url, str) or not url.startswith(BASE + "/") or not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{64}", sha):
            raise ValueError("URL ou empreinte de source ESPN invalide")
        horaire = instant(src.get("collecte_le"))
        if horaire > au:
            raise ValueError("preuve de source datée dans le futur")
        sources_valides[url] = (horaire, sha)

    controles, absents = [], 0
    for f in fixtures:
        debut = f["coup_envoi"]
        jour = debut.astimezone(timezone.utc).strftime("%Y%m%d")
        url = f"{BASE}/{f['ligue']}/scoreboard?dates={jour}"
        if url not in sources_valides:
            raise ValueError(f"preuve de calendrier manquante : {f['event_id']}")
        releve, sha = sources_valides[url]
        if releve >= debut or decouverte >= debut:
            raise ValueError("la fixture n'était pas prospective à sa découverte")
        for nom, delta in ETAPES:
            cible = debut + timedelta(minutes=delta)
            expiration = cible + (timedelta(minutes=3) if nom == "T+15" else timedelta(0))
            manque = au > expiration
            if manque:
                absents += 1
            controles.append({
                "match_id": f"espn:{f['ligue']}:{f['event_id']}",
                "etape": nom,
                "heure_cible_utc": cible.astimezone(timezone.utc).isoformat(),
                "heure_cible_kinshasa": cible.astimezone(KINS).isoformat(),
                "fenetre_t15_debut_utc": (debut + timedelta(minutes=12)).astimezone(timezone.utc).isoformat() if nom == "T+15" else None,
                "fenetre_t15_fin_utc": (debut + timedelta(minutes=18)).astimezone(timezone.utc).isoformat() if nom == "T+15" else None,
                "statut": "ECHEANCE_PASSEE_SANS_CAPTURE" if manque else "A_CONTROLER_MANUELLEMENT",
                "preuve_calendrier": {"url": url, "sha256": sha, "collecte_le": releve.isoformat()},
            })
    groupes = defaultdict(list)
    for ligne in controles:
        if ligne["statut"] == "A_CONTROLER_MANUELLEMENT":
            groupes[(ligne["heure_cible_utc"], ligne["etape"])].append(ligne["match_id"])
    lots = []
    for (heure, etape), noms in sorted(groupes.items()):
        for i in range(0, len(noms), TAILLE_LOT):
            lots.append({"etape": etape, "heure_cible_utc": heure,
                         "heure_kinshasa": instant(heure).astimezone(KINS).isoformat(),
                         "match_ids": noms[i:i + TAILLE_LOT]})
    return {
        "planifie_le": au.isoformat(), "decouverte_le": decouverte.isoformat(),
        "fixtures": len(fixtures), "controles": len(controles),
        "echeances_passees_sans_capture": absents, "lots_max_5": lots,
        "details": controles, "statut": "PLAN_MANUEL_NON_ACTIVE",
        "v1_probability": None, "v2_probability": None, "watch": 0,
        "avertissement": "Aucun horaire du plan ne prouve une capture exécutée ; ne jamais reconstruire un instantané antérieur.",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--entree", required=True, type=Path)
    p.add_argument("--sortie", required=True, type=Path)
    a = p.parse_args(argv)
    dest = a.sortie.resolve()
    if not dest.parent.is_dir() or any(dest.is_relative_to((ROOT / part).resolve())
                                       for part in ("memoire", "data", "megatron")):
        raise ValueError("plan réservé à un dossier externe au registre et aux modèles")
    rapport = planifier(json.loads(a.entree.read_text(encoding="utf-8")), au=datetime.now(timezone.utc))
    with dest.open("x", encoding="utf-8") as sortie:
        sortie.write(json.dumps(rapport, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in rapport.items() if k not in ("details", "lots_max_5")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
