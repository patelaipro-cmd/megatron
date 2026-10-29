"""Boucle de suivi : prévoir avant le coup d'envoi, saisir le résultat, faire le bilan.

``prevoir`` enregistre dans le registre (immuable, anti-fuite) la prévision
fusionnée et l'avis de chaque agent consulté, sous des versions distinctes :
le bilan compare ainsi la fusion à chacun de ses agents sur les mêmes matchs.
La trace de la fusion (agents manquants, désaccord, sources) est gardée à côté.
"""

from __future__ import annotations

from datetime import datetime
import json

from .agents import Agent, fuse
from .ledger import DOMAIN, OUTCOMES, Ledger, score
from .store import MemoryStore, now_utc, parse_dt


def fusion_version(result: dict) -> str:
    ok = sorted((r.agent, r.version or "inconnue") for r in result["reponses"] if r.status == "ok")
    return "fusion-v1:" + json.dumps(ok, ensure_ascii=True, separators=(",", ":"))


def prevoir(store: MemoryStore, task: dict, kickoff: str | datetime, *, agents: list[Agent] | None = None,
            source: str = "megatron prevoir", now: datetime | None = None) -> dict:
    """Fusion puis enregistrement ; refuse tout après le coup d'envoi, sans rien écrire."""
    kickoff_dt = parse_dt(kickoff)
    fixed_now = now  # injection temporelle réservée aux simulations/tests
    now = parse_dt(now or now_utc())
    if now >= kickoff_dt:
        raise ValueError(f"{task.get('match_id')} : coup d'envoi passé, prévision refusée")
    match_id = task["match_id"]
    result = fuse(task, agents)
    now = parse_dt(fixed_now or now_utc())
    if now >= kickoff_dt:
        raise ValueError(f"{task.get('match_id')} : coup d'envoi franchi pendant l'analyse, rien n'est enregistré")
    if not result["probs"]:
        return {"match_id": match_id, "enregistre": [], "indisponibles": result["indisponibles"],
                "raison": "aucun agent n'a donné d'avis : rien n'est enregistré"}
    ledger = Ledger(store)
    versions = [(fusion_version(result), result["probs"])]
    versions += [(f"agent:{r.agent}:{r.version or 'inconnue'}", r.probs)
                 for r in result["reponses"] if r.status == "ok" and r.probs]
    taken = [v for v, _ in versions if store.active(DOMAIN, f"pred:{match_id}:{v}")]
    if taken:
        raise ValueError(f"{match_id} : déjà prévu sous {taken}, rien n'est réécrit")
    written = []
    for version, probs in versions:
        # Ne pas inventer de preuve temporelle sur les données des agents.
        ledger.predict(match_id, kickoff_dt, probs, model_version=version, source=source,
                       recorded_at=now)
        written.append(version)
    store.record(DOMAIN, f"fusion:{match_id}", {
        "match_id": match_id, "mode": result["mode"], "agents_manquants": result["agents_manquants"],
        "indisponibles": result["indisponibles"], "desaccord_max": result["desaccord_max"],
        "a_verifier": result["a_verifier"], "avis_non_independants": result["avis_non_independants"],
        "sources": {r.agent: r.sources for r in result["reponses"] if r.status == "ok"},
        "tokens": {r.agent: [r.tokens_entree, r.tokens_sortie] for r in result["reponses"] if r.appels},
    }, source=source, status="verifie", recorded_at=now, supersede=False)
    return {"match_id": match_id, "enregistre": written, "mode": result["mode"],
            "probs": {o: round(result["probs"][o], 4) for o in OUTCOMES},
            "a_verifier": result["a_verifier"], "indisponibles": result["indisponibles"]}


def outcome_of(score_or_outcome: str) -> str:
    """« H », « D », « A » ou un score « 2-1 »."""
    text = score_or_outcome.strip().upper()
    if text in OUTCOMES:
        return text
    home, away = (int(x) for x in text.replace(":", "-").split("-"))
    return "H" if home > away else "A" if away > home else "D"


def resultat(store: MemoryStore, match_id: str, score_or_outcome: str, *, source: str,
             observed_at: str | datetime | None = None, correction: bool = False):
    if not Ledger(store)._predictions(match_id):
        raise ValueError(f"{match_id} : aucune prévision enregistrée, résultat inutile")
    return Ledger(store).result(match_id, outcome_of(score_or_outcome), source=source, observed_at=observed_at,
                                correction=correction)


def bilan(store: MemoryStore, now: datetime | None = None) -> dict:
    """Scores par version sur les matchs résolus, et comparaison sur les matchs communs."""
    now = now or now_utc()
    ledger = Ledger(store)
    entries = store.active(DOMAIN)
    results = {e.value["match_id"]: e.value["outcome"] for e in entries if e.key.startswith("result:")}
    preds = ledger._predictions()
    by_version: dict[str, dict[str, dict]] = {}
    for p in preds:
        by_version.setdefault(p.value["model_version"], {})[p.value["match_id"]] = p.value["probs"]
    common = set(results)
    for probs in by_version.values():
        common &= set(probs)
    pending = sorted({p.value["match_id"] for p in preds
                      if p.value["match_id"] not in results and parse_dt(p.value["kickoff"]) < now})
    upcoming = sorted({p.value["match_id"] for p in preds if parse_dt(p.value["kickoff"]) >= now})
    return {
        "versions": {v: score([(pr[m], results[m]) for m in pr if m in results]) for v, pr in sorted(by_version.items())},
        "communs": {"n": len(common), "log_loss": {
            v: score([(pr[m], results[m]) for m in common])["log_loss"] for v, pr in sorted(by_version.items())}},
        "resultats_a_saisir": pending,
        "a_venir": upcoming,
    }
