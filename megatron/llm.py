"""Connexion LLM via LiteLLM : Gemini, DeepSeek, Qwen, Claude, OpenRouter, Ollama, llama.cpp local.

LiteLLM est une dépendance optionnelle (``pip install -r requirements-llm.txt``) :
le socle reste en bibliothèque standard. Chaque appel renvoie les tokens
mesurés par le fournisseur et le coût estimé par LiteLLM. Les réponses sont
mises en cache sur disque (clé = modèle + messages + paramètres) pour ne
jamais repayer une question identique. Aucune clé n'est jamais écrite sur disque.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = Path(os.environ.get("MEGATRON_CACHE", ROOT / ".cache" / "llm"))
LLAMACPP_BASE = os.environ.get("LLAMACPP_API_BASE", "http://127.0.0.1:8080/v1")  # voir scripts/llama_local.sh


@dataclass(frozen=True)
class Provider:
    name: str
    env_key: str  # variable d'environnement de la clé ("" = pas de clé, modèle local)
    model: str  # modèle LiteLLM par défaut, remplaçable par MEGATRON_MODEL_<NOM>
    host: str  # hôte testé pour savoir si le réseau laisse passer
    api_base: str = ""  # serveur compatible OpenAI (modèle local) ; vide = point d'accès par défaut de LiteLLM

    def model_id(self) -> str:
        return os.environ.get(f"MEGATRON_MODEL_{self.name.upper()}", self.model)


PROVIDERS = {p.name: p for p in (
    Provider("gemini", "GEMINI_API_KEY", "gemini/gemini-flash-lite-latest", "https://generativelanguage.googleapis.com"),
    Provider("deepseek", "DEEPSEEK_API_KEY", "deepseek/deepseek-chat", "https://api.deepseek.com"),
    Provider("qwen", "DASHSCOPE_API_KEY", "dashscope/qwen-plus", "https://dashscope-intl.aliyuncs.com"),
    Provider("claude", "ANTHROPIC_API_KEY", "anthropic/claude-sonnet-5-5", "https://api.anthropic.com"),
    Provider("openrouter", "OPENROUTER_API_KEY", "openrouter/deepseek/deepseek-chat", "https://openrouter.ai"),
    Provider("ollama", "", "ollama/qwen2.5:7b", os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")),
    Provider("llamacpp", "", "openai/qwen3-4b", LLAMACPP_BASE + "/models", api_base=LLAMACPP_BASE),
)}


# Repli : si le fournisseur échoue (clé absente, quota, surcharge), on essaie le suivant.
# Remplaçable par MEGATRON_REPLI_<NOM>="claude,deepseek" ; vide = pas de repli.
REPLI = {"gemini": ("claude",)}  # Gemini abandonné (28/10) : Claude est le seul fournisseur consulté par défaut


def chain(provider: str) -> list[str]:
    env = os.environ.get(f"MEGATRON_REPLI_{provider.upper()}")
    repli = [x.strip() for x in env.split(",") if x.strip()] if env is not None else list(REPLI.get(provider, ()))
    return [provider] + [x for x in repli if x in PROVIDERS and x != provider]


@dataclass
class Reply:
    provider: str
    model: str
    status: str  # ok | indisponible | erreur
    text: str = ""
    tokens_entree: int | None = None
    tokens_sortie: int | None = None
    cout_usd: float | None = None
    cache: bool = False
    raison: str = ""
    meta: dict = field(default_factory=dict)


def litellm_installed() -> bool:
    try:
        import litellm  # noqa: F401
    except ImportError:
        return False
    return True


def reachable(url: str, timeout: float = 8.0) -> bool:
    """Vrai si l'hôte répond (n'importe quel code HTTP) ; faux si le réseau bloque."""
    try:
        urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=timeout)
        return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, OSError):
        return False


def status(check_network: bool = True) -> list[dict]:
    rows = []
    for p in PROVIDERS.values():
        key = bool(os.environ.get(p.env_key)) if p.env_key else None
        net = reachable(p.host) if check_network else None
        ready = litellm_installed() and (key is not False) and (net is not False)
        rows.append({"fournisseur": p.name, "modele": p.model_id(), "cle": p.env_key or "aucune (local)",
                     "cle_presente": key, "reseau": net, "pret": ready})
    return rows


def _cache_key(model: str, messages: list[dict], params: dict) -> str:
    raw = json.dumps({"m": model, "msg": messages, "p": params}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def complete(provider: str, messages: list[dict], *, max_tokens: int = 300, temperature: float = 0.0,
             json_mode: bool = False, use_cache: bool = True, completion_fn=None) -> Reply:
    """Un appel LLM. ``completion_fn`` permet de tester sans réseau ni clé."""
    p = PROVIDERS[provider]
    model = p.model_id()
    if p.env_key and not os.environ.get(p.env_key):
        return Reply(provider, model, "indisponible", raison=f"variable {p.env_key} absente")
    if completion_fn is None:
        if not litellm_installed():
            return Reply(provider, model, "indisponible", raison="litellm non installé (pip install -r requirements-llm.txt)")
        import litellm
        litellm.drop_params = True  # ex. Claude 5 refuse temperature=0 : le paramètre est retiré plutôt qu'en erreur
        completion_fn = litellm.completion
    params = {"max_tokens": max_tokens, "temperature": temperature}
    if json_mode:
        params["response_format"] = {"type": "json_object"}
    key = _cache_key(model, messages, params)
    path = CACHE_DIR / f"{key}.json"
    if use_cache and path.exists():
        hit = json.loads(path.read_text(encoding="utf-8"))
        return Reply(**{**hit, "cache": True})
    extra = {"api_base": p.api_base, "api_key": "local"} if p.api_base else {}
    try:
        resp = completion_fn(model=model, messages=messages, **params, **extra)
    except Exception as exc:  # erreurs réseau, quota, clé refusée : remontées telles quelles
        return Reply(provider, model, "erreur", raison=f"{type(exc).__name__}: {str(exc)[:300]}")
    usage = getattr(resp, "usage", None) or {}
    get = usage.get if isinstance(usage, dict) else lambda k: getattr(usage, k, None)
    cost = None
    try:
        import litellm
        cost = litellm.completion_cost(completion_response=resp)
    except Exception:
        pass
    if p.api_base:
        cost = 0.0  # modèle local : aucun coût d'API
    reply = Reply(provider, model, "ok", text=resp.choices[0].message.content or "",
                  tokens_entree=get("prompt_tokens"), tokens_sortie=get("completion_tokens"), cout_usd=cost)
    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data = {k: v for k, v in reply.__dict__.items() if k != "cache"}
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return reply


def complete_with_fallback(provider: str, messages: list[dict], **kwargs) -> Reply:
    """``complete`` sur la chaîne de repli ; la réponse dit quel fournisseur a répondu et pourquoi les autres non."""
    echecs = []
    for name in chain(provider):
        rep = complete(name, messages, **kwargs)
        if rep.status == "ok":
            if echecs:
                rep.meta["repli_depuis"] = echecs
            return rep
        echecs.append({"fournisseur": name, "status": rep.status, "raison": rep.raison})
    rep.meta["repli_depuis"] = echecs[:-1]
    return rep
