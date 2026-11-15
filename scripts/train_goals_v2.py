#!/usr/bin/env python3
"""GOALS V2 isolated chronological baseline; no V1 imports or writes."""
import json, pathlib, sys
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss
ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
OUT=ROOT/"artifacts"/"goals_v2"
OUT.mkdir(parents=True,exist_ok=True)
def col(df,names):
    lookup={str(c).lower().replace("_","").replace(" ",""):c for c in df.columns}
    for n in names:
        c=lookup.get(n.lower().replace("_","").replace(" ",""))
        if c is not None:return c
    return None
def load(path):
    df=pd.read_csv(path,low_memory=False)
    home=col(df,["FTHG","HG","home_goals","home_score","goals_home"])
    away=col(df,["FTAG","AG","away_goals","away_score","goals_away"])
    if not home or not away:return None,{"file":str(path),"reason":"missing full-time score columns","columns":list(df.columns)}
    date=col(df,["Date","match_date","utcDate","date_utc"])
    if not date:return None,{"file":str(path),"reason":"missing match date","columns":list(df.columns)}
    d=pd.DataFrame({"date":pd.to_datetime(df[date],errors="coerce",dayfirst=True),
       "ft_home":pd.to_numeric(df[home],errors="coerce"),"ft_away":pd.to_numeric(df[away],errors="coerce")})
    h=col(df,["HTHG","HTHome","HT_home","half_time_home_goals"])
    a=col(df,["HTAG","HTAway","HT_away","half_time_away_goals"])
    if h and a:
        d["ht_home"]=pd.to_numeric(df[h],errors="coerce")
        d["ht_away"]=pd.to_numeric(df[a],errors="coerce")
    d=d.dropna(subset=["date","ft_home","ft_away"])
    d=d[(d.ft_home>=0)&(d.ft_away>=0)]
    if "ht_home" in d:
        d=d[((d.ht_home>=0)&(d.ht_away>=0)&(d.ht_home<=d.ft_home)&(d.ht_away<=d.ft_away)) | d.ht_home.isna() | d.ht_away.isna()]
    return d,{"file":str(path),"rows":len(d),"halftime":int(d.ht_home.notna().sum()) if "ht_home" in d else 0}
paths=[DATA/"details_2000-2026.csv",DATA/"matches_top5_2000-2026.csv"]
frames=[]; inventory=[]
for p in paths:
    if not p.exists():
        inventory.append({"file":str(p),"reason":"not found"});continue
    d,info=load(p);inventory.append(info)
    if d is not None:frames.append(d)
if not frames:
    (OUT/"report.json").write_text(json.dumps({"status":"no_valid_data","inventory":inventory},indent=2))
    sys.exit("No usable historical data; see report.json")
df=pd.concat(frames,ignore_index=True).drop_duplicates().sort_values("date").reset_index(drop=True)
if len(df)<100:sys.exit("Insufficient historical matches")
cut=int(len(df)*0.7)
train,test=df.iloc[:cut],df.iloc[cut:]
def evaluate(label, tr, te):
    if len(tr)<50 or len(te)<20:return {"status":"insufficient_data","train":len(tr),"test":len(te)}
    prior=float(np.clip(tr.mean(),0.001,0.999))
    # Strict chronological expanding-window smoothed probability, no future labels.
    history=np.cumsum(np.r_[tr.astype(int).values,te.astype(int).values[:-1]])
    counts=np.arange(len(tr),len(tr)+len(te))
    probs=np.clip((history[len(tr)-1:]+80*prior)/(counts+80),0.001,0.999)
    return {"train":len(tr),"test":len(te),"prevalence_test":float(te.mean()),
            "baseline_logloss":float(log_loss(te,np.full(len(te),prior),labels=[0,1])),
            "expanding_logloss":float(log_loss(te,probs,labels=[0,1]))}
results={}
for threshold in [1.5,2.5,3.5]:
    results[f"FT_over_{threshold}"]=evaluate("FT", (train.ft_home+train.ft_away>threshold), (test.ft_home+test.ft_away>threshold))
if "ht_home" in df:
    for period in ["MT1","MT2"]:
        for threshold in [0.5,1.5]:
            def target(frame):
                valid=frame.dropna(subset=["ht_home","ht_away"])
                ft=valid.ft_home+valid.ft_away; ht=valid.ht_home+valid.ht_away
                return (ht if period=="MT1" else ft-ht)>threshold
            results[f"{period}_over_{threshold}"]=evaluate(period,target(train),target(test))
report={"status":"completed","method":"chronological 70/30 expanding historical frequency; no V1 dependencies","inventory":inventory,"rows_after_dedup":len(df),"train":len(train),"test":len(test),"results":results,"caveat":"baseline only; no betting-market comparison, no production approval"}
(OUT/"report.json").write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
