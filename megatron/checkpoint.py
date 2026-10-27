"""Checkpoint de reprise : l'état utile d'une session en un petit fichier JSON.

Une nouvelle session lit ``memoire/checkpoint.json`` (quelques centaines de
tokens) au lieu de recharger tout l'historique.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from . import __version__
from .store import DOMAINS, MemoryStore, now_utc


def _git_commit(cwd: Path) -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=cwd,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def save(store: MemoryStore, *, resume: str, prochaines_actions: list[str],
         blocages: list[str] | None = None) -> dict:
    decisions = [{"cle": e.key, "valeur": e.value, "id": e.id} for e in store.active("decisions")]
    contradictions = {d: sorted(store.contradictions(d)) for d in DOMAINS}
    body = {
        "version": __version__,
        "commit": _git_commit(store.root),
        "date": now_utc().isoformat(timespec="seconds"),
        "resume": resume,
        "prochaines_actions": prochaines_actions,
        "blocages": blocages or [],
        "decisions_actives": decisions,
        "contradictions": {d: v for d, v in contradictions.items() if v},
        "effectifs": {d: len(store.active(d)) for d in DOMAINS},
    }
    body["id"] = "ckpt-" + hashlib.sha256(
        json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:10]
    (store.root / "checkpoint.json").write_text(
        json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    store.record("travail", "checkpoint", {"id": body["id"], "resume": resume},
                 source="megatron.checkpoint", status="verifie")
    return body


def load(store: MemoryStore) -> dict | None:
    path = store.root / "checkpoint.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
