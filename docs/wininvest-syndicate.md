# WININVEST / SYNDICATE dans Megatron

Reprise du 29/10/2026 (demande de Luloki). L'ancien barème de pondération des absences de
septembre 2026 est **introuvable** dans les sources accessibles (dépôt et branches, fichiers du
projet, mémoire) : il n'a pas été reconstitué de tête. Une méthode expérimentale le remplace,
sans effet sur les probabilités tant qu'EXP-013 ne l'a pas calibrée.

## Commandes

```sh
# évaluation complète, sans écriture (fiche, 3 niveaux, angles morts, décision)
python -m megatron syndicate evaluer --division F1 --home Lyon --away Lens \
  --coup-envoi 2026-11-01T20:00:00+00:00 --dossier-externe ../megatron-externe/externe [--resume]
# contrôles enregistrés : initial (5 h à 35 min avant), T-30 (35-25 min), T-5 (8-2 min), revision
python -m megatron syndicate controle --moment initial ... --acces claude --jeton <id>
```

Options : `--contexte-favori` (grille des 13 angles), `--cotes` (relevés datés), `--absents`
(absents saisis à la main avec poste, temps de jeu, part offensive, niveau du remplaçant, sources).

## Modules

| Module | Rôle | Réutilise |
|---|---|---|
| `megatron/wininvest.py` | Fiche des 8 rubriques : forme 5 derniers, H2H, force des adversaires, classement et enjeux, compos, absences, fatigue, cotes et évolution | `data`, `models` (poisson-v5), `angles_morts`, `externe` |
| `megatron/absences.py` | Pondération expérimentale : importance (temps de jeu, apport offensif ou défensif), remplaçant, absences simultanées par ligne, consolidation des sources et contradictions | — |
| `megatron/syndicate.py` | 3 niveaux du favori (victoire, 2+, 3+ de marge), risques nul/défaite, 3 questions des angles morts, grille des 13 angles, décision GO/SECURE/WATCH/PASS | `marges`, `angles_morts`, `contexte_favori`, `marches` (Platt) |
| `megatron/controles.py` | Initial / T-30 / T-5 / révision ; changements détectés ; marchés de marge au registre immuable | `ledger`, `jeton`, `suivi.FENETRE` |

## Règles

- Marges de victoire, jamais le total de buts (`H_MARGE_2PLUS` etc. distincts de `2+`/`3+`).
- Anti-fuite : matchs strictement antérieurs au jour du match, données externes collectées avant
  l'analyse et avant le coup d'envoi, analyse refusée à partir du coup d'envoi, registre refusé
  après le coup d'envoi, rien n'est réécrit (contrôles ajoutés à côté).
- Historique de plus de 10 jours avant le match : rubriques « périmé », décision PASS.
  **État au 29/10/2026 : `data/` s'arrête au 20/09/2026** (xgabora figé, complément openfootball
  jusqu'au 20/09) : toute évaluation d'un match actuel sort PASS tant que les résultats récents
  ne sont pas ajoutés.
- Décision indicative, règles provisoires (seuils dans `syndicate.SEUILS`) :
  PASS si favori < 50 %, historique périmé, grille invalide ou, à T-5, compos non confirmées ou
  absences contradictoires ; WATCH si une information manque ou favori < 60 % ; SECURE sinon ;
  GO seulement si P(2+) >= 60 % **et** zone validée (`ZONE_GO_VALIDEE`, faux après EXP-012).
  `ACTIVATION_AUTOMATIQUE = False` : aucune action déclenchée.
- Claude est le seul fournisseur LLM externe consulté par défaut (`default_agents`).

## Validation

- EXP-012 (`docs/experiences/EXP-012-niveaux-victoire.md`) : les trois niveaux battent les
  fréquences historiques sur 2020/21-2025/26 et sont calibrés (tranches >= 500 matchs) ;
  recalibration de Platt adoptée ; zone GO non validée.
- EXP-013 (à faire, `docs/experiences/EXP-013-absences.md`) : calibrer la pondération des
  absences quand assez de compos et d'absences datées auront été collectées.
