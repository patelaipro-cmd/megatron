"""Contrôles avant match SYNDICATE : évaluation initiale, vérifications à T-30 et T-5, révisions.

- ``initial`` : dans la fenêtre de 5 h (``suivi.FENETRE``), au plus tard 35 min avant le coup d'envoi ;
  les trois niveaux du favori sont enregistrés dans le registre immuable (marchés de marge distincts
  du total de buts), avec leur version et leurs sources.
- ``T-30`` (entre 35 et 25 min avant) et ``T-5`` (entre 8 et 2 min avant) : nouvelle évaluation avec
  les données collectées depuis, comparée à la précédente ; les changements (absents, compos,
  probabilités, décision) sont listés. Le registre n'est jamais réécrit : l'évaluation revue est
  ajoutée à côté (domaine ``football``), l'ancienne reste.
- ``revision`` : même chose à tout moment de la fenêtre, quand une information fiable apparaît.

Aucune décision n'est exécutée : ``activation_automatique`` reste faux.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .jeton import protege_suivi
from .ledger import Ledger, pred_key, DOMAIN as REGISTRE
from .store import MemoryStore, now_utc, parse_dt
from .suivi import FENETRE

DOMAINE = "football"
MOMENTS = {"initial": (35, 5 * 60), "T-30": (25, 35), "T-5": (2, 8)}  # minutes avant le coup d'envoi (min, max)
SEUIL_CHANGEMENT = 0.01


def _resume(ev: dict) -> dict:
    f = ev["fiche"]
    eqs = (f["domicile"], f["exterieur"])
    return {
        "niveaux": ev["niveaux"], "decision": ev["decision"]["decision"],
        "bloquants": ev["decision"]["bloquants"], "raisons": ev["decision"]["raisons"],
        "absents": {t: sorted(j["joueur"] for j in f["rubriques"]["absences"]["equipes"][t]["joueurs"]) for t in eqs},
        "indices_absences": {t: [f["rubriques"]["absences"]["equipes"][t][k] for k in ("indice_offensif", "indice_defensif")] for t in eqs},
        "compos_confirmees": {t: f["rubriques"]["compositions"]["equipes"][t]["confirmee"] for t in eqs},
        "titulaires": {t: f["rubriques"]["compositions"]["equipes"][t]["titulaires"] for t in eqs},
        "rubriques_a_verifier": f["rubriques_a_verifier"], "alertes": f["alertes"],
        "versions": {"syndicate": ev["version"], "fiche": f["version"]},
        "analyse_le": ev["analyse_le"],
    }


def changements(avant: dict, apres: dict) -> list[str]:
    out = []
    for k, p in apres["niveaux"]["probabilites"].items():
        q = avant["niveaux"]["probabilites"][k]
        if abs(p - q) >= SEUIL_CHANGEMENT:
            out.append(f"{k} : {q:.1%} → {p:.1%}")
    if avant["niveaux"]["favori"] != apres["niveaux"]["favori"]:
        out.append(f"favori : {avant['niveaux']['favori']} → {apres['niveaux']['favori']}")
    for t, noms in apres["absents"].items():
        nouveaux, retours = set(noms) - set(avant["absents"].get(t, [])), set(avant["absents"].get(t, [])) - set(noms)
        if nouveaux:
            out.append(f"{t} : nouveaux absents {sorted(nouveaux)}")
        if retours:
            out.append(f"{t} : retirés des absents {sorted(retours)}")
    for t, ok in apres["compos_confirmees"].items():
        if ok and not avant["compos_confirmees"].get(t):
            out.append(f"{t} : compo officielle publiée")
        elif ok and set(apres["titulaires"][t]) != set(avant["titulaires"].get(t, [])):
            out.append(f"{t} : compo modifiée")
    if avant["decision"] != apres["decision"]:
        out.append(f"décision : {avant['decision']} → {apres['decision']}")
    return out


def _verifier_moment(moment: str, now: datetime, kickoff: datetime) -> None:
    if moment not in MOMENTS and moment != "revision":
        raise ValueError(f"moment inconnu : {moment!r} (initial, T-30, T-5, revision)")
    if now >= kickoff:
        raise ValueError("coup d'envoi passé : aucun contrôle enregistré")
    if now < kickoff - FENETRE:
        raise ValueError(f"trop tôt : la fenêtre de {FENETRE.total_seconds() / 3600:g} h n'est pas ouverte")
    if moment in MOMENTS:
        lo, hi = MOMENTS[moment]
        reste = (kickoff - now).total_seconds() / 60
        if not lo <= reste <= hi:
            raise ValueError(f"{moment} : {reste:.0f} min avant le coup d'envoi, attendu entre {lo} et {hi} min")


def historique(store: MemoryStore, match_id: str) -> list:
    return sorted((e for e in store.active(DOMAINE) if e.key.startswith(f"syndicate:{match_id}:")),
                  key=lambda e: e.recorded_at)


@protege_suivi
def enregistrer(store: MemoryStore, match_id: str, evaluation: dict, moment: str, *, now: datetime | None = None,
                source: str = "megatron syndicate", acces: str | None = None, jeton_id: str | None = None) -> dict:
    now = parse_dt(now or now_utc())
    kickoff = parse_dt(evaluation["match"]["coup_envoi"])
    _verifier_moment(moment, now, kickoff)
    if parse_dt(evaluation["analyse_le"]) > now:
        raise ValueError("évaluation datée après l'instant d'enregistrement")
    precedents = historique(store, match_id)
    if moment != "revision" and any(e.key == f"syndicate:{match_id}:{moment}" for e in precedents):
        raise ValueError(f"{match_id} : contrôle {moment} déjà enregistré, rien n'est réécrit")
    if moment != "initial" and not any(e.key.endswith(":initial") for e in precedents):
        raise ValueError(f"{match_id} : aucune évaluation initiale, enregistrer d'abord le moment initial")
    resume = _resume(evaluation)
    diff = changements(precedents[-1].value["resume"], resume) if precedents else []
    registre = []
    if moment == "initial":
        ledger = Ledger(store, acces=acces, jeton_id=jeton_id)
        n = evaluation["niveaux"]
        side, version = n["favori"], f"{evaluation['version']}:{n['statut']}"
        for niveau, marche in (("victoire_par_2_ou_plus", f"{side}_MARGE_2PLUS"), ("victoire_par_3_ou_plus", f"{side}_MARGE_3PLUS")):
            p = n["probabilites"][niveau]
            if store.active(REGISTRE, pred_key(match_id, version, marche)):
                raise ValueError(f"{match_id} : {marche} déjà prévu sous {version}")
            ledger.predict(match_id, kickoff, {"oui": p, "non": 1 - p}, model_version=version, source=source,
                           recorded_at=now, data_cutoff=evaluation["analyse_le"], market=marche)
            registre.append(f"{marche}:{version}")
    cle = f"syndicate:{match_id}:{moment}" + (f":{now.isoformat()}" if moment == "revision" else "")
    store.record(DOMAINE, cle, {"match_id": match_id, "moment": moment, "coup_envoi": kickoff.isoformat(),
                                "resume": resume, "changements": diff, "recalcule": moment != "initial"},
                 source=source, status="verifie", recorded_at=now, supersede=False)
    return {"match_id": match_id, "moment": moment, "decision": resume["decision"], "changements": diff,
            "enregistre_registre": registre, "activation_automatique": False,
            "minutes_avant_coup_envoi": round((kickoff - now) / timedelta(minutes=1), 1)}
