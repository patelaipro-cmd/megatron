# EXP-021 — Signaux pré-match des victoires par 2+ (protocole préalable)

Statut initial : **exploratoire, sans activation dans le modèle de production**.
Protocole établi le 14/11/2026, avant toute exécution de cette expérience.

## Question et hypothèse

Chez les favoris en bonne forme, une succession de victoires **courtes** est-elle
un signal prédictif supplémentaire du fait de **ne pas gagner par 2+**, une fois
connue la probabilité de marge du modèle de référence ? Ne pas confondre
`P(victoire)` et `P(victoire par 2+)`.

## Données et anti-fuite

- `docs/experiences/EXP-009/variables.csv` : probabilités pré-match calculées
  chronologiquement avec Poisson-v5 ; `data.CURRENT` : scores à 90 minutes.
- La forme du favori se calcule dans **sa division**, sur les **cinq matchs
  immédiatement précédents**, strictement antérieurs **au jour** de la cible.
- Cohorte principale : au moins cinq matchs précédents, dont trois victoires ;
  indicateur = proportion des victoires par 2+ parmi ces victoires.
- Réglage du modèle : saisons 2008/09–2015/16. Validation descriptive :
  2016/17–2019/20. Test rétrospectif : 2020/21–2025/26, **déjà utilisé dans
  d'autres expériences MEGATRON** : ce n'est pas un test indépendant vierge.
- Pas de Coupes de France, d'écarts de divisions, de composition, de rotation,
  de blessures ou de sources journalistiques dans cette cohorte. Le cas
  Béthune–Nancy ne participe ni au réglage ni à l'évaluation.

## Modèles et critères figés

Référence : `P(2+)` de Poisson-v5 recalibrée par les coefficients EXP-012.
Candidat : même probabilité avec un **unique terme appris** :
`logit(p_candidat) = logit(p_reference) + beta × (ratio_2plus_recent - moyenne_train)`.
Le coefficient `beta` est appris sur 2008/09–2015/16 seulement, pénalité L2 = 5,
sans recherche d'hyperparamètres sur validation ou test.

Rapport obligatoire : effectifs, log-loss et Brier sur chaque période et par
tranche si possible ; différence candidat − référence. Critère de progression
exploratoire : baisse des deux scores en validation **et** test, et `beta`
cohérent avec l'hypothèse. Aucun passage en production sans cohorte future
indépendante, contrôles qualité et décision explicite.

## Autres signaux issus du cas Béthune–Nancy

Les contrôles de rotation, XI habituel, enjeu de Coupe, résistance passée à une
division supérieure, forme régionale et classement avant H2H sont ajoutés comme
**constats datés et vérifiables**. Aucun coefficient n'est appris pour eux en
l'absence de données historiques comparables et horodatées.

## Exécution

`python scripts/exp021_signaux_v2plus.py --sortie /tmp/exp021-resultats.json`

Les résultats d'exécution figurent dans une section séparée après ce protocole.

---

## Résultats — exécution du 14/11/2026

Commande : `python scripts/exp021_signaux_v2plus.py --sortie docs/experiences/EXP-021/resultats.json`.
12 887 observations éligibles (5 475 réglage, 2 831 validation, 4 581 test).
`beta = +0,077966`, coefficient **exploratoire non déployé**.

| Période | Log-loss référence | Candidat | Δ candidat − réf. | Brier référence | Candidat | Δ candidat − réf. |
|---|---:|---:|---:|---:|---:|---:|
| Réglage | 0,596448 | 0,596396 | −0,000053 | 0,204185 | 0,204153 | −0,000032 |
| Validation | 0,601204 | 0,601249 | **+0,000045** | 0,206894 | 0,206916 | **+0,000022** |
| Test rétrospectif | 0,603186 | 0,602999 | −0,000187 | 0,207337 | 0,207256 | −0,000081 |

**Verdict : non adopté.** Les deux mesures se dégradent en validation ; les
améliorations très petites sur le test ne satisfont pas le protocole fixé.
La cohorte de test n'est en outre pas indépendante des expériences MEGATRON
précédentes. L'effet additionnel de l'historique de marges n'est pas établi.
Conserver les marges passées comme **élément d'alerte à examiner**, sans
modifier les coefficients, la décision GO ou la mémoire. Les autres signaux
(rotation, Coupe, classement historique, données régionales) ne sont pas entraînés.
