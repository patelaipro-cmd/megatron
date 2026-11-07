"""Audit en lecture seule d'un jeu de donnees Apify (aucun lancement d'Actor).

Ne modifie ni les predictions, ni le registre, ni les probabilites.
Usage : python scripts/pilote_apify.py --fichier export.json --limite 100
Ou : APIFY_TOKEN=... APIFY_TACHE_SOFASCORE=... python scripts/pilote_apify.py --tache
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.apify.com/v2"
CONFIG = Path(__file__).resolve().parent.parent / "data" / "ligues_collecte.json"


def _utc(val: str | None) -> datetime | None:
    if not val:
        return None
    dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("fin-run sans fuseau horaire")
    return dt.astimezone(timezone.utc)


def _read_api(url: str, token: str) -> object:
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/json",
        "User-Agent": "megatron-apify-audit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Apify HTTP {exc.code} (acces ou ressource a verifier)") from None
    except urllib.error.URLError:
        raise RuntimeError("Apify injoignable") from None


def charger_dernier_run(tache: str, token: str, limite: int = 100, lire=_read_api):
    """Ne lance pas de run : lit uniquement un run deja termine avec succes."""
    tache = urllib.parse.quote(tache, safe="~")
    reponse = lire(f"{API}/actor-tasks/{tache}/runs/last?status=SUCCEEDED", token)
    run = reponse.get("data") if isinstance(reponse, dict) else None
    if not isinstance(run, dict) or not run.get("defaultDatasetId") or not run.get("finishedAt"):
        raise ValueError("aucun run Apify termine exploitable")
    dataset = urllib.parse.quote(str(run["defaultDatasetId"]), safe="")
    items = lire(f"{API}/datasets/{dataset}/items?clean=true&format=json&limit={limite}", token)
    if not isinstance(items, list):
        raise ValueError("le dataset Apify ne contient pas une liste JSON")
    return items, run["finishedAt"], run.get("id")


def auditer(items: list, *, limite: int = 100, fin_run: str | None = None,
            run_id: str | None = None, ligues: set[int] | None = None) -> dict:
    """Rapport structurel sans activation de l'entrainement."""
    if not isinstance(items, list):
        raise ValueError("un tableau JSON de resultats Apify est attendu")
    if limite < 1 or limite > 1000:
        raise ValueError("limite attendue entre 1 et 1000")
    fin = _utc(fin_run)
    base = [x for x in items[:limite] if isinstance(x, dict) and x.get("type") in (None, "match")]
    matches = [x for x in base if x.get("sport") in (None, "football")]
    vus = set()
    doublons = invalides = date_valides = scores_incoherents = termines = non_debutes = 0
    suivis = stats = cotes = absents = compos = prospectifs = 0
    problemes = []
    for it in matches:
        ident = it.get("id")
        if isinstance(ident, bool) or ident is None or str(ident).strip() == "":
            invalides += 1
        elif str(ident) in vus:
            doublons += 1
        else:
            vus.add(str(ident))
        ts = it.get("startTimestamp")
        valid_ts = isinstance(ts, (int, float)) and not isinstance(ts, bool) and 946684800 < ts < 4102444800
        if valid_ts:
            date_valides += 1
        if ligues is not None and it.get("tournamentId") in ligues:
            suivis += 1
        if it.get("statistics"):
            stats += 1
        if it.get("odds"):
            cotes += 1
        lineup = it.get("lineups")
        if isinstance(lineup, dict):
            if lineup.get("confirmed"):
                compos += 1
            for cote in ("home", "away"):
                bloc = lineup.get(cote)
                if isinstance(bloc, dict):
                    absents += len(bloc.get("missingPlayers") or [])
        etat = it.get("statusType")
        if etat == "finished":
            termines += 1
            h, a = it.get("homeScore"), it.get("awayScore")
            if any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in (h, a)):
                scores_incoherents += 1
        if etat == "notstarted":
            non_debutes += 1
            if fin and valid_ts and fin.timestamp() < ts:
                prospectifs += 1
    if not fin:
        problemes.append("FIN_RUN_ABSENTE : aucune preuve de disponibilite avant match")
    if not matches:
        problemes.append("AUCUN_MATCH_FOOTBALL")
    if date_valides != len(matches):
        problemes.append("DATES_INCOMPLETES")
    if doublons or invalides:
        problemes.append("IDENTIFIANTS_INCOMPLETS_OU_DOUBLONS")
    if scores_incoherents:
        problemes.append("SCORES_FINAUX_INCOHERENTS")
    if ligues is not None and suivis == 0:
        problemes.append("AUCUNE_LIGUE_MEGATRON_RETENUE")
    return {
        "protocole": "MEGATRON-APIFY-PILOTE-001",
        "mode": "audit_lecture_seule_sans_appel_actor",
        "source": "abotapi/sofascore-scraper",
        "run_id": run_id,
        "fin_run_utc": fin.isoformat() if fin else None,
        "lignes_lues": min(len(items), limite),
        "matchs_football": len(matches),
        "matchs_ligues_megatron": suivis if ligues is not None else None,
        "matchs_avec_date_valide": date_valides,
        "matchs_avec_statistiques": stats,
        "matchs_avec_cotes": cotes,
        "matchs_termines": termines,
        "scores_finaux_incoherents": scores_incoherents,
        "matchs_non_commences": non_debutes,
        "matchs_prospectifs_observes_avant_coup_envoi": prospectifs,
        "compositions_confirmees_dans_dataset": compos,
        "joueurs_absents_declares": absents,
        "identifiants_manquants": invalides,
        "doublons": doublons,
        "alertes": problemes,
        "exploitable_entrainement": False,
        "note": "Controle structurel uniquement. Scores et caracteristiques historiques restent a confronter a une seconde source, sans fuite temporelle."
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    choix = p.add_mutually_exclusive_group(required=True)
    choix.add_argument("--fichier", type=Path, help="export JSON local Apify")
    choix.add_argument("--tache", action="store_true", help="lire le dernier run reussi via secrets")
    p.add_argument("--limite", type=int, default=100)
    p.add_argument("--fin-run", help="date UTC fin de run pour fichier local (ISO 8601)")
    p.add_argument("--rapport", type=Path, help="rapport JSON de sortie")
    a = p.parse_args(argv)
    if not 1 <= a.limite <= 1000:
        p.error("--limite doit etre entre 1 et 1000")
    try:
        if a.tache:
            token = os.getenv("APIFY_TOKEN", "")
            tache = os.getenv("APIFY_TACHE_SOFASCORE", "")
            if not token or not tache:
                raise ValueError("secrets APIFY_TOKEN et APIFY_TACHE_SOFASCORE absents")
            items, fin, run = charger_dernier_run(tache, token, a.limite)
        else:
            items = json.loads(a.fichier.read_text(encoding="utf-8"))
            fin, run = a.fin_run, None
        ligues = None
        if CONFIG.exists():
            conf = json.loads(CONFIG.read_text(encoding="utf-8"))
            ligues = {int(x["id"]) for x in conf.get("sofascore", [])}
        rapport = auditer(items, limite=a.limite, fin_run=fin, run_id=run, ligues=ligues)
        sortie = json.dumps(rapport, ensure_ascii=False, indent=2) + "\n"
        if a.rapport:
            a.rapport.parent.mkdir(parents=True, exist_ok=True)
            a.rapport.write_text(sortie, encoding="utf-8")
        else:
            print(sortie, end="")
        return 0 if not rapport["alertes"] else 2
    except (ValueError, OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"PILOTE_APIFY_ERREUR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
