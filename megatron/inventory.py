"""Lecture des inventaires de dépôts et registre d'évaluation.

Les inventaires sont des pistes, pas des preuves : chaque dépôt démarre en
« À VÉRIFIER » et ne change de classement que via ``docs/evaluations.json``,
qui consigne les vérifications réellement faites.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

CLASSES = ("INTÉGRER", "TESTER", "RÉFÉRENCE", "REDONDANT", "REJETER", "À VÉRIFIER")
_LINK = re.compile(r"\[([^\]]+)\]\(https://github\.com/([^/\s)]+)/([^/\s)#?]+)[^)]*\)")


@dataclass
class Repo:
    slug: str  # owner/name en minuscules
    fichiers: list[str] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)
    recommande: bool = False


def parse(paths: list[Path]) -> tuple[dict[str, Repo], dict[str, int]]:
    repos: dict[str, Repo] = {}
    counts: dict[str, int] = {}
    for path in paths:
        n = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|"):
                continue
            for m in _LINK.finditer(line):
                n += 1
                slug = f"{m[2]}/{m[3]}".lower()
                repo = repos.setdefault(slug, Repo(slug))
                if path.name not in repo.fichiers:
                    repo.fichiers.append(path.name)
                cells = [c.strip() for c in line.strip("|").split("|")]
                if cells:
                    repo.descriptions.append(cells[-1])
                repo.recommande |= "★" in line
        counts[path.name] = n
    return repos, counts


def registry(repos: dict[str, Repo], evaluations: dict[str, dict]) -> list[dict]:
    rows = []
    for slug, repo in sorted(repos.items()):
        ev = evaluations.get(slug, {})
        classe = ev.get("classement", "À VÉRIFIER")
        if classe not in CLASSES:
            raise ValueError(f"{slug} : classement inconnu {classe!r}")
        rows.append({
            "depot": slug,
            "role": ev.get("role") or (repo.descriptions[0] if repo.descriptions else ""),
            "verifications": ev.get("verifications", "aucune"),
            "licence": ev.get("licence", "non vérifiée"),
            "compatibilite": ev.get("compatibilite", "non vérifiée"),
            "classement": classe,
            "motif": ev.get("motif", ""),
            "inventaires": ", ".join(f.removeprefix("depots-github-").removesuffix(".md") for f in repo.fichiers),
            "recommande_inventaire": repo.recommande,
        })
    return rows


def render_markdown(rows: list[dict], counts: dict[str, int]) -> str:
    total = sum(counts.values())
    doublons = [r for r in rows if "," in r["inventaires"]]
    evalues = [r for r in rows if r["classement"] != "À VÉRIFIER"]
    out = [
        "# Registre d'évaluation des dépôts",
        "",
        "Généré par `python -m megatron inventaire`. Ne pas éditer à la main :",
        "les vérifications se consignent dans `docs/evaluations.json`.",
        "",
        f"- Entrées dans les inventaires : **{total}** "
        f"({', '.join(f'{k}: {v}' for k, v in sorted(counts.items()))})",
        f"- Dépôts uniques : **{len(rows)}**",
        f"- Dépôts présents dans plusieurs inventaires : **{len(doublons)}**",
        f"- Dépôts évalués : **{len(evalues)}** ; les autres restent « À VÉRIFIER ».",
        "",
        "## Dépôts évalués",
        "",
        "| Dépôt | Rôle potentiel | Vérifications réalisées | Licence et contraintes | Compatibilité | Classement motivé |",
        "|---|---|---|---|---|---|",
    ]
    for r in evalues:
        out.append(f"| {r['depot']} | {r['role']} | {r['verifications']} | {r['licence']} | "
                   f"{r['compatibilite']} | **{r['classement']}** : {r['motif']} |")
    out += ["", "## Doublons entre inventaires", "", "| Dépôt | Inventaires |", "|---|---|"]
    out += [f"| {r['depot']} | {r['inventaires']} |" for r in doublons]
    return "\n".join(out) + "\n"


def build(inventory_dir: Path, evaluations_path: Path) -> tuple[list[dict], dict[str, int]]:
    repos, counts = parse(sorted(inventory_dir.glob("depots-github-*.md")))
    evaluations = json.loads(evaluations_path.read_text(encoding="utf-8")) if evaluations_path.exists() else {}
    unknown = set(evaluations) - set(repos)
    if unknown:
        raise ValueError(f"évaluations pour des dépôts absents des inventaires : {sorted(unknown)}")
    return registry(repos, evaluations), counts
