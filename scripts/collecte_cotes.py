"""Collecte d'instantanés de cotes 1X2 avant match (aucun effet sur les probabilités ni les décisions).

Usage (workflow `cotes`, serveurs GitHub) : python scripts/collecte_cotes.py --sortie <externe/> [--maintenant ISO]

Sources (deux familles) :
- ESPN, tableau des scores des 5 ligues (aujourd'hui et demain, UTC) : cotes DraftKings affichées
  par ESPN, ligne courante au moment de la capture (champ `close` d'ESPN) et ligne d'ouverture
  (`open`), cotes américaines converties en décimales. Matchs non commencés seulement.
- football-data.co.uk `fixtures.csv` : cotes de plusieurs bookmakers pour les matchs à venir,
  relevées par football-data à des moments qu'il ne publie pas ligne par ligne ; seule l'heure de
  notre capture est connue. Écrit seulement quand le fichier change.

Chaque ligne porte : source, bookmaker, match (ligue, coup d'envoi, équipes de la source), cotes
décimales H/D/A, heure de capture UTC, minutes avant le coup d'envoi, horizon (T-60, T-30, T-5 ou
« hors_fenetre »), URL, SHA-256 de la réponse brute. Une fenêtre sans capture reste absente
(INCONNU au rapport) : aucune cote n'est reconstituée, aucune cote de clôture n'est prise pour une
cote T-60. Erreurs et effectifs dans <sortie>/cotes/journal.jsonl.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard?dates={jour}"
FOOTBALL_DATA = "https://www.football-data.co.uk/fixtures.csv"
LIGUES = {"E0": "eng.1", "F1": "fra.1", "D1": "ger.1", "SP1": "esp.1", "I1": "ita.1"}
HORIZONS = {"T-60": (45, 75), "T-30": (20, 45), "T-5": (0, 20)}  # minutes avant le coup d'envoi, [bas, haut[
COLONNES = ("collecte_le", "source", "bookmaker", "type_ligne", "division", "coup_envoi", "domicile", "exterieur",
            "evenement_id", "cote_H", "cote_D", "cote_A", "minutes_avant", "horizon", "url", "sha256_brut", "marche")
HEADERS = {"User-Agent": "MEGATRON-cotes/1.0", "Accept": "application/json, text/csv, */*"}


def lire_url(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30) as r:
        return r.read()


def americaine(cote) -> float | None:
    """Cote américaine (« -120 », « +295 », 295) → décimale ; None si absente ou illisible."""
    try:
        v = float(str(cote).replace("+", ""))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    if v >= 100:
        return round(1 + v / 100, 4)
    if v <= -100:
        return round(1 + 100 / -v, 4)
    return None


def horizon(minutes: float) -> str:
    for nom, (lo, hi) in HORIZONS.items():
        if lo <= minutes < hi:
            return nom
    return "hors_fenetre"


def lignes_espn(div: str, corps: bytes, url: str, maintenant: datetime) -> list[dict]:
    sha = hashlib.sha256(corps).hexdigest()
    out = []
    for ev in json.loads(corps).get("events") or []:
        comp = (ev.get("competitions") or [{}])[0]
        status = ((comp.get("status") or ev.get("status") or {}).get("type") or {})
        if status.get("state") != "pre" or status.get("name") in (
                "STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_CANCELLED", "STATUS_SUSPENDED"):
            continue
        equipes = {c.get("homeAway"): (c.get("team") or {}).get("displayName") for c in comp.get("competitors") or []}
        debut = datetime.fromisoformat((ev.get("date") or comp.get("date")).replace("Z", "+00:00"))
        minutes = (debut - maintenant) / timedelta(minutes=1)
        if minutes <= 0:
            continue  # un statut fournisseur « pre » peut être périmé
        for o in comp.get("odds") or []:
            ml = o.get("moneyline") or {}
            for type_ligne in ("close", "open"):
                c = {k: americaine(((ml.get(cote) or {}).get(type_ligne) or {}).get("odds")) for k, cote in
                     (("H", "home"), ("D", "draw"), ("A", "away"))}
                if c["D"] is None and type_ligne == "close":
                    c["D"] = americaine((o.get("drawOdds") or {}).get("moneyLine"))
                if None in c.values():
                    continue
                out.append({"collecte_le": maintenant.isoformat(timespec="seconds"), "source": "espn",
                            "bookmaker": (o.get("provider") or {}).get("name", "?"),
                            "type_ligne": "courante" if type_ligne == "close" else "ouverture", "division": div,
                            "coup_envoi": debut.isoformat(timespec="minutes"), "domicile": equipes.get("home"),
                            "exterieur": equipes.get("away"), "evenement_id": str(ev.get("id")),
                            "cote_H": c["H"], "cote_D": c["D"], "cote_A": c["A"], "minutes_avant": round(minutes, 1),
                            "horizon": horizon(minutes) if type_ligne == "close" else "ouverture",
                            "url": url, "sha256_brut": sha, "marche": "1X2"})
    return out


def lignes_football_data(corps: bytes, maintenant: datetime) -> list[dict]:
    sha = hashlib.sha256(corps).hexdigest()
    texte = corps.decode("utf-8-sig", "replace")
    lecteur = csv.DictReader(io.StringIO(texte))
    champs = lecteur.fieldnames or []
    # triplets <bookmaker>H/D/A ; exclut plus/moins de buts (>2.5) et handicap asiatique (AHH…)
    books = [c[:-1] for c in champs if c.endswith("H") and c[:-1] + "D" in champs and c[:-1] + "A" in champs
             and not c.startswith("AH") and not re.search(r"[<>]", c) and c not in ("HTH",)]
    out = []
    for r in lecteur:
        if r.get("Div") not in LIGUES:
            continue
        try:
            jour = datetime.strptime(r["Date"], "%d/%m/%Y").date()
        except (KeyError, ValueError):
            continue
        if jour < maintenant.date():  # fichier pas encore renouvelé : match déjà joué, pas une cote d'avant-match
            continue
        for b in books:
            try:
                c = [float(r[b + x]) for x in "HDA"]
            except (TypeError, ValueError):
                continue
            out.append({"collecte_le": maintenant.isoformat(timespec="seconds"), "source": "football-data",
                        "bookmaker": b, "type_ligne": "instantane_source", "division": r["Div"],
                        "coup_envoi": f"{jour.isoformat()} {r.get('Time') or '?'} (heure UK)", "domicile": r["HomeTeam"],
                        "exterieur": r["AwayTeam"], "evenement_id": "", "cote_H": c[0], "cote_D": c[1], "cote_A": c[2],
                        "minutes_avant": "", "horizon": "inconnu", "url": FOOTBALL_DATA, "sha256_brut": sha, "marche": "1X2"})
    return out


def ecrire(chemin: Path, lignes: list[dict]) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLONNES)
        w.writeheader()
        w.writerows(lignes)


def collecter(dossier: Path, maintenant: datetime, lire=lire_url) -> dict:
    base = dossier / "cotes"
    etat_f = base / "etat.json"
    etat = json.loads(etat_f.read_text(encoding="utf-8")) if etat_f.exists() else {}
    journal = {"collecte_le": maintenant.isoformat(timespec="seconds"), "erreurs": [], "espn": 0, "football_data": None}
    espn = []
    for div, slug in LIGUES.items():
        for jour in (maintenant, maintenant + timedelta(days=1)):
            url = ESPN.format(slug=slug, jour=jour.strftime("%Y%m%d"))
            try:
                espn += lignes_espn(div, lire(url), url, maintenant)
            except Exception as exc:  # une ligue en échec n'arrête pas les autres
                journal["erreurs"].append(f"espn {div} {jour:%Y-%m-%d} : {type(exc).__name__}: {exc}"[:300])
    dernier = etat.get("dernier_horaire")  # le planificateur GitHub décale les exécutions : pas d'heure fixe
    horaire_du = not dernier or maintenant - datetime.fromisoformat(dernier) >= timedelta(minutes=55)
    if horaire_du and espn:
        etat["dernier_horaire"] = maintenant.isoformat()
    gardees = []
    for l in espn:
        if l["horizon"] in HORIZONS:
            # Chaque réponse effectivement reçue est une observation : une première
            # capture par horizon peut supprimer les deux côtés d'une composition.
            gardees.append(l)
        elif l["horizon"] in ("hors_fenetre", "ouverture") and horaire_du:
            gardees.append(l)  # instantané horaire hors fenêtre : suivi du mouvement des cotes
    if gardees:
        ecrire(base / "espn" / maintenant.date().isoformat() / f"{maintenant:%H%M}.csv", gardees)
    journal["espn"] = len(gardees)
    journal["espn_par_horizon"] = {h: sum(1 for l in gardees if l["horizon"] == h) for h in (*HORIZONS, "hors_fenetre", "ouverture")}
    try:
        corps = lire(FOOTBALL_DATA)
        sha = hashlib.sha256(corps).hexdigest()
        if sha != etat.get("football_data_sha"):
            fd = lignes_football_data(corps, maintenant)
            ecrire(base / "football-data" / maintenant.date().isoformat() / f"{maintenant:%H%M}.csv", fd)
            etat["football_data_sha"] = sha
            journal["football_data"] = len(fd)
        else:
            journal["football_data"] = "inchange"
    except Exception as exc:
        journal["erreurs"].append(f"football-data : {type(exc).__name__}: {exc}"[:300])
    base.mkdir(parents=True, exist_ok=True)
    etat_f.write_text(json.dumps(etat, indent=1) + "\n", encoding="utf-8")
    with (base / "journal.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(journal, ensure_ascii=False) + "\n")
    return journal


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sortie", type=Path, required=True)
    p.add_argument("--maintenant", default=None)
    a = p.parse_args(argv)
    maintenant = (datetime.fromisoformat(a.maintenant) if a.maintenant else datetime.now(timezone.utc)).replace(second=0, microsecond=0)
    print(json.dumps(collecter(a.sortie, maintenant), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
