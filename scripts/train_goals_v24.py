#!/usr/bin/env python3
"""GOALS V2.4: lagged venue/shot features vs V2.3 and a matched O2.5 market.

Experimental only. No betting execution, production model change, or V1 import.
The V2.3 baseline is refitted on precisely the same samples as the candidate.
"""

import json
import runpy
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "goals_v2"
OUT.mkdir(parents=True, exist_ok=True)

# V2.2 builds all-match form without using any results from the match date.
env = runpy.run_path(str(ROOT / "scripts/train_goals_v22.py"))
df = env["df"].copy()
original = list(env["num"])
key = ["Division", "MatchDate", "HomeTeam", "AwayTeam"]


def add_venue_history(frame, venue):
    """One row per league/team/day; shift before rolling so today stays unseen."""
    home = venue == "home"
    team_col = "HomeTeam" if home else "AwayTeam"
    for_col = "Home" if home else "Away"
    against_col = "Away" if home else "Home"
    game = pd.DataFrame(
        {
            "Division": frame.Division,
            "date": frame.date,
            team_col: frame[team_col],
            "scored": pd.to_numeric(frame["FT" + for_col], errors="coerce"),
            "conceded": pd.to_numeric(frame["FT" + against_col], errors="coerce"),
            "shots_for": pd.to_numeric(frame[for_col + "Shots"], errors="coerce"),
            "shots_against": pd.to_numeric(frame[against_col + "Shots"], errors="coerce"),
            "target_for": pd.to_numeric(frame[for_col + "Target"], errors="coerce"),
            "target_against": pd.to_numeric(frame[against_col + "Target"], errors="coerce"),
        }
    )
    fields = ["scored", "conceded", "shots_for", "shots_against", "target_for", "target_against"]
    # Any rare double fixture on one date contributes only one day of history.
    daily = (
        game.groupby(["Division", team_col, "date"], as_index=False)[fields]
        .mean()
        .sort_values(["Division", team_col, "date"], kind="stable")
    )
    group = daily.groupby(["Division", team_col], sort=False)
    extra = []
    prior = venue + "_venue_games_prior"
    daily[prior] = group.cumcount()
    extra.append(prior)
    for field in fields:
        for window in (5, 10):
            name = f"{venue}_venue_{field}_{window}"
            daily[name] = group[field].transform(
                lambda s: s.shift(1).rolling(window, min_periods=2).mean()
            )
            extra.append(name)
    new = daily[["Division", team_col, "date"] + extra]
    joined = frame.merge(new, on=["Division", team_col, "date"], how="left", validate="many_to_one", sort=False)
    if len(joined) != len(frame):
        raise AssertionError("Venue history must preserve the original match count")
    return joined, extra


df, home_extra = add_venue_history(df, "home")
df, away_extra = add_venue_history(df, "away")
extra = home_extra + away_extra

# Previous match day in the same division; not the previous HOME or AWAY day.
appearances = pd.concat(
    [
        df[["Division", "date", "HomeTeam"]].rename(columns={"HomeTeam": "team"}),
        df[["Division", "date", "AwayTeam"]].rename(columns={"AwayTeam": "team"}),
    ],
    ignore_index=True,
).drop_duplicates(["Division", "team", "date"])
appearances = appearances.sort_values(["Division", "team", "date"], kind="stable")
appearances["previous_date"] = appearances.groupby(["Division", "team"], sort=False)["date"].shift(1)
appearances["rest_days"] = (appearances.date - appearances.previous_date).dt.days
for venue, team_col in (("home", "HomeTeam"), ("away", "AwayTeam")):
    col = venue + "_rest_days"
    lookup = appearances[["Division", "team", "date", "rest_days"]].rename(
        columns={"team": team_col, "rest_days": col}
    )
    df = df.merge(lookup, on=["Division", team_col, "date"], how="left", validate="many_to_one", sort=False)
    extra.append(col)

# The odds are ONLY an external benchmark, never a training feature.
odds = pd.read_csv(ROOT / "data" / "cotes_buts_2000-2026.csv", low_memory=False)
odds = odds[key + ["Over25", "Under25"]].drop_duplicates(key)
for col in ("Over25", "Under25"):
    odds[col] = pd.to_numeric(odds[col], errors="coerce")
odds = odds[(odds.Over25 > 1) & (odds.Under25 > 1)]
df = df.merge(odds, on=key, how="left", validate="one_to_one", sort=False)
available = df.Over25.notna() & df.Under25.notna()
market_probability = (1 / df.Over25) / (1 / df.Over25 + 1 / df.Under25)
target = (df.FTHome + df.FTAway > 2.5).astype(int)


def fit_predict(columns, train, test):
    transformer = ColumnTransformer(
        [
            (
                "numeric",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
                        ("scale", StandardScaler()),
                    ]
                ),
                columns,
            ),
            ("division", OneHotEncoder(handle_unknown="ignore"), ["Division"]),
        ]
    )
    model = Pipeline(
        [("features", transformer), ("logistic", LogisticRegression(max_iter=300))]
    )
    x = df[columns + ["Division"]]
    model.fit(x.loc[train], target.loc[train])
    return np.clip(model.predict_proba(x.loc[test])[:, 1], 0.001, 0.999)


def metrics(actual, probabilities):
    return {
        "logloss": float(log_loss(actual, probabilities, labels=[0, 1])),
        "brier": float(brier_score_loss(actual, probabilities)),
    }


def paired_date_bootstrap(actual, left, right, dates, seed=20261115):
    """95% interval for mean log-loss(left)-log-loss(right); resample days."""
    a = np.asarray(actual, dtype=int)
    left_loss = -np.where(a == 1, np.log(left), np.log1p(-left))
    right_loss = -np.where(a == 1, np.log(right), np.log1p(-right))
    daily = (
        pd.DataFrame({"date": np.asarray(dates), "delta": left_loss - right_loss})
        .groupby("date")
        .delta.agg(["sum", "size"])
    )
    random = np.random.default_rng(seed)
    sampled = random.integers(0, len(daily), size=(400, len(daily)))
    changes = daily["sum"].to_numpy()[sampled].sum(axis=1) / daily["size"].to_numpy()[sampled].sum(axis=1)
    lo, hi = np.quantile(changes, [0.025, 0.975])
    return {"lower_95": float(lo), "upper_95": float(hi), "resampling_unit": "calendar_date", "n_dates": int(len(daily))}


folds = [("2017-01-01", "2019-01-01"), ("2020-01-01", "2022-01-01"), ("2023-01-01", "2025-01-01")]
report = {
    "status": "completed",
    "approach": "Original V2.3 logistic versus venue-specific pre-match goals, past shots/on-target and rest days",
    "features_added": extra,
    "rows_all": int(len(df)),
    "rows_with_odds": int(available.sum()),
    "folds": {},
    "limitations": "Retrospective fixed-date folds, odds timing unverified, results known during research; no betting/ROI/production claim; V1 unchanged.",
}
for start, end in folds:
    train = (df.date < pd.Timestamp(start)) & available
    test = (df.date >= pd.Timestamp(start)) & (df.date < pd.Timestamp(end)) & available
    if train.sum() < 1000 or test.sum() < 300:
        report["folds"][start] = {"status": "insufficient_data", "train": int(train.sum()), "test": int(test.sum())}
        continue
    actual = target.loc[test].to_numpy()
    baseline = fit_predict(original, train, test)
    candidate = fit_predict(original + extra, train, test)
    market = np.clip(market_probability.loc[test].to_numpy(), 0.001, 0.999)
    # Uniformly defined retrospective high-scoring screen; not a betting signal.
    high = candidate >= np.quantile(candidate, 0.90)
    fold = {
        "train": int(train.sum()),
        "test": int(test.sum()),
        "v23_reproduced": metrics(actual, baseline),
        "v24_candidate": metrics(actual, candidate),
        "bet365_normalized": metrics(actual, market),
        "v24_minus_v23_logloss": float(metrics(actual, candidate)["logloss"] - metrics(actual, baseline)["logloss"]),
        "v24_minus_market_logloss": float(metrics(actual, candidate)["logloss"] - metrics(actual, market)["logloss"]),
        "v24_minus_v23_ci95": paired_date_bootstrap(actual, candidate, baseline, df.loc[test, "date"]),
        "v24_minus_market_ci95": paired_date_bootstrap(actual, candidate, market, df.loc[test, "date"]),
        "shot_feature_coverage": float(df.loc[test, ["home_venue_target_for_5", "away_venue_target_for_5"]].notna().all(axis=1).mean()),
        "high_goal_screen": {
            "n": int(high.sum()),
            "mean_predicted": float(candidate[high].mean()),
            "over25_observed": float(actual[high].mean()),
            "all_matches_observed": float(actual.mean()),
        },
    }
    report["folds"][start] = fold

(OUT / "report_v24.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
