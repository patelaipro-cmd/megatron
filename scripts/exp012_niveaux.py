"""EXP-012 : niveaux de victoire SYNDICATE (victoire, 2+, 3+) — fréquences, poisson-v5 brut, Platt.

python scripts/exp012_niveaux.py --sortie docs/experiences/EXP-012
Protocole : docs/experiences/EXP-012-niveaux-victoire.md (figé avant exécution).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from megatron import data, marches, marges  # noqa: E402

VARIABLES = Path("docs/experiences/EXP-009/variables.csv")
SAISONS = [f"{y}/{str(y + 1)[-2:]}" for y in range(2008, 2026)]
REGLAGE, CALIB, TEST = set(SAISONS[:8]), set(SAISONS[8:12]), set(SAISONS[12:])
NIVEAUX = {"victoire_simple": 1, "victoire_par_2_ou_plus": 2, "victoire_par_3_ou_plus": 3}
EPS = 1e-15


def ll(p: float, y: int) -> float:
    return -math.log(max(p if y else 1 - p, EPS))


def charger() -> list[dict]:
    scores = {m.match_id: (m.home_goals, m.away_goals) for m in data.load(data.CURRENT)}
    rows, exclus = [], 0
    with VARIABLES.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            s = scores.get(r["match_id"])
            if s is None:
                exclus += 1
                continue
            fav_dom = r["favori_dom"] == "1"
            lf, la = float(r["lam_fav"]), float(r["lam_adv"])
            lh, lam_a = (lf, la) if fav_dom else (la, lf)
            side = "H" if fav_dom else "A"
            calc = marges.calculer(lh, lam_a)["niveaux"][side]
            ecart = (s[0] - s[1]) if fav_dom else (s[1] - s[0])
            rows.append({"match_id": r["match_id"], "ligue": r["division"], "saison": r["saison"],
                         "jour": r["match_id"].split(":")[1],
                         **{f"p_{n}": calc[n] for n in NIVEAUX}, **{f"y_{n}": int(ecart >= k) for n, k in NIVEAUX.items()}})
    rows.sort(key=lambda x: (x["jour"], x["match_id"]))
    return rows, exclus


def frequences(rows: list[dict]) -> None:
    """F : part des matchs antérieurs (jour strictement antérieur) de la ligue, sinon toutes ligues."""
    cumul = {}  # (ligue|*, niveau) -> [n, oui]
    i = 0
    while i < len(rows):
        j = i
        while j < len(rows) and rows[j]["jour"] == rows[i]["jour"]:
            j += 1
        for r in rows[i:j]:
            for n in NIVEAUX:
                c = cumul.get((r["ligue"], n), [0, 0])
                g = cumul.get(("*", n), [0, 0])
                src = c if c[0] >= 200 else g
                r[f"f_{n}"] = (src[1] + 1) / (src[0] + 2) if src[0] else 0.5
        for r in rows[i:j]:
            for n in NIVEAUX:
                for key in ((r["ligue"], n), ("*", n)):
                    c = cumul.setdefault(key, [0, 0])
                    c[0] += 1
                    c[1] += r[f"y_{n}"]
        i = j


def calibration(pairs: list[tuple[float, int]]) -> list[dict]:
    out = []
    for b in range(10):
        sel = [(p, y) for p, y in pairs if b / 10 <= p < (b + 1) / 10 or (b == 9 and p == 1)]
        if sel:
            out.append({"tranche": f"{b / 10:.1f}-{(b + 1) / 10:.1f}", "n": len(sel),
                        "p_moyenne": round(sum(p for p, _ in sel) / len(sel), 4),
                        "frequence": round(sum(y for _, y in sel) / len(sel), 4)})
    return out


def resume(rows: list[dict], n: str, mod: str) -> dict:
    pairs = [(r[f"{mod}_{n}"], r[f"y_{n}"]) for r in rows]
    haut = [(p, y) for p, y in pairs if p >= 0.60]
    return {"n": len(pairs), "log_loss": round(sum(ll(p, y) for p, y in pairs) / len(pairs), 5),
            "brier": round(sum((p - y) ** 2 for p, y in pairs) / len(pairs), 5),
            "frequence": round(sum(y for _, y in pairs) / len(pairs), 4),
            "p_moyenne": round(sum(p for p, _ in pairs) / len(pairs), 4),
            "tranche_p60": {"n": len(haut), "frequence": round(sum(y for _, y in haut) / len(haut), 4) if haut else None,
                            "p_moyenne": round(sum(p for p, _ in haut) / len(haut), 4) if haut else None},
            "calibration": calibration(pairs)}


def bootstrap(rows: list[dict], n: str, a: str, b: str, tirages: int = 2000, graine: int = 1) -> dict:
    grappes: dict[tuple, list[float]] = {}
    for r in rows:
        grappes.setdefault((r["ligue"], r["saison"]), []).append(ll(r[f"{a}_{n}"], r[f"y_{n}"]) - ll(r[f"{b}_{n}"], r[f"y_{n}"]))
    g = [(sum(v), len(v)) for v in grappes.values()]
    rng = random.Random(graine)
    stats = []
    for _ in range(tirages):
        tir = [g[rng.randrange(len(g))] for _ in g]
        stats.append(sum(s for s, _ in tir) / sum(k for _, k in tir))
    stats.sort()
    moyenne = sum(s for s, _ in g) / sum(k for _, k in g)
    return {"ecart": round(moyenne, 5), "ic95": [round(stats[int(0.025 * tirages)], 5), round(stats[int(0.975 * tirages) - 1], 5)],
            "grappes": len(g)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", required=True, type=Path)
    a = ap.parse_args()
    sha = hashlib.sha256(VARIABLES.read_bytes()).hexdigest()
    rows, exclus = charger()
    frequences(rows)
    calib = [r for r in rows if r["saison"] in CALIB]
    test = [r for r in rows if r["saison"] in TEST]
    out = {"variables_sha256": sha, "matchs": len(rows), "exclus_sans_score": exclus,
           "effectifs": {"reglage": sum(r["saison"] in REGLAGE for r in rows), "calibration": len(calib), "test": len(test)},
           "niveaux": {}}
    for n in NIVEAUX:
        pa, pb = marches.fit_platt([(r[f"p_{n}"], r[f"y_{n}"]) for r in calib])
        for r in rows:
            r[f"c_{n}"] = marches.platt(r[f"p_{n}"], pa, pb)["oui"]
        ligues = {}
        for lg in sorted({r["ligue"] for r in test}):
            sub = [r for r in test if r["ligue"] == lg]
            ligues[lg] = {m: resume(sub, n, m)["log_loss"] for m in ("f", "p", "c")}
        res_c = resume(test, n, "c")
        n3 = all(abs(t["frequence"] - t["p_moyenne"]) <= 0.03 for t in res_c["calibration"] if t["n"] >= 500)
        n1 = bootstrap(test, n, "c", "f")
        n2 = sum(v["c"] < v["f"] for v in ligues.values())
        out["niveaux"][n] = {
            "platt": {"a": round(pa, 6), "b": round(pb, 6)},
            "test": {"F": resume(test, n, "f"), "B": resume(test, n, "p"), "C": res_c},
            "calibration_periode": {m: resume(calib, n, m)["log_loss"] for m in ("f", "p", "c")},
            "C_moins_F": n1, "B_moins_F": bootstrap(test, n, "p", "f"), "C_moins_B": bootstrap(test, n, "c", "p"),
            "ligues_test": ligues, "ligues_C_meilleur_que_F": n2,
            "criteres": {"N1": n1["ic95"][1] < 0, "N2": n2 >= 4, "N3": n3},
        }
        out["niveaux"][n]["valide"] = all(out["niveaux"][n]["criteres"].values())
    a.sortie.mkdir(parents=True, exist_ok=True)
    (a.sortie / "resultats.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({n: {"criteres": v["criteres"], "C_moins_F": v["C_moins_F"], "B_moins_F": v["B_moins_F"],
                          "platt": v["platt"], "ll": {k: v["test"][k]["log_loss"] for k in "FBC"}}
                      for n, v in out["niveaux"].items()}, indent=1, ensure_ascii=False))
    print("matchs", out["matchs"], "exclus", exclus, out["effectifs"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
