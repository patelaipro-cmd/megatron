"""Archive raw ESPN fixture inventory before name mapping or V1 filtering.

Read-only: no predictions, no registry writes. Snapshot is useful only when
captured before kickoff; do not use it to reconstruct earlier coverage.
"""
import argparse
import json
from datetime import datetime,timedelta,timezone
from pathlib import Path
from scripts.registre_prospectif import ESPN,LIGUES,lire_json
from megatron.store import parse_dt

def collect(now,lire=lire_json):
    fixtures=[];errors=[]
    for league,slug in LIGUES.items():
        for day in (now.date(),(now+timedelta(days=1)).date()):
            url=ESPN.format(slug=slug,jour=day.strftime("%Y%m%d"))
            try:
                events=lire(url).get("events") or []
            except Exception as exc:
                errors.append({"league":league,"day":str(day),"error":type(exc).__name__})
                continue
            for ev in events:
                comp=(ev.get("competitions") or [{}])[0]
                competitors=comp.get("competitors") or []
                sides={x.get("homeAway"):(x.get("team") or {}).get("displayName") for x in competitors}
                raw=ev.get("date") or comp.get("date")
                if not raw or set(sides)!={"home","away"}:
                    errors.append({"league":league,"event_id":str(ev.get("id")),"error":"missing_date_or_teams"})
                    continue
                kickoff=parse_dt(raw)
                state=((comp.get("status") or ev.get("status") or {}).get("type") or {}).get("state")
                fixtures.append({"league":league,"espn_id":str(ev.get("id")),"home_raw":sides["home"],
                                 "away_raw":sides["away"],"kickoff":kickoff.isoformat(),
                                 "state_at_capture":state,"pre_kickoff_at_capture":now<kickoff})
    return {"captured_at":now.isoformat(),"source":"ESPN scoreboard raw before mapping",
            "fixtures":fixtures,"errors":errors,"complete":not errors,
            "warning":"Coverage denominator is valid only for snapshots captured before kickoff; unmapped names need separate mapping audit"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    report=collect(datetime.now(timezone.utc))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"fixtures":len(report["fixtures"]),"errors":len(report["errors"]),"complete":report["complete"]}))
if __name__=="__main__":main()
