"""Archive a read-only ESPN fixture census for future V1 coverage audits.

Raw fixtures (including unmapped names) are retained; only mapped fixtures may
be compared to the ledger. A snapshot is NOT a historical completeness claim.
"""
import argparse,json
from datetime import datetime,timezone,timedelta
from pathlib import Path
from scripts.registre_prospectif import ESPN,LIGUES,NOMS,lire_json
from megatron.store import parse_dt

def capture(now, noms, lire=lire_json):
    records=[];errors=[];source_diagnostics=[]
    for div,slug in LIGUES.items():
        for offset in range(8):
            day=now+timedelta(days=offset)
            try:
                payload=lire(ESPN.format(slug=slug,jour=day.strftime("%Y%m%d")))
                events=payload.get("events") or []
                source_diagnostics.append({"league":div,"date":day.date().isoformat(),
                                           "returned_events":len(events),"response_has_events":isinstance(payload.get("events"),list)})
            except Exception as exc:
                errors.append({"league":div,"date":day.date().isoformat(),"error":type(exc).__name__})
                continue
            for ev in events:
                comp=(ev.get("competitions") or [{}])[0]
                status=((comp.get("status") or ev.get("status") or {}).get("type") or {}).get("state")
                competitors={x.get("homeAway"):(x.get("team") or {}).get("displayName") for x in comp.get("competitors") or []}
                if set(competitors)!={"home","away"}:continue
                try:kickoff=parse_dt(ev.get("date") or comp.get("date"))
                except (ValueError,TypeError):continue
                if kickoff<=now:continue
                mapped=noms.get(f"espn:{div}",{})
                home,away=mapped.get(competitors["home"]),mapped.get(competitors["away"])
                records.append({"league":div,"espn_id":str(ev.get("id")),"kickoff":kickoff.isoformat(),
                                "state":status,"home_raw":competitors["home"],"away_raw":competitors["away"],
                                "match_id":f"{div}:{kickoff.date().isoformat()}:{home}-{away}" if home and away else None,
                                "mapping_status":"mapped" if home and away else "unmapped"})
    unique={(x["league"],x["espn_id"],x["kickoff"]):x for x in records}
    rows=sorted(unique.values(),key=lambda x:(x["kickoff"],x["league"],x["espn_id"]))
    return {"captured_at":now.isoformat(),"source":"ESPN public fixture scoreboard","leagues":list(LIGUES),
            "raw_fixtures":rows,"fixtures":[{"match_id":r["match_id"],"kickoff":r["kickoff"]}
                    for r in rows if r["mapping_status"]=="mapped" and r["state"]=="pre"],
            "unmapped_n":sum(r["mapping_status"]=="unmapped" for r in rows),
            "source_errors":errors,"source_diagnostics":source_diagnostics,
            "complete":not errors and len(source_diagnostics)==8*len(LIGUES)
                       and all(d["response_has_events"] for d in source_diagnostics),
            "empty_snapshot":not rows,
            "lookahead_days":8,
            "coverage_assessable":bool(rows) and not errors}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    names=json.loads(NOMS.read_text(encoding="utf-8"))["noms"]
    snapshot=capture(datetime.now(timezone.utc),names)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(snapshot,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"raw_n":len(snapshot["raw_fixtures"]),"mapped_n":len(snapshot["fixtures"]),
                      "unmapped_n":snapshot["unmapped_n"],"errors":len(snapshot["source_errors"]),
                      "empty_snapshot":snapshot["empty_snapshot"],
                      "coverage_assessable":snapshot["coverage_assessable"]}))
    if snapshot["source_errors"]:raise SystemExit(2)
if __name__=="__main__":main()
