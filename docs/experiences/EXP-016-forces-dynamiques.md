# EXP-016 : forces d'équipes dynamiques (filtre d'état) contre poisson-v5-cal

Statut : **protocole figé le 29/10/2026, avant toute exécution**. Étage 1 du schéma
« MEGATRON : schéma d'apprentissage avancé ». Résultats ajoutés dans une section séparée.

## Question

Remplacer l'oubli fixe de `poisson-v5` (demi-vie 270 j, rétrécissement 2) par un filtre d'état,
où l'attaque et la défense de chaque équipe dérivent dans le temps et sont mises à jour après
chaque match, améliore-t-il le 1X2 sur des saisons non utilisées pour le régler ?

## Modèle `dyn-v1` (`megatron/dynamique.py`)

- Par équipe : log-attaque a et log-défense d, gaussiennes N(m, P). Par ligue : intercept μ et
  avantage du terrain h, mis à jour par le même filtre avec une variance de dérive faible.
- λ_dom = exp(μ + h + a_dom + d_ext), λ_ext = exp(μ + a_ext + d_dom).
- Entre deux matchs d'une équipe : P += q · jours ; au 1er juillet : P += q_saison (mercato).
- Après un match : mise à jour de Laplace (Kalman étendu, lien log, Poisson) de (a_dom, d_ext)
  par les buts du domicile et de (a_ext, d_dom) par ceux de l'extérieur. Observation : pseudo-buts
  (1 − w) · buts + w · k · tirs cadrés, k = rapport buts / tirs cadrés de la ligue sur le seul passé
  (même proxy que v5).
- Équipe nouvelle dans la ligue : a = −c, d = +c (promu plus faible), variance P0.
- Prévision d'un jour : états d'avant ce jour seulement (aucune fuite), matrice Poisson 0-10,
  correction de variance exp(m + P/2) en option de grille.

## Données et périodes

`data/matches_top5_2000-2026.csv` (5 ligues). Le filtre tourne depuis 2000/01 (chauffe), sans
regarder l'avenir. Réglage 2008/09-2015/16 (dev) ; recalibration 1X2 p'∝p^b·exp(c) (forme EXP-010)
apprise sur dev ; validation 2016/17-2019/20 ; test 2020/21-2025/26. Comparateur : `poisson-v5-cal`
(prévisions v5 d'EXP-008, coefficients EXP-010), sur exactement les mêmes matchs.

## Grille de réglage (dev seulement, log-loss 1X2, 5 ligues réunies)

q ∈ {0,0002 ; 0,0005 ; 0,001 ; 0,002}, q_saison ∈ {0 ; 0,01 ; 0,03}, P0 ∈ {0,05 ; 0,15},
w ∈ {0 ; 0,35}, c ∈ {0 ; 0,15}, correction de variance ∈ {non, oui} : 384 réglages. Le meilleur est figé.
Si l'optimum touche un bord de q, la grille est étendue d'un cran une seule fois, sur dev seulement.

## Critères (dyn-v1-cal − v5-cal), fixés avant exécution

- **D1** validation : borne haute IC 95 % (bootstrap apparié par match, 2 000 tirages, graine 1) < 0.
- **D2** test : même borne < 0.
- **D3** test : écart moyen < 0 dans au moins 4 ligues sur 5.
- **D4** test : RPS dyn-v1-cal ≤ RPS v5-cal.
- Information : écart au bookmaker, calibration par tranches, niveaux de victoire 1 / 2+ / 3+.

## Décision prévue

- D1-D4 tenus : `dyn-v1-cal` devient le **candidat** au 1X2 de l'agent Stats, proposé par PR
  séparée (pas de bascule automatique), et reste à confirmer sur la cohorte prospective.
- Sinon : v5-cal reste ; les résultats orientent l'étage suivant.
- Aucun GO automatique, aucune probabilité de production modifiée par cette expérience.

## Limites connues avant exécution

- Test 2020-26 déjà vu par le projet (choix de v5) : pas un test vierge.
- Approximation gaussienne du filtre ; aucune absence, coupe ni cote dans le modèle.
