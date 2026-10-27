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

---

## Résultats (exécution du 27/10/2026, ajoutés après le protocole)

Commande : `python -m megatron backtest --division F1 --half-lives 30,45,60,90 --shrinks 1,3,10 --dixon-coles 0,1 --reference 90,3,0 --sortie docs/experiences/EXP-002`. Détails dans `EXP-002/resultats.json` ; les prévisions ne sont pas recopiées, car elles sont identiques à celles d'EXP-001.

La meilleure combinaison des 24 testées sur le développement est **exactement `poisson-v1`** (demi-vie 90, rétrécissement 3, sans correction ; log-loss 0,97948). Les suivantes :

| Demi-vie | Rétrécissement | Dixon-Coles | Log-loss dev | RPS dev |
|---|---|---|---|---|
| 90 | 3 | non | **0,97948** | 0,20091 |
| 90 | 1 | non | 0,98036 | 0,20114 |
| 90 | 3 | oui | 0,98092 | 0,20105 |
| 60 | 3 | non | 0,98135 | 0,20135 |
| 60 | 1 | non | 0,98194 | 0,20140 |

Les demi-vies de 30 et 45 jours font moins bien. La correction Dixon-Coles dégrade légèrement chaque configuration. Le ρ estimé reste pourtant dans la fourchette habituelle (entre −0,12 et −0,06 sur quatre dates du développement).

## Décision

- Conformément au protocole, l'expérience conclut **sans promotion** : `poisson-v1` reste le modèle de l'agent Stats.
- Les critères C1 à C4 ne sont pas évalués, puisqu'aucun candidat distinct ne sort du développement. Aucune variante n'a été essayée sur le test.
- Hypothèse 1 rejetée sur le développement : une demi-vie plus courte que 90 jours n'aide pas.
- Hypothèse 2 rejetée sur le développement : la correction des petits scores n'améliore pas l'issue 1X2 sur la Ligue 1 2022/23. Elle pourrait servir pour les marchés de score exact ou de moins de 2,5 buts, ce qui n'a pas été testé.

## Limites

- Un seul championnat et une seule saison pour le choix : un écart de 0,0015 de log-loss est inférieur au bruit attendu sur 380 matchs.
- ρ est estimé en deux temps (taux fixés), pas conjointement.
