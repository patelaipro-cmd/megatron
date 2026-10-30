"""Audit descriptif hors réseau : compositions ESPN et cotes courantes ESPN.

La première collecte contenant deux onze complets sert de repère d'observation,
jamais d'heure de publication officielle. Aucune estimation d'avantage ni écriture
dans les données sources ou la mémoire.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


def instant(value):
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("fuseau requis")
    return d


def lignes(dossier):
    for p in sorted(Path(dossier).glob("*/*.csv")):
        with p.open(encoding="utf-8-sig", newline="") as f:
            yield from csv.DictReader(f)


def auditer(compos, cotes, au, fenetre_minutes=90):
    if au.tzinfo is None or fenetre_minutes <= 0:
        raise ValueError("date avec fuseau et fenêtre positive requises")
    captures = defaultdict(lambda: defaultdict(set))
    exclus = Counter()
    for r in compos:
        try:
            t, ko = instant(r["collecte_le"]), instant(r["coup_envoi"])
            key = (r["event_id"], r["division"], ko)
            if not all(key[:2]) or not r.get("equipe"):
                raise ValueError("identité absente")
            if t > au or t >= ko:
                exclus["compo_hors_temps"] += 1
                continue
            joueur = r.get("joueur_id") or r.get("joueur")
            if r.get("statut") == "titulaire" and joueur:
                captures[(key, t)][r["equipe"]].add(joueur)
        except (KeyError, ValueError, TypeError):
            exclus["compo_invalide"] += 1
    observations = {}
    for (key, t), equipes in sorted(captures.items(), key=lambda x: x[0][1]):
        if len(equipes) == 2 and all(len(v) == 11 for v in equipes.values()):
            observations.setdefault(key, (t, set(equipes)))
        else:
            exclus["capture_compo_incomplete"] += 1

    groupes = defaultdict(list)
    for r in cotes:
        if r.get("source") != "espn" or r.get("type_ligne") != "courante":
            exclus["cote_source_ou_type_exclu"] += 1
            continue
        try:
            t, ko = instant(r["collecte_le"]), instant(r["coup_envoi"])
            key = (r["evenement_id"], r["division"], ko)
            if not all(key[:2]) or not r.get("bookmaker") or not r.get("domicile") or not r.get("exterieur") or r["domicile"] == r["exterieur"]:
                raise ValueError("identité absente")
            if t > au or t >= ko:
                exclus["cote_hors_temps"] += 1
                continue
            odds = [float(r["cote_" + o]) for o in "HDA"]
            if any(not math.isfinite(v) or v <= 1 for v in odds):
                raise ValueError("cotes invalides")
            inv = [1 / v for v in odds]
            groupes[(key, r["bookmaker"], r.get("domicile"), r.get("exterieur"))].append(
                (t, [v / sum(inv) for v in inv]))
        except (KeyError, ValueError, TypeError):
            exclus["cote_invalide"] += 1

    paires, manquants = [], Counter()
    fenetre = timedelta(minutes=fenetre_minutes)
    for (key, book, home, away), serie in sorted(groupes.items()):
        if key not in observations:
            manquants["sans_deux_onze_complets"] += 1
            continue
        repere, equipes = observations[key]
        if equipes != {home, away}:
            manquants["equipes_non_concordantes"] += 1
            continue
        avant = [v for v in serie if repere - fenetre <= v[0] < repere]
        apres = [v for v in serie if repere < v[0] <= repere + fenetre]
        if not avant or not apres:
            manquants["sans_cote_avant" if not avant else "sans_cote_apres"] += 1
            continue
        pre, post = max(avant), min(apres)
        # Une capture contradictoire au même instant ne permet pas de choisir une cote.
        if any(len({tuple(p) for t, p in serie if t == borne}) > 1 for borne in (pre[0], post[0])):
            manquants["cotes_contradictoires"] += 1
            continue
        paires.append({"event_id": key[0], "division": key[1], "coup_envoi": key[2].isoformat(),
                       "bookmaker": book, "domicile": home, "exterieur": away,
                       "premiere_compo_complete_collectee_le": repere.isoformat(),
                       "cote_avant_collectee_le": pre[0].isoformat(),
                       "cote_apres_collectee_le": post[0].isoformat(),
                       "probabilites_sans_marge_avant": dict(zip("HDA", pre[1])),
                       "probabilites_sans_marge_apres": dict(zip("HDA", post[1])),
                       "mouvement_points": {o: round(100 * (post[1][i] - pre[1][i]), 6) for i, o in enumerate("HDA")}})
    return {"au": au.isoformat(), "fenetre_minutes": fenetre_minutes,
            "repere": "premiere_collecte_de_deux_onze_complets_pas_publication_officielle",
            "matchs_avec_compos_completes": len(observations), "series_cotes": len(groupes),
            "matchs_compos_sans_cote_courante": len(set(observations) - {k[0] for k in groupes}),
            "paires_match_bookmaker": len(paires), "matchs_apparies": len({(p['division'], p['event_id'], p['coup_envoi']) for p in paires}),
            "exclusions_lignes_ou_captures": dict(exclus), "series_non_appariees": dict(manquants),
            "paires": paires, "avantage_sur_marche": "NON_EVALUE",
            "limites": ["collecte ne prouve pas publication officielle ni réception de la nouvelle par le marché",
                        "horodatage de la cote chez le bookmaker inconnu ; seule la capture est datée",
                        "plusieurs bookmakers du même match ne sont pas des observations indépendantes",
                        "corners et cartons non couverts par ces fichiers 1X2",
                        "API-Football et football-data exclus : correspondance inter-fournisseurs non établie"]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dossier-externe", required=True, type=Path)
    p.add_argument("--au", type=instant, default=datetime.now(timezone.utc))
    p.add_argument("--sortie", type=Path)
    a = p.parse_args()
    if not a.dossier_externe.is_dir():
        p.error("dossier externe absent")
    out = auditer(lignes(a.dossier_externe / "espn/compos"), lignes(a.dossier_externe / "cotes/espn"), a.au)
    texte = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    if a.sortie:
        a.sortie.parent.mkdir(parents=True, exist_ok=True)
        a.sortie.write_text(texte, encoding="utf-8")
    print(texte, end="")


if __name__ == "__main__":
    main()
