"""Test système de bout en bout sur un match FICTIF : aucune donnée réelle analysée.

Chaîne vérifiée : historique synthétique (graine fixe) → agent Stats
(poisson-v4) + agents LLM → Méthode de Fusion → registre anti-fuite
(prévision avant coup d'envoi, résultat après, doublon refusé) → évaluation.
Tout est écrit dans un dossier temporaire : la mémoire du projet n'est pas touchée.
Sans clé LLM, la fusion tourne en mode dégradé et le rapport le dit.
"""

from __future__ import annotations

import csv
import math
import random
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .agents import Agent, LLMAgent, StatsAgent, fuse
from .ledger import OUTCOMES, Ledger, TemporalLeakError
from .store import MemoryStore

DIVISION = "FICTIF"
TEAMS = {  # force offensive, force défensive (buts encaissés relatifs)
    "Alpha FC": (1.35, 0.75), "Beta United": (1.15, 0.90), "Gamma City": (1.00, 1.00),
    "Delta Town": (0.95, 1.05), "Epsilon SC": (0.85, 1.15), "Zeta Rovers": (0.70, 1.25),
}
HEADER = ["Division", "MatchDate", "MatchTime", "HomeTeam", "AwayTeam", "FTHome", "FTAway", "FTResult",
          "OddHome", "OddDraw", "OddAway"]


def _poisson(rng: random.Random, lam: float) -> int:
    limit, k, p = math.exp(-lam), 0, rng.random()
    while p > limit:
        k += 1
        p *= rng.random()
    return k


def synthetic_history(path: Path, *, seasons: int = 2, start: date = date(2030, 8, 1), seed: int = 7) -> date:
    """Écrit des allers-retours entre équipes fictives ; renvoie la date du dernier match."""
    rng = random.Random(seed)
    names = list(TEAMS)
    day = start
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        for _ in range(seasons):
            for home in names:
                for away in names:
                    if home == away:
                        continue
                    lh = 1.45 * TEAMS[home][0] * TEAMS[away][1]
                    la = 1.10 * TEAMS[away][0] * TEAMS[home][1]
                    gh, ga = _poisson(rng, lh), _poisson(rng, la)
                    res = "H" if gh > ga else "A" if ga > gh else "D"
                    w.writerow([DIVISION, day.isoformat(), "15:00", home, away, gh, ga, res, "", "", ""])
                    day += timedelta(days=3)
    return day - timedelta(days=3)


def run(llm_agents: list[Agent] | None = None, workdir: str | Path | None = None) -> dict:
    """Lance la chaîne complète ; ``verifications`` liste chaque contrôle et son résultat.

    L'agent Stats est toujours construit sur l'historique fictif ; ``llm_agents``
    remplace les agents LLM par défaut (DeepSeek, Gemini).
    """
    tmp = None
    if workdir is None:
        tmp = tempfile.TemporaryDirectory()
        workdir = tmp.name
    root = Path(workdir)
    try:
        csv_path = root / "historique_fictif.csv"
        last = synthetic_history(csv_path)
        kickoff = datetime(last.year, last.month, last.day, 15, tzinfo=timezone.utc) + timedelta(days=7)
        task = {"match_id": f"{DIVISION}:{kickoff.date()}:Alpha FC-Zeta Rovers", "fictif": True,
                "division": DIVISION, "home": "Alpha FC", "away": "Zeta Rovers", "date": kickoff.date().isoformat()}
        if llm_agents is None:
            llm_agents = [LLMAgent("deepseek", "DEEPSEEK_API_KEY"), LLMAgent("gemini", "GEMINI_API_KEY")]
        agents = [StatsAgent(csv_path), *llm_agents]
        fusion = fuse(task, agents)
        checks: dict[str, bool | str] = {}
        stats = next((r for r in fusion["reponses"] if r.agent == "stats"), None)
        checks["stats_ok"] = bool(stats and stats.status == "ok")
        checks["stats_favori_plus_fort"] = bool(stats and stats.probs and stats.probs["H"] > stats.probs["A"])
        probs = fusion["probs"]
        checks["probs_somme_1"] = bool(probs) and abs(sum(probs.values()) - 1) < 1e-9
        checks["degrade_documente"] = fusion["mode"] == "complet" or all(
            n in fusion["indisponibles"] or n not in {a.name for a in agents} for n in fusion["agents_manquants"])
        llm_ok = [r.agent for r in fusion["reponses"] if r.agent != "stats" and r.status == "ok"]
        checks["llm_sans_avis_invente"] = all(
            r.probs is None for r in fusion["reponses"] if r.agent != "stats" and r.status != "ok")

        ledger = Ledger(MemoryStore(root / "memoire"))
        cutoff = datetime(last.year, last.month, last.day, 15, tzinfo=timezone.utc)
        version = "fusion-v0:" + "+".join(sorted(r.agent for r in fusion["reponses"] if r.status == "ok"))
        ledger.predict(task["match_id"], kickoff, probs, model_version=version, source="systeme-fictif",
                       recorded_at=kickoff - timedelta(hours=2), data_cutoff=cutoff)
        checks["prevision_enregistree"] = True
        checks["refuse_apres_coup_envoi"] = _raises(TemporalLeakError, ledger.predict, task["match_id"] + "-bis",
                                                    kickoff, probs, model_version=version, source="t",
                                                    recorded_at=kickoff + timedelta(minutes=1))
        checks["refuse_donnees_posterieures"] = _raises(TemporalLeakError, ledger.predict, task["match_id"] + "-ter",
                                                        kickoff, probs, model_version=version, source="t",
                                                        recorded_at=kickoff - timedelta(hours=1),
                                                        data_cutoff=kickoff)
        checks["refuse_doublon"] = _raises(ValueError, ledger.predict, task["match_id"], kickoff, probs,
                                           model_version=version, source="t", recorded_at=kickoff - timedelta(hours=1))
        checks["refuse_resultat_avant"] = _raises(TemporalLeakError, ledger.result, task["match_id"], "H",
                                                  source="t", observed_at=kickoff - timedelta(minutes=1))
        ledger.result(task["match_id"], "H", source="systeme-fictif", observed_at=kickoff + timedelta(hours=2))
        ev = ledger.evaluate(version)
        checks["evaluation"] = ev["n"] == 1 and math.isclose(ev["log_loss"], -math.log(probs["H"]), rel_tol=1e-5)
        return {
            "match": task, "fusion_mode": fusion["mode"], "agents_avis": ["stats"] * checks["stats_ok"] + llm_ok,
            "agents_manquants": fusion["agents_manquants"], "indisponibles": fusion["indisponibles"],
            "probs": {o: round(probs[o], 4) for o in OUTCOMES}, "desaccord_max": fusion["desaccord_max"],
            "a_verifier": fusion["a_verifier"], "avis_non_independants": fusion["avis_non_independants"],
            "version": version, "evaluation_fictive": {k: ev[k] for k in ("n", "brier", "log_loss")},
            "verifications": checks, "succes": all(v is True for v in checks.values()),
        }
    finally:
        if tmp:
            tmp.cleanup()


def _raises(exc, fn, *args, **kwargs) -> bool:
    try:
        fn(*args, **kwargs)
    except exc:
        return True
    return False
