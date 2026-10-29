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
