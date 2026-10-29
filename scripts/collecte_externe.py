"""Collecte externe multi-ligues, prévue pour GitHub Actions (réseau ouvert).

Usage : python scripts/collecte_externe.py --sortie <dossier> [--sources sofascore,fpl,clubelo,understat]

Sources (choix Luloki du 29/10/2026, voir docs/collecte-externe.md) :
- sofascore : compos et joueurs absents/incertains des matchs à venir (72 h) des
  ligues de data/ligues_collecte.json (38 divisions avec historique + coupes UEFA) ;
- fpl : statut officiel des joueurs Premier League (blessure, suspension, chance de jouer) ;
- clubelo : classement Elo du jour (tous les clubs européens) ;
- understat : statistiques d'équipe par match (xG) de la saison en cours (5 ligues couvertes par Understat).

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
SOURCES = ("sofascore", "fpl", "clubelo", "understat")
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
