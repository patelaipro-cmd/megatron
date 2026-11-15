#!/usr/bin/env python3
"""GOALS V2.2: leakage-safe same-day history, three forward tests, O2.5 market comparison."""
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
# Reuse input validation and match joins from V2.1, then REPLACE all team-history features.
env=runpy.run_path(str(ROOT/"scripts/train_goals_v21.py"))
df=env["df"].copy()
KEY=env["KEY"]
# Team/date aggregates prevent any result from the same date entering a pre-match feature.
h=pd.DataFrame({"game_id":df.game_id,"date":df.date,"team":df.HomeTeam,"gf":df.FTHome,"ga":df.FTAway})
a=pd.DataFrame({"game_id":df.game_id,"date":df.date,"team":df.AwayTeam,"gf":df.FTAway,"ga":df.FTHome})
teams=pd.concat([h,a],ignore_index=True)
teams["points"]=np.select([teams.gf>teams.ga,teams.gf==teams.ga],[3,1],default=0)
teams["total"]=teams.gf+teams.ga
daily=teams.groupby(["team","date"],as_index=False).agg(
    games=("game_id","size"),gf=("gf","sum"),ga=("ga","sum"),
    points=("points","sum"),total=("total","sum")).sort_values(["team","date"])
g=daily.groupby("team",sort=False)
daily["prior_games"]=g.games.cumsum()-daily.games
for field in ("gf","ga","points","total"):
    for window in (5,10):
        # Previous DAYS (not matches); same-day events are excluded by shift(1).
        daily[f"{field}_{window}"]=g[field].transform(lambda s:s.shift(1).rolling(window,min_periods=2).mean())
features=["prior_games"]+[f"{field}_{w}" for field in ("gf","ga","points","total") for w in (5,10)]
lookup=daily[["team","date"]+features]
for side,team in (("home","HomeTeam"),("away","AwayTeam")):
    old=[c for c in df if c.startswith(side+"_")]
    df=df.drop(columns=old)
    temp=lookup.rename(columns={"team":team,**{c:side+"_"+c for c in features}})
    df=df.merge(temp,on=[team,"date"],how="left",validate="many_to_one")
num=["home_"+c for c in features]+["away_"+c for c in features]
X=df[num+["Division"]]
ft=df.FTHome+df.FTAway
ht=df.HTHome+df.HTAway
valid_ht=(df.HTHome>=0)&(df.HTAway>=0)&(df.HTHome<=df.FTHome)&(df.HTAway<=df.FTAway)
targets={f"FT_over_{t}":(ft>t,pd.Series(True,index=df.index)) for t in (1.5,2.5,3.5)}
for t in (.5,1.5):
    targets[f"MT1_over_{t}"]=(ht>t,valid_ht)
    targets[f"MT2_over_{t}"]=((ft-ht)>t,valid_ht)
# Fixed calendar folds, never random. Training expands with each later period.
folds=[("2017-01-01","2019-01-01"),("2020-01-01","2022-01-01"),("2023-01-01","2025-01-01")]
results={}
for start,end in folds:
    tr=df.date<pd.Timestamp(start)
    te=(df.date>=pd.Timestamp(start))&(df.date<pd.Timestamp(end))
    fold={}
    for name,(y,eligible) in targets.items():
        train=tr&eligible;test=te&eligible
        if train.sum()<1000 or test.sum()<300:
            fold[name]={"status":"insufficient_data","train":int(train.sum()),"test":int(test.sum())}
            continue
        yt=y.loc[train].astype(int);yv=y.loc[test].astype(int)
        prior=float(np.clip(yt.mean(),.001,.999))
        transform=ColumnTransformer([
            ("num",Pipeline([("impute",SimpleImputer(strategy="median",add_indicator=True)),("scale",StandardScaler())]),num),
            ("division",OneHotEncoder(handle_unknown="ignore"),["Division"])])
        model=Pipeline([("transform",transform),("logistic",LogisticRegression(max_iter=300))])
        model.fit(X.loc[train],yt)
        pred=np.clip(model.predict_proba(X.loc[test])[:,1],.001,.999)
        base=np.full(len(yv),prior)
        fold[name]={"train":int(train.sum()),"test":int(test.sum()),
          "baseline_logloss":float(log_loss(yv,base,labels=[0,1])),
          "model_logloss":float(log_loss(yv,pred,labels=[0,1])),
          "model_brier":float(brier_score_loss(yv,pred)),
          "observed":float(yv.mean()),"predicted":float(pred.mean()),
          "calibration_bins":[]}
        # Reliability bins on held-out predictions.
        for lo,hi in ((0,.2),(.2,.4),(.4,.6),(.6,.8),(.8,1.01)):
            mask=(pred>=lo)&(pred<hi)
            if mask.sum():
                fold[name]["calibration_bins"].append({"range":[lo,hi],"n":int(mask.sum()),
                    "predicted":float(pred[mask].mean()),"observed":float(yv.to_numpy()[mask].mean())})
    results[start+"_"+end]=fold
report={"status":"completed","method":"3 expanding date-window validations; team features exclude all same-date results",
"rows":len(df),"folds":results,"market_comparison":"not performed: requires verified timestamped pre-match O/U odds alignment",
"caveat":"No production approval; baseline comparisons only, V1 unchanged"}
(OUT/"report_v22.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
