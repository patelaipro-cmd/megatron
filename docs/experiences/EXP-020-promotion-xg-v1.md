# EXP-020 : xg-v1 à la place de poisson-v5-cal pour le 1X2 statistique

Statut : **protocole figé le 30/10/2026, avant toute exécution**. Les résultats sont ajoutés dans une
section séparée, sans modifier le protocole.

## Question

EXP-018 a montré, hors critères, que xg-v1 (filtre dynamique d'EXP-016 nourri par les xG Understat)
bat poisson-v5-cal sur 2018-2026 (−0,0017 [−0,0031 ; −0,0002]). Le marché reste la référence 1X2
quand il existe (EXP-017, EXP-018). Question : le 1X2 de `StatsAgent` (utilisé quand il n'y a pas de
cotes, et comme base des marchés de buts) doit-il passer de poisson-v5-cal à xg-v1 recalibré ?

## Candidat `xg-v1-cal` (rien n'est réglé sur validation ni test)

- Filtre `megatron/dynamique.py`, réglage figé d'EXP-016 (q = 0,0001, q_saison = 0, P0 = 0,05,
  c = 0,15, sans correction) et w = 0,5 figé par EXP-018 : observation (1 − w) · buts + w · xG ;
  buts seuls avant 2014/15 et pour un match sans xG.
- Recalibration multinomiale p' ∝ p^b · exp(c) (même forme qu'EXP-010), (b, c_H, c_D) appris sur le
  seul dev.
- Données : xG Understat de la branche `donnees-externes` (`externe/understat/historique/`, run
  40953408635), reliées à `data/` comme EXP-018 (`relier`).

## Référence

poisson-v5-cal de production : prévisions v5 d'EXP-008 (colonne `candidat`), recalibrées par
`StatsAgent.CALIBRATION`. Calibration apprise sur 2008-2016, donc hors des périodes ci-dessous.

## Périodes (celles d'EXP-018)

Chauffe 2000/01-2014/15 ; dev 2015/16-2017/18 (recalibration) ; validation 2018/19-2020/21 ;
test 2021/22-2025/26. Tous les matchs des deux modèles, avec ou sans cotes.

## Critères (xg-v1-cal − v5-cal, log-loss 1X2), fixés avant exécution

- **Z1** validation : borne haute IC 95 % (bootstrap apparié, 2 000 tirages, graine 1) < 0.
- **Z2** test : même borne < 0.
- **Z3** test : écart moyen < 0 dans au moins 4 ligues sur 5.
- **Z4** test : RPS xg-v1-cal ≤ RPS v5-cal.
- Information : xg-v1 brut − v5-cal ; paramètres (b, c) ; calibration par tranches ; écart au
  bookmaker sur les matchs avec cotes.

## Décision prévue

- Z1-Z4 tenus : xg-v1-cal devient le candidat 1X2 statistique. Bascule de `StatsAgent` dans une PR
  séparée, **seulement quand une collecte xG de la saison en cours existe** (le filtre doit voir les
  xG de tous les matchs passés jusqu'au jour prévu) ; marchés 2+/3+ réappris sur xg-v1 dans une
  expérience à part. À confirmer sur la cohorte prospective (EXP-014).
- Sinon : poisson-v5-cal reste.
- Aucune probabilité de production modifiée par cette expérience, aucun appel LLM, aucune mémoire
  réelle touchée.

## Limites connues avant exécution

- Validation et test déjà vus : EXP-018 a publié xg-v1 − v5-cal sur 2018-2026. Les critères ne
  prouvent donc qu'une robustesse, pas une découverte hors échantillon ; la vraie preuve reste
  2026/27 (EXP-014).
- Understat peut avoir révisé ses xG après coup.
- Dev court (3 saisons) pour la recalibration.
