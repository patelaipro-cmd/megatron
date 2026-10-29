# MEGATRON — règles communes aux points d'accès

Codex et Claude Code utilisent le même cœur Python. Travailler sur une branche
distincte, relire le checkpoint et les décisions avant toute modification.
Ne jamais déclarer un appel fournisseur ou un test réussi sans preuve.

La commande `prevoir` utilise Python/Stats seul par défaut : aucun appel LLM.
Les commandes `fusion`, `llm test`, `systeme` (si des clés sont présentes)
et `prevoir --execution multi-llm` peuvent appeler des fournisseurs : ne pas les lancer sans autorisation explicite.
Ne jamais afficher ni committer de clé API.

La mémoire du dépôt n'est pas synchronisée automatiquement. Avant une reprise,
actualiser la branche et lire le checkpoint. Ne pas écraser les journaux d'un
autre environnement. Des journaux divergents exigent une réconciliation explicite.
Tester dans un répertoire temporaire, sans altérer les prévisions réelles.

La réussite technique ne prouve pas la qualité prédictive.
Le parcours actuel reste 1X2 ; 2+/3+ et fenêtre de cinq heures restent à intégrer.

Méthode de synchronisation : docs/synchro-codex-claude.md.
