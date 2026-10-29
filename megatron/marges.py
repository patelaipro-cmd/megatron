"""Marges de victoire explicites ; Poisson brut expérimental, non calibré."""
from __future__ import annotations

import math

# marché → côté, écart minimal ; aucune confusion avec le TOTAL de buts.
MARGES = {"H_MARGE_2PLUS": ("H", 2), "H_MARGE_3PLUS": ("H", 3),
          "A_MARGE_2PLUS": ("A", 2), "A_MARGE_3PLUS": ("A", 3)}
VERSION = "poisson-independant-marges-brut-v0"


def resoudre(score, market: str) -> str:
    """Score réglementaire explicite → oui/non pour l'équipe désignée."""
    if market not in MARGES:
        raise ValueError(f"marché de marge inconnu : {market!r}")
    if not isinstance(score, (list, tuple)) or len(score) != 2:
        raise ValueError("score attendu : deux entiers positifs ou nuls")
    h, a = score
    if any(type(x) is not int or x < 0 for x in (h, a)):
        raise ValueError("score attendu : deux entiers positifs ou nuls")
    side, minimum = MARGES[market]
    margin = h - a if side == "H" else a - h
    return "oui" if margin >= minimum else "non"


def calculer(lam_home: float, lam_away: float) -> dict:
    """Deux intensités fournies par l'appelant ; aucune donnée collectée ici.

    Domaine numérique volontairement borné à [0, 10]. Les scores 0..60
    couvrent la loi à moins de 1e-12 de masse manquante sur ce domaine.
    Les événements utilisent tous la même matrice, puis la même normalisation.
    """
    for value in (lam_home, lam_away):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 10:
            raise ValueError("intensités finies attendues entre 0 et 10")

    def pmf(lam):
        out = [math.exp(-lam)]
        for k in range(1, 61):
            out.append(out[-1] * lam / k)
        return out

    ph, pa = pmf(lam_home), pmf(lam_away)
    mass = math.fsum(ph) * math.fsum(pa)
    probs = {"H": 0.0, "D": 0.0, "A": 0.0}
    margins = {key: 0.0 for key in MARGES}
    for h, hp in enumerate(ph):
        for a, ap in enumerate(pa):
            p = hp * ap / mass
            probs["H" if h > a else "A" if a > h else "D"] += p
            for market, (side, minimum) in MARGES.items():
                if (h - a if side == "H" else a - h) >= minimum:
                    margins[market] += p
    return {"version": VERSION, "statut": "EXPERIMENTAL_NON_CALIBRE",
            "intensites_fournies": {"H": lam_home, "A": lam_away},
            "1X2": probs,
            "niveaux": {side: {"victoire_simple": probs[side],
                               "victoire_par_2_ou_plus": margins[f"{side}_MARGE_2PLUS"],
                               "victoire_par_3_ou_plus": margins[f"{side}_MARGE_3PLUS"]}
                         for side in ("H", "A")},
            "marches": {key: {"oui": p, "non": 1 - p} for key, p in margins.items()},
            "masse_tronquee": max(0.0, 1 - mass),
            "limites": ["intensités fournies, provenance non vérifiée ici", "Poisson indépendant, non calibré pour les marges",
                        "aucune activation dans prevoir, aucun signal GO"]}
