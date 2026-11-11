# Boucle de retour 2026-11-06 → 2026-11-08

Prédits 48 · résolus 48 (officiels 48, provisoires 0) · sans résultat 0

| modèle | n | log-loss | RPS | réussite choix | nul prévu / observé |
|---|---|---|---|---|---|
| poisson-v5-cal | 48 | 0.8884 | 0.1755 | 58% | 25% / 23% |
| xg-v1-cal | 48 | 0.8678 | 0.1690 | 65% | 23% / 23% |
| bookmaker-b365 | 48 | 0.8550 | 0.1644 | 60% | 24% / 23% |
| bookmaker-dk | 47 | 0.8525 | 0.1630 | 60% | 24% / 23% |

## Leçons

- n=48 < 300 : constats descriptifs, aucun poids modifié (EXP-014 à >= 1000).
- poisson-v5-cal vs bookmaker-b365 (matchs communs n=48) : +0.0334 log-loss.
- xg-v1-cal vs bookmaker-b365 (matchs communs n=48) : +0.0128 log-loss.
- poisson-v5-cal vs bookmaker-dk (matchs communs n=47) : +0.0375 log-loss.
- xg-v1-cal vs bookmaker-dk (matchs communs n=47) : +0.0154 log-loss.
- SYNDICATE PASS (final) : favori gagne 13/28 (46%, prévu 45%), par 2+ 5/28 (prévu 22%).
- SYNDICATE WATCH (final) : favori gagne 16/20 (80%, prévu 62%), par 2+ 8/20 (prévu 36%).

## Plus grosses surprises (poisson-v5-cal)

- E0:2026-11-07:Nott'm Forest-Man City 3-1 : p=0.212 (officiel, SYNDICATE WATCH)
- F1:2026-11-08:Le Mans-Monaco 1-1 : p=0.23 (officiel, SYNDICATE WATCH)
- I1:2026-11-07:Cagliari-Frosinone 1-0 : p=0.236 (officiel, SYNDICATE PASS)
- SP1:2026-11-08:Celta-Levante 0-0 : p=0.248 (officiel, SYNDICATE WATCH)
- E0:2026-11-08:Man United-Aston Villa 4-4 : p=0.249 (officiel, SYNDICATE PASS)
- I1:2026-11-08:Fiorentina-Juventus 2-2 : p=0.265 (officiel, SYNDICATE WATCH)
- E0:2026-11-07:Fulham-Newcastle 1-1 : p=0.268 (officiel, SYNDICATE PASS)
- SP1:2026-11-06:Sevilla-Alaves 0-0 : p=0.274 (officiel, SYNDICATE PASS)
