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

    Attend ``task["xg_home"]`` et ``task["xg_away"]`` (buts attendus estimés à
    partir de données antérieures au match). Modèle de référence volontairement
    simple ; Dixon-Coles (penaltyblog) est candidat à l'expérimentation.
    """

    name = "stats"

    def ask(self, task: dict) -> AgentResponse:
        try:
            lh, la = float(task["xg_home"]), float(task["xg_away"])
        except (KeyError, TypeError, ValueError) as exc:
            return AgentResponse(agent=self.name, status="erreur", raison=f"entrée manquante : {exc}")
        probs = poisson_1x2(lh, la)
        fav = max(probs, key=probs.get)
        return AgentResponse(
            agent=self.name, status="ok", probs=probs,
            conclusion=f"issue la plus probable {fav} ({probs[fav]:.0%})",
            preuves=[f"xG domicile {lh}, xG extérieur {la}"],
            hypotheses=["buts indépendants, loi de Poisson"],
            incertitudes=["pas de correction des scores faibles (Dixon-Coles)"],
            sources=list(task.get("sources", ["stats"])),
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
