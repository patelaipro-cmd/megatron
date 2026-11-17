"""Read-only prospective coverage of archived fixture snapshots against V1 ledger."""
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
from megatron.store import MemoryStore,parse_dt
from megatron.ledger import DOMAIN,market_of

def audit(registre,fixtures,observed_at=None,as_of=None):
    entries=MemoryStore(registre).active(DOMAIN)
    by_match=defaultdict(list)
    for e in entries:
        if e.key.startswith("pred:") and any(market_of(e.value).endswith(x) for x in ("MARGE_2PLUS","MARGE_3PLUS")):
            by_match[e.value["match_id"]].append(e)
    counts=Counter()
    details=[]
    for fixture in fixtures:
        mid=fixture["match_id"];kickoff=parse_dt(fixture["kickoff"])
        rows=by_match.get(mid,[])
        if observed_at is not None:
            minutes=(kickoff-parse_dt(as_of or observed_at)).total_seconds()/60
            if minutes>300:
                status="not_yet_in_initial_window"
                counts[status]+=1
                counts[f"{mid.split(':',1)[0]}:{status}"]+=1
                details.append({"match_id":mid,"status":status,"valid_markets":[]})
                continue
        valid=[e for e in rows if parse_dt(e.recorded_at)<kickoff and (as_of is None or parse_dt(e.recorded_at)<=parse_dt(as_of)) and (not e.value.get("data_cutoff") or parse_dt(e.value["data_cutoff"])<kickoff)]
        markets={market_of(e.value) for e in valid}
        status="covered_2plus_3plus" if any(m.endswith("MARGE_2PLUS") for m in markets) and any(m.endswith("MARGE_3PLUS") for m in markets) else ("partial_prediction" if markets else ("invalid_timing" if (any(parse_dt(e.recorded_at)<=parse_dt(as_of) for e in rows) if as_of else bool(rows)) else "no_prediction"))
        counts[status]+=1;counts[f"{mid.split(':',1)[0]}:{status}"]+=1
        details.append({"match_id":mid,"status":status,"valid_markets":sorted(markets)})
    return {"decision":"NO_GO","fixtures_n":len(fixtures),"status_counts":dict(sorted(counts.items())),"details":details,
            "limitations":["Requires independently archived fixture snapshots","No-prediction root cause needs collection and mapping logs","Read-only; no model promotion"]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--registre",type=Path,required=True)
    p.add_argument("--fixtures-json",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--as-of",help="UTC ISO audit time; defaults to snapshot capture time")
    a=p.parse_args()
    raw=json.loads(a.fixtures_json.read_text(encoding="utf-8"))
    fixtures=raw["fixtures"] if isinstance(raw,dict) else raw
    report=audit(a.registre,fixtures,raw.get("captured_at") if isinstance(raw,dict) else None,as_of=a.as_of)
    if isinstance(raw,dict):
        report["snapshot_metadata"]={"audit_as_of":a.as_of or raw.get("captured_at"),"captured_at":raw.get("captured_at"),"raw_fixtures_n":len(raw.get("raw_fixtures",[])),"unmapped_n":raw.get("unmapped_n"),"source_errors":raw.get("source_errors",[]),"complete":raw.get("complete"),"coverage_assessable":raw.get("coverage_assessable")}
        if not raw.get("coverage_assessable"):
            report["coverage_quality"]="NOT_ASSESSABLE"
        elif not fixtures:
            report["coverage_quality"]="NO_MAPPED_FIXTURES"
        else:
            report["coverage_quality"]="WINDOW_SCOPED_ONLY"
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"fixtures_n":report["fixtures_n"],"status_counts":report["status_counts"],"decision":"NO_GO"}))
if __name__=="__main__":main()
