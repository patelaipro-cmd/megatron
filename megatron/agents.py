"""Interface commune des agents et Méthode de Fusion (Gemini + DeepSeek + Stats).

Un agent n'est « consulté » que s'il a réellement été appelé. Un agent dont
l'accès manque renvoie ``status="indisponible"`` avec la raison, et la fusion
continue en mode dégradé sans jamais inventer son avis.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field

from .ledger import OUTCOMES


@dataclass
class AgentResponse:
    agent: str
    status: str  # ok | indisponible | erreur
    conclusion: str = ""
    probs: dict[str, float] | None = None
    preuves: list[str] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)
    incertitudes: list[str] = field(default_factory=list)
    objections: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    appels: int = 0
    tokens_entree: int | None = None
    tokens_sortie: int | None = None
    tokens_mesure: str = "indisponible"  # mesure | estimation | indisponible
    raison: str = ""


class Agent:
    name = "agent"

    def ask(self, task: dict) -> AgentResponse:
        raise NotImplementedError


class LLMAgent(Agent):
    """Agent LLM distant. Sans clé d'accès, il se déclare indisponible.

    Le client HTTP n'est pas encore branché (prochaine étape, via LiteLLM) :
    même avec une clé, il répond « indisponible » plutôt que de simuler un avis.
    """

    def __init__(self, name: str, env_key: str):
        self.name = name
        self.env_key = env_key

    def available(self) -> tuple[bool, str]:
        if not os.environ.get(self.env_key):
            return False, f"variable {self.env_key} absente de l'environnement"
        return False, "client non branché (prévu via LiteLLM)"

    def ask(self, task: dict) -> AgentResponse:
        ok, why = self.available()
        return AgentResponse(agent=self.name, status="indisponible", raison=why)


def poisson_1x2(lam_home: float, lam_away: float, max_goals: int = 10) -> dict[str, float]:
    """Probabilités 1X2 sous deux lois de Poisson indépendantes, renormalisées."""
    def pmf(k, lam):
        return math.exp(-lam) * lam ** k / math.factorial(k)
    ph = [pmf(k, lam_home) for k in range(max_goals + 1)]
    pa = [pmf(k, lam_away) for k in range(max_goals + 1)]
    h = sum(ph[i] * pa[j] for i in range(max_goals + 1) for j in range(i))
    d = sum(ph[i] * pa[i] for i in range(max_goals + 1))
    a = sum(ph[i] * pa[j] for j in range(max_goals + 1) for i in range(j))
    total = h + d + a
    return {"H": h / total, "D": d / total, "A": a / total}


class StatsAgent(Agent):
    """Agent Python déterministe : aucun token consommé.

    Modèle par défaut ``poisson-v1`` (promu par EXP-001) : la tâche fournit
    ``division``, ``home``, ``away`` et ``date`` (AAAA-MM-JJ) ; le modèle de
    Maher est ajusté sur les seuls matchs antérieurs de ``data/``.
    Repli ``stats-v0`` : si ``xg_home`` et ``xg_away`` sont fournis, Poisson
    direct sur ces buts attendus.
    """

    name = "stats"
    HALF_LIFE, SHRINK = 90.0, 3.0  # figés par EXP-001 sur la Ligue 1 2022/23

    def ask(self, task: dict) -> AgentResponse:
        if "xg_home" in task or "xg_away" in task:
            return self._from_xg(task)
        try:
            return self._from_history(task)
        except (KeyError, ValueError) as exc:
            return AgentResponse(agent=self.name, status="erreur", raison=f"entrée invalide : {exc}")

    def _from_history(self, task: dict) -> AgentResponse:
        from datetime import date

        from . import data, models

        day = date.fromisoformat(task["date"])
        history = [m for m in data.load(divisions={task["division"]}) if m.day < day]
        fit = models.fit_maher(history, day, half_life=self.HALF_LIFE, shrink=self.SHRINK)
        lh, la = fit.rates(task["home"], task["away"])
        unknown = [t for t in (task["home"], task["away"]) if t not in fit.attack]
        return self._response(
            poisson_1x2(lh, la), task, version="poisson-v1",
            preuves=[f"{len(history)} matchs antérieurs au {day}, dernier le "
                     f"{max(m.day for m in history) if history else 'aucun'}",
                     f"buts attendus {lh:.2f} - {la:.2f}"],
            incertitudes=["équipes sans historique traitées comme moyennes : " + ", ".join(unknown)] if unknown else [],
            sources=["data/matches_top5_2020-2026.csv"],
        )

    def _from_xg(self, task: dict) -> AgentResponse:
        try:
            lh, la = float(task["xg_home"]), float(task["xg_away"])
        except (KeyError, TypeError, ValueError) as exc:
            return AgentResponse(agent=self.name, status="erreur", raison=f"entrée manquante : {exc}")
        return self._response(poisson_1x2(lh, la), task, version="stats-v0",
                              preuves=[f"xG domicile {lh}, xG extérieur {la}"], incertitudes=[],
                              sources=list(task.get("sources", ["stats"])))

    def _response(self, probs, task, *, version, preuves, incertitudes, sources) -> AgentResponse:
        fav = max(probs, key=probs.get)
        return AgentResponse(
            agent=self.name, status="ok", probs=probs,
            conclusion=f"[{version}] issue la plus probable {fav} ({probs[fav]:.0%})",
            preuves=preuves,
            hypotheses=["buts indépendants, loi de Poisson"],
            incertitudes=incertitudes + ["pas de correction des scores faibles (Dixon-Coles)",
                                         "ni absences, ni calendrier, ni enjeu pris en compte"],
            sources=sources,
            tokens_entree=0, tokens_sortie=0, tokens_mesure="mesure",
        )


def default_agents() -> list[Agent]:
    return [
        StatsAgent(),
        LLMAgent("deepseek", "DEEPSEEK_API_KEY"),
        LLMAgent("gemini", "GEMINI_API_KEY"),
        LLMAgent("claude", "ANTHROPIC_API_KEY"),
        LLMAgent("qwen", "DASHSCOPE_API_KEY"),
    ]


EXPECTED_FUSION = ("stats", "deepseek", "gemini")


def fuse(task: dict, agents: list[Agent] | None = None, *,
         weights: dict[str, float] | None = None, disagreement: float = 0.15) -> dict:
    """Applique la Méthode de Fusion et documente chaque indisponibilité."""
    responses = [a.ask(task) for a in (agents or default_agents())]
    ok = [r for r in responses if r.status == "ok" and r.probs]
    weights = weights or {}
    total_w = sum(weights.get(r.agent, 1.0) for r in ok)
    fused = None
    if ok and total_w > 0:
        fused = {o: sum(weights.get(r.agent, 1.0) * r.probs[o] for r in ok) / total_w for o in OUTCOMES}

    gap = 0.0
    for i, a in enumerate(ok):
        for b in ok[i + 1:]:
            gap = max(gap, max(abs(a.probs[o] - b.probs[o]) for o in OUTCOMES))

    groups: dict[tuple, list[str]] = {}
    for r in ok:
        groups.setdefault(tuple(sorted(r.sources)), []).append(r.agent)
    dependants = [g for g in groups.values() if len(g) > 1]

    missing = [n for n in EXPECTED_FUSION if n not in {r.agent for r in ok}]
    return {
        "match_id": task.get("match_id"),
        "probs": fused,
        "mode": "complet" if not missing else "degrade",
        "agents_manquants": missing,
        "consultes": [r.agent for r in responses if r.appels > 0 or r.status == "ok"],
        "indisponibles": {r.agent: r.raison for r in responses if r.status != "ok"},
        "desaccord_max": round(gap, 4),
        "a_verifier": gap > disagreement,
        "avis_non_independants": dependants,
        "reponses": responses,
    }
