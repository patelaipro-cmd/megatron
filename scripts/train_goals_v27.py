#!/usr/bin/env python3
"""GOALS V2.7: match-date-safe lagged Understat xG benchmark for O2.5.

The source was downloaded retrospectively in 2026. Predictions use only xG
statistics of matches on STRICTLY earlier dates, but as-of source versions are
not proven. Source odds are NEVER passed to the independent model.
"""

import argparse
import json
import re
import runpy
import unicodedata
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

parser = argparse.ArgumentParser()
parser.add_argument(
    "--understat-dir", type=Path,
    default=ROOT / "external-data/externe/understat/historique",
    help="Directory of historical Understat match team CSVs, read only",
)
args = parser.parse_args()
files = sorted(args.understat_dir.glob("matchs_equipes_*.csv"))
if len(files) < 10:
    raise RuntimeError("Understat history unavailable: 10+ source seasons expected")


def normalized(text):
    ascii_text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", ascii_text)


league_names = {
    "ENG-Premier League": "E0", "ESP-La Liga": "SP1", "FRA-Ligue 1": "F1",
    "GER-Bundesliga": "D1", "ITA-Serie A": "I1",
}
aliases = {
    "E0": {
        "mancity": "Manchester City", "manunited": "Manchester United", "newcastle": "Newcastle United",
        "nottmforest": "Nottingham Forest", "qpr": "Queens Park Rangers",
        "westbrom": "West Bromwich Albion", "wolves": "Wolverhampton Wanderers",
    },
    "SP1": {
        "athbilbao": "Athletic Club", "athmadrid": "Atletico Madrid", "betis": "Real Betis",
        "celta": "Celta Vigo", "espanol": "Espanyol", "huesca": "SD Huesca",
        "lacoruna": "Deportivo La Coruna", "oviedo": "Real Oviedo", "santander": "Racing Santander",
        "sociedad": "Real Sociedad", "spgijon": "Sporting Gijon",
        "valladolid": "Real Valladolid", "vallecano": "Rayo Vallecano",
    },
    "F1": {
        "ajacciogfco": "GFC Ajaccio", "bastia": "SC Bastia", "clermont": "Clermont Foot",
        "parissg": "Paris Saint Germain", "stetienne": "Saint-Etienne",
    },
    "D1": {
        "bielefeld": "Arminia Bielefeld", "dortmund": "Borussia Dortmund",
        "einfrankfurt": "Eintracht Frankfurt", "fckoln": "FC Cologne",
        "fortunadusseldorf": "Fortuna Duesseldorf", "greutherfurth": "Greuther Fuerth",
        "hamburg": "Hamburger SV", "hannover": "Hannover 96",
        "heidenheim": "FC Heidenheim", "hertha": "Hertha Berlin",
        "leverkusen": "Bayer Leverkusen", "mgladbach": "Borussia M.Gladbach",
        "mainz": "Mainz 05", "nurnberg": "Nuernberg",
        "rbleipzig": "RasenBallsport Leipzig", "stpauli": "St. Pauli",
        "stuttgart": "VfB Stuttgart",
    },
    "I1": {"milan": "AC Milan", "spal": "SPAL 2013"},
}
alias_norm = {
    division: {k: normalized(v) for k, v in mapping.items()}
    for division, mapping in aliases.items()
}


def team_key(division, name):
    plain = normalized(name)
    return alias_norm.get(division, {}).get(plain, plain)


raw = pd.concat(
    [pd.read_csv(path, usecols=[
        "league", "date", "home_team", "away_team", "home_xg", "away_xg",
        "home_np_xg", "away_np_xg", "home_ppda", "away_ppda",
        "home_deep_completions", "away_deep_completions", "collecte_le",
    ]) for path in files], ignore_index=True,
)
raw["Division"] = raw.league.map(league_names)
if raw.Division.isna().any():
    raise RuntimeError("Unknown Understat league")
raw["date"] = pd.to_datetime(raw.date, errors="coerce").dt.normalize()
raw = raw.dropna(subset=["date", "home_xg", "away_xg"])
for field in (
    "home_xg", "away_xg", "home_np_xg", "away_np_xg", "home_ppda", "away_ppda",
    "home_deep_completions", "away_deep_completions",
):
    raw[field] = pd.to_numeric(raw[field], errors="coerce")

all_team_rows = []
for home in (True, False):
    side = "home" if home else "away"
    opp = "away" if home else "home"
    all_team_rows.append(pd.DataFrame({
        "Division": raw.Division, "date": raw.date,
        "team": raw[side + "_team"].map(normalized),
        "xgf": raw[side + "_xg"], "xga": raw[opp + "_xg"],
        "npxgf": raw[side + "_np_xg"], "ppda": raw[side + "_ppda"],
        "deep": raw[side + "_deep_completions"],
    }))
daily = (
    pd.concat(all_team_rows, ignore_index=True)
    .groupby(["Division", "team", "date"], as_index=False)[["xgf", "xga", "npxgf", "ppda", "deep"]]
    .mean().sort_values(["date", "Division", "team"], kind="stable")
)
group = daily.groupby(["Division", "team"], sort=False)
daily["prior_xg_games"] = group.cumcount() + 1
historic_fields = ["prior_xg_games"]
for field in ("xgf", "xga", "npxgf", "ppda", "deep"):
    for window in (5, 10):
        col = f"{field}_{window}"
        # Inclusive rolling on the source history, but the AS-OF join below is
        # strict-left of the fixture date, excluding this match and same-day games.
        daily[col] = group[field].transform(lambda s: s.rolling(window, min_periods=2).mean())
        historic_fields.append(col)

env = runpy.run_path(str(ROOT / "scripts/train_goals_v24.py"))
df = env["df"].copy()
original = list(env["original"])
extra = list(env["extra"])
new_features = []
for side, col in (("home", "HomeTeam"), ("away", "AwayTeam")):
    fixture = df[["game_id", "date", "Division", col]].copy()
    fixture["team"] = [team_key(div, name) for div, name in zip(fixture.Division, fixture[col])]
    fixture = fixture[["game_id", "date", "Division", "team"]].sort_values("date", kind="stable")
    lookup = daily[["date", "Division", "team"] + historic_fields].rename(columns={"date": "last_xg_day"})
    # Sorted as-of key is essential for pandas; by groups are matched independently.
    lookup = lookup.sort_values("last_xg_day", kind="stable")
    joined = pd.merge_asof(
        fixture, lookup, left_on="date", right_on="last_xg_day", by=["Division", "team"],
        direction="backward", allow_exact_matches=False,
    )
    if len(joined) != len(df) or joined.game_id.duplicated().any():
        raise AssertionError("Each fixture must preserve exactly one pre-match snapshot")
    joined[side + "_days_since_xg"] = (joined.date - joined.last_xg_day).dt.days
    if (joined[side + "_days_since_xg"].dropna() <= 0).any():
        raise AssertionError("xG snapshot may not include same-day or future outcomes")
    names = {field: side + "_xg_" + field for field in historic_fields}
    joined = joined.rename(columns=names).drop(columns=["Division", "date", "team", "last_xg_day"])
    df = df.merge(joined, on="game_id", how="left", validate="one_to_one", sort=False)
    new_features += list(names.values()) + [side + "_days_since_xg"]

available = df.Over25.notna() & df.Under25.notna()
target = (df.FTHome + df.FTAway > 2.5).astype(int)
market = (1 / df.Over25) / (1 / df.Over25 + 1 / df.Under25)
reference = json.loads((OUT / "report_v24.json").read_text(encoding="utf-8"))


def predictions(kind, train, test):
    numeric = original + extra + new_features
    if kind == "xg_linear":
        transformer = ColumnTransformer([
            ("numeric", Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=True)),
                                   ("scale", StandardScaler())]), numeric),
            ("division", OneHotEncoder(handle_unknown="ignore"), ["Division"]),
        ])
        classifier = LogisticRegression(C=0.6, max_iter=400)
    else:
        transformer = ColumnTransformer([
            ("numeric", "passthrough", numeric),
            ("division", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["Division"]),
        ], sparse_threshold=0)
        classifier = HistGradientBoostingClassifier(
            max_iter=160, learning_rate=0.04, max_leaf_nodes=15, min_samples_leaf=80,
            l2_regularization=20.0, early_stopping=False, random_state=20261115,
        )
    model = Pipeline([("features", transformer), ("classifier", classifier)])
    x = df[numeric + ["Division"]]
    model.fit(x.loc[train], target.loc[train])
    return np.clip(model.predict_proba(x.loc[test])[:, 1], .001, .999)


def scores(y, p):
    return {"logloss": float(log_loss(y, p, labels=[0, 1])), "brier": float(brier_score_loss(y, p))}


folds = [("2017-01-01", "2019-01-01"), ("2020-01-01", "2022-01-01"), ("2023-01-01", "2025-01-01")]
report = {
    "status": "completed", "external_seasons": len(files), "external_matches": len(raw),
    "source_collected_le": sorted(raw.collecte_le.dropna().unique().tolist())[-1],
    "new_features": new_features,
    "method": "Understat team rolling xG observed strictly before fixture calendar date; bookmaker not an input",
    "folds": {},
    "limitations": "Historical Understat xG were downloaded in 2026 and could have changed since each historic match. Backtest is not a prospectively timestamped xG feed; never claim profit or V1/production readiness.",
}
for start, end in folds:
    train = (df.date < pd.Timestamp(start)) & available
    test = (df.date >= pd.Timestamp(start)) & (df.date < pd.Timestamp(end)) & available
    y = target.loc[test].to_numpy()
    price = np.clip(market.loc[test].to_numpy(), 0.001, 0.999)
    fold = {
        "train": int(train.sum()), "test": int(test.sum()),
        "both_teams_xg_available": float(df.loc[test, ["home_xg_xgf_5", "away_xg_xgf_5"]].notna().all(axis=1).mean()),
        "v24_reference": reference["folds"][start]["v24_candidate"],
        "bookmaker": scores(y, price),
    }
    for kind in ("xg_linear", "xg_nonlinear"):
        prob = predictions(kind, train, test)
        fold[kind] = scores(y, prob)
        fold[kind + "_minus_market"] = float(fold[kind]["logloss"] - fold["bookmaker"]["logloss"])
        fold[kind + "_minus_v24"] = float(fold[kind]["logloss"] - fold["v24_reference"]["logloss"])
    report["folds"][start] = fold
report["beats_v24_all_folds"] = {
    kind: all(report["folds"][start][kind]["logloss"] < report["folds"][start]["v24_reference"]["logloss"] for start, _ in folds)
    for kind in ("xg_linear", "xg_nonlinear")
}
report["beats_bookmaker_all_folds"] = {
    kind: all(report["folds"][start][kind]["logloss"] < report["folds"][start]["bookmaker"]["logloss"] for start, _ in folds)
    for kind in ("xg_linear", "xg_nonlinear")
}
report["decision"] = "EXPERIMENTAL; NO_AUTOMATIC_PROMOTION"
(OUT / "report_v27.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
