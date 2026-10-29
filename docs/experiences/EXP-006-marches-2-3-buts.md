# EXP-006 : marchés 2+ et 3+ buts avec poisson-v4

Statut : **protocole figé le 29/10/2026, avant toute exécution**. Les résultats sont ajoutés dans une section séparée, sans modifier le protocole.

## Question

Le parcours n'enregistre que le 1X2. `poisson-v4` donne aussi, sans réglage nouveau, la loi du total de buts. Ses probabilités « au moins 2 buts » (2+) et « au moins 3 buts » (3+, soit plus de 2,5) battent-elles les fréquences passées, et sont-elles calibrées, avant d'être enregistrées par `prevoir` ?

## Données

- `data/matches_top5_2000-2026.csv` (PR #10), inchangé.
- `data/cotes_buts_2000-2026.csv` (nouveau) : cotes Bet365 plus/moins de 2,5 buts (`Over25`, `Under25`) de la même source xgabora, même fichier `Matches.csv` (SHA-256 `ef224cf2…4221`, inchangé depuis le 27/10). `python scripts/extraire_cotes_buts.py Matches.csv`. 37 736 matchs, tous reliés à l'historique par (division, date, équipes).
- Saisons évaluées (critères) : 2008/09 à 2019/20, 5 ligues, comme EXP-005 : aucune n'a servi à régler `poisson-v4`.
- Information seulement : 2022/23 à 2025/26 (saisons où `w = 0,25` a été choisi sur le 1X2).

## Versions comparées (aucun réglage)

- Candidate : `poisson-v4` figé (demi-vie 90, rétrécissement 3, a priori moyenne, proxy cadres, w = 0,25). Total T ~ Poisson(λ_dom + λ_ext) ; P(2+) = 1 − P(T ≤ 1), P(3+) = 1 − P(T ≤ 2).
- Référence : `frequences`, part des matchs à 2+ (ou 3+) buts dans la même ligue sur les 730 jours précédents, lissage de Laplace.
- Information : `bookmaker` pour le 3+ seulement, probabilités implicites des cotes Over25/Under25, marge retirée proportionnellement. Pas de cote pour le 2+.
- Commande : `python -m megatron marches --division <L> --saisons 2008/09,…,2019/20 --sortie docs/experiences/EXP-006/<L>` puis `python -m megatron marches-bilan docs/experiences/EXP-006/*/predictions_buts.csv --saisons …`.

## Mesures

Log-loss binaire, Brier, calibration en 10 tranches de 0,1 ; bootstrap apparié des matchs (2 000 tirages, graine 1) pour l'écart de log-loss.

## Critères fixés avant exécution (chaque marché séparément)

- **M1** : 5 ligues et 12 saisons réunies, borne haute de l'IC 95 % de l'écart de log-loss `poisson-v4` − `frequences` < 0.
- **M2** : écart moyen < 0 dans au moins 4 ligues sur 5.
- **M3** : calibration : dans chaque tranche d'au moins 500 prévisions, |p moyenne − fréquence observée| ≤ 0,03.

## Décision prévue

- M1, M2 et M3 tenus : le marché est enregistré par `prevoir` (agent Stats, version `poisson-v4`), et noté dans le bilan.
- M1 tenu mais M2 ou M3 non : marché non enregistré ; recalibration à tester dans une expérience suivante.
- M1 non tenu : marché non enregistré.

## Limites connues avant exécution

- Même source (Football-Data.co.uk via xgabora) que EXP-004 et EXP-005.
- Poisson indépendant : la dispersion du total de buts peut être mal rendue (sur- ou sous-dispersion), ce que M3 doit révéler.
- Le 2+ n'a pas de référence bookmaker.

---

## Résultats (exécution du 29/10/2026, ajoutés après le protocole)

Commandes : `python -m megatron marches --division <L> --saisons 2008/09,…,2019/20,2022/23,…,2025/26 --sortie docs/experiences/EXP-006/<L>` pour les 5 ligues, puis `python -m megatron marches-bilan docs/experiences/EXP-006/*/predictions_buts.csv --saisons <…>` (sorties : `EXP-006/bilan_2008-2020.json`, `EXP-006/bilan_2022-2026_info.json`).

Écart à signaler : avant l'exécution complète, un essai technique du code a tourné sur Ligue 1 2019/20 (279 matchs, saison du champ des critères). Aucun réglage n'en a découlé : le modèle est figé.

5 ligues, 12 saisons 2008-2020 (21 590 matchs) :

| Marché | `poisson-v4` | `frequences` | Bookmaker | Écart v4 − fréquences [IC 95 %] |
|---|---|---|---|---|
| 2+ | 0,55835 | 0,55937 | — | −0,0010 [−0,0034 ; +0,0014] |
| 3+ | 0,68740 | 0,69038 | 0,67559 | −0,0030 [−0,0058 ; −0,0003] |

Par ligue (écart v4 − fréquences) :

| Ligue | 2+ | 3+ |
|---|---|---|
| Bundesliga | +0,0009 | −0,0003 |
| Premier League | −0,0023 | +0,0014 |
| Ligue 1 | −0,0008 | −0,0070 |
| Serie A | +0,0035 | +0,0032 |
| Liga | −0,0060 | −0,0117 |

Calibration de `poisson-v4` (tranches ≥ 500 prévisions, fréquence observée − p moyenne) :
- 2+ : +0,109 (0,5-0,6), +0,045 (0,6-0,7), +0,005 (0,7-0,8), −0,028 (0,8-0,9).
- 3+ : +0,113 (0,2-0,3), +0,074 (0,3-0,4), +0,028 (0,4-0,5), −0,015 (0,5-0,6), −0,044 (0,6-0,7), −0,017 (0,7-0,8).

Le modèle est trop tranché : quand il annonce peu de buts, il y en a plus, et inversement. Le total de buts varie moins d'un match à l'autre que ne le disent les écarts de λ.

Information 2022-2026 (7 081 matchs) : 2+ +0,0003 [−0,0038 ; +0,0045] ; 3+ −0,0027 [−0,0074 ; +0,0020] ; même défaut de calibration. Bookmaker en avance sur le 3+ : +0,0118 [+0,0098 ; +0,0138] (2008-2020).

## Décision

- **2+** : M1 non tenu (IC contient 0), M2 non tenu (3 ligues sur 5), M3 non tenu (écart 0,109). **Non enregistré.**
- **3+** : M1 tenu (borne haute −0,0003), M2 non tenu (3 ligues sur 5), M3 non tenu (écart 0,113). **Non enregistré** ; recalibration à tester (EXP-007).

## Limites

- Même source que EXP-004/005.
- Le gain du 3+ sur les fréquences est faible et instable selon la ligue.
