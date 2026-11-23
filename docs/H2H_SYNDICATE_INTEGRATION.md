# Contrat d'intégration H2H dans SYNDICATE V1/V2

## Entrée
Le workflow `.github/workflows/h2h.yml` lit `data/fixtures_h2h_2026-11-23.csv` (colonnes `home,away,date`), les historiques MEGATRON et `data/h2h_verifies_2026-11-23.csv`.

## Sorties
- `h2h-results.json` : scores, dates, clubs et chemin du fichier historique.
- `h2h-coverage.csv` : `count`, `missing`, `status` par rencontre.
- `syndicate-h2h.csv` : `date,match,h2h_1,h2h_2,h2h_3,h2h_count,status`, importable dans les tableaux V1/V2.

## Contrôles
1. Les H2H doivent être **antérieurs** à la date de la rencontre.
2. Ne jamais mélanger équipes féminines et masculines, ou équipes réserves et premières équipes.
3. Conserver le sens domicile/extérieur du résultat historique, sans inverser le score.
4. `COMPLETE` signifie seulement **trois H2H trouvés**, pas que la rencontre est validée ou recommandée.
5. `DATA LIMITED` interdit d'inventer des scores ; garder les cellules non renseignées.
6. Le résultat de la récupération n'autorise **aucun changement de poids, pronostic ou seuil**.

## État contrôlé
Workflow GitHub Actions #45122331322 (commit a9fe6c2bdf97e80ba0515523e0f4d6ac241240f4) : 15 rencontres, 39 H2H trouvés, 6 manquants. Les tests GitHub du commit ont réussi.

## À faire avant fusion
- Revue de provenance indépendante pour chaque ligne de `data/h2h_verifies_2026-11-23.csv`.
- Vérifier la cohérence des alias et l'absence de doublons inter-sources.
- Décider si le workflow doit être généralisé aux rencontres futures (il utilise pour l'instant un fichier de fixtures daté du 23/11/2026).
- Prévoir la consommation du CSV par le pipeline V1/V2 : **le pipeline de prévision n'est pas encore branché automatiquement à cet export**.
