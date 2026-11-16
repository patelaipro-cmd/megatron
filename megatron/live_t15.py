"""Instantané SYNDICATE T+15 : Poisson conditionnel exploratoire, jamais un signal GO.

Le modèle fige les intensités de buts AVANT le coup d'envoi et ne met à jour
que le score observé et le temps restant. Aucun coefficient prématch de Platt,
aucune pondération des compositions et aucun registre prospectif ne sont touchés.

Cet estimateur constitue une hypothèse mathématique en direct, PAS un modèle
live validé/calibré. Les événements non modélisés suspendent le calcul.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import timedelta
from pathlib import Path

from .store import now_utc, parse_dt

VERSION = "live-t15-poisson-conditionnel-v0"
FENETRE_T15 = (12, 18)  # minutes sur l'horloge du match
AGE_SCORE_MAX = timedelta(minutes=3)
DEVIATION_HORLOGE_MAX = 3  # minutes entre temps réel et horloge de match
MARCHES_V2 = {"OVER_1_5": 2, "OVER_2_5": 3, "OVER_3_5": 4}


def _date(value, champ):
    try:
        return parse_dt(value)
    except (TypeError, AttributeError, ValueError) as exc:
        raise ValueError(f"{champ} : date-heure avec fuseau requise") from exc


def _entier(value, champ):
    if type(value) is not int or value < 0:
        raise ValueError(f"{champ} : entier positif ou nul requis")
    return value


def _taux(value, champ):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not 0 <= value <= 10:
        raise ValueError(f"{champ} : intensité finie comprise entre 0 et 10")
    return float(value)


def _pmf(mu):
    """Distribution de Poisson (0..60), masse résiduelle < 1e-12 pour mu <= 10."""
    out = [math.exp(-mu)]
    for n in range(1, 61):
        out.append(out[-1] * mu / n)
    mass = math.fsum(out)
    return [p / mass for p in out]


def _au_moins(nombre_observe, mu_restant, seuil):
    manque = seuil - nombre_observe
    if manque <= 0:
        return 1.0
    return min(1.0, max(0.0, math.fsum(_pmf(mu_restant)[manque:])))


def _marges(score_h, score_a, mu_h, mu_a):
    ph, pa = _pmf(mu_h), _pmf(mu_a)
    p = {"H": 0.0, "D": 0.0, "A": 0.0}
    m = {"H_MARGE_2PLUS": 0.0, "H_MARGE_3PLUS": 0.0,
         "A_MARGE_2PLUS": 0.0, "A_MARGE_3PLUS": 0.0}
    for gh, hproba in enumerate(ph):
        for ga, aproba in enumerate(pa):
            prob = hproba * aproba
            ecart = score_h + gh - score_a - ga
            p["H" if ecart > 0 else "A" if ecart < 0 else "D"] += prob
            if ecart >= 2:
                m["H_MARGE_2PLUS"] += prob
            if ecart >= 3:
                m["H_MARGE_3PLUS"] += prob
            if ecart <= -2:
                m["A_MARGE_2PLUS"] += prob
            if ecart <= -3:
                m["A_MARGE_3PLUS"] += prob
    return p, m


def _comparaison_mi_temps(observes, mu_mt1_restant, mu_mt2):
    """P(MT2>MT1) / P(MT1>MT2), sans données d'horodatage des buts futurs."""
    p1, p2 = _pmf(mu_mt1_restant), _pmf(mu_mt2)
    avant, apres, egal = 0.0, 0.0, 0.0
    for n1, q1 in enumerate(p1):
        for n2, q2 in enumerate(p2):
            product = q1 * q2
            if observes + n1 > n2:
                avant += product
            elif observes + n1 < n2:
                apres += product
            else:
                egal += product
    return {"MT1_plus": avant, "MT2_plus": apres, "egal": egal}


def evaluer(snapshot: dict) -> dict:
    """Évalue un instantané T+15 horodaté, en restant strictement exploratoire.

    Les sources, XI et événements sont déclarés par l'appelant : ce module
    valide leur cohérence temporelle, sans prétendre les avoir lus sur le Web.
    """
    if not isinstance(snapshot, dict):
        raise ValueError("instantané JSON objet requis")
    match_id = snapshot.get("match_id")
    if not isinstance(match_id, str) or not match_id.strip():
        raise ValueError("match_id non vide requis")
    kickoff = _date(snapshot.get("kickoff"), "kickoff")
    observed_at = _date(snapshot.get("observed_at"), "observed_at")
    minute = snapshot.get("minute")
    if type(minute) not in (int, float) or not math.isfinite(minute):
        raise ValueError("minute : nombre fini requis")
    if not FENETRE_T15[0] <= minute <= FENETRE_T15[1]:
        raise ValueError(f"instantané hors T+15 : horloge attendue {FENETRE_T15}")
    ecoule = (observed_at - kickoff).total_seconds() / 60
    if ecoule < 0 or abs(ecoule - minute) > DEVIATION_HORLOGE_MAX:
        raise ValueError("heure de relevé incohérente avec le coup d'envoi et la minute annoncée")
    score = snapshot.get("score")
    if not isinstance(score, dict):
        raise ValueError("score {H, A} requis")
    sh, sa = _entier(score.get("H"), "score.H"), _entier(score.get("A"), "score.A")

    calcul_at = now_utc()
    resultat = {"version": VERSION, "phase": "LIVE_T15", "match_id": match_id,
                "kickoff": kickoff.isoformat(), "observed_at": observed_at.isoformat(),
                "calcule_le": calcul_at.isoformat(),
                "nature": "REJEU_NON_PROSPECTIF" if abs((calcul_at - observed_at).total_seconds()) > 300 else "LIVE_A_CONFIRMER",
                "minute": minute, "score": {"H": sh, "A": sa},
                "statut": "REFUS", "motifs": [], "V1_DOMINATION": None,
                "V2_GOALS": None, "poids_modifies": False, "activation_automatique": False,
                "validation": "NON_CALIBRE_EN_DIRECT", "registre_prospectif_modifie": False}
    motifs = resultat["motifs"]

    base = snapshot.get("baseline")
    if not isinstance(base, dict):
        motifs.append("intensités prématch absentes")
    else:
        # Les valeurs invalides (NaN, négatives, etc.) sont des erreurs de schéma.
        lh = _taux(base.get("lambda_H"), "baseline.lambda_H") if "lambda_H" in base else None
        la = _taux(base.get("lambda_A"), "baseline.lambda_A") if "lambda_A" in base else None
        if lh is None or la is None:
            motifs.append("intensités H/A prématch manquantes")
        if not isinstance(base.get("modele"), str) or not base.get("modele"):
            motifs.append("version du modèle de référence manquante")
        if not isinstance(base.get("source"), str) or not base.get("source"):
            motifs.append("provenance du modèle prématch manquante")
        if "calcule_le" not in base:
            motifs.append("horodatage du modèle prématch manquant")
        elif _date(base["calcule_le"], "baseline.calcule_le") >= kickoff:
            motifs.append("fuite temporelle : taux de base calculés après le coup d'envoi")

    verif = snapshot.get("verification", {})
    if not isinstance(verif, dict):
        raise ValueError("verification doit être un objet")
    sources = verif.get("score_sources", [])
    if not isinstance(sources, list) or len({v.strip() for v in sources if isinstance(v, str) and v.strip()}) < 3:
        motifs.append("moins de trois sources indépendantes déclarées pour le score")
    if verif.get("conflit_sources") is not False:
        motifs.append("concordance du score non confirmée")
    if "score_collecte_le" not in verif:
        motifs.append("date du dernier relevé de score manquante")
    else:
        score_at = _date(verif["score_collecte_le"], "verification.score_collecte_le")
        if score_at > observed_at or score_at < kickoff:
            motifs.append("horodatage du score impossible")
        elif observed_at - score_at > AGE_SCORE_MAX:
            motifs.append("score périmé (plus de trois minutes)")
    if verif.get("xi_officiels") is not True or not verif.get("xi_source"):
        motifs.append("compositions officielles non documentées")
    if "xi_collecte_le" not in verif:
        motifs.append("horodatage des compositions officielles manquant")
    else:
        xi_at = _date(verif["xi_collecte_le"], "verification.xi_collecte_le")
        if xi_at > observed_at:
            motifs.append("fuite temporelle : XI relevés après l'instantané T+15")
    if verif.get("xi_identiques_hypothese_base") is not True:
        motifs.append("composition différente ou non comparable au modèle prématch")
    if verif.get("var_en_cours") is not False:
        motifs.append("VAR ou incident en cours non exclu")
    if verif.get("cartons_rouges") != {"H": 0, "A": 0}:
        motifs.append("cartons rouges inconnus ou présents : taux non adaptés")
    if motifs:
        return resultat

    # Hypothèse de temps homogène : aucun effet de score, fatigue, VAR ni XI.
    # À partir de T+15, on CONDITIONNE sur le score, et non sur les résultats
    # avant match. Aucun Platt prématch n'est appliqué au marché live.
    restant = 90 - minute
    mu_h, mu_a = lh * restant / 90, la * restant / 90
    p1x2, marges = _marges(sh, sa, mu_h, mu_a)
    total_observe, total_rate = sh + sa, lh + la
    mu_mt1 = total_rate * (45 - minute) / 90
    mu_mt2 = total_rate * 45 / 90
    resultat["statut"] = "WATCH"
    resultat["V1_DOMINATION"] = {
        "1X2_brut": p1x2,
        "marges_brutes": marges,
        "modele": "POISSON_CONDITIONNEL_NON_CALIBRE",
        "decision": "WATCH_EXPERIMENTAL_SEULEMENT",
    }
    resultat["V2_GOALS"] = {
        "over_match_brut": {k: _au_moins(total_observe, mu_h + mu_a, n)
                            for k, n in MARCHES_V2.items()},
        "MT1": {"buts_esperes": total_observe + mu_mt1,
                "over_0_5": _au_moins(total_observe, mu_mt1, 1),
                "over_1_5": _au_moins(total_observe, mu_mt1, 2)},
        "MT2": {"buts_esperes": mu_mt2, "over_0_5": _au_moins(0, mu_mt2, 1),
                "over_1_5": _au_moins(0, mu_mt2, 2)},
        "repartition": _comparaison_mi_temps(total_observe, mu_mt1, mu_mt2),
        "modele": "POISSON_CONDITIONNEL_NON_CALIBRE",
        "decision": "WATCH_EXPERIMENTAL_SEULEMENT",
    }
    resultat["intensites_prematch_figees"] = {"H": lh, "A": la, "modele": base["modele"],
                                             "calcule_le": _date(base["calcule_le"], "baseline.calcule_le").isoformat()}
    resultat["hypotheses"] = ["intensités de buts constantes par minute",
                              "aucun ajustement des taux après le score ou selon la composition",
                              "aucune recalibration live validée ; ne pas interpréter WATCH comme GO",
                              "sources déclarées par l'appelant, non authentifiées par le programme",
                              "les calculs rétrospectifs sont marqués REJEU_NON_PROSPECTIF"]
    return resultat


def enregistrer_journal(chemin: str | Path, resultat: dict) -> None:
    """Journal distinct append-only, avec identifiant de contenu et refus de doublon.

    Le journal demandé doit être explicitement nommé ``live_t15.jsonl`` ;
    le registre ``performances.jsonl`` des prévisions gelées reste intact.
    """
    path = Path(chemin)
    if path.name != "live_t15.jsonl":
        raise ValueError("journal direct obligatoire : fichier live_t15.jsonl distinct du registre prospectif")
    if resultat["statut"] != "WATCH":
        raise ValueError("instantané REFUS : aucune probabilité à archiver")
    # Les mêmes faits live ne deviennent pas des instantanés distincts
    # simplement parce qu'ils ont été recalculés quelques secondes plus tard.
    identite = {k: v for k, v in resultat.items() if k not in ("calcule_le", "nature")}
    contenu = json.dumps(identite, ensure_ascii=False, sort_keys=True, allow_nan=False)
    ident = hashlib.sha256(contenu.encode("utf-8")).hexdigest()[:24]
    ligne = json.dumps({"id": ident, "contenu": resultat}, ensure_ascii=False, sort_keys=True, allow_nan=False)
    # Aucun répertoire implicite : l'appelant choisit et prépare l'emplacement.
    if not path.parent.is_dir():
        raise ValueError("dossier de journal absent")
    if path.exists():
        with path.open(encoding="utf-8") as reader:
            if any(json.loads(row)["id"] == ident for row in reader if row.strip()):
                raise ValueError("instantané live T+15 déjà présent : pas de doublon")
    with path.open("a", encoding="utf-8") as stream:
        stream.write(ligne + "\n")
