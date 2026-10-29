"""Vérification d'une mémoire avant reprise : ``python -m megatron synchro verifier``.

Partager le dépôt ne synchronise pas la mémoire (docs/synchro-codex-claude.md).
Avant de reprendre le travail d'un autre environnement, cette commande contrôle
la mémoire telle qu'elle est sur le disque, sans rien écrire :

- erreurs (code de sortie 1) : ligne illisible ou marqueur de conflit git,
  identifiant en double, ``supersedes`` vers une entrée inconnue, clé de
  prévision ou de résultat active en double, contradiction active, prévision
  enregistrée après son coup d'envoi ;
- alertes (code 0) : checkpoint absent, effectifs différents du checkpoint,
  commit du checkpoint inconnu ou absent de l'historique, branche en retard
  sur la référence, mémoire modifiée et non commitée.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .ledger import DOMAIN as PERF
from .store import DOMAINS, Entry, MemoryStore, parse_dt

CONFLICT_MARKERS = ("<<<<<<< ", "=======", ">>>>>>> ")


def _read(path: Path, domain: str, errors: list[str]) -> list[Entry]:
    entries = []
    if not path.exists():
        return entries
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        if line.startswith(CONFLICT_MARKERS):
            errors.append(f"{path.name}:{n} : marqueur de conflit git")
            continue
        try:
            entry = Entry(**json.loads(line))
        except (ValueError, TypeError) as exc:
            errors.append(f"{path.name}:{n} : ligne illisible ({exc})")
            continue
        if entry.domain != domain:
            errors.append(f"{path.name}:{n} : entrée du domaine {entry.domain!r}")
        entries.append(entry)
    return entries


def _git(repo: Path, *args: str) -> tuple[int, str]:
    try:
        run = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    except OSError as exc:
        return 1, str(exc)
    return run.returncode, run.stdout.strip()


def verifier(memoire: str | Path, reference: str | None = None) -> dict:
    root = Path(memoire)
    errors: list[str] = []
    alerts: list[str] = []
    entries = {d: _read(root / f"{d}.jsonl", d, errors) for d in DOMAINS}

    ids: dict[str, str] = {}
    for d, es in entries.items():
        for e in es:
            if e.id in ids:
                errors.append(f"identifiant {e.id} en double ({ids[e.id]} et {d})")
            ids[e.id] = d
    active = {}
    for d, es in entries.items():
        known = {e.id for e in es}
        for e in es:
            if e.supersedes and e.supersedes not in known:
                errors.append(f"{d} : {e.id} remplace {e.supersedes}, inconnu dans ce domaine")
        replaced = {e.supersedes for e in es if e.supersedes}
        active[d] = [e for e in es if e.id not in replaced and e.status != "invalide"]

    for d in DOMAINS:
        by_key: dict[str, list[Entry]] = {}
        for e in active[d]:
            by_key.setdefault(e.key, []).append(e)
        for key, es in by_key.items():
            if len(es) < 2:
                continue
            ids_txt = ", ".join(e.id for e in es)
            if d == PERF and key.startswith(("pred:", "result:")):
                errors.append(f"{d} : {key} actif en double ({ids_txt})")
            elif len({json.dumps(e.value, sort_keys=True) for e in es}) > 1:
                errors.append(f"{d} : contradiction sur {key} ({ids_txt})")

    for e in active[PERF]:
        if e.key.startswith("pred:"):
            try:
                late = parse_dt(e.recorded_at) >= parse_dt(e.value["kickoff"])
            except (KeyError, TypeError, ValueError) as exc:
                errors.append(f"{e.key} : prévision mal formée ({exc})")
                continue
            if late:
                errors.append(f"{e.key} : enregistrée après le coup d'envoi")

    effectifs = {d: len(active[d]) for d in DOMAINS}
    ck_path = root / "checkpoint.json"
    ck = None
    if not ck_path.exists():
        alerts.append("aucun checkpoint : reprise sans état explicite")
    else:
        try:
            ck = json.loads(ck_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            errors.append(f"checkpoint.json illisible ({exc})")
    if ck:
        # checkpoint.save compte les effectifs puis note le checkpoint dans « travail » (en remplaçant le précédent)
        attendu = dict(effectifs)
        own = [e for e in active["travail"] if e.key == "checkpoint" and isinstance(e.value, dict)
               and e.value.get("id") == ck.get("id")]
        if own and not own[-1].supersedes:
            attendu["travail"] -= 1
        diff = {d: [ck.get("effectifs", {}).get(d), n] for d, n in attendu.items()
                if ck.get("effectifs", {}).get(d) != n}
        if diff:
            alerts.append(f"mémoire modifiée depuis le checkpoint (checkpoint, actuel) : {diff}")

    if ck and not ck.get("commit"):
        alerts.append("checkpoint sans commit : origine non traçable")
    repo_code, repo = _git(root, "rev-parse", "--show-toplevel")
    git = {"depot": repo if repo_code == 0 else None}
    if repo_code == 0:
        repo_path = Path(repo)
        git["head"] = _git(repo_path, "rev-parse", "HEAD")[1]
        commit = (ck or {}).get("commit")
        if commit:
            code, _ = _git(repo_path, "merge-base", "--is-ancestor", commit, "HEAD")
            git["checkpoint_ancetre_de_head"] = code == 0
            if code != 0:
                alerts.append(f"commit du checkpoint {commit} absent de l'historique de HEAD")
        if reference:
            code, behind = _git(repo_path, "rev-list", "--count", f"HEAD..{reference}")
            if code != 0:
                alerts.append(f"référence {reference} introuvable (git fetch ?)")
            else:
                git["retard_sur_reference"] = int(behind)
                if int(behind):
                    alerts.append(f"HEAD a {behind} commit(s) de retard sur {reference} : mettre à jour avant reprise")
        dirty = _git(repo_path, "status", "--porcelain", "--", str(root.resolve()))[1]
        if dirty:
            alerts.append("mémoire modifiée et non commitée : " + "; ".join(dirty.splitlines()[:5]))
    else:
        alerts.append("mémoire hors dépôt git : historique non vérifiable")

    return {"memoire": str(root), "checkpoint": {k: (ck or {}).get(k) for k in ("id", "commit", "date")},
            "effectifs": effectifs, "git": git, "erreurs": errors, "alertes": alerts, "ok": not errors}
