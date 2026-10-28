"""Backtest chronologique : chaque match est prédit avec le seul passé."""

from __future__ import annotations

import csv
import math
import random
from itertools import groupby
from pathlib import Path

from . import models
from .data import Match, season_of
from .ledger import OUTCOMES, score

BASELINES = ("frequences", "bookmaker")
Config = tuple  # demi-vie, rétrécissement, Dixon-Coles[, a priori des nouveaux[, proxy, poids du proxy]]


def predict_seasons(matches: list[Match], division: str, seasons: set[str],
                    configs: dict[str, Config]) -> list[dict]:
    league = [m for m in matches if m.division == division]
    rows = []
    for day, group in groupby((m for m in league if season_of(m.day) in seasons), key=lambda m: m.day):
        history = [m for m in league if m.day < day]
        fits = {name: models.fit_maher(history, day, **fit_kwargs(c)) for name, c in configs.items()}
        freq = models.frequencies(history, day)
        for m in group:
            row = {"match_id": m.match_id, "saison": season_of(m.day), "issue": m.result,
                   "frequences": freq, "bookmaker": models.bookmaker(m)}
            row.update({name: models.predict_1x2(fit, m) for name, fit in fits.items()})
            rows.append(row)
    return rows


def fit_kwargs(c: Config) -> dict:
    kw = {"half_life": c[0], "shrink": c[1], "dixon_coles": c[2]}
    if len(c) > 3:
        kw["newcomer_prior"] = c[3]
    if len(c) > 5:
        kw["proxy"], kw["proxy_weight"] = c[4], c[5]
    return kw


def model_names(rows: list[dict]) -> list[str]:
    return [k for k in rows[0] if k not in ("match_id", "saison", "issue")] if rows else []


def summarize(rows: list[dict]) -> dict[str, dict]:
    """Scores par modèle, sur les matchs où tous les modèles ont une prévision."""
    names = model_names(rows)
    common = [r for r in rows if all(r[k] for k in names)]
    return {k: score([(r[k], r["issue"]) for r in common]) for k in names}


def grid_search(matches: list[Match], division: str, seasons: set[str], half_lives: list[float],
                shrinks: list[float], dixon_coles: list[bool],
                priors: tuple[str, ...] = ("moyenne",),
                proxies: tuple[tuple[str, float], ...] = (("cadres", 0.0),)) -> list[dict]:
    configs = {f"{hl}|{k}|{dc}|{p}|{x}|{w}": (hl, k, dc, p, x, w)
               for hl in half_lives for k in shrinks for dc in dixon_coles for p in priors for x, w in proxies}
    s = summarize(predict_seasons(matches, division, seasons, configs))
    out = [{"half_life": hl, "shrink": k, "dixon_coles": dc, "a_priori": p, "proxy": x, "poids_proxy": w,
            "log_loss": s[name]["log_loss"], "rps": s[name]["rps"], "n": s[name]["n"]}
           for name, (hl, k, dc, p, x, w) in configs.items()]
    return sorted(out, key=lambda r: r["log_loss"])


def paired_bootstrap(rows: list[dict], a: str, b: str, draws: int = 2000, seed: int = 1) -> dict:
    """Écart moyen de log-loss a − b et intervalle à 95 % (rééchantillonnage des matchs)."""
    diffs = [math.log(max(r[b][r["issue"]], 1e-15)) - math.log(max(r[a][r["issue"]], 1e-15))
             for r in rows if r[a] and r[b]]
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(draws))
    return {"n": len(diffs), "ecart": round(sum(diffs) / len(diffs), 5),
            "ic95": [round(means[int(0.025 * draws)], 5), round(means[int(0.975 * draws) - 1], 5)]}


def read_predictions(path: Path) -> list[dict]:
    """Relit un predictions.csv sous la forme produite par predict_seasons."""
    rows = []
    with path.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            row = {"match_id": r["match_id"], "saison": r["saison"], "issue": r["issue"]}
            for name in {k.rsplit("_", 1)[0] for k in r if k.endswith("_H")}:
                row[name] = {o: float(r[f"{name}_{o}"]) for o in OUTCOMES} if r[f"{name}_H"] else None
            rows.append(row)
    return rows


def write_predictions(rows: list[dict], path: Path) -> None:
    names = model_names(rows)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["match_id", "saison", "issue"] + [f"{m}_{o}" for m in names for o in OUTCOMES])
        for r in rows:
            w.writerow([r["match_id"], r["saison"], r["issue"]]
                       + [f"{r[m][o]:.4f}" if r[m] else "" for m in names for o in OUTCOMES])
