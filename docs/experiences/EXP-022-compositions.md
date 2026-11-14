# EXP-022 — Compositions prématch et hypothèses de rotation

État : **collecteur/lecteur expérimental sur branche Codex**. Aucun entraînement de
coefficient, aucun ordre de pari, aucun changement dans `syndicate.niveaux` ou dans
`memoire/`. Le protocole expérimental précède toute évaluation d'un effet V+2.

## Les données et leur statut

| Famille | Utilisation | Limite vérifiée |
|---|---|---|
| [SportsGambler](https://www.sportsgambler.com/lineups/football/) | XI **probables** ; XI annoncés « confirmed » étiquetés **confirmés par le fournisseur** | Pas de preuve que le site soit l'auteur officiel ; aucun connecteur HTML testé sur serveur |
| [PianetaFanta](https://www.pianetafanta.it/probabili-formazioni-fantacalcio) | XI **probables**, banc et indisponibles de Serie A | Pas une source officielle de composition ; accès HTML direct du runtime non vérifié |
| Sofascore/Apify | Convertir les CSV de `externe/sofascore*` avec deux XI complets | Historique de captures insuffisant ; la date de publication est inconnue |
| ESPN / API-Football | Convertir les CSV `externe/espn/compos`, `externe/apifootball/compos` | Les **nouveaux CSV seulement** indiquent `domicile` et `exterieur` ; les anciens sans orientation sont écartés |
| Club/ligue/fédération officiels | Saisir la feuille officielle avec URL, organisme et capture | La validation automatique ne garantit pas que l'URL appartient réellement à l'organisme ; vérifier manuellement |

SportsGambler et PianetaFanta sont actuellement des **sources de saisie structurée
à partir d'une fiche effectivement consultée**. Aucune extraction de leurs XI en
direct, aucune permission de republication et aucune couverture de calendrier
ne sont revendiquées. Les CSV existants se lisent localement **sans réseau**.

## Contrat d'une fiche

Un JSON par capture, avec :

- `match_id` stable et préfixé par source (`sofa:…`, `espn:…`, `apifootball:…`),
  `domicile`, `exterieur`, `competition`, `coup_envoi` ISO avec fuseau ;
- `collecte_le` = horodatage **réel de la consultation**, `publie_le` = date
  originale **seulement si affichée et vérifiée**, sinon `null` ;
- `source` = `sportsgambler`, `pianetafanta`, `sofascore`, `espn`,
  `api-football` ou `officiel`, `source_url` HTTPS ;
- `statut` = `probable`, `confirmee_fournisseur` ou `confirmee_officielle`.
  Le statut officiel direct requiert `source: officiel` et `organisme` ;
- `equipes.H` et `equipes.A` : tableaux `titulaires` (11 au plus), `banc`,
  `absents`, et éventuelle `formation`. Un joueur peut être une chaîne ou
  `{ "nom": "…", "id": "…", "poste": "…" }` ; les XI confirmés doivent être
  complets. La cause d'absence ne doit pas être devinée.

La création d'un fichier JSON ne prouve pas à elle seule la consultation de la
source : le collecteur vérifie la cohérence, **pas l'authenticité externe**.

## Commandes (hors registre réel)

```bash
# Saisie d'une fiche *réellement lue* sur le site : ne pas antidater.
python scripts/exp022_compositions.py ajouter --fiche /tmp/fiche-observee.json \
  --archive /tmp/exp022-xi.jsonl

# Lecture des instantanés de la branche de collecte externe existante.
python scripts/exp022_compositions.py importer-externes \
  --dossier /tmp/megatron-externe/externe --archive /tmp/exp022-xi.jsonl

# Retour descriptif au moment T-5 (même si l'on consulte le résultat plus tard).
python scripts/exp022_compositions.py analyser --archive /tmp/exp022-xi.jsonl \
  --match-id 'sofa:123456' --au '2026-11-14T14:55:00+01:00'
```

L'archive JSONL est append-only ; un doublon identique n'est pas réécrit.
Chaque capture reste datée et attribuée. Le code refuse une collecte
`>=` coup d'envoi, une source HTTPS discordante, une publication future,
un XI officiel incomplet, un joueur en double et une observation postérieure
à la date `--au`. Aucun instantané antérieur ne peut être reconstitué de zéro
en s'appuyant sur une page consultée après coup.

## Signal de rotation, non calibré

Pour chacune des équipes, on compare le XI observé aux **cinq dernières
rencontres distinctes** ayant une composition complète confirmée et un coup
d'envoi antérieur ; au moins **trois références** sont nécessaires. Les joueurs
titulaires dans 60 % de ces références sont « habituels ». S'il en manque trois
ou plus parmi les onze présentés pour le prochain match, on émet un
**signal descriptif de changement massif**, sans l'appeler automatiquement
rotation ou blessure. Les XI probables sont examinés comme hypothèses ; ils
ne deviennent jamais « confirmés » par comparaison avec l'historique.

## Vérification avant/après (future phase EXP-023)

Comparer sur **les mêmes matchs prospectifs** : fiabilité des XI, détection des
XI remaniés, alertes avant les faux favoris, et performances V+2 (Brier et
log-loss versus modèle inchangé), sur jeu temporel non vu. Aucun effet
numérique ne sera appliqué avant une amélioration indépendante. Les seuils
d'apprentissage existants demeurent : au moins 1 500 matchs avec XI historiques
sur trois ligues et quatre mois, plus une cohorte prospective suffisante.

**Éléments non activés :** extraction HTML automatique SportsGambler/PianetaFanta,
nouveau workflow programmé, pondération de rotation, modification du modèle,
envoi sur un service tiers. Leur faisabilité doit être éprouvée sans contourner
les restrictions d'accès et sans republier des pages propriétaires.
