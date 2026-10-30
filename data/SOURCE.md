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

## Détails de match pour les angles morts (29/10/2026, EXP-009)

- `details_2000-2026.csv` : même fichier `Matches.csv` (SHA-256 `ef224cf2…4221`, vérifié inchangé le 29/10/2026), colonnes `Division, MatchDate, HomeTeam, AwayTeam, HTHome, HTAway, HomeRed, AwayRed, HomeCorners, AwayCorners, HomeFouls, AwayFouls, HandiSize, HandiHome, HandiAway` (handicap asiatique Bet365 selon le README d'origine). 45 559 lignes, toutes reliées à `matches_top5_2000-2026.csv`. Remplissage ≥ 99,8 % depuis 2008/09. SHA-256 `4ff14aa330a77a7213ab2635d33d2bd6e528529436a8ec7d0c528c956e40f699`.
- Elo et Form* de la source non repris : date de calcul non documentée (risque de fuite).
- Reconstruction : `python scripts/extraire_details.py Matches.csv`.

## Collecte externe (29/10/2026, branche `donnees-externes`)

- Sofascore (compos, absents), FPL (statut joueurs PL), ClubElo (Elo), Understat (xG d'équipe), collectés par `.github/workflows/collecte-externe.yml`, jamais commités sur `main`.
- Ligues suivies : `data/ligues_collecte.json` (38 divisions de l'historique xgabora + coupes UEFA). Identifiants Sofascore à vérifier après le premier run.
- Chaque ligne porte `collecte_le` ; usage pré-match seulement si `collecte_le` < coup d'envoi. CGU et limites : `docs/collecte-externe.md`.

## Résultats confirmés depuis le 21/09/2026 (29/10/2026)

- `complement_resultats_2026-27.csv` : 152 matchs du 09/10 au 28/10/2026 (E0 30, F1 27, D1 27, SP1 30, I1 38), chacun confirmé par **deux familles indépendantes** : ESPN (`site.api.espn.com`, tableau des scores) et football-data.co.uk (fichiers 2026/27). Même score final, dates à un jour près, aucune source en désaccord.
- Collecte brute : workflow `resultats` (GitHub Actions), branche `donnees-externes`, dossier `externe/resultats/2026-10-29T1944Z/` (ESPN 450 pages, 405 événements, SHA-256 `3f22746d…d6ad8e`). Recoupement hors réseau : `python scripts/verifier_resultats.py --brut <dossier> --depuis 2026-09-21`.
- Noms reliés par les matchs communs de la saison (vote de `complement_openfootball.py`) : 96 noms ESPN et 96 football-data, aucun nom approché.
- Cotes Bet365 (B365H/D/A) et tirs (HS, AS, HST, AST) repris de football-data, l'origine de l'historique xgabora.
- Heures : ESPN est en UTC, ramené à la convention de `data/` par le décalage médian mesuré (+1 h, mesuré sur août-septembre ; changement d'heure du 25/10 non corrigé, seul l'ordre intra-journée en dépend).
- Rapport, quarantaine et refus : `docs/resultats-2026-27/`. SHA-256 du fichier : `71d3f9d7…f7e7f531`.
- API-Football n'a pas servi : le plan gratuit refuse `season=2026` (« try from 2022 to 2024 »).

## Autres championnats européens (30/10/2026, EXP-022)

- `matches_autres_2000-2026.csv` : même fichier `Matches.csv` (SHA-256 `ef224cf2…4221`, vérifié inchangé le 30/10/2026), mêmes colonnes que `matches_top5_2000-2026.csv`, divisions E1, E2, E3, EC, SC0, SC1, SC2, SC3, SP2, I2, F2, D2, N1, P1, B1, T1, G1, matchs depuis le 01/07/2000 avec score (138 819 lignes). SHA-256 `d2770f88bfe5507cd1b8d3a95ec36de6d96e308f31ffcd9a0cac5626b94ec2ae`.
- Reconstruction : `python scripts/extraire_donnees.py Matches.csv --depuis 2000-07-01 --sortie data/matches_autres_2000-2026.csv --divisions E1,E2,E3,EC,SP2,I2,F2,D2,T1,N1,P1,B1,SC0,SC1,SC2,SC3,G1` (les lignes sans score sont désormais ignorées ; l'extrait des 5 ligues est inchangé, SHA vérifié).
