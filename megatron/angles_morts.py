"""Angles morts du favori : ce qui peut le faire perdre, concéder le nul ou gagner sans écart.

Cadre fixé par Luloki le 29/10/2026 : 13 angles morts, comparateur
ancien H2H → dernier H2H → situation actuelle sur 4 axes, et 3 questions par
match. Chaque scénario donne le fait observé, sa source et le mécanisme
sportif. Une incertitude seule ne modifie pas la probabilité : les
probabilités de ``poisson-v5`` sont rendues telles quelles, et un ajustement
n'est admis que s'il cite l'expérience qui l'a validé.

Seuls les matchs strictement antérieurs au jour prédit sont lus (garde-fou
``_check_past``). Les angles qui demandent des données absentes de ``data/``
(joueurs, compositions, tactique, coach) sont listés « à vérifier » avec la
source qu'il faudrait, jamais remplis par défaut.
"""

from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from .data import DATA, Match, season_of

DETAILS = DATA / "details_2000-2026.csv"
SOURCE_HISTORIQUE = "data/matches_top5_2000-2026.csv + data/details_2000-2026.csv (xgabora / Football-Data.co.uk)"

QUESTIONS = {
    "defaite": "Comment le favori peut-il perdre ?",
    "nul": "Comment l'adversaire peut-il obtenir le nul ?",
    "ecart": "Qu'est-ce qui peut empêcher une victoire par deux buts ou plus ?",
}
AXES = ("adaptation_adverse", "construction_ecart", "dependance_joueurs", "contexte")
TOUTES = ("defaite", "nul", "ecart")


@dataclass(frozen=True)
class Angle:
    cle: str
    nom: str
    a_verifier: str
    surprise: str
    questions: tuple[str, ...]
    mesure: str  # "historique", "partiel" ou "externe"
    avec_data: str  # ce que data/ permet de mesurer
    manque: str  # ce qu'il faut d'une autre source


ANGLES = (
    Angle("favori_surevalue", "Favori surévalué",
          "Victoires récentes contre des adversaires faibles ? Scores flatteurs malgré des occasions équilibrées ?",
          "Nul ou défaite", TOUTES, "partiel",
          "surperformance buts − k·tirs cadrés (pour et contre) sur 8 matchs ; force des adversaires affrontés",
          "occasions réelles (xG), contexte des victoires"),
    Angle("adversaire_progression", "Adversaire en progression",
          "Nouveau coach, retours importants, changement tactique, meilleures performances que ses derniers scores",
          "Rapport de force devenu différent", TOUTES, "partiel",
          "tendance de la différence de tirs cadrés (6 derniers matchs contre les précédents)",
          "changement de coach, retours de blessés, changement tactique"),
    Angle("adaptation_h2h", "Adaptation depuis le dernier H2H",
          "Comment l'adversaire a-t-il corrigé les faiblesses exploitées lors des précédents cartons ?",
          "Ancienne domination qui ne se répète plus", TOUTES, "partiel",
          "évolution de la différence de tirs cadrés de l'adversaire entre anciens H2H et dernier H2H",
          "corrections tactiques, effectifs des H2H"),
    Angle("style_gene", "Style qui gêne le favori",
          "Bloc bas difficile à ouvrir, pressing ciblé, transitions rapides, supériorité aérienne",
          "Possession sans occasions ; contre décisif", TOUTES, "externe",
          "aucune mesure fiable (corners et fautes ne décrivent pas un style)",
          "données d'événements : possession, PPDA, transitions, duels aériens"),
    Angle("dependance_joueur", "Dépendance à un joueur ou duo",
          "Qui crée, marque et organise ? Absence, méforme ou neutralisation possible ? Qualité du remplaçant ?",
          "Attaque moins dangereuse", TOUTES, "externe",
          "aucune (pas de données joueurs)",
          "buts et passes par joueur, absences, compositions"),
    Angle("fragilite_defensive", "Fragilité défensive masquée",
          "Espaces derrière les latéraux, défense lente, pertes dans l'axe, mauvais repli",
          "Défaite malgré une domination offensive", TOUTES, "partiel",
          "tirs cadrés concédés par le favori comparés à la moyenne de la ligue",
          "localisation des occasions concédées, vitesse de la défense"),
    Angle("rotation_fatigue", "Rotation et fatigue",
          "Minutes réellement jouées, déplacements, récupération, match important suivant, composition confirmée",
          "Intensité insuffisante", TOUTES, "partiel",
          "jours de repos depuis le dernier match de championnat (favori et adversaire)",
          "coupes et compétitions européennes, minutes jouées, composition confirmée"),
    Angle("enjeu_asymetrique", "Enjeu asymétrique",
          "Le favori doit-il absolument gagner ? Un nul lui suffit-il ? L'adversaire joue-t-il son maintien ou sa qualification ?",
          "Nul accepté ou adversaire plus engagé", TOUTES, "historique",
          "classement reconstitué : adversaire à 3 points ou moins de la zone de relégation, favori sans enjeu en fin de saison",
          "enjeux de coupe, objectifs déclarés"),
    Angle("favori_exterieur", "Favori à l'extérieur",
          "Rendement hors de ses bases, terrain, voyage, conditions locales",
          "Supériorité réduite", TOUTES, "historique",
          "points par match à domicile et à l'extérieur du favori sur 2 ans",
          "distance du voyage, terrain, météo"),
    Angle("coups_arretes", "Coups de pied arrêtés",
          "Faiblesses sur corners et coups francs, joueurs aériens adverses disponibles",
          "But encaissé sans domination adverse", TOUTES, "partiel",
          "corners obtenus par l'adversaire et concédés par le favori, comparés à la moyenne",
          "buts sur coups de pied arrêtés, joueurs aériens disponibles"),
    Angle("ecart_trompeur", "Construction de l'écart trompeuse",
          "Les anciens 4–0 ou 5–1 sont-ils venus après une expulsion, un penalty ou des buts très tardifs ?",
          "H2H large peu reproductible", ("ecart",), "partiel",
          "dans les H2H gagnés de 2 buts ou plus : carton rouge adverse, écart construit en 2e mi-temps",
          "minute des buts, penalties"),
    Angle("gestion_score", "Gestion après ouverture du score",
          "Le favori continue-t-il d'attaquer ou recule-t-il ? Concède-t-il souvent des égalisations ?",
          "Victoire courte ou nul", ("nul", "ecart"), "historique",
          "points perdus par le favori quand il mène à la pause, points pris par l'adversaire mené à la pause",
          "minute du premier but (seule la mi-temps est connue)"),
    Angle("informations_manquantes", "Informations manquantes",
          "Absences mal documentées, composition incertaine, changement récent peu couvert",
          "Confiance excessive", TOUTES, "partiel",
          "fraîcheur des données (dernier match connu), tirs manquants, équipe sans historique",
          "absences et compositions officielles"),
)
ANGLES_PAR_CLE = {a.cle: a for a in ANGLES}

MECANISMES = {
    "favori_surevalue": "ses résultats dépassent ce que ses tirs cadrés expliquent : la finition ou la chance se normalise",
    "adversaire_progression": "l'adversaire produit plus qu'avant : les résultats passés sous-estiment son niveau actuel",
    "adaptation_h2h": "l'adversaire a réduit l'écart de tirs cadrés lors du dernier H2H : l'ancienne domination se répète moins",
    "fragilite_defensive": "le favori concède plus d'occasions cadrées que la moyenne : un but encaissé reste probable même s'il domine",
    "rotation_fatigue": "le favori a moins récupéré que l'adversaire : intensité et pressing réduits",
    "enjeu_asymetrique": "l'adversaire joue son maintien, le favori moins : engagement inégal, nul accepté par l'un ou l'autre",
    "favori_exterieur": "le favori prend nettement moins de points hors de chez lui : sa supériorité se réduit",
    "coups_arretes": "l'adversaire obtient beaucoup de corners ou le favori en concède beaucoup : but possible sans domination",
    "ecart_trompeur": "l'écart du dernier H2H large s'est construit avec une expulsion ou en 2e mi-temps : peu reproductible",
    "gestion_score": "le favori lâche des points après avoir mené, ou l'adversaire revient souvent : victoire courte ou nul",
    "informations_manquantes": "les données récentes manquent : la confiance du modèle est surestimée",
}


@dataclass
class Scenario:
    """Un scénario de surprise : fait observé + source + mécanisme sportif."""

    angle: str
    question: str
    fait: str
    source: str
    mecanisme: str
    valeur: float | None = None  # indicateur chiffré, orienté : > 0 va dans le sens de la surprise
    ajustement: float = 0.0  # modification de probabilité ; 0 sauf expérience validée
    experience: str | None = None

    def __post_init__(self):
        angle = ANGLES_PAR_CLE.get(self.angle)
        if angle is None:
            raise ValueError(f"angle inconnu : {self.angle!r}")
        if self.question not in angle.questions:
            raise ValueError(f"l'angle {self.angle} ne répond pas à la question {self.question!r}")
        for nom in ("fait", "source", "mecanisme"):
            if not str(getattr(self, nom)).strip():
                raise ValueError(f"scénario sans {nom} : refusé")
        if self.ajustement and not self.experience:
            raise ValueError("ajustement de probabilité sans expérience validée : refusé")


def load_details(path: str | Path = DETAILS) -> dict[str, dict]:
    """match_id → mi-temps, cartons rouges, corners, fautes, handicap (valeurs absentes : None)."""
    out = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            key = f"{r['Division']}:{r['MatchDate']}:{r['HomeTeam']}-{r['AwayTeam']}"
            out[key] = {k: (float(v) if v else None) for k, v in r.items()
                        if k not in ("Division", "MatchDate", "HomeTeam", "AwayTeam")}
    return out


def _check_past(matches: list[Match], day: date) -> None:
    if matches and max(m.day for m in matches) >= day:
        raise AssertionError(f"fuite temporelle : historique non antérieur au {day}")


def _pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def probabilites_questions(lam_fav: float, lam_adv: float, max_goals: int = 10) -> dict[str, float]:
    """P(défaite du favori), P(nul), P(pas de victoire du favori par 2 buts ou plus), Poisson indépendant."""
    pf = [_pmf(k, lam_fav) for k in range(max_goals + 1)]
    pa = [_pmf(k, lam_adv) for k in range(max_goals + 1)]
    cells = [(i - j, pf[i] * pa[j]) for i in range(max_goals + 1) for j in range(max_goals + 1)]
    tot = sum(p for _, p in cells)
    return {"defaite": sum(p for d, p in cells if d < 0) / tot,
            "nul": sum(p for d, p in cells if d == 0) / tot,
            "ecart": sum(p for d, p in cells if d < 2) / tot}


def issues_questions(fav_goals: int, adv_goals: int) -> dict[str, bool]:
    d = fav_goals - adv_goals
    return {"defaite": d < 0, "nul": d == 0, "ecart": d < 2}


def _team_view(m: Match, team: str) -> tuple[int, int, int | None, int | None, bool]:
    """(buts pour, buts contre, cadrés pour, cadrés contre, à domicile) du point de vue de ``team``."""
    if m.home == team:
        return m.home_goals, m.away_goals, (m.shots[2] if m.shots else None), (m.shots[3] if m.shots else None), True
    return m.away_goals, m.home_goals, (m.shots[3] if m.shots else None), (m.shots[2] if m.shots else None), False


def _points(gf: int, ga: int) -> int:
    return 3 if gf > ga else 1 if gf == ga else 0


def _conversion(recent: list[Match]) -> float:
    goals = sum(m.home_goals + m.away_goals for m in recent if m.shots)
    sot = sum(m.shots[2] + m.shots[3] for m in recent if m.shots)
    return goals / sot if sot else 0.0


def _table(season_matches: list[Match]) -> dict[str, list[int]]:
    """équipe → [points, matchs joués]."""
    t: dict[str, list[int]] = {}
    for m in season_matches:
        for team in (m.home, m.away):
            gf, ga, *_ = _team_view(m, team)
            row = t.setdefault(team, [0, 0])
            row[0] += _points(gf, ga)
            row[1] += 1
    return t


def indicateurs(recent: list[Match], h2h: list[Match], details: dict[str, dict], fav: str, adv: str,
                fav_home: bool, day: date, strength: dict[str, float] | None = None) -> dict[str, dict]:
    """Indicateurs mesurables, orientés (valeur > 0 = dans le sens de la surprise).

    ``recent`` : matchs de la ligue des 730 derniers jours ; ``h2h`` : confrontations
    antérieures entre ``fav`` et ``adv`` ; ``strength`` : force attaque/défense de
    chaque équipe selon le modèle ajusté (calendrier du favori). Chaque entrée
    donne ``valeur``, ``fait`` et la plage de matchs lue.
    """
    _check_past(recent, day)
    _check_past(h2h, day)
    out: dict[str, dict] = {}
    k = _conversion(recent)
    by_team = {t: [m for m in recent if t in (m.home, m.away)] for t in (fav, adv)}
    teams = {t for m in recent for t in (m.home, m.away)}
    n_teams = max(len(teams), 1)

    def span(ms: list[Match]) -> str:
        return f"{len(ms)} matchs du {ms[0].day} au {ms[-1].day}" if ms else "aucun match"

    last8 = [m for m in by_team[fav][-8:] if m.shots]
    if len(last8) >= 4 and k:
        surperf = sum((gf - k * sf) + (k * sa - ga) for gf, ga, sf, sa, _ in (_team_view(m, fav) for m in last8)) / len(last8)
        fait = f"{fav} : {surperf:+.2f} but/match au-delà de ses tirs cadrés (pour et contre), conversion ligue {k:.3f}"
        if strength:
            opp = [strength.get(m.away if m.home == fav else m.home, 1.0) for m in last8]
            cal = 1 - sum(opp) / len(opp)
            fait += f" ; force moyenne des adversaires {1 - cal:.2f} (1 = moyenne)"
        else:
            cal = 0.0
        out["favori_surevalue"] = {"valeur": round(surperf + cal, 4), "surperformance": round(surperf, 4),
                                   "calendrier": round(cal, 4), "fait": fait, "lu": span(last8)}

    adv_ms = [m for m in by_team[adv] if m.shots]
    if len(adv_ms) >= 12:
        diff = [sf - sa for _, _, sf, sa, _ in (_team_view(m, adv) for m in adv_ms)]
        trend = sum(diff[-6:]) / 6 - sum(diff[:-6]) / len(diff[:-6])
        out["adversaire_progression"] = {
            "valeur": round(trend, 4),
            "fait": f"{adv} : différence de tirs cadrés {sum(diff[-6:]) / 6:+.2f}/match sur 6 matchs contre "
                    f"{sum(diff[:-6]) / len(diff[:-6]):+.2f} avant", "lu": span(adv_ms)}

    h2h_s = [m for m in h2h if m.shots]
    if len(h2h_s) >= 2:
        def adv_sot_diff(m):
            _, _, sf, sa, _ = _team_view(m, adv)
            return sf - sa
        old = sum(adv_sot_diff(m) for m in h2h_s[:-1]) / len(h2h_s[:-1])
        last = adv_sot_diff(h2h_s[-1])
        out["adaptation_h2h"] = {
            "valeur": round(last - old, 4),
            "fait": f"{adv} : différence de tirs cadrés {last:+d} au dernier H2H ({h2h_s[-1].day}) contre "
                    f"{old:+.2f} en moyenne sur {len(h2h_s) - 1} H2H plus anciens", "lu": span(h2h_s)}

    fav_s = [m for m in by_team[fav][-8:] if m.shots]
    league_sot = [m.shots[2] + m.shots[3] for m in recent if m.shots]
    if len(fav_s) >= 4 and league_sot:
        avg = sum(league_sot) / (2 * len(league_sot))
        conceded = sum(_team_view(m, fav)[3] for m in fav_s) / len(fav_s)
        out["fragilite_defensive"] = {
            "valeur": round(conceded / avg - 1, 4),
            "fait": f"{fav} concède {conceded:.2f} tirs cadrés/match, moyenne de la ligue {avg:.2f}", "lu": span(fav_s)}

    if by_team[fav] and by_team[adv]:
        rest_f = (day - by_team[fav][-1].day).days
        rest_a = (day - by_team[adv][-1].day).days
        out["rotation_fatigue"] = {
            "valeur": float(max(-7, min(7, rest_a - rest_f))),
            "fait": f"repos depuis le dernier match de championnat : {fav} {rest_f} j, {adv} {rest_a} j "
                    "(coupes non comprises)", "lu": f"derniers matchs {by_team[fav][-1].day} et {by_team[adv][-1].day}"}

        season = [m for m in recent if season_of(m.day) == season_of(day)]
        table = _table(season)
        if fav in table and adv in table and len(table) >= 10:
            rounds = 2 * (len(table) - 1)
            played = max(r[1] for r in table.values())
            ranked = sorted(table, key=lambda t: -table[t][0])
            relegation_line = table[ranked[len(ranked) - 3]][0]  # points de la 1re place reléguée (3 dernières)
            safe_line = table[ranked[len(ranked) - 4]][0]
            adv_lutte = played >= rounds / 2 and table[adv][0] - relegation_line <= 3
            remaining = 3 * (rounds - table[fav][1])
            fav_sans_enjeu = (played >= 0.75 * rounds and table[fav][0] - safe_line > remaining
                              and table[ranked[min(3, len(ranked) - 1)]][0] - table[fav][0] > remaining)
            out["enjeu_asymetrique"] = {
                "valeur": float(adv_lutte) + float(fav_sans_enjeu),
                "fait": f"classement reconstitué après {played}/{rounds} journées : {adv} {table[adv][0]} pts "
                        f"(zone de relégation à {relegation_line}), {fav} {table[fav][0]} pts"
                        + (" ; favori sans enjeu de classement" if fav_sans_enjeu else ""),
                "lu": span(season)}

    if not fav_home:
        home = [_points(gf, ga) for gf, ga, _, _, h in (_team_view(m, fav) for m in by_team[fav]) if h]
        away = [_points(gf, ga) for gf, ga, _, _, h in (_team_view(m, fav) for m in by_team[fav]) if not h]
        if len(home) >= 5 and len(away) >= 5:
            gap = sum(home) / len(home) - sum(away) / len(away)
            out["favori_exterieur"] = {
                "valeur": round(gap, 4),
                "fait": f"{fav} : {sum(home) / len(home):.2f} pt/match à domicile, {sum(away) / len(away):.2f} à l'extérieur",
                "lu": span(by_team[fav])}

    corners = [(details.get(m.match_id) or {}) for m in recent]
    tot = [d["HomeCorners"] + d["AwayCorners"] for d in corners if d.get("HomeCorners") is not None]
    if tot:
        avg_c = sum(tot) / (2 * len(tot))

        def corners_of(team, ms, pour):
            vals = []
            for m in ms[-8:]:
                d = details.get(m.match_id) or {}
                if d.get("HomeCorners") is None:
                    continue
                own, other = (d["HomeCorners"], d["AwayCorners"]) if m.home == team else (d["AwayCorners"], d["HomeCorners"])
                vals.append(own if pour else other)
            return sum(vals) / len(vals) if len(vals) >= 4 else None
        a_for, f_against = corners_of(adv, by_team[adv], True), corners_of(fav, by_team[fav], False)
        if a_for is not None and f_against is not None:
            out["coups_arretes"] = {
                "valeur": round(a_for / avg_c + f_against / avg_c - 2, 4),
                "fait": f"{adv} obtient {a_for:.1f} corners/match, {fav} en concède {f_against:.1f} (moyenne {avg_c:.1f})",
                "lu": "8 derniers matchs de chaque équipe"}

    big = [m for m in h2h if _team_view(m, fav)[0] - _team_view(m, fav)[1] >= 2]
    if big:
        m = big[-1]
        d = details.get(m.match_id) or {}
        gf, ga, _, _, at_home = _team_view(m, fav)
        flags = []
        red_adv = d.get("AwayRed" if at_home else "HomeRed")
        if red_adv:
            flags.append(f"{int(red_adv)} carton(s) rouge(s) pour {adv}")
        if d.get("HTHome") is not None:
            ht_f, ht_a = (d["HTHome"], d["HTAway"]) if at_home else (d["HTAway"], d["HTHome"])
            if ht_f - ht_a < 2:
                flags.append(f"écart construit en 2e mi-temps (mi-temps {int(ht_f)}-{int(ht_a)})")
        out["ecart_trompeur"] = {
            "valeur": float(len(flags)),
            "fait": f"dernier H2H large : {fav} {gf}-{ga} le {m.day}" + (" ; " + ", ".join(flags) if flags else ""),
            "lu": span(h2h)}

    def ht_rates(team, leading):
        res = []
        for m in by_team[team]:
            d = details.get(m.match_id) or {}
            if d.get("HTHome") is None:
                continue
            ht_t, ht_o = (d["HTHome"], d["HTAway"]) if m.home == team else (d["HTAway"], d["HTHome"])
            gf, ga, *_ = _team_view(m, team)
            if leading and ht_t > ht_o:
                res.append(3 - _points(gf, ga))  # points perdus
            if not leading and ht_t < ht_o:
                res.append(_points(gf, ga))  # points repris
        return res
    lost, back = ht_rates(fav, True), ht_rates(adv, False)
    if len(lost) >= 3 and len(back) >= 3:
        lg_lost, lg_back = [], []
        for m in recent:
            d = details.get(m.match_id) or {}
            if d.get("HTHome") is None or d["HTHome"] == d["HTAway"]:
                continue
            lead_home = d["HTHome"] > d["HTAway"]
            gl, gt = (m.home_goals, m.away_goals) if lead_home else (m.away_goals, m.home_goals)
            lg_lost.append(3 - _points(gl, gt))
            lg_back.append(_points(gt, gl))
        if lg_lost:
            v = (sum(lost) / len(lost) - sum(lg_lost) / len(lg_lost)) + (sum(back) / len(back) - sum(lg_back) / len(lg_back))
            out["gestion_score"] = {
                "valeur": round(v, 4),
                "fait": f"{fav} perd {sum(lost) / len(lost):.2f} pt quand il mène à la pause ({len(lost)} fois), "
                        f"{adv} reprend {sum(back) / len(back):.2f} pt quand il est mené ({len(back)} fois) ; "
                        f"ligue {sum(lg_lost) / len(lg_lost):.2f} et {sum(lg_back) / len(lg_back):.2f}",
                "lu": "730 derniers jours"}

    gaps = []
    for t in (fav, adv):
        if not by_team[t]:
            gaps.append(f"{t} sans historique")
        elif (day - by_team[t][-1].day).days > 21:
            gaps.append(f"{t} : dernier match connu le {by_team[t][-1].day}")
        elif not all(m.shots for m in by_team[t][-5:]):
            gaps.append(f"{t} : tirs manquants sur les 5 derniers matchs")
    out["informations_manquantes"] = {"valeur": float(len(gaps)),
                                      "fait": "; ".join(gaps) if gaps else "données récentes complètes",
                                      "lu": "historique de chaque équipe"}
    return out


def comparateur_h2h(h2h: list[Match], recent: list[Match], details: dict[str, dict], fav: str, adv: str,
                    day: date, ind: dict[str, dict]) -> dict:
    """Ancien H2H → dernier H2H → situation actuelle, sur les 4 axes."""
    _check_past(h2h, day)

    def bilan(ms):
        if not ms:
            return None
        res = [_team_view(m, fav) for m in ms]
        return {"matchs": len(ms), "du": str(ms[0].day), "au": str(ms[-1].day),
                "favori_v_n_d": [sum(gf > ga for gf, ga, *_ in res), sum(gf == ga for gf, ga, *_ in res),
                                 sum(gf < ga for gf, ga, *_ in res)],
                "ecart_buts_moyen": round(sum(gf - ga for gf, ga, *_ in res) / len(res), 2)}

    dernier = None
    if h2h:
        m = h2h[-1]
        d = details.get(m.match_id) or {}
        dernier = {"date": str(m.day), "score": f"{m.home} {m.home_goals}-{m.away_goals} {m.away}",
                   "mi_temps": (f"{int(d['HTHome'])}-{int(d['HTAway'])}" if d.get("HTHome") is not None else None),
                   "rouges": ([int(d["HomeRed"]), int(d["AwayRed"])] if d.get("HomeRed") is not None else None),
                   "tirs_cadres": [m.shots[2], m.shots[3]] if m.shots else None}
    actuel = {}
    for t in (fav, adv):
        ms = [m for m in recent if t in (m.home, m.away)][-6:]
        if ms:
            pts = [_points(*_team_view(m, t)[:2]) for m in ms]
            actuel[t] = {"points_par_match_6": round(sum(pts) / len(pts), 2), "dernier_match": str(ms[-1].day)}

    def axe(*cles):
        return [ind[c]["fait"] for c in cles if c in ind] or ["non mesurable avec data/"]
    return {
        "ancien_h2h": bilan(h2h[:-1]), "dernier_h2h": dernier, "situation_actuelle": actuel,
        "axes": {
            "adaptation_adverse": axe("adaptation_h2h", "adversaire_progression"),
            "construction_ecart": axe("ecart_trompeur"),
            "dependance_joueurs": ["non mesurable : aucune donnée joueur dans data/ ; source requise : "
                                   + ANGLES_PAR_CLE["dependance_joueur"].manque],
            "contexte": axe("enjeu_asymetrique", "rotation_fatigue", "favori_exterieur"),
        },
    }


def scenarios(ind: dict[str, dict]) -> list[Scenario]:
    """Un scénario par angle mesuré dont l'indicateur va dans le sens de la surprise (valeur > 0)."""
    out = []
    for cle, v in ind.items():
        if v["valeur"] <= 0 or cle not in MECANISMES:
            continue
        for q in ANGLES_PAR_CLE[cle].questions:
            out.append(Scenario(cle, q, v["fait"], f"{SOURCE_HISTORIQUE}, {v['lu']}", MECANISMES[cle], v["valeur"]))
    return out


def analyser(history: list[Match], details: dict[str, dict], home: str, away: str, day: date,
             lam_home: float, lam_away: float, version: str = "poisson-v5",
             strength: dict[str, float] | None = None) -> dict:
    """Analyse structurée d'un match : 3 questions, scénarios sourcés, comparateur H2H.

    Les probabilités viennent du modèle (``lam_home``, ``lam_away``) et ne sont pas
    modifiées. ``history`` : matchs de la division strictement antérieurs à ``day``.
    """
    _check_past(history, day)
    fav_home = lam_home >= lam_away
    fav, adv = (home, away) if fav_home else (away, home)
    probs = probabilites_questions(*((lam_home, lam_away) if fav_home else (lam_away, lam_home)))
    recent = [m for m in history if (day - m.day).days <= 730]
    h2h = [m for m in history if {m.home, m.away} == {fav, adv}]
    ind = indicateurs(recent, h2h, details, fav, adv, fav_home, day, strength)
    sc = scenarios(ind)
    externes = [{"angle": a.cle, "nom": a.nom, "a_verifier": a.a_verifier, "source_requise": a.manque}
                for a in ANGLES if a.mesure != "historique"]
    return {
        "favori": fav, "adversaire": adv, "favori_a_domicile": fav_home, "modele": version,
        "regle": "probabilités du modèle non modifiées : une incertitude seule ne justifie aucun ajustement",
        "questions": {q: {"question": texte, "probabilite": round(probs[q], 4),
                          "scenarios": [asdict(s) for s in sc if s.question == q]}
                      for q, texte in QUESTIONS.items()},
        "comparateur": comparateur_h2h(h2h, recent, details, fav, adv, day, ind),
        "indicateurs": ind,
        "a_verifier_hors_data": externes,
    }


def couverture() -> list[dict]:
    """Ce que data/ mesure et ce qui exige une autre source, angle par angle."""
    return [{"angle": a.nom, "mesure": a.mesure, "avec_data": a.avec_data, "manque": a.manque} for a in ANGLES]
