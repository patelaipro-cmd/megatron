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


def lignes(dossier, champs, inventaire, source_legacy=None):
    dossier = Path(dossier)
    fichiers = sorted(dossier.glob("*/*.csv"))
    if not dossier.is_dir() or not fichiers:
        raise ValueError(f"source absente ou sans CSV : {dossier}")
    inventaire.update(fichiers=len(fichiers), lignes=0, source_legacy=0)
    for p in fichiers:
        with p.open(encoding="utf-8-sig", newline="") as f:
            lecteur = csv.DictReader(f)
            manquants = set(champs) - set(lecteur.fieldnames or [])
            if manquants:
                raise ValueError(f"schéma incomplet {p.name} : {sorted(manquants)}")
            for r in lecteur:
                inventaire["lignes"] += 1
                if source_legacy and "source" not in r:
                    # Ancien schéma du chemin dédié espn/compos, pas une inférence
                    # applicable à des fichiers quelconques ou à une source explicite.
                    r["source"] = source_legacy
                    inventaire["source_legacy"] += 1
                yield r


def auditer(compos, cotes, au, fenetre_minutes=90):
    if au.tzinfo is None or fenetre_minutes <= 0:
        raise ValueError("date avec fuseau et fenêtre positive requises")
    captures = defaultdict(lambda: defaultdict(set))
    exclus = Counter()
    legacy_marche = 0
    for r in compos:
        if r.get("source") != "espn":
            exclus["compo_source_exclue"] += 1
            continue
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
        if "marche" in r and r["marche"] != "1X2":
            exclus["cote_marche_exclu"] += 1
            continue
        if "marche" not in r:
            legacy_marche += 1  # schéma historique ESPN à triplet H/D/A uniquement
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
                (t, tuple(odds), [v / sum(inv) for v in inv]))
        except (KeyError, ValueError, TypeError):
            exclus["cote_invalide"] += 1

    paires, manquants, details = [], Counter(), []
    fenetre = timedelta(minutes=fenetre_minutes)
    for (key, book, home, away), serie in sorted(groupes.items()):
        detail = {"event_id": key[0], "division": key[1], "coup_envoi": key[2].isoformat(),
                  "bookmaker": book, "domicile": home, "exterieur": away}
        details.append(detail)
        if key not in observations:
            raison = ("division_ou_coup_envoi_non_concordant" if any(k[0] == key[0] for k in observations)
                      else "sans_deux_onze_complets")
            manquants[raison] += 1
            detail["statut"] = raison
            continue
        repere, equipes = observations[key]
        if equipes != {home, away}:
            manquants["equipes_non_concordantes"] += 1
            detail["statut"] = "equipes_non_concordantes"
            continue
        avant = [v for v in serie if repere - fenetre <= v[0] < repere]
        apres = [v for v in serie if repere < v[0] <= repere + fenetre]
        detail.update(captures_avant=len({v[0] for v in avant}), captures_apres=len({v[0] for v in apres}),
                      captures_simultanees=len({v[0] for v in serie if v[0] == repere}),
                      premiere_compo_complete_collectee_le=repere.isoformat())
        if not avant or not apres:
            raison = "sans_cote_avant_et_apres" if not avant and not apres else "sans_cote_avant" if not avant else "sans_cote_apres"
            manquants[raison] += 1
            detail["statut"] = raison
            continue
        pre, post = max(avant), min(apres)
        # Une capture contradictoire au même instant ne permet pas de choisir une cote.
        if any(len({odds for t, odds, _ in serie if t == borne}) > 1 for borne in (pre[0], post[0])):
            manquants["cotes_contradictoires"] += 1
            detail["statut"] = "cotes_contradictoires"
            continue
        detail["statut"] = "apparie"
        paires.append({"event_id": key[0], "division": key[1], "coup_envoi": key[2].isoformat(),
                       "bookmaker": book, "domicile": home, "exterieur": away,
                       "premiere_compo_complete_collectee_le": repere.isoformat(),
                       "cote_avant_collectee_le": pre[0].isoformat(),
                       "cote_apres_collectee_le": post[0].isoformat(),
                       "publication_officielle_le": None, "marche": "1X2",
                       "cotes_avant": dict(zip("HDA", pre[1])), "cotes_apres": dict(zip("HDA", post[1])),
                       "surcote_avant": sum(1 / o for o in pre[1]) - 1,
                       "surcote_apres": sum(1 / o for o in post[1]) - 1,
                       "probabilites_sans_marge_avant": dict(zip("HDA", pre[2])),
                       "probabilites_sans_marge_apres": dict(zip("HDA", post[2])),
                       "mouvement_points": {o: round(100 * (post[2][i] - pre[2][i]), 6) for i, o in enumerate("HDA")}})
    return {"au": au.isoformat(), "fenetre_minutes": fenetre_minutes,
            "repere": "premiere_collecte_de_deux_onze_complets_pas_publication_officielle",
            "matchs_avec_compos_completes": len(observations), "series_cotes": len(groupes),
            "matchs_compos_sans_cote_courante": len(set(observations) - {k[0] for k in groupes}),
            "paires_match_bookmaker": len(paires), "matchs_apparies": len({(p['division'], p['event_id'], p['coup_envoi']) for p in paires}),
            "exclusions_lignes_ou_captures": dict(exclus), "series_non_appariees": dict(manquants),
            "diagnostic_series": details, "lignes_cotes_schema_legacy_1x2": legacy_marche,
            "compos_sans_cote_courante": [{"event_id": k[0], "division": k[1], "coup_envoi": k[2].isoformat(),
                                          "equipes": sorted(observations[k][1])}
                                         for k in sorted(set(observations) - {g[0] for g in groupes})],
            "paires": paires, "avantage_sur_marche": "NON_EVALUE",
            "limites": ["collecte ne prouve pas publication officielle ni réception de la nouvelle par le marché",
                        "horodatage de la cote chez le bookmaker inconnu ; seule la capture est datée",
                        "plusieurs bookmakers du même match ne sont pas des observations indépendantes",
                        "corners et cartons non couverts par ces fichiers 1X2",
                        "API-Football et football-data exclus : correspondance inter-fournisseurs non établie"]}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dossier-externe", required=True, type=Path)
    p.add_argument("--au", type=instant, default=datetime.now(timezone.utc))
    p.add_argument("--sortie", type=Path)
    a = p.parse_args(argv)
    if not a.dossier_externe.is_dir():
        p.error("dossier externe absent")
    inventaire = {"compos": {}, "cotes": {}}
    try:
        out = auditer(lignes(a.dossier_externe / "espn/compos",
                             ("event_id", "division", "coup_envoi", "collecte_le", "equipe", "statut", "joueur_id"),
                             inventaire["compos"], source_legacy="espn"),
                      lignes(a.dossier_externe / "cotes/espn",
                             ("evenement_id", "division", "coup_envoi", "collecte_le", "domicile", "exterieur",
                              "source", "bookmaker", "type_ligne", "cote_H", "cote_D", "cote_A"),
                             inventaire["cotes"]), a.au)
    except (OSError, ValueError, csv.Error) as exc:
        p.error(str(exc))
    out["entrees"] = inventaire
    texte = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    if a.sortie:
        a.sortie.parent.mkdir(parents=True, exist_ok=True)
        a.sortie.write_text(texte, encoding="utf-8")
    print(texte, end="")


if __name__ == "__main__":
    main()
