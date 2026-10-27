"""Backtest chronologique : chaque match est prédit avec le seul passé."""

from __future__ import annotations

import csv
from itertools import groupby
from pathlib import Path

from . import models
from .data import Match, season_of
from .ledger import OUTCOMES, score

MODELS = ("poisson-v1", "frequences", "bookmaker")


def predict_seasons(matches: list[Match], division: str, seasons: set[str], *,
                    half_life: float, shrink: float) -> list[dict]:
    league = [m for m in matches if m.division == division]
    rows = []
    for day, group in groupby((m for m in league if season_of(m.day) in seasons), key=lambda m: m.day):
        history = [m for m in league if m.day < day]
        fit = models.fit_maher(history, day, half_life=half_life, shrink=shrink)
        freq = models.frequencies(history, day)
        for m in group:
            rows.append({
                "match_id": m.match_id, "saison": season_of(m.day), "issue": m.result,
                "poisson-v1": models.poisson_v1(fit, m),
                "frequences": freq,
                "bookmaker": models.bookmaker(m),
            })
    return rows


def summarize(rows: list[dict]) -> dict[str, dict]:
    """Scores par modèle, sur les matchs où tous les modèles ont une prévision."""
    common = [r for r in rows if all(r[k] for k in MODELS)]
    return {k: score([(r[k], r["issue"]) for r in common]) for k in MODELS}


def grid_search(matches: list[Match], division: str, seasons: set[str],
                half_lives: list[float], shrinks: list[float]) -> list[dict]:
    out = []
    for hl in half_lives:
        for k in shrinks:
            s = summarize(predict_seasons(matches, division, seasons, half_life=hl, shrink=k))
            out.append({"half_life": hl, "shrink": k, **{m: s[m]["log_loss"] for m in MODELS},
                        "rps": s["poisson-v1"]["rps"], "n": s["poisson-v1"]["n"]})
    return sorted(out, key=lambda r: r["poisson-v1"])


def write_predictions(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["match_id", "saison", "issue"] + [f"{m}_{o}" for m in MODELS for o in OUTCOMES])
        for r in rows:
            w.writerow([r["match_id"], r["saison"], r["issue"]]
                       + [f"{r[m][o]:.4f}" if r[m] else "" for m in MODELS for o in OUTCOMES])
