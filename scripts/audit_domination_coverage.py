"""Read-only V1 historical coverage audit."""
import argparse,csv,json
from collections import Counter
from pathlib import Path
from megatron import data

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    matches=data.load(data.CURRENT)
    ids={m.match_id for m in matches}
    with open("docs/experiences/EXP-009/variables.csv",newline="",encoding="utf-8") as f:
        feature_ids=[r["match_id"] for r in csv.DictReader(f)]
    assert len(feature_ids)==len(set(feature_ids)),"duplicate feature match_id"
    feats=set(feature_ids)
    counts=Counter(m.division for m in matches)
    uncovered=Counter(m.division for m in matches if m.match_id not in feats)
    report={"historical_matches":len(matches),"feature_matches":len(feats),
            "covered_matches":len(ids&feats),"without_features":len(ids-feats),
            "features_without_scores":len(feats-ids),
            "divisions":[{"division":d,"historical":n,"without_features":uncovered[d]} for d,n in sorted(counts.items(),key=lambda x:(-uncovered[x[0]],x[0]))],
            "warning":"Inventory only: new prematch predictions require strict historical rolling features; no production promotion"}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":
    main()
