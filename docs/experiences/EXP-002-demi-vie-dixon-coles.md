# EXP-002 : pondération plus courte et correction Dixon-Coles

Statut : **protocole figé le 27/10/2026, avant toute exécution**. Les résultats sont ajoutés dans une section séparée, sans modifier le protocole.

## Versions

- Référence : `poisson-v1` (EXP-001), demi-vie 90 jours, rétrécissement 3, sans correction.
- Candidate : `poisson-v2`, meilleure combinaison sur le développement parmi :
  - demi-vie ∈ {30, 45, 60, 90} jours ;
  - rétrécissement ∈ {1, 3, 10} ;
  - correction Dixon-Coles ∈ {non, oui}. Avec correction, ρ est estimé à chaque date par maximum de vraisemblance pondérée sur l'historique, les taux de buts étant fixés par le modèle de Maher (estimation en deux temps), sur une grille ρ ∈ [−0,25 ; 0,10] au pas de 0,01.

## Hypothèses

1. EXP-001 a retenu la borne basse de sa grille (90 jours) : une demi-vie plus courte pourrait mieux suivre la forme.
2. La correction Dixon-Coles améliore la probabilité des nuls et des petits scores.

## Données et découpage

Identiques à EXP-001 : `data/matches_top5_2020-2026.csv`, buts des matchs strictement antérieurs uniquement. Ligue 1 : développement 2022/23, validation 2023/24, test 2024/25 et 2025/26. Réplication sur les mêmes saisons pour E0, D1, SP1 et I1 avec les réglages choisis sur la Ligue 1.

## Critères de réussite fixés avant exécution

- **C1** : log-loss test Ligue 1 de `poisson-v2` < celle de `poisson-v1`.
- **C2** : RPS test Ligue 1 de `poisson-v2` ≤ celui de `poisson-v1`.
- **C3** : log-loss validation Ligue 1 de `poisson-v2` < celle de `poisson-v1`.
- **C4** : sur le test des 5 ligues réunies, la borne haute de l'intervalle à 95 % (bootstrap apparié, 2 000 tirages, graine 1) de l'écart de log-loss `poisson-v2` − `poisson-v1` est < 0.

Si la meilleure combinaison du développement est exactement `poisson-v1`, l'expérience conclut sans promotion.

## Décision prévue

- C1 à C4 tenus : `poisson-v2` est promu modèle par défaut de l'agent Stats.
- Sinon : `poisson-v1` reste en place, le diagnostic est consigné.

## Retour arrière

Rétablir les réglages `poisson-v1` dans `StatsAgent` (demi-vie 90, rétrécissement 3, sans correction).
