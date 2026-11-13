# Boucle de domination : objectif minimum de cinq matchs

La boucle parcourt par lots le calendrier d'un instantané local du collecteur,
sans moteur de recherche ni collecte supplémentaire. Elle s'arrête à cinq
dominations confirmées ou à l'épuisement des rencontres accessibles. Elle ne
répète pas les mêmes données jusqu'à obtenir artificiellement un résultat.
Une nouvelle exécution avec un nouvel instantané reprend l'analyse des faits actualisés.
Ce programme ne constitue pas une surveillance en arrière-plan.

Une confirmation exige P(marge 2+) >= 60 %, décision GO sans blocage ni réserve
et validation de la zone GO dans le moteur. Le verrou `ZONE_GO_VALIDEE=False`
reste en place. Les matchs WATCH et les données manquantes ne sont jamais
promus pour remplir le quota. Un résultat inférieur à cinq rend le code 2,
avec le nombre manquant et les raisons. Le code 0 exige l'objectif atteint.

Les noms des équipes proviennent des correspondances recoupées dans l'audit
des résultats ou des alias déclarés ; aucun rapprochement par inclusion.
Les cotes 1X2 servent de contexte, jamais de probabilité indépendante ni de
preuve de rentabilité des marges. L'instantané doit dater de moins d'une heure
et être antérieur à l'analyse et au coup d'envoi. Les rencontres déjà commencées
et les noms explicitement SRL sont exclus. Le calendrier de cotes ne prouve pas
à lui seul l'absence de report : le contrôle préalable reste nécessaire au GO.

Exécution après récupération de la branche de données et recoupement des résultats :

```sh
python scripts/boucle_domination.py --instantane ../megatron-externe/externe/cotes/espn/2026-11-06/0804.csv --dossier-externe ../megatron-externe/externe --complement docs/boucles/2026-11-06/complement.csv --audit-resultats docs/boucles/2026-11-06/audit-resultats.json --objectif 5 --lot 10 --horizon-heures 72 --sortie docs/boucles/2026-11-06-domination.json
```

L'exemple utilise un instantané daté : une exécution ultérieure le rejettera
comme périmé. Remplacer son chemin par un instantané récent. Le complément
est passé explicitement : ni `data/` ni le registre réel ne sont modifiés.
L'horizon de balayage de 72 h n'autorise pas l'enregistrement anticipé d'une
prévision hors fenêtre. Aucune commande `controle`, aucun pari, aucun appel LLM.

## Exécution du 6 novembre 2026

Branche de données examinée : `8147d25`. Les résultats du lot du 6 novembre à
07:18 UTC ont été recoupés hors réseau : 202 résultats admis, tous confirmés
par ESPN et football-data, zéro quarantaine et zéro rejet. Il s'agit d'une mise
à jour des entrées, pas d'un réentraînement ou d'une validation supplémentaire.

Le calendrier collecté contient 23 matchs du 6 et du 7 novembre, tous analysés
en trois lots (10, 10, 3). Bilan : 12 PASS, 11 WATCH, zéro GO et aucun nom non
résolu après utilisation des correspondances de l'audit.

Un seul candidat dépasse le seuil numérique : PSG–Troyes, le 7 novembre à
21:05 Kinshasa, P(victoire)=88,04 %, P(marge 2+)=67,92 %, P(marge 3+)=43,82 %.
Statut WATCH : compositions non confirmées, angles morts incomplets, zone GO
non validée. Les quatre candidats suivants en marge 2+ sont Bayern à Mainz
(49,72 %), Roma–Sassuolo (47,61 %), Dortmund–Elversberg (44,48 %) et
Leipzig–Augsburg (42,18 %) : tous sous le seuil, non confirmés.

Le manifeste du collecteur signale API-Football suspendu et Apify ignoré faute
de secrets. Aucun secret n'a été affiché. Répéter ce calendrier sans nouvelles
données ne peut fournir cinq confirmations. Le résultat détaillé et les SHA256
des entrées sont conservés dans `boucles/2026-11-06-domination.json`.
