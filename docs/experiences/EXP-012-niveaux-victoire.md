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

---

## Résultats (exécution du 29/10/2026, ajoutés après le protocole)

Commande : `python scripts/exp012_niveaux.py --sortie docs/experiences/EXP-012` (44 s).
32 544 matchs, 0 exclu (réglage 14 608, calibration 6 982, test 10 954) ; `variables.csv` SHA-256 `52ce2b08c769…`.
Détail : `EXP-012/resultats.json`.

Test 2020/21-2025/26, log-loss (fréquence observée) :

| Niveau | Fréquence | F fréquences | B v5 brut | C v5 recalibré | C − F [IC 95 %] | C − B [IC 95 %] | Ligues C < F |
|---|---|---|---|---|---|---|---|
| Victoire simple | 0,525 | 0,6918 | 0,6626 | 0,6621 | −0,0297 [−0,0336 ; −0,0259] | −0,0004 [−0,0014 ; +0,0006] | 5/5 |
| Victoire par 2+ | 0,286 | 0,5987 | 0,5693 | 0,5692 | −0,0295 [−0,0339 ; −0,0255] | −0,0000 [−0,0004 ; +0,0003] | 5/5 |
| Victoire par 3+ | 0,134 | 0,3944 | 0,3715 | 0,3718 | −0,0226 [−0,0266 ; −0,0189] | +0,0002 [−0,0003 ; +0,0007] | 5/5 |

Platt (calibration 2016/17-2019/20) : victoire a = 0,0791, b = 1,1736 ; 2+ a = 0,0902, b = 1,0849 ;
3+ a = 0,0245, b = 0,9647.

N3 (tranches d'au moins 500 matchs) : tenu pour les trois niveaux avec C. Sans recalibration, B
sous-estime la victoire simple dans la tranche 0,6-0,7 (0,644 annoncé, 0,699 observé, 1 570 matchs).

Zone de décision (information) : P(2+) >= 0,60 avec C : 216 matchs du test, 0,670 annoncé,
0,625 observé. Tranche de moins de 500 matchs : non validée (règle du protocole v0).

## Décision

- N1, N2, N3 tenus pour les trois niveaux : coefficients inscrits dans
  `syndicate.CALIBRATION_NIVEAUX`, statut `RECALIBRE_EXP-012`.
- La recalibration n'apporte presque rien au-delà du brut (C − B non significatif) ; son seul
  apport net est la calibration de la victoire simple au-dessus de 60 %.
- La zone GO (P(2+) >= 60 %) n'est pas validée : `syndicate.ZONE_GO_VALIDEE = False`, GO reste
  rétrogradé en SECURE. Activation automatique toujours désactivée.

## Limites

- Test rétrospectif sur des saisons déjà vues par le projet (1X2) ; une cohorte prospective
  horodatée (prévisions enregistrées avant match par `syndicate controle`) reste indispensable.
- Battre les fréquences ne dit rien de la rentabilité : aucune cote de marge exacte comparée.
- Favori défini par le modèle ; aucune absence ni composition dans ces données.
