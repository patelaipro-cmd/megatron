"""Capture ESPN du score à T+15 : preuve d'une source, jamais un WATCH réel.

Entrée : JSON {"fixtures":[{"event_id":"401883117","ligue":"esp.2",
"coup_envoi":"2026-11-15T17:30:00+00:00"}]}. La liste doit être
établie avant la collecte avec de véritables identifiants de rencontres.

Sortie : JSON avec horodatage de capture, SHA256 des octets ESPN, score,
minute, refus et limites explicites. Ne consulte ni compte Premium ni clés API.
Le script ne modifie jamais les poids, les prévisions, ni memoire/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "data" / "ligues_collecte.json"
BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"
TIMEOUT_S = 12
TAILLE_MAX = 2_000_000
MAX_FIXTURES = 50
# Compétitions confirmées sur les pages ESPN, hors collection principale des
# ligues de clubs. Ne change pas la configuration de collecte historique.
COMPETITIONS_INTERNATIONALES = {"uefa.nations", "fifa.friendly", "fifa.friendly.w",
                                "uefa.euro_u21_qual"}


def instant(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("date ISO horodatée obligatoire")
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("date ISO incorrecte") from exc
    if d.tzinfo is None or d.utcoffset() is None:
        raise ValueError("date sans fuseau")
    return d


def valider_fixtures(document: dict, slugs: set[str]) -> list[dict]:
    liste = document.get("fixtures") if isinstance(document, dict) else None
    if not isinstance(liste, list) or not 1 <= len(liste) <= MAX_FIXTURES:
        raise ValueError("1 à 50 fixtures requises")
    vus, valides = set(), []
    for f in liste:
        if not isinstance(f, dict):
            raise ValueError("fixture doit être un objet")
        ligue, event_id = f.get("ligue"), f.get("event_id")
        if ligue not in slugs or not isinstance(event_id, str) or not re.fullmatch(r"[0-9]{1,16}", event_id):
            raise ValueError("ligue non configurée ou identifiant ESPN invalide")
        kickoff = instant(f.get("coup_envoi"))
        cle = (ligue, event_id)
        if cle in vus:
            raise ValueError("match ESPN en double")
        vus.add(cle)
        valides.append({"ligue": ligue, "event_id": event_id, "coup_envoi": kickoff})
    return valides


def minute_espn(status: dict) -> float:
    affichage = status.get("displayClock")
    if isinstance(affichage, str):
        chaine = affichage.strip().replace("'", "")
        if re.fullmatch(r"[0-9]{1,2}", chaine):
            return float(chaine)
        if re.fullmatch(r"[0-9]{1,2}:[0-9]{2}", chaine):
            minutes, secondes = chaine.split(":")
            if int(secondes) < 60:
                return int(minutes) + int(secondes) / 60
    raise ValueError("minute de jeu ESPN absente ou non interprétable")


def score_espn(champ) -> int:
    if isinstance(champ, dict):
        champ = champ.get("value")
    if type(champ) is int and champ >= 0:
        return champ
    if isinstance(champ, str) and re.fullmatch(r"[0-9]{1,2}", champ):
        return int(champ)
    raise ValueError("score absent, non entier ou invalide")


def decoder(evenement: dict, f: dict, capture: datetime) -> dict:
    if str(evenement.get("id")) != f["event_id"]:
        raise ValueError("identifiant match différent")
    competitions = evenement.get("competitions") or []
    if len(competitions) != 1:
        raise ValueError("nombre de compétitions incohérent")
    competition = competitions[0]
    status = competition.get("status") or evenement.get("status") or {}
    etat = status.get("type") or {}
    if (etat.get("state") != "in" or etat.get("completed") is True
            or etat.get("name") != "STATUS_IN_PROGRESS"):
        raise ValueError("statut de rencontre non confirmé en première période")
    if status.get("period") != 1:
        raise ValueError("période de match absente ou != 1")
    minute = minute_espn(status)
    if not 12 <= minute <= 18:
        raise ValueError("minute ESPN hors fenêtre T+15")
    kickoff_source = instant(evenement.get("date") or competition.get("date"))
    if abs((kickoff_source - f["coup_envoi"]).total_seconds()) > 60:
        raise ValueError("coup d'envoi source en désaccord avec référence")
    if not 12 <= (capture - kickoff_source).total_seconds() / 60 <= 18:
        raise ValueError("heure de collecte hors fenêtre T+15")
    if abs(minute - (capture - kickoff_source).total_seconds() / 60) > 2:
        raise ValueError("minute ESPN incohérente avec l'heure de collecte")
    concurrents = competition.get("competitors") or []
    cotes = {c.get("homeAway"): c for c in concurrents}
    if len(concurrents) != 2 or set(cotes) != {"home", "away"}:
        raise ValueError("équipes domicile/extérieur manquantes ou dupliquées")
    equipes = [((cotes[s].get("team") or {}).get("displayName") or "").strip()
               for s in ("home", "away")]
    if not all(equipes) or equipes[0] == equipes[1]:
        raise ValueError("équipes non identifiables")
    return {"minute_jeu": minute, "score": {"H": score_espn(cotes["home"].get("score")),
                                             "A": score_espn(cotes["away"].get("score"))},
            "domicile": equipes[0], "exterieur": equipes[1],
            "coup_envoi_source": kickoff_source.isoformat()}


def lire_public(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "MEGATRON-audit/1.0",
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as res:
        if res.status != 200:
            raise ValueError(f"ESPN HTTP {res.status}")
        if not res.geturl().startswith(BASE + "/"):
            raise ValueError("redirection ESPN hors domaine attendu")
        data = res.read(TAILLE_MAX + 1)
        if len(data) > TAILLE_MAX:
            raise ValueError("réponse ESPN trop volumineuse")
        return data


def reperer_prochains(slugs: set[str], *, au: datetime, lire=lire_public,
                      horizon_h: int = 3, horloge=None) -> dict:
    """Découvre des rencontres non commencées ESPN ; n'émet aucune prévision."""
    if au.tzinfo is None or au.utcoffset() is None or not 0 < horizon_h <= 24:
        raise ValueError("horizon 1 à 24 h et fuseau requis")
    horloge = horloge or (lambda: au)
    fin = au + timedelta(hours=horizon_h)
    jours = {d.astimezone(timezone.utc).strftime("%Y%m%d") for d in (au, fin)}
    matches, erreurs, conflits, sources = {}, [], set(), []
    for ligue in sorted(slugs):
        for jour in sorted(jours):
            url = f"{BASE}/{ligue}/scoreboard?dates={jour}"
            try:
                brut = lire(url)
                if not isinstance(brut, bytes) or len(brut) > TAILLE_MAX:
                    raise ValueError("réponse ESPN absente ou trop volumineuse")
                d = json.loads(brut)
                if not isinstance(d, dict) or not isinstance(d.get("events"), list):
                    raise ValueError("calendrier ESPN invalide")
                capture = horloge()
                if capture.tzinfo is None or capture.utcoffset() is None:
                    raise ValueError("horodatage source sans fuseau")
                sources.append({"url": url, "collecte_le": capture.isoformat(),
                                "sha256": hashlib.sha256(brut).hexdigest()})
                for e in d["events"]:
                    if not isinstance(e, dict):
                        continue
                    statut = (e.get("status") or {}).get("type") or {}
                    if (statut.get("state") != "pre" or statut.get("completed") is True
                            or statut.get("name") in {"STATUS_POSTPONED", "STATUS_CANCELED",
                                                        "STATUS_CANCELLED", "STATUS_SUSPENDED"}):
                        continue
                    kickoff = instant(e.get("date"))
                    identifiant = str(e.get("id", ""))
                    if (not capture < kickoff <= capture + timedelta(hours=horizon_h)
                            or not re.fullmatch(r"[0-9]{1,16}", identifiant)):
                        continue
                    cle = (ligue, identifiant)
                    if cle in conflits:
                        continue
                    courant = {"ligue": ligue, "event_id": identifiant,
                               "coup_envoi": kickoff.isoformat(),
                               "collecte_le": capture.isoformat(),
                               "source_url": f"https://www.espn.com/soccer/match/_/gameId/{identifiant}"}
                    if cle in matches and matches[cle]["coup_envoi"] != courant["coup_envoi"]:
                        erreurs.append(f"{ligue}:{identifiant}: coup d'envoi contradictoire")
                        del matches[cle]
                        conflits.add(cle)
                        continue
                    matches[cle] = courant
            except (ValueError, OSError, UnicodeError, TypeError, AttributeError, KeyError) as exc:
                erreurs.append(f"{ligue}:{jour}: {type(exc).__name__}: {str(exc)[:80]}")
    trouves = sorted(matches.values(), key=lambda r: (r["coup_envoi"], r["ligue"], r["event_id"]))
    return {"decouverte_le": au.isoformat(), "horizon_heures": horizon_h,
            "ligues_tentees": len(slugs), "matchs_trouves": len(trouves),
            "tronques": max(0, len(trouves) - MAX_FIXTURES),
            "fixtures": trouves[:MAX_FIXTURES], "erreurs": erreurs,
            "sources_capturees": sources,
            "statut": "LISTE_PROSPECTIVE_ESPN_NON_VALIDEE_MULTI_SOURCE"}


def collecter(fixtures: list[dict], *, au: datetime, lire=lire_public, horloge=None) -> list[dict]:
    """Une seule famille ESPN, aucune probabilité, et REFUS même si score lu."""
    if au.tzinfo is None or au.utcoffset() is None:
        raise ValueError("instant de capture sans fuseau")
    horloge = horloge or (lambda: au)  # tests déterministes ; la CLI injecte l'horloge réelle
    resultats = []
    cache = {}
    for f in fixtures:
        base = {"match_id": f"espn:{f['ligue']}:{f['event_id']}",
                "ligue": f["ligue"], "coup_envoi": f["coup_envoi"].isoformat(),
                "capture_le": au.isoformat(), "source": "espn",
                "score_sources_independantes": 1, "xi_officiel_primaire_verifie": False,
                "var_et_cartons_rouges": "INCONNUS", "V1_DOMINATION": None,
                "V2_GOALS": None, "statut": "REFUS"}
        minute_reelle = (au - f["coup_envoi"]).total_seconds() / 60
        if not 12 <= minute_reelle <= 18:
            resultats.append({**base, "motif": "HORS_FENETRE_T15 : aucun appel ESPN"})
            continue
        jour = f["coup_envoi"].astimezone(timezone.utc).strftime("%Y%m%d")
        url = f"{BASE}/{f['ligue']}/scoreboard?dates={jour}"
        try:
            if url not in cache:
                brut = lire(url)
                if not isinstance(brut, bytes) or len(brut) > TAILLE_MAX:
                    raise ValueError("réponse brute ESPN absente ou trop volumineuse")
                document = json.loads(brut)
                if not isinstance(document, dict) or not isinstance(document.get("events"), list):
                    raise ValueError("liste de rencontres absente")
                fin = horloge()
                if fin.tzinfo is None or fin.utcoffset() is None:
                    raise ValueError("horodatage réel de capture sans fuseau")
                cache[url] = (document, hashlib.sha256(brut).hexdigest(), fin)
            document, digest, fin = cache[url]
            evenements = [e for e in document["events"] if isinstance(e, dict) and str(e.get("id")) == f["event_id"]]
            if len(evenements) != 1:
                raise ValueError("match absent ou dupliqué dans le calendrier ESPN")
            resultat = decoder(evenements[0], f, fin)
            resultats.append({**base, **resultat, "capture_le": fin.isoformat(), "sha256_reponse_espn": digest,
                              "source_url": f"https://www.espn.com/soccer/match/_/gameId/{f['event_id']}",
                              "motif": "SOURCE_ESPN_UNIQUE : trois scores indépendants, XI primaire, incidents et calibration LIVE manquants"})
        except (ValueError, OSError, UnicodeError, TypeError, AttributeError, KeyError) as exc:
            resultats.append({**base, "motif": f"ESPN_INUTILISABLE : {type(exc).__name__} : {str(exc)[:120]}"})
    return resultats


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--entree", type=Path, help="JSON de 1 à 50 matchs ESPN pré-identifiés")
    mode.add_argument("--decouvrir", action="store_true", help="Repérer les matchs ESPN des 3 prochaines heures")
    p.add_argument("--horizon-heures", type=int, default=3, help="3 h pour XI ; jusqu'à 24 h pour le calendrier")
    p.add_argument("--ligues", help="Sous-ensemble de slugs ESPN, séparés par virgules (optionnel)")
    p.add_argument("--sortie-fixtures", type=Path, help="Nouveau fichier JSON prospectif (mode découverte)")
    p.add_argument("--journal", type=Path, help="Journal JSONL append-only, hors memoire/ et data/")
    a = p.parse_args(argv)
    ligues = json.loads(CONFIG.read_text(encoding="utf-8"))
    slugs = {r["slug"] for r in ligues["espn"]} | COMPETITIONS_INTERNATIONALES
    if a.ligues:
        selection = set(a.ligues.split(","))
        if not selection or not selection <= slugs:
            p.error("--ligues contient une compétition non autorisée")
        slugs = selection
    if a.decouvrir:
        if not a.sortie_fixtures or a.journal:
            p.error("--decouvrir exige --sortie-fixtures et refuse --journal")
        dest = a.sortie_fixtures.resolve()
        if (not dest.parent.is_dir() or any(dest.is_relative_to((ROOT / part).resolve())
                                           for part in ("memoire", "data", "megatron"))):
            raise ValueError("destination de la découverte hors mémoire, modèles et data/")
        rapport = reperer_prochains(slugs, au=datetime.now(timezone.utc),
                                    horizon_h=a.horizon_heures,
                                    horloge=lambda: datetime.now(timezone.utc))
        with dest.open("x", encoding="utf-8") as sortie:
            sortie.write(json.dumps(rapport, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({k: v for k, v in rapport.items()
                          if k not in ("fixtures", "sources_capturees")}, ensure_ascii=False))
        return 0 if rapport["matchs_trouves"] and not rapport["erreurs"] else 2
    if a.sortie_fixtures:
        p.error("--sortie-fixtures s'utilise uniquement avec --decouvrir")
    fixtures = valider_fixtures(json.loads(a.entree.read_text(encoding="utf-8")), slugs)
    resultats = collecter(fixtures, au=datetime.now(timezone.utc),
                         horloge=lambda: datetime.now(timezone.utc))
    if a.journal:
        dest = a.journal.resolve()
        if (not dest.parent.is_dir() or any(dest.is_relative_to((ROOT / part).resolve())
                                           for part in ("memoire", "data", "megatron"))):
            raise ValueError("journal réservé à un dossier dédié existant, hors mémoire et modèles")
        with dest.open("a", encoding="utf-8") as sortie:
            for resultat in resultats:
                sortie.write(json.dumps(resultat, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"captures": len(resultats), "scores_espn": sum("score" in r for r in resultats),
                      "watch": 0, "refus": len(resultats), "details": resultats}, ensure_ascii=False))
    return 0 if any("score" in r for r in resultats) else 2


if __name__ == "__main__":
    raise SystemExit(main())
