"""Capture de disponibilité de pages football publiques, sans scraper les comptes Premium.

Entrée : JSON {"match_id": "...", "checkpoint": "T-3h", "urls":
[{"source": "sportsmole", "url": "https://www.sportsmole.co.uk/..."}]}.
Sortie : journal JSONL attribué et horodaté ; aucune extraction de score/XI.
Les informations structurées doivent être relues/confirmées séparément avant
de remplir le contrat de ``megatron.veille_live.assembler_t15``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from megatron.veille_live import CHECKPOINTS, DOMAINES
from megatron.store import parse_dt

TAILLE_MAX = 500_000
NOMBRE_MAX = 6
TIMEOUT = 12
TOLERANCES_MIN = {"T-3h": 10, "T-60": 8, "T-30": 8, "T-5": 3, "T+15": 3}
HEADERS = {"User-Agent": "megatron-veille/0.1 (contact: repository patelaipro-cmd/megatron)",
           "Accept": "text/html,application/json;q=0.9,*/*;q=0.1"}


class _RedirectionAutorisee(urllib.request.HTTPRedirectHandler):
    def __init__(self, source):
        super().__init__()
        self.source = source

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _valider_url(self.source, newurl)  # contrôler avant de suivre le lien
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _ouvrir_public(req, timeout, source):
    return urllib.request.build_opener(_RedirectionAutorisee(source)).open(req, timeout=timeout)


def _valider_url(source: str, url: str) -> None:
    if source not in DOMAINES:
        raise ValueError(f"fournisseur inconnu : {source!r}")
    if source == "officiel":
        raise ValueError("capture officielle : exiger le site explicite et une vérification humaine")
    if not isinstance(url, str):
        raise ValueError("URL texte requise")
    p = urlsplit(url)
    domain = DOMAINES[source]
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise ValueError("URL publique HTTPS sans identifiants requise")
    if p.query or p.fragment:
        raise ValueError("URL avec paramètres ou fragment refusée : risque de divulgation de session")
    if not (p.hostname.lower() == domain or p.hostname.lower().endswith("." + domain)):
        raise ValueError("nom de domaine incompatible avec la source")
    if p.port not in (None, 443):
        raise ValueError("port HTTPS non standard refusé")


def capturer(doc: dict, *, ouvrir=None, au: datetime | None = None) -> list[dict]:
    """Une requête par URL ; résultat HTTP réel ou erreur, jamais une donnée sportive inventée."""
    if not isinstance(doc, dict) or not isinstance(doc.get("match_id"), str) or not doc["match_id"].strip():
        raise ValueError("match_id requis")
    phase = doc.get("checkpoint")
    if phase not in {*CHECKPOINTS, "SONDE_RESEAU"}:
        raise ValueError("checkpoint ou SONDE_RESEAU requis")
    urls = doc.get("urls")
    if not isinstance(urls, list) or not 1 <= len(urls) <= NOMBRE_MAX:
        raise ValueError("1 à 6 pages maximum par collecte")
    valides = []
    for row in urls:
        if not isinstance(row, dict):
            raise ValueError("source/url requises")
        _valider_url(row.get("source"), row.get("url"))
        valides.append(row)
    date_capture = au or datetime.now(timezone.utc)
    if date_capture.tzinfo is None:
        raise ValueError("date de collecte sans fuseau")
    if phase != "SONDE_RESEAU":
        if "kickoff" not in doc:
            raise ValueError("kickoff réel obligatoire pour tout contrôle temporel")
        kickoff = parse_dt(doc["kickoff"])
        if abs((date_capture - (kickoff + timedelta(minutes=CHECKPOINTS[phase]))).total_seconds()) > 60 * TOLERANCES_MIN[phase]:
            raise ValueError(f"{phase} hors fenêtre : capture interdite comme relevé de contrôle")
    out = []
    for row in valides:
        source, url = row["source"], row["url"]
        statut, code, error, digest, size, type_contenu = "ERREUR", 0, None, None, None, None
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            ouvrir_courant = ouvrir or (lambda requete, timeout: _ouvrir_public(requete, timeout, source))
            with ouvrir_courant(req, timeout=TIMEOUT) as response:
                # Refuse les redirections vers un autre domaine/site inattendu.
                _valider_url(source, response.geturl())
                code = int(response.status)
                type_contenu = response.headers.get("Content-Type", "")
                blob = response.read(TAILLE_MAX + 1)
                size = len(blob)
                digest = hashlib.sha256(blob).hexdigest()
                statut = "CAPTURE_PARTIELLE" if len(blob) > TAILLE_MAX else "HTTP_OK"
                if code != 200:
                    statut = "HTTP_NON_200"
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            if isinstance(exc, urllib.error.HTTPError):
                code = exc.code
            error = str(exc)[:160]
        out.append({"match_id": doc["match_id"], "checkpoint": phase,
                    "capture_le": date_capture.isoformat(), "source": source, "url": url,
                    "code_http": code, "statut": statut, "erreur": error,
                    "type_contenu": type_contenu, "octets_lus": size, "sha256": digest,
                    "extraction_sportive": "NON_EFFECTUEE",
                    "acces": "PAGE_PUBLIQUE_SEULEMENT"})
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--entree", required=True, type=Path)
    parser.add_argument("--sortie", required=True, type=Path, help="fichier JSONL dédié ; parent existant")
    args = parser.parse_args(argv)
    try:
        doc = json.loads(args.entree.read_text(encoding="utf-8"))
        result = capturer(doc)
        if not args.sortie.parent.is_dir():
            raise ValueError("dossier de sortie inexistant")
        if args.sortie.name in ("performances.jsonl", "decisions.jsonl"):
            raise ValueError("interdiction d'écrire dans le registre prospectif ou les décisions")
        with args.sortie.open("a", encoding="utf-8") as journal:
            for item in result:
                journal.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"refus : {exc}")
        return 2
    print(json.dumps({"captures": len(result), "http_200": sum(r["code_http"] == 200 for r in result),
                      "partielles": [r["source"] for r in result if r["statut"] == "CAPTURE_PARTIELLE"],
                      "echecs": [f'{r["source"]}:{r["code_http"]}' for r in result if r["code_http"] != 200]}, ensure_ascii=False))
    return 0 if all(r["code_http"] == 200 for r in result) else 1


if __name__ == "__main__":
    raise SystemExit(main())
