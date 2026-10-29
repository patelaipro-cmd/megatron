# Trois niveaux pour une équipe désignée avant le match

| Niveau | Définition | Clé |
|---|---|---|
| Victoire simple | au moins un but d'écart | 1X2 : H ou A |
| Victoire par 2+ | au moins deux buts d'écart | H_MARGE_2PLUS / A_MARGE_2PLUS |
| Victoire par 3+ | au moins trois buts d'écart | H_MARGE_3PLUS / A_MARGE_3PLUS |

Les probabilités sont emboîtées : ne pas les additionner. Une victoire par
exactement deux buts est incluse dans 2+, pas dans 3+. En cas de nul ou de
défaite, les deux marges du côté choisi sont « non ».

Les anciennes clés `2+` et `3+` restent des TOTAUX de buts. Leur recalibration
EXP-007 n'est pas applicable aux nouvelles marges. Rien n'est renommé dans
l'historique. Les nouveaux marchés exigent un score, et non seulement H/D/A.

## Calcul exploratoire local, sans écriture ni réseau

```sh
python -m megatron marges --xg-home 1.8 --xg-away 0.7
```

Les intensités ci-dessus sont un exemple artificiel, pas une analyse de match.
La commande expose les trois niveaux pour H et A, les quatre événements de
marge et le 1X2 sous un même Poisson indépendant. Elle renvoie explicitement
`EXPERIMENTAL_NON_CALIBRE`. Aucune collecte n'est effectuée, aucune provenance
n'est inventée. Domaine numérique : intensités finies entre 0 et 10 ; support
0..60, masse restante déclarée. Valeurs invalides : refus, code 2.

## Registre expérimental

Ledger accepte les quatre nouvelles clés dans `predict(..., market=...)`.
`Ledger.evaluate(version, market=...)` les évalue à partir des résultats avec
score. Un résultat sans score les laisse non résolus. Dans une mémoire protégée,
les règles de jeton s'appliquent également à ces prévisions.

`prevoir` ne produit PAS automatiquement ces marges ; le bilan CLI habituel
reste celui des marchés déjà intégrés. Aucun signal GO ni seuil de domination
n'est activé. Le choix des cotes, des absences et du contexte n'est pas couvert
par ce module brut. Le protocole à suivre avant toute performance historique
ou calibration est [PROTOCOLE_MARGES_VICTOIRE_V0.md](experiences/PROTOCOLE_MARGES_VICTOIRE_V0.md).

Tests réalisés : événements directionnels, seuils exacts, score nul, conservation
des marchés de total, loi de Poisson exacte quand l'adversaire a une intensité
nulle, symétrie, emboîtement des niveaux, normalisation, valeurs non finies,
évaluation d'un registre fictif et absence d'écriture de la commande exploratoire.
Ces tests prouvent le contrat et les calculs, pas la calibration sur le football réel.
