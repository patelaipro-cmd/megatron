"""EXP-022 : observations de XI datées et rotations descriptives, hors probabilités.

Un instantané est une observation réellement capturée, pas une reconstruction de
ce que le fournisseur aurait publié auparavant. Les données éditoriales restent
des prévisions même si elles détaillent onze joueurs. Aucune écriture au registre.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from .store import parse_dt

SOURCES = {
    "sportsgambler": "sportsgambler.com",
    "pianetafanta": "pianetafanta.it",
    "sofascore": "sofascore.com",
    "espn": "espn.com",
    "api-football": "api-sports.io",
    "officiel": None,  # identité de l'organisme officiel à vérifier séparément
}
STATUTS = {"probable", "confirmee_fournisseur", "confirmee_officielle"}


def _instant(value: str, champ: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{champ} : date ISO avec fuseau requise")
    try:
        dt = parse_dt(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{champ} : date ISO avec fuseau requise") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{champ} : fuseau requis")
    return dt


def _texte(value, champ: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{champ} : texte non vide requis")
    return value.strip()


def _joueurs(value, champ: str) -> list[dict]:
    if not isinstance(value, list) or len(value) > 30:
        raise ValueError(f"{champ} : liste de 0 à 30 joueurs requise")
    result, ids = [], set()
    for p in value:
        if isinstance(p, str):
            p = {"nom": p}
        if not isinstance(p, dict):
            raise ValueError(f"{champ} : joueur invalide")
        nom = _texte(p.get("nom"), f"{champ}.nom")
        identifiant = str(p.get("id") or "").strip()
        cle = identifiant or unicodedata.normalize("NFKD", nom).casefold().strip()
        if cle in ids:
            raise ValueError(f"{champ} : doublon {nom}")
        ids.add(cle)
        result.append({"nom": nom, "id": identifiant, "poste": str(p.get("poste") or "").strip()})
    return result


def valider(observation: dict, *, au: str | None = None) -> dict:
    """Fige une preuve datée. Impossible d'antidater au moment de l'analyse."""
    if not isinstance(observation, dict):
        raise ValueError("observation JSON attendue")
    match = _texte(observation.get("match_id"), "match_id")
    home, away = (_texte(observation.get(k), k) for k in ("domicile", "exterieur"))
    if home == away:
        raise ValueError("deux équipes distinctes requises")
    coup = _instant(observation.get("coup_envoi"), "coup_envoi")
    capture = _instant(observation.get("collecte_le"), "collecte_le")
    if capture >= coup:
        raise ValueError("observation à/après le coup d'envoi refusée")
    if au is not None and capture > _instant(au, "au"):
        raise ValueError("observation future au regard de l'instant d'analyse")
    publication = observation.get("publie_le")
    if publication is not None and _instant(publication, "publie_le") > capture:
        raise ValueError("publication postérieure à la collecte")
    source = _texte(observation.get("source"), "source").lower()
    if source not in SOURCES:
        raise ValueError("source inconnue")
    url = _texte(observation.get("source_url"), "source_url")
    parsed = urlparse(url)
    domaine = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not domaine or parsed.username or parsed.password:
        raise ValueError("URL HTTPS de preuve requise")
    attendu = SOURCES[source]
    if attendu and not (domaine == attendu or domaine.endswith("." + attendu)):
        raise ValueError(f"source_url ne correspond pas à {source}")
    statut = _texte(observation.get("statut"), "statut")
    if statut not in STATUTS:
        raise ValueError("statut probable/confirmee_fournisseur/confirmee_officielle requis")
    if source != "officiel" and statut == "confirmee_officielle":
        raise ValueError("un fournisseur tiers ne constitue pas une source officielle directe")
    if source == "officiel" and statut != "confirmee_officielle":
        raise ValueError("une fiche officielle doit être une composition confirmée")
    equipes = observation.get("equipes")
    if not isinstance(equipes, dict) or set(equipes) != {"H", "A"}:
        raise ValueError("equipes H et A requises")
    sorties = {}
    for cote in ("H", "A"):
        d = equipes[cote]
        if not isinstance(d, dict):
            raise ValueError("données d'équipe invalides")
        titulaires = _joueurs(d.get("titulaires", []), f"{cote}.titulaires")
        banc = _joueurs(d.get("banc", []), f"{cote}.banc")
        absents = _joueurs(d.get("absents", []), f"{cote}.absents")
        clefs = [p["id"] or p["nom"].casefold() for p in titulaires + banc + absents]
        if len(clefs) != len(set(clefs)):
            raise ValueError(f"{cote} : joueur présent dans plusieurs catégories")
        if len(titulaires) > 11:
            raise ValueError(f"{cote} : plus de 11 titulaires")
        if statut != "probable" and len(titulaires) != 11:
            raise ValueError(f"{cote} : XI déclaré confirmé mais incomplet")
        sorties[cote] = {"titulaires": titulaires, "banc": banc, "absents": absents,
                         "formation": str(d.get("formation") or "").strip(),
                         "xi_complet": len(titulaires) == 11}
    if source == "officiel" and not observation.get("organisme"):
        raise ValueError("organisme officiel requis (vérification humaine)")
    return {"version": "EXP-022/v1", "match_id": match, "domicile": home, "exterieur": away,
            "competition": str(observation.get("competition") or ""),
            "coup_envoi": coup.isoformat(), "collecte_le": capture.isoformat(),
            "publie_le": _instant(publication, "publie_le").isoformat() if publication else None,
            "source": source, "source_url": url, "statut": statut,
            "canal": str(observation.get("canal") or source),
            "organisme": str(observation.get("organisme") or ""),
            "equipes": sorties, "verification": "SOURCE_ATTRIBUEE_NON_AUDITEE",
            "ajustement_probabilites": False}


def charger(archive: Path) -> list[dict]:
    if not archive.exists():
        return []
    return [json.loads(l) for l in archive.read_text(encoding="utf-8").splitlines() if l.strip()]


def ajouter(archive: Path, observation: dict, *, au: str | None = None) -> dict:
    """Ajout sans écrasement, doublons exacts ignorés ; aucune écriture dans memoire/."""
    v = valider(observation, au=au)
    v["empreinte"] = hashlib.sha256(json.dumps(v, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    anciennes = charger(archive)
    for ancien in anciennes:
        if ancien.get("match_id") == v["match_id"] and any(ancien.get(k) != v[k] for k in
                ("domicile", "exterieur", "coup_envoi")):
            raise ValueError("match_id déjà utilisé pour une autre affiche ou un autre coup d'envoi")
    if any(r.get("empreinte") == v["empreinte"] for r in anciennes):
        return {"statut": "doublon", "empreinte": v["empreinte"]}
    archive.parent.mkdir(parents=True, exist_ok=True)
    with archive.open("a", encoding="utf-8") as f:
        f.write(json.dumps(v, ensure_ascii=False, sort_keys=True) + "\n")
    return {"statut": "ajoute", "empreinte": v["empreinte"]}


def _cle(joueur: dict) -> str:
    return joueur["id"] or joueur["nom"].casefold()


def _complet(record: dict, cote: str) -> bool:
    return record["equipes"][cote]["xi_complet"]


def analyser(archive: list[dict], match_id: str, au: str, *, profondeur: int = 5) -> dict:
    """XI actuel vs derniers XI *antérieurs* confirmés, sur même équipe.

    Les deux XI d'une même rencontre ne sont jamais additionnés en doublon.
    Une composition prédite ne devient jamais une composition officielle.
    """
    instant = _instant(au, "au")
    actuelles = [r for r in archive if r["match_id"] == match_id and _instant(r["collecte_le"], "collecte_le") <= instant
                 and _instant(r["collecte_le"], "collecte_le") < _instant(r["coup_envoi"], "coup_envoi")]
    if not actuelles:
        return {"match_id": match_id, "statut": "ABSENT", "ajustement_probabilites": False}
    # Pas de promotion d'un XI probable par déduction ; l'ordre de confiance
    # départage les sources, puis la fraîcheur de la capture.
    rang = {"probable": 0, "confirmee_fournisseur": 1, "confirmee_officielle": 2}
    courant = max(actuelles, key=lambda r: (rang[r["statut"]], _instant(r["collecte_le"], "collecte_le")))
    ko = _instant(courant["coup_envoi"], "coup_envoi")
    resultat = {"match_id": match_id, "au": instant.isoformat(), "source": courant["source"],
                "source_url": courant["source_url"], "statut_composition": courant["statut"],
                "collecte_le": courant["collecte_le"], "equipes": {},
                "ajustement_probabilites": False, "impact_probabilites": "NON_CALIBRE"}
    for cote, nom in (("H", courant["domicile"]), ("A", courant["exterieur"])):
        x = courant["equipes"][cote]
        precedent: dict[str, dict] = {}
        for r in archive:
            if r["match_id"] == match_id or r["statut"] not in ("confirmee_fournisseur", "confirmee_officielle"):
                continue
            if _instant(r["collecte_le"], "collecte_le") > instant:
                continue
            date = _instant(r["coup_envoi"], "coup_envoi")
            if date >= ko:
                continue
            rcote = "H" if r["domicile"] == nom else "A" if r["exterieur"] == nom else None
            if rcote is None or not _complet(r, rcote):
                continue
            # Un XI par rencontre ; la source officielle prime.
            ancien = precedent.get(r["match_id"])
            if ancien is None or (rang[r["statut"]], _instant(r["collecte_le"], "collecte_le")) > (rang[ancien["statut"]], _instant(ancien["collecte_le"], "collecte_le")):
                precedent[r["match_id"]] = {**r, "_cote": rcote}
        derniers = sorted(precedent.values(), key=lambda r: (_instant(r["coup_envoi"], "coup_envoi"), r["match_id"]), reverse=True)[:profondeur]
        freq = Counter(_cle(j) for r in derniers for j in r["equipes"][r["_cote"]]["titulaires"])
        noms = {_cle(j): j["nom"] for r in derniers for j in r["equipes"][r["_cote"]]["titulaires"]}
        actuels = {_cle(j) for j in x["titulaires"]}
        habituels = {j for j, nb in freq.items() if len(derniers) >= 3 and nb / len(derniers) >= 0.6}
        # Aucun motif de non-sélection (blessure/rotation) n'est déduit.
        resultat["equipes"][cote] = {"nom": nom, "xi_complet": x["xi_complet"],
            "historiques_confirmes": len(derniers), "rencontres_reference": [r["match_id"] for r in derniers],
            "changements_vs_dernier_xi": len(actuels - {_cle(j) for j in derniers[0]["equipes"][derniers[0]["_cote"]]["titulaires"]}) if derniers and x["xi_complet"] else None,
            "habituels_non_titulaires": sorted(noms[j] for j in habituels - actuels) if x["xi_complet"] else [],
            "signal_changements_massifs": len(habituels - actuels) >= 3 if x["xi_complet"] and len(derniers) >= 3 else None,
            "motif_non_selection": "INCONNU : ne pas déduire une rotation ou une blessure",
            "absences_declarees": [j["nom"] for j in x["absents"]],
            "couverture": "COMPARABLE" if x["xi_complet"] and len(derniers) >= 3 else "INSUFFISANTE"}
    return resultat
