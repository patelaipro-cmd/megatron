"""Collecte unique de l'historique xG Understat (5 ligues, 2014/15 à 2025/26) pour EXP-018.

Usage (workflow `xg-historique`, serveurs GitHub) : python scripts/collecte_xg_historique.py --sortie <externe/>
Écrit <sortie>/understat/historique/matchs_equipes_<saison>.csv (une ligne par équipe et par match,
xG du match, chiffre d'après-match) et <sortie>/understat/historique/manifeste.json.
Usage prévu : seul le passé d'un match sert à le prévoir. Understat peut avoir révisé son modèle
xG après coup : les valeurs collectées aujourd'hui ne sont pas forcément celles publiées à l'époque.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIGUES = json.loads((ROOT / "data" / "ligues_collecte.json").read_text(encoding="utf-8"))["understat"]
SAISONS = [f"{a}-{(a + 1) % 100:02d}" for a in range(2014, 2026)]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sortie", type=Path, required=True)
    a = p.parse_args(argv)
    import soccerdata as sd  # installé seulement dans le workflow

    dossier = a.sortie / "understat" / "historique"
    dossier.mkdir(parents=True, exist_ok=True)
    manifeste = {"ligues": LIGUES, "saisons": {}}
    for s in SAISONS:
        quand = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            df = sd.Understat(leagues=LIGUES, seasons=s).read_team_match_stats()
            df.reset_index().assign(collecte_le=quand).to_csv(dossier / f"matchs_equipes_{s}.csv", index=False)
            manifeste["saisons"][s] = {"lignes": len(df), "collecte_le": quand}
        except Exception as exc:  # une saison en échec n'arrête pas les autres
            manifeste["saisons"][s] = {"erreur": f"{type(exc).__name__}: {exc}"[:300], "collecte_le": quand}
        print(s, manifeste["saisons"][s], flush=True)
    (dossier / "manifeste.json").write_text(json.dumps(manifeste, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0 if any("lignes" in v for v in manifeste["saisons"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
