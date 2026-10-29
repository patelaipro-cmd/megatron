# MEGATRON — règles communes aux points d'accès

Codex et Claude Code utilisent le même cœur Python. Travailler sur une branche
distincte, relire le checkpoint et les décisions avant toute modification.
Ne jamais déclarer un appel fournisseur ou un test réussi sans preuve.

La commande `prevoir` utilise Python/Stats seul par défaut : aucun appel LLM.
Les commandes `fusion`, `llm test`, `systeme` (si des clés sont présentes)
et `prevoir --execution multi-llm` peuvent appeler des fournisseurs : ne pas les lancer sans autorisation explicite.
Ne jamais afficher ni committer de clé API.

La mémoire du dépôt n'est pas synchronisée automatiquement. Avant une reprise,
actualiser la branche, lire le checkpoint et lancer
`python -m megatron synchro verifier --reference origin/main` (code 1 = ne pas reprendre).
Ne pas écraser les journaux d'un
autre environnement. Des journaux divergents exigent une réconciliation explicite.
Tester dans un répertoire temporaire, sans altérer les prévisions réelles.

La réussite technique ne prouve pas la qualité prédictive.
`prevoir` enregistre le 1X2 et les marchés 2+ / 3+ buts (EXP-007), seulement dans
les 5 h qui précèdent le coup d'envoi. Saisir le score (`2-1`) pour résoudre les marchés de buts.

Méthode de synchronisation : docs/synchro-codex-claude.md.
Validation d'un point d'accès (sans LLM, sans toucher memoire/) :
`python scripts/valider_acces.py --acces codex` (ou `claude`) ; code 0 = tout passe.

Le registre réel (`memoire/`) exige un jeton explicite : `jeton statut`, puis
`--acces codex|claude --jeton <id actif>` pour `prevoir` et `resultat`.
Ne pas initialiser ni transférer le jeton pendant les tests du projet : utiliser
une mémoire temporaire. Un transfert doit être commité, fusionné dans main et
relu par le destinataire ; l'ancien détenteur cesse d'écrire dès le transfert.
Ce jeton est coopératif et le verrou est local : Git ne verrouille pas les
copies distantes. Consignes détaillées : docs/jeton-registre.md.
