"""Boucle de suivi : prévoir avant le coup d'envoi, saisir le résultat, faire le bilan.

``prevoir`` enregistre dans le registre (immuable, anti-fuite) la prévision
fusionnée et l'avis de chaque agent consulté, sous des versions distinctes :
le bilan compare ainsi la fusion à chacun de ses agents sur les mêmes matchs.
La trace de la fusion (agents manquants, désaccord, sources) est gardée à côté.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import json

from .agents import Agent, fuse
from . import angles_morts
from .jeton import protege_suivi
from .ledger import DOMAIN, MARKETS, OUTCOMES, Ledger, pred_key, score
from .store import MemoryStore, now_utc, parse_dt


FENETRE = timedelta(hours=5)  # une prévision s'enregistre dans les 5 h qui précèdent le coup d'envoi, pas avant


def _check_window(match_id, now: datetime, kickoff_dt: datetime, moment: str) -> None:
    if now >= kickoff_dt:
        raise ValueError(f"{match_id} : coup d'envoi {moment}, rien n'est enregistré")
    if now < kickoff_dt - FENETRE:
        raise ValueError(f"{match_id} : trop tôt, la fenêtre s'ouvre le {(kickoff_dt - FENETRE).isoformat()} "
                         f"({FENETRE.total_seconds() / 3600:g} h avant le coup d'envoi)")


def fusion_version(result: dict) -> str:
    ok = sorted((r.agent, r.version or "inconnue") for r in result["reponses"] if r.status == "ok")
    return "fusion-v1:" + json.dumps(ok, ensure_ascii=True, separators=(",", ":"))


@protege_suivi
def prevoir(store: MemoryStore, task: dict, kickoff: str | datetime, *, agents: list[Agent] | None = None,
            source: str = "megatron prevoir", now: datetime | None = None,
            acces: str | None = None, jeton_id: str | None = None, contexte_favori: dict | None = None) -> dict:
    """Fusion puis enregistrement, seulement dans les 5 h avant le coup d'envoi ; hors fenêtre, rien n'est écrit."""
    kickoff_dt = parse_dt(kickoff)
    fixed_now = now  # injection temporelle réservée aux simulations/tests
    _check_window(task.get("match_id"), parse_dt(now or now_utc()), kickoff_dt, "passé")
    match_id = task["match_id"]
    contexte_rapport = None
    if contexte_favori is not None:
        contexte_rapport = angles_morts.verifier(contexte_favori, at=parse_dt(now or now_utc()))
        if not contexte_rapport["ok"]:
            raise ValueError("contexte favori invalide : " + "; ".join(contexte_rapport["erreurs"]))
        if contexte_favori["match_id"] != match_id or parse_dt(contexte_favori["kickoff"]) != kickoff_dt:
            raise ValueError("contexte favori d'un autre match ou coup d'envoi")
        for field in ("home", "away"):
            if task.get(field) is not None and task[field] != contexte_favori[field]:
                raise ValueError(f"contexte favori : équipe {field} différente")
    result = fuse(task, agents)
    now = parse_dt(fixed_now or now_utc())
    _check_window(match_id, now, kickoff_dt, "franchi pendant l'analyse")
    if not result["probs"]:
        return {"match_id": match_id, "enregistre": [], "indisponibles": result["indisponibles"],
                "raison": "aucun agent n'a donné d'avis : rien n'est enregistré"}
    ledger = Ledger(store, acces=acces, jeton_id=jeton_id)
    versions = [(fusion_version(result), result["probs"])]
    versions += [(f"agent:{r.agent}:{r.version or 'inconnue'}", r.probs)
                 for r in result["reponses"] if r.status == "ok" and r.probs]
    buts = [(m, f"agent:{r.agent}:{r.version_marches}", p) for r in result["reponses"]
            if r.status == "ok" and r.marches for m, p in sorted(r.marches.items())]
    taken = [v for v, _ in versions if store.active(DOMAIN, pred_key(match_id, v))]
    taken += [f"{m}:{v}" for m, v, _ in buts if store.active(DOMAIN, pred_key(match_id, v, m))]
    if taken:
        raise ValueError(f"{match_id} : déjà prévu sous {taken}, rien n'est réécrit")
    written = []
    for version, probs in versions:
        # Ne pas inventer de preuve temporelle sur les données des agents.
        ledger.predict(match_id, kickoff_dt, probs, model_version=version, source=source,
                       recorded_at=now)
        written.append(version)
    written_buts = []
    for market, version, probs in buts:
        ledger.predict(match_id, kickoff_dt, probs, model_version=version, source=source,
                       recorded_at=now, market=market)
        written_buts.append(f"{market}:{version}")
    store.record(DOMAIN, f"fusion:{match_id}", {
        "contexte_favori": {"donnees": contexte_favori, "verification": contexte_rapport} if contexte_favori is not None else None,
        "match_id": match_id, "mode": result["mode"], "agents_manquants": result["agents_manquants"],
        "indisponibles": result["indisponibles"], "desaccord_max": result["desaccord_max"],
        "a_verifier": result["a_verifier"], "avis_non_independants": result["avis_non_independants"],
        "sources": {r.agent: r.sources for r in result["reponses"] if r.status == "ok"},
        "tokens": {r.agent: [r.tokens_entree, r.tokens_sortie] for r in result["reponses"] if r.appels},
    }, source=source, status="verifie", recorded_at=now, supersede=False)
    return {"match_id": match_id, "enregistre": written, "enregistre_buts": written_buts, "mode": result["mode"],
            "probs": {o: round(result["probs"][o], 4) for o in OUTCOMES},
            "a_verifier": result["a_verifier"], "indisponibles": result["indisponibles"],
            "contexte_favori_statut": contexte_rapport["statut"] if contexte_rapport else "NON_FOURNI"}


def outcome_of(score_or_outcome: str) -> str:
    """« H », « D », « A » ou un score « 2-1 »."""
    text = score_or_outcome.strip().upper()
    if text in OUTCOMES:
        return text
    home, away = (int(x) for x in text.replace(":", "-").split("-"))
    return "H" if home > away else "A" if away > home else "D"


def goals_of(score_or_outcome: str) -> tuple[int, int] | None:
    """Score « 2-1 » → (2, 1) ; None pour une issue seule (marchés de buts non résolus)."""
    text = score_or_outcome.strip().upper()
    if text in OUTCOMES:
        return None
    home, away = (int(x) for x in text.replace(":", "-").split("-"))
    return home, away


@protege_suivi
def resultat(store: MemoryStore, match_id: str, score_or_outcome: str, *, source: str,
             observed_at: str | datetime | None = None, correction: bool = False,
             acces: str | None = None, jeton_id: str | None = None):
    if not Ledger(store)._predictions(match_id):
        raise ValueError(f"{match_id} : aucune prévision enregistrée, résultat inutile")
    return Ledger(store, acces=acces, jeton_id=jeton_id).result(match_id, outcome_of(score_or_outcome), source=source, observed_at=observed_at,
                                correction=correction, goals=goals_of(score_or_outcome))


def bilan(store: MemoryStore, now: datetime | None = None) -> dict:
    """Scores par version sur les matchs résolus, et comparaison sur les matchs communs."""
    now = now or now_utc()
    ledger = Ledger(store)
    entries = store.active(DOMAIN)
    results = {e.value["match_id"]: e.value["outcome"] for e in entries if e.key.startswith("result:")}
    preds = ledger._predictions(market="1X2")
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
        "marches_buts": _bilan_buts(ledger),
        "resultats_a_saisir": pending,
        "a_venir": upcoming,
    }


def _bilan_buts(ledger: Ledger) -> dict:
    """Scores par version sur les marchés 2+ / 3+ ; un résultat saisi sans score ne les résout pas."""
    out = {}
    for market in ("2+", "3+"):
        preds = ledger._predictions(market=market)
        if not preds:
            continue
        results = ledger.outcomes(market)
        by_version: dict[str, list] = {}
        for p in preds:
            by_version.setdefault(p.value["model_version"], [])
            if p.value["match_id"] in results:
                by_version[p.value["model_version"]].append((p.value["probs"], results[p.value["match_id"]]))
        out[market] = {v: score(pairs, outcomes=MARKETS[market]) for v, pairs in sorted(by_version.items())}
    return out
