"""EXP-013 : compositions (Transfermarkt) sur l'historique, contre poisson-v5-cal et contre les cotes.
Protocole figé : docs/experiences/EXP-013-absences.md.

Usage : python scripts/exp013_compos.py --tm <externe/transfermarkt/historique> --v5 docs/experiences/EXP-013/v5 \
          --sortie docs/experiences/EXP-013
(--v5 : sortie de grille_multi --configs "v5=270,2,0,moyenne,cadres,0.35" sur 2013/14-2025/26).
Valeurs des titulaires (du jour et de la fenêtre) prises à la dernière valorisation datée avant le jour du match.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import json
import math
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from exp010_calibration import _solve, calibrate  # noqa: E402
from megatron import backtest, data, xg  # noqa: E402
from megatron.agents import StatsAgent  # noqa: E402
from megatron.ledger import OUTCOMES  # noqa: E402

LIGUES = {"GB1": "E0", "ES1": "SP1", "IT1": "I1", "L1": "D1", "FR1": "F1"}
saisons = lambda a, b: {f"{x}/{str(x + 1)[-2:]}" for x in range(a, b + 1)}  # noqa: E731
PERIODES = {"dev": saisons(2013, 2018), "validation": saisons(2019, 2021), "test": saisons(2022, 2025)}
FENETRE, MINI = 10, 3


def lire(dossier: Path, table: str):
    with gzip.open(dossier / f"{table}.csv.gz", "rt", encoding="utf-8", newline="") as fh:
        yield from csv.DictReader(fh)


def indicateurs(tm: Path, matchs: list[data.Match]) -> tuple[dict, dict]:
    """{match_id de data/: (x1, x2)} et un compte rendu de liaison."""
    jeux = {r["game_id"]: r for r in lire(tm, "games") if r["competition_id"] in LIGUES}
    lignes = [{"division": LIGUES[g["competition_id"]], "jour": date.fromisoformat(g["date"]), "dom": g["home_club_name"],
               "ext": g["away_club_name"], "bd": int(float(g["home_club_goals"] or -1)),
               "be": int(float(g["away_club_goals"] or -1)), "xg": gid} for gid, g in jeux.items() if g["home_club_goals"]]
    lie, liaison = xg.relier(lignes, matchs)  # « xg » porte ici l'identifiant Transfermarkt
    titulaires = defaultdict(lambda: defaultdict(set))
    for r in lire(tm, "game_lineups"):
        if r["type"] == "starting_lineup" and r["game_id"] in jeux:
            titulaires[r["game_id"]][r["club_id"]].add(r["player_id"])
    minutes = defaultdict(lambda: defaultdict(dict))
    for r in lire(tm, "appearances"):
        if r["game_id"] in jeux and r["minutes_played"]:
            minutes[r["game_id"]][r["player_club_id"]][r["player_id"]] = int(float(r["minutes_played"]))
    valeurs = defaultdict(list)
    for r in lire(tm, "player_valuations"):
        if r["market_value_in_eur"]:
            valeurs[r["player_id"]].append((r["date"][:10], float(r["market_value_in_eur"])))
    for v in valeurs.values():
        v.sort()

    def valeur(joueur: str, jour: str) -> float:
        v = valeurs.get(joueur)
        if not v:
            return 0.0
        i = bisect.bisect_left(v, (jour, -1.0)) - 1  # strictement avant le jour
        return v[i][1] if i >= 0 else 0.0

    par_club = defaultdict(list)  # club -> [(jour, game_id)]
    for gid, g in jeux.items():
        for c in (g["home_club_id"], g["away_club_id"]):
            par_club[c].append((g["date"], gid))
    for v in par_club.values():
        v.sort()

    def cote(gid: str, club: str, jour: str) -> tuple[float, float] | None:
        xi = titulaires[gid].get(club, set())
        if len(xi) != 11:
            return None
        passe = [g for j, g in par_club[club] if j < jour and len(titulaires[g].get(club, ())) == 11][-FENETRE:]
        if len(passe) < MINI:
            return None
        val_jour = sum(valeur(p, jour) for p in xi)
        val_passe = sum(sum(valeur(p, jour) for p in titulaires[g][club]) for g in passe) / len(passe)
        mins = defaultdict(int)
        for g in passe:
            for p, m in minutes[g].get(club, {}).items():
                mins[p] += m
        return math.log((val_jour + 1) / (val_passe + 1)), sum(m / 900 for p, m in mins.items() if p not in xi)

    out, sans = {}, 0
    for mid, gid in lie.items():
        g = jeux[gid]
        h, a = cote(gid, g["home_club_id"], g["date"]), cote(gid, g["away_club_id"], g["date"])
        if h is None or a is None:
            sans += 1
            out[mid] = (0.0, 0.0)
        else:
            out[mid] = (h[0] - a[0], h[1] - a[1])
    return out, {**liaison, "indicateurs_a_zero": sans}


def ajuste(p: dict, x: tuple, th: list[float]) -> dict:
    z = {"H": math.log(max(p["H"], 1e-12)) + th[0] * x[0] + th[1] * x[1], "D": math.log(max(p["D"], 1e-12)),
         "A": math.log(max(p["A"], 1e-12)) + th[2] * x[0] + th[3] * x[1]}
    m = max(z.values())
    e = {o: math.exp(v - m) for o, v in z.items()}
    s = sum(e.values())
    return {o: e[o] / s for o in OUTCOMES}


def ajuster(rows: list[dict], base: str, iters: int = 30) -> list[float]:
    """Newton, log-vraisemblance multinomiale concave en θ."""
    th = [0.0] * 4
    for _ in range(iters):
        g, h = [0.0] * 4, [[0.0] * 4 for _ in range(4)]
        for r in rows:
            q = ajuste(r[base], r["x"], th)
            dz = {"H": (r["x"][0], r["x"][1], 0.0, 0.0), "D": (0.0,) * 4, "A": (0.0, 0.0, r["x"][0], r["x"][1])}
            moy = [sum(q[o] * dz[o][k] for o in OUTCOMES) for k in range(4)]
            for k in range(4):
                g[k] += dz[r["issue"]][k] - moy[k]
                for j in range(4):
                    h[k][j] -= sum(q[o] * dz[o][k] * dz[o][j] for o in OUTCOMES) - moy[k] * moy[j]
        pas = _solve(h, g)
        th = [t - s for t, s in zip(th, pas)]
        if max(abs(s) for s in pas) < 1e-10:
            break
    return th


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tm", type=Path, required=True)
    p.add_argument("--v5", type=Path, required=True)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args(argv)
    matchs = data.load(data.CURRENT)
    x, liaison = indicateurs(a.tm, [m for m in matchs if data.season_of(m.day) <= "2025/26"])
    print(liaison, flush=True)
    b, c = StatsAgent.CALIBRATION[0], StatsAgent.CALIBRATION[1:]
    d = {k: [] for k in PERIODES}
    for lg in LIGUES.values():
        for r in backtest.read_predictions(a.v5 / lg / "predictions.csv"):
            if r["v5"] and r["match_id"] in x:
                for k, s in PERIODES.items():
                    if r["saison"] in s:
                        d[k].append({"ligue": lg, "issue": r["issue"], "x": x[r["match_id"]],
                                     "S": calibrate(r["v5"], b, c), "K": r["bookmaker"]})
    th_s = ajuster(d["dev"], "S")
    th_k = ajuster([r for r in d["dev"] if r["K"]], "K")
    out = {"protocole": "docs/experiences/EXP-013-absences.md", "liaison": liaison,
           "n": {k: len(v) for k, v in d.items()},
           "theta_S": [round(t, 6) for t in th_s], "theta_K": [round(t, 6) for t in th_k],
           "ordre_theta": ["H·x1 (valeur)", "H·x2 (habitués absents)", "A·x1", "A·x2"]}
    for k, rows in d.items():
        for r in rows:
            r["S+"] = ajuste(r["S"], r["x"], th_s)
            r["K+"] = ajuste(r["K"], r["x"], th_k) if r["K"] else None
        rk = [r for r in rows if r["K"]]
        out[k] = {"S+_moins_S": backtest.paired_bootstrap(rows, "S+", "S"),
                  "K+_moins_K": backtest.paired_bootstrap(rk, "K+", "K"),
                  "par_ligue_K": {lg: backtest.paired_bootstrap([r for r in rk if r["ligue"] == lg], "K+", "K")
                                  for lg in LIGUES.values()},
                  "par_ligue_S": {lg: backtest.paired_bootstrap([r for r in rows if r["ligue"] == lg], "S+", "S")
                                  for lg in LIGUES.values()}}
    v, t = out["validation"], out["test"]
    out["criteres"] = {"A1": v["S+_moins_S"]["ic95"][1] < 0 and t["S+_moins_S"]["ic95"][1] < 0,
                       "A2": v["K+_moins_K"]["ic95"][1] < 0 and t["K+_moins_K"]["ic95"][1] < 0
                       and sum(z["ecart"] < 0 for z in t["par_ligue_K"].values()) >= 3}
    a.sortie.mkdir(parents=True, exist_ok=True)
    (a.sortie / "resultats.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("n", "theta_S", "theta_K", "criteres")}, ensure_ascii=False))
    for k in PERIODES:
        print(k, out[k]["S+_moins_S"], out[k]["K+_moins_K"], {lg: z["ecart"] for lg, z in out[k]["par_ligue_K"].items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
