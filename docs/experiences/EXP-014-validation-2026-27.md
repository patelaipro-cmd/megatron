# EXP-014 : les calibrations figées tiennent-elles sur la saison 2026/27, jamais vue ?

Statut : **protocole figé le 29/10/2026, avant toute exécution**. Exécution bloquée tant que
`scripts/preparer_entrainement.py` ne rend pas ADMISSIBLE pour ce candidat. Aucun paramètre n'est
réappris : c'est une validation hors échantillon, pas un entraînement.

## Question

Les coefficients appris sur des saisons passées et figés (1X2 `poisson-v5-cal`, EXP-010 ; niveaux
victoire / 2+ / 3+, EXP-012) restent-ils meilleurs que les fréquences et calibrés sur des matchs
qu'aucun réglage n'a vus ? La saison 2026/27 est le premier vrai échantillon neuf du projet.

## Données admissibles

- Matchs 2026/27 de `data.CURRENT` : xgabora jusqu'au 03/09, openfootball jusqu'au 20/09, puis
  seulement les résultats confirmés par deux familles (`complement_resultats_2026-27.csv`).
  Les matchs en quarantaine sont exclus et comptés.
- Intensités `poisson-v5` ajustées, pour chaque match, sur les seuls matchs des jours antérieurs.
- Seuil d'exécution : au moins 1 000 matchs 2026/27 confirmés, dans les 5 ligues (402 au 29/10/2026 ;
  à ~45 matchs par semaine, seuil attendu vers fin janvier 2027).

## Modèles comparés (aucun réajusté)

- **F** fréquences antérieures (même définition qu'EXP-012) ;
- **B** v5 brut ; **C** v5 avec les coefficients figés (`StatsAgent.CALIBRATION`, `syndicate.CALIBRATION_NIVEAUX`) ;
- information : cotes Bet365 de football-data quand présentes (marge retirée, 1X2 seulement).

## Critères fixés avant exécution (1X2 et chaque niveau)

- **V1** : borne haute de l'IC 95 % de log-loss C − F < 0 (bootstrap apparié par journée de
  championnat et ligue, 2 000 tirages, graine 1).
- **V2** : C − F < 0 dans au moins 4 ligues sur 5.
- **V3** : |fréquence observée − probabilité moyenne| ≤ 0,05 dans chaque tranche de 0,1 comptant
  au moins 100 matchs (seuil plus lâche qu'EXP-012 : effectifs plus petits).
- Information sans décision : C − B, C − Bet365, zone P(2+) ≥ 0,60.

## Décision prévue

- V1-V3 tenus : coefficients maintenus, statut confirmé « validé hors échantillon 2026/27 ».
- Un critère échoue : le statut du modèle concerné repasse à `EXPERIMENTAL_NON_CALIBRE` dans la
  fiche ; un nouveau protocole de recalibration (EXP-015) est écrit avant tout réapprentissage,
  avec 2026/27 comme période de test seulement si une saison suivante reste pour valider.
- Aucun GO automatique, quelle que soit l'issue : la zone GO exige en plus la cohorte prospective.
