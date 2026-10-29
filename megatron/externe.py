"""Faits externes collectés (branche `donnees-externes`) versés dans la grille du favori.

Seules les lignes dont `collecte_le` précède à la fois l'instant d'analyse et le coup
d'envoi sont lues (anti-fuite). Les faits remplissent l'angle `informations_manquantes`
à l'état `a_verifier` : aucune probabilité n'est modifiée, l'importance des absents
reste à juger.
"""
from __future__ import annotations

import csv
from datetime import timedelta
from pathlib import Path

from .store import now_utc, parse_dt

SOURCES = {
    "apifootball": ("api-football", "https://v3.football.api-sports.io/injuries?fixture={fixture_id}"),
    "apifootball_compos": ("api-football", "https://v3.football.api-sports.io/fixtures/lineups?fixture={fixture_id}"),
    "fpl": ("fpl", "https://fantasy.premierleague.com/api/bootstrap-static/"),
}
FENETRE = timedelta(hours=12)  # écart toléré entre le coup d'envoi déclaré et celui de la source


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


def faits(dossier: Path, equipe: str, kickoff: str, at: str | None = None) -> dict:
    """Absences (API-Football), compo officielle (API-Football) et statuts FPL d'une équipe pour un match."""
    ko = parse_dt(kickoff)
    avant = min(parse_dt(at or now_utc()), ko)
    out = {"equipe": equipe, "absences": [], "compo": [], "fpl": []}
    for snap in instantanes(dossier, "apifootball/blessures", avant)[:1]:
        out["absences"] = [l for l in snap if _du_match(l, equipe, ko)]
    for snap in instantanes(dossier, "apifootball/compos", avant):  # un instantané ne contient que les matchs de son heure
        out["compo"] = [l for l in snap if _du_match(l, equipe, ko)]
        if out["compo"]:
            break
    for snap in instantanes(dossier, "fpl", avant)[:1]:
        out["fpl"] = [l for l in snap if l.get("equipe") == equipe]
    return out


def _sources(f: dict) -> list[dict]:
    vues = {}
    for cle, lignes in (("apifootball", f["absences"]), ("apifootball_compos", f["compo"]), ("fpl", f["fpl"])):
        if lignes:
            famille, url = SOURCES[cle]
            l = lignes[0]
            vues[url.format(fixture_id=l.get("fixture_id", ""))] = {
                "url": url.format(fixture_id=l.get("fixture_id", "")), "famille": famille,
                "publie_le": l["collecte_le"], "collecte_le": l["collecte_le"]}
    return list(vues.values())


def _resume(f: dict) -> str:
    parts = []
    if f["absences"]:
        parts.append("absents API-Football : " + ", ".join(f"{l['joueur']} ({l['type']}, {l['motif']})" for l in f["absences"]))
    if f["fpl"]:
        parts.append("FPL : " + ", ".join(f"{l['joueur']} ({l['statut']}, {l['chance_prochain_match'] or '?'} %)" for l in f["fpl"]))
    titulaires = [l for l in f["compo"] if l.get("statut") == "titulaire"]
    if titulaires:
        parts.append(f"compo officielle ({titulaires[0].get('formation') or '?'}) : " + ", ".join(l["joueur"] for l in titulaires))
    return f"{f['equipe']} — " + ("; ".join(parts) if parts else "aucun fait collecté")


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
        if not (f["absences"] or f["compo"] or f["fpl"]):
            manques.append(f"aucune donnée externe pour « {f['equipe']} » (nom différent dans la source ?)")
        elif not f["compo"]:
            manques.append(f"compo officielle de {f['equipe']} non collectée")
    out = {**doc, "angles": [dict(a) for a in doc["angles"]]}
    for a in out["angles"]:
        if a.get("id") == "informations_manquantes":
            a.update({"etat": "a_verifier", "constat": " | ".join(_resume(f) for f in tous),
                      "sources": (a.get("sources") or []) + [s for s in sources if s not in (a.get("sources") or [])],
                      "categorie_preuve": "absences", "informations_manquantes": manques})
    return out
