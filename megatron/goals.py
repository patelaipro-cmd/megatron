"""V2 GOALS: independent full-time totals screening, read-only and experimental."""
from __future__ import annotations

import math
from . import marches, models, wininvest
from .store import now_utc, parse_dt

VERSION = 'goals-v2-independent-1'
MARKETS = {'OVER_2_5': 3, 'OVER_3_5': 4, 'OVER_4_5': 5, 'UNDER_1_5': 2}


def probabilities(home_rate, away_rate):
    if any(not math.isfinite(x) or x < 0 for x in (home_rate, away_rate)):
        raise ValueError('Intensités invalides')
    calibrated = marches.probs_buts_calibrees(home_rate, away_rate)
    return {
        'OVER_2_5': (calibrated['3+']['oui'], marches.VERSION_BUTS),
        'OVER_3_5': (marches.total_au_moins(home_rate + away_rate, 4), 'poisson-v5-brut-experimental'),
        'OVER_4_5': (marches.total_au_moins(home_rate + away_rate, 5), 'poisson-v5-brut-experimental'),
        'UNDER_1_5': (calibrated['2+']['non'], marches.VERSION_BUTS),
    }


def evaluate(fixture, *, at=None, history=None, threshold=0.60):
    """Evaluate independently of V1; no favorite, margin or half-time input."""
    if not math.isfinite(threshold) or not 0.5 < threshold <= 1:
        raise ValueError('Seuil attendu dans ]0.5, 1]')
    instant = parse_dt(at or now_utc())
    kickoff = parse_dt(fixture['kickoff'])
    if kickoff.tzinfo is None or instant.tzinfo is None:
        raise ValueError('Fuseau horaire obligatoire')
    result = {'version': VERSION, 'match': {k: fixture[k] for k in ('division', 'home', 'away', 'kickoff')},
              'analyse_le': instant.isoformat(), 'markets': {}, 'candidates': [],
              'status': 'PASS', 'automatic_activation': False}
    if kickoff <= instant:
        return {**result, 'status': 'EXCLU_COMMENCE'}
    # Day-only histories cannot prove same-day availability. Use earlier dates only.
    cutoff = min(instant.date(), kickoff.date())
    source = history if history is not None else wininvest.historique(fixture['division'], cutoff)
    hist = sorted((m for m in source if m.division == fixture['division'] and m.day < cutoff), key=lambda m: m.day)
    recent = {t: [m for m in hist if t in (m.home, m.away)][-5:] for t in (fixture['home'], fixture['away'])}
    if any(len(ms) < 5 for ms in recent.values()):
        return {**result, 'status': 'DONNEES_INSUFFISANTES'}
    if any((cutoff - ms[-1].day).days > 30 for ms in recent.values()):
        return {**result, 'status': 'A_ACTUALISER'}
    fit = models.fit_maher(hist, cutoff, **wininvest.V5)
    rates = fit.rates(fixture['home'], fixture['away'])
    result['intensities'] = dict(zip(('home', 'away'), rates))
    result['data_cutoff'] = max(m.day for m in hist).isoformat()
    result['recent_totals'] = {t: [m.home_goals + m.away_goals for m in ms] for t, ms in recent.items()}
    result['h2h'] = [{'date': m.day.isoformat(), 'score': f'{m.home_goals}-{m.away_goals}'}
                     for m in hist if {m.home, m.away} == {fixture['home'], fixture['away']}][-3:][::-1]
    for market, (p, model) in probabilities(*rates).items():
        result['markets'][market] = {'probability': p, 'model': model}
        if p >= threshold:
            result['candidates'].append(market)
    result['status'] = 'WATCH' if result['candidates'] else 'PASS'
    result['limitations'] = ['Contexte, absences et compositions non vérifiés par cette commande',
                            'Calibration des zones de sélection à valider ; aucun GO automatique',
                            'Over 3.5 et 4.5 bruts expérimentaux, non calibrés']
    return result


def screen(fixtures, **kwargs):
    """Accept the full calendar, never the output of the V1 selector."""
    return {'version': VERSION, 'scope': 'calendrier fourni, couverture non garantie',
            'results': [evaluate(f, **kwargs) for f in fixtures]}
