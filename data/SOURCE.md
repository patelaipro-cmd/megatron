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

## Historique complet et saison en cours (28/10/2026)

- `matches_top5_2000-2026.csv` : même source, mêmes colonnes, matchs depuis le 01/07/2000 (45 559 lignes, SHA-256 `399f92c774a257dd68b680e709ae5b6b9cdaa8297ac4fb7056019b15d1ede01c`). `python scripts/extraire_donnees.py Matches.csv --depuis 2000-07-01 --sortie data/matches_top5_2000-2026.csv`. Tirs complets à partir de 2006/07 (partiels avant) ; heure absente avant 2019 (midi par défaut).
- `complement_openfootball_2026-27.csv` : **openfootball/football.json** (CC0, domaine public), `https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/{en,fr,de,es,it}.1.json`, téléchargé le 28/10/2026. 151 matchs du 04/09 au 20/09/2026, buts seulement (ni cotes ni tirs). `python scripts/complement_openfootball.py`.
  - Noms d'équipes reliés à ceux de xgabora par les matchs communs (même date, même score, saisons 2025-26 et 2026-27) : 1 850 matchs communs, 0 écart de score.
  - Heures ramenées à la convention xgabora par le décalage médian mesuré (−1 h sauf Premier League 0 h).
  - Source communautaire, non recoupée au-delà de ce contrôle.
- `matches_top5_2020-2026.csv` reste l'extrait figé des expériences EXP-001 à EXP-004 ; l'agent Stats utilise les deux fichiers ci-dessus (`data.CURRENT`).

## Cotes plus/moins de 2,5 buts (29/10/2026, EXP-006)

- `cotes_buts_2000-2026.csv` : même fichier `Matches.csv` (SHA-256 `ef224cf2…4221`, vérifié inchangé le 29/10/2026), colonnes `Division, MatchDate, HomeTeam, AwayTeam, Over25, Under25` (cotes Bet365 selon le README d'origine). Matchs des 5 ligues depuis le 01/07/2000 ayant les deux cotes : 37 736 lignes (à partir de 2005/06), toutes reliées à `matches_top5_2000-2026.csv`. SHA-256 `a677960d5eeff221e4eab939fcfc0caf9ee36b7af2813f1243eb8f1f81904f31`.
- Reconstruction : `python scripts/extraire_cotes_buts.py Matches.csv`.
