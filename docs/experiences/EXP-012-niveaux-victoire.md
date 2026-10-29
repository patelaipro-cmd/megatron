# EXP-012 : les trois niveaux SYNDICATE (victoire, victoire par 2+, victoire par 3+) sont-ils fiables ?

Statut : **protocole figé le 29/10/2026, avant toute exécution**. Il applique
`PROTOCOLE_MARGES_VICTOIRE_V0.md`. Les résultats sont ajoutés dans une section séparée, sans
modifier le protocole.

## Question

`syndicate.niveaux` donne, pour le favori, P(victoire), P(victoire par au moins 2 buts) et
P(victoire par au moins 3 buts) sur la matrice Poisson `poisson-v5` brute. Ces probabilités
battent-elles les fréquences historiques et sont-elles calibrées ? Une recalibration logistique
par niveau (Platt) apprise sur des saisons passées fait-elle mieux, sur des saisons jamais
utilisées pour l'apprendre ? Ce sont des marges de victoire, jamais le total de buts.

## Données

- `docs/experiences/EXP-009/variables.csv` (déjà publié, SHA-256 vérifié à l'exécution) :
  pour chaque match 2008/09-2025/26 des 5 ligues, `lam_fav` et `lam_adv` de `poisson-v5`
  (demi-vie 270, rétrécissement 2, w 0,35), ajustés sur les seuls matchs antérieurs ; favori =
  plus grand taux de buts (identique au plus grand P(victoire) sous Poisson indépendant).
- Scores réglementaires : `data.CURRENT` (xgabora / Football-Data), joints par `match_id`.
  Un match sans score joint est exclu et compté.

## Modèles, pour chaque niveau k = 1, 2, 3 (événement : buts favori − buts adversaire >= k)

- **F** fréquences : part des matchs antérieurs de la même ligue (depuis 2008/09, jour strictement
  antérieur) où le favori a gagné par k ou plus ; moins de 200 matchs antérieurs : toutes ligues.
- **B** `poisson-v5` brut (matrice 0-10 buts, renormalisée).
- **C** B recalibré : `logit(p') = a + b · logit(p)`, a et b appris sur la calibration
  2016/17-2019/20 (5 ligues réunies), puis figés.

Périodes : réglage du modèle 2008/09-2015/16 (déjà fait par EXP-008), calibration
2016/17-2019/20, réévaluation figée 2020/21-2025/26. Ces saisons ont déjà servi au projet
(1X2) : ce n'est pas un test vierge.

## Critères fixés avant exécution (par niveau, sur 2020/21-2025/26)

- **N1** : borne haute de l'IC 95 % de l'écart de log-loss C − F < 0. Bootstrap apparié par
  grappes ligue-saison (30 grappes), 2 000 tirages, graine 1.
- **N2** : log-loss C < F dans au moins 4 ligues sur 5.
- **N3** : |fréquence observée − probabilité moyenne| <= 0,03 dans chaque tranche de
  probabilité (10 tranches de 0,1) comptant au moins 500 matchs.
- Information (sans décision) : B − F, C − B, Brier, tranche P >= 0,60, effectifs.

## Décision prévue

- N1, N2, N3 tenus pour un niveau : ses coefficients (a, b) sont inscrits dans
  `syndicate.CALIBRATION_NIVEAUX` pour ce niveau ; les autres restent bruts.
- Le statut `RECALIBRE_EXP-012` (seul à permettre une décision GO) exige les trois niveaux
  validés. Sinon : statut `EXPERIMENTAL_NON_CALIBRE`, GO rétrogradé en SECURE.
- Aucune comparaison bookmaker ni conclusion de rentabilité : pas de cotes de marge exacte.

## Limites connues avant exécution

- Favori défini par le modèle, pas par le marché.
- Aucune absence ni composition : `data/` n'a pas de données joueurs.
- Une seule source de scores ; championnats seulement.
