"""Contexte qualitatif du favori : preuves déclarées, jamais de correction numérique.

Indicateurs mesurés sur l'historique (EXP-009) : ``megatron/angles_morts.py`` ; ce module-ci est la grille déclarative pré-match.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from .store import now_utc, parse_dt

VERSION = "angles-morts-favori-v1"
ANGLES = {
    "favori_surevalue": "Résultats flatteurs ou adversaires récents faibles",
    "adversaire_en_progression": "Coach, retours et performances adverses en évolution",
    "adaptation_h2h": "Corrections adverses depuis les anciennes confrontations",
    "style_genant": "Bloc bas, pressing, transitions ou duel aérien défavorables",
    "dependance_joueurs": "Joueur ou duo déterminant, disponibilité et remplaçant",
    "fragilite_defensive": "Espaces, lenteur, pertes et repli du favori",
    "rotation_fatigue": "Minutes, récupération, déplacements et prochain match",
    "enjeu_asymetrique": "Conséquences concrètes d'une victoire, d'un nul ou d'une défaite",
    "terrain_deplacement": "Rendement extérieur, terrain et conditions locales",
    "coups_pied_arretes": "Faiblesses et forces sur corners et coups francs",
    "construction_ecart": "Cartons larges liés à expulsion, penalty ou buts tardifs",
    "gestion_avantage": "Comportement après ouverture du score et égalisations",
    "informations_manquantes": "Compositions, absences ou changements peu documentés",
}
AXES_H2H = ("adaptation_adversaire", "construction_ecart", "dependance_joueurs", "contexte_match")
SCENARIOS = ("defaite", "nul", "victoire_courte")


def modele(match_id: str, home: str, away: str, favori: str, kickoff: str) -> dict:
    if favori not in ("H", "A") or not all(isinstance(x, str) and x.strip() for x in (match_id, home, away)) or home == away:
        raise ValueError("identifiant, deux équipes distinctes et favori H/A requis")
    parse_dt(kickoff)
    return {"version": VERSION, "match_id": match_id, "home": home, "away": away,
            "favori": favori, "kickoff": kickoff,
            "angles": [{"id": key, "etat": "inconnu", "constat": "", "mecanisme": "",
                        "effets": [], "sources": [], "categorie_preuve": "contexte",
                        "informations_manquantes": ["non renseigné"]} for key in ANGLES],
            "comparateur_h2h": {period: {"date": None, "score": None,
                                       "home": home if period == "actuel" else None,
                                       "away": away if period == "actuel" else None,
                                       "axes": dict.fromkeys(AXES_H2H, "")}
                                for period in ("ancien", "dernier", "actuel")},
            "scenarios": {key: {"hypothese": "", "angles": []} for key in SCENARIOS}}


def charger(path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f"contexte favori illisible : {exc}") from exc


def verifier(doc, *, at=None) -> dict:
    errors, missing, alerts = [], [], []
    reference = None
    def result(n=0):
        return {"version": VERSION, "date_reference": reference, "ok": not errors,
                "statut": "INVALIDE" if errors else "INCOMPLET" if missing else "DOCUMENTE_NON_VERIFIE",
                "angles_documentes": n, "angles_attendus": len(ANGLES), "erreurs": errors,
                "manquants": missing, "alertes": alerts, "ajustement_probabilites": False,
                "limite": "Sources déclarées, contenu et indépendance non vérifiés automatiquement ; aucun signal GO."}
    if not isinstance(doc, dict):
        errors.append("objet JSON attendu")
        return result()
    if doc.get("version") != VERSION:
        errors.append("version du contexte inconnue")
    if doc.get("favori") not in ("H", "A"):
        errors.append("favori H ou A requis")
    if not all(isinstance(doc.get(k), str) and doc[k].strip() for k in ("match_id", "home", "away")) or doc.get("home") == doc.get("away"):
        errors.append("identifiant et équipes distinctes requis")
    try:
        instant = parse_dt(at or now_utc())
        kickoff = parse_dt(doc["kickoff"])
        reference = instant.isoformat()
        if instant >= kickoff:
            errors.append("analyse non antérieure au coup d'envoi")
    except (KeyError, TypeError, ValueError, AttributeError):
        errors.append("dates avec fuseau requises")
        return result()
    angles = doc.get("angles")
    if not isinstance(angles, list) or any(not isinstance(a, dict) for a in angles):
        errors.append("liste d'angles structurés requise")
        return result()
    ids = [a.get("id") for a in angles]
    if len(ids) != len(ANGLES) or any(not isinstance(k, str) for k in ids) or set(k for k in ids if isinstance(k, str)) != set(ANGLES):
        errors.append("les 13 angles distincts sont requis, sans ajout ni doublon")
    documented = 0
    for a in angles:
        key = a.get("id")
        if not isinstance(key, str) or key not in ANGLES:
            continue
        state = a.get("etat")
        if state not in ("inconnu", "a_verifier", "documente"):
            errors.append(f"{key} : état inconnu")
        if state != "documente":
            missing.append(f"{key} : {state}")
        else:
            documented += 1
            for field in ("constat", "mecanisme"):
                if not isinstance(a.get(field), str) or not a[field].strip():
                    errors.append(f"{key} : {field} requis pour un angle documenté")
        effects = a.get("effets")
        if not isinstance(effects, list) or any(x not in SCENARIOS for x in effects):
            errors.append(f"{key} : effets attendus défaite/nul/victoire courte")
        gaps = a.get("informations_manquantes")
        if not isinstance(gaps, list) or any(not isinstance(x, str) for x in gaps):
            errors.append(f"{key} : informations manquantes attendues en liste")
        elif gaps:
            missing.append(f"{key} : " + "; ".join(gaps))
        sources = a.get("sources")
        if not isinstance(sources, list):
            errors.append(f"{key} : liste de sources requise")
            continue
        if state == "documente" and not sources:
            errors.append(f"{key} : source requise")
        families, hosts = set(), set()
        for source in sources:
            if not isinstance(source, dict):
                errors.append(f"{key} : source structurée requise")
                continue
            try:
                url = urlsplit(source.get("url", ""))
                family = source.get("famille", "")
                if url.scheme not in ("http", "https") or not url.hostname or not isinstance(family, str) or not family.strip():
                    raise ValueError()
                published = parse_dt(source["publie_le"])
                collected = parse_dt(source["collecte_le"])
                if published > collected or collected > instant or published >= kickoff:
                    raise ValueError()
                families.add(family.strip().casefold())
                hosts.add(url.hostname.casefold())
            except (ValueError, TypeError, KeyError, AttributeError):
                errors.append(f"{key} : URL, famille et dates pré-match cohérentes requises")
        if a.get("categorie_preuve") not in ("absences", "statistiques", "tactique", "contexte"):
            errors.append(f"{key} : catégorie de preuve inconnue")
        if a.get("categorie_preuve") == "absences" and (len(families) < 3 or len(hosts) < 3):
            missing.append(f"{key} : trois sites et familles de sources pour les absences requis")
    h2h = doc.get("comparateur_h2h")
    if not isinstance(h2h, dict):
        errors.append("comparateur H2H requis")
    else:
        dates = {}
        for period in ("ancien", "dernier", "actuel"):
            entry = h2h.get(period)
            if not isinstance(entry, dict) or not isinstance(entry.get("axes"), dict) or set(entry["axes"]) != set(AXES_H2H):
                errors.append(f"H2H {period} : quatre axes requis")
                continue
            for axis in AXES_H2H:
                if not isinstance(entry['axes'][axis], str) or not entry['axes'][axis].strip():
                    missing.append(f"H2H {period} : {axis}")
            if entry.get("home") is None or entry.get("away") is None:
                missing.append(f"H2H {period} : orientation domicile/extérieur inconnue")
            elif not isinstance(entry["home"], str) or not isinstance(entry["away"], str) or (entry["home"], entry["away"]) not in ((doc.get("home"), doc.get("away")), (doc.get("away"), doc.get("home"))):
                errors.append(f"H2H {period} : équipes différentes du match")
            if period == "actuel":
                if entry.get("score") is not None:
                    errors.append("aucun score final actuel ne doit servir à l'analyse pré-match")
                continue
            if entry.get("date") is None or entry.get("score") is None:
                missing.append(f"H2H {period} : date/score inconnus")
                continue
            try:
                day = date.fromisoformat(entry['date'])
                score = entry['score']
                if day >= instant.date() or not isinstance(score, list) or len(score) != 2 or any(type(g) is not int or g < 0 for g in score):
                    raise ValueError()
                dates[period] = day
            except (ValueError, TypeError):
                errors.append(f"H2H {period} : date passée et score entier requis")
        if len(dates) == 2 and dates['ancien'] >= dates['dernier']:
            errors.append("l'ancien H2H doit précéder le dernier")
    scenarios = doc.get('scenarios')
    if not isinstance(scenarios, dict) or set(scenarios) != set(SCENARIOS):
        errors.append("trois scénarios requis : défaite, nul, victoire courte")
    else:
        for key, scenario in scenarios.items():
            if not isinstance(scenario, dict) or not isinstance(scenario.get('angles'), list) or any(x not in ANGLES for x in scenario['angles'] if isinstance(x, str)) or any(not isinstance(x, str) for x in scenario['angles']):
                errors.append(f"scénario {key} : références d'angles invalides")
                continue
            if not isinstance(scenario.get('hypothese'), str) or not scenario['hypothese'].strip() or not scenario['angles']:
                missing.append(f"scénario {key} : hypothèse et mécanismes à renseigner")
    return result(documented)
