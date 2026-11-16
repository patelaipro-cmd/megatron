"""Passerelle de preuves datées vers LIVE T+15 (sources déclarées, non authentifiées).

Le fichier d'observations est normalisé par une collecte séparée. Une mention
« officiel » dans un JSON n'est pas une preuve de publication officielle.
Cette passerelle vérifie domaines, horodatages, recoupements et XI, sans
fabriquer ni ajuster les intensités pré-match.
"""

from __future__ import annotations

import math
import unicodedata
from datetime import timedelta
from urllib.parse import urlsplit

from .store import parse_dt


DOMAINES = {
    "sportsmole": "sportsmole.co.uk",
    "sportsgambler": "sportsgambler.com",
    "pianetafanta": "pianetafanta.it",
    "180score": "180score.com",
    "xpertstats": "xpertstats.com",
    "sofascore": "sofascore.com",
    "officiel": None,
}
CHECKPOINTS = {"T-3h": -180, "T-60": -60, "T-30": -30, "T-5": -5, "T+15": 15}
FRAICHEUR_SCORE = timedelta(minutes=3)


def _date(value, champ):
    try:
        return parse_dt(value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"{champ} : date ISO avec fuseau obligatoire") from exc


def _source(preuve, at):
    if not isinstance(preuve, dict):
        raise ValueError("observation : objet requis")
    fournisseur = preuve.get("source")
    if fournisseur not in DOMAINES:
        raise ValueError(f"fournisseur inconnu : {fournisseur!r}")
    url = preuve.get("source_url")
    if not isinstance(url, str):
        raise ValueError("source_url HTTPS requis")
    u = urlsplit(url)
    if u.scheme != "https" or not u.hostname or u.username or u.password:
        raise ValueError("source_url HTTPS sans identifiants requis")
    domaine = DOMAINES[fournisseur]
    h = u.hostname.lower()
    if domaine is not None and h != domaine and not h.endswith("." + domaine):
        raise ValueError(f"URL non attribuable à {fournisseur}")
    if fournisseur == "officiel" and not preuve.get("organisme"):
        raise ValueError("identité de l'organisme officiel requise")
    collecte = _date(preuve.get("collecte_le"), "collecte_le")
    if collecte > at:
        raise ValueError("preuve postérieure à l'analyse : fuite temporelle")
    if preuve.get("publie_le") is not None and _date(preuve["publie_le"], "publie_le") > collecte:
        raise ValueError("publication postérieure au relevé")
    return fournisseur, url, collecte


def _xi(formation):
    if not isinstance(formation, dict) or set(formation) != {"H", "A"}:
        raise ValueError("XI H et A requis")
    result = {}
    for side in ("H", "A"):
        joueurs = formation[side]
        if not isinstance(joueurs, list) or len(joueurs) != 11:
            raise ValueError(f"XI {side} incomplet : 11 titulaires requis")
        normalises = []
        for nom in joueurs:
            if not isinstance(nom, str) or not nom.strip():
                raise ValueError("nom de titulaire vide")
            normalises.append("".join(c for c in unicodedata.normalize("NFKD", nom.casefold()) if not unicodedata.combining(c)).strip())
        if len(set(normalises)) != 11:
            raise ValueError(f"XI {side} avec doublons")
        result[side] = set(normalises)
    return result


def planifier(coup_envoi, *, au=None):
    """Cinq instants calculés, sans activer de tâche d'arrière-plan."""
    kickoff = _date(coup_envoi, "coup_envoi")
    now = _date(au, "au") if au is not None else None
    return [{"checkpoint": nom, "prevu_le": (kickoff + timedelta(minutes=delta)).isoformat(),
             "a_venir": now is None or now < kickoff + timedelta(minutes=delta)}
            for nom, delta in CHECKPOINTS.items()]


def assembler_t15(entree: dict) -> dict:
    """Convertit trois scores concordants + une preuve XI en snapshot LIVE T+15.

    Les observations sont livrées par un extracteur en amont (ou une personne) ;
    cette fonction ne visite pas les pages et ne certifie pas leur véracité.
    """
    if not isinstance(entree, dict):
        raise ValueError("dossier live : objet requis")
    match_id = entree.get("match_id")
    if not isinstance(match_id, str) or not match_id.strip():
        raise ValueError("match_id non vide requis")
    kickoff = _date(entree.get("kickoff"), "kickoff")
    au = _date(entree.get("au"), "au")
    if au < kickoff:
        raise ValueError("T+15 pas encore commencé")
    minute = entree.get("minute")
    if type(minute) not in (int, float) or not math.isfinite(minute) or not 12 <= minute <= 18:
        raise ValueError("minute T+15 attendue dans [12, 18]")
    observations = entree.get("scores", [])
    if not isinstance(observations, list):
        raise ValueError("scores : liste d'observations requise")
    valides = []
    for o in observations:
        fournisseur, url, collecte = _source(o, au)
        if fournisseur == "officiel":
            # Les sources officielles peuvent servir de preuve, mais on exige
            # encore trois fournisseurs réellement distincts dans cet essai.
            continue
        if o.get("match_id") != match_id:
            raise ValueError("source score attribuée à un autre match")
        if collecte < kickoff or au - collecte > FRAICHEUR_SCORE:
            continue  # preuves conservables mais trop anciennes pour T+15
        score = o.get("score")
        if (not isinstance(score, dict) or set(score) != {"H", "A"}
                or any(type(score[s]) is not int or score[s] < 0 for s in ("H", "A"))):
            raise ValueError("score H/A entier invalide")
        if o.get("cartons_rouges") != {"H": 0, "A": 0} or o.get("var_en_cours") is not False:
            raise ValueError("incident live non couvert : carton rouge ou VAR")
        m_observee = o.get("minute")
        if type(m_observee) not in (int, float) or not math.isfinite(m_observee) or abs(m_observee - minute) > 2:
            raise ValueError("minute observée incohérente")
        valides.append((fournisseur, url, collecte, score))
    providers = {v[0] for v in valides}
    if len(providers) < 3:
        raise ValueError("moins de trois fournisseurs de score récents distincts")
    scores = {tuple((v[3]["H"], v[3]["A"])) for v in valides}
    if len(scores) != 1:
        raise ValueError("conflit score entre fournisseurs : REFUS")
    sh, sa = next(iter(scores))

    xi_preuve = entree.get("xi_officiel")
    fournisseur, url_xi, au_xi = _source(xi_preuve, au)
    if fournisseur != "officiel" or xi_preuve.get("statut") != "confirmee_officielle":
        raise ValueError("XI non confirmé par une source présentée comme officielle")
    if au_xi >= kickoff:
        raise ValueError("compositions officielles relevées trop tard pour la comparaison pré-match")
    actuels = _xi(xi_preuve.get("titulaires"))
    base = entree.get("baseline")
    if not isinstance(base, dict):
        raise ValueError("baseline prématch requise")
    attendu = _xi(base.get("titulaires_attendus"))
    identique = all(actuels[s] == attendu[s] for s in ("H", "A"))
    return {
        "match_id": match_id,
        "kickoff": kickoff.isoformat(),
        "observed_at": au.isoformat(), "minute": minute,
        "score": {"H": sh, "A": sa},
        "baseline": {k: base[k] for k in ("lambda_H", "lambda_A", "modele", "calcule_le", "source") if k in base},
        "verification": {
            "score_sources": [v[1] for v in sorted(valides, key=lambda v: v[0])],
            "conflit_sources": False,
            "score_collecte_le": max(v[2] for v in valides).isoformat(),
            "xi_officiels": True, "xi_source": url_xi, "xi_collecte_le": au_xi.isoformat(),
            "xi_identiques_hypothese_base": identique,
            "var_en_cours": False, "cartons_rouges": {"H": 0, "A": 0},
        },
        "qualite_preuves": "DECLARATIVE_NON_AUDITEE : contrôler chaque source primaire avant WATCH réel",
    }
