# Collecte externe par GitHub Actions

Décision de Luloki du 29/10/2026 : collecte complète, compos incluses, puis élargie
au-delà des 5 ligues. L'environnement cloud de Claude ne joint que GitHub. Les
serveurs GitHub Actions, eux, ont un Internet ouvert : le workflow
`.github/workflows/collecte-externe.yml` collecte et écrit sur la branche orpheline
`donnees-externes`. Megatron lit ensuite cette branche par git, sans jamais la
fusionner dans `main`.

## Sources et fréquence

| Source | Contenu | Couverture | Fréquence |
|---|---|---|---|
| Sofascore (API interne) | Compos confirmées, absents et incertains (`missingPlayers`) | 38 divisions de `data/ligues_collecte.json` (celles qui ont un historique xgabora) + LDC, Ligue Europa, Conference League | Chaque heure pour les matchs à moins de 3 h ; tout l'horizon de 72 h aux heures UTC 0, 6, 12, 18 |
| FPL (API officielle du jeu) | Statut blessé/suspendu/incertain, chance de jouer, news | Premier League | Chaque heure |
| ClubElo | Elo du jour | Tous les clubs européens | Chaque jour |
| Understat (via soccerdata) | Statistiques d'équipe par match, xG | 5 ligues (seules couvertes par Understat) | Chaque jour |
| ESPN (API publique, sans clé) | Compos officielles (titulaires, remplaçants, formation) | 27 ligues + 3 coupes UEFA (`espn` de `data/ligues_collecte.json`) | Chaque heure, matchs qui débutent dans les 75 min, une fois par match publié |
| API-Football (clé, secret `API_FOOTBALL_KEY`) | Blessures/suspensions (toutes ligues) ; compos officielles des ligues `apifootball` de `data/ligues_collecte.json` | Toutes ligues pour les blessures ; 19 ligues + coupes UEFA pour les compos | Statut + calendrier J/J+1 au premier passage du jour, blessures aux heures 0/6/12/18 UTC, compo de chaque match suivi à moins de 75 min ; plafond 90 requêtes/jour |

## Format de la branche `donnees-externes`

```
externe/manifeste.json                     dernière exécution : statut par source
externe/etat.json                          empreinte du dernier instantané (dédoublonnage)
externe/sofascore/AAAA-MM-JJ/HHMM.csv      instantané, seulement si différent du précédent
externe/sofascore/tournois_vus.csv         tous les tournois vus (vérification des identifiants)
externe/fpl/AAAA-MM-JJ/HHMM.csv
externe/clubelo/AAAA-MM-JJ/HHMM.csv
externe/understat/matchs_equipes_<saison>.csv   réécrit chaque jour (l'historique git garde les versions)
externe/apifootball/statut.json, calendrier.json   plan, quota, matchs suivis, ligues vues
externe/apifootball/blessures/AAAA-MM-JJ/HHMM.csv
externe/apifootball/compos/AAAA-MM-JJ/HHMM.csv
externe/espn/compos/AAAA-MM-JJ/HHMM.csv
```

Chaque ligne porte `collecte_le` (UTC). Règle anti-fuite : une information n'est
utilisable pour un match que si `collecte_le` < coup d'envoi.
`scripts/lire_externe.py joueurs --avant` applique cette règle.

## Lecture depuis Claude ou Codex

```sh
git fetch origin donnees-externes
git worktree add --detach ../megatron-externe origin/donnees-externes
python scripts/lire_externe.py --dossier ../megatron-externe/externe statut
python scripts/lire_externe.py --dossier ../megatron-externe/externe joueurs --equipe '<nom Sofascore>' --avant '2026-11-01T20:00:00+01:00'
```

## Branchement au moteur (grille du favori)

```sh
python -m megatron angles-morts modele --match-id <id> --home '<A>' --away '<B>' --favori H --coup-envoi '<date avec fuseau>' > ctx.json
python -m megatron angles-morts externe --fichier ctx.json --dossier-externe ../megatron-externe/externe \
  [--nom-home '<nom API-Football>'] [--nom-away '<nom>'] [--au '<date avec fuseau>'] > ctx_enrichi.json
python -m megatron angles-morts verifier --fichier ctx_enrichi.json
```

`megatron/externe.py` lit le dernier instantané de blessures API-Football, la compo officielle
et les statuts FPL collectés avant l'analyse et avant le coup d'envoi (± 12 h pour reconnaître le
match), puis remplit l'angle `informations_manquantes` à l'état `a_verifier`. Les noms Megatron
sont rapprochés automatiquement de ceux de chaque source (`resoudre`) : nom exact, alias de
`data/noms_equipes.json` (seuls acceptés pour un nom qui y figure, ex. Paris FC / Paris SG), puis
comparaison normalisée (accents, FC/SV/City...) parmi les équipes du même créneau, refusée si ambiguë.
La méthode retenue est écrite dans le constat. Vérifié le 29/10/2026 : les 20 équipes de Premier League
vers FPL et les 14 équipes Megatron présentes dans les blessures API-Football du jour.
Un nom ambigu ou introuvable est signalé dans les informations manquantes ; `--nom-home/--nom-away` reste possible.
Avec une seule famille de sources, la règle « trois sites et familles pour les absences » reste
signalée. Aucune probabilité n'est modifiée.

## Limites connues (à lire avant usage)

- **Premier run réel (29/10/2026 15:31 UTC, déclenchement manuel)** : FPL OK (199 joueurs non disponibles ou avec news), Understat OK (402 matchs, 5 ligues), ClubElo 502 (serveur ; 3 essais ajoutés ensuite), **Sofascore 403** sur les IP GitHub malgré curl_cffi. Contourner davantage la protection anti-bot de Sofascore n'est pas fait : compos et absences hors Premier League restent sans source automatique tant qu'une API autorisée (ex. API-Football avec clé) n'est pas branchée.
- **Identifiants Sofascore** de `data/ligues_collecte.json` donnés de mémoire : comparer avec `tournois_vus.csv` après le premier run complet et corriger.
- **CGU** : Sofascore ne licencie pas son API (selon des sources secondaires ; CGU non lisibles depuis l'environnement). Le dépôt est **public** : les données collectées sont donc republiées. Risque accepté par Luloki le 29/10/2026 ; rendre le dépôt privé le réduirait (quota Actions alors limité à 2 000 min/mois sur le plan Free).
- Sofascore et Understat peuvent bloquer les IP de GitHub (Cloudflare) : une source en échec n'arrête pas les autres ; l'erreur est commitée dans le manifeste.
- Codes `reason` de Sofascore non documentés : gardés bruts (`code N`) quand il n'y a pas de description.
- Une compo « probable » n'est pas collectée : seules les compos confirmées (`confirmed`) et les absents sont écrits.
- **Premier run API-Football (29/10/2026 18:12 UTC)** : plan Free actif, 100 requêtes/jour, saison en cours accessible ; 17 matchs suivis sur J/J+1, 241 blessures/suspensions uniques (doublons J/J+1 retirés ensuite), 5 requêtes. Identifiants vérifiés dans `ligues_vues` : 40, 61, 62, 78, 79, 94, 135, 140, 144, 203. Pas encore vus (aucun match J/J+1) : 2, 3, 848, 39, 88, 136, 141, 179, 197.
- **Sonde du 29/10/2026 18:30 UTC** (`sonde-sources.yml`) : l'API ESPN répond 200 depuis GitHub ; ses compos (`rosters`) n'apparaissent qu'une fois publiées et elle ne donne **aucune blessure** (champ `injuries` absent). ESPN est une 2e famille pour les compos, pas pour les absences. CGU ESPN : usage de l'API non documenté (gris) ; ESPN exploite une marque de paris (affiliation probable). ClubElo toujours 502, aussi en http.
- API-Football : sans le secret, la source est « ignore ». Le plan gratuit peut refuser la saison en cours (réponse `errors`) : le premier run le dira dans `statut.json`/manifeste. La clé passe en en-tête, jamais dans l'URL ni les journaux.
- Rien de tout cela ne modifie une probabilité : faits déclaratifs pour `contexte_favori`, aucune utilisation dans les modèles sans expérience validée.
