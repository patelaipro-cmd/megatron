"""Fetch available football-data.org fixtures and finished matches. No fake data."""
import json,os,urllib.request,urllib.parse
from datetime import datetime,timezone,timedelta
from pathlib import Path
from model import score
BASE="https://api.football-data.org/v4"
def fetch(path,params):
    token=os.environ.get("FOOTBALL_DATA_API_KEY")
    if not token:raise RuntimeError("GitHub secret FOOTBALL_DATA_API_KEY is required")
    url=BASE+path+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"X-Auth-Token":token,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=35) as resp:return json.load(resp).get("matches",[])
def normalize(m,league):
    h=m.get("homeTeam") or {};a=m.get("awayTeam") or {}
    h=str(h.get("id") or "");a=str(a.get("id") or "")
    if not h or not a or h==a or not m.get("utcDate"):return None
    return {"date":m["utcDate"],"league":league,"home":h,"away":a,"home_name":(m.get("homeTeam") or {}).get("name",h),"away_name":(m.get("awayTeam") or {}).get("name",a)}
def run():
    today=datetime.now(timezone.utc)
    codes=[s.strip() for s in os.getenv("COMPETITIONS","PL,BL1").split(",") if s.strip()]
    history=[];upcoming=[];errors=[]
    for code in codes:
        try:
            finished=fetch("/competitions/"+code+"/matches",{"status":"FINISHED"})
            scheduled=fetch("/competitions/"+code+"/matches",{"status":"SCHEDULED","dateFrom":today.date().isoformat(),"dateTo":(today+timedelta(days=2)).date().isoformat()})
        except Exception as exc:
            errors.append({"competition":code,"error":type(exc).__name__});continue
        for m in finished:
            row=normalize(m,code); ft=(m.get("score") or {}).get("fullTime") or {}
            if row and isinstance(ft.get("home"),int) and isinstance(ft.get("away"),int):
                row.update(hg=ft["home"],ag=ft["away"]);history.append(row)
        for m in scheduled:
            row=normalize(m,code)
            if row and row["date"]>today.isoformat().replace("+00:00","Z"):upcoming.append(row)
    history.sort(key=lambda x:x["date"])
    results=[]
    for m in upcoming:
        # Strict cutoff: no match result at or after the target fixture kickoff.
        past=[r for r in history if r["date"]<m["date"]]
        p=score(past,m["home"],m["away"],m["league"])
        results.append({"date":m["date"],"league":m["league"],"home":m["home_name"],"away":m["away_name"],"p_btts_oui":p,"status":"ok_non_calibre" if p is not None else "donnees_insuffisantes"})
    results.sort(key=lambda x:x["p_btts_oui"] if x["p_btts_oui"] is not None else -1,reverse=True)
    output={"generated_at":today.isoformat(),"results":results,"errors":errors,"method":"independent_poisson_uncalibrated"}
    target=Path(__file__).parent/"data"/"predictions.json";target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Matches:",len(results),"Errors:",len(errors))
    if not history or not upcoming:raise RuntimeError("No historical data or upcoming fixtures available")
if __name__=="__main__":run()
