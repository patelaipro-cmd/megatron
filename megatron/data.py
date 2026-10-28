"""Chargement des matchs historiques (extrait Club-Football-Match-Data)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

SHOT_COLUMNS = ("HomeShots", "AwayShots", "HomeTarget", "AwayTarget")
DATA = Path(__file__).resolve().parent.parent / "data"
DEFAULT_CSV = DATA / "matches_top5_2020-2026.csv"  # extrait figé des expériences EXP-001 à EXP-004
# historique complet pour l'agent Stats : xgabora 2000-2026 + saison en cours (openfootball, sans cotes ni tirs)
CURRENT = (DATA / "matches_top5_2000-2026.csv", DATA / "complement_openfootball_2026-27.csv")


@dataclass(frozen=True)
class Match:
    division: str
    day: date
    kickoff: datetime  # UTC ; midi si l'heure manque
    home: str
    away: str
    home_goals: int
    away_goals: int
    result: str  # H, D ou A
    odds: tuple[float, float, float] | None
    shots: tuple[int, int, int, int] | None = None  # tirs dom., tirs ext., cadrés dom., cadrés ext.

    @property
    def match_id(self) -> str:
        return f"{self.division}:{self.day.isoformat()}:{self.home}-{self.away}"


def season_of(day: date) -> str:
    """Saison du 1er juillet au 30 juin, notée 2024/25."""
    start = day.year if day.month >= 7 else day.year - 1
    return f"{start}/{str(start + 1)[-2:]}"


def load(path: str | Path | tuple | list = DEFAULT_CSV, divisions: set[str] | None = None) -> list[Match]:
    """Un fichier ou plusieurs (fusionnés) ; un même match présent deux fois est une erreur."""
    paths = [path] if isinstance(path, (str, Path)) else list(path)
    matches = [m for p in paths for m in _load_one(p, divisions)]
    ids = [m.match_id for m in matches]
    if len(ids) != len(set(ids)):
        dup = sorted({i for i in ids if ids.count(i) > 1})[:5]
        raise ValueError(f"matchs en double entre fichiers : {dup}")
    matches.sort(key=lambda m: (m.kickoff, m.match_id))
    return matches


def _load_one(path: str | Path, divisions: set[str] | None) -> list[Match]:
    matches = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if divisions and r["Division"] not in divisions:
                continue
            day = date.fromisoformat(r["MatchDate"])
            hh, mm = (r["MatchTime"] or "12:00").split(":")[:2]
            odds = None
            if r["OddHome"] and r["OddDraw"] and r["OddAway"]:
                odds = (float(r["OddHome"]), float(r["OddDraw"]), float(r["OddAway"]))
            shots = None
            if all(r.get(c) for c in SHOT_COLUMNS):
                shots = tuple(int(float(r[c])) for c in SHOT_COLUMNS)
            matches.append(Match(
                division=r["Division"], day=day,
                kickoff=datetime(day.year, day.month, day.day, int(hh), int(mm), tzinfo=timezone.utc),
                home=r["HomeTeam"], away=r["AwayTeam"],
                home_goals=int(r["FTHome"]), away_goals=int(r["FTAway"]), result=r["FTResult"],
                odds=odds, shots=shots,
            ))
    return matches
