# EXP-010 : recalibration du 1X2 de poisson-v5

Statut : **protocole figé le 29/10/2026, avant toute exécution**. Les résultats sont ajoutés dans une section séparée, sans modifier le protocole.

## Question

EXP-009 a montré, en passant, qu'une recalibration logistique de `poisson-v5` (pente 1,13 à 1,17) améliorait la log-loss des questions défaite et nul : v5 serait trop prudent. Une recalibration du 1X2 entier réduit-elle l'écart avec le bookmaker ?

## Données

Prévisions `poisson-v5` déjà calculées par EXP-008, sans nouveau calcul de modèle :

- développement 2008/09-2015/16 : `docs/experiences/EXP-008/dev/<L>/predictions.csv`, colonne `270|2|0.35` (fichiers non versionnés, régénérables par la commande d'EXP-008) ;
- validation 2016/17-2019/20 et test 2020/21-2025/26 : `docs/experiences/EXP-008/{validation,test}/<L>/predictions.csv`, colonne `candidat`.

Les prévisions sont arrondies à 4 décimales (format existant).

## Recalibration

`p'_o ∝ p_o^b · exp(c_o)`, o ∈ {H, D, A}, c_A = 0 : 3 paramètres (b, c_H, c_D), maximum de vraisemblance sur le développement seul (5 ligues réunies), puis figés.

## Critères fixés avant exécution (recalibré − brut)

- **K1** : validation, borne haute IC 95 % (bootstrap apparié, 2 000 tirages, graine 1) de l'écart de log-loss < 0.
- **K2** : test, même borne < 0.
- **K3** : test, écart moyen < 0 dans au moins 4 ligues sur 5.
- **K4** : test, RPS recalibré ≤ RPS brut.
- Information : écart avec le bookmaker, calibration par tranches.

## Décision prévue

- K1-K4 tenus : `poisson-v5-cal` (v5 + b, c_H, c_D figés) devient le 1X2 de l'agent Stats.
- Sinon : `poisson-v5` brut reste.

## Limites connues avant exécution

- Même source ; une seule recalibration pour 5 ligues ; arrondi à 4 décimales.
- Le test recoupe des saisons vues par EXP-008 (choix du modèle, pas de la recalibration).

---

## Résultats (exécution du 29/10/2026, ajoutés après le protocole)

Commande : `python scripts/exp010_calibration.py --sortie docs/experiences/EXP-010`. Paramètres appris sur le développement (14 608 matchs) : **b = 1,1601, c_H = 0,0162, c_D = 0,1503** (v5 trop prudent, nuls sous-estimés).

| Log-loss | v5 brut | v5 recalibré | Bookmaker | Recalibré − brut [IC 95 %] |
|---|---|---|---|---|
| Dev 2008-2016 | 0,99118 | 0,98923 | 0,97744 | −0,0020 [−0,0030 ; −0,0009] |
| Validation 2016-2020 | 0,96948 | 0,96686 | 0,95414 | −0,0026 [−0,0040 ; −0,0012] |
| Test 2020-2026 | 0,99038 | 0,98816 | 0,97229 | −0,0022 [−0,0033 ; −0,0011] |

Test : RPS 0,20125 → 0,20082. Par ligue (recalibré − brut) : Ligue 1 −0,0008, Premier League −0,0005, Bundesliga −0,0003, Liga −0,0035, Serie A −0,0054 (IC sous 0 pour Liga et Serie A seulement).

Calibration test (tranches ≥ 2 000 prévisions) : écart max 0,046 brut (0,6-0,8 : prévu 0,671, observé 0,717) → 0,011 recalibré.

Information : retard sur le bookmaker au test +0,0181 [+0,0156 ; +0,0206] brut → +0,0159 [+0,0133 ; +0,0183] recalibré.

## Décision

- K1, K2, K3 (5/5), K4 tenus : **`poisson-v5-cal` devient le 1X2 de l'agent Stats** (`StatsAgent.CALIBRATION`). Retour arrière : `CALIBRATION = None`.
- Marchés 2+ / 3+ inchangés (`poisson-v4-platt`).

## Limites

- Gain par ligue non significatif seul en Ligue 1, Premier League et Bundesliga.
- Même source ; arrondi à 4 décimales des prévisions lues.
