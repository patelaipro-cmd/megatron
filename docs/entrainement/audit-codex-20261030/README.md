# Audit et reproduction Codex — 30 octobre 2026

Base du code : `6ba333a5c379532fa3fe5b8b00ff3372c83b2b1e`.
Données externes : `aacd3a1` (copie séparée, jamais fusionnée).

Intégration actualisée sur `8a387cd` : EXP-015 (totaux de buts) a été renommée EXP-019 par Claude pour éviter une collision de numérotation. Les résultats reproduits sont inchangés.

## Expérience reproduite

Commande : `python scripts/exp019_buts_v5.py --sortie <dossier temporaire>`.
Le JSON produit est identique, après chargement JSON, à celui d'EXP-015 dans
le dépôt. 10 954 matchs de test ; B1/B2/B3 vrais pour les deux marchés.

| Total de buts | Log-loss v5 Platt | Log-loss v4 Platt | Écart [IC 95 %] |
|---|---:|---:|---|
| 2+ | 0,525710 | 0,527651 | −0,001940 [−0,002840 ; −0,001100] |
| 3+ | 0,678425 | 0,681329 | −0,002900 [−0,004100 ; −0,001750] |

Il s'agit de totaux de buts, pas de marges de victoire. Cette reproduction
confirme l'exécution et les calculs existants ; elle ne crée pas un échantillon
indépendant. Aucun paramètre de production modifié.

## Fiabilité de la préparation

- Les matchs de compositions sont désormais comptés par identifiant fournisseur,
  plutôt que par couple heure/ligue : deux rencontres simultanées restent distinctes.
  Les captures répétées du même identifiant comptent une seule fois par source.
- Les lignes sans identifiant sont exclues et signalées ; chaque ligne doit être
  collectée avant le coup d'envoi et avant la borne de l'audit.
- La cohorte prospective utilise `value.match_id` sans tronquer les identifiants
  contenant des deux-points. Plusieurs marchés/modèles ne multiplient pas les matchs.

Tests de régression : matchs simultanés, répétition des captures, identifiant absent,
horodatage futur sur une ligne autre que la première, identifiants courts et longs,
plusieurs marchés et résultats partiels.

## État et limites

402 matchs 2026/27 dans les cinq ligues, sur les 1 000 requis par EXP-014.
Dernier résultat : 28 octobre. Compositions pré-match : 4 identifiants ESPN,
1 API-Football ; le maximum par source est conservé pour ne pas additionner
les mêmes matchs sans correspondance d'identifiants. Deux ligues, deux jours.
Ces compteurs ne certifient ni onze titulaires des deux côtés, ni un dossier
complet d'absences apparié. Ils ne suffisent pas à autoriser EXP-013.
La mémoire auditée de main ne contient aucune prévision résolue.

EXP-016/018/020 sont désormais fusionnées ; EXP-017 est disponible sur sa branche. Ces expériences sont déclarées rejetées :
leurs résultats ont été lus mais pas reproduits dans cet audit. Aucun entraînement
sur une cohorte insuffisante, aucune collecte réseau ni aucun appel LLM exécuté.
Seuls Git et la reproduction locale d'EXP-015 ont été utilisés.

La synchronisation signale un écart hérité de main : checkpoint performances=10, mémoire=11. Le diff mémoire contre origin/main est vide ; cet audit ne réécrit pas le checkpoint de Claude.

Validation après intégration de main : `python scripts/valider_acces.py --acces codex`, code 0, 207 tests réussis, parcours fictif complet et mémoire inchangée. Aucun réentraînement supplémentaire autorisé par les seuils actuels.
