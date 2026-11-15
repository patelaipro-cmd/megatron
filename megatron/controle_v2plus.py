"""Signaux descriptifs V+2, sans modifier les probabilités ni déclencher de pari.

Le classement et la forme inter-divisions/coupes ne figurent pas dans data.CURRENT.
Des constats manuels datés peuvent les documenter, mais restent déclaratifs.
"""

from __future__ import annotations

from datetime import date, datetime
from urllib.parse import urlparse

from .data import Match
from .store import parse_dt

CONTROLES = (
    "rotation_et_xi_habituel",
    "resistance_contre_division_superieure",
    "classements_avant_h2h",
    "motivation_et_enjeu_coupe",
    "forme_regionale_croisee",
)


def resume_victoires(history: list[Match], equipe: str, jour: date) -> dict:
    """Forme strictement antérieure au jour J ; rien du match évalué ni du même jour."""
    matchs = sorted((m for m in history if m.day < jour and equipe in (m.home, m.away)),
                    key=lambda m: (m.day, m.match_id))

    def convertir(m: Match) -> dict:
        dom = m.home == equipe
        buts = m.home_goals if dom else m.away_goals
        encaisses = m.away_goals if dom else m.home_goals
        return {"date": m.day.isoformat(), "adversaire": m.away if dom else m.home,
                "score": f"{buts}-{encaisses}", "marge": buts - encaisses}

    cinq_matchs = [convertir(m) for m in matchs[-5:]]
    cinq_victoires = [convertir(m) for m in matchs if
                     (m.home_goals > m.away_goals if m.home == equipe else m.away_goals > m.home_goals)][-5:]
    victoires_dans_5 = [m for m in cinq_matchs if m["marge"] > 0]
    courtes = sum(m["marge"] == 1 for m in victoires_dans_5)
    larges = sum(m["marge"] >= 2 for m in victoires_dans_5)
    alerte = (len(cinq_matchs) == 5 and len(victoires_dans_5) >= 3 and
              courtes >= 3 and courtes / len(victoires_dans_5) >= 0.75)
    return {"cinq_derniers_matchs": cinq_matchs, "cinq_dernieres_victoires": cinq_victoires,
            "victoires_sur_5_matchs": len(victoires_dans_5), "victoires_courtes_sur_5": courtes,
            "victoires_2plus_sur_5": larges, "signal_victoires_courtes": alerte,
            "couverture": "division seulement ; compétitions de coupe absentes",
            "statut": "MESURE_HISTORIQUE" if len(cinq_matchs) == 5 else "DONNEES_INSUFFISANTES"}


def verifier_signaux(signaux: list[dict] | None, at: datetime, ko: datetime) -> list[dict]:
    """Refuse toute observation tardive, non attribuable ou hors périmètre connu."""
    if signaux is None:
        return []
    if not isinstance(signaux, list):
        raise ValueError("signaux V+2 : une liste de constats est requise")
    vus = set()
    out = []
    for ligne in signaux:
        if not isinstance(ligne, dict) or ligne.get("controle") not in CONTROLES:
            raise ValueError("signal V+2 : controle inconnu")
        controle = ligne["controle"]
        if controle in vus:
            raise ValueError(f"signal V+2 en double : {controle}")
        vus.add(controle)
        if ligne.get("etat") not in ("alerte", "favorable", "incertain"):
            raise ValueError("signal V+2 : etat attendu alerte/favorable/incertain")
        if not isinstance(ligne.get("constat"), str) or not ligne["constat"].strip():
            raise ValueError("signal V+2 : constat manquant")
        url = ligne.get("source_url", "")
        if not isinstance(url, str) or urlparse(url).scheme not in ("https", "http") or not urlparse(url).netloc:
            raise ValueError("signal V+2 : source_url HTTP(S) requise")
        if not ligne.get("collecte_le") or not ligne.get("publie_le"):
            raise ValueError("signal V+2 : collecte_le et publie_le requis")
        collecte, publie = parse_dt(ligne["collecte_le"]), parse_dt(ligne["publie_le"])
        if collecte >= min(at, ko) or publie > collecte:
            raise ValueError("signal V+2 : source postérieure à l'analyse ou au coup d'envoi")
        out.append({"controle": controle, "etat": ligne["etat"], "constat": ligne["constat"].strip(),
                    "source_url": url, "publie_le": publie.isoformat(), "collecte_le": collecte.isoformat(),
                    "verification": "DECLARATIF_NON_VERIFIE"})
    return out


def evaluer(history: list[Match], favori: str, ko: datetime, at: datetime,
           signaux: list[dict] | None = None) -> dict:
    if at >= ko:
        raise ValueError("contrôle V+2 après coup d'envoi refusé")
    constats = verifier_signaux(signaux, at, ko)
    par_type = {c["controle"]: c for c in constats}
    retour = resume_victoires(history, favori, ko.date())
    return {"version": "controles-v2plus-v1", "favori": favori,
            "historique_victoires": retour,
            "points": [{"controle": k, **(par_type[k] if k in par_type else {"etat": "inconnu"})}
                       for k in CONTROLES],
            "alertes": (["victoires récentes majoritairement courtes (signal descriptif non calibré)"]
                         if retour["signal_victoires_courtes"] else []) +
                        [f"{c['controle']} : {c['constat']} (source déclarée, non vérifiée)"
                         for c in constats if c["etat"] == "alerte"],
            "ajustement_probabilites": False, "bloquant_automatique": False}
