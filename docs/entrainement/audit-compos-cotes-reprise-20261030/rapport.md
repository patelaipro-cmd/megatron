# Audit compositions/cotes — reprise Codex du 30 octobre 2026

## Base et protection du protocole

`origin/main` actualisé : `fa9a8809f4ecb000cf0ee79d4e1b5e07757f114a`.
AGENTS.md, checkpoint et dernières décisions relus. La vérification
`python -m megatron synchro verifier --reference origin/main` retourne 0,
sans erreur ; alerte préexistante checkpoint 10 performances / mémoire 13.
Aucune correction du checkpoint ni de la mémoire n'a été faite.

Le correctif `14d63b816af2eee770bc0c71091eb34a81afee54` n'est pas ancêtre de
main et `git cherry` le marque `+` ; le fichier d'audit était absent de main.
Import du bundle vérifié, puis branche `codex/fiabiliser-audit-compos-cotes-20261030`.
La recherche GitHub ne trouve aucune PR pour la branche d'origine au contrôle.

La branche de données a été récupérée par Git, jamais fusionnée. Seuls les
fichiers compositions, cotes et manifeste ont été extraits pour cette analyse.
Aucun score EXP-021 ni résultat de cette cohorte n'a été consulté. Aucun modèle,
paramètre, seuil EXP-013/014/021 ou probabilité de production n'a été modifié.
Les totaux 2+/3+ restent distincts des marges de victoire 2+/3+.

## Données et couverture reproduites

Commit de données figé : `257675b0e294528c0dc4a8f9c7f3e2168fa0860a`.
Date d'audit : **30 octobre 2026, 09:08:44 UTC / 10:08:44 Kinshasa**.
Le [rapport JSON](audit.json) est une nouvelle exécution, sans remplacer
le rapport historique du premier audit.

| Source examinée | Fichiers CSV | Lignes | Portée |
|---|---:|---:|---|
| ESPN compositions | 4 | 180 | 4 matchs, deux onze complets chacun |
| ESPN cotes | 5 | 226 | 113 courantes + 113 ouvertures ; 27 séries/matchs |
| football-data cotes | 1 | 89 | Source distincte, pas d'identifiant ESPN validé |
| API-Football compositions | 1 | 41 | Source distincte, correspondance ESPN non établie |

**Zéro paire match/bookmaker**, zéro match apparié. Les 27 séries n'ont pas de
composition complète correspondante ; les 4 compositions n'ont aucune cote
courante correspondante. Les 31 identités d'événements de l'union sont distinctes.

Causes observées, sans attribution spéculative aux bugs :

- Atlético-MG–Cruzeiro (`401841288`), Flamengo–Vasco (`401841292`) et
  Athletico Paranaense–Grêmio (`401841290`) sont en BRA. Le collecteur de cotes
  ne couvre que E0/F1/D1/SP1/I1 : aucune couverture BRA n'est promise.
- Atalanta–Fiorentina (`401874969`) débute le 29 octobre à 19:45 UTC ; sa
  composition est observée à 19:17:28. La première capture de cotes ESPN disponible
  date de 21:11 UTC, après le coup d'envoi : elle ne peut fournir une paire valide.
- Les cotes des 27 autres matchs concernent des rencontres du 30/31 octobre,
  alors que les compositions disponibles concernent les quatre événements ci-dessus.
  Il ne s'agit pas de variations de noms autorisant un rapprochement approximatif.

### Corners et cartons, contrôlés séparément

[Mesure de couverture](couverture.json) : aucun champ corners ou cartons dans
les neuf CSV ESPN examinés. Pour chacun : **0 événement couvert sur 31**,
état `manquant`, valeur `null`. Le zéro est un compte de couverture,
jamais une valeur sportive imputée.

Le dépôt contient par ailleurs `data/details_2000-2026.csv` : 45 559 lignes historiques,
dont 40 271 avec les deux champs corners non vides et 40 661 avec les deux champs
cartons rouges non vides. Les cartons jaunes ne sont pas présents dans ce schéma.
Ces comptes portent sur des statistiques historiques après match, pas des cotes
de corners/cartons ni une couverture pré-match des 31 événements. Les colonnes
de scores n'ont pas été utilisées. Empreinte du fichier dans `couverture.json`.

### Source du bilan cinq matchs / Fantacalcio

Non identifiée : recherche dans documentation, scripts, tests, README (hors
EXP-021), messages de commits et recherche GitHub issues/PR pour `Fantacalcio`
et `cinq matchs`. Aucun bilan source retrouvé ; la mention dans la documentation
de l'audit est seulement le constat de cette absence. Aucun pourcentage de ce
bilan n'est repris. Il faut son fichier, lien ou message d'origine pour aller plus loin.

## Corrections reproductibles

1. Rejeter sources absentes et schémas incomplets au lieu d'un rapport vide réussi.
2. Contrôler source des compositions et marché explicite, tracer la compatibilité
   avec le schéma historique et détailler chaque motif de non-appariement.
3. Comparer les contradictions sur les triplets bruts : (2,3,4) et (4,6,8) ne deviennent
   pas compatibles parce que leurs probabilités normalisées sont identiques.
4. Ne pas arrêter la collecte sur une composition partielle ou des joueurs dupliqués
   (ESPN/API-Football) ; rester strictement avant coup d'envoi, dans le budget existant.
5. Préserver les compositions ESPN déjà collectées lorsqu'un autre événement échoue.
6. Conserver les captures de cotes successives dans un même horizon ; rejeter les
   événements déjà commencés malgré un statut `pre` périmé, les statuts explicitement
   annulés/reportés et les cotes américaines non finies.

Les tests utilisent uniquement des lecteurs injectés et des dossiers temporaires.
Un cas de bout en bout vérifie deux captures dans T−60, autour d'une composition,
sans inventer de mouvement lorsque les cotes sont identiques.

## Validation effectuée

- 34 tests ciblés : `python -m unittest tests.test_auditer_compos_cotes tests.test_collecte_cotes tests.test_collecte_externe -v`.
- `python scripts/valider_acces.py --acces codex` : 228 tests réussis,
  parcours fictif complet réussi, synchronisation valide, mémoire inchangée.
- Réseau Python bloqué pendant la validation par un audit hook local refusant
  `socket.connect` et `socket.getaddrinfo`, hérité par les sous-processus Python.
- Aucun appel LLM ou fournisseur sportif, aucune modification du jeton, des données
  sources ni des probabilités de production. Les accès réseau de la session sont Git/GitHub.

## Limites et prochaine vérification

Le manifeste externe de 06:16:55 UTC signale Sofascore 403 et ClubElo 502 ; ce sont
des erreurs enregistrées, pas des appels reproduits ici. Aucun contournement tenté.
La disponibilité historique d'API-Football ne constitue pas une nouvelle autorisation
d'appel : aucune requête payante ni requête utilisant une clé n'a été lancée.

Après revue et intégration par le responsable, vérifier sur les nouvelles captures
si les mêmes événements disposent enfin de deux onze et de cotes du même bookmaker
strictement avant/après le repère, toujours avant coup d'envoi. Rejouer l'audit avec
un commit de données et une date figés, puis contrôler séparément l'heure officielle
de publication si une source la fournit. Ne pas étendre BRA ni la cadence des sources
sur la base de cet audit sans décision explicite. Aucun avantage bookmaker n'est établi.
