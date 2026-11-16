# V2 GOALS indépendante — 16 novembre 2026

V2 reçoit le calendrier complet fourni, sans présélection par V1 domination.
Elle ne consomme ni favori, ni marge de victoire, ni probabilité 1X2.
Les mi-temps ne figurent pas dans cette sortie.

| Marché | Total gagnant | Modèle |
|---|---|---|
| OVER_2_5 | 3 buts ou plus | poisson-v5-platt existant |
| OVER_3_5 | 4 buts ou plus | Poisson brut expérimental |
| OVER_4_5 | 5 buts ou plus | Poisson brut expérimental |
| UNDER_1_5 | 0 ou 1 but | complément du marché 2+ calibré existant |

Commande en lecture seule :

```sh
python -m megatron goals --calendrier calendrier.json
```

Entrée JSON : liste de rencontres avec `division`, `home`, `away`, `kickoff`
(ISO 8601 avec fuseau). Le fournisseur du calendrier doit inclure tous les matchs
à étudier, pas uniquement les favoris V1. La commande ne collecte pas le calendrier.
`--au` permet un contrôle historique ; les résultats ne constituent alors pas un
registre prospectif. `--seuil` vaut 0.60 par défaut, seuil opérationnel provisoire,
pas preuve de calibration des sélections.

La prévision utilise uniquement des résultats de jours strictement antérieurs
à l'instant d'analyse et au match. Les matchs commencés sont exclus ; les équipes
avec moins de cinq observations sont bloquées ; dernières observations de plus
30 jours : A_ACTUALISER. Aucun modèle n'est ajusté sur les cotes.
Les historiques proviennent de data.CURRENT, dont la couverture reste limitée.

Les candidats restent WATCH : compositions, absences et contexte ne sont pas
vérifiés automatiquement. Over 3.5/4.5 doivent être calibrés et évalués sur une
période indépendante avant utilisation validée. La calibration existante ne
prouve pas la calibration d'une sélection à 60 %, ni sa rentabilité.
Pas de modification de V1, des coefficients ou du registre réel.

Tests : indépendance de V1 sur équipes équilibrées, faibles/forts totaux, anti-fuite,
match commencé, historique manquant/périmé, seuil invalide et traitement de tous
les matchs fournis. Tests avec données synthétiques, sans valeur de backtest.
