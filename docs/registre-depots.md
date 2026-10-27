# Registre d'évaluation des dépôts

Généré par `python -m megatron inventaire`. Ne pas éditer à la main :
les vérifications se consignent dans `docs/evaluations.json`.

- Entrées dans les inventaires : **542** (depots-github-autoevolutif.md: 102, depots-github-football.md: 140, depots-github-multi-llm.md: 89, depots-github-orchestration.md: 108, depots-github-reduction-tokens.md: 103)
- Dépôts uniques : **516**
- Dépôts présents dans plusieurs inventaires : **24**
- Dépôts évalués : **6** ; les autres restent « À VÉRIFIER ».

## Dépôts évalués

| Dépôt | Rôle potentiel | Vérifications réalisées | Licence et contraintes | Compatibilité | Classement motivé |
|---|---|---|---|---|---|
| berriai/litellm | Passerelle unique vers Claude, Gemini, DeepSeek, Qwen ; comptage des tokens | PyPI 27/10/2026 : v1.106.4, Python >=3.10,<3.15 ; dépôt GitHub non consulté (proxy 403) | MIT (déclarée sur PyPI) | Python 3.13 OK ; à brancher derrière LLMAgent quand des clés existeront | **TESTER** : candidat n°1 pour l'interface commune ; inutile tant qu'aucune clé Gemini/DeepSeek n'est disponible |
| martineastwood/penaltyblog | Modèles de buts (Poisson, Dixon-Coles), scraping, métriques | PyPI 27/10/2026 : v1.13.1, Python >=3.10, 48 dépendances déclarées | non déclarée sur PyPI : à confirmer sur le dépôt | Python 3.13 OK selon métadonnées ; non installé | **TESTER** : candidat challenger de l'agent Stats (Poisson de référence) dans une expérience chronologique |
| ml-kuleuven/socceraction | Valorisation des actions (VAEP, xT) sur données événementielles | PyPI 27/10/2026 : v1.5.3, Python >=3.9,<3.13 | MIT (déclarée sur PyPI) | incompatible avec Python 3.13 de cet environnement | **RÉFÉRENCE** : utile pour l'analyse tactique plus tard, mais contrainte de version Python |
| mlflow/mlflow | Suivi d'expériences | PyPI 27/10/2026 : v3.17.2, 60 dépendances déclarées | Apache-2.0 (classifieur PyPI) | lourd ; le registre JSONL de MEGATRON couvre le besoin actuel | **RÉFÉRENCE** : à reconsidérer si le nombre d'expériences dépasse ce qu'un journal JSONL gère bien |
| optuna/optuna | Optimisation d'hyperparamètres pour les expériences | PyPI 27/10/2026 : v5.0.0, Python >=3.9 | MIT (classifieur PyPI) | Python 3.13 OK selon métadonnées | **RÉFÉRENCE** : prématuré : aucun modèle ni jeu de backtest à optimiser pour l'instant |
| probberechts/soccerdata | Collecte de données (FBref, Understat, ClubElo, etc.) | PyPI 27/10/2026 : v2026.43.0, Python >=3.10,<3.15 | Apache-2.0 (déclarée sur PyPI) ; respecter les CGU des sites sources | Python 3.13 OK selon métadonnées ; non installé | **TESTER** : source de xG historiques nécessaire pour alimenter l'agent Stats et le backtest |

## Doublons entre inventaires

| Dépôt | Inventaires |
|---|---|
| agno-agi/agno | autoevolutif, orchestration |
| aider-ai/aider | multi-llm, reduction-tokens |
| anative-lab/evoagentx | autoevolutif, orchestration |
| berriai/litellm | multi-llm, reduction-tokens |
| cheaper-inference/omniroute | multi-llm, reduction-tokens |
| commonstackai/uncommonroute | multi-llm, reduction-tokens |
| davidecolombo/local-mcp | multi-llm, reduction-tokens |
| enterpilot/gomodel | multi-llm, reduction-tokens |
| langgenius/dify | multi-llm, orchestration |
| lm-sys/routellm | multi-llm, reduction-tokens |
| mastra-ai/mastra | multi-llm, orchestration |
| maximhq/bifrost | multi-llm, reduction-tokens |
| memtensor/memos | autoevolutif, reduction-tokens |
| musistudio/claude-code-router | multi-llm, orchestration, reduction-tokens |
| n8n-io/n8n | multi-llm, orchestration |
| nadirrouter/nadirclaw | multi-llm, reduction-tokens |
| nanako0129/pilotfish | multi-llm, orchestration, reduction-tokens |
| nvidia-nemo/switchyard | multi-llm, reduction-tokens |
| openai/codex-plugin-cc | multi-llm, orchestration |
| openai/openai-agents-python | multi-llm, orchestration |
| othmanadi/planning-with-files | orchestration, reduction-tokens |
| pydantic/pydantic-ai | multi-llm, orchestration |
| slopus/happy | multi-llm, orchestration |
| stellarlinkco/myclaude | multi-llm, orchestration |
