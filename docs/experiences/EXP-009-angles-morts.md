# EXP-009 : les angles morts mesurables améliorent-ils les 3 questions ?

Statut : **protocole figé le 29/10/2026, avant toute exécution**. Les résultats sont ajoutés dans une section séparée, sans modifier le protocole.

## Question

Cadre de Luloki (29/10/2026) : pour chaque match, 1) comment le favori peut-il perdre, 2) comment l'adversaire peut-il obtenir le nul, 3) qu'est-ce qui peut empêcher une victoire par deux buts ou plus. `megatron/angles_morts.py` calcule les angles mesurables avec `data/`. Ces indicateurs apportent-ils une information que `poisson-v5` n'a pas déjà ? Sinon, ils restent descriptifs : aucun ajustement de probabilité.

## Données

- `data.CURRENT` + `data/details_2000-2026.csv` (nouveau : mi-temps, rouges, corners, fautes, handicap ; même fichier source xgabora, SHA-256 `ef224cf2…4221` vérifié le 29/10/2026). Seule vérification faite avant ce protocole : taux de remplissage (≥ 99,8 % depuis 2008/09). Aucun score calculé.
- Elo et Form* de la source ne sont pas utilisés (date de calcul non documentée).

## Variables

Pour chaque match 2008/09 à 2025/26, avec le seul passé :

- favori = équipe au plus grand taux de buts `poisson-v5` (demi-vie 270, rétr. 2, w 0,35) ;
- p_q = probabilité `poisson-v5` de chaque question (score Poisson indépendant) ; issue_q = vrai/faux d'après le score final ;
- 12 indicateurs orientés (valeur > 0 = dans le sens de la surprise) : surperformance et calendrier du favori, progression de l'adversaire, adaptation H2H, fragilité défensive, repos, enjeu, favori à l'extérieur, corners, écart H2H trompeur, gestion du score, données manquantes. Indicateur non calculable = 0.

## Modèles (par question, ajustés sur le développement seulement)

- **B** (référence) : logistique `a + b · logit(p_q)` : `poisson-v5` recalibré.
- **A** : B + les 12 indicateurs centrés-réduits (moyenne et écart-type du développement), pénalité L2 λ = 1 sur les seuls coefficients des indicateurs.
- **A_i** (information) : B + un seul indicateur i.

Développement 2008/09-2015/16, validation 2016/17-2019/20, test 2020/21-2025/26 (5 ligues réunies). Le test recoupe des saisons vues par EXP-001/004/008 pour le 1X2, jamais pour ces indicateurs.

## Critères fixés avant exécution (pour chaque question)

- **Q1** : validation, borne haute IC 95 % (bootstrap apparié, 2 000 tirages, graine 1) de l'écart de log-loss A − B < 0.
- **Q2** : test, même borne < 0.
- **Q3** : test, écart moyen A − B < 0 dans au moins 4 ligues sur 5.
- **Angle confirmé** (information, par indicateur et question) : coefficient > 0 sur le développement et borne haute IC 99 % de A_i − B sur le test < 0 (99 % car 36 comparaisons).
- Information : référence bookmaker pour la question 3 (handicap asiatique −1,5 du favori, sans remboursement possible), calibration.

## Décision prévue

- Q1, Q2, Q3 tenus pour une question : le modèle A de cette question est enregistré (`angles-v1`) ; un scénario peut alors porter un ajustement en citant EXP-009.
- Sinon pour cette question : les angles restent descriptifs (fait + source + mécanisme), probabilité `poisson-v5` inchangée.

## Limites connues avant exécution

- Seuls 11 des 13 angles ont un indicateur, souvent partiel (pas de joueurs, compositions, coupes, minute des buts, tactique).
- Même source de données ; favori défini par le modèle, pas par le marché.
- Un effet linéaire par indicateur ; pas d'interactions.

---

## Résultats (exécution du 29/10/2026, ajoutés après le protocole)

Commandes : `python scripts/exp009_angles.py extraire --sortie docs/experiences/EXP-009` puis `evaluer`. 32 544 matchs (dev 14 608, validation 6 982, test 10 954). Détail : `EXP-009/resultats.json`, variables : `EXP-009/variables.csv`.

Log-loss, A − B [IC 95 %] :

| Question | Fréquence test | Dev | Validation (Q1) | Test (Q2) | Ligues < 0 (Q3) |
|---|---|---|---|---|---|
| Défaite du favori | 0,221 | −0,0017 [−0,0027 ; −0,0008] | +0,0002 [−0,0012 ; +0,0016] | −0,0005 [−0,0017 ; +0,0006] | 3/5 |
| Nul | 0,253 | −0,0005 [−0,0010 ; 0,0000] | −0,0003 [−0,0011 ; +0,0004] | +0,0001 [−0,0005 ; +0,0007] | 3/5 |
| Pas de victoire par 2+ | 0,714 | −0,0018 [−0,0028 ; −0,0009] | −0,0002 [−0,0017 ; +0,0013] | +0,0005 [−0,0006 ; +0,0017] | 2/5 |

Le gain du développement ne se retrouve ni en validation ni en test : surajustement.

Angles confirmés (coefficient dev > 0 et IC 99 % test < 0), sur 36 comparaisons :

- Défaite du favori : **coups de pied arrêtés** (corners) −0,0008 [−0,0015 ; −0,0001].
- Nul : **fragilité défensive** −0,0003 [−0,0006 ; 0,0000].
- Aucun pour la question 3. Tous les autres : IC 99 % contenant 0.

Information :

- Référence bookmaker question 3 (handicap −1,5 du favori, 590 matchs du test) : bookmaker 0,6939, A 0,7021, B 0,7051.
- `poisson-v5` recalibré seul (B) bat `poisson-v5` brut sur le test pour la défaite (0,5106 contre 0,5127) et le nul (0,5605 contre 0,5611) : pente > 1, v5 trop prudent sur ces questions. Piste à part, nouveau protocole.

## Décision

- Q1, Q2 et Q3 non tenus pour les 3 questions : **pas d'`angles-v1`**. Les angles restent descriptifs (fait + source + mécanisme) ; probabilités `poisson-v5` inchangées ; aucun scénario ne porte d'ajustement.
- Les 2 angles confirmés ont un effet minuscule (< 0,001) : notés, pas utilisés pour ajuster.

## Limites

- Indicateurs partiels : les angles les plus sportifs (joueurs, compositions, tactique, coach, coupes, minute des buts) ne sont pas mesurables avec `data/`. Ce résultat ne dit pas qu'ils sont inutiles, seulement que les proxies disponibles n'ajoutent rien au modèle.
- Même source ; un effet linéaire par indicateur.
