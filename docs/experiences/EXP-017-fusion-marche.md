# EXP-017 : fusion poisson-v5-cal + marché contre le bookmaker seul

**Protocole figé le 29/10/2026 avant toute exécution.** Suite d'EXP-016 : le retard de v5-cal sur
le bookmaker (≈ 0,015 de log-loss en test) ne vient pas de la dynamique des forces. Question :
v5-cal apporte-t-il une information que les cotes n'ont pas ?

## Modèle `fus-v1` (pool log-linéaire, sans grille)

log p'_o = α · log v5cal_o + β · log book_o + c_o − log Z, avec c_A = 0, o ∈ {H, D, A}.
- v5cal : prévisions v5 d'EXP-008 recalibrées avec les coefficients EXP-010.
- book : 1/cote Bet365 (`OddHome/Draw/Away` de `data/`, football-data.co.uk), marge retirée
  proportionnellement (`models.bookmaker`).
- (α, β, c_H, c_D) estimés par maximum de vraisemblance (Newton) sur dev 2008/09-2015/16, matchs
  avec cotes. Prévisions v5 dev regénérées par `scripts/grille_multi.py` (config `270|2|0.35`). Le
  contrôle porte sur la cohorte commune avec les cotes, comme dans EXP-008 : 14 604 matchs, log-loss
  de référence 0,991185 (tolérance de reproduction `1e-5` pour les prévisions sérialisées).
- Un seul modèle, pas de choix de réglage : aucune sélection sur validation ni test.

## Périodes

Validation 2016/17-2019/20 ; test 2020/21-2025/26 ; matchs d'EXP-008 qui ont des cotes.

## Critères (fus-v1 − bookmaker), fixés avant exécution

- **M1** validation : borne haute IC 95 % (bootstrap apparié par match, 2 000 tirages, graine 1) < 0.
- **M2** test : même borne < 0.
- **M3** test : écart moyen < 0 dans au moins 4 ligues sur 5.
- **M4** test : RPS fus-v1 ≤ RPS bookmaker.
- Information : fus-v1 − v5-cal, poids α et β, calibration par tranches.

## Décision prévue

- M1-M4 tenus : v5 contient une information absente des cotes. `fus-v1` devient le candidat de
  référence 1X2 quand des cotes existent (PR séparée), à confirmer sur la cohorte prospective.
- Sinon : le marché est la référence 1X2 ; v5 n'ajoute rien de mesurable sur ce marché. Les
  étages suivants (xG EXP-018, contexte EXP-019) se jugent contre le bookmaker, pas contre v5.
- Aucun GO automatique, aucune probabilité de production modifiée par cette expérience.

## Limites connues avant exécution

- Cotes Bet365 relevées par football-data avant le match (vendredi ou mardi), pas les cotes de
  clôture : un marché plus tardif serait plus dur à battre.
- Test 2020-26 déjà vu par le projet.
- Une probabilité fusionnée qui ne bat pas le bookmaker n'a aucune valeur de pari.

## Résultats (exécution du 29/10/2026)

`python scripts/exp017_fusion.py --dev <prévisions v5 dev> --sortie docs/experiences/EXP-017`,
après `python scripts/grille_multi.py --saisons 2008/09,…,2015/16 --configs "270|2|0.35=270,2,0,moyenne,cadres,0.35" --sortie <prévisions v5 dev>`
(contrôle attendu : log-loss 0,991185 sur les 14 604 matchs avec cotes, à `1e-5` près).

**Audit du contrôle dev :** l'artefact de cette exécution indiquait 0,991192 alors que son contrôle
avait été calculé sur les 14 608 lignes v5, dont quatre sans cotes. Le comparateur EXP-008 porte
sur 14 604 matchs avec cotes. Le contrôle de `scripts/exp017_fusion.py` est corrigé pour imposer
cette cohorte exacte. Les prévisions v5 dev n'étant pas conservées dans le dépôt, le contrôle devra
être régénéré avec la commande ci-dessus avant de déclarer la reproduction confirmée. Les paramètres
et scores de fusion calculés sur les lignes avec cotes n'incluaient déjà pas ces quatre matchs.

**Verdict : REJETÉ (M1, M2, M3 non tenus). Le marché reste la référence opérationnelle 1X2.**

Poids appris sur dev : α (v5-cal) = −0,0076 ; β (bookmaker) = 1,0706 ; c_H = 0,0252 ; c_D = 0,0167.
Le coefficient de v5 est proche de zéro sur le dev. Cette expérience ne démontre toutefois pas
que v5 n'apporte aucune information : elle ne compare pas la fusion à un bookmaker recalibré seul.
Les critères préenregistrés montrent uniquement que la fusion testée ne bat pas significativement
le bookmaker brut. Le gain ponctuel observé ne peut pas être attribué au recalibrage des cotes sans
ce comparateur additionnel.

| fus-v1 − bookmaker [IC 95 %] | log-loss fus / book | RPS fus / book |
|---|---|---|
| validation (6 982) : −0,00056 [−0,00133 ; +0,00017] | 0,95358 / 0,95414 | 0,19198 / 0,19213 |
| test (10 953) : −0,00036 [−0,00094 ; +0,00021] | 0,97193 / 0,97229 | 0,19576 / 0,19588 |

Par ligue, test : F1 +0,0002 ; E0 +0,0004 ; D1 +0,0002 ; SP1 −0,0017 ; I1 −0,0007 (2/5).
Critères : M1 non ; M2 non ; M3 non ; M4 oui.

Conséquence : les étages suivants (xG, contexte, absences) se jugent contre le bookmaker. EXP-017
n'a pas établi de gain incrémental mesurable pour v5 sur le 1X2. Une comparaison future de v5 à un
bookmaker recalibré seul serait nécessaire pour isoler l'apport propre de v5. Une information peut
également être évaluée sur des marchés autres que le 1X2.
