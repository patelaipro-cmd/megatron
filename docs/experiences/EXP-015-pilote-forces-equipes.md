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

---

## Résultats (29/10/2026, ajoutés après le protocole)

Commandes (racine du dépôt) : `node scripts/experiences/EXP-015/test_exp014.js` (OK), puis
`node scripts/experiences/EXP-015/exp014_train.js data/matches_top5_2020-2026.csv <reexec.json> <checkpoint.json>`
(0,8 s), puis `python scripts/experiences/EXP-015/comparer.py --checkpoint <checkpoint.json> --sortie docs/experiences/EXP-015`.

**R (reproduction) tenu** : blob `0bdc03ab…ad68` vérifié ; 7 451 / 1 751 / 1 752 ; ridge 0,002 (bord
inférieur de la grille) ; 136 équipes ; log-loss test 0,657386 / 0,545181 / 0,344231 et Brier
identiques à l'archive (écart < 1e-10). `resultats_reexecution.json`.

**Comparaison** (1 752 matchs 2025/26, log-loss, écart pilote − modèle en place [IC 95 %]) :

| Mesure | Pilote | En place | Écart |
|---|---|---|---|
| C1 1X2 (contre v5-cal) | 1,0028 | 0,9921 | +0,0107 [+0,0016 ; +0,0193] |
| C2 marge 7 classes (contre v5 brut) | 1,7386 | 1,7271 | +0,0115 [+0,0013 ; +0,0221] |
| C3 victoire, favori v5 (contre v5 EXP-012) | 0,6680 | 0,6619 | +0,0061 [−0,0030 ; +0,0146] |
| C3 victoire par 2+ | 0,5635 | 0,5551 | +0,0084 [+0,0007 ; +0,0161] |
| C3 victoire par 3+ | 0,3599 | 0,3520 | +0,0079 [+0,0015 ; +0,0148] |
| Info : 3 niveaux, favori du pilote, contre v5 brut | 0,6574 / 0,5452 / 0,3442 | 0,6489 / 0,5363 / 0,3371 | tous > 0 |

Favori identique dans 1 499 matchs sur 1 752. Détail : `EXP-015/comparaison.json`.

## Décision

Le pilote ne bat le modèle en place sur **aucune** mesure ; il est significativement moins bon
sur 1X2, marge et niveaux 2+ / 3+. Il bat seulement la référence « moyennes de ligue » de
l'archive, ce que v5 fait aussi, et mieux. **Classé, sans suite** : rien n'est remplacé, aucun
paramètre de production modifié, GO OFF.

Causes probables, non testées : modèle figé toute la saison (v5 se réajuste chaque jour), aucun
oubli progressif (v5 : demi-vie 270 j), historique limité à 2020 (v5 : depuis 2000), pas de tirs
cadrés (v5 : proxy 0,35), ridge choisi au bord de la grille.
