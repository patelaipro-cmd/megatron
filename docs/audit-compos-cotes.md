# Audit descriptif des compositions et des cotes

Cet outil contrôle si les données permettent une comparaison ; il ne mesure
ni avantage prédictif, ni rentabilité. Il ne lit pas les scores des modèles de
la cohorte EXP-021 et ne modifie aucune mémoire.

```sh
python scripts/auditer_compos_cotes.py --dossier-externe <copie-donnees-externes/externe> --sortie <rapport.json>
```

Seules les sources ESPN sont rapprochées : même identifiant d'événement,
division et coup d'envoi. La première capture contenant exactement onze
titulaires distincts pour chacune des deux équipes fournit un repère
d'observation. Une liste partielle, répétée ou tardive ne suffit pas.

Pour chaque bookmaker, l'outil prend la dernière cote courante strictement avant
ce repère et la première strictement après, à au plus 90 minutes de chaque côté,
toutes deux collectées avant le coup d'envoi et avant la date d'audit.
Une cote d'ouverture n'est jamais substituée à une capture antérieure.
Des cotes contradictoires à l'instant sélectionné excluent la série.
Les probabilités implicites sont normalisées sur H/D/A pour retirer
proportionnellement la marge. Les mouvements sont exprimés en points signés,
avec les dates et les deux distributions ; plusieurs bookmakers ne multiplient
pas le nombre de matchs indépendants.

**Ce repère n'est pas l'heure de publication officielle.** L'heure de mise à jour
chez le bookmaker reste également inconnue. Il faut collecter la publication
officielle horodatée avant d'étudier un effet autour de sa publication ; cet
audit ne permet aucune attribution causale.

Corners et cartons ne figurent pas dans les instantanés 1X2 utilisés. Ils restent
non évalués ; aucun zéro n'est substitué à une donnée manquante. Le journal de
cinq matchs cité dans le bilan utilisateur n'a pas été identifié dans ce dépôt.

## Première exécution — 30 octobre 2026

Code basé sur main `fa9a880`, données externes `e077f16` : quatre matchs avec deux
onze complets, 27 séries de cotes courantes, **zéro match apparié**. Les quatre
matchs avec compositions n'ont pas de cote courante correspondante dans les
captures disponibles. La couverture est donc insuffisante pour estimer un
mouvement autour des compositions. Les pourcentages du bilan utilisateur n'ont
pas été reproduits dans ce contrôle.

La suite requiert des captures antérieures et postérieures pour les mêmes
événements, puis une source donnant l'heure de publication officielle. Les
règles d'extraction doivent être figées avant leur mesure sur un nouvel
échantillon. Les seuils EXP-014, EXP-013 et EXP-021 restent inchangés.

## Reprise Codex — collecte et diagnostic

Le lecteur refuse un dossier source absent/sans CSV et un schéma incomplet.
Il fournit un inventaire fichiers/lignes et le motif par série (identité discordante,
composition incomplète, absence avant/après, contradiction). Un fichier présent
mais vide reste identifié par son inventaire, distinct d'une source absente.

Les nouvelles compositions portent `source=espn`, les cotes `marche=1X2`.
Pour l'ancien schéma, le lecteur CLI attribue la provenance uniquement depuis
le chemin dédié `espn/compos`, et compte ces lignes dans
`entrees.compos.source_legacy`. La fonction `auditer` exige une source explicite.
Le marché des anciens triplets H/D/A est documenté et compté dans
`lignes_cotes_schema_legacy_1x2` ; un autre marché explicite est exclu.

Les contradictions sont comparées sur les cotes brutes avant normalisation.
Chaque paire exporte les triplets, surcotes et distributions, avec
`publication_officielle_le=null` tant que cette information manque.

Les collecteurs ESPN et API-Football ne marquent plus une composition terminée
avant deux onze complets distincts. Les réponses partielles restent conservées
et pourront être retentées au passage suivant dans le quota existant. Une erreur
de réponse ESPN ne fait plus perdre les compositions des autres matchs.
Le collecteur de cotes garde chaque capture courante à moins de 75 minutes,
même si l'horizon est déjà renseigné. Le comportement horaire au-delà de cette
fenêtre et pour l'ouverture reste inchangé.

Aucun workflow n'est déclenché ou modifié, aucun quota augmenté, aucun état
historique réparé artificiellement. La cadence horaire des compositions peut
encore manquer des publications ; les dates de réponse réelles chez le fournisseur
restent inconnues. La correction ne crée aucune paire dans les anciennes données.

Preuves : [reprise du 30 octobre](entrainement/audit-compos-cotes-reprise-20261030/rapport.md).
