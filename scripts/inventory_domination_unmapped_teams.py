"""Read-only unmapped-team inventory from an archived V1 ESPN snapshot.

Never guesses team equivalences or authorizes prediction in exploratory leagues.
"""
import argparse
import csv
import json
from collections import Counter,defaultdict
from pathlib import Path

def build(snapshot, reference_names=None):
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
    reference_names=reference_names or {}
    teams=[{"league":league,"team_raw":name,"fixtures_n":count,
            "mapping_status":"UNVERIFIED","canonical_team":"",
            "reference_status":"LEAGUE_REFERENCE_MISSING" if f"espn:{league}" not in reference_names else "TEAM_ALIAS_UNVERIFIED"}
           for league,group in sorted(groups.items())
           for name,count in sorted(group["teams"].items())]
    ranked_leagues=sorted(({"league":k,"unmapped_fixtures":v["fixtures"],"unique_raw_teams":len(v["teams"])} for k,v in groups.items()),key=lambda x:(-x["unmapped_fixtures"],x["league"]))
    return {"priority_leagues":ranked_leagues,"raw_n":len(rows),"unmapped_fixtures_n":len(missing),
            "league_summary":{k:{"unmapped_fixtures":v["fixtures"],
                                  "unique_raw_teams":len(v["teams"])}
                              for k,v in sorted(groups.items())},
            "teams":teams,"decision":"NO_GO",
            "warning":"Missing league references are not team aliases; verify competition and historical data before promotion"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--csv",type=Path,required=True)
    p.add_argument("--reference",type=Path,help="Existing audit.json canonical name references")
    a=p.parse_args()
    references=json.loads(a.reference.read_text(encoding="utf-8")).get("noms",{}) if a.reference else {}
    result=build(json.loads(a.snapshot.read_text(encoding="utf-8")),references)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    a.csv.parent.mkdir(parents=True,exist_ok=True)
    with a.csv.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["league","team_raw","fixtures_n","mapping_status","canonical_team","reference_status"])
        w.writeheader();w.writerows(result["teams"])
    print(json.dumps({"unmapped_fixtures_n":result["unmapped_fixtures_n"],
                      "unmapped_teams_n":len(result["teams"]),
                      "league_summary":result["league_summary"],"priority_leagues":result["priority_leagues"]}))
if __name__=="__main__":main()
