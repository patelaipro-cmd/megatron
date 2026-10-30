# EXP-024 : calibration glissante sur les 10 ligues non couvertes

Statut : **protocole figé le 30/10/2026, avant toute exécution**. Les résultats sont ajoutés dans une
section séparée, sans modifier le protocole. Expérience **diagnostique** : les saisons 2016-2026
ont déjà servi à EXP-022 et EXP-023 ; seule la partie prospective (2026/27) peut valider.

## Question

EXP-023 : la recalibration fixe par ligue (apprise sur 2008-2016) ne corrige pas les 10 ligues mal
calibrées (E1, E2, E3, EC, SP2, I2, N1, P1, B1, T1) ; le défaut ressemble à une dérive dans le temps
(taux de nuls, avantage du terrain). Une calibration réapprise chaque saison sur le seul passé
récent de la ligue corrige-t-elle cette dérive ?

## Données

Prévisions v5 brutes d'EXP-022 (`docs/experiences/EXP-022/brut`, régénérables, aucun réglage v5 changé).

## Modèles

- **A** : v5 + calibration des 5 ligues (`StatsAgent.CALIBRATION`), modèle actuel.
- **G** : pour la ligue L et la saison s, v5 + recalibration p' ∝ p^b · exp(c) (forme d'EXP-010,
  `exp010_calibration.fit`) apprise sur les **3 saisons précédentes** de L seulement (s−3 à s−1),
  appliquée à toute la saison s. Fenêtre fixée ici, non réglée.
- Bases : fréquences antérieures de la ligue ; bookmaker (Bet365, marge retirée), information.

## Périodes (diagnostiques)

Validation 2016/17-2019/20 ; test 2020/21-2025/26 (G de 2016/17 appris sur 2013-2016, etc.).

## Critères, fixés avant exécution (log-loss 1X2, bootstrap apparié 2 000 tirages, graine 1)

Par ligue :

- **R1** : G − A, borne haute IC 95 % < 0 en validation **et** en test.
- **R2** : G − fréquences en test, borne haute IC 95 % < 0.
- **R3** : calibration de G en test, |observé − prévu| ≤ 0,05 dans chaque tranche de 0,1 comptant au
  moins 200 matchs (règle de L3/K3).
- Information : G − A et calibration **saison par saison** en test (la dérive est-elle suivie ?) ;
  G − bookmaker ; les 10 ligues réunies.

## Décision prévue

- Ligues tenant R1, R2 et R3 : **candidates diagnostiques** seulement. Aucune entrée dans le
  registre réel, aucune probabilité de production modifiée.
- Validation prospective obligatoire avant tout usage : paramètres G de 2026/27 (appris sur
  2023-2026) figés et enregistrés dans les résultats ; lecture unique en fin de saison 2026/27
  (juin 2027) sur les matchs joués après le figeage, mêmes critères R1 (contre A), R2, R3.
- Les 7 ligues couvertes par EXP-022/023 restent **candidates** elles aussi, jusqu'à leur propre
  validation prospective (décision de Luloki, 30/10/2026).
- Aucun appel LLM.

## Limites connues avant exécution

- Validation et test déjà vus (scores de A) : risque de choix de forme guidé par EXP-023.
- Fenêtre de 3 saisons ≈ 900 à 1 650 matchs par ligue : paramètres bruités possibles.
- Promus et relégués entre divisions toujours traités comme équipes nouvelles.
- Cotes Bet365 de football-data, pas de clôture.
