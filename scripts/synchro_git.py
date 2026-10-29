"""Test de synchronisation Codex ↔ Claude par Git, sur une mémoire fictive.

La mémoire testée est ``essais/synchro_git/memoire`` (jamais ``memoire/``) et
vit seulement sur des branches de test, jamais fusionnées dans main. Aucun LLM,
réseau bloqué dans le processus. Le script n'exécute aucune commande git qui
écrit : commit et push restent à l'opérateur (commandes affichées).

Étapes, chacune depuis la racine du dépôt :
  claude      départ : 3 prévisions fictives, checkpoint, synchro verifier
  codex       reprise après git pull : contrôles, doublon refusé, 3 scores, checkpoint
  retour      reprise côté Claude après fusion de la branche Codex : tout vérifier
  divergence  bac à sable git local : deux branches prévoient le même match,
              fusion par union des lignes, synchro verifier doit refuser

Code de sortie 0 seulement si tous les contrôles passent.
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEST = ROOT / "essais" / "synchro_git"
MEMOIRE = TEST / "memoire"
MANIFESTE = TEST / "manifeste_claude.json"
KO = "2099-01-01T12:00:00+00:00"
TACHES = [{"match_id": f"FICTIF:GIT:{i}", "xg_home": h, "xg_away": a, "fictif": True}
          for i, (h, a) in enumerate([(1.6, 0.9), (1.0, 1.4), (1.2, 1.2)], 1)]
SCORES = ["2-0", "1-1", "0-3"]


def _block_network() -> None:
    def blocked(*a, **kw):
        raise RuntimeError("réseau interdit pendant le test de synchronisation")
    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    socket.create_connection = blocked


def _git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True).stdout.strip()


def _preds(st) -> dict:
    from megatron.ledger import Ledger
    return {p.id: p.value for p in Ledger(st)._predictions()}


def _verifier(memoire: Path, reference: str | None = None) -> dict:
    from megatron import synchro
    return synchro.verifier(memoire, reference)


def etape_claude() -> dict:
    from megatron import checkpoint, jeton, suivi
    from megatron.agents import StatsAgent
    from megatron.store import MemoryStore, parse_dt
    if MEMOIRE.exists():
        raise SystemExit("REFUS : essais/synchro_git/memoire existe déjà ; l'étape claude ne se rejoue pas")
    st = MemoryStore(MEMOIRE)
    ko = parse_dt(KO)
    for t in TACHES:
        suivi.prevoir(st, t, ko, agents=[StatsAgent()], source="synchro-git:claude", now=ko - timedelta(hours=3))
    tok = jeton.initialiser(st, "claude", source="synchro-git:claude")
    jeton.transmettre(st, "claude", tok.id, "codex", source="synchro-git:claude")
    ck = checkpoint.save(st, resume="TEST SYNCHRO GIT : départ Claude ; jeton à Codex",
                         prochaines_actions=["Codex : reprendre, saisir les 3 scores"])
    MANIFESTE.write_text(json.dumps({"commit_depart": _git("rev-parse", "HEAD"), "checkpoint": ck["id"],
                                     "previsions": _preds(st)}, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    sy = _verifier(MEMOIRE)
    checks = {"previsions": len(_preds(st)) == 2 * len(TACHES), "synchro_ok": sy["ok"]}
    return {"etape": "claude", "checks": checks, "checkpoint": ck["id"], "synchro": sy,
            "a_faire": ["git add essais/synchro_git", "git commit -m 'Test synchro git : départ Claude'",
                        "git push origin <branche>"]}


def _reprise_communes(st, manifeste: dict, reference: str | None) -> dict:
    sy = _verifier(MEMOIRE, reference)
    return {"synchro_ok": sy["ok"], "previsions_identiques": _preds(st) == manifeste["previsions"],
            "manifeste_suivi_par_git": bool(_git("log", "--format=%H", "-1", "--", str(MANIFESTE)))}, sy


def etape_codex(reference: str | None) -> dict:
    from megatron import checkpoint, jeton, suivi
    from megatron.agents import StatsAgent
    from megatron.store import MemoryStore, parse_dt
    manifeste = json.loads(MANIFESTE.read_text(encoding="utf-8"))
    st = MemoryStore(MEMOIRE)
    checks, sy = _reprise_communes(st, manifeste, reference)
    ck = checkpoint.load(st) or {}
    checks["checkpoint_depart_repris"] = ck.get("id") == manifeste["checkpoint"]
    tok = jeton.statut(st)
    checks["jeton_pour_codex"] = tok["detenteur"] == "codex"
    checks["commit_depart_ancetre"] = subprocess.run(
        ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", manifeste["commit_depart"], "HEAD"]).returncode == 0
    if not all(checks.values()):
        return {"etape": "codex", "checks": checks, "synchro": sy}
    ko = parse_dt(KO)
    perf = MEMOIRE / "performances.jsonl"
    before = perf.read_bytes()
    try:
        suivi.prevoir(st, TACHES[0], ko, agents=[StatsAgent()], source="synchro-git:codex", now=ko - timedelta(hours=2),
                      acces="codex", jeton_id=tok["id"])
        checks["doublon_refuse_sans_ecriture"] = False
    except jeton.JetonError:
        checks["doublon_refuse_sans_ecriture"] = False
    except ValueError:
        checks["doublon_refuse_sans_ecriture"] = perf.read_bytes() == before
    for t, s in zip(TACHES, SCORES):
        suivi.resultat(st, t["match_id"], s, source="synchro-git:codex", observed_at=ko + timedelta(hours=2),
                       acces="codex", jeton_id=tok["id"])
    jeton.transmettre(st, "codex", tok["id"], "claude", source="synchro-git:codex")
    new = checkpoint.save(st, resume="TEST SYNCHRO GIT : scores saisis par Codex ; jeton à Claude",
                          prochaines_actions=["Claude : fusionner la branche Codex et vérifier"])
    checks["previsions_identiques"] = _preds(st) == manifeste["previsions"]
    checks["synchro_ok_apres"] = _verifier(MEMOIRE)["ok"]
    return {"etape": "codex", "checks": checks, "checkpoint": new["id"], "synchro": sy,
            "a_faire": ["git add essais/synchro_git", "git commit -m 'Test synchro git : étape Codex'",
                        "git push -u origin codex/synchro-git"]}


def etape_retour(reference: str | None) -> dict:
    from megatron import checkpoint, jeton, suivi
    from megatron.store import MemoryStore, parse_dt
    manifeste = json.loads(MANIFESTE.read_text(encoding="utf-8"))
    st = MemoryStore(MEMOIRE)
    checks, sy = _reprise_communes(st, manifeste, reference)
    ck = checkpoint.load(st) or {}
    checks["checkpoint_codex_repris"] = ck.get("id") != manifeste["checkpoint"] and "Codex" in ck.get("resume", "")
    checks["checkpoint_commit_ancetre"] = bool(sy["git"].get("checkpoint_ancetre_de_head"))
    checks["jeton_pour_claude"] = jeton.statut(st)["detenteur"] == "claude"
    b = suivi.bilan(st, now=parse_dt(KO) + timedelta(days=1))
    checks["trois_matchs_resolus"] = b["communs"]["n"] == 3 and not b["resultats_a_saisir"]
    sources = {e.source for e in st.active("performances") if e.key.startswith("result:")}
    checks["scores_venus_de_codex"] = sources == {"synchro-git:codex"}
    return {"etape": "retour", "checks": checks, "checkpoint": ck.get("id"), "synchro": sy}


def etape_divergence() -> dict:
    """Bac à sable : deux clones prévoient le même match, union des lignes, refus attendu."""
    from megatron import suivi
    from megatron.agents import StatsAgent
    from megatron.store import MemoryStore, parse_dt
    checks = {}
    with tempfile.TemporaryDirectory() as tmp:
        bare, a, b = Path(tmp) / "distant.git", Path(tmp) / "codex", Path(tmp) / "claude"
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
        for clone, nom in ((a, "codex"), (b, "claude")):
            subprocess.run(["git", "clone", "-q", str(bare), str(clone)], check=True, capture_output=True)
            _git("config", "user.email", f"{nom}@test", cwd=clone)
            _git("config", "user.name", nom, cwd=clone)
            _git("config", "commit.gpgsign", "false", cwd=clone)
        mem = lambda c: MemoryStore(c / "memoire")
        ko = parse_dt(KO)
        mem(a).record("decisions", "base", "test", source="t", status="verifie")
        _git("add", "-A", cwd=a)
        _git("commit", "-q", "-m", "base", cwd=a)
        _git("push", "-q", "origin", "HEAD:main", cwd=a)
        _git("fetch", "-q", "origin", cwd=b)
        _git("switch", "-q", "-c", "main", "origin/main", cwd=b)
        for clone in (a, b):  # même match prévu des deux côtés, sans se voir
            suivi.prevoir(mem(clone), TACHES[0], ko, agents=[StatsAgent()], source=clone.name,
                          now=ko - timedelta(hours=3))
            _git("add", "-A", cwd=clone)
            _git("commit", "-q", "-m", f"prévision {clone.name}", cwd=clone)
        _git("push", "-q", "origin", "HEAD:main", cwd=a)
        _git("fetch", "-q", "origin", cwd=b)
        merge = subprocess.run(["git", "-C", str(b), "merge", "-q", "origin/main"], capture_output=True, text=True)
        checks["conflit_git_signale"] = merge.returncode != 0
        checks["marqueurs_detectes"] = any("marqueur de conflit" in e for e in _verifier(b / "memoire")["erreurs"])
        # résolution naïve par union des lignes (ce que ferait merge=union)
        for f in (b / "memoire").glob("*.jsonl"):
            lines = [l for l in f.read_text(encoding="utf-8").splitlines()
                     if l and not l.startswith(("<<<<<<< ", "=======", ">>>>>>> "))]
            f.write_text("\n".join(dict.fromkeys(lines)) + "\n", encoding="utf-8")
        sy = _verifier(b / "memoire")
        checks["union_refusee"] = not sy["ok"] and any("actif en double" in e for e in sy["erreurs"])
    return {"etape": "divergence", "checks": checks, "erreurs_union": sy["erreurs"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("etape", choices=["claude", "codex", "retour", "divergence"])
    ap.add_argument("--reference", help="ex. origin/<branche> : signale un retard avant reprise")
    args = ap.parse_args()
    _block_network()
    sys.path.insert(0, str(ROOT))
    out = {"claude": etape_claude, "divergence": etape_divergence}.get(args.etape)
    rapport = out() if out else (etape_codex if args.etape == "codex" else etape_retour)(args.reference)
    rapport["commit"] = _git("rev-parse", "HEAD")
    rapport["succes"] = all(rapport["checks"].values())
    print(json.dumps(rapport, indent=2, ensure_ascii=False))
    return 0 if rapport["succes"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
