# EXP-013 : pondération des absences — protocole à figer, non exécuté

Statut : **projet de protocole**, aucune donnée admissible à ce jour. Rien n'est exécuté.

## Pourquoi pas maintenant

`data/` n'a aucune donnée joueur. Les absences (API-Football) et compositions (API-Football,
ESPN) ne sont collectées, datées, que depuis le 29/10/2026. Il faut au moins une saison de
matchs avec absences et compos collectées **avant** le coup d'envoi pour apprendre quoi que ce soit.

## Méthode à calibrer (`megatron/absences.py`, version `absences-exp-v0`)

Indice offensif et défensif par équipe (0 à 1). Effet candidat sur les buts attendus :
λ_eq × (1 − α_off · off_eq) × (1 + α_def · def_adv), symétrique pour l'adversaire.

## Plan proposé (à figer avant exécution)

- Données : matchs des ligues suivies avec, collectés avant le coup d'envoi, les absents
  (API-Football) et les compos des 10 matchs précédents (taux de titularisation).
- α_off, α_def appris par maximum de vraisemblance sur les buts, sur les premiers mois ;
  évaluation figée sur les mois suivants (chronologique), contre `poisson-v5-cal` sans absences.
- Critères proposés : borne haute IC 95 % (bootstrap par journée) de l'écart de log-loss 1X2
  < 0, et amélioration dans au moins 3 ligues sur 5 suivies.
- Tant que non validé : `ajuster_intensites` sans coefficient, aucune probabilité modifiée.
