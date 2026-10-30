# Audit et reproduction Codex — 30 octobre 2026

Base du code : `6ba333a5c379532fa3fe5b8b00ff3372c83b2b1e`.
Données externes : `cd90a0c` (copie séparée, jamais fusionnée).

## Expérience reproduite

Commande : `python scripts/exp015_buts_v5.py --sortie <dossier temporaire>`.
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

Les branches EXP-016/017/018 contiennent déjà des expériences déclarées rejetées :
leurs résultats ont été lus mais pas reproduits dans cet audit. Aucun entraînement
sur une cohorte insuffisante, aucune collecte réseau ni aucun appel LLM exécuté.
Seuls Git et la reproduction locale d'EXP-015 ont été utilisés.
