"""Fetch and validate E1/SP2 historical results for V1 research, never promote models.

Data source: football-data.co.uk. Raw files are NOT committed to GitHub.
"""
import argparse,csv,hashlib,io,json,urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

DIVISIONS=("E1","SP2")
SEASONS=("2324","2425","2526")
BASE="https://www.football-data.co.uk/mmz4281/{season}/{division}.csv"

def parse_csv(data,division,season):
    text=data.decode("utf-8-sig",errors="replace")
    if text.count("\ufffd")>0:
        text=data.decode("cp1252")
    records=[];bad=Counter();seen=set()
    for row in csv.DictReader(io.StringIO(text)):
        if not row or not row.get("Date"):continue
        if row.get("Div") and row["Div"]!=division:
            bad["wrong_division"]+=1;continue
        try:
            date=datetime.strptime(row["Date"].strip(),"%d/%m/%Y").date()
        except ValueError:
            try:date=datetime.strptime(row["Date"].strip(),"%d/%m/%y").date()
            except ValueError:bad["invalid_date"]+=1;continue
        home=(row.get("HomeTeam") or "").strip()
        away=(row.get("AwayTeam") or "").strip()
        if not home or not away or home==away:bad["invalid_teams"]+=1;continue
        try:h=int(row["FTHG"]);a=int(row["FTAG"])
        except (ValueError,TypeError,KeyError):bad["missing_score"]+=1;continue
        if min(h,a)<0 or max(h,a)>30:bad["invalid_score"]+=1;continue
        key=(str(date),home,away)
        if key in seen:bad["duplicate"]+=1;continue
        seen.add(key)
        records.append({"division":division,"season":season,"date":str(date),
                        "home":home,"away":away,"home_goals":h,"away_goals":a,
                        "home_win_2plus":int(h-a>=2),"away_win_2plus":int(a-h>=2),
                        "home_win_3plus":int(h-a>=3),"away_win_3plus":int(a-h>=3)})
    return records,dict(bad)

def collect(fetch=None):
    if fetch is None:
        def fetch(url):
            request=urllib.request.Request(url,headers={"User-Agent":"MEGATRON-research/1.0"})
            with urllib.request.urlopen(request,timeout=25) as r:return r.read()
    all_rows=[];sources=[];errors=[]
    for division in DIVISIONS:
        for season in SEASONS:
            url=BASE.format(division=division,season=season)
            try:
                payload=fetch(url)
                records,bad=parse_csv(payload,division,season)
                if len(records)<100:raise ValueError("insufficient validated results")
                all_rows.extend(records)
                sources.append({"division":division,"season":season,"url":url,
                                "sha256":hashlib.sha256(payload).hexdigest(),
                                "validated_matches":len(records),"rejected":bad})
            except Exception as e:
                errors.append({"division":division,"season":season,"error":type(e).__name__})
    return {"decision":"NO_GO","historical_results":all_rows,"sources":sources,
            "errors":errors,"complete":len(sources)==len(DIVISIONS)*len(SEASONS),
            "notice":"Historical results alone do not validate ESPN aliases or 2+/3+ calibration"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    report=collect()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"matches":len(report["historical_results"]),"sources":report["sources"],
                      "errors":report["errors"],"complete":report["complete"],"decision":"NO_GO"}))
    if not report["complete"]:raise SystemExit(2)
if __name__=="__main__":main()
