"""Strict historical team-name coverage audit; no fuzzy auto-acceptance.

This is an inventory of the 24 ESPN fixtures captured 2026-11-16.
Presence in 2023-26 football-data results does not prove 2026-27 league membership.
"""
import argparse,json,unicodedata
from collections import Counter
from pathlib import Path

FIXTURES={
"E1":[("Southampton","Derby County"),("Norwich City","Cardiff City"),("Millwall","Queens Park Rangers"),("Wolverhampton Wanderers","Charlton Athletic"),("West Ham United","Preston North End"),("Swansea City","West Bromwich Albion"),("Stoke City","Birmingham City"),("Sheffield United","Watford"),("Middlesbrough","Bristol City"),("Lincoln City","Wrexham"),("Bolton Wanderers","Portsmouth"),("Burnley","Blackburn Rovers")],
"SP2":[("Albacete","RC Celta Fortuna"),("FC Andorra","Leganés"),("CD Sabadell","Granada"),("Real Sociedad II","Cádiz"),("Castellón","Eldense"),("Tenerife","Mallorca"),("Córdoba","Real Oviedo"),("Sporting Gijón","Las Palmas"),("Girona","Eibar"),("RC Celta Fortuna","Real Valladolid"),("Burgos","Albacete"),("Ceuta","Almería")]}
def normalized(s):
    return " ".join("".join(c for c in unicodedata.normalize("NFKD",s.casefold()) if not unicodedata.combining(c)).split())
def audit(data):
    by_league={}
    for row in data["historical_results"]:
        by_league.setdefault(row["division"],Counter()).update([row["home"],row["away"]])
    teams=[];fixtures=[]
    for league,pairs in FIXTURES.items():
        history=by_league.get(league,Counter())
        for name in sorted({n for pair in pairs for n in pair}):
            exact=history.get(name,0)
            normalized_matches=[n for n in history if normalized(n)==normalized(name)]
            teams.append({"league":league,"espn_name":name,"historical_exact_appearances":exact,
                          "historical_normalized_candidates":normalized_matches,
                          "status":"EXACT_NAME_PRESENT" if exact else "REQUIRES_MANUAL_ALIAS_OR_CROSS_DIVISION_CHECK"})
        for home,away in pairs:
            fixtures.append({"league":league,"home":home,"away":away,
                             "both_exact_in_same_league":bool(history.get(home) and history.get(away)),
                             "admission":"NO_GO","reason":"historical name coverage does not establish current league membership or prospective calibration"})
    return {"decision":"NO_GO","source_complete":data.get("complete",False),
            "historical_matches":len(data["historical_results"]),
            "teams":teams,"fixtures":fixtures,
            "summary":{"teams":len(teams),"exact_names":sum(t["historical_exact_appearances"]>0 for t in teams),
                       "fixtures_both_exact":sum(f["both_exact_in_same_league"] for f in fixtures)}}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--historical",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=audit(json.loads(a.historical.read_text(encoding="utf-8")))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result["summary"]))
    print("DECISION: NO_GO - current membership and alias checks required")
if __name__=="__main__":main()
