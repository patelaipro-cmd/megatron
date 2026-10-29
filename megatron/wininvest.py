"""Fiche d'analyse WININVEST : les huit rubriques de la méthode, calculées sans fuite temporelle.

Chaque rubrique porte un ``statut`` : ``mesure`` (calculé depuis ``data/`` ou la collecte externe,
avec sa source), ``partiel`` (une partie seulement est mesurable) ou ``a_verifier`` (aucune source
automatique : à documenter par une source datée). Seuls les matchs strictement antérieurs au jour
du coup d'envoi et les données collectées avant l'instant d'analyse sont lus. La fiche décrit ;
elle ne modifie aucune probabilité.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from . import absences, data, externe, models
from .angles_morts import _points, _table, _team_view
from .data import Match, season_of
from .store import now_utc, parse_dt

VERSION = "wininvest-fiche-v1"
V5 = {"half_life": 270.0, "shrink": 2.0, "proxy": "cadres", "proxy_weight": 0.35}  # réglage de StatsAgent (EXP-008)
FRAICHEUR_MAX_JOURS = 10  # au-delà, forme, classement et fatigue ne décrivent plus le présent
RUBRIQUES = ("forme", "confrontations", "force_adversaires", "classement_enjeux", "compositions",
             "absences", "fatigue", "cotes")


def historique(division: str, day: date, path=None) -> list[Match]:
    """Matchs de la division strictement antérieurs au jour du match."""
    return [m for m in data.load(path or data.CURRENT, divisions={division}) if m.day < day]


def _res(gf: int, ga: int) -> str:
    return "V" if gf > ga else "N" if gf == ga else "D"


def _forme(history: list[Match], team: str, force: dict[str, float], n: int = 5) -> dict:
    ms = [m for m in history if team in (m.home, m.away)][-n:]
    lignes = []
    for m in ms:
        gf, ga, _, _, dom = _team_view(m, team)
        adv = m.away if dom else m.home
        lignes.append({"date": m.day.isoformat(), "adversaire": adv, "lieu": "dom" if dom else "ext",
                       "score": f"{gf}-{ga}", "resultat": _res(gf, ga), "force_adversaire": round(force.get(adv, 1.0), 3)})
    pts = sum(_points(*(_team_view(m, team)[:2])) for m in ms)
    return {"matchs": lignes, "points": pts, "sur": 3 * len(ms),
            "buts": [sum(_team_view(m, team)[0] for m in ms), sum(_team_view(m, team)[1] for m in ms)]}


def _classement(history: list[Match], day: date) -> list[tuple[str, int, int]]:
    saison = [m for m in history if season_of(m.day) == season_of(day)]
    table = _table(saison)
    return sorted(((t, p, j) for t, (p, j) in table.items()), key=lambda x: (-x[1], x[2], x[0]))


def _enjeu(rangs: list[tuple[str, int, int]], team: str) -> dict | None:
    pos = next((i for i, r in enumerate(rangs) if r[0] == team), None)
    if pos is None:
        return None
    n, pts = len(rangs), rangs[pos][1]

    def ecart(rang):  # points d'écart avec le rang donné (1 = premier)
        return pts - rangs[min(rang, n) - 1][1] if n else None
    return {"rang": pos + 1, "points": pts, "joues": rangs[pos][2], "equipes": n,
            "ecart_premier": ecart(1), "ecart_4e": ecart(4), "ecart_relegable": pts - rangs[n - 3][1] if n >= 3 else None}


def _fatigue(history: list[Match], team: str, kickoff: datetime) -> dict:
    ms = [m for m in history if team in (m.home, m.away)]
    if not ms:
        return {"jours_repos": None, "matchs_14j": 0}
    dernier = ms[-1]
    return {"jours_repos": (kickoff.date() - dernier.day).days, "dernier_match": dernier.day.isoformat(),
            "matchs_14j": sum(1 for m in ms if (kickoff.date() - m.day).days <= 14),
            "deplacement_precedent": dernier.away == team}


def _statut_absence_fpl(ligne: dict) -> str | None:
    """Convertit les libellés *réels* FPL en statuts du moteur.

    Les joueurs partis en transfert ne sont pas des blessés du club précédent.
    Une indisponibilité non expliquée reste incertaine : ne pas affirmer une blessure.
    """
    statut = (ligne.get("statut") or "").strip().casefold()
    news = (ligne.get("news") or "").casefold()
    depart = ("has joined", "signed for", "has left", "departed the club", "has returned to", "transferred to",
              "loan move", "on loan at")
    if any(m in news for m in depart) or statut in ("a", "disponible"):
        return None
    if statut in ("i", "blesse", "blessé"):
        return "blesse"
    if statut in ("s", "suspendu"):
        return "suspendu"
    if statut in ("d", "incertain"):
        return "incertain"
    if statut in ("n", "non_eligible", "non éligible"):
        return "absent"
    if statut in ("u", "indisponible"):
        return "incertain"
    return None  # valeur inconnue : ne pas ajouter une absence fictive


def _implicites(cotes: tuple[float, float, float]) -> dict:
    inv = [1 / c for c in cotes]
    s = sum(inv)
    return {"H": round(inv[0] / s, 4), "D": round(inv[1] / s, 4), "A": round(inv[2] / s, 4), "marge": round(s - 1, 4)}


def _cotes(releves: list[dict] | None, at: datetime, kickoff: datetime) -> dict:
    """Relevés de cotes déclarés {collecte_le, H, D, A, source} : seuls ceux d'avant l'analyse et le coup d'envoi."""
    ok = sorted((r for r in releves or [] if parse_dt(r["collecte_le"]) < min(at, kickoff)),
                key=lambda r: parse_dt(r["collecte_le"]))
    if not ok:
        return {"statut": "a_verifier", "raison": "aucune cote datée fournie (data/ n'a que les cotes de clôture des matchs joués)"}
    premier, dernier = ok[0], ok[-1]
    p0, p1 = _implicites((premier["H"], premier["D"], premier["A"])), _implicites((dernier["H"], dernier["D"], dernier["A"]))
    return {"statut": "mesure", "releves": len(ok), "ouverture": {**p0, "collecte_le": premier["collecte_le"], "source": premier.get("source")},
            "dernier": {**p1, "collecte_le": dernier["collecte_le"], "source": dernier.get("source")},
            "evolution": {o: round(p1[o] - p0[o], 4) for o in "HDA"}}


def fiche(division: str, home: str, away: str, kickoff: str | datetime, *, at: str | datetime | None = None,
          history: list[Match] | None = None, dossier_externe: Path | None = None, cotes: list[dict] | None = None,
          absents_declares: dict[str, list[dict]] | None = None) -> dict:
    """Fiche WININVEST d'un match. ``history`` : matchs de la division (filtrés ici avant le jour du match).

    ``absents_declares`` : {équipe: [dicts Absent]} saisis à la main avec leur source, ajoutés aux absences collectées.
    """
    ko = parse_dt(kickoff)
    at = parse_dt(at or now_utc())
    if at >= ko:
        raise ValueError("analyse non antérieure au coup d'envoi : refusée")
    day = ko.date()
    history = [m for m in (history if history is not None else historique(division, day)) if m.day < day]
    if not history:
        raise ValueError(f"aucun match de {division} avant le {day}")
    fit = models.fit_maher(history, day, **V5)
    force = {t: fit.attack[t] / fit.defence[t] for t in fit.attack}
    equipes = (home, away)
    inconnues = [t for t in equipes if t not in fit.attack]
    rangs = _classement(history, day)
    h2h = [m for m in history if {m.home, m.away} == {home, away}][-5:]
    r: dict[str, dict] = {}
    formes = {t: _forme(history, t, force) for t in equipes}
    r["forme"] = {"statut": "partiel", "equipes": formes,
                  "limite": "championnat seulement : coupes et compétitions européennes absentes de data/"}
    r["confrontations"] = {"statut": "partiel" if h2h else "a_verifier",
                           "matchs": [{"date": m.day.isoformat(), "domicile": m.home, "exterieur": m.away,
                                       "score": f"{m.home_goals}-{m.away_goals}"} for m in h2h],
                           "evolution_tactique": "a_verifier : systèmes, entraîneurs et plans de jeu non mesurés"}
    r["force_adversaires"] = {"statut": "mesure", "modele": "poisson-v5 (attaque/défense, 1 = moyenne de la ligue)",
                              "force": {t: round(force.get(t, 1.0), 3) for t in equipes},
                              "adversaires_recents": {t: round(sum(x["force_adversaire"] for x in formes[t]["matchs"]) /
                                                              max(len(formes[t]["matchs"]), 1), 3) for t in equipes},
                              "equipes_sans_historique": inconnues}
    r["classement_enjeux"] = {"statut": "partiel", "saison": season_of(day),
                              "equipes": {t: _enjeu(rangs, t) for t in equipes},
                              "motivation": "a_verifier : objectifs, derby, match suivant, déclarations"}
    faits = {t: externe.faits(dossier_externe, t, ko.isoformat(), at.isoformat()) if dossier_externe else None for t in equipes}
    compos = {}
    for t in equipes:
        f = faits[t]
        tit = [l["joueur"] for l in (f["compo"] or f["compo_espn"]) if l.get("statut") == "titulaire"] if f else []
        compos[t] = {"confirmee": bool(tit), "titulaires": tit,
                     "source": ("api-football" if f and f["compo"] else "espn" if f and f["compo_espn"] else None)}
    r["compositions"] = {"statut": "mesure" if all(c["confirmee"] for c in compos.values()) else "a_verifier",
                         "equipes": compos, "probables": "a_verifier : aucune source de compos probables branchée"}
    abs_eq = {}
    for t in equipes:
        f = faits[t]
        decl = [{"joueur": l["joueur"], "statut": "absent" if l.get("type") == "Missing Fixture" else "incertain",
                 "source": "api-football"} for l in (f["absences"] if f else [])]
        for l in (f["fpl"] if f else []):
            statut_fpl = _statut_absence_fpl(l)
            if statut_fpl is not None:
                decl.append({"joueur": l["joueur"], "statut": statut_fpl, "source": "fpl"})
        decl += [{"joueur": d["joueur"], "statut": d.get("statut", "absent"), "source": ",".join(d.get("sources", ["declare"]))}
                 for d in (absents_declares or {}).get(t, [])]
        cons = absences.consolider(decl, set(compos[t]["titulaires"]))
        profils = (externe.profils_titularisation(dossier_externe, t, min(at, ko)) if dossier_externe
                   else {"matchs_lus": 0, "joueurs": {}})
        manuels = {d["joueur"]: d for d in (absents_declares or {}).get(t, [])}
        liste = []
        for a in cons["absents"]:
            p = profils["joueurs"].get(a["joueur"], {})
            m = manuels.get(a["joueur"], {})
            liste.append(absences.Absent(
                joueur=a["joueur"], poste=m.get("poste") or p.get("poste"), statut=a["statut"],
                part_minutes=m.get("part_minutes", p.get("part_titularisations")),
                part_offensive=m.get("part_offensive"), remplacant_niveau=m.get("remplacant_niveau"),
                sources=a["sources"]))
        abs_eq[t] = {**absences.evaluer_equipe(liste), "contradictions": cons["contradictions"],
                     "compos_lues_pour_profils": profils["matchs_lus"]}
    r["absences"] = {"statut": "mesure" if dossier_externe or absents_declares else "a_verifier", "equipes": abs_eq}
    r["fatigue"] = {"statut": "partiel", "equipes": {t: _fatigue(history, t, ko) for t in equipes},
                    "limite": "matchs de championnat seulement ; distance et voyages européens à vérifier"}
    r["cotes"] = _cotes(cotes, at, ko)
    dernier = max(m.day for m in history)
    alertes = []
    if (day - dernier).days > FRAICHEUR_MAX_JOURS:
        alertes.append(f"historique périmé : dernier match connu le {dernier}, {(day - dernier).days} jours avant le match")
        for k in ("forme", "classement_enjeux", "fatigue"):
            r[k]["statut"] = "perime"
    manquantes = [k for k, v in r.items() if v.get("statut") in ("a_verifier", "perime")]
    return {"version": VERSION, "division": division, "domicile": home, "exterieur": away,
            "coup_envoi": ko.isoformat(), "analyse_le": at.isoformat(),
            "historique": {"matchs": len(history), "dernier": dernier.isoformat()}, "alertes": alertes,
            "rubriques": r, "rubriques_a_verifier": manquantes, "ajustement_probabilites": False,
            "intensites_v5": dict(zip(("H", "A"), (round(x, 4) for x in fit.rates(home, away))))}
