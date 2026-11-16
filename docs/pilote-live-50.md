# Préparation du pilote réel LIVE T+15 — V1 / V2

État au 16 novembre 2026 : **audit de couverture, pas pilote prospectif lancé**.
Le code du prototype LIVE de la PR #74 est expérimental et, par défaut, refuse
de convertir des preuves JSON déclaratives en probabilités ou WATCH réels.

## Audit reproductible des archives, sans écrire dans la mémoire

```sh
git fetch origin donnees-externes
python scripts/auditer_pilote_live.py --git-ref FETCH_HEAD --cible 50
```

Ou, si la branche externe est déjà extraite dans un dossier :

```sh
python scripts/auditer_pilote_live.py --dossier-externe ../megatron-externe/externe --cible 50
```

L'auditeur lit uniquement `externe/manifeste.json` et les CSV de
`externe/espn/compos/`. Pour chaque identifiant ESPN, il exige **deux XI de
11 titulaires distincts**, relevés **strictement avant le coup d'envoi** et
avant la date de l'audit. Il dédoublonne les captures, refuse dates sans fuseau,
captures futures, effectifs incomplets, identités de match incohérentes.

**Attention au changement de schéma :** les anciens CSV ne comportent pas
`domicile` et `exterieur` ; ils sont comptés séparément comme deux XI sans
orientation H/A vérifiée. L'étiquette ESPN n'est **pas** la validation d'une
composition par une source primaire officielle.

## Portes nécessaires avant un WATCH prospectif

| Porte | Preuve requise | En l'absence de preuve |
|---|---|---|
| 1. Couverture | Match futur et identifiant stable, horodatage Kinshasa | REFUS |
| 2. Baseline | V1 et V2 pré-match verrouillées avant le coup d'envoi | REFUS |
| 3. XI | XI confirmés en source primaire officielle, captures datées et comparaison aux XI attendus | REFUS |
| 4. Direct | Trois sources de score réellement indépendantes et fraîches, minute 12–18, vérification VAR/cartons | REFUS |
| 5. Calibration | Modèle LIVE validé hors échantillon et distinct du modèle pré-match | REFUS |
| 6. Immutabilité | Prévision originale archivée, nouvelle observation append-only, aucune réécriture de `memoire/` | REFUS |

Le pilote **50 matchs** sera prospectif : un match déjà joué ne peut être
« ajouté » comme prévision T-3h, T-5 ou T+15. Le dénominateur doit inclure les
REFUS aussi bien que les WATCH afin de mesurer la couverture réelle. Aucun
seuil de 60 % ne valide à lui seul une probabilité non calibrée au direct.

## Première source LIVE : ESPN, observation isolée

`scripts/collecter_score_t15_espn.py` interroge le calendrier JSON public ESPN
**uniquement** pour des fixtures ESPN pré-identifiées dont le coup d'envoi
référencé se situe à T+12 à T+18. Il exige que le fournisseur confirme encore
la première période, donne une minute cohérente et deux scores entiers. Il
capture l'identifiant du match, l'heure, le SHA-256 de la réponse et l'URL
publique du match. Une indisponibilité, un match absent, un conflit d'heure ou
une minute hors fenêtre sont consignés en `REFUS`.

Exemple de fichier de configuration (remplacer par des identifiants vérifiés et
des horaires réellement à venir, jamais par les identifiants de démonstration) :

```json
{"fixtures": [{"event_id": "<identifiant ESPN réel>", "ligue": "esp.2",
              "coup_envoi": "<date ISO avec fuseau>"}]}
```

Exécution ponctuelle au bon créneau :

```sh
python scripts/collecter_score_t15_espn.py --decouvrir --horizon-heures 24 --sortie-fixtures /tmp/fixtures_jour.json
# Nouveau relevé trois heures avant les prochains matchs :
python scripts/collecter_score_t15_espn.py --decouvrir --horizon-heures 3 --sortie-fixtures /tmp/fixtures_reelles.json
# Après le coup d'envoi, seulement durant les minutes 12 à 18 :
python scripts/collecter_score_t15_espn.py --entree /tmp/fixtures_reelles.json --journal /tmp/scores_t15_espn.jsonl
```

Le mode découverte couvre les ligues ESPN réellement configurées ainsi que
Ligue des nations, amicaux internationaux masculins/féminins et qualifications
EURO U21 publiées sur ESPN. Il balaie le calendrier jusqu'à 24 h, puis
resserre les contrôles des **trois heures à venir** ; il exclut les rencontres
déjà commencées et limite
la liste à 50 rencontres. Le fichier de découverte est créé sans écraser un
fichier existant ; chaque nouveau passage exige un nouveau nom de sortie.
La première commande peut légitimement trouver zéro rencontre, et la seconde
refuser toute fixture qui ne se trouve pas exactement à T+12–18.

**Ce n'est pas une boucle planifiée** et le programme n'extrait pas de contenu
Premium. ESPN est **une seule** famille de scores ; l'absence de confirmation
sur VAR et cartons rouges, la nécessité d'une source primaire pour les XI et
l'absence de modèle LIVE calibré imposent `REFUS` même avec un score ESPN valide.
Le journal est append-only dans un dossier externe à `memoire/` et `data/`.
Le compteur `score_sources_independantes` reste **0** tant qu'aucun score ESPN
valide n'a été capturé, y compris lorsque le contrôle est hors fenêtre ; il
devient 1 uniquement pour une capture effectivement validée par le décodeur.

## Planification des contrôles : créneaux connus, pas de tâche activée

Après une découverte authentifiée par l'empreinte SHA256 d'une réponse ESPN,
générer le plan de vérification de chaque fixture :

```sh
python scripts/planifier_controles_t15.py \
  --entree /tmp/fixtures_jour.json --sortie /tmp/plan_controles_jour.json
```

Le plan précise **T-3h, T-90, T-60, T-30, T-5, T+15**, en UTC et à Kinshasa.
Pour T+15, la cible est coup d'envoi +15 minutes et la fenêtre autorisée
s'étend de **+12 à +18 minutes**. Les rencontres simultanées sont découpées en
lots de cinq. Il refuse toute découverte ESPN sans empreinte de calendrier,
datée après le coup d'envoi, tronquée ou contradictoire. Une échéance manquée
devient `ECHEANCE_PASSEE_SANS_CAPTURE`, jamais un instantané reconstitué.

**Important :** `PLAN_MANUEL_NON_ACTIVE` signifie que le fichier d'horaires
est prêt ; aucun ordonnanceur ni surveillance de fond n'a été créé par la
commande. Aucun contrôle planifié ne démontre que le score ou les compositions
ont été réellement observés. L'activation future devra consigner l'heure
effective de chaque requête et accepter l'échec des fenêtres trop étroites.

### État de la collecte à vérifier à chaque passage

- ESPN : compositions historiques utilisables pour tester l'hygiène des données ;
  ce n'est pas un flux de score T+15 multi-source.
- FPL : statuts d'effectif seulement, pas un score LIVE indépendant.
- Apify/Sofascore : la collecte dépend de secrets GitHub Actions configurés par
  le titulaire du compte, pas de secrets copiés dans une conversation.
- API-Football : si l'API signale un compte suspendu, **ne pas contourner** ce blocage.
- 180Score/Xpertstats : ne compter comme sources LIVE que si une collecte
  autorisée, des réponses de score auditables et des horaires réels sont établis.

Les poids de MEGATRON, ses registres prospectifs et `main` restent inchangés
tant que ce pilote ne dispose pas de la chaîne complète et d'une validation
prédictive indépendante.
