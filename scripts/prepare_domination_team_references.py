"""Build a conservative, review-ready team reference inventory from a fixture CSV.

Does not infer historical team IDs or promote exploratory leagues.
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

def inventory(rows):
    result=[]
    for league in sorted({r["league"] for r in rows}):
        fixtures=[r for r in rows if r["league"]==league]
        counts=Counter(name for r in fixtures for name in (r["home_raw"],r["away_raw"]))
        for name in sorted(counts):
            result.append({"league":league,"source":"ESPN","source_team_name":name,
                           "fixture_appearances":counts[name],"canonical_team_id":"",
                           "competition_verified":"NO","historical_reference_verified":"NO",
                           "mapping_decision":"BLOCKED"})
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--fixtures-csv",type=Path,required=True)
    p.add_argument("--output-csv",type=Path,required=True)
    p.add_argument("--output-json",type=Path,required=True)
    a=p.parse_args()
    with a.fixtures_csv.open(encoding="utf-8-sig",newline="") as f:
        teams=inventory(list(csv.DictReader(f)))
    a.output_csv.parent.mkdir(parents=True,exist_ok=True)
    with a.output_csv.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(teams[0]) if teams else [
            "league","source","source_team_name","fixture_appearances",
            "canonical_team_id","competition_verified","historical_reference_verified","mapping_decision"])
        w.writeheader();w.writerows(teams)
    a.output_json.write_text(json.dumps({"teams":teams,"n_teams":len(teams),
        "admission":"NO_GO","note":"No source-confirmed canonical aliases"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"n_teams":len(teams),"status":"BLOCKED_PENDING_VERIFICATION"}))
if __name__=="__main__":main()
