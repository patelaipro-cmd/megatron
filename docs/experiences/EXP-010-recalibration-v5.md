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
