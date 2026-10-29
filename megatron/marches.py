"""Marchés binaires sur le total de buts : 2+ (au moins 2 buts) et 3+ (au moins 3, soit plus de 2,5).

Sous Poisson indépendant, le total suit une loi de Poisson de paramètre
λ_dom + λ_ext. EXP-006 évalue ces probabilités contre les fréquences passées
et, pour le 3+, contre les cotes plus/moins de 2,5 buts.
"""

from __future__ import annotations

import csv
import math
import random
from datetime import date
from itertools import groupby
from pathlib import Path

from . import models
from .data import DATA, Match, season_of

MARCHES_BUTS = {"2+": 2, "3+": 3}
ISSUES_BINAIRES = ("oui", "non")
COTES_BUTS = DATA / "cotes_buts_2000-2026.csv"
V4 = {"half_life": 90.0, "shrink": 3.0, "proxy": "cadres", "proxy_weight": 0.25}  # figé par EXP-004/005
EPS = 1e-15


def total_au_moins(lam_total: float, seuil: int) -> float:
    """P(T ≥ seuil) pour T ~ Poisson(lam_total)."""
    return 1 - sum(math.exp(-lam_total) * lam_total ** k / math.factorial(k) for k in range(seuil))


def probs_buts(lam_home: float, lam_away: float) -> dict[str, dict[str, float]]:
    out = {}
    for marche, seuil in MARCHES_BUTS.items():
        p = total_au_moins(lam_home + lam_away, seuil)
        out[marche] = {"oui": p, "non": 1 - p}
    return out


def issue_buts(marche: str, home_goals: int, away_goals: int) -> str:
    return "oui" if home_goals + away_goals >= MARCHES_BUTS[marche] else "non"


def load_cotes(path: str | Path = COTES_BUTS) -> dict[str, tuple[float, float]]:
    """match_id → (cote plus de 2,5, cote moins de 2,5)."""
    with open(path, newline="", encoding="utf-8") as fh:
        return {f"{r['Division']}:{r['MatchDate']}:{r['HomeTeam']}-{r['AwayTeam']}":
                (float(r["Over25"]), float(r["Under25"])) for r in csv.DictReader(fh)}


def bookmaker_3plus(cotes: tuple[float, float] | None) -> dict[str, float] | None:
    if not cotes:
        return None
    over, under = 1 / cotes[0], 1 / cotes[1]
    return {"oui": over / (over + under), "non": under / (over + under)}


def frequences(history: list[Match], day: date, seuil: int, lookback_days: int = 730) -> dict[str, float]:
    recent = [m for m in history if (day - m.day).days <= lookback_days]
    if recent and max(m.day for m in recent) >= day:
        raise AssertionError(f"fuite temporelle : historique non antérieur au {day}")
    oui = 1 + sum(m.home_goals + m.away_goals >= seuil for m in recent)
    p = oui / (len(recent) + 2)
    return {"oui": p, "non": 1 - p}


def predict_seasons(matches: list[Match], division: str, seasons: set[str],
                    cotes: dict[str, tuple[float, float]]) -> list[dict]:
    """Une ligne par match : issue et probabilités de chaque modèle pour chaque marché."""
    league = [m for m in matches if m.division == division]
    rows = []
    for day, group in groupby((m for m in league if season_of(m.day) in seasons), key=lambda m: m.day):
        history = [m for m in league if m.day < day]
        fit = models.fit_maher(history, day, **V4)
        freq = {k: frequences(history, day, s) for k, s in MARCHES_BUTS.items()}
        for m in group:
            pv4 = probs_buts(*fit.rates(m.home, m.away))
            for marche in MARCHES_BUTS:
                rows.append({"match_id": m.match_id, "saison": season_of(m.day), "marche": marche,
                             "issue": issue_buts(marche, m.home_goals, m.away_goals),
                             "poisson-v4": pv4[marche], "frequences": freq[marche],
                             "bookmaker": bookmaker_3plus(cotes.get(m.match_id)) if marche == "3+" else None})
    return rows


MODELES = ("poisson-v4", "frequences", "bookmaker")


def write_predictions(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["match_id", "saison", "marche", "issue", *MODELES])
        for r in rows:
            w.writerow([r["match_id"], r["saison"], r["marche"], r["issue"]]
                       + [f"{r[k]['oui']:.5f}" if r[k] else "" for k in MODELES])


def read_predictions(path: Path) -> list[dict]:
    rows = []
    with path.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            row = {k: r[k] for k in ("match_id", "saison", "marche", "issue")}
            for k in MODELES:
                row[k] = {"oui": float(r[k]), "non": 1 - float(r[k])} if r[k] else None
            rows.append(row)
    return rows


def score_binaire(pairs: list[tuple[dict[str, float], str]], bins: int = 10) -> dict:
    n = len(pairs)
    if not n:
        return {"n": 0, "log_loss": None, "brier": None, "calibration": []}
    log_loss = -sum(math.log(max(p[y], EPS)) for p, y in pairs) / n
    brier = sum((p["oui"] - (y == "oui")) ** 2 for p, y in pairs) / n
    buckets = [[0, 0.0, 0] for _ in range(bins)]
    for p, y in pairs:
        b = min(int(p["oui"] * bins), bins - 1)
        buckets[b][0] += 1
        buckets[b][1] += p["oui"]
        buckets[b][2] += y == "oui"
    calibration = [{"tranche": f"{i / bins:.1f}-{(i + 1) / bins:.1f}", "n": c, "p_moyenne": round(s / c, 4),
                    "frequence_observee": round(k / c, 4), "ecart": round(k / c - s / c, 4)}
                   for i, (c, s, k) in enumerate(buckets) if c]
    return {"n": n, "log_loss": round(log_loss, 6), "brier": round(brier, 6), "calibration": calibration}


def bootstrap(rows: list[dict], a: str, b: str, draws: int = 2000, seed: int = 1) -> dict:
    """Écart moyen de log-loss a − b et IC 95 % (rééchantillonnage des matchs)."""
    diffs = [math.log(max(r[b][r["issue"]], EPS)) - math.log(max(r[a][r["issue"]], EPS))
             for r in rows if r[a] and r[b]]
    if not diffs:
        return {"n": 0, "ecart": None, "ic95": None}
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(draws))
    return {"n": len(diffs), "ecart": round(sum(diffs) / len(diffs), 5),
            "ic95": [round(means[int(0.025 * draws)], 5), round(means[int(0.975 * draws) - 1], 5)]}


def bilan(rows: list[dict]) -> dict:
    """Critères M1-M3 d'EXP-006 pour chaque marché, plus le détail par ligue."""
    out = {}
    for marche in MARCHES_BUTS:
        rm = [r for r in rows if r["marche"] == marche]
        par_ligue = {}
        for div in sorted({r["match_id"].split(":")[0] for r in rm}):
            rl = [r for r in rm if r["match_id"].startswith(div + ":")]
            par_ligue[div] = bootstrap(rl, "poisson-v4", "frequences")
        scores = {k: score_binaire([(r[k], r["issue"]) for r in rm if r[k]]) for k in MODELES}
        m1 = bootstrap(rm, "poisson-v4", "frequences")
        calib = [c for c in scores["poisson-v4"]["calibration"] if c["n"] >= 500]
        out[marche] = {
            "scores": scores,
            "M1_v4_moins_frequences": m1,
            "M1": m1["ic95"] is not None and m1["ic95"][1] < 0,
            "M2_par_ligue": par_ligue,
            "M2": sum(v["ecart"] is not None and v["ecart"] < 0 for v in par_ligue.values()) >= 4,
            "M3_ecart_max": max((abs(c["ecart"]) for c in calib), default=None),
            "M3": bool(calib) and all(abs(c["ecart"]) <= 0.03 for c in calib),
            "info_v4_moins_bookmaker": bootstrap(rm, "poisson-v4", "bookmaker") if marche == "3+" else None,
        }
    return out
