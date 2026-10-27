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
    ):
        kickoff_dt = parse_dt(kickoff)
        rec_dt = parse_dt(recorded_at or now_utc())
        if rec_dt >= kickoff_dt:
            raise TemporalLeakError(f"{match_id} : prévision enregistrée après le coup d'envoi")
        if data_cutoff and parse_dt(data_cutoff) >= kickoff_dt:
            raise TemporalLeakError(f"{match_id} : données utilisées postérieures au coup d'envoi")
        if set(probs) != set(OUTCOMES):
            raise ValueError(f"probabilités attendues pour {OUTCOMES}, reçu {sorted(probs)}")
        if any(p < 0 for p in probs.values()) or abs(sum(probs.values()) - 1) > 1e-6:
            raise ValueError(f"{match_id} : probabilités invalides {probs}")
        key = f"pred:{match_id}:{model_version}"
        if self.store.active(DOMAIN, key):
            raise ValueError(f"prévision déjà enregistrée : {key}")
        return self.store.record(
            DOMAIN, key,
            {"match_id": match_id, "kickoff": kickoff_dt.isoformat(), "probs": probs,
             "model_version": model_version,
             "data_cutoff": parse_dt(data_cutoff).isoformat() if data_cutoff else None},
            source=source, status="verifie", recorded_at=rec_dt, supersede=False,
        )

    def result(self, match_id: str, outcome: str, *, source: str,
               observed_at: str | datetime | None = None):
        if outcome not in OUTCOMES:
            raise ValueError(f"issue inconnue : {outcome!r}")
        preds = self._predictions(match_id)
        obs_dt = parse_dt(observed_at or now_utc())
        for p in preds:
            if obs_dt <= parse_dt(p.value["kickoff"]):
                raise TemporalLeakError(f"{match_id} : résultat daté avant le coup d'envoi")
        return self.store.record(DOMAIN, f"result:{match_id}", {"match_id": match_id, "outcome": outcome},
                                 source=source, status="verifie", observed_at=obs_dt)

    def _predictions(self, match_id: str | None = None, model_version: str | None = None):
        out = []
        for e in self.store.active(DOMAIN):
            if not e.key.startswith("pred:"):
                continue
            if match_id and e.value["match_id"] != match_id:
                continue
            if model_version and e.value["model_version"] != model_version:
                continue
            out.append(e)
        return out

    def evaluate(self, model_version: str, bins: int = 5) -> dict:
        """Brier multiclasse, log-loss et calibration sur les matchs résolus."""
        results = {e.value["match_id"]: e.value["outcome"]
                   for e in self.store.active(DOMAIN) if e.key.startswith("result:")}
        pairs = [(p.value["probs"], results[p.value["match_id"]])
                 for p in self._predictions(model_version=model_version)
                 if p.value["match_id"] in results]
        n = len(pairs)
        if n == 0:
            return {"model_version": model_version, "n": 0, "brier": None, "log_loss": None, "calibration": []}
        brier = sum(sum((probs[o] - (o == y)) ** 2 for o in OUTCOMES) for probs, y in pairs) / n
        log_loss = -sum(math.log(max(probs[y], EPS)) for probs, y in pairs) / n
        # calibration : toutes les probabilités (une par issue) regroupées par tranche
        buckets = [[0, 0.0, 0] for _ in range(bins)]  # effectif, somme des p, réalisations
        for probs, y in pairs:
            for o in OUTCOMES:
                b = min(int(probs[o] * bins), bins - 1)
                buckets[b][0] += 1
                buckets[b][1] += probs[o]
                buckets[b][2] += o == y
        calibration = [
            {"tranche": f"{i / bins:.1f}-{(i + 1) / bins:.1f}", "n": c,
             "p_moyenne": round(s / c, 4), "frequence_observee": round(k / c, 4)}
            for i, (c, s, k) in enumerate(buckets) if c
        ]
        return {"model_version": model_version, "n": n, "brier": round(brier, 6),
                "log_loss": round(log_loss, 6), "calibration": calibration}
