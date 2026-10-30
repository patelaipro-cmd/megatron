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

## Résultats (exécution du 30/10/2026)

`python scripts/grille_multi.py --saisons 2013/14,…,2025/26 --configs "v5=270,2,0,moyenne,cadres,0.35" --sortie docs/experiences/EXP-013/v5 --processus 4`
(`predictions.csv` non versionnés, régénérables), puis
`python scripts/exp013_compos.py --tm <externe/transfermarkt/historique> --v5 docs/experiences/EXP-013/v5 --sortie docs/experiences/EXP-013`
(détail : `docs/experiences/EXP-013/resultats.json`).

Liaison : 25 241 matchs Transfermarkt, 25 204 reliés (33 non reliés, 4 scores différents) ;
2 245 matchs à indicateurs 0 (fenêtre < 3 ou XI incomplet). Matchs évalués : dev 10 954,
validation 5 376, test 7 048.

θ (ordre H·x₁, H·x₂, A·x₁, A·x₂) : S [0,272 ; −0,037 ; −0,363 ; −0,013] ;
K [0,155 ; −0,034 ; −0,245 ; −0,017]. Signes attendus : un XI plus cher que d'habitude
favorise l'équipe ; l'effet des habitués absents est faible.

| écart log-loss | validation | test |
|---|---|---|
| S+compos − S | −0,00196 [−0,00370 ; −0,00017] | −0,00097 [−0,00235 ; +0,00050] |
| K+compos − K | −0,00104 [−0,00215 ; +0,00009] | −0,00010 [−0,00104 ; +0,00087] |

K par ligue en test : E0 −0,0019 ; SP1 +0,0010 ; I1 +0,0014 ; D1 −0,0009 ; F1 −0,0004 (3/5 < 0).

**A1 non tenu** (validation oui, test non). **A2 non tenu** (IC traversant 0 en validation et en
test). Décision prévue : compositions **descriptives seulement**.

Lecture (corrigée le 30/10/2026 à la relecture de Luloki) : l'expérience **n'établit pas de gain
prédictif exploitable** ; elle ne prouve pas que le marché contient déjà l'information des
compositions. Contre les cotes, l'écart moyen est négatif dans 3 ligues sur 5 en test mais les IC
traversent 0 en validation et en test. Explications possibles non départagées : information déjà
dans les cotes, valeur Transfermarkt trop grossière.

Limite d'interprétation : 2 245 des 25 204 matchs reliés (≈ 9 %) ont des indicateurs nuls (fenêtre
< 3 matchs ou XI incomplet). Cela ne change pas le verdict préenregistré ; un protocole futur
devrait mesurer la couverture des compositions et analyser séparément les matchs couverts, cette
analyse étant fixée à l'avance. Aucune probabilité de production modifiée.
