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
