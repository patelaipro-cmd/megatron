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
