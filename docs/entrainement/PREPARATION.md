# Préparation des entraînements (29/10/2026)

Aucun entraînement n'est lancé. Cette page fixe, avant toute exécution, ce qui peut être appris,
sur quelles données et à partir de quel seuil. `python scripts/preparer_entrainement.py
--dossier-externe <externe/>` compte les données et rend ADMISSIBLE ou NON_ADMISSIBLE.
État du jour : `etat_2026-10-29.json`.

| Candidat | Ce qui serait appris ou validé | Seuil | Au 29/10/2026 | Statut |
|---|---|---|---|---|
| Fraîcheur des données | rien (condition préalable) | dernier résultat ≤ 10 j | 28/10, 1 j | ADMISSIBLE |
| EXP-014 validation 2026/27 | rien : test des coefficients figés (1X2, 3 niveaux) | ≥ 1 000 matchs 2026/27, 5 ligues | 402 | NON_ADMISSIBLE |
| EXP-013 pondération des absences | α_off, α_def (`absences.ajuster_intensites`) | ≥ 1 500 matchs avec compo avant coup d'envoi, ≥ 3 ligues, ≥ 4 mois | 1 match, 1 ligue, 0 mois | NON_ADMISSIBLE |
| Cohorte prospective | rien : preuve réelle (zone GO, seuils SYNDICATE) | ≥ 500 prévisions enregistrées avant match avec résultat | 0 | NON_ADMISSIBLE |

## Ce qui n'a pas besoin d'entraînement

`poisson-v5` se réajuste à chaque match sur les matchs antérieurs : les 152 résultats confirmés
(PR #38) suffisent à le remettre à jour, sans changer ses réglages (EXP-008, EXP-011).

## Ce qui bloque la cohorte prospective

Le registre réel est protégé par le jeton (`megatron/jeton.py`) : tant que `jeton initialiser`
n'est pas fait, aucune prévision réelle n'est enregistrée, donc aucune preuve prospective ne
s'accumule. C'est une décision de Luloki (écriture immuable dans `memoire/`).

## Interdits maintenus

Aucun réapprentissage sur 2020-2026 (déjà utilisé comme test), aucun coefficient d'absence
appris sur quelques matchs, aucun GO automatique, aucune simulation présentée comme performance.
