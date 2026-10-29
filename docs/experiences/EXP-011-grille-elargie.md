# EXP-011 : grille élargie au-delà du bord d'EXP-008

Statut : **protocole figé le 29/10/2026, avant toute exécution**. Les résultats sont ajoutés dans une section séparée, sans modifier le protocole.

## Question

L'optimum d'EXP-008 (demi-vie 270, rétrécissement 2, w 0,35) est au bord de la grille. Une demi-vie plus longue ou un poids des tirs cadrés plus fort fait-il mieux, une fois recalibré comme `poisson-v5-cal` (EXP-010) ?

## Grille (développement 2008/09-2015/16, 5 ligues réunies)

Proxy cadres, a priori moyenne, sans Dixon-Coles, historique max 1 095 jours (inchangé) :
demi-vie ∈ {270, 365, 540, 730} × rétrécissement ∈ {1, 2, 3} × w ∈ {0,35 ; 0,45 ; 0,55 ; 0,7} = 48 combinaisons, dont v5.

Candidat = log-loss brute minimale sur le développement. Si c'est v5 (270, 2, 0,35) : pas de promotion.

Commandes : `python scripts/grille_multi.py --saisons <dev> --grille 270,365,540,730:1,2,3:0.35,0.45,0.55,0.7 --sortie docs/experiences/EXP-011/dev`, puis `--configs candidat=…;reference=270,2,0,moyenne,cadres,0.35` sur validation et test.

## Comparaison

Candidat et v5 sont chacun recalibrés sur le développement par la méthode d'EXP-010 (p' ∝ p^b · exp(c), 3 paramètres), puis comparés recalibrés.

## Critères fixés avant exécution (candidat-cal − v5-cal)

- **V1** : validation, borne haute IC 95 % (bootstrap apparié, 2 000 tirages, graine 1) < 0.
- **T1** : test 2020-2026, même borne < 0.
- **T2** : test, écart moyen < 0 dans au moins 4 ligues sur 5.
- **T3** : test, RPS candidat-cal ≤ RPS v5-cal.

## Décision prévue

Tous tenus : le candidat recalibré remplace `poisson-v5-cal` (nouvelle version `poisson-v6-cal`). Sinon `poisson-v5-cal` reste.

## Limites connues avant exécution

- Historique plafonné à 3 ans : une demi-vie de 730 j y pèse peu différemment de 540 j.
- Même source ; test recoupant des saisons déjà vues.

---

## Résultats (exécution du 29/10/2026, ajoutés après le protocole)

Commande du protocole (développement, 14 604 matchs). `dev/resultats.json` garde les 48 scores ; les `predictions.csv` (non versionnées) se régénèrent par la même commande.

| Demi-vie | Rétr. | w | Log-loss | RPS |
|---|---|---|---|---|
| **270** | **2** | **0,35** (v5) | **0,99119** | 0,20125 |
| 270 | 3 | 0,35 | 0,99123 | 0,20125 |
| 270 | 2 | 0,45 | 0,99130 | 0,20125 |
| 365 | 3 | 0,35 | 0,99136 | 0,20131 |
| 365 | 2 | 0,35 | 0,99139 | 0,20133 |

## Décision

- Meilleure combinaison du développement = `poisson-v5` : **pas de promotion**, validation et test non exécutés (prévu par le protocole). `poisson-v5-cal` reste.
- Le bord d'EXP-008 n'était pas une limite : demi-vie > 270 et w > 0,35 dégradent légèrement. Optimum local confirmé.

## Limites

- Écarts très faibles en haut du classement (< 0,0003) : surface plate autour de v5.
