# Provenance des données

`matches_top5_2020-2026.csv` est un extrait de **xgabora/Club-Football-Match-Data** (licence MIT, © 2025 xgabora).

- Fichier d'origine : `https://raw.githubusercontent.com/xgabora/Club-Football-Match-Data/main/data/Matches.csv`
- Téléchargé le 27/10/2026, 45 370 018 octets, SHA-256 `ef224cf2c252f07a842b3bcfd4ba5c718c25cedd8937ffa174a74b86b5ba4221`
- Données d'origine : Football-Data.co.uk (résultats, cotes Bet365). Dernier match du fichier : 03/09/2026.
- Filtre : divisions F1, E0, D1, SP1, I1 ; matchs à partir du 01/07/2020 ; 11 053 lignes.
- Colonnes conservées : `Division, MatchDate, MatchTime, HomeTeam, AwayTeam, FTHome, FTAway, FTResult, OddHome, OddDraw, OddAway`, plus `HomeShots, AwayShots, HomeTarget, AwayTarget` (tirs, tirs cadrés) depuis le 28/10/2026 (EXP-004).
- Reconstruction : `python scripts/extraire_donnees.py Matches.csv` (comptes écrits en entiers).
- `MatchTime` est à l'heure CET-1 selon le README d'origine (non vérifié).
- SHA-256 de l'extrait : `fbcad524b16dc0571dbd4d85b6bea5f51002d1d88aa70b09b1404a7d255ce76c` (15 colonnes ; version à 11 colonnes : `1b821dd2…779bf727e`)

Football-Data.co.uk autorise un usage personnel et de recherche ; une diffusion commerciale demanderait une vérification de ses conditions.
