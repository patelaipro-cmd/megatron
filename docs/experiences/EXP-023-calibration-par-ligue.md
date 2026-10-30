# EXP-023 : recalibration 1X2 par ligue sur les 17 autres championnats

Statut : **protocole figé le 30/10/2026, avant toute exécution**. Les résultats sont ajoutés dans une
section séparée, sans modifier le protocole.

## Question

EXP-022 : poisson-v5 bat les fréquences dans les 17 ligues mais 11 restent mal calibrées, avec
des défauts propres à chaque ligue (taux de nuls, avantage du terrain). Une recalibration propre
à chaque ligue corrige-t-elle cela sans surapprentissage ?

## Données et modèles

Mêmes prévisions v5 brutes qu'EXP-022 (`docs/experiences/EXP-022/brut`, régénérables), mêmes périodes
(dev 2008/09-2015/16, validation 2016/17-2019/20, test 2020/21-2025/26).

- **A** : v5 + calibration des 5 ligues (retenu par EXP-022).
- **C_L** : v5 + recalibration p' ∝ p^b · exp(c) (b, c_H, c_D) apprise sur le seul dev de la ligue L.

## Critères, fixés avant exécution

- **K1** (choix par ligue) : C_L − A en validation, borne haute IC 95 % (bootstrap apparié, 2 000
  tirages, graine 1) < 0 → C_L ; sinon A. Le modèle retenu pour la ligue est M_L.
- **K2** : M_L − fréquences en test, borne haute IC 95 % < 0.
- **K3** : calibration de M_L en test, |observé − prévu| ≤ 0,05 dans chaque tranche de 0,1 comptant
  au moins 200 matchs (même règle que L3).
- Information : C_L − A en test pour toutes les ligues ; M_L − bookmaker.

## Décision prévue

Ligues tenant K2 et K3 : couvertes, avec M_L (paramètres par ligue enregistrés dans la fiche ;
branchement de `StatsAgent` dans une PR séparée). Les autres restent non couvertes. Aucun GO,
aucune probabilité de production modifiée, aucun appel LLM.

## Limites connues avant exécution

Test déjà vu globalement par EXP-022 (score de A) ; seuls les paramètres C_L sont nouveaux.
Dev d'environ 2 000 à 4 400 matchs par ligue.

## Résultats (exécution du 30/10/2026)

`python scripts/exp023_calibration_ligue.py --brut docs/experiences/EXP-022/brut --sortie docs/experiences/EXP-023` (~1 min).

**Verdict : la recalibration par ligue aide peu. 7 ligues couvertes : SC0, SC1, SC2, SC3, F2, D2, G1.**

- K1 retient C_L dans 3 ligues seulement (EC, SC2, D2) ; A partout ailleurs.
- En test, C_L − A n'est significativement négatif qu'en E3 (−0,0022) et positif en P1 et T1 :
  les paramètres appris sur 2008-2016 ne tiennent pas sur 2020-2026.
- Seule SC2 gagne K3 (couverte avec C_L). Les défauts de E1, E2, E3, EC, SP2, I2, N1, P1, B1,
  T1 persistent (mêmes tranches qu'EXP-022) : c'est une **dérive dans le temps** (taux de nuls,
  avantage du terrain qui changent entre 2008-16 et 2020-26), pas un biais fixe de ligue.

| ligue | modèle | (b ; c_H ; c_D) de C_L | K1 C − A validation | C − A test | K3 |
|---|:-:|---|---:|---:|:-:|
| EC | C | 0,994 ; −0,010 ; 0,020 | −0,0047 | −0,0018 | non |
| SC2 | C | 0,898 ; 0,042 ; −0,085 | −0,0089 | 0,0000 | oui |
| D2 | C | 0,754 ; 0,151 ; 0,133 | −0,0100 | −0,0002 | oui |
| autres | A | voir `resultats.json` | IC traverse 0 | | |

Suite possible (protocole séparé) : calibration glissante (réapprise chaque saison sur les saisons
précédentes) pour suivre la dérive.
