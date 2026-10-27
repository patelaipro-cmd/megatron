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
