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
