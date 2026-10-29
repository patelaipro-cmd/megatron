"""Sonde des API candidates (2e/3e famille de sources pour les absences et compos).

Exécuté sur GitHub Actions (`sonde-sources.yml`, déclenchement manuel) : pour chaque URL, écrit
le code HTTP, les clés JSON de premier niveau et un extrait dans `<sortie>/sondes/<nom>.json`.
Ne collecte rien pour le moteur : sert à décider s'il faut écrire un collecteur.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer"
HEADERS = {"User-Agent": "megatron-sonde/1.0", "Accept": "application/json"}


def lire(url: str) -> tuple[int, object]:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30) as r:
            corps = r.read()
            code = r.status
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:500].decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError) as e:
        return 0, str(e)
    try:
        return code, json.loads(corps)
    except ValueError:
        return code, corps[:500].decode("utf-8", "replace")


def resume(code: int, corps: object) -> dict:
    out = {"code": code}
    if isinstance(corps, dict):
        out["cles"] = sorted(corps)
        out["extrait"] = json.dumps(corps, ensure_ascii=False)[:20000]
    else:
        out["extrait"] = str(corps)[:2000]
    return out


def structure_summary(corps) -> dict:
    if not isinstance(corps, dict):
        return {}
    out = {"statut": corps.get("header", {}).get("competitions", [{}])[0].get("status", {}).get("type", {}).get("name")}
    for r in corps.get("rosters") or []:
        joueurs = r.get("roster") or []
        out[(r.get("team") or {}).get("displayName", "?")] = {
            "cles_bloc": sorted(r), "joueurs": len(joueurs), "titulaires": sum(1 for j in joueurs if j.get("starter")),
            "exemple": json.dumps(joueurs[0], ensure_ascii=False)[:1500] if joueurs else None}
    return out


def structure_equipe(corps) -> dict:
    if not isinstance(corps, dict):
        return {}
    t = corps.get("team") or {}
    ath = t.get("athletes") or []
    blesses = [a for a in ath if a.get("injuries")]
    return {"cles_equipe": sorted(t), "joueurs": len(ath), "cles_joueur": sorted(ath[0]) if ath else [],
            "statuts": sorted({json.dumps(a.get("status"), ensure_ascii=False) for a in ath})[:10],
            "avec_injuries": len(blesses),
            "exemple_blesse": json.dumps(blesses[0], ensure_ascii=False)[:2000] if blesses else None,
            "injuries_equipe": json.dumps(t.get("injuries"), ensure_ascii=False)[:2000]}


def sonder() -> dict:
    res = {}
    for ligue in ("eng.1", "fra.1", "esp.1", "ger.1", "ita.1", "ned.1"):
        code, corps = lire(f"{ESPN}/{ligue}/scoreboard")
        res[f"espn_scoreboard_{ligue}"] = resume(code, corps)
        events = corps.get("events") if isinstance(corps, dict) else None
        for ev in (events or [])[:2]:  # un match passé ou en cours et un à venir si possible
            etat = ev.get("status", {}).get("type", {}).get("state")
            code2, corps2 = lire(f"{ESPN}/{ligue}/summary?event={ev['id']}")
            res[f"espn_summary_{ligue}_{etat}"] = {**resume(code2, corps2), "structure": structure_summary(corps2)}
        if events:
            equipes = [c["team"]["id"] for c in events[0]["competitions"][0]["competitors"]]
            code3, corps3 = lire(f"{ESPN}/{ligue}/teams/{equipes[0]}?enable=roster,injuries")
            res[f"espn_team_{ligue}"] = {**resume(code3, corps3), "structure": structure_equipe(corps3)}
    code, corps = lire("http://api.clubelo.com/" + datetime.now(timezone.utc).date().isoformat())
    res["clubelo_http"] = resume(code, corps)
    return res


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--sortie", required=True, type=Path)
    a = p.parse_args(argv)
    dossier = a.sortie / "sondes"
    dossier.mkdir(parents=True, exist_ok=True)
    quand = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for nom, r in sonder().items():
        (dossier / f"{nom}.json").write_text(json.dumps({"sonde_le": quand, **r}, indent=1, ensure_ascii=False) + "\n")
        print(nom, r["code"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
