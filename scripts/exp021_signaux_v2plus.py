"""EXP-021 : entraînement exploratoire d'un signal de victoires courtes.

Le protocole est fixé dans docs/experiences/EXP-021-signaux-v2plus.md.
Ce script ne modifie ni les coefficients de production ni la mémoire du registre.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict, deque
from itertools import groupby
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from megatron import data, marches, syndicate  # noqa: E402

VARIABLES = ROOT / "docs/experiences/EXP-009/variables.csv"
TRAIN = {f"{y}/{str(y+1)[-2:]}" for y in range(2008, 2016)}
VALIDATION = {f"{y}/{str(y+1)[-2:]}" for y in range(2016, 2020)}
TEST = {f"{y}/{str(y+1)[-2:]}" for y in range(2020, 2026)}
L2 = 5.0


def marge_2plus(lam_fav: float, lam_adv: float) -> float:
    """P(F-A >= 2) sous Poisson indépendant (équivalent aux marges Poisson du moteur)."""
    n = 45
    pf, pa = [math.exp(-lam_fav)], [math.exp(-lam_adv)]
    for i in range(1, n + 1):
        pf.append(pf[-1] * lam_fav / i)
        pa.append(pa[-1] * lam_adv / i)
    tail = [0.0] * (n + 2)
    for i in range(n, -1, -1):
        tail[i] = tail[i + 1] + pf[i]
    return sum(pa[a] * tail[a + 2] for a in range(n - 1))


def cohortes(matches: list[data.Match], variables: dict[str, dict]) -> list[dict]:
    """Aucun résultat du jour J ne peut entrer dans le signal de J."""
    recentes = defaultdict(lambda: deque(maxlen=5))
    out = []
    for jour, groupe in groupby(matches, key=lambda m: m.day):
        matchs = list(groupe)
        for m in matchs:
            v = variables.get(m.match_id)
            if v is None:
                continue
            fav_dom = v["favori_dom"] == "1"
            favori = m.home if fav_dom else m.away
            forme = recentes[(m.division, favori)]
            victoires = [x for x in forme if x > 0]
            if len(forme) != 5 or len(victoires) < 3:
                continue
            ratio = sum(x >= 2 for x in victoires) / len(victoires)
            p0 = marge_2plus(float(v["lam_fav"]), float(v["lam_adv"]))
            p = marches.platt(p0, *syndicate.CALIBRATION_NIVEAUX["victoire_par_2_ou_plus"])["oui"]
            diff = (m.home_goals - m.away_goals) if fav_dom else (m.away_goals - m.home_goals)
            out.append({"id": m.match_id, "saison": v["saison"], "ligue": m.division,
                        "ratio": ratio, "p": p, "y": int(diff >= 2)})
        # Après avoir construit toutes les prédictions du jour, révéler les scores.
        for m in matchs:
            recentes[(m.division, m.home)].append(m.home_goals - m.away_goals)
            recentes[(m.division, m.away)].append(m.away_goals - m.home_goals)
    return out


def logit(p: float) -> float:
    p = min(max(p, 1e-10), 1 - 1e-10)
    return math.log(p / (1 - p))


def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-max(-40, min(40, x))))


def entrainer(rows: list[dict], moyenne: float) -> float:
    """Newton à une variable avec pénalité fixe, sur le réglage seulement."""
    beta = 0.0
    for _ in range(40):
        grad = L2 * beta
        hessian = L2
        for r in rows:
            x = r["ratio"] - moyenne
            p = sigmoid(logit(r["p"]) + beta * x)
            grad += (p - r["y"]) * x
            hessian += p * (1 - p) * x * x
        suivant = beta - grad / hessian
        if abs(suivant - beta) < 1e-9:
            return suivant
        beta = suivant
    return beta


def mesures(rows: list[dict], beta: float, moyenne: float) -> dict:
    if not rows:
        return {"n": 0}
    scores = {"reference": [0.0, 0.0], "candidat": [0.0, 0.0]}
    for r in rows:
        y, p = r["y"], r["p"]
        adj = sigmoid(logit(p) + beta * (r["ratio"] - moyenne))
        for nom, x in (("reference", p), ("candidat", adj)):
            x = min(max(x, 1e-12), 1 - 1e-12)
            scores[nom][0] += -(y * math.log(x) + (1-y) * math.log(1-x))
            scores[nom][1] += (y - x)**2
    return {"n": len(rows), "frequence_observee": round(sum(r["y"] for r in rows) / len(rows), 6),
            **{nom: {"log_loss": round(v[0] / len(rows), 6), "brier": round(v[1] / len(rows), 6)}
               for nom, v in scores.items()},
            "delta_candidat_moins_reference": {
                "log_loss": round((scores["candidat"][0] - scores["reference"][0]) / len(rows), 6),
                "brier": round((scores["candidat"][1] - scores["reference"][1]) / len(rows), 6)}}


def executer() -> dict:
    if syndicate.CALIBRATION_NIVEAUX is None:
        raise ValueError("probabilités EXP-012 non disponibles")
    with VARIABLES.open(encoding="utf-8", newline="") as h:
        variables = {r["match_id"]: r for r in csv.DictReader(h)}
    rows = cohortes(data.load(data.CURRENT), variables)
    train = [r for r in rows if r["saison"] in TRAIN]
    valid = [r for r in rows if r["saison"] in VALIDATION]
    test = [r for r in rows if r["saison"] in TEST]
    if not train or not valid or not test:
        raise ValueError("cohorte historique incomplète")
    mean = sum(r["ratio"] for r in train) / len(train)
    beta = entrainer(train, mean)
    return {"experience": "EXP-021", "statut": "EXPLORATOIRE_NON_DEPLOYE",
            "apprentissage_effectue": True, "parametre_appris_non_deploye": round(beta, 6),
            "ratio_moyen_train": round(mean, 6),
            "periode_train": "2008/09-2015/16", "periode_validation": "2016/17-2019/20",
            "periode_test": "2020/21-2025/26 (déjà utilisée dans le projet ; non indépendante)",
            "cohortes": {"train": mesures(train, beta, mean),
                         "validation": mesures(valid, beta, mean), "test": mesures(test, beta, mean)},
            "limites": ["championnats des cinq ligues seulement ; pas de coupes ni écarts de divisions",
                        "aucune composition/rotation/absence datée dans ce test",
                        "un match isolé, notamment Béthune–Nancy, ne valide pas un signal",
                        "coefficients SYNDICATE inchangés ; nouvelle cohorte indépendante requise"]}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sortie", type=Path, help="rapport JSON hors du registre")
    a = p.parse_args(argv)
    resultats = executer()
    texte = json.dumps(resultats, indent=2, ensure_ascii=False) + "\n"
    if a.sortie:
        a.sortie.parent.mkdir(parents=True, exist_ok=True)
        a.sortie.write_text(texte, encoding="utf-8")
    print(texte, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
