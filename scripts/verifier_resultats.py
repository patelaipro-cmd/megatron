"""Recoupe les résultats bruts de trois familles et n'admet que les scores confirmés deux fois.

Usage (hors réseau, après le workflow `resultats`) :
  python scripts/verifier_resultats.py --brut <externe/resultats/AAAA-MM-JJTHHMMZ> --depuis 2026-09-21 \
      [--jusqua AAAA-MM-JJ] [--admis data/complement_resultats_2026-27.csv] [--rapport docs/resultats-2026-27]

1. Noms : chaque nom de source est relié à un nom de data/ par les matchs communs de la saison
   (même jour, même score : vote de scripts/complement_openfootball.py) ; aucun rapprochement approché.
2. ESPN est lu par scripts/collecte_resultats_espn.py (matchs terminés seulement, conflits avec
   l'historique refusés). API-Football : statut FT. football-data : fichier de résultats, tous terminés.
3. Un match (division, domicile, extérieur ; unique dans une saison de championnat) est ADMIS si au
   moins deux familles donnent le même score final et qu'aucune ne le contredit, avec des dates à
   un jour près. Sinon il reste en QUARANTAINE avec sa raison. Rien n'est estimé ni inventé.
4. Les cotes Bet365 et les tirs viennent de football-data quand il fait partie des familles qui
   confirment (même origine que l'historique xgabora) ; sinon les colonnes restent vides.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import collecte_resultats_espn as espn  # noqa: E402
from complement_openfootball import COLUMNS, hour_offset, name_map  # noqa: E402

BASE = (ROOT / "data" / "matches_top5_2000-2026.csv", ROOT / "data" / "complement_openfootball_2026-27.csv")
DEBUT_SAISON = "2026-07-01"
FAMILLES = ("espn", "apifootball", "footballdata")
TOLERANCE_JOURS = 1


def _reference(paths) -> list[dict]:
    out = []
    for p in paths:
        with Path(p).open(newline="", encoding="utf-8") as fh:
            out += [r for r in csv.DictReader(fh) if r["MatchDate"] >= DEBUT_SAISON]
    return out


def lire_espn(brut: Path, maintenant: datetime) -> tuple[dict[str, list[dict]], list[dict]]:
    """Matchs terminés par division, au format de vote {date, time, team1, team2, ft, ...}."""
    pages = json.loads((brut / "espn_scoreboards.json").read_text(encoding="utf-8"))
    divs = {slug: d for d, slug in espn.LEAGUES.items()}
    out, rejets, vus = {d: [] for d in espn.LEAGUES}, [], set()
    for url, page in pages.items():
        slug = url.split("/soccer/")[1].split("/")[0]
        for ev in page.get("events") or []:
            try:
                x = espn.decode_event(ev, slug, maintenant)
            except ValueError as exc:
                rejets.append({"famille": "espn", "division": divs[slug], "id": ev.get("id"), "raison": str(exc)})
                continue
            if x is None:
                nom = ((ev.get("status") or {}).get("type") or {}).get("name", "")
                if nom not in ("STATUS_SCHEDULED", "STATUS_FINAL", "STATUS_FULL_TIME", ""):
                    rejets.append({"famille": "espn", "division": divs[slug], "id": ev.get("id"),
                                   "raison": f"NON_TERMINE : {nom} {str(ev.get('date'))[:10]}"})
                continue
            if (slug, x["id"]) in vus:
                continue
            vus.add((slug, x["id"]))
            out[divs[slug]].append({"date": x["day"], "time": x["time"][:5], "team1": x["home"], "team2": x["away"],
                                    "ft": (x["hg"], x["ag"]), "id": x["id"], "kickoff_utc": x["kickoff_utc"]})
    return out, rejets


def lire_apifootball(brut: Path) -> dict[str, list[dict]]:
    f = brut / "apifootball_fixtures.json"
    data = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    out = {}
    for div, fixtures in data.items():
        out[div] = []
        for x in fixtures:
            if x.get("statut") != "FT" or x.get("buts_domicile") is None:
                continue
            ko = datetime.fromisoformat(x["date"]).astimezone(timezone.utc)
            out[div].append({"date": ko.date().isoformat(), "time": ko.strftime("%H:%M"), "team1": x["domicile"],
                             "team2": x["exterieur"], "ft": (int(x["buts_domicile"]), int(x["buts_exterieur"])),
                             "id": str(x["fixture_id"]), "kickoff_utc": ko.isoformat()})
    return out


def lire_footballdata(brut: Path) -> dict[str, list[dict]]:
    out = {}
    for f in sorted(brut.glob("footballdata_*.csv")):
        div = f.stem.split("_", 1)[1]
        texte = f.read_bytes().decode("utf-8-sig", errors="replace")
        out[div] = []
        for r in csv.DictReader(io.StringIO(texte)):
            if not (r.get("HomeTeam") and r.get("FTHG") not in (None, "") and r.get("Date")):
                continue
            j, m, a = r["Date"].split("/")
            jour = date(int(a) + (2000 if len(a) == 2 else 0), int(m), int(j))
            out[div].append({"date": jour.isoformat(), "time": (r.get("Time") or "")[:5], "team1": r["HomeTeam"],
                             "team2": r["AwayTeam"], "ft": (int(r["FTHG"]), int(r["FTAG"])), "id": "",
                             "cotes": tuple(r.get(k, "") for k in ("B365H", "B365D", "B365A")),
                             "tirs": tuple(r.get(k, "") for k in ("HS", "AS", "HST", "AST"))})
    return out


def verifier(brut: Path, depuis: date, jusqua: date, base=BASE, maintenant: datetime | None = None) -> dict:
    maintenant = maintenant or datetime.now(timezone.utc)
    ref = _reference(base)
    if not ref:
        raise ValueError("aucun match de référence pour la saison : arrêt")
    connus = {(r["Division"], r["HomeTeam"], r["AwayTeam"]): r for r in ref}
    sources, rejets = {}, []
    sources["espn"], rejets = lire_espn(brut, maintenant)
    sources["apifootball"] = lire_apifootball(brut)
    sources["footballdata"] = lire_footballdata(brut)
    noms, decalages, candidats, compteurs = {}, {}, {}, Counter()
    for fam, par_div in sources.items():
        for div, matchs in par_div.items():
            try:
                mapping = name_map(div, [m for m in matchs if m["date"] <= max(r["MatchDate"] for r in ref)], ref)
            except SystemExit as exc:
                rejets.append({"famille": fam, "division": div, "id": "", "raison": f"NOMS_AMBIGUS : {exc}"})
                continue
            noms[f"{fam}:{div}"] = mapping
            decalages[f"{fam}:{div}"] = hour_offset(div, [m for m in matchs if m.get("time")], ref, mapping)
            for m in matchs:
                compteurs[f"{fam}_termines"] += 1
                h, a = mapping.get(m["team1"]), mapping.get(m["team2"])
                dans_fenetre = depuis.isoformat() <= m["date"] <= jusqua.isoformat()
                if not dans_fenetre and (div, h, a) not in connus:
                    continue
                if not (h and a):
                    rejets.append({"famille": fam, "division": div, "id": m["id"],
                                   "raison": f"NOM_NON_RELIE : {[t for t in (m['team1'], m['team2']) if t not in mapping]}"})
                    continue
                if (div, h, a) in connus:
                    r = connus[(div, h, a)]
                    if (int(r["FTHome"]), int(r["FTAway"])) != m["ft"]:
                        rejets.append({"famille": fam, "division": div, "id": m["id"],
                                       "raison": f"CONFLIT_HISTORIQUE : {r['MatchDate']} {r['FTHome']}-{r['FTAway']} vs {m['ft']}"})
                    compteurs["deja_connus"] += 1
                    continue
                candidats.setdefault((div, h, a), {})[fam] = {**m, "decalage_h": decalages[f"{fam}:{div}"]}
    admis, quarantaine = [], []
    for (div, h, a), par_fam in sorted(candidats.items(), key=lambda kv: min(m["date"] for m in kv[1].values())):
        scores = Counter(m["ft"] for m in par_fam.values())
        jours = sorted(date.fromisoformat(m["date"]) for m in par_fam.values())
        ligne = {"Division": div, "HomeTeam": h, "AwayTeam": a,
                 **{f"score_{f}": "-".join(map(str, par_fam[f]["ft"])) if f in par_fam else "" for f in FAMILLES},
                 **{f"date_{f}": par_fam[f]["date"] if f in par_fam else "" for f in FAMILLES},
                 "id_espn": par_fam.get("espn", {}).get("id", ""), "id_apifootball": par_fam.get("apifootball", {}).get("id", "")}
        raisons = []
        if len(par_fam) < 2:
            raisons.append("SOURCE_UNIQUE : " + next(iter(par_fam)))
        if len(scores) > 1:
            raisons.append("DESACCORD_SCORE : " + ", ".join(f"{f}={m['ft'][0]}-{m['ft'][1]}" for f, m in par_fam.items()))
        if (jours[-1] - jours[0]).days > TOLERANCE_JOURS:
            raisons.append("DESACCORD_DATE : " + ", ".join(f"{f}={m['date']}" for f, m in par_fam.items()))
        if raisons:
            quarantaine.append({**ligne, "raison": " | ".join(raisons)})
            continue
        (hg, ag), = scores
        horaire = next((par_fam[f] for f in ("espn", "apifootball") if f in par_fam), None)
        jour, heure = (horaire["date"], horaire["time"]) if horaire else (par_fam["footballdata"]["date"], "")
        if heure:
            hh, mm = heure.split(":")
            heure = f"{(int(hh) + horaire['decalage_h']) % 24:02d}:{mm}:00"  # convention de data/, mesurée par source
        fd = par_fam.get("footballdata", {})
        cotes = fd.get("cotes", ("", "", "")) if all(fd.get("cotes", ("",))) else ("", "", "")
        tirs = fd.get("tirs", ("",) * 4) if all(fd.get("tirs", ("",))) else ("",) * 4
        res = "H" if hg > ag else "A" if ag > hg else "D"
        admis.append({**dict(zip(COLUMNS, [div, jour, heure, h, a, hg, ag, res, *cotes, *tirs])),
                      "familles": "+".join(f for f in FAMILLES if f in par_fam)})
    compteurs.update(admis=len(admis), quarantaine=len(quarantaine), rejets=len(rejets))
    return {"admis": admis, "quarantaine": quarantaine, "rejets": rejets, "noms": noms, "decalages_h": decalages,
            "compteurs": dict(compteurs), "familles_par_admis": dict(Counter(r["familles"] for r in admis)),
            "par_division": {d: sum(1 for r in admis if r["Division"] == d) for d in espn.LEAGUES}}


def _ecrire(path: Path, lignes: list[dict], champs: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=champs, extrasaction="ignore")
        w.writeheader()
        w.writerows(lignes)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--brut", type=Path, required=True)
    p.add_argument("--depuis", type=date.fromisoformat, default=date(2026, 9, 21))
    p.add_argument("--jusqua", type=date.fromisoformat, default=None)
    p.add_argument("--admis", type=Path, default=ROOT / "data" / "complement_resultats_2026-27.csv")
    p.add_argument("--rapport", type=Path, default=ROOT / "docs" / "resultats-2026-27")
    a = p.parse_args(argv)
    manifeste = json.loads((a.brut / "manifeste.json").read_text(encoding="utf-8"))
    capture = datetime.fromisoformat(manifeste["collecte_le"])
    jusqua = a.jusqua or capture.date()
    r = verifier(a.brut, a.depuis, jusqua, maintenant=capture)
    admis = sorted(r["admis"], key=lambda x: (x["MatchDate"], x["MatchTime"], x["Division"], x["HomeTeam"]))
    _ecrire(a.admis, admis, COLUMNS)
    _ecrire(a.rapport / "admis_sources.csv", admis, COLUMNS + ["familles"])
    _ecrire(a.rapport / "quarantaine.csv", r["quarantaine"],
            ["Division", "HomeTeam", "AwayTeam", *(f"score_{f}" for f in FAMILLES), *(f"date_{f}" for f in FAMILLES),
             "id_espn", "id_apifootball", "raison"])
    _ecrire(a.rapport / "rejets.csv", r["rejets"], ["famille", "division", "id", "raison"])
    audit = {"brut": str(a.brut.name), "collecte_le": manifeste["collecte_le"], "depuis": a.depuis.isoformat(),
             "jusqua": jusqua.isoformat(), "manifeste_sources": manifeste["sources"],
             "regle": "admis si >= 2 familles indépendantes donnent le même score final, aucune ne contredit, dates à 1 jour près",
             **{k: r[k] for k in ("compteurs", "par_division", "familles_par_admis", "decalages_h", "noms")}}
    (a.rapport / "audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: audit[k] for k in ("compteurs", "par_division", "familles_par_admis")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
