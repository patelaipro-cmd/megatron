"""Validation d'un point d'accès (Codex, Claude Code ou autre) : une seule commande.

Usage, depuis la racine du dépôt : python scripts/valider_acces.py [--acces codex]

Sans appel LLM (clés retirées de l'environnement des tests, agent Stats seul)
et sans toucher à memoire/ : tout parcours s'exécute en mémoire temporaire.
Étapes : état git, reprise du checkpoint, synchro verifier, suite complète des tests, parcours
fictif (prévision, doublon, résultat, bilan, relecture, reprise), contrôle
que memoire/ est inchangée. Code de sortie 0 seulement si tout passe.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LLM_KEYS = ("GEMINI_API_KEY", "DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY")


def _hashes() -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / "memoire").glob("*"))}


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "inconnu"


def parcours_fictif() -> dict[str, bool]:
    sys.path.insert(0, str(ROOT))
    from megatron import checkpoint, suivi
    from megatron.agents import StatsAgent
    from megatron.ledger import Ledger
    from megatron.store import MemoryStore, parse_dt

    checks = {}
    with tempfile.TemporaryDirectory() as tmp:
        st = MemoryStore(tmp)
        ko = parse_dt("2099-01-01T12:00:00Z")
        before = ko - timedelta(hours=3)
        tasks = [{"match_id": f"FICTIF:{i}", "xg_home": h, "xg_away": a}
                 for i, (h, a) in enumerate([(1.6, 0.9), (1.0, 1.4), (1.2, 1.2)])]
        for t in tasks:
            suivi.prevoir(st, t, ko, agents=[StatsAgent()], now=before)
        perf = st.root / "performances.jsonl"
        h1 = hashlib.sha256(perf.read_bytes()).hexdigest()
        preds = {p.key: p.value for p in Ledger(st)._predictions()}
        checks["prevision"] = len(preds) == 2 * len(tasks)
        try:
            suivi.prevoir(st, tasks[0], ko, agents=[StatsAgent()], now=before)
            checks["doublon_refuse"] = False
        except ValueError:
            checks["doublon_refuse"] = True
        checks["registre_intact_apres_doublon"] = hashlib.sha256(perf.read_bytes()).hexdigest() == h1
        try:
            suivi.prevoir(st, {"match_id": "FICTIF:9", "xg_home": 1, "xg_away": 1}, ko,
                          agents=[StatsAgent()], now=ko)
            checks["apres_coup_envoi_refuse"] = False
        except ValueError:
            checks["apres_coup_envoi_refuse"] = True
        for t, sc in zip(tasks, ["2-0", "1-1", "0-3"]):
            suivi.resultat(st, t["match_id"], sc, source="validation", observed_at=ko + timedelta(hours=2))
        try:
            suivi.resultat(st, "FICTIF:0", "0-0", source="validation", observed_at=ko + timedelta(hours=3))
            checks["second_resultat_refuse"] = False
        except ValueError:
            checks["second_resultat_refuse"] = True
        b = suivi.bilan(st, now=ko + timedelta(days=1))
        checks["bilan"] = b["communs"]["n"] == len(tasks) and not b["resultats_a_saisir"]
        ck = checkpoint.save(st, resume="validation", prochaines_actions=[], blocages=[])
        st2 = MemoryStore(tmp)
        checks["relecture"] = {p.key: p.value for p in Ledger(st2)._predictions()} == preds
        checks["reprise"] = (checkpoint.load(st2) or {}).get("id") == ck["id"]
    return checks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--acces", default="inconnu", help="nom du point d'accès, ex. codex ou claude")
    acces = ap.parse_args().acces
    for k in LLM_KEYS:  # aucun appel fournisseur possible pendant la validation
        os.environ.pop(k, None)
    avant = _hashes()
    rapport = {"acces": acces, "branche": _git("rev-parse", "--abbrev-ref", "HEAD"),
               "commit": _git("rev-parse", "HEAD"), "modifications_locales": _git("status", "--short") or "aucune"}
    sys.path.insert(0, str(ROOT))
    from megatron import checkpoint
    from megatron.store import MemoryStore
    ck = checkpoint.load(MemoryStore(ROOT / "memoire")) or {}
    rapport["checkpoint"] = {"id": ck.get("id"), "commit": ck.get("commit"), "date": ck.get("date")}
    from megatron import synchro
    sy = synchro.verifier(ROOT / "memoire")
    rapport["synchro"] = {"ok": sy["ok"], "erreurs": sy["erreurs"], "alertes": sy["alertes"]}
    tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                           cwd=ROOT, capture_output=True, text=True)
    rapport["tests"] = {"ok": tests.returncode == 0, "fin": tests.stderr.strip().splitlines()[-3:]}
    rapport["parcours_fictif"] = parcours_fictif()
    rapport["memoire_inchangee"] = _hashes() == avant
    rapport["succes"] = (rapport["tests"]["ok"] and rapport["synchro"]["ok"] and all(rapport["parcours_fictif"].values())
                         and rapport["memoire_inchangee"])
    print(json.dumps(rapport, indent=2, ensure_ascii=False))
    return 0 if rapport["succes"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
