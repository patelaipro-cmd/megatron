"""EXP-009 : indicateurs d'angles morts contre poisson-v5 recalibré, pour les 3 questions.

Étape 1 : python scripts/exp009_angles.py extraire --sortie docs/experiences/EXP-009
  (une ligne par match 2008/09-2025/26 : probabilités poisson-v5, issues, 12 indicateurs, seul le passé lu)
Étape 2 : python scripts/exp009_angles.py evaluer --sortie docs/experiences/EXP-009
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from itertools import groupby
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from megatron import angles_morts as am, data, models  # noqa: E402
from megatron.data import season_of  # noqa: E402

LIGUES = ("F1", "E0", "D1", "SP1", "I1")
V5 = {"half_life": 270.0, "shrink": 2.0, "proxy": "cadres", "proxy_weight": 0.35}
SAISONS = [f"{y}/{str(y + 1)[-2:]}" for y in range(2008, 2026)]
DEV, VAL, TEST = set(SAISONS[:8]), set(SAISONS[8:12]), set(SAISONS[12:])
INDICATEURS = ["surperformance", "calendrier", "adversaire_progression", "adaptation_h2h", "fragilite_defensive",
               "rotation_fatigue", "enjeu_asymetrique", "favori_exterieur", "coups_arretes", "ecart_trompeur",
               "gestion_score", "informations_manquantes"]
Q = list(am.QUESTIONS)


def _bk_ecart(d: dict, fav_home: bool) -> float | None:
    """P(pas de victoire du favori par 2+) implicite du handicap asiatique −1,5 du favori."""
    size, hh, ha = d.get("HandiSize"), d.get("HandiHome"), d.get("HandiAway")
    if size is None or not hh or not ha or size != (-1.5 if fav_home else 1.5):
        return None
    ih, ia = 1 / hh, 1 / ha
    cover = (ih if fav_home else ia) / (ih + ia)
    return 1 - cover


def _job(args) -> list[dict]:
    division, season = args
    matches = data.load(data.CURRENT, divisions={division})
    details = am.load_details()
    rows = []
    for day, group in groupby((m for m in matches if season_of(m.day) == season), key=lambda m: m.day):
        history = [m for m in matches if m.day < day]
        fit = models.fit_maher(history, day, **V5)
        strength = {t: fit.attack[t] / fit.defence[t] for t in fit.attack}
        recent = [m for m in history if (day - m.day).days <= 730]
        for m in group:
            lh, la = fit.rates(m.home, m.away)
            fav_home = lh >= la
            fav, adv = (m.home, m.away) if fav_home else (m.away, m.home)
            lf, lad = (lh, la) if fav_home else (la, lh)
            h2h = [x for x in history if {x.home, x.away} == {fav, adv}]
            ind = am.indicateurs(recent, h2h, details, fav, adv, fav_home, day, strength)
            gf, ga = (m.home_goals, m.away_goals) if fav_home else (m.away_goals, m.home_goals)
            p = am.probabilites_questions(lf, lad)
            iss = am.issues_questions(gf, ga)
            row = {"match_id": m.match_id, "division": division, "saison": season, "favori_dom": int(fav_home),
                   "lam_fav": round(lf, 4), "lam_adv": round(lad, 4)}
            row.update({f"p_{q}": round(p[q], 6) for q in Q})
            row.update({f"issue_{q}": int(iss[q]) for q in Q})
            fs = ind.get("favori_surevalue", {})
            vals = {"surperformance": fs.get("surperformance", 0.0), "calendrier": fs.get("calendrier", 0.0)}
            vals.update({k: ind[k]["valeur"] if k in ind else 0.0 for k in INDICATEURS[2:]})
            row.update(vals)
            bk = _bk_ecart(details.get(m.match_id) or {}, fav_home)
            row["bk_ecart"] = "" if bk is None else round(bk, 6)
            rows.append(row)
    return rows


def extraire(out: Path, processus: int) -> None:
    jobs = [(d, s) for d in LIGUES for s in SAISONS]
    rows = []
    with Pool(processus) as pool:
        for r in pool.imap_unordered(_job, jobs):
            rows += r
            print(f"{r[0]['division'] if r else '?'} {r[0]['saison'] if r else ''} : {len(r)}", file=sys.stderr, flush=True)
    rows.sort(key=lambda r: r["match_id"])
    out.mkdir(parents=True, exist_ok=True)
    with (out / "variables.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} matchs", file=sys.stderr)


# --- logistique pénalisée (Newton), bibliothèque standard ---

def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[piv] = m[piv], m[c]
        for r in range(n):
            if r != c and m[r][c]:
                f = m[r][c] / m[c][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return [m[i][n] / m[i][i] for i in range(n)]


def _sig(z: float) -> float:
    return 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))


def fit_logit(x: list[list[float]], y: list[int], penal: list[float], iters: int = 25) -> list[float]:
    k = len(x[0])
    beta = [0.0] * k
    for _ in range(iters):
        g = [-penal[j] * beta[j] for j in range(k)]
        h = [[-(penal[i] if i == j else 0.0) for j in range(k)] for i in range(k)]
        for xi, yi in zip(x, y):
            p = _sig(sum(b * v for b, v in zip(beta, xi)))
            w = p * (1 - p)
            for i in range(k):
                g[i] += (yi - p) * xi[i]
                for j in range(i, k):
                    h[i][j] -= w * xi[i] * xi[j]
        for i in range(k):
            for j in range(i):
                h[i][j] = h[j][i]
        step = _solve(h, g)
        beta = [b - s for b, s in zip(beta, step)]
        if max(abs(s) for s in step) < 1e-9:
            break
    return beta


def _logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def _ll(p: float, y: int) -> float:
    return -math.log(max(p if y else 1 - p, 1e-15))


def bootstrap(diffs: list[float], level: float = 0.95, draws: int = 2000, seed: int = 1) -> dict:
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(draws))
    lo = (1 - level) / 2
    return {"n": len(diffs), "ecart": round(sum(diffs) / len(diffs), 5),
            f"ic{int(level * 100)}": [round(means[int(lo * draws)], 5), round(means[int((1 - lo) * draws) - 1], 5)]}


def evaluer(out: Path) -> dict:
    with (out / "variables.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    dev = [r for r in rows if r["saison"] in DEV]
    mean = {k: sum(float(r[k]) for r in dev) / len(dev) for k in INDICATEURS}
    sd = {k: (sum((float(r[k]) - mean[k]) ** 2 for r in dev) / len(dev)) ** 0.5 or 1.0 for k in INDICATEURS}

    def z(r, k):
        return (float(r[k]) - mean[k]) / sd[k]
    result = {"n": {"dev": len(dev), "validation": sum(r["saison"] in VAL for r in rows),
                    "test": sum(r["saison"] in TEST for r in rows)},
              "normalisation": {"moyenne": mean, "ecart_type": sd}, "questions": {}}
    for q in Q:
        y = {id(r): int(r[f"issue_{q}"]) for r in rows}
        base = {id(r): [1.0, _logit(float(r[f"p_{q}"]))] for r in rows}
        b_beta = fit_logit([base[id(r)] for r in dev], [y[id(r)] for r in dev], [0.0, 0.0])
        feats = {id(r): base[id(r)] + [z(r, k) for k in INDICATEURS] for r in rows}
        a_beta = fit_logit([feats[id(r)] for r in dev], [y[id(r)] for r in dev], [0.0, 0.0] + [1.0] * len(INDICATEURS))

        def pred(beta, xs):
            return _sig(sum(b * v for b, v in zip(beta, xs)))
        res = {"B": [round(v, 5) for v in b_beta], "A": dict(zip(["const", "logit_p"] + INDICATEURS, (round(v, 5) for v in a_beta)))}
        for role, seasons in (("dev", DEV), ("validation", VAL), ("test", TEST)):
            part = [r for r in rows if r["saison"] in seasons]
            la = [_ll(pred(a_beta, feats[id(r)]), y[id(r)]) for r in part]
            lb = [_ll(pred(b_beta, base[id(r)]), y[id(r)]) for r in part]
            lr = [_ll(float(r[f"p_{q}"]), y[id(r)]) for r in part]
            res[role] = {"log_loss_A": round(sum(la) / len(la), 5), "log_loss_B": round(sum(lb) / len(lb), 5),
                         "log_loss_v5_brut": round(sum(lr) / len(lr), 5),
                         "frequence": round(sum(y[id(r)] for r in part) / len(part), 4),
                         "A_moins_B": bootstrap([a - b for a, b in zip(la, lb)])}
            if role == "test":
                res[role]["par_ligue"] = {}
                for lg in LIGUES:
                    idx = [i for i, r in enumerate(part) if r["division"] == lg]
                    res[role]["par_ligue"][lg] = round(sum(la[i] - lb[i] for i in idx) / len(idx), 5)
                if q == "ecart":
                    bk = [(i, float(r["bk_ecart"])) for i, r in enumerate(part) if r["bk_ecart"]]
                    res[role]["info_bookmaker_handicap_1_5"] = {
                        "n": len(bk), "bookmaker": round(sum(_ll(p, y[id(part[i])]) for i, p in bk) / len(bk), 5),
                        "A": round(sum(la[i] for i, _ in bk) / len(bk), 5),
                        "B": round(sum(lb[i] for i, _ in bk) / len(bk), 5)} if bk else None
        test = [r for r in rows if r["saison"] in TEST]
        lb_t = [_ll(pred(b_beta, base[id(r)]), y[id(r)]) for r in test]
        res["angles"] = {}
        for j, k in enumerate(INDICATEURS):
            xi = {id(r): base[id(r)] + [z(r, k)] for r in rows}
            bi = fit_logit([xi[id(r)] for r in dev], [y[id(r)] for r in dev], [0.0, 0.0, 1.0])
            li = [_ll(pred(bi, xi[id(r)]), y[id(r)]) for r in test]
            bs = bootstrap([a - b for a, b in zip(li, lb_t)], level=0.99)
            res["angles"][k] = {"coef_dev": round(bi[2], 5), "test_Ai_moins_B": bs,
                                "confirme": bi[2] > 0 and bs["ic99"][1] < 0}
        v, t = res["validation"]["A_moins_B"], res["test"]["A_moins_B"]
        res["criteres"] = {"Q1": v["ic95"][1] < 0, "Q2": t["ic95"][1] < 0,
                           "Q3": sum(x < 0 for x in res["test"]["par_ligue"].values()) >= 4}
        result["questions"][q] = res
        print(q, res["criteres"], res["test"]["A_moins_B"], file=sys.stderr, flush=True)
    (out / "resultats.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("etape", choices=["extraire", "evaluer"])
    p.add_argument("--sortie", required=True)
    p.add_argument("--processus", type=int, default=4)
    a = p.parse_args()
    if a.etape == "extraire":
        extraire(Path(a.sortie), a.processus)
    else:
        evaluer(Path(a.sortie))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
