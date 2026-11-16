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
