# MEGATRON — pilote Apify en lecture seule

## But

Le lecteur Apify deja existant (`scripts/collecte_externe.py`, PR #65) recupere
les compositions depuis une tache `abotapi/sofascore-scraper`.
Ce pilote ajoute un audit de 100 resultats issus d'un run **deja termine**,
sans demarrer d'Actor, sans ecrire dans `memoire/` et sans modifier les modeles.

L'audit examine : presence des identifiants, doublons, dates, scores finaux,
statistiques, cotes, compositions, joueurs absents, ligues suivies et
preuve temporelle prudente que le run s'est termine avant le coup d'envoi.
Il ne remplace pas la verification croisee sur une deuxieme source.

## Configuration du compte Apify

Actor : https://apify.com/abotapi/sofascore-scraper

Configuration de depart **a verifier avant lancement** (date illustrative) :

```json
{
  "mode": "scheduled",
  "sports": ["football"],
  "date": "2026-11-03",
  "daysAhead": 0,
  "maxItems": 100,
  "includeStatistics": false,
  "includeLineups": true,
  "includeIncidents": false,
  "includeOdds": false,
  "includeVotes": false,
  "includeH2H": false,
  "includeShotmap": false,
  "includePlayerHeatmaps": false,
  "incrementalMode": false
}
```

Un run de 100 resultats Apify n'assure pas 100 matchs dans les ligues
de MEGATRON : il peut contenir d'autres competitions. Verifier le prix,
les eventuels frais de proxy et le droit d'utilisation avant de lancer l'Actor.

Secrets GitHub Actions : `APIFY_TOKEN` (jeton, ne jamais publier) et
`APIFY_TACHE_SOFASCORE` (id ou nom de la Task Apify).

## Execution

Workflow manuel : `.github/workflows/pilote-apify.yml`.
Il lit seulement le dernier run reussi de la Task, lance les tests sans
reseau et fournit le rapport `rapports/pilote-apify.json` comme artifact
pendant sept jours. Il a l'autorisation `contents: read`.

Commande locale avec un export de dataset :

```bash
python scripts/pilote_apify.py --fichier export.json --limite 100 --rapport rapports/pilote-apify.json
```

La date de fin du run peut etre fournie si elle est **reellement connue** :

```bash
python scripts/pilote_apify.py --fichier export.json --fin-run 2026-11-03T12:00:00Z
```

Lecture d'un run deja existant, si les variables d'environnement sont
configurees en secret (aucune creation de run) :

```bash
python scripts/pilote_apify.py --tache --limite 100 --rapport rapports/pilote-apify.json
```

Code de sortie : 0 = aucune anomalie structurelle detectee ;
2 = alertes qualite ; 1 = erreur de configuration/lecture. **0 ne signifie
pas que les donnees sont valides pour l'entrainement**.

## Etapes de validation avant entrainement

1. Obtenir effectivement au moins 100 matchs des ligues visees,
   en adaptant la taille d'echantillon si necessaire.
2. Comparer horaires, scores, competitions et stats a une deuxieme famille
   independante (API-Football, ESPN, Football-Data.org selon disponibilite).
3. Mesurer les champs manquants, doublons et indisponibilites des compos.
4. Pour les analyses T-60, T-30 et T-5, n'utiliser que les donnees
   **connues a l'instant de la prevision** et avant le coup d'envoi.
5. Conserver la provenance et les refus. Ouvrir une experience
   distincte avant toute integration aux probabilites.

Le dernier run termine peut etre posterieur a un match historique ; dans
ce cas il n'etablit aucune disponibilite pre-match. Les six tests unitaires
sont hors reseau et ne prouvent aucune collecte reelle.
