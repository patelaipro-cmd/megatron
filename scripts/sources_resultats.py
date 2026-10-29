"""Collecte brute des résultats des cinq championnats auprès de trois familles indépendantes.

Usage (GitHub Actions, seul endroit d'où ces sites répondent) :
  python scripts/sources_resultats.py --sortie donnees/externe/resultats --depuis 2026-08-01 [--jusqua AAAA-MM-JJ]

- espn : tableau des scores par ligue et par jour (site.api.espn.com), réduit aux champs utiles,
  sous la forme {url: réponse} relue telle quelle par scripts/collecte_resultats_espn.py ;
- apifootball : /fixtures?league=&season=2026 (une requête par ligue, clé API_FOOTBALL_KEY en en-tête) ;
- footballdata : fichiers saison 2026/27 de football-data.co.uk, texte d'origine.

Rien n'est interprété ici : le rapprochement des noms, le recoupement et la quarantaine sont faits
par scripts/verifier_resultats.py, hors réseau. Une source en échec est notée, les autres continuent.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard?dates={jour}"
APIFOOTBALL = "https://v3.football.api-sports.io/fixtures?league={id}&season={saison}"
FOOTBALLDATA = "https://www.football-data.co.uk/mmz4281/{code}/{division}.csv"
LIGUES = {  # division de data/ : (slug ESPN, id API-Football)
    "E0": ("eng.1", 39), "F1": ("fra.1", 61), "D1": ("ger.1", 78), "SP1": ("esp.1", 140), "I1": ("ita.1", 135)}
SAISON = 2026
HEADERS = {"User-Agent": "MEGATRON-collecte-resultats/1.0", "Accept": "application/json"}


def lire(url: str, headers: dict | None = None, essais: int = 3) -> bytes:
    for i in range(essais):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={**HEADERS, **(headers or {})}), timeout=30) as r:
                return r.read()
        except Exception:
            if i == essais - 1:
                raise
            time.sleep(2 ** i)
    raise AssertionError


def reduire_espn(data: dict) -> dict:
    """Garde ce que decode_event lit : id, date, statut, domicile/extérieur, nom, score."""
    out = []
    for ev in data.get("events") or []:
        comp = (ev.get("competitions") or [{}])[0]
        out.append({"id": ev.get("id"), "date": ev.get("date"), "status": ev.get("status"),
                     "competitions": [{"date": comp.get("date"), "status": comp.get("status"),
                                       "competitors": [{"homeAway": c.get("homeAway"), "score": c.get("score"),
                                                        "team": {k: (c.get("team") or {}).get(k) for k in ("id", "displayName", "name", "abbreviation")}}
                                                       for c in comp.get("competitors") or []]}]})
    return {"events": out}


def reduire_apifootball(data: dict) -> list[dict]:
    out = []
    for r in data.get("response") or []:
        fx, t, g, s = r.get("fixture") or {}, r.get("teams") or {}, r.get("goals") or {}, r.get("score") or {}
        out.append({"fixture_id": fx.get("id"), "date": fx.get("date"), "statut": (fx.get("status") or {}).get("short"),
                    "domicile": (t.get("home") or {}).get("name"), "exterieur": (t.get("away") or {}).get("name"),
                    "buts_domicile": g.get("home"), "buts_exterieur": g.get("away"),
                    "temps_reglementaire": (s.get("fulltime") or {}), "journee": (r.get("league") or {}).get("round")})
    return out


def collecter(sortie: Path, depuis: date, jusqua: date, sources: list[str], cle: str = "", pause: float = 0.2,
              lire=lire) -> dict:
    sortie.mkdir(parents=True, exist_ok=True)
    manifeste = {"collecte_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "depuis": depuis.isoformat(), "jusqua": jusqua.isoformat(), "sources": {}}
    if "espn" in sources:
        pages, erreurs = {}, {}
        d = depuis
        while d <= jusqua:
            for slug, _ in LIGUES.values():
                url = ESPN.format(slug=slug, jour=d.strftime("%Y%m%d"))
                try:
                    pages[url] = reduire_espn(json.loads(lire(url)))
                except Exception as exc:
                    erreurs[url] = f"{type(exc).__name__}: {exc}"[:200]
                time.sleep(pause)
            d += timedelta(days=1)
        (sortie / "espn_scoreboards.json").write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
        manifeste["sources"]["espn"] = {"pages": len(pages), "evenements": sum(len(p["events"]) for p in pages.values()),
                                        "erreurs": erreurs}
    if "apifootball" in sources:
        if not cle:
            manifeste["sources"]["apifootball"] = {"statut": "ignore", "raison": "secret API_FOOTBALL_KEY absent"}
        else:
            res, erreurs = {}, {}
            for division, (_, lid) in LIGUES.items():
                url = APIFOOTBALL.format(id=lid, saison=SAISON)
                try:
                    data = json.loads(lire(url, {"x-apisports-key": cle}))
                    if data.get("errors"):
                        raise RuntimeError(str(data["errors"])[:200])
                    res[division] = reduire_apifootball(data)
                except Exception as exc:
                    erreurs[division] = f"{type(exc).__name__}: {exc}"[:200]
            (sortie / "apifootball_fixtures.json").write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
            manifeste["sources"]["apifootball"] = {"matchs": {k: len(v) for k, v in res.items()}, "erreurs": erreurs,
                                                   "requetes": len(LIGUES)}
    if "footballdata" in sources:
        code = f"{SAISON % 100:02d}{(SAISON + 1) % 100:02d}"
        tailles, erreurs = {}, {}
        for division in LIGUES:
            url = FOOTBALLDATA.format(code=code, division=division)
            try:
                brut = lire(url, {"Accept": "text/csv"})
                (sortie / f"footballdata_{division}.csv").write_bytes(brut)
                tailles[division] = len(brut)
            except Exception as exc:
                erreurs[division] = f"{type(exc).__name__}: {exc}"[:200]
        manifeste["sources"]["footballdata"] = {"octets": tailles, "erreurs": erreurs}
    (sortie / "manifeste.json").write_text(json.dumps(manifeste, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifeste


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sortie", type=Path, required=True)
    p.add_argument("--depuis", type=date.fromisoformat, default=date(2026, 8, 1))
    p.add_argument("--jusqua", type=date.fromisoformat, default=None)
    p.add_argument("--sources", default="espn,apifootball,footballdata")
    a = p.parse_args(argv)
    jusqua = a.jusqua or datetime.now(timezone.utc).date()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%MZ")
    m = collecter(a.sortie / stamp, a.depuis, jusqua, a.sources.split(","), os.environ.get("API_FOOTBALL_KEY", "").strip())
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "erreurs"} | {"erreurs": len(v.get("erreurs", {}))}
                      for k, v in m["sources"].items()}, ensure_ascii=False))
    return 0 if any(not v.get("erreurs") and v.get("statut") != "ignore" for v in m["sources"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
