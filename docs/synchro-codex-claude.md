# Synchronisation Codex ↔ Claude Code

Partager le dépôt ne synchronise pas la mémoire : chaque environnement a sa
copie de `memoire/*.jsonl`, et rien ne les réunit tant qu'elles ne passent pas
par `main` sur GitHub. Méthode proposée (manuelle, non automatisée).

## Règles

1. **Source de vérité : `origin/main`.** Rien n'est « synchronisé » tant que ce
   n'est pas fusionné dans `main`.
2. **Une branche par environnement et par tâche** : `codex/…`, `claude/…`.
   Toujours partir de `origin/main` à jour.
3. **Un seul détenteur du registre réel.** Les prévisions et résultats réels
   (`memoire/performances.jsonl`, clés `pred:` et `result:`) ne sont écrits que
   par un environnement à la fois, celui qui détient le jeton (noté dans le
   checkpoint, champ `resume`). L'autre teste en mémoire temporaire
   (`--memoire $(mktemp -d)`).
4. **Pas de réécriture** des JSONL : ajout seulement, corrections par
   `supersedes`.

## Début de session

```
git fetch origin main
git switch -c <env>/<tache> origin/main
python -m megatron reprise
```

Vérifier : le `commit` du checkpoint est un ancêtre de `origin/main`
(`git merge-base --is-ancestor <commit> origin/main`) et les `effectifs` du
checkpoint correspondent aux fichiers (sinon : mémoire modifiée après le
checkpoint, lire `git log -- memoire/`).

## Fin de session

```
python -m unittest discover -s tests
# checkpoint.save(...) avec résumé, prochaines actions, blocages, détenteur du jeton
git add -A && git commit && git push -u origin <env>/<tache>
```

Puis PR vers `main`. Le passage de relais est valide seulement quand la PR est
fusionnée et que l'autre environnement a relu le checkpoint de `main`.

## Divergence

Deux branches ont ajouté des lignes aux mêmes JSONL :

- conflit git en fin de fichier : garder l'union des lignes (chaque entrée a un
  `id` unique), triées par `recorded_at` ;
- puis `MemoryStore.contradictions()` sur chaque domaine : toute clé active en
  double doit être tranchée à la main ;
- deux `pred:` pour le même match et la même version : garder la plus ancienne
  (antérieure au coup d'envoi), signaler l'autre ; jamais de choix a posteriori.

Ne pas activer `merge=union` dans `.gitattributes` sans une commande de
vérification automatique : l'union silencieuse peut laisser deux prévisions
actives.

## À construire

- `python -m megatron synchro verifier` : contrôle commit/effectifs du
  checkpoint, doublons `pred:`/`result:`, contradictions.
- Jeton d'écriture explicite dans la mémoire (`travail`, clé `jeton_registre`).
