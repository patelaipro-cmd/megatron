#!/usr/bin/env python3
"""GOALS V2: historical chronological baseline, isolated from DOMINATION V1."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts"/"goals_v2"
OUT.mkdir(parents=True,exist_ok=True)
KEY=["Division","MatchDate","HomeTeam","AwayTeam"]
inventory=[]

def read(name, required):
    path=ROOT/"data"/name
    if not path.exists():
        inventory.append({"file":name,"error":"missing file"})
        return None
    frame=pd.read_csv(path,low_memory=False)
    missing=[x for x in required if x not in frame.columns]
    inventory.append({"file":name,"rows":len(frame),"columns":list(frame.columns),"missing":missing})
    if missing:return None
    return frame

def numeric(frame, name):
    return pd.to_numeric(frame[name],errors="coerce")

def main():
    matches=read("matches_top5_2000-2026.csv",KEY+["FTHome","FTAway"])
    other=read("matches_autres_2000-2026.csv",KEY+["FTHome","FTAway"])
    details=read("details_2000-2026.csv",KEY+["HTHome","HTAway"])
    sources=[x for x in [matches,other] if x is not None]
    if not sources:
        return {"status":"no_valid_data","inventory":inventory}
    games=pd.concat(sources,ignore_index=True)
    games=games.drop_duplicates(subset=KEY,keep="first").copy()
    games["ft_home"]=numeric(games,"FTHome")
    games["ft_away"]=numeric(games,"FTAway")
    games["date"]=pd.to_datetime(games["MatchDate"],errors="coerce",dayfirst=True)
    games=games.dropna(subset=["date","ft_home","ft_away"])
    games=games[(games.ft_home>=0)&(games.ft_away>=0)]
    if details is not None:
        h=details[KEY+["HTHome","HTAway"]].drop_duplicates(subset=KEY)
        games=games.merge(h,on=KEY,how="left",validate="one_to_one")
        games["ht_home"]=numeric(games,"HTHome")
        games["ht_away"]=numeric(games,"HTAway")
        valid=(games.ht_home>=0)&(games.ht_away>=0)&(games.ht_home<=games.ft_home)&(games.ht_away<=games.ft_away)
        games.loc[~valid,["ht_home","ht_away"]]=np.nan
    games=games.sort_values(["date","Division","HomeTeam","AwayTeam"],kind="stable").reset_index(drop=True)
    if len(games)<1500:
        return {"status":"insufficient_data","rows":len(games),"inventory":inventory}
    # Split on date, not row, to prevent same-day labels entering test predictions.
    cut_date=games["date"].iloc[int(len(games)*.7)]
    train=games[games.date<cut_date]
    test=games[games.date>=cut_date]
    if len(train)<100 or len(test)<100:
        return {"status":"insufficient_split","inventory":inventory,"train":len(train),"test":len(test)}
    def evaluate(label, valid=None):
        tr=train if valid is None else train[valid(train)]
        te=test if valid is None else test[valid(test)]
        if len(tr)<100 or len(te)<100:
            return {"status":"insufficient_data","train":len(tr),"test":len(te)}
        ytr=label(tr).astype(int).to_numpy()
        yte=label(te).astype(int).to_numpy()
        prior=float(np.clip(ytr.mean(),.001,.999))
        # Global smoothed frequency from training only; true untouched holdout.
        pred=np.full(len(yte),prior)
        return {"train":len(ytr),"test":len(yte),"prevalence_train":float(ytr.mean()),
                "prevalence_test":float(yte.mean()),"baseline_logloss":float(log_loss(yte,pred,labels=[0,1])),
                "brier":float(np.mean((pred-yte)**2))}
    results={}
    for t in (1.5,2.5,3.5):
        results[f"FT_over_{t}"]=evaluate(lambda f,t=t:(f.ft_home+f.ft_away)>t)
    if "ht_home" in games.columns:
        ok=lambda f:f.ht_home.notna()&f.ht_away.notna()
        for t in (.5,1.5):
            results[f"MT1_over_{t}"]=evaluate(lambda f,t=t:(f.ht_home+f.ht_away)>t,ok)
            results[f"MT2_over_{t}"]=evaluate(lambda f,t=t:(f.ft_home+f.ft_away-f.ht_home-f.ht_away)>t,ok)
    return {"status":"completed","method":"chronological date-separated 70/30, training-only global frequency baseline",
            "inventory":inventory,"rows_after_dedup":len(games),"train":len(train),"test":len(test),
            "cut_date":str(cut_date.date()),"results":results,
            "caveat":"Baseline evaluation only, not a fitted predictive model; no odds comparison or production approval."}

if __name__=="__main__":
    report=main()
    (OUT/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))
    if report["status"]!="completed":raise SystemExit(1)
