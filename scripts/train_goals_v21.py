#!/usr/bin/env python3
"""GOALS V2.1 isolated pre-match logistic model with chronological holdout."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, brier_score_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/goals_v2"
OUT.mkdir(parents=True,exist_ok=True)
KEY=["Division","MatchDate","HomeTeam","AwayTeam"]
files=["matches_top5_2000-2026.csv","matches_autres_2000-2026.csv"]
frames=[]
for name in files:
    f=pd.read_csv(ROOT/"data"/name,low_memory=False)
    required=KEY+["FTHome","FTAway"]
    if any(c not in f for c in required):raise RuntimeError("Missing columns in "+name)
    frames.append(f)
df=pd.concat(frames,ignore_index=True).drop_duplicates(KEY).copy()
df["date"]=pd.to_datetime(df.MatchDate,format="%Y-%m-%d",errors="coerce")
for c in ("FTHome","FTAway"):
    df[c]=pd.to_numeric(df[c],errors="coerce")
df=df.dropna(subset=["date","FTHome","FTAway"])
df=df[(df.FTHome>=0)&(df.FTAway>=0)].sort_values(["date","Division","HomeTeam","AwayTeam"],kind="stable").reset_index(drop=True)
df["game_id"]=np.arange(len(df))
# Each observation uses only earlier games of that same team.
home=pd.DataFrame({"game_id":df.game_id,"date":df.date,"team":df.HomeTeam,"division":df.Division,
                   "side":"home","gf":df.FTHome,"ga":df.FTAway})
away=pd.DataFrame({"game_id":df.game_id,"date":df.date,"team":df.AwayTeam,"division":df.Division,
                   "side":"away","gf":df.FTAway,"ga":df.FTHome})
teams=pd.concat([home,away],ignore_index=True).sort_values(["team","date","game_id"],kind="stable")
teams["points"]=np.select([teams.gf>teams.ga,teams.gf==teams.ga],[3,1],default=0)
teams["total"]=teams.gf+teams.ga
g=teams.groupby("team",sort=False)
teams["prior_games"]=g.cumcount()
for field in ("gf","ga","points","total"):
    for window in (5,10):
        teams[f"{field}_{window}"]=g[field].transform(lambda s:s.shift(1).rolling(window,min_periods=2).mean())
feature_cols=["prior_games"]+[f"{field}_{window}" for field in ("gf","ga","points","total") for window in (5,10)]
h=teams[teams.side=="home"][["game_id"]+feature_cols].rename(columns={c:"home_"+c for c in feature_cols})
a=teams[teams.side=="away"][["game_id"]+feature_cols].rename(columns={c:"away_"+c for c in feature_cols})
df=df.merge(h,on="game_id",validate="one_to_one").merge(a,on="game_id",validate="one_to_one")
# Half-time data is joined by actual match identity, never by row number.
details=pd.read_csv(ROOT/"data/details_2000-2026.csv",low_memory=False)
details=details[KEY+["HTHome","HTAway"]].drop_duplicates(KEY)
df=df.merge(details,on=KEY,how="left",validate="one_to_one")
for c in ("HTHome","HTAway"):df[c]=pd.to_numeric(df[c],errors="coerce")
valid_ht=(df.HTHome>=0)&(df.HTAway>=0)&(df.HTHome<=df.FTHome)&(df.HTAway<=df.FTAway)
cut=df.date.iloc[int(len(df)*.7)]
train=df.date<cut
test=~train
numeric=[c for c in df.columns if c.startswith(("home_","away_")) and c in list(h.columns)+list(a.columns)]
transform=ColumnTransformer([
    ("num",Pipeline([("impute",SimpleImputer(strategy="median",add_indicator=True)),("scale",StandardScaler())]),numeric),
    ("league",OneHotEncoder(handle_unknown="ignore"),["Division"])
])
X=df[numeric+["Division"]]
results={}
def evaluate(name,y,eligible):
    tr=train&eligible
    te=test&eligible
    if tr.sum()<1000 or te.sum()<1000:
        results[name]={"status":"insufficient_data","train":int(tr.sum()),"test":int(te.sum())}
        return
    ytr=y.loc[tr].astype(int)
    yte=y.loc[te].astype(int)
    prior=float(np.clip(ytr.mean(),.001,.999))
    model=Pipeline([("features",transform),("classifier",LogisticRegression(max_iter=300,solver="lbfgs"))])
    model.fit(X.loc[tr],ytr)
    prob=np.clip(model.predict_proba(X.loc[te])[:,1],.001,.999)
    base=np.full(len(yte),prior)
    results[name]={"train":int(tr.sum()),"test":int(te.sum()),
      "baseline_logloss":float(log_loss(yte,base,labels=[0,1])),
      "model_logloss":float(log_loss(yte,prob,labels=[0,1])),
      "baseline_brier":float(brier_score_loss(yte,base)),
      "model_brier":float(brier_score_loss(yte,prob)),
      "observed_rate":float(yte.mean()),"predicted_rate":float(prob.mean())}
ft=df.FTHome+df.FTAway
for t in (1.5,2.5,3.5):
    evaluate(f"FT_over_{t}",ft>t,pd.Series(True,index=df.index))
ht=df.HTHome+df.HTAway
for t in (.5,1.5):
    evaluate(f"MT1_over_{t}",ht>t,valid_ht)
    evaluate(f"MT2_over_{t}",(ft-ht)>t,valid_ht)
report={"status":"completed","method":"Logistic regression, lagged 5/10-game team form and division, date-separated chronological 70/30 holdout",
"rows":len(df),"train":int(train.sum()),"test":int(test.sum()),"cut_date":str(cut.date()),
"features":numeric+["Division"],"results":results,
"limitations":"Single holdout; no market-odds comparison; same-day team games may create ordering ambiguity; V1 untouched. No production approval."}
(OUT/"report_v21.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
