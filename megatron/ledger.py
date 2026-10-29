"""Registre des prévisions avant match et des résultats observés.

Règles anti-fuite temporelle :
- une prévision doit être enregistrée strictement avant le coup d'envoi ;
- une prévision enregistrée n'est jamais modifiée (une nouvelle version de
  modèle crée une nouvelle prévision, pas un remplacement) ;
- un résultat ne peut être observé qu'après le coup d'envoi.
"""

from __future__ import annotations

import math
from datetime import datetime

from .store import MemoryStore, now_utc, parse_dt

OUTCOMES = ("H", "D", "A")  # domicile, nul, extérieur
# marché → issues ; 2+ et 3+ : au moins 2 (ou 3) buts dans le match (EXP-006)
MARKETS = {"1X2": OUTCOMES, "2+": ("oui", "non"), "3+": ("oui", "non")}
DOMAIN = "performances"
EPS = 1e-15


class TemporalLeakError(ValueError):
    """Une prévision ou un résultat viole l'ordre chronologique."""


class Ledger:
    def __init__(self, store: MemoryStore):
        self.store = store

    def predict(
        self,
        match_id: str,
        kickoff: str | datetime,
        probs: dict[str, float],
        *,
        model_version: str,
        source: str,
        recorded_at: str | datetime | None = None,
        data_cutoff: str | datetime | None = None,
        market: str = "1X2",
    ):
        kickoff_dt = parse_dt(kickoff)
        rec_dt = parse_dt(recorded_at or now_utc())
        if rec_dt >= kickoff_dt:
            raise TemporalLeakError(f"{match_id} : prévision enregistrée après le coup d'envoi")
        if data_cutoff and parse_dt(data_cutoff) >= kickoff_dt:
            raise TemporalLeakError(f"{match_id} : données utilisées postérieures au coup d'envoi")
        if market not in MARKETS:
            raise ValueError(f"marché inconnu : {market!r}")
        if set(probs) != set(MARKETS[market]):
            raise ValueError(f"probabilités attendues pour {MARKETS[market]}, reçu {sorted(probs)}")
        if any(not math.isfinite(p) or p < 0 or p > 1 for p in probs.values()) or abs(sum(probs.values()) - 1) > 1e-6:
            raise ValueError(f"{match_id} : probabilités invalides {probs}")
        key = pred_key(match_id, model_version, market)
        if self.store.active(DOMAIN, key):
            raise ValueError(f"prévision déjà enregistrée : {key}")
        return self.store.record(
            DOMAIN, key,
            {"match_id": match_id, "kickoff": kickoff_dt.isoformat(), "probs": probs,
             "model_version": model_version, "market": market,
             "data_cutoff": parse_dt(data_cutoff).isoformat() if data_cutoff else None},
            source=source, status="verifie", recorded_at=rec_dt, supersede=False,
        )

    def result(self, match_id: str, outcome: str, *, source: str,
               observed_at: str | datetime | None = None, correction: bool = False,
               goals: tuple[int, int] | None = None):
        """Un seul résultat actif par match ; le remplacer exige ``correction`` (historique gardé)."""
        if outcome not in OUTCOMES:
            raise ValueError(f"issue inconnue : {outcome!r}")
        current = self.store.active(DOMAIN, f"result:{match_id}")
        if current and not correction:
            raise ValueError(f"{match_id} : résultat déjà saisi ({current[-1].value['outcome']}), "
                             "correction explicite requise")
        preds = self._predictions(match_id)
        obs_dt = parse_dt(observed_at or now_utc())
        for p in preds:
            if obs_dt <= parse_dt(p.value["kickoff"]):
                raise TemporalLeakError(f"{match_id} : résultat daté avant le coup d'envoi")
        value = {"match_id": match_id, "outcome": outcome}
        if goals is not None:
            home, away = (int(g) for g in goals)
            if home < 0 or away < 0 or outcome != ("H" if home > away else "A" if away > home else "D"):
                raise ValueError(f"{match_id} : score {home}-{away} incohérent avec l'issue {outcome}")
            value["score"] = [home, away]
        return self.store.record(DOMAIN, f"result:{match_id}", value,
                                 source=source, status="verifie", observed_at=obs_dt)

    def _predictions(self, match_id: str | None = None, model_version: str | None = None,
                     market: str | None = None):
        out = []
        for e in self.store.active(DOMAIN):
            if not e.key.startswith("pred:"):
                continue
            if match_id and e.value["match_id"] != match_id:
                continue
            if model_version and e.value["model_version"] != model_version:
                continue
            if market and market_of(e.value) != market:
                continue
            out.append(e)
        return out

    def evaluate(self, model_version: str, bins: int = 5, market: str = "1X2") -> dict:
        """Brier multiclasse, log-loss et calibration sur les matchs résolus."""
        results = self.outcomes(market)
        pairs = [(p.value["probs"], results[p.value["match_id"]])
                 for p in self._predictions(model_version=model_version, market=market)
                 if p.value["match_id"] in results]
        return {"model_version": model_version, "market": market, **score(pairs, bins, MARKETS[market])}

    def outcomes(self, market: str = "1X2") -> dict[str, str]:
        """match_id → issue du marché ; un marché de buts exige un score saisi."""
        out = {}
        for e in self.store.active(DOMAIN):
            if not e.key.startswith("result:"):
                continue
            if market == "1X2":
                out[e.value["match_id"]] = e.value["outcome"]
            elif e.value.get("score"):
                out[e.value["match_id"]] = "oui" if sum(e.value["score"]) >= int(market[0]) else "non"
        return out


def pred_key(match_id: str, model_version: str, market: str = "1X2") -> str:
    """Clé du registre ; le 1X2 garde la forme d'avant les marchés de buts."""
    return f"pred:{match_id}:{model_version}" if market == "1X2" else f"pred:{match_id}:{market}:{model_version}"


def market_of(value: dict) -> str:
    return value.get("market", "1X2")  # prévisions antérieures aux marchés : 1X2


def rps(probs: dict[str, float], outcome: str, outcomes: tuple[str, ...] = OUTCOMES) -> float:
    """Ranked probability score pour des issues ordonnées (H < D < A par défaut)."""
    cum_p = cum_o = total = 0.0
    for o in outcomes[:-1]:
        cum_p += probs[o]
        cum_o += o == outcome
        total += (cum_p - cum_o) ** 2
    return total / (len(outcomes) - 1)


def score(pairs: list[tuple[dict[str, float], str]], bins: int = 5,
          outcomes: tuple[str, ...] = OUTCOMES) -> dict:
    """Brier multiclasse, log-loss, RPS et calibration de couples (probabilités, issue)."""
    n = len(pairs)
    if n == 0:
        return {"n": 0, "brier": None, "log_loss": None, "rps": None, "calibration": []}
    brier = sum(sum((probs[o] - (o == y)) ** 2 for o in outcomes) for probs, y in pairs) / n
    log_loss = -sum(math.log(max(probs[y], EPS)) for probs, y in pairs) / n
    mean_rps = sum(rps(probs, y, outcomes) for probs, y in pairs) / n
    # calibration : toutes les probabilités (une par issue) regroupées par tranche
    buckets = [[0, 0.0, 0] for _ in range(bins)]  # effectif, somme des p, réalisations
    for probs, y in pairs:
        for o in outcomes:
            b = min(int(probs[o] * bins), bins - 1)
            buckets[b][0] += 1
            buckets[b][1] += probs[o]
            buckets[b][2] += o == y
    calibration = [
        {"tranche": f"{i / bins:.1f}-{(i + 1) / bins:.1f}", "n": c,
         "p_moyenne": round(s / c, 4), "frequence_observee": round(k / c, 4)}
        for i, (c, s, k) in enumerate(buckets) if c
    ]
    return {"n": n, "brier": round(brier, 6), "log_loss": round(log_loss, 6),
            "rps": round(mean_rps, 6), "calibration": calibration}
