"""EXP-015 étape 2 : pilote forces d'équipes contre poisson-v5(-cal) sur les 1 752 matchs 2025/26.

Usage (racine du dépôt) :
  node scripts/experiences/EXP-015/exp014_train.js data/matches_top5_2020-2026.csv <reexec.json> <checkpoint.json>
  python scripts/experiences/EXP-015/comparer.py --checkpoint <checkpoint.json> --sortie docs/experiences/EXP-015
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from megatron import marches, marges, syndicate  # noqa: E402
from megatron.agents import poisson_1x2  # noqa: E402
from megatron.models import calibrer_1x2  # noqa: E402

DEBUT, FIN = "2025-07-01", "2026-07-01"
CLASSES = (-3, -2, -1, 0, 1, 2, 3)  # bornes : <= -3 et >= 3
EPS = 1e-6


def borne(x, lo, hi):
    return max(lo, min(hi, x))


def taux_pilote(ck, div, h, a):  # identique à rates() de exp014_train.js
    hk, ak = f"{div}|{h}", f"{div}|{a}"
    att, de = ck["attaque"], ck["defense"]
    lh = math.exp(borne(ck["intercept_domicile"].get(div, math.log(1.4)) + att.get(hk, 0) - de.get(ak, 0), -1.5, 2.8))
    la = math.exp(borne(ck["intercept_exterieur"].get(div, math.log(1.1)) + att.get(ak, 0) - de.get(hk, 0), -1.5, 2.8))
    return lh, la


def matrice(lh, la, n=12):  # comme probs() du pilote : 0..12 buts, renormalisée
    p = [math.exp(-lh)]
    q = [math.exp(-la)]
    for i in range(1, n + 1):
        p.append(p[-1] * lh / i)
        q.append(q[-1] * la / i)
    s = sum(p) * sum(q)
    return [[p[i] * q[j] / s for j in range(n + 1)] for i in range(n + 1)]


def marge7(m):
    out = defaultdict(float)
    for i, row in enumerate(m):
        for j, v in enumerate(row):
            out[max(-3, min(3, i - j))] += v
    return out


def niveaux_cote(m, cote):
    s = 1 if cote == "H" else -1
    return [sum(v for i, row in enumerate(m) for j, v in enumerate(row) if s * (i - j) >= k) for k in (1, 2, 3)]


def ll(p, y):
    p = borne(p, EPS, 1 - EPS)
    return -math.log(p) if y else -math.log(1 - p)


def bootstrap(par_jour: dict[str, list[float]], n=2000, graine=1):
    jours = sorted(par_jour)
    rng = random.Random(graine)
    tot = sum(sum(v) for v in par_jour.values()) / sum(len(v) for v in par_jour.values())
    stats = []
    for _ in range(n):
        tir = [jours[rng.randrange(len(jours))] for _ in jours]
        s = sum(sum(par_jour[j]) for j in tir)
        c = sum(len(par_jour[j]) for j in tir)
        stats.append(s / c)
    stats.sort()
    return {"ecart": round(tot, 6), "ic95": [round(stats[int(0.025 * n)], 6), round(stats[int(0.975 * n) - 1], 6)]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--sortie", type=Path, required=True)
    a = ap.parse_args(argv)
    ck = json.loads(a.checkpoint.read_text(encoding="utf-8"))
    v5 = {r["match_id"]: r for r in csv.DictReader((ROOT / "docs/experiences/EXP-009/variables.csv").open(encoding="utf-8"))}
    test = [r for r in csv.DictReader((ROOT / "data/matches_top5_2020-2026.csv").open(encoding="utf-8"))
            if DEBUT <= r["MatchDate"] < FIN]
    diffs = defaultdict(lambda: defaultdict(list))
    sommes = defaultdict(float)
    accord = 0
    for r in test:
        mid = f"{r['Division']}:{r['MatchDate']}:{r['HomeTeam']}-{r['AwayTeam']}"
        x = v5[mid]
        lf, la_ = float(x["lam_fav"]), float(x["lam_adv"])
        lh5, la5 = (lf, la_) if x["favori_dom"] == "1" else (la_, lf)
        hg, ag = int(r["FTHome"]), int(r["FTAway"])
        d = hg - ag
        res = "H" if d > 0 else "A" if d < 0 else "D"
        mp, m5 = matrice(*taux_pilote(ck, r["Division"], r["HomeTeam"], r["AwayTeam"])), matrice(lh5, la5)
        # C1 : 1X2
        pp = marge7(mp)
        p1 = {"H": sum(v for k, v in pp.items() if k > 0), "D": pp[0], "A": sum(v for k, v in pp.items() if k < 0)}
        p5 = calibrer_1x2(poisson_1x2(lh5, la5), *syndicate.CALIBRATION_1X2)
        c1 = (-math.log(max(p1[res], EPS)), -math.log(max(p5[res], EPS)))
        # C2 : marge 7 classes, v5 brut
        p57 = marge7(m5)
        k = max(-3, min(3, d))
        c2 = (-math.log(max(pp[k], EPS)), -math.log(max(p57[k], EPS)))
        # C3 : favori de v5, niveaux v5 recalibrés EXP-012 vs pilote
        fav5 = "H" if lh5 >= la5 else "A"
        ecart5 = d if fav5 == "H" else -d
        n5 = syndicate.niveaux(lh5, la5)["probabilites"]
        n5 = [n5[kk] for kk in syndicate.NIVEAUX]
        npil5 = niveaux_cote(mp, fav5)
        # information : favori du pilote, v5 brut vs pilote
        favp = "H" if niveaux_cote(mp, "H")[0] >= niveaux_cote(mp, "A")[0] else "A"
        accord += favp == fav5
        ecartp = d if favp == "H" else -d
        nb5p, npp = niveaux_cote(m5, favp), niveaux_cote(mp, favp)
        jour = r["MatchDate"]
        lignes = {"C1_1x2_pilote_moins_v5cal": c1[0] - c1[1], "C2_marge7_pilote_moins_v5brut": c2[0] - c2[1]}
        for i, nom in enumerate(("victoire", "2plus", "3plus")):
            y5, yp = ecart5 >= i + 1, ecartp >= i + 1
            lignes[f"C3_{nom}_favori_v5_pilote_moins_v5cal"] = ll(npil5[i], y5) - ll(n5[i], y5)
            lignes[f"info_{nom}_favori_pilote_pilote_moins_v5brut"] = ll(npp[i], yp) - ll(nb5p[i], yp)
            sommes[f"{nom}_favori_v5:pilote"] += ll(npil5[i], y5)
            sommes[f"{nom}_favori_v5:v5cal"] += ll(n5[i], y5)
            sommes[f"{nom}_favori_pilote:pilote"] += ll(npp[i], yp)
            sommes[f"{nom}_favori_pilote:v5brut"] += ll(nb5p[i], yp)
        sommes["1x2:pilote"] += c1[0]; sommes["1x2:v5cal"] += c1[1]
        sommes["marge7:pilote"] += c2[0]; sommes["marge7:v5brut"] += c2[1]
        for nom, v in lignes.items():
            diffs[nom][jour].append(v)
    n = len(test)
    out = {"n": n, "favoris_identiques": accord, "logloss": {k: round(v / n, 6) for k, v in sorted(sommes.items())},
           "ecarts": {k: bootstrap(v) for k, v in diffs.items()},
           "bootstrap": "apparié par journée (date), 2 000 tirages, graine 1"}
    out["pilote_meilleur"] = {k: v["ic95"][1] < 0 for k, v in out["ecarts"].items() if not k.startswith("info")}
    a.sortie.mkdir(parents=True, exist_ok=True)
    (a.sortie / "comparaison.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
