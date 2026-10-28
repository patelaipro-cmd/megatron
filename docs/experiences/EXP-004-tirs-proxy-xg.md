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

---

## Résultats (exécution du 28/10/2026, ajoutés après le protocole)

Commandes : `python -m megatron backtest --division F1 --half-lives 90 --shrinks 3 --proxys cadres:0,cadres:0.25,cadres:0.5,cadres:0.75,cadres:1,tirs:0.25,tirs:0.5,tirs:0.75,tirs:1 --reference 90,3,0 --sortie docs/experiences/EXP-004`, puis `--fixe 90,3,0,moyenne,cadres,0.25 --reference 90,3,0` pour chaque ligue de réplication, et `python -m megatron bootstrap docs/experiences/EXP-004/predictions.csv docs/experiences/EXP-004/replication-*/predictions.csv` pour C4.

Grille sur le développement (Ligue 1 2022/23, 380 matchs) :

| X | w | Log-loss | RPS |
|---|---|---|---|
| **cadres** | **0,25** | **0,97925** | 0,20059 |
| — (`poisson-v1`) | 0 | 0,97948 | 0,20091 |
| tirs | 0,25 | 0,98101 | 0,20109 |
| cadres | 0,5 | 0,98182 | 0,20116 |
| cadres | 0,75 | 0,98730 | 0,20273 |
| tirs | 0,5 | 0,98778 | 0,20297 |
| cadres | 1 | 0,99580 | 0,20542 |
| tirs | 0,75 | 1,00009 | 0,20686 |
| tirs | 1 | 1,01837 | 0,21302 |

Candidat retenu : `poisson-v4` = cadres, w = 0,25. Les tirs non cadrés et les poids forts dégradent : les buts gardent l'essentiel de l'information.

| Ligue 1 | `poisson-v4` | `poisson-v1` | Bookmaker | Écart v4 − v1 [IC 95 %] |
|---|---|---|---|---|
| Dev, log-loss | 0,97925 | 0,97948 | 0,97119 | −0,0002 [−0,0055 ; +0,0048] |
| Validation, log-loss | 1,04343 | 1,04884 | 1,01383 | −0,0054 [−0,0111 ; −0,0000] |
| Test, log-loss | 0,99003 | 0,99521 | 0,96613 | −0,0052 [−0,0093 ; −0,0011] |
| Test, RPS | 0,20883 | 0,21048 | 0,20115 | |

Réplication sur le test (log-loss v4 / v1, écart [IC 95 %]) :

| Ligue | v4 | v1 | Écart |
|---|---|---|---|
| Premier League | 1,0066 | 1,0109 | −0,0043 [−0,0077 ; −0,0010] |
| Bundesliga | 1,0075 | 1,0138 | −0,0063 [−0,0105 ; −0,0022] |
| Liga | 0,9839 | 0,9867 | −0,0028 [−0,0063 ; +0,0007] |
| Serie A | 0,9946 | 0,9978 | −0,0032 [−0,0072 ; +0,0003] |

Test des 5 ligues réunies (3 503 matchs) : écart −0,0042 [−0,0060 ; −0,0026].

Information :
- Écart avec le bookmaker sur le test des 5 ligues : +0,0291 [+0,0231 ; +0,0353] pour `poisson-v1`, +0,0249 [+0,0194 ; +0,0302] pour `poisson-v4`. Environ 15 % du retard comblé.
- Validation 2023/24 hors Ligue 1 (non prévue dans les critères) : Premier League 0,9449 / 0,9493 (mieux), Bundesliga 0,9732 / 0,9729, Liga 0,9828 / 0,9816, Serie A 0,9912 / 0,9903 (légèrement moins bien). 5 ligues réunies en validation : −0,0014 [−0,0039 ; +0,0010]. Le gain est net sur 2024-2026, pas sur 2023/24 hors France et Angleterre.

## Décision

- C1 tenu (0,99003 < 0,99521), C2 tenu (0,20883 ≤ 0,21048), C3 tenu (1,04343 < 1,04884), C4 tenu (borne haute −0,0026 < 0).
- **Promotion** : `poisson-v4` devient le modèle par défaut de l'agent Stats (`StatsAgent.PROXY_WEIGHT = 0.25`).

## Limites

- Gain modeste (−0,004 de log-loss) ; le bookmaker reste devant de ~0,025.
- Instable en validation hors Ligue 1 et Premier League : à surveiller dans les prochaines expériences.
- Un seul réglage de w choisi sur une saison de Ligue 1 ; w n'a pas été réajusté par ligue.
