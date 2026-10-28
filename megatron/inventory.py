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
            "module": ev.get("module", ""),
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
    par_classe = {c: [r for r in rows if r["classement"] == c] for c in CLASSES}
    out = [
        "# Registre d'évaluation des dépôts",
        "",
        "Généré par `python -m megatron inventaire`. Ne pas éditer à la main :",
        "les vérifications se consignent dans `docs/evaluations.json`.",
        "",
        f"- Entrées dans les inventaires : **{total}** "
        f"({', '.join(f'{k}: {v}' for k, v in sorted(counts.items()))})",
        f"- Dépôts uniques : **{len(rows)}**, évalués : **{len(evalues)}**",
        "- " + " · ".join(f"{c} : **{len(v)}**" for c, v in par_classe.items() if v),
        "",
    ]
    for classe in ("INTÉGRER", "TESTER"):
        lignes = sorted(par_classe[classe], key=lambda r: (r["motif"][:2], r["module"]))
        if not lignes:
            continue
        out += [f"## {classe}", "", "| Dépôt | Module | Licence | Vérification | Motif |", "|---|---|---|---|---|"]
        out += [f"| {r['depot']} | {r['module']} | {r['licence']} | {r['verifications']} | {r['motif']} |" for r in lignes]
        out.append("")
    for classe in ("RÉFÉRENCE", "REDONDANT", "REJETER", "À VÉRIFIER"):
        lignes = sorted(par_classe[classe], key=lambda r: (r["module"], r["depot"]))
        if not lignes:
            continue
        out += [f"## {classe} ({len(lignes)})", "", "| Dépôt | Module | Motif |", "|---|---|---|"]
        out += [f"| {r['depot']} | {r['module']} | {r['motif']} |" for r in lignes]
        out.append("")
    out += ["## Doublons entre inventaires", "", "| Dépôt | Inventaires |", "|---|---|"]
    out += [f"| {r['depot']} | {r['inventaires']} |" for r in doublons]
    return "\n".join(out) + "\n"


def build(inventory_dir: Path, evaluations_path: Path) -> tuple[list[dict], dict[str, int]]:
    repos, counts = parse(sorted(inventory_dir.glob("depots-github-*.md")))
    evaluations = json.loads(evaluations_path.read_text(encoding="utf-8")) if evaluations_path.exists() else {}
    unknown = set(evaluations) - set(repos)
    if unknown:
        raise ValueError(f"évaluations pour des dépôts absents des inventaires : {sorted(unknown)}")
    return registry(repos, evaluations), counts
