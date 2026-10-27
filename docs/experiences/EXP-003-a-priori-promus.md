# EXP-003 : a priori « équipe faible » pour les promus

Statut : **protocole figé le 27/10/2026, avant toute exécution**. Les résultats sont ajoutés dans une section séparée, sans modifier le protocole.

## Constat de départ (développement uniquement)

Dans `poisson-v1`, une équipe sans historique dans la division vaut une équipe moyenne. Sur le développement Ligue 1 2022/23 (promus : Toulouse, Ajaccio, Auxerre), avant le 20/10/2022, l'écart de log-loss avec le bookmaker est de +0,050 sur les 33 matchs impliquant un promu (1,0305 contre 0,9801). Il est de +0,008 sur l'ensemble du développement. Après cette date, sur 75 matchs, `poisson-v1` fait mieux que le bookmaker (0,8724 contre 0,8897). L'échantillon est petit.

## Versions

- Référence : `poisson-v1` (demi-vie 90, rétrécissement 3, a priori « moyenne »).
- Candidate : `poisson-v3`. Une équipe est « nouvelle » si elle n'a aucun match dans la division avant le 1er juillet de la saison en cours. Son rétrécissement tire vers un a priori au lieu de 1 :
  - `faibles3` : moyenne de l'attaque et de la défense des 3 équipes établies les plus faibles (rapport attaque/défense), recalculée à chaque itération de l'ajustement. Cet a priori sert aussi pour une équipe encore jamais vue.
- Grille sur le développement : a priori ∈ {moyenne, faibles3} × rétrécissement ∈ {3, 10}, demi-vie fixée à 90 jours, sans Dixon-Coles (EXP-002).

## Données et découpage

Identiques à EXP-001 : Ligue 1, développement 2022/23, validation 2023/24, test 2024/25 et 2025/26. Réplication sur E0, D1, SP1 et I1, mêmes saisons, réglages choisis sur la Ligue 1.

## Critères de réussite fixés avant exécution

- **C1** : log-loss test Ligue 1 de `poisson-v3` < celle de `poisson-v1`.
- **C2** : RPS test Ligue 1 de `poisson-v3` ≤ celui de `poisson-v1`.
- **C3** : log-loss validation Ligue 1 de `poisson-v3` < celle de `poisson-v1`.
- **C4** : sur le test des 5 ligues réunies, la borne haute de l'intervalle à 95 % (bootstrap apparié, 2 000 tirages, graine 1) de l'écart de log-loss `poisson-v3` − `poisson-v1` est < 0.
- Information seulement : mêmes mesures restreintes aux matchs impliquant un promu.

Si la meilleure combinaison du développement est `poisson-v1` (moyenne, 3), l'expérience conclut sans promotion.

## Décision prévue

- C1 à C4 tenus : `poisson-v3` est promu modèle par défaut de l'agent Stats.
- Sinon : `poisson-v1` reste en place.

## Retour arrière

Rétablir l'a priori « moyenne » et le rétrécissement 3 dans `StatsAgent`.

---

## Résultats (exécution du 27/10/2026, ajoutés après le protocole)

Commandes : `python -m megatron backtest --division F1 --half-lives 90 --shrinks 3,10 --a-priori moyenne,faibles3 --reference 90,3,0 --sortie docs/experiences/EXP-003`, puis `--fixe 90,3,0,faibles3 --reference 90,3,0` pour chaque ligue de réplication, et `python -m megatron bootstrap docs/experiences/EXP-003/predictions.csv docs/experiences/EXP-003/replication-*/predictions.csv` pour C4.

Grille sur le développement (Ligue 1 2022/23, 380 matchs) :

| A priori | Rétrécissement | Log-loss | RPS |
|---|---|---|---|
| **faibles3** | 3 | **0,97727** | 0,20027 |
| moyenne (`poisson-v1`) | 3 | 0,97948 | 0,20091 |
| faibles3 | 10 | 0,98624 | 0,20281 |
| moyenne | 10 | 0,99080 | 0,20428 |

Candidat retenu : `poisson-v3` = faibles3, rétrécissement 3.

| Ligue 1 | `poisson-v3` | `poisson-v1` | Écart v3 − v1 [IC 95 %] |
|---|---|---|---|
| Dev, log-loss | 0,97727 | 0,97948 | −0,0022 [−0,0076 ; +0,0030] |
| Validation, log-loss | 1,04914 | 1,04884 | +0,0003 [−0,0051 ; +0,0055] |
| Test, log-loss | 0,99577 | 0,99521 | +0,0006 [−0,0020 ; +0,0032] |
| Test, RPS | 0,21065 | 0,21048 | |

Réplication sur le test (log-loss v3 / v1) : Premier League 1,0124 / 1,0109 ; Bundesliga 1,0111 / 1,0138 ; Liga 0,9859 / 0,9867 ; Serie A 0,9970 / 0,9978.

Test des 5 ligues réunies (3 503 matchs) : écart −0,0004 [−0,0020 ; +0,0011].

Information : sur les 1 007 matchs de test impliquant un promu (5 ligues), log-loss 0,9820 (v3), 0,9836 (v1) et 0,9441 (bookmaker). L'écart avec le marché y est de +0,038, proche de l'écart global : les promus ne sont pas la principale source du retard.

## Décision

- C1 non tenu (0,99577 > 0,99521), C2 non tenu (0,21065 > 0,21048), C3 non tenu (1,04914 > 1,04884), C4 non tenu (borne haute +0,0011 ≥ 0).
- **Rejet** : `poisson-v1` reste en place. Le gain vu sur le développement ne se confirme ni en validation ni en test. Il venait probablement des trois promus de 2022/23.
- L'option `newcomer_prior` reste dans le code (désactivée par défaut) pour d'éventuelles expériences futures.

## Limites

- « Nouvelle » se juge sur la fenêtre de données (depuis 2020) : un club redescendu puis remonté dans la fenêtre garde son ancien historique.
- Un seul a priori testé (moyenne des 3 plus faibles) ; un a priori appris sur les promus passés n'a pas été essayé.
