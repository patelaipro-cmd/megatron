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

Attention : les anciennes clés 2+/3+ signifient total de buts. Les marchés
H_MARGE_2PLUS / H_MARGE_3PLUS et A_MARGE_2PLUS / A_MARGE_3PLUS signifient
marge de victoire. `marges` est exploratoire et non calibré, sans écriture ;
aucune activation automatique de ces marges dans prevoir. Voir docs/marges-victoire.md.

Pour une analyse sportive du favori, documenter les angles morts et les trois
contre-scénarios (défaite, nul, victoire courte), ainsi que le comparateur H2H
ancien/dernier/actuel à quatre axes. Utiliser `angles-morts modele|verifier` et
`prevoir --contexte-favori` (`megatron/contexte_favori.py`) ; ne pas présenter un contexte INCOMPLET ou NON_FOURNI
comme une analyse complète. Les sources restent déclaratives et aucune
probabilité n'est corrigée automatiquement. Voir docs/angles-morts-favori.md.
Indicateurs historiques des angles morts (cadre Luloki, 29/10/2026) : `megatron/angles_morts.py`, 13 angles, 3 questions,
scénario = fait + source + mécanisme ; aucune modification de probabilité sans expérience validée (EXP-009 : aucune).

Collecte externe (29/10/2026) : GitHub Actions écrit sur la branche `donnees-externes`
(jamais fusionnée dans main). Lecture par `scripts/lire_externe.py` avec `--avant`
(collecte antérieure au coup d'envoi). Faits déclaratifs seulement, aucune probabilité modifiée.
Voir docs/collecte-externe.md.
