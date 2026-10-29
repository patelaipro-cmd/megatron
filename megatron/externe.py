"""Faits externes collectés (branche `donnees-externes`) versés dans la grille du favori.

Seules les lignes dont `collecte_le` précède à la fois l'instant d'analyse et le coup
d'envoi sont lues (anti-fuite). Les faits remplissent l'angle `informations_manquantes`
à l'état `a_verifier` : aucune probabilité n'est modifiée, l'importance des absents
reste à juger.
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from datetime import timedelta
from pathlib import Path

from .store import now_utc, parse_dt

SOURCES = {
    "apifootball": ("api-football", "https://v3.football.api-sports.io/injuries?fixture={fixture_id}"),
    "apifootball_compos": ("api-football", "https://v3.football.api-sports.io/fixtures/lineups?fixture={fixture_id}"),
    "fpl": ("fpl", "https://fantasy.premierleague.com/api/bootstrap-static/"),
    "espn": ("espn", "https://site.api.espn.com/apis/site/v2/sports/soccer/{ligue}/summary?event={event_id}"),
}
FENETRE = timedelta(hours=12)  # écart toléré entre le coup d'envoi déclaré et celui de la source
ALIAS = Path(__file__).resolve().parent.parent / "data" / "noms_equipes.json"
GENERIQUES = {"fc", "afc", "cf", "sc", "sv", "fsv", "ac", "as", "ss", "ssc", "us", "ud", "cd", "rcd", "sd", "vfb", "vfl",
              "tsg", "1", "04", "05", "1899", "1846", "calcio", "club", "de", "city", "town", "united", "utd"}


def _jetons(nom: str) -> frozenset:
    sans_accent = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode().casefold()
    return frozenset(t for t in re.split(r"[^a-z0-9]+", sans_accent) if t and t not in GENERIQUES)


def charger_alias(path: Path = ALIAS) -> dict:
    return {k: v for k, v in json.loads(path.read_text(encoding="utf-8")).items() if not k.startswith("_")}


def resoudre(nom: str, candidats, alias: dict | None = None) -> tuple[str | None, str]:
    """Nom de `candidats` désignant `nom`, et la méthode ; (None, raison) si absent ou ambigu."""
    candidats = set(candidats)
    alias = charger_alias() if alias is None else alias
    if nom in candidats:
        return nom, "exact"
    if nom in alias:  # nom piégeux (ex. Paris FC / Paris SG) : seuls les alias déclarés valent
        trouves = [c for c in alias[nom] if c in candidats]
        return (trouves[0], "alias") if trouves else (None, "aucun alias présent")
    cible = _jetons(nom)
    if not cible:
        return None, "nom vide après normalisation"
    egaux = [c for c in candidats if _jetons(c) == cible]
    if len(egaux) == 1:
        return egaux[0], "normalise"
    inclus = [c for c in candidats if cible <= _jetons(c) or (_jetons(c) and _jetons(c) <= cible)]
    if len(egaux) > 1 or len(inclus) > 1:
        return None, "ambigu : " + ", ".join(sorted(egaux or inclus))
    return (inclus[0], "inclusion") if inclus else (None, "introuvable")


def _lire(fichier: Path) -> list[dict]:
    return list(csv.DictReader(fichier.read_text(encoding="utf-8").splitlines()))


def instantanes(dossier: Path, source: str, avant) -> list[list[dict]]:
    """Instantanés de `source` collectés strictement avant `avant`, du plus récent au plus ancien."""
    out = []
    for fichier in sorted((Path(dossier) / source).glob("*/*.csv"), reverse=True):
        lignes = _lire(fichier)
        if lignes and parse_dt(lignes[0]["collecte_le"]) < avant:
            out.append(lignes)
    return out


def _du_match(ligne: dict, equipe: str, kickoff) -> bool:
    if ligne.get("equipe") != equipe:
        return False
    try:
        return abs(parse_dt(ligne["coup_envoi"]) - kickoff) <= FENETRE
    except (KeyError, TypeError, ValueError):
        return False


def faits(dossier: Path, equipe: str, kickoff: str, at: str | None = None, alias: dict | None = None) -> dict:
    """Absences (API-Football), compos officielles (API-Football, ESPN) et statuts FPL d'une équipe pour un match."""
    alias = charger_alias() if alias is None else alias
    ko = parse_dt(kickoff)
    avant = min(parse_dt(at or now_utc()), ko)
    out = {"equipe": equipe, "absences": [], "compo": [], "compo_espn": [], "fpl": [], "noms": {}}

    def nom_source(cle, lignes, creneau):
        # candidats : équipes de la source jouant dans le même créneau (FPL : toutes, sans coup d'envoi)
        cands = {l.get("equipe") for l in lignes if not creneau or _du_match(l, l.get("equipe"), ko)} - {None, ""}
        retenu, methode = resoudre(equipe, cands, alias)
        out["noms"][cle] = {"nom": retenu, "methode": methode}
        return retenu

    for snap in instantanes(dossier, "apifootball/blessures", avant)[:1]:
        n = nom_source("apifootball/blessures", snap, True)
        out["absences"] = [l for l in snap if n and _du_match(l, n, ko)]
    for source, cle in (("apifootball/compos", "compo"), ("espn/compos", "compo_espn")):
        for snap in instantanes(dossier, source, avant):  # un instantané ne contient que les matchs de son heure
            cands = {l.get("equipe") for l in snap if _du_match(l, l.get("equipe"), ko)} - {None, ""}
            n, methode = resoudre(equipe, cands, alias)
            if n:
                out["noms"][source] = {"nom": n, "methode": methode}
                out[cle] = [l for l in snap if _du_match(l, n, ko)]
                break
    for snap in instantanes(dossier, "fpl", avant)[:1]:
        n = nom_source("fpl", snap, False)
        out["fpl"] = [l for l in snap if n and l.get("equipe") == n]
    return out


def _sources(f: dict) -> list[dict]:
    vues = {}
    for cle, lignes in (("apifootball", f["absences"]), ("apifootball_compos", f["compo"]), ("espn", f["compo_espn"]), ("fpl", f["fpl"])):
        if lignes:
            famille, modele = SOURCES[cle]
            l = lignes[0]
            url = modele.format(fixture_id=l.get("fixture_id", ""), ligue=l.get("ligue", ""), event_id=l.get("event_id", ""))
            vues[url] = {"url": url, "famille": famille, "publie_le": l["collecte_le"], "collecte_le": l["collecte_le"]}
    return list(vues.values())


def _resume(f: dict) -> str:
    parts = []
    if f["absences"]:
        parts.append("absents API-Football : " + ", ".join(f"{l['joueur']} ({l['type']}, {l['motif']})" for l in f["absences"]))
    if f["fpl"]:
        parts.append("FPL : " + ", ".join(f"{l['joueur']} ({l['statut']}, {l['chance_prochain_match'] or '?'} %)" for l in f["fpl"]))
    for cle, nom in (("compo", "API-Football"), ("compo_espn", "ESPN")):
        titulaires = [l for l in f[cle] if l.get("statut") == "titulaire"]
        if titulaires:
            parts.append(f"compo officielle {nom} ({titulaires[0].get('formation') or '?'}) : " + ", ".join(l["joueur"] for l in titulaires))
    noms = ", ".join(f"{k} = {v['nom']} ({v['methode']})" for k, v in f["noms"].items() if v["nom"] and v["nom"] != f["equipe"])
    return f"{f['equipe']}" + (f" [{noms}]" if noms else "") + " — " + ("; ".join(parts) if parts else "aucun fait collecté")


def enrichir(doc: dict, dossier: Path, *, at: str | None = None, noms: dict | None = None) -> dict:
    """Copie de `doc` dont l'angle `informations_manquantes` reçoit les faits collectés avant le match."""
    noms = noms or {}
    equipes = [noms.get(doc["home"]) or doc["home"], noms.get(doc["away"]) or doc["away"]]
    tous = [faits(dossier, e, doc["kickoff"], at) for e in equipes]
    sources, manques = [], ["importance des absents et remplaçants non évaluée"]
    for f in tous:
        for s in _sources(f):
            if s not in sources:
                sources.append(s)
        for cle, n in f["noms"].items():
            if n["nom"] is None and n["methode"].startswith("ambigu"):
                manques.append(f"{f['equipe']} / {cle} : nom {n['methode']} (ajouter un alias dans data/noms_equipes.json)")
        if not (f["absences"] or f["compo"] or f["compo_espn"] or f["fpl"]):
            manques.append(f"aucune donnée externe pour « {f['equipe']} » (absent des sources ou nom à ajouter dans data/noms_equipes.json)")
        elif not (f["compo"] or f["compo_espn"]):
            manques.append(f"compo officielle de {f['equipe']} non collectée")
    out = {**doc, "angles": [dict(a) for a in doc["angles"]]}
    for a in out["angles"]:
        if a.get("id") == "informations_manquantes":
            a.update({"etat": "a_verifier", "constat": " | ".join(_resume(f) for f in tous),
                      "sources": (a.get("sources") or []) + [s for s in sources if s not in (a.get("sources") or [])],
                      "categorie_preuve": "absences", "informations_manquantes": manques})
    return out
