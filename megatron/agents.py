"""Interface commune des agents et Méthode de Fusion (Gemini + DeepSeek + Stats).

Un agent n'est « consulté » que s'il a réellement été appelé. Un agent dont
l'accès manque renvoie ``status="indisponible"`` avec la raison, et la fusion
continue en mode dégradé sans jamais inventer son avis.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path

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
    version: str = ""  # modèle exact ayant produit l'avis (ex. poisson-v4, gemini/gemini-flash-lite-latest)
    marches: dict[str, dict[str, float]] | None = None  # 2+ / 3+ buts, seulement si validés (EXP-007)
    version_marches: str = ""


class Agent:
    name = "agent"

    def ask(self, task: dict) -> AgentResponse:
        raise NotImplementedError


class LLMAgent(Agent):
    """Agent LLM distant, branché via ``megatron.llm`` (LiteLLM).

    Sans clé, sans LiteLLM ou sans réseau, il se déclare indisponible ou en
    erreur avec la raison exacte ; il ne simule jamais un avis. La consigne
    impose une réponse JSON courte (moins de tokens de sortie).
    """

    SYSTEME = ("Analyste football. Réponds UNIQUEMENT en JSON : "
               '{"H":p,"D":p,"A":p,"raison":"<=25 mots","sources":[]}. '
               "p = probabilité 0-1, somme 1. Aucune info inventée : si tu ne sais pas, dis-le dans raison.")

    def __init__(self, name: str, env_key: str = "", provider: str | None = None, completion_fn=None):
        self.name = name
        self.provider = provider or name
        self.env_key = env_key
        self.completion_fn = completion_fn

    def available(self) -> tuple[bool, str]:
        from . import llm

        keys = [self.env_key or llm.PROVIDERS[self.provider].env_key] + [llm.PROVIDERS[n].env_key for n in llm.chain(self.provider)[1:]]
        if all(k and not os.environ.get(k) for k in keys):
            return False, f"variable {' / '.join(keys)} absente de l'environnement"
        if self.completion_fn is None and not llm.litellm_installed():
            return False, "litellm non installé (pip install -r requirements-llm.txt)"
        return True, ""

    def ask(self, task: dict) -> AgentResponse:
        from . import llm

        ok, why = self.available()
        if not ok:
            return AgentResponse(agent=self.name, status="indisponible", raison=why)
        messages = [{"role": "system", "content": self.SYSTEME},
                    {"role": "user", "content": json.dumps(task, ensure_ascii=False, separators=(",", ":"))}]
        rep = llm.complete_with_fallback(self.provider, messages, json_mode=True, completion_fn=self.completion_fn)
        base = dict(agent=self.name, appels=0 if rep.cache else 1, tokens_entree=rep.tokens_entree,
                    tokens_sortie=rep.tokens_sortie, tokens_mesure="mesure" if rep.tokens_entree is not None else "indisponible")
        if rep.status != "ok":
            return AgentResponse(status=rep.status, raison=rep.raison, **base)
        try:
            out = json.loads(rep.text)
            probs = {o: float(out[o]) for o in OUTCOMES}
            total = sum(probs.values())
            if total <= 0 or any(v < 0 for v in probs.values()):
                raise ValueError("probabilités invalides")
            probs = {o: v / total for o, v in probs.items()}
        except (ValueError, KeyError, TypeError) as exc:
            return AgentResponse(status="erreur", raison=f"réponse non conforme : {exc}", **base)
        fav = max(probs, key=probs.get)
        return AgentResponse(status="ok", probs=probs, version=rep.model,
                             conclusion=f"[{rep.model}] {fav} ({probs[fav]:.0%})",
                             preuves=[str(out.get("raison", ""))], sources=list(out.get("sources") or [rep.model]),
                             incertitudes=["avis de modèle de langage, non calibré"], **base)


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

    Modèle 1X2 par défaut ``poisson-v5-cal`` (EXP-008 : demi-vie 270, rétrécissement
    2, pseudo-buts mêlant 35 % de tirs cadrés convertis ; recalibré par EXP-010) ; marchés 2+ / 3+ sur
    un ajustement ``poisson-v4`` séparé (recalibration EXP-007) : la tâche fournit
    ``division``, ``home``, ``away`` et ``date`` (AAAA-MM-JJ) ; le modèle de
    Maher est ajusté sur les seuls matchs antérieurs de ``data/``.
    Repli ``stats-v0`` : si ``xg_home`` et ``xg_away`` sont fournis, Poisson
    direct sur ces buts attendus.
    """

    name = "stats"
    HALF_LIFE, SHRINK = 270.0, 2.0  # promus par EXP-008 (retour arrière : 90, 3, 0,25 = poisson-v4)
    PROXY, PROXY_WEIGHT = "cadres", 0.35
    CALIBRATION = (1.160088, 0.016201, 0.150311)  # b, c_H, c_D appris par EXP-010 sur 2008-2016 ; None = v5 brut
    VERSION = "poisson-v5-cal"

    def __init__(self, csv_path=None):
        self.csv_path = csv_path  # None = data.CURRENT (2000-2026 + saison en cours)

    def ask(self, task: dict) -> AgentResponse:
        if "xg_home" in task or "xg_away" in task:
            return self._from_xg(task)
        try:
            return self._from_history(task)
        except (KeyError, ValueError) as exc:
            return AgentResponse(agent=self.name, status="erreur", raison=f"entrée invalide : {exc}")

    def _from_history(self, task: dict) -> AgentResponse:
        from datetime import date

        from . import data, marches, models

        day = date.fromisoformat(task["date"])
        path = self.csv_path or data.CURRENT
        history = [m for m in data.load(path, divisions={task["division"]}) if m.day < day]
        if not history:
            raise ValueError(f"aucun match de {task['division']} avant le {day}")
        fit = models.fit_maher(history, day, half_life=self.HALF_LIFE, shrink=self.SHRINK,
                               proxy=self.PROXY, proxy_weight=self.PROXY_WEIGHT)
        lh, la = fit.rates(task["home"], task["away"])
        unknown = [t for t in (task["home"], task["away"]) if t not in fit.attack]
        rep = self._response(
            models.calibrer_1x2(poisson_1x2(lh, la), *self.CALIBRATION) if self.CALIBRATION else poisson_1x2(lh, la),
            task, version=self.VERSION if self.CALIBRATION else "poisson-v5",
            preuves=[f"{len(history)} matchs antérieurs au {day}, dernier le "
                     f"{max(m.day for m in history)}",
                     f"buts attendus {lh:.2f} - {la:.2f}"],
            incertitudes=["équipes sans historique traitées comme moyennes : " + ", ".join(unknown)] if unknown else [],
            sources=[f"data/{Path(p).name}" for p in ([path] if isinstance(path, (str, Path)) else path)],
        )
        # recalibration EXP-007 apprise sur poisson-v4 seulement : ajustement v4 séparé
        v4 = models.fit_maher(history, day, **marches.V4)
        rep.marches, rep.version_marches = (marches.probs_buts_calibrees(*v4.rates(task["home"], task["away"])),
                                            marches.VERSION_BUTS)
        return rep

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
            agent=self.name, status="ok", probs=probs, version=version,
            conclusion=f"[{version}] issue la plus probable {fav} ({probs[fav]:.0%})",
            preuves=preuves,
            hypotheses=["buts indépendants, loi de Poisson"],
            incertitudes=incertitudes + ["pas de correction des scores faibles (Dixon-Coles)",
                                         "ni absences, ni calendrier, ni enjeu pris en compte"],
            sources=sources,
            tokens_entree=0, tokens_sortie=0, tokens_mesure="mesure",
        )


def default_agents() -> list[Agent]:
    """Décision de Luloki (29/10/2026) : Claude est le seul fournisseur LLM externe.

    Les autres fournisseurs restent déclarés dans ``megatron.llm`` mais ne sont plus consultés par défaut.
    """
    return [StatsAgent(), LLMAgent("claude", "ANTHROPIC_API_KEY")]


EXPECTED_FUSION = ("stats", "claude")


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
