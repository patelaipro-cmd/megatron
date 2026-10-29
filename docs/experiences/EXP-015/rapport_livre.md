# MEGATRON — EXP-014 : premier entraînement réel exploratoire

**Date : 29 octobre 2026.** **État : exécution statistique réelle terminée, non intégrée au dépôt, non déployable.**

## Exécution

Les 11 053 lignes du fichier `data/matches_top5_2020-2026.csv` ont été lues par le connecteur GitHub du dépôt `patelaipro-cmd/megatron` (Git blob SHA `0bdc03ab503c4f8020e50e66513c74b84d51ad68`). Le calcul a été effectué en JavaScript dans un environnement isolé, sans tirer de scores fictifs. Les tableaux détaillés sont consignés dans `resultats_exp014.json`.

Modèle candidat : Poisson indépendant, avec effets d'attaque et de défense par équipe et moyennes de buts domicile/extérieur par ligue. Optimisation par SGD déterministe, 32 passages. Paramètre de régularisation choisi sur **validation 2024-2025** parmi 0,002, 0,02 et 0,10 (retenu : 0,002). Ensuite, **réentraînement** sur l'ensemble de 2020-2025, évaluation sur **2025-2026 uniquement**.

| Phase | Observations |
|---|---:|
| Entraînement initial (avant juillet 2024) | 7 451 |
| Validation (juillet 2024 — juin 2025) | 1 751 |
| Test (juillet 2025 — juin 2026) | 1 752 |
| Fichier complet, dont saison partielle 2026-27 exclue | 11 053 |

Le favori est désigné d'après les probabilités de victoire du **modèle étudié**. Le comparateur Poisson utilise uniquement les moyennes domicile/extérieur de la ligue et **évalue le même favori**. La cible est **marge de victoire du favori**, pas nombre total de buts.

## Résultats du test chronologique

| Événement | Log-loss référence | Log-loss candidat | Brier référence | Brier candidat |
|---|---:|---:|---:|---:|
| Victoire simple | 0,714739 | 0,657386 | 0,260198 | 0,232729 |
| Victoire par au moins 2 buts | 0,587181 | 0,545181 | 0,196641 | 0,180959 |
| Victoire par au moins 3 buts | 0,380668 | 0,344231 | 0,107765 | 0,099885 |

**Attention, calibration imparfaite :** pour 2+ le modèle prédit en moyenne 28,65 %, la fréquence observée est 26,03 %. Pour la victoire simple : 51,54 % annoncés contre 49,94 % observés ; pour 3+ : 13,26 % contre 12,04 %.

Ces résultats montrent uniquement que ce candidat bat **une référence très simple** dans cet essai. Ils **ne montrent pas** qu'il bat `poisson-v5-cal` ni les modèles de MEGATRON, ni qu'il est rentable, ni qu'il anticipe réellement des matchs futurs. Le test 2025-26 avait déjà été utilisé ailleurs dans le projet ; il n'est **pas vierge à l'échelle globale**. La sélection exploratoire de cette expérience n'a pas été préenregistrée, donc le résultat doit être confirmé sur une nouvelle cohorte.

## Reproductibilité / limites concrètes

- `exp014_train.js` : reproduit le calcul à partir du **même fichier du dépôt**, vérifie le SHA Git blob et refuse toute dérive. Il peut conserver un `checkpoint.json` expérimental.
- `test_exp014.js` : tests locaux sur données **synthétiques**, réussis. Ils ne remplacent pas une deuxième exécution sur les données réelles dans le vrai clone.
- Source complète lue par GitHub, mais **pas copiée localement** : le script doit être réexécuté dans Claude Code avec les fichiers du dépôt. Les résultats ci-joints sont les nombres observés lors de la première exécution JavaScript, et non une preuve de CI.
- Aucune branche ni commit : le connecteur GitHub a refusé la création de branche (403 Resource not accessible by integration).
- Pas de scores récents certifiés après le 20/09 dans `data.CURRENT`, ni absences calibrées ; aucune activation automatique.

## Suite autorisée

1. Claude Code réexécute EXP-014 **sans en modifier les critères après avoir vu le résultat**, conserve le checkpoint et vérifie les mêmes métriques.
2. Comparer le candidat à `poisson-v5-cal` sur **exactement les mêmes matchs** avec une évaluation chronologique (résultats non prédis avant-match = rétrospectif).
3. Réparer la collecte des résultats depuis le 21 septembre, recouper source indépendante et rejeter les scores non certifiés.
4. Construire une cohorte prospective horodatée et un protocole EXP-015 avant de valider les paramètres d'absences.
5. GO automatique OFF, aucune fusion sans revue.
