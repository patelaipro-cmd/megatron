# MEGATRON CORE : intervention n°1 (27/10/2026)

## 1. Diagnostic de l'existant

Faits vérifiés dans le dépôt (`git log`, arborescence) :

- 2 commits sur `main` (`2f1b693` Initial commit, `53d78bd` correction du README).
- Un seul fichier : `README.md` (« auto construction machine d'analyse de football »).
- Aucun code, aucune dépendance, aucun test, aucun rapport, aucun checkpoint.
- Dernier état validé : **néant**. Rien à préserver ni à reprendre ; aucune ancienne règle métier n'est présente dans le dépôt.

Ressources manquantes (signalées, travaux indépendants poursuivis) :

| Ressource | État constaté | Conséquence |
|---|---|---|
| Clé Gemini (`GEMINI_API_KEY`) | absente de l'environnement | agent Gemini « indisponible », fusion en mode dégradé |
| Clé DeepSeek (`DEEPSEEK_API_KEY`) | absente | idem |
| Clé Qwen (`DASHSCOPE_API_KEY`) | absente | idem |
| Clé Claude API (`ANTHROPIC_API_KEY`) | absente (seule une URL de base est définie) | agent Claude API indisponible ; Claude n'intervient ici que comme développeur |
| github.com / api.github.com | proxy 403 depuis cet environnement | dépôts des inventaires vérifiés via PyPI uniquement |
| Données de matchs historiques | aucune dans le dépôt | pas encore de backtest possible |

## 2. Architecture et interfaces

Python 3.13, bibliothèque standard uniquement (aucune dépendance à installer).

```
megatron/
  store.py       Mémoire JSONL append-only, 5 domaines, provenance, statut, remplacement
  checkpoint.py  Checkpoint de reprise compact (memoire/checkpoint.json)
  ledger.py      Prévisions avant match + résultats, garde-fous anti-fuite, Brier/log-loss/calibration
  agents.py      Interface Agent commune, agent Stats (Poisson), agents LLM, Méthode de Fusion
  inventory.py   Analyse des inventaires et registre d'évaluation
  __main__.py    CLI : reprise | inventaire | fusion
memoire/         État persistant versionné dans git (lisible, diffable)
docs/            Inventaires, évaluations, registre généré, ce document
```

**Mémoire.** Domaines `travail`, `decisions`, `football`, `performances`, `technique`. Chaque entrée porte `source`, `status` (`verifie`, `declare`, `hypothese`, `invalide`), `recorded_at`, `observed_at` et `supersedes`. Une entrée n'est jamais réécrite : la remplacer ajoute une ligne qui pointe vers l'ancienne. `contradictions()` liste les clés ayant plusieurs valeurs actives, `stale()` les informations trop anciennes, `search()` permet de ne charger que l'utile.

**Checkpoint.** `checkpoint.save()` écrit un JSON de quelques centaines de tokens : résumé, prochaines actions, blocages, décisions actives, contradictions, effectifs par domaine, commit et version. Une nouvelle session lance `python -m megatron reprise` au lieu de relire l'historique.

**Registre de prévisions.** Une prévision est refusée si elle est enregistrée au coup d'envoi ou après, ou si sa date de coupure des données est postérieure au coup d'envoi. Elle est immuable (une nouvelle version de modèle crée une nouvelle prévision). Un résultat daté avant le coup d'envoi est refusé. `evaluate(version)` calcule Brier multiclasse, log-loss et table de calibration.

**Agents et fusion.** Chaque agent renvoie la même structure : conclusion, probabilités 1X2, preuves, hypothèses, incertitudes, objections, sources, nombre d'appels et tokens (avec la mention `mesure`, `estimation` ou `indisponible`). `fuse()` combine les avis disponibles, liste les agents manquants de la triade Gemini + DeepSeek + Stats, signale un désaccord supérieur à 15 points et regroupe les agents qui s'appuient sur les mêmes sources (avis non indépendants). Un agent sans accès ne produit jamais d'avis.

## 3. Plan d'intégration priorisé

1. **Données** : tester `probberechts/soccerdata` pour extraire des xG historiques d'une ligue (une saison de développement, une de validation, une de test, dans l'ordre chronologique).
2. **Référence prédictive** : backtest chronologique de l'agent Stats (Poisson) dans le registre, Brier et log-loss par saison.
3. **Expérience n°1** : `martineastwood/penaltyblog` (Dixon-Coles) contre Poisson, critères fixés avant l'exécution (licence à confirmer d'abord).
4. **Accès LLM** : dès qu'une clé Gemini ou DeepSeek est fournie, brancher `LLMAgent` via LiteLLM avec budget d'appels et comptage de tokens mesuré.
5. **Cache et index** : cache des sorties d'agents invalidé par version de modèle, de règles et de données.

## 4. Première implémentation exécutable

```bash
python -m megatron reprise                     # état utile de la dernière session
python -m megatron inventaire                  # régénère docs/registre-depots.{md,csv}
python -m megatron fusion '{"match_id": "demo", "xg_home": 1.6, "xg_away": 0.9}'
```

Exemple réel de `fusion` ci-dessus : H 53,8 %, N 25,0 %, E 21,2 %, mode `degrade`, agents manquants `deepseek` et `gemini` (clés absentes). Ce chiffre illustre le calcul, ce n'est pas une prévision : les xG sont fictifs.

## 5. Tests réellement exécutés

`python -m unittest discover -s tests -t . -v` : **16 tests, 16 réussis** (27/10/2026, Python 3.13). Ils couvrent le remplacement avec historique, la détection de contradictions et d'informations périmées, la persistance, les refus anti-fuite, l'immuabilité des prévisions, le calcul exact du Brier et de la log-loss, le mode dégradé de la fusion, la détection du désaccord et des sources partagées, la reprise sur checkpoint et le décompte des inventaires (542 entrées, 516 uniques, 24 doublons).

Limites : aucune donnée réelle, aucun appel LLM, aucune mesure de qualité prédictive. Ces tests prouvent que le socle se comporte comme prévu, pas que MEGATRON prédit bien.

## 6. Journal de décisions

Les décisions sont aussi enregistrées dans `memoire/decisions.jsonl`.

| Décision | Justification |
|---|---|
| Bibliothèque standard uniquement | zéro installation, socle testable partout ; les bibliothèques des inventaires entrent une par une via expérience |
| Mémoire en JSONL versionné dans git | les conteneurs sont éphémères ; git garde l'historique et rend chaque changement relisible |
| Entrées immuables, remplacement par chaînage | préserve l'historique exigé par la directive |
| Prévisions immuables et datées avant le coup d'envoi | empêche la fuite temporelle et la réécriture a posteriori |
| Poisson comme agent Stats de référence | simple, déterministe, sans token ; sert de base pour mesurer tout challenger |
| Agents LLM déclarés indisponibles sans clé | interdiction de prétendre avoir consulté un modèle |
| Inventaires classés « À VÉRIFIER » par défaut | ce sont des pistes ; seules 6 évaluations ont été réellement faites |
