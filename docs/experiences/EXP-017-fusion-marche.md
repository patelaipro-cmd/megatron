# EXP-017 : fusion poisson-v5-cal + marché contre le bookmaker seul

**Protocole figé le 29/10/2026 avant toute exécution.** Suite d'EXP-016 : le retard de v5-cal sur
le bookmaker (≈ 0,015 de log-loss en test) ne vient pas de la dynamique des forces. Question :
v5-cal apporte-t-il une information que les cotes n'ont pas ?

## Modèle `fus-v1` (pool log-linéaire, sans grille)

log p'_o = α · log v5cal_o + β · log book_o + c_o − log Z, avec c_A = 0, o ∈ {H, D, A}.
- v5cal : prévisions v5 d'EXP-008 recalibrées avec les coefficients EXP-010.
- book : 1/cote Bet365 (`OddHome/Draw/Away` de `data/`, football-data.co.uk), marge retirée
  proportionnellement (`models.bookmaker`).
- (α, β, c_H, c_D) estimés par maximum de vraisemblance (Newton) sur dev 2008/09-2015/16, matchs
  avec cotes. Prévisions v5 dev regénérées par `scripts/grille_multi.py` (config `270|2|0.35`), à
  l'identique d'EXP-008 (contrôle : log-loss dev v5 = 0,991185 sur 14 604 matchs).
- Un seul modèle, pas de choix de réglage : aucune sélection sur validation ni test.

## Périodes

Validation 2016/17-2019/20 ; test 2020/21-2025/26 ; matchs d'EXP-008 qui ont des cotes.

## Critères (fus-v1 − bookmaker), fixés avant exécution

- **M1** validation : borne haute IC 95 % (bootstrap apparié par match, 2 000 tirages, graine 1) < 0.
- **M2** test : même borne < 0.
- **M3** test : écart moyen < 0 dans au moins 4 ligues sur 5.
- **M4** test : RPS fus-v1 ≤ RPS bookmaker.
- Information : fus-v1 − v5-cal, poids α et β, calibration par tranches.

## Décision prévue

- M1-M4 tenus : v5 contient une information absente des cotes. `fus-v1` devient le candidat de
  référence 1X2 quand des cotes existent (PR séparée), à confirmer sur la cohorte prospective.
- Sinon : le marché est la référence 1X2 ; v5 n'ajoute rien de mesurable sur ce marché. Les
  étages suivants (xG EXP-018, contexte EXP-019) se jugent contre le bookmaker, pas contre v5.
- Aucun GO automatique, aucune probabilité de production modifiée par cette expérience.

## Limites connues avant exécution

- Cotes Bet365 relevées par football-data avant le match (vendredi ou mardi), pas les cotes de
  clôture : un marché plus tardif serait plus dur à battre.
- Test 2020-26 déjà vu par le projet.
- Une probabilité fusionnée qui ne bat pas le bookmaker n'a aucune valeur de pari.
