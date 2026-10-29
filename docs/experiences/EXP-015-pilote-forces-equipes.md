# EXP-015 : pilote « Poisson à forces d'équipes » (archive EXP-014 de Luloki) contre poisson-v5-cal

Statut : **protocole de comparaison figé le 29/10/2026, avant de calculer la comparaison**. La
reproduction du pilote a déjà été lancée (elle est l'objet même de la demande) ; la comparaison
avec le modèle en place ne l'a pas été.

Numérotation : l'archive l'appelle EXP-014, mais EXP-014 est déjà le protocole de validation
2026/27 du dépôt (PR #39). Le pilote devient EXP-015 ; scripts et rapport d'origine sont gardés
tels quels dans `scripts/experiences/EXP-015/` et `docs/experiences/EXP-015/` (`*_livre*`).

## Pilote (inchangé)

`exp014_train.js` : Poisson indépendant, intercepts domicile/extérieur par ligue, forces attaque
/ défense par équipe, SGD 32 passages, graine 17, ridge choisi sur 2024/25 parmi 0,002 / 0,02 / 0,10,
réentraîné sur 2020/21-2024/25, **figé** pour toute la saison test 2025/26 (1 752 matchs).
Source : `data/matches_top5_2020-2026.csv`, blob `0bdc03ab…ad68` vérifié par le script.

## Étape 1 : reproduction

Critère R : mêmes effectifs (7 451 / 1 751 / 1 752), même ridge, log-loss et Brier du test égaux
à ceux de l'archive à 1e-8 près. Sinon : pilote rejeté.

## Étape 2 : comparaison sur les mêmes 1 752 matchs

Modèle en place : `poisson-v5` (intensités d'EXP-009, réajustées chaque jour sur les seuls matchs
antérieurs), 1X2 recalibré `poisson-v5-cal` (EXP-010), niveaux recalibrés EXP-012.

- **C1** 1X2 : log-loss pilote − v5-cal.
- **C2** marge en 7 classes (≤ −3, −2, −1, 0, +1, +2, ≥ +3, côté domicile) : pilote − v5 brut.
- **C3** niveaux du favori **désigné par v5** (définition de production) : pilote − v5 recalibré
  EXP-012, pour victoire, 2+, 3+.
- Information : niveaux avec le favori du pilote (définition de l'archive), pilote − v5 brut.

IC 95 % par bootstrap apparié par journée (grappes = date de match), 2 000 tirages, graine 1.

## Décision prévue

- Le pilote n'est jugé « meilleur » sur une mesure que si la borne haute de l'IC de l'écart est < 0.
- Quelle que soit l'issue, **aucun remplacement** : saison test déjà vue par le projet, modèle
  non préenregistré. Un pilote meilleur sur C1-C3 donnerait seulement lieu à un protocole
  prospectif (cohorte du registre) ; un pilote moins bon est classé, sans suite.
- GO OFF, aucun paramètre de production modifié.
