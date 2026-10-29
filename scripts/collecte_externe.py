"""Collecte externe multi-ligues, prévue pour GitHub Actions (réseau ouvert).

Usage : python scripts/collecte_externe.py --sortie <dossier> [--sources sofascore,fpl,clubelo,understat]

Sources (choix Luloki du 29/10/2026, voir docs/collecte-externe.md) :
- sofascore : compos et joueurs absents/incertains des matchs à venir (72 h) des
  ligues de data/ligues_collecte.json (38 divisions avec historique + coupes UEFA) ;
- fpl : statut officiel des joueurs Premier League (blessure, suspension, chance de jouer) ;
- clubelo : classement Elo du jour (tous les clubs européens) ;
- understat : statistiques d'équipe par match (xG) de la saison en cours (5 ligues couvertes par Understat) ;
- apifootball : blessures/suspensions (toutes ligues) et compos officielles des ligues de
  data/ligues_collecte.json, clé `API_FOOTBALL_KEY` (secret Actions), budget de 90 requêtes/jour.

Volume Sofascore : compos interrogées pour les matchs à moins de 3 h à chaque
exécution, et pour tout l'horizon de 72 h seulement aux heures UTC multiples de 6.

Chaque ligne porte `collecte_le` (UTC) : une donnée n'est utilisable avant un
match que si elle a été collectée avant son coup d'envoi. Un instantané
identique au précédent n'est pas réécrit. Les échecs d'une source sont
consignés dans `manifeste.json` sans arrêter les autres sources.
Bibliothèque standard seulement, sauf understat (soccerdata) et, si présent,
curl_cffi pour Sofascore. Rien n'est envoyé aux modèles ni à `memoire/`.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

SOFASCORE_API = "https://api.sofascore.com/api/v1"
FPL_API = "https://fantasy.premierleague.com/api/bootstrap-static/"
CLUBELO_API = "http://api.clubelo.com"
CONFIG = Path(__file__).resolve().parent.parent / "data" / "ligues_collecte.json"
CLUBELO_PAYS = {"ENG": "E0", "ESP": "SP1", "ITA": "I1", "GER": "D1", "FRA": "F1", "NED": "N1", "BEL": "B1",
                "POR": "P1", "TUR": "T1", "GRE": "G1", "SCO": "SC0", "AUT": "AUT", "SUI": "SUI", "DEN": "DEN",
                "SWE": "SWE", "NOR": "NOR", "FIN": "FIN", "POL": "POL", "ROM": "ROM", "RUS": "RUS", "IRL": "IRL"}
FPL_STATUT = {"a": "disponible", "d": "incertain", "i": "blesse", "s": "suspendu", "u": "indisponible", "n": "non_eligible"}
SOURCES = ("sofascore", "fpl", "clubelo", "understat", "apifootball", "espn")
ESPN_API = "https://site.api.espn.com/apis/site/v2/sports/soccer"
APIFOOTBALL = "https://v3.football.api-sports.io"
APIFOOTBALL_BUDGET_JOUR = 90  # plan gratuit : 100 requêtes/jour, 10 gardées en réserve
COLONNES_BLESSURES = ("collecte_le", "fixture_id", "coup_envoi", "ligue_id", "ligue", "pays", "equipe",
                      "joueur", "joueur_id", "type", "motif")
COLONNES_COMPOS_AF = ("collecte_le", "fixture_id", "coup_envoi", "ligue_id", "ligue", "equipe", "formation",
                      "joueur", "joueur_id", "poste", "statut")
COLONNES_ESPN = ("collecte_le", "event_id", "ligue", "division", "coup_envoi", "equipe", "formation",
                 "joueur", "joueur_id", "poste", "statut")
COLONNES_SOFASCORE = ("collecte_le", "event_id", "division", "coup_envoi", "domicile", "exterieur", "cote",
                      "equipe", "joueur", "joueur_id", "poste", "statut", "motif", "compo_confirmee")
COLONNES_FPL = ("collecte_le", "joueur_id", "joueur", "equipe", "statut", "chance_prochain_match",
                "chance_ce_match", "news", "news_ajoutee_le")
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
           "Accept": "application/json, text/csv, */*"}


def utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")


def lire_url(url: str, timeout: int = 30) -> bytes:
    """GET ; Sofascore refuse souvent urllib, d'où curl_cffi (empreinte navigateur) s'il est installé."""
    try:
        from curl_cffi import requests as cr  # type: ignore
    except ImportError:
        cr = None
    if cr is not None and "sofascore" in url:
        r = cr.get(url, impersonate="chrome", timeout=timeout)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code} sur {url}")
        return r.content
    for essai in range(3):  # 502 ClubElo au premier run du 29/10/2026 : erreurs serveur passagères
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as exc:
            if exc.code < 500 or essai == 2:
                raise
        time.sleep(10 * (essai + 1))
    raise AssertionError("inatteignable")


def lire_json(url: str, lire=lire_url):
    return json.loads(lire(url))


# --- Sofascore -----------------------------------------------------------

def charger_config(chemin: Path = CONFIG) -> dict:
    return json.loads(chemin.read_text(encoding="utf-8"))


def ligues_sofascore(config: dict) -> dict[int, str]:
    """id Sofascore -> division (ou « UEFA:<nom> » pour une coupe sans historique)."""
    return {l["id"]: l["division"] or f"UEFA:{l['nom']}" for l in config["sofascore"]}


def tournois_vus(evenements: list[dict]) -> dict[int, dict]:
    """Tous les tournois du calendrier, pour vérifier les identifiants de la configuration."""
    out = {}
    for e in evenements:
        t = (e.get("tournament") or {}).get("uniqueTournament") or {}
        if "id" in t:
            out[t["id"]] = {"id": t["id"], "nom": t.get("name", ""),
                            "pays": ((e.get("tournament") or {}).get("category") or {}).get("name", "")}
    return out


def matchs_a_venir(evenements: list[dict], debut: float, fin: float, ligues: dict[int, str]) -> list[dict]:
    """Matchs non commencés des ligues suivies dont le coup d'envoi est dans [debut, fin]."""
    out = []
    for e in evenements:
        tid = ((e.get("tournament") or {}).get("uniqueTournament") or {}).get("id")
        if tid not in ligues or (e.get("status") or {}).get("type") != "notstarted":
            continue
        if not debut <= e.get("startTimestamp", 0) <= fin:
            continue
        out.append({"event_id": e["id"], "division": ligues[tid], "coup_envoi": utc(e["startTimestamp"]),
                    "domicile": e["homeTeam"]["name"], "exterieur": e["awayTeam"]["name"]})
    return out


def lignes_compo(match: dict, compo: dict, collecte_le: str) -> list[dict]:
    """Titulaires/remplaçants (si compo confirmée) et absents/incertains d'un match."""
    confirmee = bool(compo.get("confirmed"))
    lignes = []
    for cote, equipe in (("H", match["domicile"]), ("A", match["exterieur"])):
        bloc = compo.get("home" if cote == "H" else "away") or {}
        base = {**match, "collecte_le": collecte_le, "cote": cote, "equipe": equipe, "compo_confirmee": confirmee}
        if confirmee:
            for p in bloc.get("players") or []:
                joueur = p.get("player") or {}
                lignes.append({**base, "joueur": joueur.get("name", ""), "joueur_id": joueur.get("id", ""),
                               "poste": p.get("position") or joueur.get("position", ""),
                               "statut": "remplacant" if p.get("substitute") else "titulaire", "motif": ""})
        for p in bloc.get("missingPlayers") or []:
            joueur = p.get("player") or {}
            statut = "incertain" if p.get("type") == "doubtful" else "absent"
            motif = p.get("description") or (f"code {p['reason']}" if "reason" in p else "")
            lignes.append({**base, "joueur": joueur.get("name", ""), "joueur_id": joueur.get("id", ""),
                           "poste": joueur.get("position", ""), "statut": statut, "motif": motif})
    return lignes


def collecter_sofascore(maintenant: float, ligues: dict[int, str], lire=lire_url, horizon_h: int = 72,
                        pause: float = 1.0, vus: dict | None = None) -> list[dict]:
    complet = datetime.fromtimestamp(maintenant, tz=timezone.utc).hour % 6 == 0
    fin = maintenant + (horizon_h if complet else 3) * 3600
    jours = sorted({datetime.fromtimestamp(t, tz=timezone.utc).date().isoformat()
                    for t in (maintenant, fin, *range(int(maintenant), int(fin), 6 * 3600))})
    matchs = {}
    for jour in jours:
        evenements = lire_json(f"{SOFASCORE_API}/sport/football/scheduled-events/{jour}", lire).get("events") or []
        if vus is not None:
            vus.update(tournois_vus(evenements))
        for m in matchs_a_venir(evenements, maintenant, fin, ligues):
            matchs[m["event_id"]] = m
    collecte_le, lignes, erreurs = utc(maintenant), [], 0
    for m in sorted(matchs.values(), key=lambda x: (x["coup_envoi"], x["event_id"])):
        time.sleep(pause)
        try:
            compo = lire_json(f"{SOFASCORE_API}/event/{m['event_id']}/lineups", lire)
        except Exception:  # compo pas encore publiée (404) ou refus ponctuel
            erreurs += 1
            continue
        lignes.extend(lignes_compo(m, compo, collecte_le))
    if matchs and erreurs == len(matchs):
        raise RuntimeError(f"aucune compo lisible sur {len(matchs)} matchs")
    return lignes


# --- FPL, ClubElo, Understat ---------------------------------------------

def lignes_fpl(bootstrap: dict, collecte_le: str) -> list[dict]:
    """Joueurs PL dont le statut n'est pas « disponible » ou qui portent une news."""
    equipes = {t["id"]: t["name"] for t in bootstrap.get("teams", [])}
    out = []
    for p in bootstrap.get("elements", []):
        if p.get("status") == "a" and not p.get("news"):
            continue
        out.append({"collecte_le": collecte_le, "joueur_id": p["id"], "joueur": p.get("web_name", ""),
                    "equipe": equipes.get(p.get("team"), ""), "statut": FPL_STATUT.get(p.get("status"), p.get("status")),
                    "chance_prochain_match": p.get("chance_of_playing_next_round"),
                    "chance_ce_match": p.get("chance_of_playing_this_round"),
                    "news": p.get("news", ""), "news_ajoutee_le": p.get("news_added") or ""})
    return sorted(out, key=lambda r: (r["equipe"], r["joueur"]))


def lignes_clubelo(texte: str) -> list[dict]:
    """Tous les clubs du CSV ClubElo du jour ; division renseignée pour le niveau 1 des pays suivis."""
    return [{**r, "division": CLUBELO_PAYS.get(r.get("Country"), "") if r.get("Level") == "1" else ""}
            for r in csv.DictReader(io.StringIO(texte))]


def saison_courante(maintenant: float) -> str:
    d = datetime.fromtimestamp(maintenant, tz=timezone.utc)
    debut = d.year if d.month >= 7 else d.year - 1
    return f"{debut}-{(debut + 1) % 100:02d}"  # format non ambigu pour soccerdata


def collecter_understat(maintenant: float, dossier: Path, ligues: list[str]) -> int:
    import soccerdata as sd  # dépendance installée seulement dans le workflow

    saison = saison_courante(maintenant)
    df = sd.Understat(leagues=ligues, seasons=saison).read_team_match_stats()
    chemin = dossier / "understat" / f"matchs_equipes_{saison}.csv"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    df.reset_index().assign(collecte_le=utc(maintenant)).to_csv(chemin, index=False)
    return len(df)


# --- API-Football ---------------------------------------------------------

def lecteur_apifootball(cle: str):
    """GET authentifié ; la clé passe dans un en-tête, jamais dans l'URL ni les journaux."""
    def lire(chemin: str) -> dict:
        req = urllib.request.Request(APIFOOTBALL + chemin, headers={**HEADERS, "x-apisports-key": cle})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        if data.get("errors"):  # l'API répond 200 avec un champ errors (plan, quota, saison)
            raise RuntimeError(f"API-Football {chemin.split('?')[0]} : {data['errors']}")
        return data
    return lire


def lignes_blessures(reponse: list[dict], collecte_le: str) -> list[dict]:
    out = []
    for r in reponse:
        joueur, equipe, fx, ligue = r.get("player") or {}, r.get("team") or {}, r.get("fixture") or {}, r.get("league") or {}
        out.append({"collecte_le": collecte_le, "fixture_id": fx.get("id"), "coup_envoi": fx.get("date"),
                    "ligue_id": ligue.get("id"), "ligue": ligue.get("name"), "pays": ligue.get("country"),
                    "equipe": equipe.get("name"), "joueur": joueur.get("name"), "joueur_id": joueur.get("id"),
                    "type": joueur.get("type"), "motif": joueur.get("reason")})
    return sorted(out, key=lambda x: (str(x["coup_envoi"]), str(x["fixture_id"]), str(x["equipe"]), str(x["joueur"])))


def lignes_compos_af(match: dict, reponse: list[dict], collecte_le: str) -> list[dict]:
    out = []
    for bloc in reponse:
        base = {**match, "collecte_le": collecte_le, "equipe": (bloc.get("team") or {}).get("name"),
                "formation": bloc.get("formation")}
        for cle, statut in (("startXI", "titulaire"), ("substitutes", "remplacant")):
            for p in bloc.get(cle) or []:
                j = p.get("player") or {}
                out.append({**base, "joueur": j.get("name"), "joueur_id": j.get("id"), "poste": j.get("pos"),
                            "statut": statut})
    return out


def calendrier_af(reponse: list[dict], ligues: set[int]) -> list[dict]:
    """Matchs non commencés des ligues suivies (pour les compos)."""
    out = {r["fixture"]["id"]: {"fixture_id": r["fixture"]["id"], "coup_envoi": r["fixture"]["date"],
                                "debut_ts": r["fixture"].get("timestamp"), "ligue_id": r["league"]["id"],
                                "ligue": r["league"]["name"]}
           for r in reponse if r["league"]["id"] in ligues and r["fixture"]["status"]["short"] in ("NS", "TBD")}
    return list(out.values())


def collecter_apifootball(dossier: Path, maintenant: float, config: dict, etat: dict, lire) -> dict:
    """Premier passage du jour : statut + calendrier J et J+1 + blessures J et J+1. Aux heures UTC 0, 6, 12, 18 : blessures J.
    Chaque heure : compos officielles des matchs suivis qui débutent dans les 75 min (une fois par match)."""
    d = datetime.fromtimestamp(maintenant, tz=timezone.utc)
    jour, demain = d.date().isoformat(), (d + timedelta(days=1)).date().isoformat()
    compteur = etat.setdefault("apifootball", {})
    if compteur.get("jour") != jour:
        compteur.update({"jour": jour, "requetes": 0, "compos_faites": []})

    def appel(chemin):
        if compteur["requetes"] >= APIFOOTBALL_BUDGET_JOUR:
            raise RuntimeError("budget journalier atteint")
        compteur["requetes"] += 1
        return lire(chemin)

    res, collecte_le = {}, utc(maintenant)
    base = dossier / "apifootball"
    base.mkdir(parents=True, exist_ok=True)
    chemin_cal = base / "calendrier.json"
    nouveau_jour = not chemin_cal.exists() or json.loads(chemin_cal.read_text()).get("jour") != jour
    if nouveau_jour:
        statut = appel("/status").get("response") or {}
        (base / "statut.json").write_text(json.dumps({"collecte_le": collecte_le, **{k: statut.get(k) for k in ("subscription", "requests")}},
                                                     indent=1, ensure_ascii=False) + "\n")
        ligues = {l["id"] for l in config.get("apifootball", [])}
        brut = [r for j in (jour, demain) for r in appel(f"/fixtures?date={j}").get("response") or []]
        cal = calendrier_af(brut, ligues)
        vues = sorted({(r["league"]["id"], r["league"]["name"], r["league"].get("country") or "") for r in brut})
        chemin_cal.write_text(json.dumps({"jour": jour, "matchs": cal, "ligues_vues": vues}, indent=1, ensure_ascii=False) + "\n")
        res["calendrier"] = len(cal)
    if nouveau_jour or d.hour % 6 == 0:
        jours = (jour, demain) if nouveau_jour else (jour,)
        brut_b = [r for j in jours for r in appel(f"/injuries?date={j}").get("response") or []]
        # J et J+1 renvoient en partie les mêmes lignes (vu au premier run réel : 482 lignes, 241 uniques)
        uniques = {(l["fixture_id"], l["equipe"], l["joueur_id"], l["type"]): l for l in lignes_blessures(brut_b, collecte_le)}
        blessures = sorted(uniques.values(), key=lambda x: (str(x["coup_envoi"]), str(x["fixture_id"]), str(x["equipe"]), str(x["joueur"])))
        res["blessures"] = len(blessures)
        res["fichier_blessures"] = ecrire_instantane(dossier, "apifootball/blessures", blessures, COLONNES_BLESSURES, maintenant, etat)
    compos = []
    for m in json.loads(chemin_cal.read_text())["matchs"]:
        if m["fixture_id"] in compteur["compos_faites"] or not m.get("debut_ts"):
            continue
        if 0 <= m["debut_ts"] - maintenant <= 75 * 60 and compteur["requetes"] < APIFOOTBALL_BUDGET_JOUR:
            reponse = appel(f"/fixtures/lineups?fixture={m['fixture_id']}").get("response") or []
            if reponse:  # compo pas encore publiée : on retentera à l'heure suivante
                compteur["compos_faites"].append(m["fixture_id"])
                compos.extend(lignes_compos_af({k: m[k] for k in ("fixture_id", "coup_envoi", "ligue_id", "ligue")}, reponse, collecte_le))
    if compos:
        res["fichier_compos"] = ecrire_instantane(dossier, "apifootball/compos", compos, COLONNES_COMPOS_AF, maintenant, etat)
    res["compos"] = len(compos)
    res["requetes_jour"] = compteur["requetes"]
    return res


# --- ESPN (compos officielles, sans clé) ----------------------------------

def _poste_espn(joueur: dict) -> str:
    """Écarte les codes de banc (« SUB ») qui ne sont PAS des postes.

    Privilégie la position effective de la ligne si sportive, sinon le profil
    athlète ; si les deux sont inconnus, ne fabrique pas de poste.
    """
    athlete = joueur.get("athlete") or {}
    for p in (joueur.get("position"), athlete.get("position")):
        code = (p.get("abbreviation") or "") if isinstance(p, dict) else (p or "")
        code = str(code).strip().upper()
        if code and code not in ("SUB", "BENCH", "RES", "N/A", "NA", "UNK"):
            return code
    return ""


def lignes_compos_espn(base: dict, summary: dict, collecte_le: str) -> list[dict]:
    out = []
    for bloc in summary.get("rosters") or []:
        joueurs = bloc.get("roster") or []
        if not any(j.get("starter") for j in joueurs):
            continue
        for j in joueurs:
            a = j.get("athlete") or {}
            out.append({**base, "collecte_le": collecte_le, "equipe": (bloc.get("team") or {}).get("displayName"),
                        "formation": bloc.get("formation"), "joueur": a.get("displayName"), "joueur_id": a.get("id"),
                        "poste": _poste_espn(j),
                        "statut": "titulaire" if j.get("starter") else "remplacant"})
    return out


def collecter_espn(maintenant: float, config: dict, etat: dict, lire, pause: float = 1.0) -> dict:
    """Chaque heure : compos publiées des matchs qui débutent dans les 75 min (une fois par match)."""
    d = datetime.fromtimestamp(maintenant, tz=timezone.utc)
    suivi = etat.setdefault("espn", {})
    if suivi.get("jour") != d.date().isoformat():
        suivi.update({"jour": d.date().isoformat(), "compos_faites": suivi.get("compos_faites", [])[-200:]})
    jours = {d.strftime("%Y%m%d"), (d + timedelta(minutes=75)).strftime("%Y%m%d")}
    compos, erreurs, vus = [], [], 0
    for ligue in config.get("espn", []):
        for jour in sorted(jours):
            try:
                events = lire_json(f"{ESPN_API}/{ligue['slug']}/scoreboard?dates={jour}", lire).get("events") or []
            except Exception as exc:
                erreurs.append(f"{ligue['slug']}: {type(exc).__name__}: {exc}"[:120])
                continue
            for ev in events:
                debut = datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).timestamp()
                if ev["id"] in suivi["compos_faites"] or not 0 <= debut - maintenant <= 75 * 60:
                    continue
                vus += 1
                summary = lire_json(f"{ESPN_API}/{ligue['slug']}/summary?event={ev['id']}", lire)
                base = {"event_id": ev["id"], "ligue": ligue["slug"], "division": ligue.get("division") or "",
                        "coup_envoi": utc(debut)}
                lignes = lignes_compos_espn(base, summary, utc(maintenant))
                if lignes:  # compo pas encore publiée : on retentera à l'heure suivante
                    suivi["compos_faites"].append(ev["id"])
                    compos.extend(lignes)
                time.sleep(pause)
    if erreurs and len(erreurs) == len(config.get("espn", [])) * len(jours):
        raise RuntimeError("tous les calendriers ESPN en échec : " + "; ".join(erreurs[:3]))
    return {"matchs_proches": vus, "compos": compos, "erreurs_ligues": erreurs}


# --- Écriture ------------------------------------------------------------

def empreinte(lignes: list[dict]) -> str:
    """Empreinte du contenu hors date de collecte (détecte un instantané inchangé)."""
    contenu = [{k: v for k, v in r.items() if k != "collecte_le"} for r in lignes]
    return hashlib.sha256(json.dumps(contenu, sort_keys=True, default=str).encode()).hexdigest()


def ecrire_instantane(dossier: Path, source: str, lignes: list[dict], colonnes, maintenant: float,
                      etat: dict) -> str:
    """Écrit <source>/<AAAA-MM-JJ>/<HHMM>.csv sauf si le contenu est identique au dernier instantané."""
    h = empreinte(lignes)
    if etat.get(source, {}).get("empreinte") == h:
        return "inchange"
    d = datetime.fromtimestamp(maintenant, tz=timezone.utc)
    chemin = dossier / source / d.date().isoformat() / f"{d:%H%M}.csv"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(colonnes), extrasaction="ignore")
        w.writeheader()
        w.writerows(lignes)
    etat[source] = {"empreinte": h, "fichier": str(chemin.relative_to(dossier))}
    return str(chemin.relative_to(dossier))


def ecrire_tournois(dossier: Path, vus: dict, config: dict) -> None:
    """Cumule les tournois vus ; « suivi » indique s'ils sont dans la configuration."""
    chemin = dossier / "sofascore" / "tournois_vus.csv"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    anciens = {int(r["id"]): r for r in csv.DictReader(io.StringIO(chemin.read_text(encoding="utf-8")))} if chemin.exists() else {}
    suivis = {l["id"] for l in config["sofascore"]}
    anciens.update(vus)
    for tid, t in anciens.items():
        anciens[tid] = {**t, "suivi": tid in suivis}
    with chemin.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "nom", "pays", "suivi"])
        w.writeheader()
        w.writerows(anciens[k] for k in sorted(anciens))


def collecter(dossier: Path, sources, maintenant: float | None = None, lire=lire_url,
              config: dict | None = None, pause: float = 1.0) -> dict:
    maintenant = time.time() if maintenant is None else maintenant
    config = charger_config() if config is None else config
    dossier.mkdir(parents=True, exist_ok=True)
    chemin_etat = dossier / "etat.json"
    etat = json.loads(chemin_etat.read_text()) if chemin_etat.exists() else {}
    manifeste = {"execution_le": utc(maintenant), "sources": {}}
    for source in sources:
        try:
            if source == "sofascore":
                vus = {}
                try:
                    lignes = collecter_sofascore(maintenant, ligues_sofascore(config), lire, pause=pause, vus=vus)
                finally:
                    if vus:
                        ecrire_tournois(dossier, vus, config)
                res = {"lignes": len(lignes), "fichier": ecrire_instantane(dossier, source, lignes, COLONNES_SOFASCORE, maintenant, etat)}
            elif source == "fpl":
                lignes = lignes_fpl(lire_json(FPL_API, lire), utc(maintenant))
                res = {"lignes": len(lignes), "fichier": ecrire_instantane(dossier, source, lignes, COLONNES_FPL, maintenant, etat)}
            elif source == "clubelo":
                jour = datetime.fromtimestamp(maintenant, tz=timezone.utc).date().isoformat()
                lignes = [{**r, "collecte_le": utc(maintenant)} for r in lignes_clubelo(lire(f"{CLUBELO_API}/{jour}").decode())]
                cols = ("collecte_le", "division", "Rank", "Club", "Country", "Level", "Elo", "From", "To")
                res = {"lignes": len(lignes), "fichier": ecrire_instantane(dossier, source, lignes, cols, maintenant, etat)}
            elif source == "apifootball":
                cle = os.environ.get("API_FOOTBALL_KEY", "").strip()
                if not cle and lire is lire_url:
                    manifeste["sources"][source] = {"statut": "ignore", "raison": "secret API_FOOTBALL_KEY absent"}
                    continue
                res = collecter_apifootball(dossier, maintenant, config, etat,
                                            lecteur_apifootball(cle) if lire is lire_url else lire)
            elif source == "espn":
                r = collecter_espn(maintenant, config, etat, lire, pause=pause)
                res = {"matchs_proches": r["matchs_proches"], "lignes": len(r["compos"]), "erreurs_ligues": r["erreurs_ligues"]}
                if r["compos"]:
                    res["fichier"] = ecrire_instantane(dossier, "espn/compos", r["compos"], COLONNES_ESPN, maintenant, etat)
            elif source == "understat":
                res = {"lignes": collecter_understat(maintenant, dossier, config["understat"])}
            else:
                raise ValueError(f"source inconnue : {source}")
            res["statut"] = "ok"
        except Exception as exc:  # une source en échec n'arrête pas les autres
            res = {"statut": "erreur", "erreur": f"{type(exc).__name__}: {exc}"[:300]}
        manifeste["sources"][source] = res
    chemin_etat.write_text(json.dumps(etat, indent=1, sort_keys=True) + "\n")
    (dossier / "manifeste.json").write_text(json.dumps(manifeste, indent=1, ensure_ascii=False) + "\n")
    return manifeste


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--sortie", required=True, type=Path)
    p.add_argument("--sources", default=",".join(SOURCES))
    a = p.parse_args(argv)
    sources = [s.strip() for s in a.sources.split(",") if s.strip()]
    manifeste = collecter(a.sortie, sources)
    print(json.dumps(manifeste, indent=1, ensure_ascii=False))
    # Code 1 seulement si toutes les sources ont échoué : le workflow commite quand même le manifeste.
    return 0 if any(s["statut"] == "ok" for s in manifeste["sources"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
