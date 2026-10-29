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


def sonder() -> dict:
    res = {}
    for ligue in ("eng.1", "fra.1", "esp.1", "ger.1", "ita.1", "ned.1"):
        code, corps = lire(f"{ESPN}/{ligue}/scoreboard")
        res[f"espn_scoreboard_{ligue}"] = resume(code, corps)
        events = corps.get("events") if isinstance(corps, dict) else None
        if events:
            ev = events[0]["id"]
            code2, corps2 = lire(f"{ESPN}/{ligue}/summary?event={ev}")
            res[f"espn_summary_{ligue}"] = resume(code2, corps2)
            equipes = [c["team"]["id"] for c in events[0]["competitions"][0]["competitors"]]
            code3, corps3 = lire(f"{ESPN}/{ligue}/teams/{equipes[0]}?enable=roster,injuries")
            res[f"espn_team_{ligue}"] = resume(code3, corps3)
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
