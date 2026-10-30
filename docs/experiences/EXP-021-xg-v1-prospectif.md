# EXP-021 : xg-v1-cal contre poisson-v5-cal sur la cohorte prospective 2026/27

Statut : **protocole figé le 30/10/2026, avant le premier enregistrement prospectif de xg-v1-cal**
(PR #56). Aucune prévision de la cohorte n'a été lue.

## Question

EXP-020 : xg-v1-cal bat poisson-v5-cal en test (−0,0032) mais pas significativement en validation.
Sur des matchs prévus **avant leur coup d'envoi**, sans aucun réglage après coup, le gain tient-il ?

## Cohorte

- Matchs de `memoire/` (registre réel) ayant, au moment `initial`, à la fois
  `pred:<match>:poisson-v5-cal` et `pred:<match>:xg-v1-cal`, tous deux enregistrés avant le coup
  d'envoi (heure d'enregistrement et heure du commit poussé), et un résultat saisi par le registre
  (confirmé par deux familles). Les autres matchs sont exclus et comptés par motif.
- Les paramètres restent ceux du 30/10/2026 (`megatron/xg.py`, `StatsAgent.CALIBRATION`). Tout
  changement de l'un ou l'autre modèle en cours de saison arrête la cohorte à la veille du changement.

## Lecture

- **Une seule lecture**, au 1er juin 2027 (fin de saison des 5 ligues). Avant : seuls les effectifs
  (matchs, motifs d'exclusion) peuvent être consultés, jamais les scores.
- Puissance : d'après EXP-020 (écart-type d'un écart par match ≈ 0,087), environ 1 300 matchs
  attendus d'ici juin donnent un IC 95 % de ± 0,0047 : un gain de l'ordre de −0,003 ne sera
  probablement pas établi en une saison. La règle ci-dessous en tient compte.

## Critères (log-loss 1X2, xg-v1-cal − poisson-v5-cal), fixés avant lecture

- **P1** : borne haute IC 95 % < 0 (bootstrap apparié, 2 000 tirages, graine 1).
- **P2** : écart moyen < 0 dans au moins 3 ligues sur 5.
- **P3** : RPS xg-v1-cal ≤ RPS poisson-v5-cal.
- Information : écart de chacun au bookmaker sur les matchs avec cotes ; calibration par tranches.

## Décision prévue

- P1-P3 tenus : xg-v1-cal devient le 1X2 statistique de `StatsAgent` (PR séparée, marchés 2+/3+
  réappris dans une expérience à part).
- P1 non tenu mais écart moyen < 0 : observation prolongée sur 2027/28, cohortes cumulées, nouvelle
  lecture unique au 1er juin 2028 avec les mêmes critères.
- Écart moyen ≥ 0 : xg-v1-cal est abandonné, l'enregistrement en observation s'arrête.
- Aucun GO automatique ; aucune probabilité de fusion modifiée par cette expérience.

## Limites connues

- Les xG Understat d'un match peuvent être révisés après sa collecte : le registre utilise ceux
  disponibles avant l'enregistrement, ce qui est la condition réelle d'usage.
- Le registre ne couvre que les matchs vus par le calendrier ESPN entre 300 et 35 min avant le coup
  d'envoi (fréquence réelle des lancements GitHub) : la cohorte n'est pas toute la saison.
