# Registre d'évaluation des dépôts

Généré par `python -m megatron inventaire`. Ne pas éditer à la main :
les vérifications se consignent dans `docs/evaluations.json`.

- Entrées dans les inventaires : **542** (depots-github-autoevolutif.md: 102, depots-github-football.md: 140, depots-github-multi-llm.md: 89, depots-github-orchestration.md: 108, depots-github-reduction-tokens.md: 103)
- Dépôts uniques : **516**, évalués : **516**
- INTÉGRER : **2** · TESTER : **29** · RÉFÉRENCE : **72** · REDONDANT : **143** · REJETER : **270**

## INTÉGRER

| Dépôt | Module | Licence | Vérification | Motif |
|---|---|---|---|---|
| berriai/litellm | M5 connexion LLM | MIT hors dossier enterprise/ (LICENSE lu le 28/10/2026) | GitHub 28/10/2026 : 62199 étoiles, dernier push 2026-10-28, Python ; v1.106.4 installée et testée dans megatron/llm.py (5 tests, sans clé) | branché dans megatron/llm.py : Gemini, DeepSeek, Qwen, Claude, OpenRouter ; comptage tokens et coûts |
| xgabora/club-football-match-data | M1 données | MIT | GitHub 28/10/2026 : 219 étoiles, dernier push 2026-09-06, langage none ; 27/10/2026 : README et LICENSE lus via raw.githubusercontent.com, data/Matches.csv téléchargé (SHA-256 consigné dans data/SOURCE.md), extrait Top 5 utilisé dans EXP-001 | déjà intégré : résultats + cotes, MIT, accessible depuis le cloud |

## TESTER

| Dépôt | Module | Licence | Vérification | Motif |
|---|---|---|---|---|
| dcaribou/transfermarkt-datasets | M1 données | CC0-1.0 | GitHub 28/10/2026 : 524 étoiles, dernier push 2026-09-05, langage Python | P1 : valeurs marchandes et effectifs, CC0 ; donnée absente du modèle |
| openfootball/football.json | M1 données | CC0-1.0 | GitHub 28/10/2026 : 1050 étoiles, dernier push 2026-09-22, langage none | P1 : calendriers des matchs à venir, CC0, accessible via raw.githubusercontent |
| probberechts/soccerdata | M1 données | Apache-2.0 (LICENSE.rst lu le 28/10/2026) ; respecter les CGU des sites sources | GitHub 28/10/2026 : 2124 étoiles, dernier push 2026-10-27, langage Python ; PyPI 27/10/2026 : v2026.43.0, Python >=3.10,<3.15 ; sites sources (FBref, Understat, football-data.co.uk) bloqués par le proxy de l'environnement cloud | P1 : xG FBref/Understat, ClubElo, Sofascore ; sites bloqués depuis le cloud → poste local |
| withqwerty/reep | M1 données | CC0-1.0 | GitHub 28/10/2026 : 239 étoiles, dernier push 2026-08-20, langage TypeScript | P1 : table de correspondance des noms d'équipes entre 25 sources, CC0 ; indispensable pour fusionner |
| optuna/optuna | M10 auto-amélioration | MIT | GitHub 28/10/2026 : 14976 étoiles, dernier push 2026-10-28, langage Python ; PyPI 27/10/2026 : v5.0.0, Python >=3.9 | P1 : remplace les grilles manuelles d'EXP-002 (demi-vie, rétrécissement), MIT |
| unclecode/crawl4ai | M2 collecte presse | Apache-2.0 | GitHub 28/10/2026 : 86421 étoiles, dernier push 2026-10-26, langage Python | P1 : pages dynamiques ; presse bloquée depuis le cloud → test local |
| martineastwood/penaltyblog | M3 modèles | MIT | GitHub 28/10/2026 : 245 étoiles, dernier push 2026-10-19, langage Python ; PyPI 27/10/2026 : v1.13.1, Python >=3.10, 48 dépendances déclarées | P1 : challenger de poisson-v1 (Dixon-Coles, bayésien, pi-rating), MIT confirmé |
| 567-labs/instructor | M5 connexion LLM | MIT | GitHub 28/10/2026 : 14068 étoiles, dernier push 2026-10-26, langage Python | P1 : force des réponses JSON validées (probabilités 1X2) avec relance auto, MIT |
| juliusbrussee/caveman | M9 tokens | Apache-2.0 | GitHub 28/10/2026 : 115582 étoiles, dernier push 2026-10-27, langage Go | P1 : style réponse minimal appliqué aux prompts des agents (moins de tokens de sortie) |
| toon-format/toon | M9 tokens | MIT | GitHub 28/10/2026 : 25569 étoiles, dernier push 2026-10-09, langage TypeScript | P1 : tableaux de stats envoyés aux LLM en TOON au lieu de JSON, MIT |
| manucabral/easysoccerdata | M1 données | MIT | GitHub 28/10/2026 : 52 étoiles, dernier push 2026-05-14, langage Python | P2 : Sofascore + Promiedos, couvre l'Amérique du Sud (Venezuela, Colombie) |
| online-ml/river | M10 auto-amélioration | BSD-3-Clause | GitHub 28/10/2026 : 6139 étoiles, dernier push 2026-10-27, langage Python | P2 : mise à jour du modèle après chaque match, BSD |
| stanfordnlp/dspy | M10 auto-amélioration | MIT | GitHub 28/10/2026 : 38822 étoiles, dernier push 2026-10-28, langage Python | P2 : optimise les prompts des agents LLM contre la log-loss historique, MIT |
| octosport/octopy | M3 modèles | MIT | GitHub 28/10/2026 : 77 étoiles, dernier push 2022-04-10, langage Jupyter Notebook | P2 : méthode de Shin pour retirer la marge des cotes ; MIT |
| hudl/open-data | M4 métriques | non standard : à lire avant usage | GitHub 28/10/2026 : 3744 étoiles, dernier push 2026-10-27, langage none | P2 : événements StatsBomb gratuits pour un xG maison ; licence StatsBomb non commerciale |
| hudl/statsbombpy | M4 métriques | aucune : code non réutilisable | GitHub 28/10/2026 : 747 étoiles, dernier push 2026-10-20, langage Python | P2 : client officiel des données StatsBomb ; pas de fichier de licence |
| ollama/ollama | M5 connexion LLM | MIT | GitHub 28/10/2026 : 185051 étoiles, dernier push 2026-10-28, langage Go | P2 : Qwen/DeepSeek en local et gratuit sur ton poste ; contourne les API bloquées |
| langchain-ai/langgraph | M7 agents | MIT | GitHub 28/10/2026 : 44021 étoiles, dernier push 2026-10-28, langage Python | P2 : graphe d'agents avec état et reprise, MIT ; à tester quand 3 agents LLM tournent |
| prefecthq/prefect | M7 pipeline | Apache-2.0 | GitHub 28/10/2026 : 24088 étoiles, dernier push 2026-10-27, langage Python | P2 : planifier collecte + prévisions chaque jour, reprises auto, Apache-2.0 |
| headroomlabs-ai/headroom | M9 tokens | Apache-2.0 | GitHub 28/10/2026 : 78059 étoiles, dernier push 2026-10-28, langage Python | P2 : compresser les articles collectés avant envoi au LLM, Python, Apache-2.0 |
| martj42/international_results | M1 données | CC0-1.0 | GitHub 28/10/2026 : 527 étoiles, dernier push 2026-10-10, langage none | P3 : matchs internationaux depuis 1872, CC0, pour les sélections |
| algorithmicsuperintelligence/openevolve | M10 auto-amélioration | Apache-2.0 | GitHub 28/10/2026 : 7663 étoiles, dernier push 2026-10-27, langage Python | P3 : fait évoluer le code du modèle contre le backtest ; demande une clé LLM |
| andrewrowlinson/mplsoccer | M12 rapports | MIT | GitHub 28/10/2026 : 552 étoiles, dernier push 2026-10-27, langage Python | P3 : graphiques de terrain pour les rapports, MIT |
| microsoft/markitdown | M2 collecte presse | MIT | GitHub 28/10/2026 : 192608 étoiles, dernier push 2026-10-23, langage Python | P3 : PDF/Word (rapports, communiqués) en Markdown, MIT |
| ml-kuleuven/socceraction | M4 métriques | MIT | GitHub 28/10/2026 : 823 étoiles, dernier push 2026-10-18, langage Python ; PyPI 27/10/2026 : v1.5.3, Python >=3.9,<3.13 | P3 : VAEP/xT si données événements ; Python < 3.13 |
| pysport/kloppy | M4 métriques | BSD-3-Clause | GitHub 28/10/2026 : 569 étoiles, dernier push 2026-10-24, langage Python | P3 : standardise les événements de tous fournisseurs, BSD |
| anthropics/claude-agent-sdk-python | M7 agents | MIT | GitHub 28/10/2026 : 8369 étoiles, dernier push 2026-10-27, langage Python | P3 : agent Claude avec outils, MIT |
| pydantic/pydantic-ai | M7 agents | MIT | GitHub 28/10/2026 : 20916 étoiles, dernier push 2026-10-28, langage Python | P3 : agents typés, alternative à LangGraph |
| microsoft/llmlingua | M9 tokens | MIT | GitHub 28/10/2026 : 6777 étoiles, dernier push 2026-09-10, langage Python | P3 : compression de prompts ; lourd (modèle PyTorch) |

## RÉFÉRENCE (72)

| Dépôt | Module | Motif |
|---|---|---|
| anthropics/claude-code | DEV | outil qui construit la machine |
| mksglu/context-mode | DEV | utile sur ton poste pour Claude Code |
| oraios/serena | DEV | utile sur ton poste pour Claude Code |
| rtk-ai/rtk | DEV | utile sur ton poste pour Claude Code ; pas pour la machine |
| roboflow/sports | HORS | référence vidéo si un jour la machine lit des vidéos |
| ai-boost/awesome-harness-engineering | M0 veille | liste de pistes, pas de code |
| anative-lab/awesome-self-evolving-agents | M0 veille | liste de travaux, pas de code |
| andyrewlee/awesome-agent-orchestrators | M0 veille | liste de pistes, pas de code |
| antonio86itna/claude-code-efficiency-guide | M0 veille | guide ou liste, pas de code |
| charlesq9/self-evolving-agents | M0 veille | liste de travaux, pas de code |
| congvmit/awesome-llm-token-reduction | M0 veille | guide ou liste, pas de code |
| devinpleuler/analytics-handbook | M0 veille | manuel Python MIT, base de méthode |
| eddwebster/football_analytics | M0 veille | plus grosse liste du domaine, à jour 2025 |
| hesreallyhim/awesome-claude-code | M0 veille | liste de pistes, pas de code |
| jihoo-kim/awesome-context-engineering | M0 veille | guide ou liste, pas de code |
| jim-schwoebel/awesome_ai_agents | M0 veille | liste de pistes, pas de code |
| lobehub/awesome-rsi | M0 veille | liste de travaux, pas de code |
| meirtz/awesome-context-engineering | M0 veille | guide ou liste, pas de code |
| nirdiamant/agents-towards-production | M0 veille | liste de pistes, pas de code |
| nirdiamant/genai_agents | M0 veille | liste de pistes, pas de code |
| ravinperera/ai-token-efficiency-playbook | M0 veille | guide ou liste, pas de code |
| selfimproving-agent/awesome-self-improving-agents | M0 veille | liste de travaux, pas de code |
| shanraisshan/claude-code-best-practice | M0 veille | guide ou liste, pas de code |
| wkqdzkd/awesome-reliable-self-evolving-agents | M0 veille | liste de travaux, pas de code |
| jfjelstul/worldcup | M1 données | base Coupe du monde complète ; pas de licence |
| m3mons/flashscorescraper | M1 données | Flashscore couvre les ligues sud-américaines ; 13 étoiles, à surveiller |
| machina-sports/sports-skills | M1 données | skills d'agent pour données sportives en direct, MIT |
| pseudo-r/public-sofascore-api | M1 données | doc des endpoints Sofascore, qui couvre les ligues sud-américaines |
| withqwerty/football-docs | M1 données | doc des fournisseurs pour agents ; pas de licence |
| withqwerty/open-football | M1 données | carte à jour des sources ouvertes : sert à choisir les collecteurs |
| anyoptimization/pymoo | M10 auto-amélioration | multi-objectifs (précision + rendement) plus tard |
| chrisworsey55/atlas-gic | M10 auto-amélioration | agents de trading auto-améliorants, proche des paris |
| human-agent-society/coral | M10 auto-amélioration | recherche autonome avec notation |
| karpathy/autoresearch | M10 auto-amélioration | boucle d'expériences autonome ; pas de licence |
| microsoft/flaml | M10 auto-amélioration | AutoML léger quand il y aura plus de variables |
| quantaalpha/quantaalpha | M10 auto-amélioration | découverte de facteurs prédictifs, transposable ; pas de licence |
| trevorstephens/gplearn | M10 auto-amélioration | formules lisibles par régression symbolique |
| mlflow/mlflow | M11 suivi | si les expériences dépassent ce que le JSONL gère |
| jakeyk11/football-data-analytics | M12 rapports | outils d'analyse et de viz |
| alan-turing-institute/footballtournamentprediction | M3 modèles | tournois internationaux (bayésien) |
| hicruben/world-cup-2026-prediction-model | M3 modèles | Elo + Dixon-Coles + Monte Carlo, JS |
| jetqiao/football-prediction-skill | M3 modèles | skill Claude Dixon-Coles + backtest |
| kochlisgit/prophitbet-soccer-bets-predictor | M3 modèles | variables de forme à reprendre ; app complète, MIT |
| mauroandretta/aifootballpredictions | M3 modèles | marché Over 2,5 |
| mhaythornthwaite/football_prediction_project | M3 modèles | dépend d'api-football payante |
| mjhajharia/pydata21 | M3 modèles | bayésien hiérarchique PyMC |
| nickpadd/europeanfootballleaguepredictor | M3 modèles | même approche que poisson-v1 |
| ronyka77/soccerpredictor_byrichardszita | M3 modèles | pipeline ML avancé |
| tanamsethi31/footymodel | M3 modèles | compositions + validation walk-forward ; pas de licence |
| turingism/worldcup-predictor | M3 modèles | auto-calibration |
| withqwerty/nutmeg | M3 modèles | boîte à outils d'analyse ; pas de licence |
| yixuuuan/pm-watcher | M3 modèles | calibration des marchés de prédiction |
| andrewsimplebet/expected_goals_deep_dive | M4 métriques | méthode de calibration xG |
| friends-of-tracking-data-fotd/laurieontracking | M4 métriques | code de référence tracking |
| friends-of-tracking-data-fotd/soccermaticsforpython | M4 métriques | cours de méthode |
| impectapi/open-data | M4 métriques | licence propriétaire Impect |
| ml-kuleuven/soccer_xg | M4 métriques | entraînement xG, inactif depuis 2024 |
| skillcorner/opendata | M4 métriques | 10 matchs de tracking seulement |
| unravelsports/unravelsports | M4 métriques | graphes sur tracking |
| ussoccerfederation/ussf_ssac_23_soccer_gnn | M4 métriques | GNN sur tracking |
| lm-sys/routellm | M5 connexion LLM | routage par difficulté ; inactif depuis 2024 |
| mozilla-ai/any-llm | M5 connexion LLM | plan B si LiteLLM pose problème |
| doriandarko/make-it-heavy | M6 délibération | agents parallèles + synthèse |
| karpathy/llm-council | M6 délibération | schéma retenu pour la fusion (avis, notation croisée, synthèse) ; pas de licence → réécrit, pas copié |
| thg-muc/tip-genius | M6 délibération | pronostics LLM + cotes |
| togethercomputer/moa | M6 délibération | Mixture-of-Agents : couches d'agrégation, Apache-2.0 |
| wzk1015/worldcuparena | M6 délibération | protocole pour évaluer des LLM sur de vrais matchs, MIT |
| dagucloud/dagu | M7 pipeline | alternative ultra-légère (cron + DAG YAML), GPL-3.0 |
| dbos-inc/dbos-transact-py | M7 pipeline | workflows durables sur Postgres, Python |
| wlrwx/football-engine | M7 pipeline | automatisation par GitHub Actions ; pas de licence |
| getzep/graphiti | M8 mémoire | graphe temporel (faits avec dates de validité) : piste si la mémoire JSONL sature |
| othmanadi/planning-with-files | M8 mémoire | principe déjà appliqué (checkpoint + journal) |

## REDONDANT (143)

| Dépôt | Module | Motif |
|---|---|---|
| amosbastian/understat | M1 données | couvert par soccerdata |
| datasets/football-datasets | M1 données | même origine que xgabora (football-data.co.uk) |
| felipeall/transfermarkt-api | M1 données | transfermarkt-datasets donne la même chose sans scraping |
| footballcsv/england | M1 données | couvert par xgabora (E0) |
| jalapic/engsoccerdata | M1 données | R, sans licence, couvert par xgabora |
| openfootball/england | M1 données | couvert par xgabora (E0) |
| openfootball/worldcup | M1 données | même contenu que worldcup.json |
| openfootball/worldcup.json | M1 données | couvert par international_results |
| oseymour/scraperfc | M1 données | couvert par soccerdata ; GPL-3.0 |
| osvaldomx/underdata | M1 données | couvert par soccerdata |
| salimt/football-datasets | M1 données | Transfermarkt déjà couvert par transfermarkt-datasets ; pas de licence |
| adaptive-intelligent-robotics/qdax | M10 auto-amélioration | Optuna couvre le réglage ; algorithme génétique inutile ici |
| ahmedfgad/geneticalgorithmpython | M10 auto-amélioration | Optuna couvre le réglage ; algorithme génétique inutile ici |
| autogluon/autogluon | M10 auto-amélioration | AutoML lourd ; à reconsidérer avec plus de variables |
| automl/auto-sklearn | M10 auto-amélioration | AutoML lourd ; à reconsidérer avec plus de variables |
| automl/smac3 | M10 auto-amélioration | Optuna retenu |
| cma-es/pycma | M10 auto-amélioration | Optuna couvre le réglage ; algorithme génétique inutile ici |
| deap/deap | M10 auto-amélioration | Optuna couvre le réglage ; algorithme génétique inutile ici |
| emi-group/evox | M10 auto-amélioration | Optuna couvre le réglage ; algorithme génétique inutile ici |
| epistasislab/tpot | M10 auto-amélioration | AutoML lourd ; à reconsidérer avec plus de variables |
| facebookresearch/nevergrad | M10 auto-amélioration | Optuna couvre le réglage ; algorithme génétique inutile ici |
| gepa-ai/gepa | M10 auto-amélioration | intégré à DSPy |
| giacomelli/geneticsharp | M10 auto-amélioration | Optuna couvre le réglage ; algorithme génétique inutile ici |
| guofei9987/scikit-opt | M10 auto-amélioration | Optuna couvre le réglage ; algorithme génétique inutile ici |
| hyperopt/hyperopt | M10 auto-amélioration | Optuna retenu |
| icaros-usc/pyribs | M10 auto-amélioration | Optuna couvre le réglage ; algorithme génétique inutile ici |
| jenetics/jenetics | M10 auto-amélioration | Optuna couvre le réglage ; algorithme génétique inutile ici |
| keras-team/keras-tuner | M10 auto-amélioration | Optuna retenu |
| linshenkx/prompt-optimizer | M10 auto-amélioration | optimisation de prompts : DSPy retenu pour test |
| lucidrains/lion-pytorch | M10 auto-amélioration | Optuna couvre le réglage ; algorithme génétique inutile ici |
| ludwig-ai/ludwig | M10 auto-amélioration | AutoML lourd ; à reconsidérer avec plus de variables |
| maxhalford/eaopt | M10 auto-amélioration | Optuna couvre le réglage ; algorithme génétique inutile ici |
| meta-llama/prompt-ops | M10 auto-amélioration | optimisation de prompts : DSPy retenu pour test |
| microsoft/promptwizard | M10 auto-amélioration | optimisation de prompts : DSPy retenu pour test |
| microsoft/sammo | M10 auto-amélioration | optimisation de prompts : DSPy retenu pour test |
| microsoft/skillopt | M10 auto-amélioration | optimisation de prompts : DSPy retenu pour test |
| nnaisense/evotorch | M10 auto-amélioration | Optuna couvre le réglage ; algorithme génétique inutile ici |
| ray-project/ray | M10 auto-amélioration | Optuna retenu |
| roberttlange/evosax | M10 auto-amélioration | Optuna couvre le réglage ; algorithme génétique inutile ici |
| salesforceairesearch/promptomatix | M10 auto-amélioration | optimisation de prompts : DSPy retenu pour test |
| zou-group/textgrad | M10 auto-amélioration | optimisation de prompts : DSPy retenu pour test |
| ctrlb-hq/ctrlb-decompose | M2 collecte presse | Crawl4AI + Trafilatura couvrent la presse |
| docling-project/docling | M2 collecte presse | Crawl4AI + Trafilatura couvrent la presse |
| vectifyai/pageindex | M2 collecte presse | Crawl4AI + Trafilatura couvrent la presse |
| callumfm/dixon-coles | M3 modèles | couvert par penaltyblog |
| adaline/gateway | M5 connexion LLM | LiteLLM couvre déjà ce rôle en Python |
| aimeos/prisma | M5 connexion LLM | LiteLLM couvre déjà ce rôle en Python |
| aklivity/zilla | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| andrewyng/aisuite | M5 connexion LLM | LiteLLM couvre déjà ce rôle en Python |
| apiparklab/apipark | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| bricks-cloud/bricksllm | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| casdoor/casdoor | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| cheaper-inference/omniroute | M5 connexion LLM | passerelle 375 fournisseurs dont gratuits ; LiteLLM suffit, risque CGU sur les gratuits |
| coaidev/coai | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| commonstackai/uncommonroute | M5 connexion LLM | routage : LiteLLM gère repli et choix de modèle |
| davidecolombo/local-mcp | M5 connexion LLM | Ollama couvre le modèle local |
| enterpilot/gomodel | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| ggml-org/llama.cpp | M5 connexion LLM | moteur sous Ollama |
| helicone/ai-gateway | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| jonigl/mcp-client-for-ollama | M5 connexion LLM | Ollama couvre le modèle local |
| katanemo/plano | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| looplj/axonhub | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| mastra-ai/mastra | M5 connexion LLM | LiteLLM couvre déjà ce rôle en Python |
| maximhq/bifrost | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| mirrowel/llm-api-key-proxy | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| mnfst/llm-gateway | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| mozilla-ai/otari | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| mudler/localai | M5 connexion LLM | Ollama couvre le modèle local |
| nadirrouter/nadirclaw | M5 connexion LLM | routage : LiteLLM gère repli et choix de modèle |
| nomic-ai/gpt4all | M5 connexion LLM | Ollama couvre le modèle local |
| nvidia-nemo/switchyard | M5 connexion LLM | routage : LiteLLM gère repli et choix de modèle |
| openai/openai-agents-python | M5 connexion LLM | LiteLLM couvre déjà ce rôle en Python |
| portkey-ai/gateway | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| quantumnous/new-api | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| simonw/llm | M5 connexion LLM | LiteLLM couvre déjà ce rôle en Python |
| smg-project/smg | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| songquanpeng/one-api | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| tbphp/gpt-load | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| theagentrouter/agent-router | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| theopenco/llmgateway | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| tyktechnologies/tyk | M5 connexion LLM | passerelle serveur : LiteLLM fait SDK et proxy, inutile d'en ajouter une |
| vercel/ai | M5 connexion LLM | LiteLLM couvre déjà ce rôle en Python |
| sepandhaghighi/wc2026 | M6 délibération | même idée que worldcuparena |
| agentjido/jido | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| camel-ai/camel | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| crewaiinc/crewai | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| deepset-ai/haystack | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| demondamon/agenticx | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| emiyaaaaa/hivemind | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| google/adk-go | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| google/adk-java | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| google/adk-python | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| internlm/mindsearch | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| jetbrains/koog | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| kocoro-lab/shannon | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| kyegomez/swarms | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| langroid/langroid | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| lofcz/llmtornado | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| lupantech/agentflow | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| massgen/massgen | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| microsoft/agent-framework | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| microsoft/agent-framework-go | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| microsoft/autogen | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| open-multi-agent/open-multi-agent | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| rcortx/kiwiq | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| strands-agents/harness-sdk | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| vrsen/agency-swarm | M7 agents | framework d'agents : un seul suffit, LangGraph retenu pour test |
| apache/airflow | M7 pipeline | orchestrateur de pipeline : Prefect retenu pour test |
| apache/dolphinscheduler | M7 pipeline | orchestrateur de pipeline : Prefect retenu pour test |
| apache/hop | M7 pipeline | orchestrateur de pipeline : Prefect retenu pour test |
| argoproj/argo-workflows | M7 pipeline | orchestrateur de pipeline : Prefect retenu pour test |
| dagster-io/dagster | M7 pipeline | orchestrateur de pipeline : Prefect retenu pour test |
| flyteorg/flyte | M7 pipeline | orchestrateur de pipeline : Prefect retenu pour test |
| hatchet-dev/hatchet | M7 pipeline | exécution durable : surdimensionné pour une collecte quotidienne |
| inngest/inngest | M7 pipeline | exécution durable : surdimensionné pour une collecte quotidienne |
| kedro-org/kedro | M7 pipeline | orchestrateur de pipeline : Prefect retenu pour test |
| kestra-io/kestra | M7 pipeline | orchestrateur de pipeline : Prefect retenu pour test |
| mage-ai/mage-ai | M7 pipeline | orchestrateur de pipeline : Prefect retenu pour test |
| netflix/maestro | M7 pipeline | exécution durable : surdimensionné pour une collecte quotidienne |
| netflix/metaflow | M7 pipeline | orchestrateur de pipeline : Prefect retenu pour test |
| spotify/luigi | M7 pipeline | orchestrateur de pipeline : Prefect retenu pour test |
| temporalio/temporal | M7 pipeline | exécution durable : surdimensionné pour une collecte quotidienne |
| vercel/workflow | M7 pipeline | exécution durable : surdimensionné pour une collecte quotidienne |
| zenml-io/zenml | M7 pipeline | orchestrateur de pipeline : Prefect retenu pour test |
| cocoindex-io/cocoindex | M8 mémoire | la mémoire JSONL versionnée couvre le besoin |
| mem0ai/mem0 | M8 mémoire | la mémoire JSONL versionnée couvre le besoin |
| topoteretes/cognee | M8 mémoire | la mémoire JSONL versionnée couvre le besoin |
| 3dagentworld/toolkit-for-prompt-compression | M9 tokens | compression de prompts : LLMLingua est la référence |
| codefuse-ai/modelcache | M9 tokens | cache : LiteLLM a un cache intégré ; le cache exact maison suffit |
| context-engine-ai/context-engine | M9 tokens | compression de prompts : LLMLingua est la référence |
| gatalifeltd/economizer-skills | M9 tokens | même principe que caveman |
| green-pt/honey-for-devs | M9 tokens | même principe que caveman |
| ikislay/copium | M9 tokens | compression de prompts : LLMLingua est la référence |
| jaypokale/chisle | M9 tokens | même principe que caveman |
| jgravelle/jdatamunch-mcp | M9 tokens | voir TOON |
| jia-gao/leanctx | M9 tokens | compression de prompts : LLMLingua est la référence |
| messkan/prompt-cache | M9 tokens | cache : LiteLLM a un cache intégré ; le cache exact maison suffit |
| mostafamoq/tooner | M9 tokens | voir TOON |
| openai/tiktoken | M9 tokens | LiteLLM compte déjà les tokens |
| thu-nics/c2c | M9 tokens | cache : LiteLLM a un cache intégré ; le cache exact maison suffit |
| upstash/semantic-cache | M9 tokens | cache : LiteLLM a un cache intégré ; le cache exact maison suffit |
| yvgude/lean-ctx | M9 tokens | compression de prompts : LLMLingua est la référence |
| zilliztech/gptcache | M9 tokens | cache : LiteLLM a un cache intégré ; le cache exact maison suffit |

## REJETER (270)

| Dépôt | Module | Motif |
|---|---|---|
| 777genius/agent-teams-ai | DEV | tableau de bord d'agents de programmation |
| a5c-ai/babysitter | DEV | orchestre des agents de programmation, pas la machine |
| abhi1693/openclaw-mission-control | DEV | archivé par son auteur |
| activeing123/mcptoon | DEV | réduit les outils MCP de l'outil de dev ; la machine n'utilise pas MCP |
| agentsmesh/agentsmesh | DEV | tableau de bord d'agents de programmation |
| agusrdz/chop | DEV | compresse les sorties de terminal de l'outil de dev, pas les appels de la machine |
| aider-ai/aider | DEV | agent de programmation, pas un composant de la machine |
| alexgreensh/token-optimizer | DEV | optimise Claude Code, pas la machine |
| alishahryar1/free-claude-code | DEV | ⚠ risque CGU |
| alvinunreal/oh-my-opencode-slim | DEV | orchestre des agents de programmation, pas la machine |
| awslabs/cli-agent-orchestrator | DEV | orchestre des agents de programmation, pas la machine |
| axiomcodeai/axiomcodegraph | DEV | index de code pour l'outil de dev |
| bloopai/vibe-kanban | DEV | orchestre des agents de programmation, pas la machine |
| bug-ops/mcp-execution | DEV | réduit les outils MCP de l'outil de dev ; la machine n'utilise pas MCP |
| builderz-labs/mission-control | DEV | tableau de bord d'agents de programmation |
| catlog22/claude-code-workflow | DEV | archivé par son auteur |
| charmbracelet/crush | DEV | agent de programmation, pas un composant de la machine |
| chesterra/cccc | DEV | orchestre des agents de programmation, pas la machine |
| cline/cline | DEV | agent de programmation, pas un composant de la machine |
| coderamp-labs/gitingest | DEV | empaquette un dépôt pour l'outil de dev |
| colbymchenry/codegraph | DEV | index de code pour l'outil de dev |
| continuedev/continue | DEV | agent de programmation, pas un composant de la machine |
| cytostack/openwolf | DEV | AGPL-3.0 |
| danau5tin/multi-agent-coding-system | DEV | orchestre des agents de programmation, pas la machine |
| decolua/9router | DEV | ⚠ risque CGU |
| dfkhelper/token-goat | DEV | optimise Claude Code, pas la machine |
| edouard-claude/snip | DEV | compresse les sorties de terminal de l'outil de dev, pas les appels de la machine |
| efrenbl/code-navigator | DEV | index de code pour l'outil de dev |
| elusznik/mcp-server-code-execution-mode | DEV | réduit les outils MCP de l'outil de dev ; la machine n'utilise pas MCP |
| fajarhide/omni | DEV | compresse les sorties de terminal de l'outil de dev, pas les appels de la machine |
| farion1231/cc-switch | DEV | outil pour l'éditeur de code, pas un composant de la machine |
| fkiene/llmtrim | DEV | compresse les sorties de terminal de l'outil de dev, pas les appels de la machine |
| gastownhall/gascity | DEV | orchestre des agents de programmation, pas la machine |
| gglucass/headroom-desktop | DEV | compresse les sorties de terminal de l'outil de dev, pas les appels de la machine |
| gman1911/claude-cognitive | DEV | optimise Claude Code, pas la machine |
| graphify-labs/graphify | DEV | index de code pour l'outil de dev |
| growth4u-systems/claude-token-hygiene | DEV | optimise Claude Code, pas la machine |
| gsd-build/get-shit-done | DEV | archivé par son auteur |
| hansipie/ecotokens | DEV | compresse les sorties de terminal de l'outil de dev, pas les appels de la machine |
| herdrdev/herdr | DEV | tableau de bord d'agents de programmation |
| hoangp8/tokless | DEV | optimise Claude Code, pas la machine |
| intrect-io/openswarm | DEV | orchestre des agents de programmation, pas la machine |
| iyadhkhalfallah/clauditor | DEV | optimise Claude Code, pas la machine |
| jayminwest/overstory | DEV | archivé par son auteur |
| jgravelle/jcodemunch-mcp | DEV | index de code pour l'outil de dev |
| jgravelle/jdocmunch-mcp | DEV | index de code pour l'outil de dev |
| johunsang/semble_rs | DEV | index de code pour l'outil de dev |
| justlovemaki/aiclient2api | DEV | ⚠ risque CGU ; GPL-3.0 |
| juyterman1000/entroly | DEV | compresse les sorties de terminal de l'outil de dev, pas les appels de la machine |
| kgt24k/mcp-tool-search | DEV | réduit les outils MCP de l'outil de dev ; la machine n'utilise pas MCP |
| kingstar-omega/claude-token-optimizer | DEV | optimise Claude Code, pas la machine |
| kittors/clirelay | DEV | outil pour l'éditeur de code, pas un composant de la machine |
| lap-platform/lap | DEV | réduit les outils MCP de l'outil de dev ; la machine n'utilise pas MCP |
| lidge-jun/opencodex | DEV | outil pour l'éditeur de code, pas un composant de la machine |
| lucasrosati/claude-code-memory-setup | DEV | optimise Claude Code, pas la machine |
| maciek-roboblog/claude-code-usage-monitor | DEV | optimise Claude Code, pas la machine |
| manojmallick/sigmap | DEV | index de code pour l'outil de dev |
| masurii/pi-rtk-optimizer | DEV | compresse les sorties de terminal de l'outil de dev, pas les appels de la machine |
| mikhail-tokarev/greenbelt | DEV | optimise Claude Code, pas la machine |
| moazbuilds/codemachine-cli | DEV | orchestre des agents de programmation, pas la machine |
| mufeedvh/code2prompt | DEV | empaquette un dépôt pour l'outil de dev |
| musistudio/claude-code-router | DEV | outil pour l'éditeur de code, pas un composant de la machine |
| mvschwarz/openrig | DEV | tableau de bord d'agents de programmation |
| nadimtuhin/claude-token-optimizer | DEV | optimise Claude Code, pas la machine |
| nanako0129/pilotfish | DEV | outil pour l'éditeur de code, pas un composant de la machine |
| nickcirv/engram | DEV | index de code pour l'outil de dev |
| ojuschugh1/sqz | DEV | compresse les sorties de terminal de l'outil de dev, pas les appels de la machine |
| omnigent-ai/omnigent | DEV | orchestre des agents de programmation, pas la machine |
| ooples/token-optimizer-mcp | DEV | optimise Claude Code, pas la machine |
| open-compress/claw-compactor | DEV | compresse les sorties de terminal de l'outil de dev, pas les appels de la machine |
| open-mercato/cezar | DEV | orchestre des agents de programmation, pas la machine |
| openai/codex-plugin-cc | DEV | outil pour l'éditeur de code, pas un composant de la machine |
| orchestratorinc/agent-orchestrator | DEV | orchestre des agents de programmation, pas la machine |
| oxygen-fragment/claude-modular | DEV | optimise Claude Code, pas la machine |
| paperclipai/paperclip | DEV | tableau de bord d'agents de programmation |
| paradevai/paradev | DEV | tableau de bord d'agents de programmation |
| paritok-official/paritok-4b-v1 | DEV | compresse les sorties de terminal de l'outil de dev, pas les appels de la machine |
| preset-io/agor | DEV | tableau de bord d'agents de programmation |
| ratel-ai/ratel | DEV | réduit les outils MCP de l'outil de dev ; la machine n'utilise pas MCP |
| redhat-et/ripwire | DEV | index de code pour l'outil de dev |
| router-for-me/cliproxyapi | DEV | ⚠ transforme des abonnements en API : risque CGU |
| ruvnet/ruflo | DEV | orchestre des agents de programmation, pas la machine |
| seemseam/claude_codex_bridge | DEV | outil pour l'éditeur de code, pas un composant de la machine |
| skibidiskib/ai-codex | DEV | index de code pour l'outil de dev |
| slopus/happy | DEV | outil pour l'éditeur de code, pas un composant de la machine |
| solaceproducts/solace-agent-mesh | DEV | tableau de bord d'agents de programmation |
| stablyai/orca | DEV | tableau de bord d'agents de programmation |
| stellarlinkco/myclaude | DEV | outil pour l'éditeur de code, pas un composant de la machine |
| the-open-engine/zeroshot | DEV | orchestre des agents de programmation, pas la machine |
| thedotmack/claude-mem | DEV | optimise Claude Code, pas la machine |
| tintinweb/pi-subagents | DEV | orchestre des agents de programmation, pas la machine |
| vdutts7/skills-not-mcp | DEV | réduit les outils MCP de l'outil de dev ; la machine n'utilise pas MCP |
| voltagent/awesome-claude-code-subagents | DEV | orchestre des agents de programmation, pas la machine |
| wshobson/agents | DEV | orchestre des agents de programmation, pas la machine |
| yamadashy/repomix | DEV | empaquette un dépôt pour l'outil de dev |
| yeachan-heo/oh-my-claudecode | DEV | orchestre des agents de programmation, pas la machine |
| yohey-w/multi-agent-shogun | DEV | orchestre des agents de programmation, pas la machine |
| yttrium400/reducethemtokens | DEV | empaquette un dépôt pour l'outil de dev |
| zdk/lowfat | DEV | compresse les sorties de terminal de l'outil de dev, pas les appels de la machine |
| zhnt/loushang | DEV | outil pour l'éditeur de code, pas un composant de la machine |
| zilliztech/claude-context | DEV | index de code pour l'outil de dev |
| zipengwu365/tomc | DEV | optimise Claude Code, pas la machine |
| abdullahtarek/football_analysis | HORS | analyse vidéo : hors périmètre (pas de vidéo) ; inactif depuis 2024-04 |
| agenta-ai/agenta | HORS | plateforme visuelle ; la machine est en code |
| architv/soccer-cli | HORS | simulation de jeu : hors périmètre ; inactif depuis 2023-05 |
| arztsamuel/applying_eanns | HORS | neuroévolution : inutile pour nos modèles |
| chatboxai/chatbox | HORS | interface de chat : la machine n'en a pas besoin |
| chatgptnextweb/nextchat | HORS | interface de chat : la machine n'en a pas besoin |
| chatlunalab/chatluna | HORS | interface de chat : la machine n'en a pas besoin |
| cherryhq/cherry-studio | HORS | interface de chat : la machine n'en a pas besoin |
| codereclaimers/neat-python | HORS | neuroévolution : inutile pour nos modèles |
| colgreen/sharpneat | HORS | neuroévolution : inutile pour nos modèles |
| ekkolearnai/ekko-studio | HORS | interface de chat : la machine n'en a pas besoin |
| emi-group/tensorneat | HORS | neuroévolution : inutile pour nos modèles |
| exo-explore/exo | HORS | grappe de machines |
| flowiseai/flowise | HORS | archivé par son auteur |
| gallagheraiden/footballsimulationengine | HORS | simulation de jeu : hors périmètre |
| greerviau/snakeai | HORS | neuroévolution : inutile pour nos modèles ; inactif depuis 2023-11 |
| hmzbo/football-analytics-with-deep-learning-and-computer-vision | HORS | analyse vidéo : hors périmètre (pas de vidéo) |
| iflytek/astron-agent | HORS | plateforme visuelle ; la machine est en code |
| inker/draw | HORS | simulation de jeu : hors périmètre |
| iofficeai/aionui | HORS | interface de chat : la machine n'en a pas besoin |
| janhq/jan | HORS | interface de chat : la machine n'en a pas besoin |
| labring/fastgpt | HORS | plateforme visuelle ; la machine est en code |
| langgenius/dify | HORS | plateforme visuelle, licence restrictive ; la machine est en code |
| lobehub/lobehub | HORS | interface de chat : la machine n'en a pas besoin |
| mintplex-labs/anything-llm | HORS | interface de chat : la machine n'en a pas besoin |
| mradovic38/football-analysis | HORS | analyse vidéo : hors périmètre (pas de vidéo) |
| n8n-io/n8n | HORS | plateforme visuelle, licence restrictive ; la machine est en code |
| open-webui/open-webui | HORS | interface de chat : la machine n'en a pas besoin |
| openfootmanager/openfootmanager | HORS | simulation de jeu : hors périmètre |
| oriveo/oriveo | HORS | interface de chat : la machine n'en a pas besoin |
| peter-ch/multineat | HORS | neuroévolution : inutile pour nos modèles |
| sdcb/chats | HORS | interface de chat : la machine n'en a pas besoin |
| soccernet/sn-gamestate | HORS | analyse vidéo : hors périmètre (pas de vidéo) |
| ssusnic/machine-learning-flappy-bird | HORS | neuroévolution : inutile pour nos modèles ; inactif depuis 2017-12 |
| triggerdotdev/trigger.dev | HORS | plateforme visuelle ; la machine est en code |
| tryolabs/soccer-video-analytics | HORS | analyse vidéo : hors périmètre (pas de vidéo) ; inactif depuis 2023-12 |
| uber-research/deep-neuroevolution | HORS | neuroévolution : inutile pour nos modèles ; inactif depuis 2024-01 |
| vllm-project/vllm | HORS | serveur GPU |
| windmill-labs/windmill | HORS | plateforme visuelle ; la machine est en code |
| xviniette/flappylearning | HORS | neuroévolution : inutile pour nos modèles ; inactif depuis 2023-11 |
| zoxexivo/open-football | HORS | simulation de jeu : hors périmètre |
| diegopastor/awesome-football-analytics | M0 veille | liste de liens, rien à brancher ; inactif depuis 2022-03 |
| fcrstats/coordinatefc | M0 veille | liste de liens, rien à brancher ; inactif depuis 2022-07 |
| flowuenne/soccer_data_analytics_resources | M0 veille | liste de liens, rien à brancher ; inactif depuis 2024-08 |
| janvanhaaren/soccer-analytics-resources | M0 veille | liste de liens, rien à brancher ; inactif depuis 2021-11 |
| larsmaurath/soccer-analytics-library | M0 veille | liste de liens, rien à brancher ; inactif depuis 2022-10 |
| matiasmascioto/awesome-soccer-analytics | M0 veille | liste de liens, rien à brancher ; inactif depuis 2020-11 |
| swayoleg/football-catalogs | M0 veille | liste de liens, rien à brancher |
| adror1/nwslr | M1 données | jeu de données ancien, partiel ou hors des championnats visés ; inactif depuis 2022-09 |
| apdmatos/sofascore-api | M1 données | scraper isolé, peu suivi, couvert par soccerdata ; inactif depuis 2022-07 |
| chonalchendo/footcrawl | M1 données | scraper isolé, peu suivi, couvert par soccerdata |
| chrismusson/fbref_db | M1 données | archivé par son auteur |
| deanpatel2/webscraper-premdata | M1 données | scraper isolé, peu suivi, couvert par soccerdata ; inactif depuis 2021-08 |
| ewenme/transfers | M1 données | jeu de données ancien, partiel ou hors des championnats visés ; inactif depuis 2023-04 |
| fcrstats/statsbomb_womensdata | M1 données | jeu de données ancien, partiel ou hors des championnats visés ; inactif depuis 2018-09 |
| hoyishian/footballwebscraper | M1 données | scraper isolé, peu suivi, couvert par soccerdata |
| hugomathien/football-data-collection | M1 données | jeu de données ancien, partiel ou hors des championnats visés ; inactif depuis 2018-11 |
| irsooti/football-data-scraper | M1 données | scraper isolé, peu suivi, couvert par soccerdata ; inactif depuis 2023-01 |
| jaseziv/worldfootballr | M1 données | archivé par son auteur |
| jokecamp/footballdata | M1 données | jeu de données ancien, partiel ou hors des championnats visés ; inactif depuis 2023-12 |
| liamculligan/football-data-scraper | M1 données | scraper isolé, peu suivi, couvert par soccerdata ; inactif depuis 2017-01 |
| lsv/fifa-worldcup-2018 | M1 données | jeu de données ancien, partiel ou hors des championnats visés ; inactif depuis 2019-10 |
| luukhopman/football-logos | M1 données | jeu de données ancien, partiel ou hors des championnats visés |
| omarbadrani/football-scraper-pro | M1 données | scraper isolé, peu suivi, couvert par soccerdata |
| openfootball/openfootball.github.io | M1 données | jeu de données ancien, partiel ou hors des championnats visés |
| pseudo-r/sportly | M1 données | scraper isolé, peu suivi, couvert par soccerdata |
| rezarahiminia/free-api-worldcup2022 | M1 données | jeu de données ancien, partiel ou hors des championnats visés ; inactif depuis 2022-11 |
| rjtavares/football-crunching | M1 données | jeu de données ancien, partiel ou hors des championnats visés ; inactif depuis 2021-12 |
| s1m0n38/soccerapi | M1 données | scraper isolé, peu suivi, couvert par soccerdata ; inactif depuis 2022-12 |
| sportdb/sport.db | M1 données | jeu de données ancien, partiel ou hors des championnats visés |
| tadeq/flashscore-scraper | M1 données | scraper isolé, peu suivi, couvert par soccerdata ; inactif depuis 2022-07 |
| tarun7r/premier-league-api | M1 données | scraper isolé, peu suivi, couvert par soccerdata |
| tunjayoff/sofascore_scraper | M1 données | scraper isolé, peu suivi, couvert par soccerdata |
| victorstdev/sofascore-api-stats | M1 données | scraper isolé, peu suivi, couvert par soccerdata ; inactif depuis 2024-03 |
| wcesarpsv/flashscorerepo | M1 données | scraper isolé, peu suivi, couvert par soccerdata |
| zekda96/football-scrapers | M1 données | scraper isolé, peu suivi, couvert par soccerdata |
| a-evo-lab/a-evolve | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| agno-agi/agno | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| aiming-lab/agent0 | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| aiwaves-cn/agents | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss ; inactif depuis 2024-09 |
| amap-ml/skillclaw | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| anative-lab/evoagentx | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| aymenfurter/microagents | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss ; inactif depuis 2024-03 |
| evermind-ai/raven | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| evomap/evolver | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| facebookresearch/drzero | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| facebookresearch/hyperagents | M10 auto-amélioration | projet de recherche, sans lien direct avec un modèle de pronostic |
| google-deepmind/alphaevolve_results | M10 auto-amélioration | projet de recherche, sans lien direct avec un modèle de pronostic |
| google/evojax | M10 auto-amélioration | archivé par son auteur |
| greyhaven-ai/autocontext | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| handcraftsman/geneticalgorithmswithpython | M10 auto-amélioration | inactif depuis 2022-10 |
| hexo-ai/sia | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| hkuds/autoagent | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| human-agent-society/reef | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| jennyzzt/dgm | M10 auto-amélioration | projet de recherche, sans lien direct avec un modèle de pronostic |
| kulaxyz/self-learning-skills | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| letta-ai/letta | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| ljvmiranda921/pyswarms | M10 auto-amélioration | inactif depuis 2024-08 |
| lsdefine/genericagent | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| memtensor/memos | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| metauto-ai/gptswarm | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| microsoft/nni | M10 auto-amélioration | archivé par son auteur |
| mikekelly/agentk | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss ; inactif depuis 2024-09 |
| mindsdb/anton | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| modelscope/agentevolver | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| morvanzhou/evolutionary-algorithm | M10 auto-amélioration | inactif depuis 2023-11 |
| nousresearch/hermes-agent-self-evolution | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| oliveirabruno01/babyagi-asi | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss ; inactif depuis 2023-06 |
| os-copilot/os-copilot | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss ; inactif depuis 2024-09 |
| primaryobjects/ai-programmer | M10 auto-amélioration | projet de recherche, sans lien direct avec un modèle de pronostic |
| primeintellect-ai/prime-agent | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| pskoett/self-improving-agent | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| rohitg00/pro-workflow | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| sakanaai/ai-scientist | M10 auto-amélioration | projet de recherche, sans lien direct avec un modèle de pronostic |
| sakanaai/evolutionary-model-merge | M10 auto-amélioration | projet de recherche, sans lien direct avec un modèle de pronostic |
| sakanaai/shinkaevolve | M10 auto-amélioration | projet de recherche, sans lien direct avec un modèle de pronostic |
| scikit-optimize/scikit-optimize | M10 auto-amélioration | archivé par son auteur |
| shengranhu/adas | M10 auto-amélioration | projet de recherche, sans lien direct avec un modèle de pronostic |
| viktoraxelsen/memskill | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| volcengine/openviking | M10 auto-amélioration | agent généraliste auto-évolutif : pas de critère mesurable comme la log-loss |
| wanshuiyin/auto-claude-code-research-in-sleep | M10 auto-amélioration | projet de recherche, sans lien direct avec un modèle de pronostic |
| wandb/wandb | M11 suivi | service en ligne |
| dato-futbol/passing-networks | M12 rapports | visualisation R ou spécifique ; inactif depuis 2021-10 |
| ryo-n7/soccer_ggplots | M12 rapports | visualisation R ou spécifique ; inactif depuis 2024-06 |
| tom-draper/pldashboard | M12 rapports | visualisation R ou spécifique |
| torvaney/ggsoccer | M12 rapports | visualisation R ou spécifique ; inactif depuis 2024-10 |
| acredjb/fbp | M3 modèles | projet de démonstration, rien de plus que poisson-v1 ; inactif depuis 2024-06 |
| amar0302/footballmatchpredictionpoisson | M3 modèles | projet de démonstration, rien de plus que poisson-v1 ; inactif depuis 2024-04 |
| bradleygrantham/pl-predictions-using-fifa | M3 modèles | projet de démonstration, rien de plus que poisson-v1 ; inactif depuis 2022-11 |
| cookpete/soccer-predictor | M3 modèles | projet de démonstration, rien de plus que poisson-v1 ; inactif depuis 2017-09 |
| czl0325/football_frontend | M3 modèles | projet de démonstration, rien de plus que poisson-v1 |
| dagbolade/all_leagues-_prediction | M3 modèles | projet de démonstration, rien de plus que poisson-v1 |
| didierrlopes/momentum-football-bets | M3 modèles | projet de démonstration, rien de plus que poisson-v1 ; inactif depuis 2021-12 |
| dosinga/football_predictions | M3 modèles | projet de démonstration, rien de plus que poisson-v1 |
| flooorent/football-elo-ratings | M3 modèles | projet de démonstration, rien de plus que poisson-v1 ; inactif depuis 2018-05 |
| googlecloudplatform/ipython-soccer-predictions | M3 modèles | archivé par son auteur |
| hansichan/soccerpredictor | M3 modèles | projet de démonstration, rien de plus que poisson-v1 |
| jrbadiabo/bet-on-sibyl | M3 modèles | projet de démonstration, rien de plus que poisson-v1 ; inactif depuis 2017-02 |
| kseligga/qatar2022-elo-simulation | M3 modèles | projet de démonstration, rien de plus que poisson-v1 ; inactif depuis 2022-11 |
| monomania/foot | M3 modèles | projet de démonstration, rien de plus que poisson-v1 ; inactif depuis 2021-03 |
| msoczi/football_predictions | M3 modèles | projet de démonstration, rien de plus que poisson-v1 ; inactif depuis 2024-03 |
| rvdmaazen/fivethirtyeight-soccer-predictions | M3 modèles | projet de démonstration, rien de plus que poisson-v1 ; inactif depuis 2023-05 |
| ryanscodes/dixon-coles-football-predictor | M3 modèles | projet de démonstration, rien de plus que poisson-v1 ; inactif depuis 2016-08 |
| salikfaisal/club_soccer_season_projections | M3 modèles | projet de démonstration, rien de plus que poisson-v1 |
| sashml/betalytics | M3 modèles | projet de démonstration, rien de plus que poisson-v1 |
| tanjt107/football-prediction | M3 modèles | projet de démonstration, rien de plus que poisson-v1 |
| umitkaanusta/mactahminbotu | M3 modèles | projet de démonstration, rien de plus que poisson-v1 |
| woongbinchoi/english-premier-league-prediction | M3 modèles | projet de démonstration, rien de plus que poisson-v1 ; inactif depuis 2021-09 |
| xzhangfox/football-prediction-by-bayesian-method | M3 modèles | projet de démonstration, rien de plus que poisson-v1 ; inactif depuis 2020-02 |
| alek050/databallpy | M4 métriques | données de tracking : nous n'en avons pas |
| dato-futbol/xg-model | M4 métriques | inactif ou dépend de données que nous n'avons pas ; inactif depuis 2023-08 |
| hyunsungkim-ds/soccercpd | M4 métriques | données de tracking : nous n'en avons pas |
| jogall/soccermatics | M4 métriques | données de tracking : nous n'en avons pas ; inactif depuis 2021-08 |
| ml-kuleuven/etsy | M4 métriques | données de tracking : nous n'en avons pas ; inactif depuis 2024-05 |
| ofirmg/football2vec | M4 métriques | inactif ou dépend de données que nous n'avons pas ; inactif depuis 2021-10 |
| unravelsports/fast-forward | M4 métriques | données de tracking : nous n'en avons pas |
| tensorzero/tensorzero | M5 connexion LLM | archivé par son auteur |
| 99xagency/godmodeskill | M6 délibération | conseil branché sur Claude Code (outil de dev), pas sur la machine |
| bencmorrison/modelguild | M6 délibération | conseil branché sur Claude Code (outil de dev), pas sur la machine |
| dezoito/ollama-grid-search | M6 délibération | conseil branché sur Claude Code (outil de dev), pas sur la machine |
| frescodicredito/rasputin | M6 délibération | conseil branché sur Claude Code (outil de dev), pas sur la machine |
| kingedwardi/second-opinion | M6 délibération | conseil branché sur Claude Code (outil de dev), pas sur la machine |
| leeroo-ai/mergoo | M6 délibération | conseil branché sur Claude Code (outil de dev), pas sur la machine ; inactif depuis 2024-08 |
| lm-sys/fastchat | M6 délibération | conseil branché sur Claude Code (outil de dev), pas sur la machine |
| salutaris91/llm-council-mcp-server | M6 délibération | conseil branché sur Claude Code (outil de dev), pas sur la machine |
| yonk-labs/abe | M6 délibération | conseil branché sur Claude Code (outil de dev), pas sur la machine |
| camel-ai/owl | M7 agents | pas de licence |
| openai/swarm | M7 agents | éducatif, remplacé par openai-agents |

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
