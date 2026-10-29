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
python -m megatron synchro verifier --reference origin/main
python scripts/valider_acces.py --acces <codex|claude>
```

`synchro verifier` ne modifie rien. Code 1 (erreurs) : ne pas reprendre avant
réconciliation. Erreurs : ligne illisible ou marqueur de conflit git,
identifiant en double, `supersedes` inconnu, prévision ou résultat actif en
double, contradiction active, prévision enregistrée après le coup d'envoi.
Alertes (code 0, à lire) : checkpoint absent ou sans commit, effectifs
différents du checkpoint, commit du checkpoint hors de l'historique, retard sur
la référence, mémoire non commitée. Une mémoire hors dépôt (relais par fichier)
s'utilise avec `--memoire <dossier>`.

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
- puis `python -m megatron synchro verifier` : toute clé active en double
  ou contradiction est listée et doit être tranchée à la main ;
- deux `pred:` pour le même match et la même version : garder la plus ancienne
  (antérieure au coup d'envoi), signaler l'autre ; jamais de choix a posteriori.

`merge=union` dans `.gitattributes` reste désactivé : l'union silencieuse peut
laisser deux prévisions actives ; `synchro verifier` les détecte après coup.

## Test de synchronisation par Git

`scripts/synchro_git.py` rejoue un relais complet sur une mémoire fictive
(`essais/synchro_git/memoire`, branches de test seulement, jamais dans main) :

1. Claude : `python scripts/synchro_git.py claude`, commit, push de sa branche.
2. Codex : branche `codex/synchro-git` tirée de celle de Claude,
   `python scripts/synchro_git.py codex --reference origin/<branche Claude>`, commit, push.
3. Claude : fusion de `origin/codex/synchro-git`, `python scripts/synchro_git.py retour`.

`python scripts/synchro_git.py divergence` montre, dans un bac à sable local,
que deux branches qui prévoient le même match produisent un conflit git, et
que la résolution par union est refusée par `synchro verifier`.

## À construire

- Jeton d'écriture explicite dans la mémoire (`travail`, clé `jeton_registre`).
