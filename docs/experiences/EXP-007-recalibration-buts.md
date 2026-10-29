# EXP-007 : recalibration des marchés 2+ et 3+ buts

Statut : **protocole figé le 29/10/2026, avant toute exécution**. Les résultats sont ajoutés dans une section séparée, sans modifier le protocole.

## Question

EXP-006 : `poisson-v4` est trop tranché sur le total de buts (écarts de calibration jusqu'à 0,11). Une recalibration logistique, apprise sur le passé, rend-elle les marchés 2+ et 3+ meilleurs que les fréquences et calibrés, sur des saisons jamais utilisées pour l'apprendre ?

## Méthode (figée)

- Base : probabilités `poisson-v4` d'EXP-006, inchangées.
- Recalibration de Platt par marché, commune aux 5 ligues : p' = σ(a + b · logit(p)), a et b au maximum de vraisemblance (Newton, 50 itérations), p bornée dans [1e-6 ; 1 − 1e-6].
- Apprentissage : 2008/09 à 2019/20, 5 ligues (lignes d'EXP-006).
- Test : 2020/21 à 2025/26, 5 ligues. 2020/21 et 2021/22 n'ont été vus nulle part ; 2022/23 à 2025/26 n'ont servi qu'à l'information d'EXP-006 (aucun réglage). Prédictions `poisson-v4` recalculées pour ces 6 saisons dans `EXP-007/<L>`.
- Commandes : `python -m megatron marches --division <L> --saisons 2020/21,…,2025/26 --sortie docs/experiences/EXP-007/<L>` puis `python -m megatron marches-recalibrer --apprentissage docs/experiences/EXP-006/*/predictions_buts.csv --test docs/experiences/EXP-007/*/predictions_buts.csv --saisons-apprentissage 2008/09,…,2019/20 --sortie docs/experiences/EXP-007`.

## Critères fixés avant exécution (chaque marché séparément, sur le test)

Mêmes critères qu'EXP-006, appliqués à `poisson-v4-platt` contre `frequences` :

- **M1** : 5 ligues réunies, borne haute de l'IC 95 % de l'écart de log-loss < 0 (bootstrap apparié, 2 000 tirages, graine 1).
- **M2** : écart moyen < 0 dans au moins 4 ligues sur 5.
- **M3** : dans chaque tranche d'au moins 500 prévisions, |p moyenne − fréquence observée| ≤ 0,03.
- Information : écart avec `poisson-v4` brut, avec le bookmaker (3+), a et b appris.

## Décision prévue

- M1, M2 et M3 tenus : le marché est enregistré par `prevoir` sous la version `poisson-v4-platt` (a et b figés dans le code).
- Sinon : marché non enregistré ; le total de buts demande un autre modèle (dispersion propre), à traiter plus tard.

## Limites connues avant exécution

- Une seule recalibration commune aux 5 ligues : une ligue particulière peut rester mal calibrée.
- Le test (≈ 10 700 matchs) est plus petit que l'apprentissage ; les IC seront plus larges.
