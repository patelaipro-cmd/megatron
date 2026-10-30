"""Modèle xg-v1-cal (EXP-018, EXP-020) : forces d'équipes dynamiques nourries par les xG Understat.

Candidat statistique, **pas en production** : EXP-020 l'a rejeté (validation non significative) ;
poisson-v5-cal reste le 1X2 de ``StatsAgent``. Ce module sert à le prévoir sans fuite, pour une
comparaison prospective sur 2026/27 (EXP-014), si Luloki l'active en observation.

Données xG : fichiers ``matchs_equipes_*.csv`` de la branche ``donnees-externes``
(``externe/understat/historique/`` et ``externe/understat/`` pour la saison en cours). Chiffre
d'après-match : seul le passé du jour prévu est lu, et seulement les lignes collectées avant
l'instant de la prévision.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import data, models
from .agents import Agent, AgentResponse
from .dynamique import Filtre, Reglage, issues

DIVISION = {"ENG-Premier League": "E0", "ESP-La Liga": "SP1", "ITA-Serie A": "I1", "GER-Bundesliga": "D1",
            "FRA-Ligue 1": "F1"}
REGLAGE = Reglage(w=0.5, q=0.0001, q_saison=0.0, p0=0.05, c=0.15, correction=False)  # EXP-016 + w d'EXP-018
CALIBRATION = (1.075291, 0.025332, 0.091197)  # b, c_H, c_D appris par EXP-020 sur 2015/16-2017/18
VERSION = "xg-v1-cal"


def _dt(s: str) -> datetime:
    d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def charger(dossiers: list[Path], avant: datetime | None = None) -> list[dict]:
    """Lignes xG des dossiers ; une par match (la collecte la plus récente gagne).

    ``avant`` : ignore les lignes collectées à cet instant ou après (preuve temporelle).
    """
    garde: dict[tuple, dict] = {}
    for dossier in dossiers:
        for f in sorted(Path(dossier).glob("matchs_equipes_*.csv")):
            with f.open(newline="", encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    if r.get("league") not in DIVISION or not r.get("home_xg") or not r.get("away_xg"):
                        continue
                    quand = _dt(r["collecte_le"]) if r.get("collecte_le") else None
                    if avant is not None and (quand is None or quand >= avant):
                        continue
                    ligne = {"division": DIVISION[r["league"]], "jour": date.fromisoformat(r["date"][:10]),
                             "dom": r["home_team"], "ext": r["away_team"], "bd": int(float(r["home_goals"])),
                             "be": int(float(r["away_goals"])), "xg": (float(r["home_xg"]), float(r["away_xg"])),
                             "collecte_le": quand}
                    cle = (ligne["division"], ligne["jour"], ligne["dom"], ligne["ext"])
                    ancien = garde.get(cle)
                    if ancien is None or (quand and (ancien["collecte_le"] is None or quand > ancien["collecte_le"])):
                        garde[cle] = ligne
    return list(garde.values())


def relier(xg: list[dict], matchs: list[data.Match]) -> tuple[dict[str, tuple[float, float]], dict]:
    """Noms Understat → data/ par vote sur les matchs communs (date ± 1 j, même score), puis liaison.

    Méthode d'EXP-018, mais vote par saison : data/ change parfois d'orthographe (« Nottm Forest »
    puis « Nott'm Forest »), un vote sur tout l'historique perdrait la saison en cours."""
    par_jour = defaultdict(list)
    for m in matchs:
        par_jour[(m.division, m.day)].append(m)

    def proches(r):
        return [m for d in (-1, 0, 1) for m in par_jour[(r["division"], r["jour"] + timedelta(days=d))]]

    votes = defaultdict(Counter)
    for r in xg:
        for m in proches(r):
            if (m.home_goals, m.away_goals) == (r["bd"], r["be"]):
                s = data.season_of(r["jour"])
                votes[(r["division"], s, r["dom"])][m.home] += 1
                votes[(r["division"], s, r["ext"])][m.away] += 1
    noms = {k: c.most_common(1)[0][0] for k, c in votes.items()}
    lie, rejets = {}, Counter()
    for r in xg:
        s = data.season_of(r["jour"])
        h, a = noms.get((r["division"], s, r["dom"])), noms.get((r["division"], s, r["ext"]))
        ms = [m for m in proches(r) if (m.home, m.away) == (h, a)]
        if len(ms) != 1:
            rejets["non_relie"] += 1
        elif (ms[0].home_goals, ms[0].away_goals) != (r["bd"], r["be"]):
            rejets["score_different"] += 1
        else:
            lie[ms[0].match_id] = r["xg"]
    return lie, {"lignes_xg": len(xg), "relies": len(lie), **rejets}


def intensites(matchs: list[data.Match], xg: dict[str, tuple[float, float]], division: str, home: str,
               away: str, day: date) -> tuple[float, float, int]:
    """Filtre déroulé sur les seuls matchs d'avant ``day`` ; renvoie (λ_dom, λ_ext, matchs vus)."""
    f = Filtre(REGLAGE)
    vus = 0
    for m in sorted((m for m in matchs if m.day < day), key=lambda m: (m.kickoff, m.match_id)):  # ordre de data.load
        f.mettre_a_jour(m, xg.get(m.match_id), mode_xg=True)
        vus += 1
    lh, la = f.intensites(division, home, away, day)
    return lh, la, vus


def probabilites(lh: float, la: float) -> dict[str, float]:
    return models.calibrer_1x2(issues(lh, la), *CALIBRATION)


class XgAgent(Agent):
    """Agent d'observation xg-v1-cal : aucun token ; absent de ``default_agents`` (non promu)."""

    name = "xg"

    def __init__(self, dossiers_xg: list[Path], csv_path=None, avant: datetime | None = None):
        self.dossiers_xg, self.csv_path, self.avant = list(dossiers_xg), csv_path, avant

    def ask(self, task: dict) -> AgentResponse:
        try:
            day = date.fromisoformat(task["date"])
            division, home, away = task["division"], task["home"], task["away"]
        except (KeyError, ValueError) as exc:
            return AgentResponse(agent=self.name, status="erreur", raison=f"entrée invalide : {exc}")
        path = self.csv_path or data.CURRENT
        matchs = [m for m in data.load(path, divisions={division}) if m.day < day]
        if not matchs:
            return AgentResponse(agent=self.name, status="erreur", raison=f"aucun match de {division} avant le {day}")
        lignes = [r for r in charger(self.dossiers_xg, self.avant) if r["division"] == division and r["jour"] < day]
        if not lignes:
            return AgentResponse(agent=self.name, status="indisponible", raison="aucune donnée xG lisible")
        xg, liaison = relier(lignes, matchs)
        lh, la, vus = intensites(matchs, xg, division, home, away, day)
        probs = probabilites(lh, la)
        saison = data.season_of(day)
        sans_xg = sum(1 for m in matchs if data.season_of(m.day) == saison and m.match_id not in xg)
        fav = max(probs, key=probs.get)
        return AgentResponse(
            agent=self.name, status="ok", probs=probs, version=VERSION,
            conclusion=f"[{VERSION}] issue la plus probable {fav} ({probs[fav]:.0%})",
            preuves=[f"{vus} matchs antérieurs au {day}, {liaison['relies']} avec xG",
                     f"buts attendus {lh:.2f} - {la:.2f}"],
            hypotheses=["buts indépendants, loi de Poisson", "observation = 0,5 buts + 0,5 xG"],
            incertitudes=([f"{sans_xg} matchs de la saison sans xG relié (buts seuls)"] if sans_xg else [])
            + ["candidat rejeté par EXP-020 : observation seulement", "xG Understat révisables après coup"],
            sources=["data/ (résultats)", "Understat via donnees-externes (xG)"],
            tokens_entree=0, tokens_sortie=0, tokens_mesure="mesure",
        )
