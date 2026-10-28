# EXP-005 : revalidation de poisson-v4 sur 2008-2020

Statut : **protocole figé le 28/10/2026, avant toute exécution**. Les résultats sont ajoutés dans une section séparée, sans modifier le protocole.

## Question

`poisson-v4` (EXP-004 : pseudo-buts 0,75 · buts + 0,25 · k · tirs cadrés) a été choisi et testé sur 2022-2026. En validation 2023/24, le gain n'apparaissait qu'en Ligue 1 et en Premier League. Le gain tient-il sur une autre époque, jamais vue lors du choix ?

## Données

- `data/matches_top5_2000-2026.csv` (`--donnees complet`), ajouté par la PR #10. Les saisons 2008/09 à 2019/20 n'ont servi à aucun réglage.
- Saisons évaluées : 2008/09 à 2019/20 (12 saisons, 5 ligues, environ 21 600 matchs). Saison du 1er juillet au 30 juin : les matchs de juillet 2020 (fin de saison retardée par la COVID) tombent dans 2020/21 et sont hors champ.
- Tirs cadrés complets à partir de 2006/07 : l'historique de chaque ajustement (3 ans au plus) en contient dès 2008/09 ; un match sans tirs garde ses buts.

## Versions comparées (aucun réglage)

- Référence : `poisson-v1` (demi-vie 90, rétrécissement 3, a priori moyenne, sans Dixon-Coles).
- Candidate : `poisson-v4` (mêmes réglages, proxy cadres, w = 0,25).
- Pas de recherche sur grille : les deux sont figés. Commande par ligue :
  `python -m megatron backtest --donnees complet --division <L> --fixe 90,3,0,moyenne,cadres,0.25 --reference 90,3,0 --dev 2008/09,2009/10,2010/11,2011/12 --val 2012/13,2013/14,2014/15,2015/16 --test 2016/17,2017/18,2018/19,2019/20 --sortie docs/experiences/EXP-005/<L>`
  (le découpage dev / validation / test ne sert ici qu'à l'affichage ; les critères portent sur les 12 saisons).

## Critères fixés avant exécution

- **R1** : sur les 12 saisons et les 5 ligues réunies, borne haute de l'IC 95 % (bootstrap apparié, 2 000 tirages, graine 1) de l'écart de log-loss v4 − v1 < 0.
- **R2** : écart moyen de log-loss v4 − v1 < 0 dans au moins 4 ligues sur 5 (12 saisons chacune).
- **R3** : écart moyen de log-loss v4 − v1 < 0 dans au moins 8 saisons sur 12 (5 ligues réunies).
- Information : RPS, écart avec le bookmaker, détail par ligue et par saison.

## Décision prévue

- R1, R2 et R3 tenus : `poisson-v4` est confirmé.
- R1 tenu mais R2 ou R3 non : confirmé avec réserve (gain réel en moyenne, pas uniforme), noté dans les limites.
- R1 non tenu : `poisson-v4` est remis en cause ; retour à `poisson-v1` à décider dans une expérience suivante, avec les données 2008-2026 réunies.

## Limites connues avant exécution

- Même source (Football-Data.co.uk via xgabora) que EXP-004 : ce n'est pas une validation sur une autre source.
- Le football 2008-2020 diffère (rythme, tirs) : un échec peut venir d'un changement d'époque autant que d'un surajustement.

---

## Résultats (exécution du 28/10/2026, ajoutés après le protocole)

Commandes : celle du protocole pour F1, E0, D1, SP1, I1, puis `python -m megatron bootstrap docs/experiences/EXP-005/*/predictions.csv --saisons 2008/09,…,2019/20` (5 ligues réunies, par ligue, par saison).

5 ligues, 12 saisons (21 586 matchs avec cotes) :

| | `poisson-v4` | `poisson-v1` | Bookmaker |
|---|---|---|---|
| Log-loss | 0,98979 | 0,99369 | 0,96991 |
| RPS | 0,20156 | 0,20285 | 0,19564 |

**R1** : écart v4 − v1 = −0,0039 [−0,0046 ; −0,0032] sur 21 590 matchs.

**R2** (par ligue, écart [IC 95 %]) :

| Ligue | Écart |
|---|---|
| Ligue 1 | −0,0040 [−0,0056 ; −0,0025] |
| Premier League | −0,0043 [−0,0060 ; −0,0026] |
| Bundesliga | −0,0048 [−0,0066 ; −0,0031] |
| Liga | −0,0030 [−0,0048 ; −0,0013] |
| Serie A | −0,0036 [−0,0052 ; −0,0020] |

**R3** (par saison, 5 ligues) : écart négatif dans les 12 saisons, de −0,0071 (2010/11) à −0,0016 (2016/17). IC 95 % sous 0 sauf 2016/17 [−0,0043 ; +0,0012] et 2019/20 [−0,0050 ; +0,0002].

Information : écart avec le bookmaker +0,0238 [+0,0213 ; +0,0265] pour v1, +0,0199 [+0,0176 ; +0,0222] pour v4 (environ 16 % du retard comblé, comme dans EXP-004).

## Décision

- R1 tenu (borne haute −0,0032 < 0), R2 tenu (5 ligues sur 5), R3 tenu (12 saisons sur 12).
- **`poisson-v4` confirmé** sur une époque jamais vue lors de son choix. Le doute de la validation 2023/24 (EXP-004) ne se retrouve pas sur 2008-2020.

## Limites

- Même source de données que EXP-004.
- Le gain reste petit (−0,004) ; le bookmaker garde ~0,02 d'avance.
