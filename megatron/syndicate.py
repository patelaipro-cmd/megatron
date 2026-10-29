"""SYNDICATE DOMINATION : trois niveaux de victoire du favori, angles morts, décision indicative.

Niveaux (marges de victoire, jamais le total de buts ; voir docs/marges-victoire.md) :
victoire simple, victoire par au moins deux buts, victoire par au moins trois buts. Ils sont
emboîtés : P(3+) <= P(2+) <= P(victoire). Calcul sur la même matrice Poisson ``poisson-v5``
(intensités de StatsAgent, matchs strictement antérieurs) ; recalibration de Platt par niveau validée par EXP-012
(``CALIBRATION_NIVEAUX``) ; les valeurs brutes restent affichées.

Décision GO / SECURE / WATCH / PASS : règles provisoires écrites ci-dessous, seuils non calibrés,
**aucune activation automatique** (``ACTIVATION_AUTOMATIQUE`` est une constante fausse, aucune
fonction ne place de pari ni n'envoie d'ordre). GO n'est émis que si les niveaux sont recalibrés
et la zone de décision P(2+) >= 60 % validée (``ZONE_GO_VALIDEE``, faux après EXP-012) : sinon
il est rétrogradé en SECURE avec la raison.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import angles_morts, contexte_favori, marches, marges, wininvest
from .agents import poisson_1x2
from .models import calibrer_1x2
from .store import now_utc, parse_dt

VERSION = "syndicate-domination-v1"
ACTIVATION_AUTOMATIQUE = False
NIVEAUX = ("victoire_simple", "victoire_par_2_ou_plus", "victoire_par_3_ou_plus")
# (a, b) de Platt par niveau : EXP-012 (calibration 2016/17-2019/20, critères N1-N3 tenus sur 2020/21-2025/26)
CALIBRATION_NIVEAUX: dict[str, tuple[float, float]] | None = {
    "victoire_simple": (0.079141, 1.173564),
    "victoire_par_2_ou_plus": (0.09015, 1.084905),
    "victoire_par_3_ou_plus": (0.024482, 0.964744),
}
# Zone de décision GO (P(2+) >= 0,60) : 216 matchs du test, moins des 500 exigés pour déclarer une tranche
# calibrée, écart observé 4,5 points (EXP-012). GO reste rétrogradé en SECURE tant qu'elle n'est pas validée.
ZONE_GO_VALIDEE = False
CALIBRATION_1X2 = (1.160088, 0.016201, 0.150311)  # poisson-v5-cal (EXP-010), pour la référence 1X2
SEUILS = {"favori_minimum": 0.50, "secure_victoire": 0.60, "go_marge_2": 0.60, "indice_absence_majeur": 0.15}


def niveaux(lam_home: float, lam_away: float) -> dict:
    """Trois niveaux du favori (côté au plus grand P(victoire)) sur une seule matrice de scores."""
    brut = marges.calculer(lam_home, lam_away)
    side = "H" if brut["niveaux"]["H"]["victoire_simple"] >= brut["niveaux"]["A"]["victoire_simple"] else "A"
    p = dict(brut["niveaux"][side])
    statut = "EXPERIMENTAL_NON_CALIBRE"
    if CALIBRATION_NIVEAUX:
        p = {k: marches.platt(v, *CALIBRATION_NIVEAUX[k])["oui"] if k in CALIBRATION_NIVEAUX else v for k, v in p.items()}
        p["victoire_par_2_ou_plus"] = min(p["victoire_par_2_ou_plus"], p["victoire_simple"])
        p["victoire_par_3_ou_plus"] = min(p["victoire_par_3_ou_plus"], p["victoire_par_2_ou_plus"])
        statut = "RECALIBRE_EXP-012" if set(CALIBRATION_NIVEAUX) == set(NIVEAUX) else "PARTIELLEMENT_RECALIBRE"
    defaite, nul = brut["1X2"]["A" if side == "H" else "H"], brut["1X2"]["D"]
    reste = (1 - p["victoire_simple"]) / (defaite + nul)  # nul et défaite rééchelonnés : les trois issues somment à 1
    return {"favori": side, "probabilites": {k: round(p[k], 4) for k in NIVEAUX}, "statut": statut,
            "brut": {k: round(brut["niveaux"][side][k], 4) for k in NIVEAUX},
            "risques": {"defaite": round(defaite * reste, 4), "nul": round(nul * reste, 4)},
            "risques_bruts": {"defaite": round(defaite, 4), "nul": round(nul, 4)}}


def decider(n: dict, fiche: dict, contexte: dict | None, moment: str | None = None) -> dict:
    """Décision indicative et ses raisons ; rien n'est déclenché."""
    p = n["probabilites"]
    fav_nom = fiche["domicile"] if n["favori"] == "H" else fiche["exterieur"]
    raisons, bloquants = [], []
    if p["victoire_simple"] < SEUILS["favori_minimum"]:
        bloquants.append(f"favori à {p['victoire_simple']:.0%} (< {SEUILS['favori_minimum']:.0%})")
    if fiche["alertes"]:
        bloquants.extend(fiche["alertes"])
    if contexte is not None and not contexte["ok"]:
        bloquants.append("grille des angles morts invalide")
    abs_fav = fiche["rubriques"]["absences"]["equipes"][fav_nom]
    if abs_fav["contradictions"]:
        (bloquants if moment == "T-5" else raisons).append("absences contradictoires : " + "; ".join(abs_fav["contradictions"]))
    compos = fiche["rubriques"]["compositions"]["equipes"]
    if not all(c["confirmee"] for c in compos.values()):
        (bloquants if moment == "T-5" else raisons).append("compositions officielles non confirmées")
    if max(abs_fav["indice_offensif"], abs_fav["indice_defensif"]) >= SEUILS["indice_absence_majeur"]:
        raisons.append(f"absences importantes chez le favori (indices {abs_fav['indice_offensif']}/{abs_fav['indice_defensif']}, non calibrés)")
    autres = [k for k in fiche["rubriques_a_verifier"] if k not in ("compositions", "absences")]
    if autres:
        raisons.append("rubriques à vérifier : " + ", ".join(autres))
    if contexte is None or contexte["statut"] != "DOCUMENTE_NON_VERIFIE":
        raisons.append("angles morts non documentés entièrement")
    if bloquants:
        decision = "PASS"
    elif raisons or p["victoire_simple"] < SEUILS["secure_victoire"]:
        decision = "WATCH"
    elif p["victoire_par_2_ou_plus"] >= SEUILS["go_marge_2"]:
        decision = "GO" if n["statut"] == "RECALIBRE_EXP-012" and ZONE_GO_VALIDEE else "SECURE"
        if decision == "SECURE":
            raisons.append("GO bloqué : zone P(2+) >= 60 % non validée (EXP-012 : 216 matchs, écart 4,5 points)"
                           if n["statut"] == "RECALIBRE_EXP-012" else "GO bloqué : probabilités de marge non validées (EXP-012)")
    else:
        decision = "SECURE"
    return {"decision": decision, "bloquants": bloquants, "raisons": raisons, "seuils": SEUILS,
            "activation_automatique": ACTIVATION_AUTOMATIQUE,
            "nature": "indicative, règles provisoires non calibrées ; aucune action déclenchée"}


def evaluer(division: str, home: str, away: str, kickoff: str | datetime, *, at: str | datetime | None = None,
            history=None, dossier_externe: Path | None = None, contexte: dict | None = None,
            cotes: list[dict] | None = None, absents_declares: dict | None = None, moment: str | None = None) -> dict:
    at_dt = parse_dt(at or now_utc())
    f = wininvest.fiche(division, home, away, kickoff, at=at_dt, history=history, dossier_externe=dossier_externe,
                        cotes=cotes, absents_declares=absents_declares)
    lh, la = f["intensites_v5"]["H"], f["intensites_v5"]["A"]
    n = niveaux(lh, la)
    day = parse_dt(kickoff).date()
    hist = [m for m in (history if history is not None else wininvest.historique(division, day)) if m.day < day]
    fit_force = {t: v for t, v in f["rubriques"]["force_adversaires"]["force"].items()}
    try:
        details = angles_morts.load_details()
    except OSError:
        details = {}
    am = angles_morts.analyser(hist, details, home, away, day, lh, la, version="poisson-v5", strength=fit_force)
    rapport = contexte_favori.verifier(contexte, at=at_dt) if contexte is not None else None
    if rapport is not None and rapport["ok"] and (contexte.get("home"), contexte.get("away")) != (home, away):
        rapport = {**rapport, "ok": False, "erreurs": rapport["erreurs"] + ["grille d'un autre match"]}
    return {"version": VERSION, "match": {"division": division, "domicile": home, "exterieur": away,
                                          "coup_envoi": parse_dt(kickoff).isoformat()},
            "analyse_le": at_dt.isoformat(), "moment": moment,
            "niveaux": n, "reference_1x2_v5cal": {k: round(v, 4) for k, v in calibrer_1x2(poisson_1x2(lh, la), *CALIBRATION_1X2).items()},
            "angles_morts": {"questions": am["questions"], "a_verifier_hors_data": am["a_verifier_hors_data"],
                             "grille_13_angles": rapport},
            "fiche": f, "decision": decider(n, f, rapport, moment),
            "ajustement_probabilites": "aucun : absences et angles restent descriptifs (EXP-009, EXP-013)"}
