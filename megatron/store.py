"""Mémoire persistante en JSONL, append-only.

Chaque domaine (travail, decisions, football, performances, technique) est un
fichier ``<domaine>.jsonl``. Une entrée n'est jamais modifiée : la remplacer
consiste à écrire une nouvelle entrée qui pointe vers l'ancienne via
``supersedes``. L'historique est donc préservé et lisible avec ``git diff``.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

DOMAINS = ("travail", "decisions", "football", "performances", "technique")
STATUSES = ("verifie", "declare", "hypothese", "invalide")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_dt(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"date sans fuseau horaire : {value!r}")
    return dt


@dataclass(frozen=True)
class Entry:
    id: str
    domain: str
    key: str
    value: Any
    source: str
    status: str
    recorded_at: str
    observed_at: str | None = None
    supersedes: str | None = None
    meta: dict = field(default_factory=dict)


class MemoryStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, domain: str) -> Path:
        if domain not in DOMAINS:
            raise ValueError(f"domaine inconnu : {domain!r} (attendu : {DOMAINS})")
        return self.root / f"{domain}.jsonl"

    def entries(self, domain: str) -> list[Entry]:
        path = self._path(domain)
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as fh:
            return [Entry(**json.loads(line)) for line in fh if line.strip()]

    def record(
        self,
        domain: str,
        key: str,
        value: Any,
        *,
        source: str,
        status: str = "declare",
        observed_at: str | datetime | None = None,
        supersede: bool = True,
        recorded_at: str | datetime | None = None,
        meta: dict | None = None,
    ) -> Entry:
        """Ajoute une entrée.

        ``supersede=True`` remplace l'entrée active de même clé (l'ancienne
        reste dans l'historique). ``supersede=False`` garde les deux actives,
        ce que ``contradictions()`` signalera si les valeurs diffèrent.
        """
        if status not in STATUSES:
            raise ValueError(f"statut inconnu : {status!r} (attendu : {STATUSES})")
        if not source:
            raise ValueError("toute entrée doit indiquer sa provenance")
        previous = self.active(domain, key)
        entry = Entry(
            id=uuid.uuid4().hex[:12],
            domain=domain,
            key=key,
            value=value,
            source=source,
            status=status,
            recorded_at=parse_dt(recorded_at or now_utc()).isoformat(),
            observed_at=parse_dt(observed_at).isoformat() if observed_at else None,
            supersedes=previous[-1].id if (supersede and previous) else None,
            meta=meta or {},
        )
        with self._path(domain).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(entry), ensure_ascii=False, sort_keys=True) + "\n")
        return entry

    def active(self, domain: str, key: str | None = None) -> list[Entry]:
        entries = self.entries(domain)
        replaced = {e.supersedes for e in entries if e.supersedes}
        return [
            e for e in entries
            if e.id not in replaced and e.status != "invalide" and (key is None or e.key == key)
        ]

    def history(self, domain: str, key: str) -> list[Entry]:
        return [e for e in self.entries(domain) if e.key == key]

    def contradictions(self, domain: str) -> dict[str, list[Entry]]:
        by_key: dict[str, list[Entry]] = {}
        for e in self.active(domain):
            by_key.setdefault(e.key, []).append(e)
        return {
            k: v for k, v in by_key.items()
            if len({json.dumps(e.value, sort_keys=True) for e in v}) > 1
        }

    def stale(self, domain: str, max_age: timedelta, at: datetime | None = None) -> list[Entry]:
        at = at or now_utc()
        return [
            e for e in self.active(domain)
            if at - parse_dt(e.observed_at or e.recorded_at) > max_age
        ]

    def search(self, text: str, domains: Iterable[str] = DOMAINS) -> list[Entry]:
        """Recherche ciblée sur les entrées actives, pour ne charger que l'utile."""
        needle = text.lower()
        return [
            e for d in domains for e in self.active(d)
            if needle in e.key.lower() or needle in json.dumps(e.value, ensure_ascii=False).lower()
        ]
