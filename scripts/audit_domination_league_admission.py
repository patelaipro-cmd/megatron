"""Read-only V1 league admission gate: coverage is not model readiness."""
import argparse
import json
from pathlib import Path

def assess(snapshot, references, production_leagues):
    names=references.get("noms",{})
    counts=snapshot.get("league_counts",{})
    result=[]
    for league in snapshot.get("leagues",[]):
        n=counts.get(league,{})
        raw=n.get("raw",0);mapped=n.get("mapped",0)
        has_ref=f"espn:{league}" in names
        production=league in production_leagues
        result.append({
            "league":league,"raw_fixtures":raw,"mapped_fixtures":mapped,
            "unmapped_fixtures":n.get("unmapped",0),
            "reference_exists":has_ref,
            "historical_data_verified":False if not production else None,
            "model_calibration_verified":False if not production else None,
            "admission":"EXISTING_PRODUCTION_SCOPE" if production else "BLOCKED_EXPLORATORY",
            "blockers":[] if production else (
                (["LEAGUE_REFERENCE_MISSING"] if not has_ref else [])+
                (["FIXTURE_MAPPING_INCOMPLETE"] if mapped!=raw else [])+
                ["HISTORICAL_DATA_NOT_VERIFIED","2PLUS_3PLUS_CALIBRATION_NOT_VERIFIED"]
            )})
    return {"decision":"NO_GO","leagues":result,
            "exploratory_blocked":sum(x["admission"]=="BLOCKED_EXPLORATORY" for x in result),
            "note":"Existing production scope is not a GO verdict. Historical/calibration checks for new leagues are not inferred from name mappings."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",type=Path,required=True)
    p.add_argument("--reference",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    from scripts.registre_prospectif import LIGUES
    report=assess(json.loads(a.snapshot.read_text(encoding="utf-8")),
                  json.loads(a.reference.read_text(encoding="utf-8")),LIGUES)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"exploratory_blocked":report["exploratory_blocked"],
                      "leagues":[{"league":x["league"],"blockers":x["blockers"]}
                                 for x in report["leagues"] if x["blockers"]]}))
if __name__=="__main__":main()
