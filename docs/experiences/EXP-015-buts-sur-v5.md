# EXP-015 : marchés 2+ / 3+ buts sur poisson-v5

Statut : **protocole figé le 30/10/2026, avant toute exécution**. Les résultats sont ajoutés dans une section séparée, sans modifier le protocole.

## Question

Les marchés de total de buts (2+ = au moins 2 buts, 3+ = plus de 2,5) utilisent encore un ajustement `poisson-v4` séparé, recalibré par Platt (EXP-007, `poisson-v4-platt`). Les taux de buts de `poisson-v5` (EXP-008), recalibrés de la même façon, font-ils mieux ? Ce sont des totaux de buts, pas des marges de victoire (EXP-012).

## Données

- Taux v5 : `docs/experiences/EXP-009/variables.csv` (`lam_fav`, `lam_adv`, seul le passé, 2008/09-2025/26). Total λ = lam_fav + lam_adv ; P(T ≥ s) sous Poisson.
- Référence : `poisson-v4` de `docs/experiences/EXP-007/<L>/predictions_buts.csv` (test 2020/21-2025/26) avec `marches.PLATT_V4` figés.
- Issues : scores de `data.CURRENT`, joints par `match_id` ; cotes plus/moins 2,5 : `data/cotes_buts_2000-2026.csv` (information).

## Méthode (identique à EXP-007)

Platt par marché, commun aux 5 ligues : p' = σ(a + b · logit p), p bornée dans [1e-6 ; 1 − 1e-6], maximum de vraisemblance. Apprentissage 2008/09-2019/20 (comme EXP-007). Test 2020/21-2025/26, matchs communs aux deux modèles.

## Critères fixés avant exécution (chaque marché, test, `poisson-v5-platt` − `poisson-v4-platt`)

- **B1** : 5 ligues réunies, borne haute IC 95 % (bootstrap apparié, 2 000 tirages, graine 1) de l'écart de log-loss < 0.
- **B2** : écart moyen < 0 dans au moins 4 ligues sur 5.
- **B3** : calibration : dans chaque tranche d'au moins 500 prévisions, |p moyenne − fréquence| ≤ 0,03 (critère M3 d'EXP-007).
- Information : écart avec le bookmaker (3+), a et b.

## Décision prévue

- B1-B3 tenus pour un marché : il passe sur `poisson-v5-platt` (un seul ajustement v5 dans l'agent Stats pour ce marché).
- Sinon : `poisson-v4-platt` reste pour ce marché.

## Limites connues avant exécution

- Même source ; test recoupant des saisons vues par EXP-007/008 (aucun réglage de ces marchés dessus).
- Taux v5 arrondis à 4 décimales dans `variables.csv`.
