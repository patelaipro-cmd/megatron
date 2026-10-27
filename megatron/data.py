"""Chargement des matchs historiques (extrait Club-Football-Match-Data)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "data" / "matches_top5_2020-2026.csv"


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

    @property
    def match_id(self) -> str:
        return f"{self.division}:{self.day.isoformat()}:{self.home}-{self.away}"


def season_of(day: date) -> str:
    """Saison du 1er juillet au 30 juin, notée 2024/25."""
    start = day.year if day.month >= 7 else day.year - 1
    return f"{start}/{str(start + 1)[-2:]}"


def load(path: str | Path = DEFAULT_CSV, divisions: set[str] | None = None) -> list[Match]:
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
            matches.append(Match(
                division=r["Division"], day=day,
                kickoff=datetime(day.year, day.month, day.day, int(hh), int(mm), tzinfo=timezone.utc),
                home=r["HomeTeam"], away=r["AwayTeam"],
                home_goals=int(r["FTHome"]), away_goals=int(r["FTAway"]), result=r["FTResult"],
                odds=odds,
            ))
    matches.sort(key=lambda m: (m.kickoff, m.match_id))
    return matches
