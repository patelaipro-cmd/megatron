# EXP-013 : compositions et absences, sur l'historique 2013-2026

Statut : **protocole figé le 30/10/2026, avant toute exécution** (remplace le projet de protocole
du 29/10, qui attendait une saison de collecte en direct). Les résultats sont ajoutés dans une
section séparée, sans modifier le protocole.

## Question

La composition officielle (connue environ 1 h avant le coup d'envoi) contient-elle une information
absente du modèle statistique et, surtout, **absente des cotes** Bet365 de football-data (relevées
avant la publication des compositions) ? C'est le seul gain encore attendu après EXP-017 et EXP-018.

## Données

- Transfermarkt (dcaribou/transfermarkt-datasets, figé au 06/07/2026), branche `donnees-externes`
  `externe/transfermarkt/historique/` (workflow `transfermarkt-historique`, 30/10/2026) :
  `games`, `game_lineups` (titulaires), `appearances` (minutes), `player_valuations` (valeur datée).
- Matchs, résultats et cotes : `data/matches_top5_2000-2026.csv`. Liaison Transfermarkt → `data/`
  par ligue, date ± 1 jour et score, noms de clubs votés par saison (méthode de `megatron/xg.py`) ;
  un match non relié est exclu et compté.

## Indicateurs (seul le passé du match, plus sa composition)

Pour chaque équipe et chaque match, fenêtre = ses 10 derniers matchs de championnat reliés,
strictement avant le jour du match :

- **V** (valeur) : log((valeur des 11 titulaires du jour + 1) / (valeur moyenne des 11 titulaires
  de la fenêtre + 1)), valeur d'un joueur = dernière valorisation datée **avant** le jour du match
  (joueur sans valorisation : 0).
- **M** (habitués absents) : Σ sur les joueurs de la fenêtre de (minutes jouées / 900) pour ceux
  qui ne sont pas titulaires ce jour-là.
- Moins de 3 matchs dans la fenêtre ou composition incomplète (≠ 11 titulaires) : indicateurs à 0.

Variables du match : x₁ = V_dom − V_ext, x₂ = M_dom − M_ext.

## Modèles

Pour une base p (1X2) : p'_o ∝ p_o · exp(θ_o,1 · x₁ + θ_o,2 · x₂), θ_D = 0, soit 4 paramètres
appris par maximum de vraisemblance multinomiale sur le dev seulement.

- Base **S** : poisson-v5-cal (v5 270|2|0,35 prédit jour par jour sur le seul passé, puis
  `StatsAgent.CALIBRATION`).
- Base **K** : bookmaker (Bet365 de football-data, marge retirée), matchs avec cotes seulement.

## Périodes

Dev 2013/14-2018/19 ; validation 2019/20-2021/22 ; test 2022/23-2025/26.

## Critères, fixés avant exécution (log-loss 1X2, bootstrap apparié 2 000 tirages, graine 1)

- **A1** (modèle statistique) : S+compos − S, borne haute IC 95 % < 0 en validation **et** en test.
- **A2** (contre le marché, critère principal) : K+compos − K, borne haute IC 95 % < 0 en
  validation **et** en test, et écart moyen < 0 dans au moins 3 ligues sur 5 en test.
- Information : paramètres θ ; écart par ligue ; nombre de matchs reliés, exclus, sans composition.

## Décision prévue

- A2 tenu : les compositions deviennent un étage au-dessus du marché, **à confirmer en prospectif**
  (compositions collectées avant le coup d'envoi, EXP-021/EXP-014) avant tout usage ; aucun GO.
- A1 seul : amélioration du seul modèle statistique (pour les matchs sans cotes).
- Ni l'un ni l'autre : compositions descriptives seulement.
- Aucune probabilité de production modifiée par cette expérience, aucun appel LLM.

## Limites connues avant exécution

- Valeurs Transfermarkt = estimations communautaires, mises à jour par vagues.
- Cotes Bet365 relevées avant les compositions mais pas à la clôture : un éventuel gain contre ces
  cotes peut ne pas exister contre les cotes de clôture (non disponibles ici).
- Données Transfermarkt corrigées après coup possibles (compositions saisies a posteriori).
