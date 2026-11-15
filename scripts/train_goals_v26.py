#!/usr/bin/env python3
"""GOALS V2.6: audit two failed experimental markets without changing V1.

O2.5: compare fixed-parameter nonlinear and shrunken-linear candidates against
the V2.4 logistic and normalized historical bookmaker quotes.
MT1/MT2: test a deliberately simple, shrunken league-frequency fallback.
All labels, rolling form and half-time histories originate in earlier V2 steps.
"""

import json
import runpy
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "goals_v2"
OUT.mkdir(parents=True, exist_ok=True)

env25 = runpy.run_path(str(ROOT / "scripts/train_goals_v25.py"))
env24 = env25["env"]
df = env25["df"]
original = list(env24["original"])
extra = list(env24["extra"])
fields = original + extra
previous_v24 = json.loads((OUT / "report_v24.json").read_text(encoding="utf-8"))
previous_v25 = json.loads((OUT / "report_v25.json").read_text(encoding="utf-8"))
o25 = (df.FTHome + df.FTAway > 2.5).astype(int)
odds_available = df.Over25.notna() & df.Under25.notna()
market_prob = (1 / df.Over25) / (1 / df.Over25 + 1 / df.Under25)


def candidate_predictions(kind, train, test):
    if kind == "nonlinear":
        # Native missing-value handling in the tree estimator; never use odds.
        transformer = ColumnTransformer(
            [
                ("num", "passthrough", fields),
                ("division", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["Division"]),
            ],
            sparse_threshold=0,
        )
        estimator = HistGradientBoostingClassifier(
            max_iter=160,
            learning_rate=0.04,
            max_leaf_nodes=15,
            min_samples_leaf=80,
            l2_regularization=20.0,
            early_stopping=False,
            random_state=20261115,
        )
    elif kind == "shrunken_logistic":
        transformer = ColumnTransformer(
            [
                ("num", Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=True)),
                                   ("scale", StandardScaler())]), fields),
                ("division", OneHotEncoder(handle_unknown="ignore"), ["Division"]),
            ]
        )
        estimator = LogisticRegression(max_iter=350, C=0.15)
    else:
        raise ValueError(kind)
    model = Pipeline([("features", transformer), ("model", estimator)])
    x = df[fields + ["Division"]]
    model.fit(x.loc[train], o25.loc[train])
    return np.clip(model.predict_proba(x.loc[test])[:, 1], 0.001, 0.999)


def scores(y, probabilities):
    return {
        "logloss": float(log_loss(y, probabilities, labels=[0, 1])),
        "brier": float(brier_score_loss(y, probabilities)),
    }


def three_way_scores(y, probabilities):
    return {
        "logloss": float(log_loss(y, probabilities, labels=[0, 1, 2])),
        "brier_sum_three": float(np.mean(np.sum((probabilities - np.eye(3)[y]) ** 2, axis=1))),
    }


half1 = df.HTHome + df.HTAway
half2 = df.FTHome + df.FTAway - half1
valid_halves = (
    df.HTHome.notna() & df.HTAway.notna() & (df.HTHome >= 0) & (df.HTAway >= 0)
    & (df.HTHome <= df.FTHome) & (df.HTAway <= df.FTAway)
)
half_target = np.select([half1 > half2, half1 == half2], [0, 1], default=2)

folds = [("2017-01-01", "2019-01-01"), ("2020-01-01", "2022-01-01"), ("2023-01-01", "2025-01-01")]
report = {
    "status": "completed",
    "goal": "Try independent O2.5 improvements and conservative MT1/MT2 fallback; do not force green",
    "predeclared_candidates": ["nonlinear", "shrunken_logistic", "division_shrinkage_200"],
    "folds": {},
    "restrictions": "Research-only; non-timestamped odds never model inputs; 3 historical windows already visible to researchers; V1 and production untouched.",
}
for start, end in folds:
    train = (df.date < pd.Timestamp(start)) & odds_available
    test = (df.date >= pd.Timestamp(start)) & (df.date < pd.Timestamp(end)) & odds_available
    y = o25.loc[test].to_numpy()
    market = np.clip(market_prob.loc[test].to_numpy(), 0.001, 0.999)
    old = previous_v24["folds"][start]["v24_candidate"]
    o25_fold = {
        "train": int(train.sum()), "test": int(test.sum()),
        "v24_reference": old,
        "bookmaker": scores(y, market),
    }
    for kind in ("nonlinear", "shrunken_logistic"):
        prob = candidate_predictions(kind, train, test)
        o25_fold[kind] = scores(y, prob)
        o25_fold[kind + "_minus_v24"] = float(o25_fold[kind]["logloss"] - old["logloss"])
        o25_fold[kind + "_minus_bookmaker"] = float(o25_fold[kind]["logloss"] - o25_fold["bookmaker"]["logloss"])

    half_train = (df.date < pd.Timestamp(start)) & valid_halves
    half_test = (df.date >= pd.Timestamp(start)) & (df.date < pd.Timestamp(end)) & valid_halves
    y_half = half_target[half_test.to_numpy()]
    train_y = half_target[half_train.to_numpy()]
    global_counts = np.bincount(train_y, minlength=3)
    global_prior = global_counts / global_counts.sum()
    counts = pd.crosstab(df.loc[half_train, "Division"], train_y).reindex(columns=[0, 1, 2], fill_value=0)
    counts = counts.reindex(df.loc[half_test, "Division"].to_numpy(), fill_value=0)
    proportions = (counts.to_numpy() + 200 * global_prior) / (counts.to_numpy().sum(axis=1, keepdims=True) + 200)
    half_old = previous_v25["folds"][start]
    report["folds"][start] = {
        "over25": o25_fold,
        "half_comparison": {
            "test": int(half_test.sum()),
            "global_prior": three_way_scores(y_half, np.tile(global_prior, (len(y_half), 1))),
            "division_shrinkage_200": three_way_scores(y_half, proportions),
            "v25_rejected": {k: half_old["v25_candidate"][k] for k in ("logloss", "brier_sum_three")},
            "above_60pct": int((proportions.max(axis=1) >= 0.60).sum()),
        },
    }

report["O25_candidates_beat_v24_in_all_folds"] = {
    kind: all(report["folds"][start]["over25"][kind]["logloss"] < report["folds"][start]["over25"]["v24_reference"]["logloss"] for start, _ in folds)
    for kind in ("nonlinear", "shrunken_logistic")
}
report["O25_candidates_beat_market_in_all_folds"] = {
    kind: all(report["folds"][start]["over25"][kind]["logloss"] < report["folds"][start]["over25"]["bookmaker"]["logloss"] for start, _ in folds)
    for kind in ("nonlinear", "shrunken_logistic")
}
report["halves_fallback_beats_global_prior_in_all_folds"] = all(
    report["folds"][start]["half_comparison"]["division_shrinkage_200"]["logloss"]
    < report["folds"][start]["half_comparison"]["global_prior"]["logloss"] for start, _ in folds
)
report["decision"] = "EXPERIMENT_ONLY; NO_AUTOMATIC_PROMOTION"
(OUT / "report_v26.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
