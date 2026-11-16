# SYNDICATE LIVE — prototype T+15 (V1 et V2 séparés)

Statut : **exploratoire, non calibré, non déployé automatiquement**.

## Règles temporelles

1. **T-180 à T-1** : collecte et contrôles pré-match inchangés. Les prévisions
   enregistrées avant le coup d'envoi restent gelées et évaluables après le match.
2. **T+15** : un état daté distinct est accepté si l'horloge est entre les minutes
   12 et 18, si le score provient d'au moins trois sources déclarées concordantes,
   s'il date de moins de trois minutes, et si les compositions officielles ont
   été déclarées confirmées et compatibles avec la référence prématch.
3. Carton rouge, VAR en cours, désaccord de sources, score trop ancien, XI
   différent ou taux prématch absents → **REFUS**, aucune probabilité recalculée.
4. **V1** : probabilités brutes 1X2 et victoire d'un côté par ≥2 / ≥3 buts d'écart.
   **V2** : Over 1,5 / 2,5 / 3,5 fin de match, Over par mi-temps et répartition
   attendue MT1/MT2. La nomenclature des marchés reste distincte.
5. Les valeurs V1/V2 étant **non calibrées en direct**, leur affichage donne
   seulement `WATCH_EXPERIMENTAL_SEULEMENT`, jamais GO/SECURE. Il n'y a aucune
   modification des poids historiques, de `megatron/syndicate.py` ou du registre
   `memoire/performances.jsonl`.

## Hypothèse calculée

La moyenne de buts prématch `lambda_H`, `lambda_A` est déterminée uniquement
avec des faits antérieurs au coup d'envoi, puis figée. Le modèle suppose que,
durant les `90 - minute` minutes restantes, chaque équipe marque selon une
loi de Poisson indépendante de moyenne `lambda_equipe × (90-minute)/90`.
Le score déjà observé est ajouté aux futurs buts et les probabilités
événementielles sont sommées sur la grille de scores futurs.

Pour les mi-temps au moment T+15, MT1 couvre les buts déjà marqués et
les trente minutes restantes de la première période ; MT2 couvre les
45 minutes théoriques de seconde période. Le temps additionnel n'est pas
estimé dans ce prototype.

**Attention :** c'est un calcul conditionnel opérationnel, pas une preuve
que les probabilités directes sont prédictives. Le score, le style, la fatigue,
les remplacements et les changements tactiques peuvent modifier les intensités.
Les coefficients de calibration acquis sur des données **prématch** (EXP-012,
EXP-019) **ne sont pas réutilisés en live**.

## Entrée et commande

```bash
python -m megatron live-t15 tests/fixtures/live_t15_demo.json
# journal dédié choisi explicitement ; jamais performances.jsonl
python -m megatron live-t15 tests/fixtures/live_t15_demo.json --journal /tmp/live_t15.jsonl
python -m megatron veille-live planifier --coup-envoi 2026-11-16T20:00:00+01:00
python -m megatron veille-live assembler --entree tests/fixtures/veille_live_demo.json
```

L'exemple est entièrement **fictif** ; la présence de sources dans le JSON
ne signifie pas que le programme les vérifie en ligne. Le journal ne s'écrit
que pour les snapshots `WATCH` et refuse les doublons identiques.
La sortie distingue `observed_at` de `calcule_le` et classe toute analyse
rejouée plus de cinq minutes après son observation `REJEU_NON_PROSPECTIF`.
Un rejeu n'est **jamais** une prévision horodatée avant son résultat final.

La commande `veille-live` expose cinq jalons T-3h/T-60/T-30/T-5/T+15. Elle
**calcule les horaires mais ne crée pas de tâche planifiée**. L'action `assembler`
réunit trois relevés de score distincts déclarés, vérifie leurs timestamps,
compare les XI présentés comme officiels avec la référence anticipée, puis
transmet l'instantané validable au calculateur T+15. Toute différence ou
absence de preuve donne REFUS. La confiance dans le contenu des pages n'est
pas attestée par cette passerelle : seuls des extracteurs réels et une
vérification des publications peuvent transformer les exemples en faits.

La sonde publique `scripts/capturer_sources_live.py` capture les statuts HTTP,
horodatages, empreintes SHA-256 et URLs de pages nommées SportsMole,
SportsGambler, PianetaFanta, 180Score, Xpertstats ou Sofascore. Elle refuse
les URLs avec secrets et n'extrait ni XI, ni buts, ni chiffres des abonnements.
Elle conserve les échecs HTTP : une sonde inaccessible ne devient pas une
source confirmée. Les liens de la fixture fictive ne prouvent aucun match réel.
`SONDE_RESEAU` teste seulement l'accès au domaine. Les véritables contrôles
T-3h/T-60/T-30/T-5/T+15 exigent l'heure réelle du coup d'envoi et refusent
toute capture réalisée hors de leur fenêtre.

## Validation exigée avant décision réelle

- Collecter des séquences historiques horodatées : score, minute, XI, cartons,
  événements, et résultat final, sans informations postérieures au snapshot.
- Pré-enregistrer l'expérience : split chronologique train/validation/test,
  log-loss/Brier/calibration par marché, comparaison avec probabilités
  live de marché dé-margées et référence naïve.
- Tester explicitement les matchs de Coupe, équipes B/jeunes/féminines et
  les faux favoris ; mesurer refus et défauts de couverture.
- Développer et calibrer un modèle d'intensité dépendant du temps et des
  événements avant d'autoriser la substitution de ce calcul au signal WATCH.
- Faire inspecter les sources réelles et le raccordement de la collecte T-180
  (SportsMole, SportsGambler, PianetaFanta, 180Score, Xpertstats) au JSON.
