# Jeton coopératif du registre

Le registre canonique `memoire/` refuse les nouvelles prévisions et résultats
sans jeton actif. Une autre mémoire devient protégée dès qu'un jeton y a été
initialisé. Une mémoire isolée sans jeton conserve le parcours de simulation
existant. Ne pas traiter une copie du registre réel sans jeton comme une
simulation : l'initialiser explicitement avant toute exploitation.

L'état est une entrée du domaine travail, clé `jeton_registre`, avec détenteur
`codex` ou `claude`. Son identifiant doit être fourni à chaque écriture. Un
transfert remplace cette entrée par chaînage supersedes ; l'ancienne reste
lisible dans l'historique. Les probabilités déjà enregistrées sont conservées.

## Usage (exemples, aucune activation réelle pendant l'intégration)

```sh
python -m megatron jeton statut
python -m megatron jeton initialiser --acces codex --source "Décision de mise en service"
```

Lire l'identifiant renvoyé puis commiter le jeton, suivre les contrôles et
la PR de synchronisation. Utiliser cet identifiant pour les écritures :

```sh
python -m megatron prevoir '<tache JSON>' --coup-envoi '<date avec fuseau>' --acces codex --jeton '<id actif>'
python -m megatron resultat '<match_id>' '2-0' --source '<source vérifiée>' --acces codex --jeton '<id actif>'
```

Ces commandes restent soumises aux règles temporelles et de doublons existantes.
Sans jeton valide, `prevoir` refuse avant de consulter un agent. Le mode Stats
par défaut ne réalise aucun appel LLM.

Transmettre seulement après avoir terminé les écritures en cours :

```sh
python -m megatron jeton transmettre --acces codex --jeton '<id actif>' --a claude --source "Relais explicite"
python -m megatron synchro verifier --reference origin/main
```

Dès le transfert local, Codex cesse d'écrire. Commiter les journaux, fusionner
la PR dans main, puis Claude actualise sa copie, relit le checkpoint et exécute
`synchro verifier` et `jeton statut`. Claude écrit avec le nouvel identifiant.
La transmission ne met pas automatiquement le checkpoint à jour : le sauvegarder
suivant la procédure de fin de session habituelle.

Pour Python : `Ledger(store, acces="codex", jeton_id=identifiant)` ;
`suivi.prevoir` et `suivi.resultat` acceptent les mêmes arguments nommés.
Les lectures (bilan, reprise, statut) n'exigent pas le jeton.

## Garanties et limites

- Détenteur absent, différent ou identifiant périmé : refus sans écriture du registre.
- Deux jetons actifs ou jeton mal formé : refus, également signalé par synchro verifier.
- Un fichier `.registre.lock` créé exclusivement sérialise les écritures locales
  et les transferts, y compris entre processus. Une prévision complète garde
  le verrou pendant les agents et l'enregistrement. Le verrou est retiré à la
  sortie, y compris après une exception. Un arrêt brutal peut le laisser :
  vérifier qu'aucun processus n'écrit avant de le retirer manuellement.
- Le verrou n'est pas un mécanisme de transaction : une panne disque peut
  laisser une écriture partielle ; lancer synchro verifier avant reprise.
- Ce jeton n'authentifie pas une personne. Les écritures directes aux fichiers
  ou à MemoryStore.record sont de bas niveau et ne constituent pas un accès
  autorisé au registre ; les parcours métier passent par Ledger/suivi.
- Git n'offre aucun verrou distribué. Deux clones anciens du détenteur peuvent
  encore écrire chacun localement. Publication, arrêt de l'ancien détenteur,
  relecture et réconciliation des divergences restent obligatoires. Pour une
  exclusion distribuée stricte, un service central transactionnel est requis.

Le verrou local n'est pas versionné ; son existence n'est jamais une preuve
de possession du jeton distant. L'activation en mémoire réelle et le choix de
son premier détenteur restent une opération explicite de mise en service.
