"""Fiches prématch attribuées à cinq sites, sans accès privé ni scraping.

Ce module *importe* des observations réellement consultées. Il n'affirme ni
qu'une page est officielle, ni qu'une donnée Premium peut être téléchargée.
Les fiches restent descriptives : aucune influence sur les probabilités.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from . import compositions_prematch as xi

SITES = {
    "sportsmole": {"domaine": "sportsmole.co.uk", "types": {"analyse", "xi"}},
    "sportsgambler": {"domaine": "sportsgambler.com", "types": {"analyse", "xi"}},
    "pianetafanta": {"domaine": "pianetafanta.it", "types": {"analyse", "xi"}},
    "180score": {"domaine": "180score.com", "types": {"classement", "h2h", "prediction", "xi"}},
    "xpertstats": {"domaine": "xpertstats.com", "types": {"classement", "h2h", "analyse", "prediction"}},
}


def _instant(valeur, champ: str) -> datetime:
    return xi._instant(valeur, champ)


def _nom(valeur, champ: str) -> str:
    return xi._texte(valeur, champ)


def _url(valeur, domaine_attendu: str) -> str:
    url = _nom(valeur, "source_url")
    parsed = urlparse(url)
    domaine = (parsed.hostname or "").lower()
    if (parsed.scheme != "https" or parsed.username or parsed.password
            or not (domaine == domaine_attendu or domaine.endswith("." + domaine_attendu))):
        raise ValueError(f"source_url : domaine HTTPS attendu {domaine_attendu}")
    return url


def _rang(valeur, champ: str) -> int:
    if type(valeur) is not int or valeur < 1:
        raise ValueError(f"{champ} : rang entier positif requis")
    return valeur


def valider_fiche(fiche: dict, *, au: str | None = None) -> dict:
    """Vérifie forme, provenance et chronologie, jamais la véracité d'un site."""
    if not isinstance(fiche, dict):
        raise ValueError("fiche JSON requise")
    source = _nom(fiche.get("source"), "source").lower()
    if source not in SITES:
        raise ValueError("source non prise en charge")
    genre = _nom(fiche.get("type"), "type").lower()
    if genre not in SITES[source]["types"]:
        raise ValueError(f"{source} ne fournit pas ce type de fiche dans le protocole")
    url = _url(fiche.get("source_url"), SITES[source]["domaine"])
    home, away = (_nom(fiche.get(k), k) for k in ("domicile", "exterieur"))
    if home.casefold() == away.casefold():
        raise ValueError("équipes identiques")
    kickoff = _instant(fiche.get("coup_envoi"), "coup_envoi")
    capture = _instant(fiche.get("collecte_le"), "collecte_le")
    if capture >= kickoff:
        raise ValueError("fiche capturée après ou au coup d'envoi")
    if au is not None and capture > _instant(au, "au"):
        raise ValueError("fiche future au regard du contrôle")
    publie = fiche.get("publie_le")
    if publie is not None and _instant(publie, "publie_le") > capture:
        raise ValueError("date de publication future")
    match_id = _nom(fiche.get("match_id"), "match_id")
    base = {"version": "SITES-PREMATCH/v1", "source": source, "type": genre,
            "match_id": match_id, "source_url": url, "domicile": home, "exterieur": away,
            "competition": str(fiche.get("competition") or ""),
            "coup_envoi": kickoff.isoformat(), "collecte_le": capture.isoformat(),
            "publie_le": _instant(publie, "publie_le").isoformat() if publie else None,
            "verification": "FICHE_DECLARATIVE_SOURCE_NON_AUDITEE", "ajustement_probabilites": False}
    details = fiche.get("donnees")
    if not isinstance(details, dict):
        raise ValueError("donnees : objet structuré requis")
    if genre == "xi":
        statut = details.get("statut", "probable")
        if source in ("sportsmole", "pianetafanta") and statut != "probable":
            raise ValueError(f"{source} : XI éditorial probable uniquement")
        observation = xi.valider({**base, "statut": statut, "equipes": details.get("equipes")}, au=au)
        base["donnees"] = observation
    elif genre == "classement":
        periode = _instant(details.get("classement_au"), "classement_au")
        if periode > capture or periode >= kickoff:
            raise ValueError("classement postérieur à la capture ou au coup d'envoi")
        base["donnees"] = {"classement_au": periode.isoformat(),
                           "rang_domicile": _rang(details.get("rang_domicile"), "rang_domicile"),
                           "rang_exterieur": _rang(details.get("rang_exterieur"), "rang_exterieur"),
                           "portee": _nom(details.get("portee"), "portee")}
    elif genre == "h2h":
        rencontres = details.get("rencontres")
        if not isinstance(rencontres, list) or not 1 <= len(rencontres) <= 3:
            raise ValueError("h2h : 1 à 3 rencontres historiques requises")
        recentes = []
        for r in rencontres:
            if not isinstance(r, dict):
                raise ValueError("rencontre H2H invalide")
            date = _instant(r.get("date"), "h2h.date")
            if date >= kickoff or date > capture:
                raise ValueError("H2H non antérieur au match analysé")
            score_h, score_a = r.get("buts_domicile"), r.get("buts_exterieur")
            if any(type(score) is not int or score < 0 for score in (score_h, score_a)):
                raise ValueError("score H2H invalide")
            preuve = {"date": date.isoformat(), "domicile": _nom(r.get("domicile"), "h2h.domicile"),
                      "exterieur": _nom(r.get("exterieur"), "h2h.exterieur"),
                      "buts_domicile": score_h, "buts_exterieur": score_a}
            if "classement_avant" in r:
                c = r["classement_avant"]
                if not isinstance(c, dict):
                    raise ValueError("classement_avant invalide")
                au_h2h = _instant(c.get("au"), "classement_avant.au")
                if au_h2h >= date:
                    raise ValueError("classement historique connu seulement après le H2H")
                preuve["classement_avant"] = {"au": au_h2h.isoformat(),
                    "rang_domicile": _rang(c.get("rang_domicile"), "classement_avant.rang_domicile"),
                    "rang_exterieur": _rang(c.get("rang_exterieur"), "classement_avant.rang_exterieur"),
                    "source_url": _url(c.get("source_url"), SITES[source]["domaine"])}
            recentes.append(preuve)
        if len({(r["date"], r["domicile"], r["exterieur"]) for r in recentes}) != len(recentes):
            raise ValueError("H2H dupliqué")
        base["donnees"] = {"rencontres": sorted(recentes, key=lambda r: r["date"], reverse=True)}
    elif genre == "prediction":
        if details.get("marche") != "1X2":
            raise ValueError("seul le marché 1X2 est prévu ; 1X2 n'est pas V+2")
        probs = details.get("probabilites")
        if not isinstance(probs, dict) or set(probs) != {"H", "D", "A"}:
            raise ValueError("probabilités 1X2 H/D/A requises")
        if any(type(x) not in (int, float) or not 0 <= x <= 1 for x in probs.values()) or abs(sum(probs.values()) - 1) > 0.02:
            raise ValueError("probabilités 1X2 invalides")
        base["donnees"] = {"marche": "1X2", "probabilites": probs, "statut": "PREDICTION_FOURNISSEUR_NON_CALIBREE"}
    else:  # analyse : quelques faits courts, pas de reproduction intégrale d'articles
        champs = {"enjeu", "forme", "tactique", "absences", "risque_nul", "note"}
        if not details or not set(details) <= champs:
            raise ValueError("analyse : champs inconnus ou vides")
        if any(not isinstance(v, str) or not v.strip() or len(v) > 300 for v in details.values()):
            raise ValueError("analyse : notes courtes et attribuées requises")
        base["donnees"] = {k: v.strip() for k, v in details.items()}
    return base


def importer_source(dossier: Path, source: str, maintenant: float, *, entrees: Path | None = None) -> dict:
    """Fiches déjà fournies uniquement ; un site Premium n'est jamais aspiré.

    Réécritures interdites ; seule une capture horodatée et distincte est ajoutée.
    """
    if source not in SITES:
        raise ValueError("source non prise en charge")
    repertoire = (entrees or dossier / "imports") / source
    fichiers = sorted(repertoire.glob("*.json"))
    if not fichiers:
        return {"statut": "attente", "fiches": 0,
                "raison": "aucune capture vérifiée importée ; pas d'API/site Premium connecté"}
    ajoutes = 0
    for fichier in fichiers:
        fiche = valider_fiche(json.loads(fichier.read_text(encoding="utf-8")), au=datetime.fromtimestamp(maintenant, tz=timezone.utc).isoformat())
        instant = _instant(fiche["collecte_le"], "collecte_le")
        contenu = json.dumps(fiche, sort_keys=True, ensure_ascii=False)
        empreinte = hashlib.sha256(contenu.encode()).hexdigest()[:16]
        chemin = dossier / "sites" / source / instant.strftime("%Y-%m-%d") / f"{instant:%H%M%S}-{empreinte}.json"
        if not chemin.exists():
            chemin.parent.mkdir(parents=True, exist_ok=True)
            chemin.write_text(contenu + "\n", encoding="utf-8")
            ajoutes += 1
    return {"statut": "ok", "fiches": len(fichiers), "nouvelles": ajoutes,
            "mode": "imports de captures attribuées (aucune extraction HTML/API)"}
