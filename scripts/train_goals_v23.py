#!/usr/bin/env python3
"""GOALS V2.3: matched historical Bet365 O/U2.5 comparison (quote timing unverified)."""
import json,runpy
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss,brier_score_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder,StandardScaler

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/goals_v2"
# V2.2 computes same-day-safe pre-match form features.
env=runpy.run_path(str(ROOT/"scripts/train_goals_v22.py"))
df=env["df"].copy()
num=env["num"]
KEY=["Division","MatchDate","HomeTeam","AwayTeam"]
odds=pd.read_csv(ROOT/"data/cotes_buts_2000-2026.csv",low_memory=False)
odds=odds[KEY+["Over25","Under25"]].drop_duplicates(KEY)
for c in ("Over25","Under25"):odds[c]=pd.to_numeric(odds[c],errors="coerce")
odds=odds[(odds.Over25>1)&(odds.Under25>1)].copy()
df=df.merge(odds,on=KEY,how="left",validate="one_to_one")
available=df.Over25.notna()&df.Under25.notna()
df["market_raw"]=1/df.Over25
df["market_normalized"]=(1/df.Over25)/((1/df.Over25)+(1/df.Under25))
y=(df.FTHome+df.FTAway>2.5).astype(int)
folds=[("2017-01-01","2019-01-01"),("2020-01-01","2022-01-01"),("2023-01-01","2025-01-01")]
report={"status":"completed","market":"Bet365 historical O/U 2.5","rows_with_odds":int(available.sum()),
"odds_provenance":"Repository data/SOURCE.md; quote timestamp and whether opening/closing prices NOT verified",
"folds":{},"limitations":"Retrospective benchmark only; cannot assert tradable pre-match odds or profitable betting; no staking or V1 changes."}
for start,end in folds:
    tr=(df.date<pd.Timestamp(start))&available
    te=(df.date>=pd.Timestamp(start))&(df.date<pd.Timestamp(end))&available
    if tr.sum()<1000 or te.sum()<100:
        report["folds"][start]={"status":"insufficient_data","train":int(tr.sum()),"test":int(te.sum())}
        continue
    transformer=ColumnTransformer([
        ("num",Pipeline([("impute",SimpleImputer(strategy="median",add_indicator=True)),("scale",StandardScaler())]),num),
        ("division",OneHotEncoder(handle_unknown="ignore"),["Division"])])
    model=Pipeline([("features",transformer),("logistic",LogisticRegression(max_iter=300))])
    X=df[num+["Division"]]
    model.fit(X.loc[tr],y.loc[tr])
    pred=np.clip(model.predict_proba(X.loc[te])[:,1],.001,.999)
    market=np.clip(df.loc[te,"market_normalized"].to_numpy(),.001,.999)
    actual=y.loc[te].to_numpy()
    report["folds"][start]={"train":int(tr.sum()),"test":int(te.sum()),
      "model_logloss":float(log_loss(actual,pred,labels=[0,1])),
      "market_logloss":float(log_loss(actual,market,labels=[0,1])),
      "model_brier":float(brier_score_loss(actual,pred)),
      "market_brier":float(brier_score_loss(actual,market)),
      "model_mean":float(pred.mean()),"market_mean":float(market.mean()),
      "observed":float(actual.mean()),"model_beats_market":bool(log_loss(actual,pred,labels=[0,1])<log_loss(actual,market,labels=[0,1])),
      "calibration_bins":[]}
    for lo,hi in ((0,.2),(.2,.4),(.4,.6),(.6,.8),(.8,1.01)):
        mask=(pred>=lo)&(pred<hi)
        if mask.sum():
            report["folds"][start]["calibration_bins"].append({"range":[lo,hi],"n":int(mask.sum()),"predicted":float(pred[mask].mean()),"observed":float(actual[mask].mean())})
(OUT/"report_v23.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
