# Relais Git fictif Codex → Claude → Codex

État de départ : trois matchs entièrement fictifs, six prévisions 1X2 et un
checkpoint, créés par Codex sur le cœur 308f653. Aucun résultat réel ni clé.
Les prévisions viennent de stats-v0 sur des xG artificiels : ce test valide
le transfert de mémoire, pas les marchés de buts ou la performance prédictive.
Les dates 2099 sont exclusivement injectées pour cette simulation.

## Étape Claude (non encore exécutée)

Après réception de la branche codex/relais-git-20261029, lire AGENTS.md et
préserver les changements locaux. Créer une branche Claude basée sur cette
branche Codex, car elle contient le témoin à reprendre. Cette dépendance
explicite est propre à ce relais ; les tâches indépendantes partent de main.
Depuis une copie propre :

```sh
git fetch origin
git switch -c claude/relais-git-20261029 origin/codex/relais-git-20261029
python -m megatron synchro verifier --reference origin/main
python -m megatron --memoire tests/fixtures/relais_git_20261029/memoire_fictive synchro verifier --reference origin/main
python tests/fixtures/relais_git_20261029/relais.py --repo . --etape claude
```

Code 1 : ne pas poursuivre, donner l'erreur exacte. Les alertes ne valent pas
validation de leur cause : les lire. Le script bloque le réseau dans son
processus et utilise explicitement Stats seul. Ne pas modifier relais.py ou
depart_codex.json. Le script conserve les lignes initiales, refuse un doublon,
ajoute trois scores fictifs et écrit rapport_claude.json puis le checkpoint.

Avant publication, relancer les deux commandes synchro ci-dessus. L'alerte
« mémoire fictive non commitée » est attendue à ce stade. Vérifier que
`git diff -- memoire` est vide. Commiter seulement le dossier de ce relais :

```sh
git add tests/fixtures/relais_git_20261029
git commit -m "Test relais Git : étape Claude sur mémoire fictive"
python -m megatron synchro verifier --reference origin/main
python -m megatron --memoire tests/fixtures/relais_git_20261029/memoire_fictive synchro verifier --reference origin/main
git push -u origin claude/relais-git-20261029
```

Transmettre la branche, le SHA du commit et le rapport à l'utilisateur.
Ne pas fusionner dans main à cette étape. Les journaux fictifs ne doivent
jamais être copiés dans memoire/. Aucun jeton du registre réel n'est transféré.

## Retour Codex (à faire après publication Claude)

Dans une copie propre de la branche Claude, relire les consignes et lancer les
deux synchro verifier. Vérifier que depart_codex.json et relais.py sont
identiques à ceux de la branche Codex publiée, puis exécuter :

```sh
python tests/fixtures/relais_git_20261029/relais.py --repo . --etape retour
```

Code 0 et contrôles vrais valident la conservation du témoin via les branches
publiées. Créer une PR pour les preuves vérifiées, puis contrôler main après
fusion : le protocole considère la synchronisation achevée seulement à ce
moment. Une simulation locale ne remplace pas cette exécution Claude ni la
fusion distante. Le nom d'étape du rapport est déclaratif.
