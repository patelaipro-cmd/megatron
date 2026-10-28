"""Modèles de probabilités 1X2 ajustés uniquement sur le passé.

Chaque modèle reçoit l'historique et la date du match ; il refuse tout match
d'historique daté du jour du match ou après (garde-fou anti-fuite).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

from .agents import poisson_1x2
from .data import Match
from .ledger import OUTCOMES


def _check_past(history: list[Match], day: date) -> None:
    if history and max(m.day for m in history) >= day:
        raise AssertionError(f"fuite temporelle : historique non antérieur au {day}")


def frequencies(history: list[Match], day: date, lookback_days: int = 730) -> dict[str, float]:
    """Fréquences H/N/E observées sur la fenêtre passée (lissage de Laplace)."""
    _check_past(history, day)
    recent = [m for m in history if (day - m.day).days <= lookback_days]
    counts = {o: 1 for o in OUTCOMES}
    for m in recent:
        counts[m.result] += 1
    total = sum(counts.values())
    return {o: c / total for o, c in counts.items()}


def bookmaker(match: Match) -> dict[str, float] | None:
    """Probabilités implicites des cotes, marge retirée proportionnellement."""
    if not match.odds:
        return None
    inv = [1 / o for o in match.odds]
    s = sum(inv)
    return dict(zip(OUTCOMES, (x / s for x in inv)))


@dataclass
class MaherFit:
    mu: float
    home_adv: float
    attack: dict[str, float]
    defence: dict[str, float]
    rho: float = 0.0  # correction Dixon-Coles des petits scores (0 = Poisson indépendant)
    new_attack: float = 1.0  # valeurs d'une équipe jamais vue dans la division
    new_defence: float = 1.0

    def rates(self, home: str, away: str) -> tuple[float, float]:
        a, d = self.attack, self.defence
        lam_h = self.mu * self.home_adv * a.get(home, self.new_attack) * d.get(away, self.new_defence)
        lam_a = self.mu * a.get(away, self.new_attack) * d.get(home, self.new_defence)
        return lam_h, lam_a


def fit_maher(history: list[Match], day: date, *, half_life: float, shrink: float,
              dixon_coles: bool = False, newcomer_prior: str = "moyenne",
              proxy: str = "cadres", proxy_weight: float = 0.0,
              max_age_days: int = 1095, iterations: int = 40) -> MaherFit:
    """Modèle de Maher (attaque × défense × terrain), pondéré dans le temps.

    ``shrink`` ajoute ce nombre de matchs fictifs à chaque équipe, ce qui la
    ramène vers son a priori quand elle est peu observée. L'a priori vaut 1
    (équipe moyenne), sauf avec ``newcomer_prior="faibles3"`` pour une équipe
    sans match dans la division avant le 1er juillet de la saison en cours :
    elle est alors tirée vers la moyenne des 3 équipes établies les plus faibles.

    Avec ``proxy_weight = w > 0`` (EXP-004), chaque équipe compte des pseudo-buts
    ``(1 − w) · buts + w · k · X``, X = tirs cadrés (``proxy="cadres"``) ou tirs
    (``"tirs"``), k = buts / X pondérés sur ce seul historique. Un match sans tirs
    connus garde ses buts.
    """
    if newcomer_prior not in ("moyenne", "faibles3"):
        raise ValueError(f"a priori inconnu : {newcomer_prior!r}")
    if proxy not in PROXIES:
        raise ValueError(f"proxy inconnu : {proxy!r}")
    if dixon_coles and proxy_weight > 0:
        raise ValueError("Dixon-Coles exige des buts entiers : incompatible avec les pseudo-buts")
    _check_past(history, day)
    rows = []
    for m in history:
        age = (day - m.day).days
        if age <= max_age_days:
            rows.append((m.home, m.away, m.home_goals, m.away_goals, 0.5 ** (age / half_life)))
    if proxy_weight > 0:
        rows = _pseudo_goals(rows, [m for m in history if (day - m.day).days <= max_age_days],
                             PROXIES[proxy], proxy_weight)
    if not rows:
        return MaherFit(1.3, 1.2, {}, {})
    teams = {t for r in rows for t in r[:2]}
    att = dict.fromkeys(teams, 1.0)
    dfn = dict.fromkeys(teams, 1.0)
    w_tot = sum(r[4] for r in rows)
    mu = sum(w * (hg + ag) for _, _, hg, ag, w in rows) / (2 * w_tot)
    gamma = 1.2
    season_start = date(day.year if day.month >= 7 else day.year - 1, 7, 1)
    newcomers = set()
    if newcomer_prior == "faibles3":
        seen_before = {t for m in history if m.day < season_start for t in (m.home, m.away)}
        newcomers = teams - seen_before
    established = sorted(teams - newcomers)
    a0 = d0 = 1.0
    for _ in range(iterations):
        if newcomers and len(established) >= 3:
            weakest = sorted(established, key=lambda t: att[t] / dfn[t])[:3]
            a0 = sum(att[t] for t in weakest) / 3
            d0 = sum(dfn[t] for t in weakest) / 3
        prior_a = {t: a0 if t in newcomers else 1.0 for t in teams}
        prior_d = {t: d0 if t in newcomers else 1.0 for t in teams}
        g_for = dict.fromkeys(teams, 0.0)
        e_for = dict.fromkeys(teams, 0.0)
        for h, a, hg, ag, w in rows:
            g_for[h] += w * hg
            e_for[h] += w * mu * gamma * dfn[a]
            g_for[a] += w * ag
            e_for[a] += w * mu * dfn[h]
        att = {t: (g_for[t] + shrink * mu * prior_a[t]) / (e_for[t] + shrink * mu) for t in teams}
        g_ag = dict.fromkeys(teams, 0.0)
        e_ag = dict.fromkeys(teams, 0.0)
        for h, a, hg, ag, w in rows:
            g_ag[a] += w * hg
            e_ag[a] += w * mu * gamma * att[h]
            g_ag[h] += w * ag
            e_ag[h] += w * mu * att[a]
        dfn = {t: (g_ag[t] + shrink * mu * prior_d[t]) / (e_ag[t] + shrink * mu) for t in teams}
        ma = sum(att.values()) / len(teams)
        md = sum(dfn.values()) / len(teams)
        att = {t: v / ma for t, v in att.items()}
        dfn = {t: v / md for t, v in dfn.items()}
        gamma = (sum(w * hg for _, _, hg, _, w in rows)
                 / sum(w * mu * att[h] * dfn[a] for h, a, _, _, w in rows))
        mu = (sum(w * (hg + ag) for _, _, hg, ag, w in rows)
              / sum(w * (gamma * att[h] * dfn[a] + att[a] * dfn[h]) for h, a, _, _, w in rows))
    fit = MaherFit(mu, gamma, att, dfn)
    if newcomer_prior == "faibles3" and len(established) >= 3:
        weakest = sorted(established, key=lambda t: att[t] / dfn[t])[:3]
        fit.new_attack = sum(att[t] for t in weakest) / 3
        fit.new_defence = sum(dfn[t] for t in weakest) / 3
    if dixon_coles:
        fit.rho = estimate_rho(fit, rows)
    return fit


PROXIES = {"tirs": (0, 1), "cadres": (2, 3)}  # positions dans Match.shots (domicile, extérieur)


def _pseudo_goals(rows: list[tuple], matches: list[Match], idx: tuple[int, int], w: float) -> list[tuple]:
    num = den = 0.0
    for (_, _, hg, ag, wt), m in zip(rows, matches):
        if m.shots:
            num += wt * (hg + ag)
            den += wt * (m.shots[idx[0]] + m.shots[idx[1]])
    if den <= 0:
        return rows
    k = num / den
    out = []
    for (h, a, hg, ag, wt), m in zip(rows, matches):
        if m.shots:
            hg = (1 - w) * hg + w * k * m.shots[idx[0]]
            ag = (1 - w) * ag + w * k * m.shots[idx[1]]
        out.append((h, a, hg, ag, wt))
    return out


RHO_GRID = [round(-0.25 + 0.01 * i, 2) for i in range(36)]  # -0,25 à 0,10


def _tau(hg: int, ag: int, lam_h: float, lam_a: float, rho: float) -> float:
    if hg == 0 and ag == 0:
        return 1 - lam_h * lam_a * rho
    if hg == 0 and ag == 1:
        return 1 + lam_h * rho
    if hg == 1 and ag == 0:
        return 1 + lam_a * rho
    if hg == 1 and ag == 1:
        return 1 - rho
    return 1.0


def estimate_rho(fit: MaherFit, rows: list[tuple]) -> float:
    """ρ maximisant la vraisemblance pondérée des petits scores, taux de buts fixés."""
    low = [(fit.rates(h, a), hg, ag, w) for h, a, hg, ag, w in rows if hg <= 1 and ag <= 1]
    best, best_ll = 0.0, -math.inf
    for rho in RHO_GRID:
        ll = 0.0
        for (lh, la), hg, ag, w in low:
            t = _tau(hg, ag, lh, la, rho)
            if t <= 0:
                ll = -math.inf
                break
            ll += w * math.log(t)
        if ll > best_ll:
            best, best_ll = rho, ll
    return best


def dixon_coles_1x2(lam_home: float, lam_away: float, rho: float, max_goals: int = 10) -> dict[str, float]:
    def pmf(k, lam):
        return math.exp(-lam) * lam ** k / math.factorial(k)
    ph = [pmf(k, lam_home) for k in range(max_goals + 1)]
    pa = [pmf(k, lam_away) for k in range(max_goals + 1)]
    out = {"H": 0.0, "D": 0.0, "A": 0.0}
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = max(_tau(i, j, lam_home, lam_away, rho), 0.0) * ph[i] * pa[j]
            out["H" if i > j else "D" if i == j else "A"] += p
    total = sum(out.values())
    return {o: v / total for o, v in out.items()}


def predict_1x2(fit: MaherFit, match: Match) -> dict[str, float]:
    if fit.rho:
        return dixon_coles_1x2(*fit.rates(match.home, match.away), fit.rho)
    return poisson_1x2(*fit.rates(match.home, match.away))
