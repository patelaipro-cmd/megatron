# EXP-020 : xg-v1 à la place de poisson-v5-cal pour le 1X2 statistique

Statut : **protocole figé le 30/10/2026, avant toute exécution**. Les résultats sont ajoutés dans une
section séparée, sans modifier le protocole.

## Question

EXP-018 a montré, hors critères, que xg-v1 (filtre dynamique d'EXP-016 nourri par les xG Understat)
bat poisson-v5-cal sur 2018-2026 (−0,0017 [−0,0031 ; −0,0002]). Le marché reste la référence 1X2
quand il existe (EXP-017, EXP-018). Question : le 1X2 de `StatsAgent` (utilisé quand il n'y a pas de
cotes, et comme base des marchés de buts) doit-il passer de poisson-v5-cal à xg-v1 recalibré ?

## Candidat `xg-v1-cal` (rien n'est réglé sur validation ni test)

- Filtre `megatron/dynamique.py`, réglage figé d'EXP-016 (q = 0,0001, q_saison = 0, P0 = 0,05,
  c = 0,15, sans correction) et w = 0,5 figé par EXP-018 : observation (1 − w) · buts + w · xG ;
  buts seuls avant 2014/15 et pour un match sans xG.
- Recalibration multinomiale p' ∝ p^b · exp(c) (même forme qu'EXP-010), (b, c_H, c_D) appris sur le
  seul dev.
- Données : xG Understat de la branche `donnees-externes` (`externe/understat/historique/`, run
  40953408635), reliées à `data/` comme EXP-018 (`relier`).

## Référence

poisson-v5-cal de production : prévisions v5 d'EXP-008 (colonne `candidat`), recalibrées par
`StatsAgent.CALIBRATION`. Calibration apprise sur 2008-2016, donc hors des périodes ci-dessous.

## Périodes (celles d'EXP-018)

Chauffe 2000/01-2014/15 ; dev 2015/16-2017/18 (recalibration) ; validation 2018/19-2020/21 ;
test 2021/22-2025/26. Tous les matchs des deux modèles, avec ou sans cotes.

## Critères (xg-v1-cal − v5-cal, log-loss 1X2), fixés avant exécution

- **Z1** validation : borne haute IC 95 % (bootstrap apparié, 2 000 tirages, graine 1) < 0.
- **Z2** test : même borne < 0.
- **Z3** test : écart moyen < 0 dans au moins 4 ligues sur 5.
- **Z4** test : RPS xg-v1-cal ≤ RPS v5-cal.
- Information : xg-v1 brut − v5-cal ; paramètres (b, c) ; calibration par tranches ; écart au
  bookmaker sur les matchs avec cotes.

## Décision prévue

- Z1-Z4 tenus : xg-v1-cal devient le candidat 1X2 statistique. Bascule de `StatsAgent` dans une PR
  séparée, **seulement quand une collecte xG de la saison en cours existe** (le filtre doit voir les
  xG de tous les matchs passés jusqu'au jour prévu) ; marchés 2+/3+ réappris sur xg-v1 dans une
  expérience à part. À confirmer sur la cohorte prospective (EXP-014).
- Sinon : poisson-v5-cal reste.
- Aucune probabilité de production modifiée par cette expérience, aucun appel LLM, aucune mémoire
  réelle touchée.

## Limites connues avant exécution

- Validation et test déjà vus : EXP-018 a publié xg-v1 − v5-cal sur 2018-2026. Les critères ne
  prouvent donc qu'une robustesse, pas une découverte hors échantillon ; la vraie preuve reste
  2026/27 (EXP-014).
- Understat peut avoir révisé ses xG après coup.
- Dev court (3 saisons) pour la recalibration.

## Résultats (exécution du 30/10/2026)

`python scripts/exp020_xg_v1.py --xg <externe/understat/historique> --sortie docs/experiences/EXP-020`
(~40 s). Liaison identique à EXP-018 : 21 471 matchs reliés, 117 non reliés, 1 score différent.
Recalibration apprise sur dev (5 478 matchs) : b = 1,0753 ; c_H = 0,0253 ; c_D = 0,0912.

**Verdict : REJETÉ (Z1 non tenu). poisson-v5-cal reste.**

| xg-v1-cal − v5-cal | validation 2018-21 (5 377) | test 2021-26 (8 907) |
|---|---:|---:|
| log-loss [IC 95 %] | −0,00111 [−0,00328 ; +0,00116] | −0,00324 [−0,00506 ; −0,00138] |
| RPS xg-v1-cal / v5-cal | 0,20051 / 0,20097 | 0,19897 / 0,20019 |
| xg-v1 brut − v5-cal | −0,00097 [−0,00332 ; +0,00138] | −0,00213 [−0,00396 ; −0,00022] |
| recalibration (cal − brut) | −0,00014 [−0,00112 ; +0,00085] | −0,00111 [−0,00183 ; −0,00040] |
| écart au bookmaker (matchs avec cotes) : xg-v1-cal / v5-cal | +0,0126 / +0,0137 | +0,0120 / +0,0153 |

Par ligue, test : F1 −0,0037 ; E0 −0,0020 ; D1 −0,0062 ; SP1 −0,0042 ; I1 −0,0009 (5/5 < 0).
Critères : Z1 non ; Z2 oui ; Z3 oui ; Z4 oui.

Lecture : le gain va dans le bon sens partout, net en test, mais la validation 2018-21 (saison
Covid incluse) ne l'établit pas. Selon la règle figée, pas de promotion. xg-v1-cal reste le
meilleur candidat statistique connu ; à reconsidérer avec la cohorte 2026/27 (EXP-014), ce qui
demande d'abord une collecte xG de la saison en cours.
