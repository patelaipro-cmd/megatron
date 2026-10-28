# EXP-004 : tirs et tirs cadrés comme proxy des buts attendus

Statut : **protocole figé le 28/10/2026, avant toute exécution**. Les résultats sont ajoutés dans une section séparée, sans modifier le protocole.

## Hypothèse

Les buts sont rares et bruités. Les tirs et tirs cadrés d'un match passé mesurent mieux la qualité offensive et défensive réelle (idée des xG). Ajuster le modèle de Maher sur un mélange buts + tirs convertis devrait mieux estimer la force des équipes que les buts seuls, et réduire une partie de l'écart avec le bookmaker (~0,03 de log-loss, EXP-003).

## Données

- `data/matches_top5_2020-2026.csv`, régénéré par `scripts/extraire_donnees.py` depuis le même fichier source (SHA-256 `ef224cf2…4ba5c718c25cedd8937ffa174a74b86b5ba4221`, inchangé). Ajout de 4 colonnes : `HomeShots`, `AwayShots`, `HomeTarget`, `AwayTarget`. Les 11 colonnes existantes sont identiques ligne à ligne (vérifié). 11 053 matchs, aucune valeur de tir manquante.
- Seule vérification faite sur ces colonnes avant le protocole : leur présence et leur taux de remplissage. Aucun score calculé.

## Versions

- Référence : `poisson-v1` (demi-vie 90, rétrécissement 3, a priori « moyenne », sans Dixon-Coles).
- Candidate : `poisson-v4`. Mêmes réglages, mais chaque match d'historique compte pour l'équipe avec des « pseudo-buts » :
  `y = (1 − w) · buts + w · k · X`
  où `X` est le nombre de tirs cadrés (`cadres`) ou de tirs (`tirs`) de l'équipe, et `k` le taux de conversion de la ligue : somme pondérée des buts / somme pondérée de `X`, calculée à chaque ajustement sur le seul historique de cet ajustement, avec les mêmes poids temporels. `w = 0` redonne `poisson-v1`.
- Grille sur le développement : `X` ∈ {cadres, tirs} × `w` ∈ {0,25 ; 0,5 ; 0,75 ; 1}, plus `w = 0`. Demi-vie et rétrécissement ne sont pas réajustés.

## Anti-fuite temporelle

- Les tirs d'un match ne sont connus qu'après ce match. Ils n'entrent dans le modèle que par l'historique (`m.day < jour du match`, garde-fou `_check_past`), jamais pour le match prédit.
- `k` est recalculé sur l'historique de chaque ajustement : aucune moyenne de ligue calculée sur l'ensemble des données.
- Test unitaire : modifier les tirs des matchs du jour prédit ne change pas la prévision.

## Découpage

Identique à EXP-001 : Ligue 1, développement 2022/23, validation 2023/24, test 2024/25 et 2025/26. Réplication sur E0, D1, SP1 et I1, mêmes saisons, réglage choisi sur la Ligue 1.

## Critères de réussite fixés avant exécution

- **C1** : log-loss test Ligue 1 de `poisson-v4` < celle de `poisson-v1`.
- **C2** : RPS test Ligue 1 de `poisson-v4` ≤ celui de `poisson-v1`.
- **C3** : log-loss validation Ligue 1 de `poisson-v4` < celle de `poisson-v1`.
- **C4** : sur le test des 5 ligues réunies, la borne haute de l'intervalle à 95 % (bootstrap apparié, 2 000 tirages, graine 1) de l'écart de log-loss `poisson-v4` − `poisson-v1` est < 0.
- Information seulement : écart avec le bookmaker sur le test des 5 ligues, avant et après.

Si la meilleure combinaison du développement est `w = 0`, l'expérience conclut sans promotion.

## Décision prévue

- C1 à C4 tenus : `poisson-v4` devient le modèle par défaut de l'agent Stats.
- Sinon : `poisson-v1` reste en place ; l'option reste dans le code, désactivée.

## Retour arrière

Remettre `w = 0` dans `StatsAgent`.

## Limites connues avant exécution

- Tirs et tirs cadrés de Football-Data.co.uk : définition non documentée en détail, pas de distinction penalty / jeu, pas de position de tir. C'est un proxy grossier, pas un vrai xG.
- Un seul mélange linéaire testé ; pas de modèle séparé tirs → buts par équipe (finition).
