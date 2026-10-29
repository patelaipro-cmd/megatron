"""Jeton coopératif du registre et verrou local. Aucun verrou distribué Git."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import json
import os
from pathlib import Path

from .store import MemoryStore

KEY = "jeton_registre"
ACCES = ("codex", "claude")
REAL_MEMORY = Path(__file__).resolve().parent.parent / "memoire"
_HELD = ContextVar("megatron_registre_locks", default=())


class JetonError(ValueError):
    """Écriture refusée sans changement du registre."""


def _current(store):
    entries = store.active("travail", KEY)
    if len(entries) > 1:
        raise JetonError("plusieurs jetons actifs : réconciliation obligatoire")
    if not entries:
        if store.history("travail", KEY):
            raise JetonError("historique de jeton sans détenteur actif : réconciliation obligatoire")
        return None
    e = entries[0]
    if not isinstance(e.value, dict) or e.value.get("detenteur") not in ACCES:
        raise JetonError("jeton mal formé : détenteur attendu codex ou claude")
    if e.value.get("precedent") != e.supersedes:
        raise JetonError("précédent du jeton incohérent avec supersedes")
    return e


def statut(store):
    e = _current(store)
    return {"protege": e is not None or store.root.resolve() == REAL_MEMORY.resolve(),
            "initialise": e is not None, "id": e.id if e else None,
            "detenteur": e.value["detenteur"] if e else None}


@contextmanager
def _lock(store):
    """Création exclusive portable Windows/Linux ; aucun déverrouillage forcé."""
    path = store.root / ".registre.lock"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise JetonError("registre occupé (.registre.lock) ; vérifier le processus, ne pas forcer") from None
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"pid": os.getpid()}, fh)
        yield
    finally:
        path.unlink()


def _check(store, acces, expected):
    e = _current(store)
    if e is None:
        raise JetonError("jeton non initialisé ; initialisation explicite requise")
    if acces != e.value["detenteur"]:
        raise JetonError(f"accès {acces!r} refusé : détenteur {e.value['detenteur']}")
    if not expected or expected != e.id:
        raise JetonError("identifiant du jeton absent ou périmé : relire le jeton synchronisé")
    return e


@contextmanager
def ecriture(store, acces=None, jeton_id=None):
    # Les anciennes simulations isolées sans jeton restent utilisables.
    protected = store.root.resolve() == REAL_MEMORY.resolve() or bool(store.history("travail", KEY))
    if not protected:
        yield
        return
    identity = (str(store.root.resolve()), acces, jeton_id)
    if identity in _HELD.get():
        _check(store, acces, jeton_id)
        yield
        return
    with _lock(store):
        _check(store, acces, jeton_id)
        token = _HELD.set(_HELD.get() + (identity,))
        try:
            yield
        finally:
            _HELD.reset(token)


def initialiser(store, acces, *, source):
    if acces not in ACCES or not source:
        raise JetonError("accès codex/claude et source non vide requis")
    with _lock(store):
        if _current(store) is not None:
            raise JetonError("jeton déjà initialisé : utiliser transmettre")
        return store.record("travail", KEY, {"detenteur": acces, "precedent": None},
                            source=source, status="verifie")


def transmettre(store, acces, jeton_id, destinataire, *, source):
    if destinataire not in ACCES or not source:
        raise JetonError("destinataire codex/claude et source non vide requis")
    # Un transfert ne doit pas intervenir dans une prévision en cours.
    if any(x[0] == str(store.root.resolve()) for x in _HELD.get()):
        raise JetonError("transfert interdit pendant une écriture")
    with _lock(store):
        previous = _check(store, acces, jeton_id)
        if destinataire == acces:
            raise JetonError("le destinataire détient déjà le jeton")
        return store.record("travail", KEY, {"detenteur": destinataire, "precedent": previous.id},
                            source=source, status="verifie")


def protege_ledger(fn):
    @wraps(fn)
    def wrapped(self, *args, **kwargs):
        with ecriture(self.store, self.acces, self.jeton_id):
            return fn(self, *args, **kwargs)
    return wrapped


def protege_suivi(fn):
    @wraps(fn)
    def wrapped(store, *args, **kwargs):
        with ecriture(store, kwargs.get("acces"), kwargs.get("jeton_id")):
            return fn(store, *args, **kwargs)
    return wrapped
