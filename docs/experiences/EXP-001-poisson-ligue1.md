# EXP-001 : modèle Poisson de référence, Ligue 1

Statut : **protocole figé le 27/10/2026, avant toute exécution**. Les résultats sont ajoutés dans une section séparée, sans modifier le protocole.

## Versions

- Référence : `stats-v0`, agent Stats de la v0.1 (Poisson sur des xG fournis à la main, jamais évalué).
- Candidate : `poisson-v1`, modèle de Maher (attaque, défense, avantage du terrain) ajusté uniquement sur les matchs joués avant la date du match prédit, avec pondération temporelle et rétrécissement vers la moyenne.
- Points de comparaison : `frequences` (fréquences H/N/E observées avant le match, même ligue) et `bookmaker` (cotes Bet365 avant match, marge retirée proportionnellement).

## Hypothèse

`poisson-v1` prédit mieux l'issue 1X2 que les simples fréquences historiques. On s'attend à ce qu'il reste moins bon que le marché.

## Données

- `data/matches_top5_2020-2026.csv`, extrait de xgabora/Club-Football-Match-Data (voir `data/SOURCE.md`).
- Seules colonnes utilisées pour prédire : date, équipes, buts des matchs **antérieurs**. Les cotes servent uniquement de point de comparaison. Elo, forme et clusters du jeu de données ne sont pas utilisés (leur calcul pourrait inclure des informations postérieures, non vérifié).

## Découpage chronologique (saisons du 1er juillet au 30 juin)

| Rôle | Ligue 1 |
|---|---|
| Historique seul (jamais évalué) | 2020/21, 2021/22 |
| Développement : choix des hyperparamètres | 2022/23 |
| Validation : contrôle sans réglage | 2023/24 |
| Test : évalué une seule fois, après figement | 2024/25 et 2025/26 |

Chaque prédiction n'utilise que les matchs de dates strictement antérieures (garde-fou vérifié par assertion dans le code).

Grille d'hyperparamètres (choix par log-loss sur le développement uniquement) : demi-vie de la pondération ∈ {90, 180, 365, 730} jours ; force du rétrécissement ∈ {1, 3, 10} matchs fictifs.

## Critères de réussite fixés avant exécution

- **C1** : log-loss de `poisson-v1` sur le test < log-loss de `frequences`.
- **C2** : RPS (ranked probability score) de `poisson-v1` sur le test < RPS de `frequences`.
- **C3** : la validation ne contredit pas le développement (`poisson-v1` meilleur que `frequences` en log-loss aussi en validation).
- Information, pas critère : écart avec `bookmaker`, Brier, calibration.
- Réplication, information seulement : mêmes hyperparamètres, mêmes saisons de test, sur Premier League, Bundesliga, Liga et Serie A.

## Décision prévue

- C1, C2 et C3 tenus : `poisson-v1` est promu modèle de référence de l'agent Stats.
- Sinon : rejet, `stats-v0` reste en place et le diagnostic est consigné.

## Retour arrière

La promotion se limite à la version par défaut du modèle utilisée par l'agent Stats ; revenir en arrière consiste à rétablir `stats-v0` (fonction `poisson_1x2` sur xG fournis), qui reste disponible.

---

## Résultats (exécution du 27/10/2026, ajoutés après le protocole)

Commande : `python -m megatron backtest --division F1 --sortie docs/experiences/EXP-001`. Détails : `EXP-001/resultats.json`, prévisions match par match : `EXP-001/predictions.csv`.

Hyperparamètres choisis sur le développement : demi-vie **90 jours**, rétrécissement **3**. 90 jours est la borne basse de la grille : une demi-vie plus courte pourrait faire mieux, ce sera à tester dans une prochaine expérience, pas en modifiant celle-ci.

Ligue 1, matchs où les trois modèles ont une prévision (plus bas = meilleur) :

| Période | n | Log-loss Poisson | Log-loss fréquences | Log-loss bookmaker | RPS Poisson | RPS fréquences | RPS bookmaker |
|---|---|---|---|---|---|---|---|
| Dev 2022/23 | 380 | 0,9795 | 1,0749 | 0,9712 | 0,2009 | 0,2335 | 0,1984 |
| Validation 2023/24 | 306 | 1,0488 | 1,0891 | 1,0138 | 0,2184 | 0,2328 | 0,2063 |
| **Test 2024/25 + 2025/26** | 611 | **0,9952** | 1,0605 | 0,9661 | **0,2105** | 0,2330 | 0,2012 |

Sur le test (bootstrap apparié, 2 000 tirages, intervalle à 95 %), l'écart de log-loss de Poisson est de −0,065 [−0,094 ; −0,036] contre les fréquences, et de +0,029 [+0,015 ; +0,044] contre le bookmaker.  Calcul ponctuel (graine 1) à partir de `predictions.csv`, pas encore intégré à la ligne de commande.

Calibration sur le test (toutes issues confondues) :

| Tranche prédite | n | p moyenne | Fréquence observée |
|---|---|---|---|
| 0,0-0,2 | 311 | 0,155 | 0,183 |
| 0,2-0,4 | 991 | 0,275 | 0,266 |
| 0,4-0,6 | 373 | 0,490 | 0,512 |
| 0,6-0,8 | 147 | 0,668 | 0,612 |
| 0,8-1,0 | 11 | 0,848 | 0,818 |

Le modèle est un peu trop sûr de lui sur les gros favoris (0,6-0,8) et sous-estime les outsiders (0,0-0,2).

Réplication sur les mêmes saisons de test, mêmes hyperparamètres (log-loss Poisson / fréquences / bookmaker) :

| Ligue | n | Poisson | Fréquences | Bookmaker |
|---|---|---|---|---|
| Premier League | 760 | 1,0109 | 1,0833 | 0,9946 |
| Bundesliga | 612 | 1,0138 | 1,0838 | 0,9700 |
| Liga | 760 | 0,9867 | 1,0618 | 0,9584 |
| Serie A | 760 | 0,9978 | 1,0900 | 0,9670 |

## Décision

- C1 tenu (0,9952 < 1,0605), C2 tenu (0,2105 < 0,2330), C3 tenu (validation 1,0488 < 1,0891).
- **`poisson-v1` est promu** modèle par défaut de l'agent Stats. `stats-v0` reste disponible en repli (tâche avec `xg_home` et `xg_away`).
- Le marché reste nettement meilleur. Rien dans cette expérience ne justifie de parier contre les cotes.

## Limites

- Équipes promues traitées comme des équipes moyennes (pas de données de deuxième division dans l'extrait).
- Ni absences, ni calendrier, ni enjeu, ni xG : seuls les buts passés sont utilisés.
- Cotes Bet365 à un instant non précisé avant le match (pas forcément la cote de clôture).
- Heures de coup d'envoi non vérifiées ; le garde-fou anti-fuite travaille à la journée (historique strictement antérieur à la date du match).
