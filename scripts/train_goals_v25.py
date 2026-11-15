#!/usr/bin/env python3
"""GOALS V2.5: experimental pre-match MT1-vs-MT2 goal balance.

Predicts three mutually exclusive classes: more first-half goals, a tie, or more
second-half goals. Evaluates on chronological tests, never on shuffled fixtures.
Nothing is deployed into DOMINATION V1 or the live prediction registry.
"""

import json
import runpy
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/goals_v2"
OUT.mkdir(parents=True, exist_ok=True)

# V2.4 provides the already date-lagged pre-match model features.
env = runpy.run_path(str(ROOT / "scripts/train_goals_v24.py"))
df = env["df"].copy()
base_features = list(env["original"])
venue_features = list(env["extra"])
half1 = df.HTHome + df.HTAway
half2 = df.FTHome + df.FTAway - half1
valid = (
    df.HTHome.notna()
    & df.HTAway.notna()
    & (df.HTHome >= 0)
    & (df.HTAway >= 0)
    & (df.HTHome <= df.FTHome)
    & (df.HTAway <= df.FTAway)
)

# Historical half-time features are calculated only from previously played
# matches with observed half-time scores. Today's result enters *after* today.
observed = df.loc[valid].copy()
home = pd.DataFrame(
    {
        "Division": observed.Division,
        "team": observed.HomeTeam,
        "date": observed.date,
        "first_for": observed.HTHome,
        "first_against": observed.HTAway,
        "second_for": observed.FTHome - observed.HTHome,
        "second_against": observed.FTAway - observed.HTAway,
    }
)
away = pd.DataFrame(
    {
        "Division": observed.Division,
        "team": observed.AwayTeam,
        "date": observed.date,
        "first_for": observed.HTAway,
        "first_against": observed.HTHome,
        "second_for": observed.FTAway - observed.HTAway,
        "second_against": observed.FTHome - observed.HTHome,
    }
)
fields = ("first_for", "first_against", "second_for", "second_against")
daily = (
    pd.concat([home, away], ignore_index=True)
    .groupby(["Division", "team", "date"], as_index=False)[list(fields)]
    .mean()
    .sort_values(["Division", "team", "date"], kind="stable")
)
group = daily.groupby(["Division", "team"], sort=False)
half_features = []
for field in fields:
    for window in (5, 10):
        col = field + "_" + str(window)
        daily[col] = group[field].transform(lambda s: s.shift(1).rolling(window, min_periods=2).mean())
        half_features.append(col)
for side, team in (("home", "HomeTeam"), ("away", "AwayTeam")):
    names = {c: side + "_historic_" + c for c in half_features}
    lookup = daily[["Division", "date", "team"] + half_features].rename(
        columns={"team": team, **names}
    )
    previous = len(df)
    df = df.merge(lookup, on=["Division", "date", team], how="left", validate="many_to_one", sort=False)
    if len(df) != previous:
        raise AssertionError("Half-time features must not duplicate matches")

halftime_features = [side + "_historic_" + c for side in ("home", "away") for c in half_features]
class_names = ["MT1_superieure", "egalite", "MT2_superieure"]
y = np.select([half1 > half2, half1 == half2], [0, 1], default=2).astype(int)


def probabilities(features, train, test):
    transform = ColumnTransformer(
        [
            ("numeric", Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=True)), ("scale", StandardScaler())]), features),
            ("division", OneHotEncoder(handle_unknown="ignore"), ["Division"]),
        ]
    )
    model = Pipeline([("features", transform), ("classifier", LogisticRegression(max_iter=350))])
    x = df[features + ["Division"]]
    model.fit(x.loc[train], y[train])
    if list(model.named_steps["classifier"].classes_) != [0, 1, 2]:
        raise RuntimeError("Missing half-balance class from training data")
    return np.clip(model.predict_proba(x.loc[test]), 0.001, 0.999)


def evaluate(actual, prediction):
    indicator = np.eye(3)[actual]
    return {
        "logloss": float(log_loss(actual, prediction, labels=[0, 1, 2])),
        "brier_sum_three": float(np.mean(np.sum((prediction - indicator) ** 2, axis=1))),
        "accuracy_top_class": float(np.mean(prediction.argmax(axis=1) == actual)),
        "predicted_rates": {name: float(prediction[:, index].mean()) for index, name in enumerate(class_names)},
    }


folds = [("2017-01-01", "2019-01-01"), ("2020-01-01", "2022-01-01"), ("2023-01-01", "2025-01-01")]
report = {
    "status": "completed",
    "market": "No valid pre-match MT1-versus-MT2 bookmaker comparison available",
    "goal": "Classify which half has more goals, or equal totals",
    "class_names": class_names,
    "history_features": halftime_features,
    "matches_with_valid_halftime": int(valid.sum()),
    "folds": {},
    "limitations": "Retrospective and limited to observed half-time results; no market odds, no guaranteed goals or production selection, V1 unchanged.",
}
for start, end in folds:
    train = (df.date < pd.Timestamp(start)) & valid
    test = (df.date >= pd.Timestamp(start)) & (df.date < pd.Timestamp(end)) & valid
    if train.sum() < 1000 or test.sum() < 300:
        report["folds"][start] = {"status": "insufficient_data", "train": int(train.sum()), "test": int(test.sum())}
        continue
    actual = y[test.to_numpy()]
    prior = np.bincount(y[train.to_numpy()], minlength=3) / train.sum()
    base = np.tile(prior, (int(test.sum()), 1))
    old = probabilities(base_features, train, test)
    expanded = probabilities(base_features + venue_features + halftime_features, train, test)
    report["folds"][start] = {
        "train": int(train.sum()),
        "test": int(test.sum()),
        "prior": evaluate(actual, base),
        "v22_base": evaluate(actual, old),
        "v25_candidate": evaluate(actual, expanded),
        "v25_minus_v22_logloss": float(log_loss(actual, expanded, labels=[0, 1, 2]) - log_loss(actual, old, labels=[0, 1, 2])),
        "observed_rates": {name: float(np.mean(actual == index)) for index, name in enumerate(class_names)},
        "high_confidence_60pct": {
            name: {
                "n": int((expanded[:, index] >= 0.60).sum()),
                "observed": (
                    float(np.mean(actual[expanded[:, index] >= 0.60] == index))
                    if (expanded[:, index] >= 0.60).any() else None
                ),
            }
            for index, name in enumerate(class_names)
        },
        "historic_halves_coverage": float(df.loc[test, halftime_features].notna().all(axis=1).mean()),
    }

comparable = [v for v in report["folds"].values() if "v25_candidate" in v]
report["candidate_beats_both_references_in_all_folds"] = bool(comparable) and all(
    v["v25_candidate"]["logloss"] < min(v["prior"]["logloss"], v["v22_base"]["logloss"])
    for v in comparable
)
report["decision"] = "KEEP_EXPERIMENTAL_ONLY; NO_MT1_MT2_SIGNAL"

(OUT / "report_v25.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
