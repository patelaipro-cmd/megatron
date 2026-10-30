# EXP-022 : poisson-v5 sur 17 autres championnats européens

Statut : **protocole figé le 30/10/2026, avant toute exécution**. Les résultats sont ajoutés dans une
section séparée, sans modifier le protocole.

## Question

Demande de Luloki (30/10/2026) : élargir au-delà des 5 grands championnats. Le modèle 1X2
poisson-v5 (réglé sur les 5 ligues) est-il utilisable tel quel sur d'autres championnats, faut-il
une recalibration propre, et dans quelles ligues est-il fiable ?

## Données

`data/matches_autres_2000-2026.csv` : même source que `data/matches_top5_2000-2026.csv`
(xgabora `Matches.csv`, SHA-256 `ef224cf2…4221`), 17 divisions européennes encore à jour
(dernier match fin août / début septembre 2026) : E1, E2, E3, EC (Angleterre 2 à 5), SC0-SC3
(Écosse 1 à 4), SP2, I2, F2, D2, N1, P1, B1, T1, G1. 138 819 matchs joués (lignes sans score
retirées). Les 16 ligues hors Europe de la source s'arrêtent en décembre 2024 : exclues (rien à
prévoir aujourd'hui). Tirs cadrés absents de beaucoup de ligues : pseudo-buts = buts seuls quand
ils manquent (comportement existant de `fit_maher`). Chaque ligue est ajustée sur son seul passé
(pas de lien entre divisions : un promu arrive avec l'a priori « moyenne »).

## Modèles (aucun hyperparamètre réajusté)

- **A** v5 + calibration des 5 ligues (`StatsAgent.CALIBRATION`, EXP-010) : transfert tel quel.
- **B** v5 + recalibration p' ∝ p^b · exp(c) (forme d'EXP-010) apprise sur le dev des 17 ligues réunies.
- Bases : fréquences antérieures de la ligue ; bookmaker (Bet365, marge retirée), information.

## Périodes (celles d'EXP-008)

Dev 2008/09-2015/16 (recalibration B) ; validation 2016/17-2019/20 ; test 2020/21-2025/26.

## Critères, fixés avant exécution

- **L1** (choix de la calibration) : B − A en validation, borne haute IC 95 % (bootstrap apparié,
  2 000 tirages, graine 1) < 0 → B ; sinon A. Le modèle retenu est noté M.
- **L2** (ligue couverte) : pour chaque ligue, M − fréquences en test, borne haute IC 95 % < 0.
- **L3** (ligue couverte) : calibration de M en test, |fréquence observée − probabilité moyenne|
  ≤ 0,05 dans chaque tranche de 0,1 comptant au moins 200 matchs de la ligue.
- Information : M − bookmaker par ligue ; écart moyen de toutes les ligues réunies.

## Décision prévue

- Ligues tenant L2 et L3 : `StatsAgent` peut les prévoir avec M (PR séparée : chargement de
  `matches_autres`, calibration par groupe de ligues). Les autres restent non couvertes.
- Aucun GO, aucune probabilité de production modifiée par cette expérience ; aucun appel LLM.

## Limites connues avant exécution

- Hyperparamètres v5 réglés sur les 5 grandes ligues ; une grille propre aux autres ligues serait
  une expérience à part.
- Promus et relégués entre divisions traités comme équipes nouvelles (perte d'information).
- Cotes Bet365 de football-data, pas de clôture.

## Résultats (exécution du 30/10/2026)

`python scripts/grille_multi.py --donnees data/matches_autres_2000-2026.csv --saisons 2008/09,…,2025/26 --ligues <17> --configs "v5=270,2,0,moyenne,cadres,0.35" --sortie docs/experiences/EXP-022/brut --processus 4`
(~25 min ; `predictions.csv` non versionnés, régénérables), puis
`python scripts/exp022_autres_ligues.py --brut docs/experiences/EXP-022/brut --sortie docs/experiences/EXP-022`.

Correctif hors protocole avant l'exécution : `models.bookmaker` ignore une cote ≤ 1 (7 lignes à cote
0 dans E1/E2/E3, qui faisaient planter le calcul ; aucune ligne de ce type dans les 5 ligues).

Recalibration B (dev, 45 201 matchs) : b = 0,9316 ; c_H = 0,0674 ; c_D = 0,0982.
**L1** : B − A validation −0,00063 [−0,00141 ; +0,00015] → **A retenu** (calibration des 5 ligues).

Test 2020-26, 17 ligues réunies (34 982 matchs) : log-loss A 1,0268 ; fréquences 1,0774 ;
A − fréquences −0,0507 [−0,0541 ; −0,0471] ; A − bookmaker +0,0164 [+0,0147 ; +0,0182]
(même ordre que dans les 5 ligues : 0,0159).

| ligue | n test | A − fréquences | A − bookmaker | L2 | L3 |
|---|---:|---:|---:|:-:|:-:|
| E1 | 3 387 | −0,027 | +0,015 | oui | non |
| E2 | 3 309 | −0,038 | +0,018 | oui | non |
| E3 | 3 308 | −0,015 | +0,017 | oui | non |
| EC | 2 819 | −0,054 | +0,016 | oui | non |
| SC0 | 1 340 | −0,118 | +0,014 | oui | **oui** |
| SC1 | 1 014 | −0,031 | +0,012 | oui | **oui** |
| SC2 | 994 | −0,057 | +0,023 | oui | non |
| SC3 | 999 | −0,025 | +0,014 | oui | **oui** |
| SP2 | 2 836 | −0,017 | +0,018 | oui | non |
| I2 | 2 350 | −0,021 | +0,021 | oui | non |
| F2 | 2 129 | −0,021 | +0,020 | oui | **oui** |
| D2 | 1 836 | −0,025 | +0,014 | oui | **oui** |
| N1 | 1 836 | −0,122 | +0,014 | oui | non |
| P1 | 1 883 | −0,147 | +0,012 | oui | non |
| B1 | 1 853 | −0,069 | +0,010 | oui | non |
| T1 | 2 187 | −0,076 | +0,021 | oui | non |
| G1 | 902 | −0,107 | +0,017 | oui | **oui** |

**Ligues couvertes (L2 et L3) : SC0, SC1, SC3, F2, D2, G1.** Les 11 autres battent nettement les
fréquences mais ont au moins une tranche mal calibrée (écart > 0,05) : nuls surestimés en E1/E2
(prévu 0,31-0,32, observé 0,24-0,25) et sous-estimés en I2 (0,27 contre 0,32) ; domicile
sous-estimé chez les outsiders (tranche 0,2 : E1, E3, EC, SP2) et surestimé chez les favoris
(N1, P1, B1, EC). Le défaut est propre à chaque ligue (taux de nuls, avantage du terrain) :
une recalibration **par ligue** (intercepts c_H, c_D propres) est la suite naturelle, dans un
protocole séparé (EXP-023).
