"""Forces d'équipes dynamiques (EXP-016) : filtre d'état de Poisson, mis à jour après chaque match.

Chaque équipe a une log-attaque a et une log-défense d gaussiennes N(m, P) ; chaque ligue un
intercept μ et un avantage du terrain h. λ_dom = exp(μ + h + a_dom + d_ext), λ_ext = exp(μ + a_ext + d_dom).
Entre deux matchs, la variance d'une équipe croît de q par jour, et de q_saison au 1er juillet.
Après un match, mise à jour de Laplace (Kalman étendu, lien log) sur les pseudo-buts
(1 − w) · buts + w · k · tirs cadrés, k = buts / tirs cadrés de la ligue sur le seul passé.
Covariances croisées ignorées (approximation diagonale). Une prévision n'utilise que les états
d'avant le jour du match : `Filtre.prevoir` ne lit rien de ce jour-là.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

from .data import Match

GRILLE = 10  # buts 0..10 par équipe, comme poisson_1x2


@dataclass(frozen=True)
class Reglage:
    q: float = 0.0005          # dérive par jour d'une force d'équipe
    q_saison: float = 0.01     # dérive supplémentaire au 1er juillet
    p0: float = 0.15           # variance d'une équipe nouvelle dans la ligue
    w: float = 0.35            # poids des tirs cadrés dans les pseudo-buts
    c: float = 0.15            # handicap a priori d'une équipe nouvelle (a = −c, d = +c)
    correction: bool = False   # λ = exp(m + P/2) au lieu de exp(m)
    q_ligue: float = 0.00002   # dérive par jour de μ et h
    demi_vie_k: float = 730.0  # oubli du rapport buts / tirs cadrés (jours)

    @property
    def nom(self) -> str:
        return f"q{self.q}|qs{self.q_saison}|p0{self.p0}|w{self.w}|c{self.c}|cor{int(self.correction)}"


@dataclass
class _Etat:
    m: float
    p: float
    jour: date


@dataclass
class Filtre:
    reglage: Reglage = field(default_factory=Reglage)
    equipes: dict = field(default_factory=dict)  # (ligue, équipe, "a"|"d") -> _Etat
    ligues: dict = field(default_factory=dict)   # (ligue, "mu"|"h") -> _Etat
    tirs: dict = field(default_factory=dict)     # ligue -> [buts pondérés, cadrés pondérés, jour]

    # --- états -------------------------------------------------------------
    def _deriver(self, e: _Etat, jour: date, q: float, saison: float) -> _Etat:
        if jour > e.jour:
            juillets = sum(1 for an in range(e.jour.year, jour.year + 1)
                           if e.jour < date(an, 7, 1) <= jour)
            e = _Etat(e.m, min(e.p + q * (jour - e.jour).days + saison * juillets, 2.0), jour)
        return e

    def _equipe(self, ligue: str, equipe: str, cote: str, jour: date) -> _Etat:
        r = self.reglage
        cle = (ligue, equipe, cote)
        e = self.equipes.get(cle)
        if e is None:  # relatif à la moyenne des équipes de la ligue vues dans l'année, sinon c s'annule
            vus = [x.m for (lg, _, cc), x in self.equipes.items() if lg == ligue and cc == cote
                   and (jour - x.jour).days <= 365]
            moy = sum(vus) / len(vus) if vus else 0.0
            return _Etat(moy - r.c if cote == "a" else moy + r.c, r.p0, jour)
        return self._deriver(e, jour, r.q, r.q_saison)

    def _ligue(self, ligue: str, cle: str, jour: date) -> _Etat:
        e = self.ligues.get((ligue, cle))
        if e is None:
            return _Etat(math.log(1.35) if cle == "mu" else math.log(1.25), 0.05, jour)
        return self._deriver(e, jour, self.reglage.q_ligue, 0.0)

    # --- prévision ---------------------------------------------------------
    def intensites(self, ligue: str, dom: str, ext: str, jour: date) -> tuple[float, float]:
        mu, h = self._ligue(ligue, "mu", jour), self._ligue(ligue, "h", jour)
        ad, dd = self._equipe(ligue, dom, "a", jour), self._equipe(ligue, dom, "d", jour)
        ae, de = self._equipe(ligue, ext, "a", jour), self._equipe(ligue, ext, "d", jour)
        eh, ee = mu.m + h.m + ad.m + de.m, mu.m + ae.m + dd.m
        if self.reglage.correction:
            eh += (mu.p + h.p + ad.p + de.p) / 2
            ee += (mu.p + ae.p + dd.p) / 2
        return math.exp(eh), math.exp(ee)

    def prevoir(self, m: Match) -> dict[str, float]:
        return issues(*self.intensites(m.division, m.home, m.away, m.day))

    # --- mise à jour -------------------------------------------------------
    def _k(self, ligue: str, jour: date) -> float | None:
        t = self.tirs.get(ligue)
        if not t or t[1] <= 0:
            return None
        f = 0.5 ** ((jour - t[2]).days / self.reglage.demi_vie_k)
        return (t[0] * f) / (t[1] * f)

    def _observer(self, cles: list[tuple], etats: list[_Etat], y: float) -> None:
        eta = sum(e.m for e in etats)
        s = sum(e.p for e in etats)
        lam = math.exp(min(eta, 3.0))
        gain = (y - lam) / (1 + s * lam)
        for cle, e in zip(cles, etats):
            p = e.p - e.p * e.p * lam / (1 + s * lam)
            nouveau = _Etat(e.m + e.p * gain, max(p, 1e-6), e.jour)
            (self.ligues if len(cle) == 2 else self.equipes)[cle] = nouveau

    def mettre_a_jour(self, m: Match, xg: tuple[float, float] | None = None, mode_xg: bool = False) -> None:
        """mode_xg (EXP-018) : observation (1 − w) · buts + w · xG ; sans xG, buts seuls."""
        r, lg, j = self.reglage, m.division, m.day
        yh, ya = float(m.home_goals), float(m.away_goals)
        k = self._k(lg, j)
        if mode_xg:
            if xg is not None and r.w > 0:
                yh, ya = (1 - r.w) * yh + r.w * xg[0], (1 - r.w) * ya + r.w * xg[1]
        elif r.w > 0 and m.shots and k is not None:
            yh = (1 - r.w) * yh + r.w * k * m.shots[2]
            ya = (1 - r.w) * ya + r.w * k * m.shots[3]
        # domicile : μ, h, a_dom, d_ext
        cles = [(lg, "mu"), (lg, "h"), (lg, m.home, "a"), (lg, m.away, "d")]
        etats = [self._ligue(lg, "mu", j), self._ligue(lg, "h", j), self._equipe(lg, m.home, "a", j),
                 self._equipe(lg, m.away, "d", j)]
        self._observer(cles, etats, yh)
        # extérieur : μ, a_ext, d_dom (μ relu après la première mise à jour)
        cles = [(lg, "mu"), (lg, m.away, "a"), (lg, m.home, "d")]
        etats = [self._ligue(lg, "mu", j), self._equipe(lg, m.away, "a", j), self._equipe(lg, m.home, "d", j)]
        self._observer(cles, etats, ya)
        if m.shots and m.shots[2] + m.shots[3] > 0:
            t = self.tirs.get(lg)
            f = 0.5 ** ((j - t[2]).days / r.demi_vie_k) if t else 0.0
            self.tirs[lg] = [(t[0] * f if t else 0.0) + m.home_goals + m.away_goals,
                             (t[1] * f if t else 0.0) + m.shots[2] + m.shots[3], j]


def issues(lh: float, la: float, n: int = GRILLE) -> dict[str, float]:
    ph = [math.exp(-lh)]
    pa = [math.exp(-la)]
    for i in range(1, n + 1):
        ph.append(ph[-1] * lh / i)
        pa.append(pa[-1] * la / i)
    ca = [0.0]  # cumul des probabilités extérieures : P(buts ext < i)
    for v in pa:
        ca.append(ca[-1] + v)
    h = sum(ph[i] * ca[i] for i in range(n + 1))
    d = sum(ph[i] * pa[i] for i in range(n + 1))
    a = sum(ph[i] * (ca[n + 1] - ca[i + 1]) for i in range(n + 1))
    t = h + d + a
    return {"H": h / t, "D": d / t, "A": a / t}


def derouler(matchs: list[Match], reglage: Reglage, garder=lambda m: True,
             xg: dict[str, tuple[float, float]] | None = None) -> dict[str, tuple]:
    """Parcourt les matchs dans l'ordre ; prévoit chaque jour avant de mettre à jour avec ce jour.

    Renvoie {match_id: (1X2, λ_dom, λ_ext)} pour les matchs retenus par ``garder``.
    ``xg`` ({match_id: (xG dom, xG ext)}) active le mode xG d'EXP-018 à la place des tirs cadrés.
    """
    f = Filtre(reglage)
    out: dict[str, tuple] = {}
    par_jour: dict[date, list[Match]] = {}
    for m in matchs:
        par_jour.setdefault(m.day, []).append(m)
    for jour in sorted(par_jour):
        du_jour = par_jour[jour]
        for m in du_jour:
            if garder(m):
                lh, la = f.intensites(m.division, m.home, m.away, m.day)
                out[m.match_id] = (issues(lh, la), lh, la)
        for m in du_jour:
            f.mettre_a_jour(m, None if xg is None else xg.get(m.match_id), mode_xg=xg is not None)
    return out
