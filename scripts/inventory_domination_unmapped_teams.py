"""Read-only unmapped-team inventory from an archived V1 ESPN snapshot.

Never guesses team equivalences or authorizes prediction in exploratory leagues.
"""
import argparse
import csv
import json
from collections import Counter,defaultdict
from pathlib import Path

def build(snapshot):
    rows=snapshot.get("raw_fixtures",[])
    missing=[r for r in rows if r.get("mapping_status")=="unmapped"]
    groups=defaultdict(lambda:{"fixtures":0,"teams":Counter()})
    for row in missing:
        league=row["league"]
        groups[league]["fixtures"]+=1
        for key in ("home_raw","away_raw"):
            name=row.get(key)
            if name:
                groups[league]["teams"][name]+=1
    teams=[{"league":league,"team_raw":name,"fixtures_n":count,
            "mapping_status":"UNVERIFIED","canonical_team":""}
           for league,group in sorted(groups.items())
           for name,count in sorted(group["teams"].items())]
    return {"raw_n":len(rows),"unmapped_fixtures_n":len(missing),
            "league_summary":{k:{"unmapped_fixtures":v["fixtures"],
                                  "unique_raw_teams":len(v["teams"])}
                              for k,v in sorted(groups.items())},
            "teams":teams,"decision":"NO_GO",
            "warning":"Manual/source-verified mapping required; no automatic alias promotion"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--csv",type=Path,required=True)
    a=p.parse_args()
    result=build(json.loads(a.snapshot.read_text(encoding="utf-8")))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    a.csv.parent.mkdir(parents=True,exist_ok=True)
    with a.csv.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["league","team_raw","fixtures_n","mapping_status","canonical_team"])
        w.writeheader();w.writerows(result["teams"])
    print(json.dumps({"unmapped_fixtures_n":result["unmapped_fixtures_n"],
                      "unmapped_teams_n":len(result["teams"]),
                      "league_summary":result["league_summary"]}))
if __name__=="__main__":main()
