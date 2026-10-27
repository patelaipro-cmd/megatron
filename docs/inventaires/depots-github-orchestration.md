# 108 dépôts GitHub d'orchestration

Relevé du 27/10/2026 via la recherche GitHub (tri par étoiles). ⭐ = étoiles, tous actifs en 2026 sauf mention contraire.
Deux familles : **orchestration d'agents IA** (sections 1 à 4) et **orchestration de workflows / pipelines de données** (sections 5 et 6).
★ = pertinent pour Megatron (pipeline : collecte → modèles → pronostics → suivi des résultats).

> Les étoiles de certains dépôts récents d'agents IA paraissent gonflées. Il vaut mieux juger sur l'activité et la documentation.

## 1. Frameworks multi-agents (code)

| # | Dépôt | ⭐ | Langage | Contenu |
|---|---|---|---|---|
| 1 | [microsoft/autogen](https://github.com/microsoft/autogen) | 61588 | Python | Framework d'IA agentique de Microsoft |
| 2 | [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) ★ | 60174 | Python | Équipes d'agents à rôles (ex. « scout », « analyste », « parieur ») |
| 3 | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) ★ | 43991 | Python | Agents sous forme de graphes avec état, très utilisé en production |
| 4 | [agno-agi/agno](https://github.com/agno-agi/agno) | 42920 | Python | Plateforme d'agents qui s'améliorent |
| 5 | [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | 30334 | Python | SDK multi-agents d'OpenAI |
| 6 | [mastra-ai/mastra](https://github.com/mastra-ai/mastra) | 29122 | TypeScript | Framework d'agents et workflows en TS |
| 7 | [deepset-ai/haystack](https://github.com/deepset-ai/haystack) | 26858 | Python | Orchestration IA et RAG en production |
| 8 | [openai/swarm](https://github.com/openai/swarm) | 22079 | Python | Orchestration multi-agents légère (éducatif) |
| 9 | [google/adk-python](https://github.com/google/adk-python) | 22021 | Python | Agent Development Kit de Google |
| 10 | [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) ★ | 20905 | Python | Agents typés, sorties structurées fiables |
| 11 | [camel-ai/camel](https://github.com/camel-ai/camel) | 17980 | Python | Framework multi-agents de recherche |
| 12 | [camel-ai/owl](https://github.com/camel-ai/owl) | 20168 | Python | Main-d'œuvre multi-agents pour tâches réelles |
| 13 | [microsoft/agent-framework](https://github.com/microsoft/agent-framework) | 14342 | Python/.NET | Construire, orchestrer et déployer des agents |
| 14 | [anthropics/claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python) ★ | 8362 | Python | SDK officiel pour piloter Claude comme agent dans ton code |
| 15 | [strands-agents/harness-sdk](https://github.com/strands-agents/harness-sdk) | 8967 | Python | SDK d'agents en production (AWS) |
| 16 | [google/adk-go](https://github.com/google/adk-go) | 8904 | Go | ADK Google en Go |
| 17 | [kyegomez/swarms](https://github.com/kyegomez/swarms) | 7306 | Python | Orchestration multi-agents « entreprise » |
| 18 | [open-multi-agent/open-multi-agent](https://github.com/open-multi-agent/open-multi-agent) | 7025 | TypeScript | Runtime d'agents avec validations durables |
| 19 | [JetBrains/koog](https://github.com/JetBrains/koog) | 4638 | Kotlin | Agents JVM tolérants aux pannes |
| 20 | [VRSEN/agency-swarm](https://github.com/VRSEN/agency-swarm) | 4617 | Python | Orchestration multi-agents fiable |
| 21 | [langroid/langroid](https://github.com/langroid/langroid) | 4120 | Python | Programmation multi-agents |
| 22 | [ANative-Lab/EvoAgentX](https://github.com/ANative-Lab/EvoAgentX) | 3404 | Python | Écosystème d'agents auto-évolutifs |
| 23 | [Kocoro-lab/Shannon](https://github.com/Kocoro-lab/Shannon) | 2303 | Go | Orchestration multi-agents pour la production |
| 24 | [rcortx/kiwiq](https://github.com/rcortx/kiwiq) | 2171 | Python | Agents définis en JSON |
| 25 | [lupantech/AgentFlow](https://github.com/lupantech/AgentFlow) | 2069 | Python | Optimisation de systèmes agentiques |
| 26 | [agentjido/jido](https://github.com/agentjido/jido) | 1896 | Elixir | Agents autonomes distribués |
| 27 | [google/adk-java](https://github.com/google/adk-java) | 1758 | Java | ADK Google en Java |
| 28 | [Emiyaaaaa/HiveMind](https://github.com/Emiyaaaaa/HiveMind) | 1056 | Python | Runtime multi-agents avec état persistant |
| 29 | [DemonDamon/AgenticX](https://github.com/DemonDamon/AgenticX) | 731 | Python | Plateforme multi-agents SDK + CLI |
| 30 | [microsoft/agent-framework-go](https://github.com/microsoft/agent-framework-go) | 656 | Go | Agent Framework en Go |
| 31 | [lofcz/LLMTornado](https://github.com/lofcz/LLMTornado) | 649 | C# | Agents .NET, 30+ connecteurs |
| 32 | [Doriandarko/make-it-heavy](https://github.com/Doriandarko/make-it-heavy) | 1117 | Python | Plusieurs agents en parallèle puis synthèse |
| 33 | [massgen/MassGen](https://github.com/massgen/MassGen) | 1144 | Python | Mise à l'échelle multi-agents en terminal |
| 34 | [InternLM/MindSearch](https://github.com/InternLM/MindSearch) | 6944 | JS | Moteur de recherche multi-agents (2025) |

## 2. Orchestrer Claude Code et les agents de code

| # | Dépôt | ⭐ | Langage | Contenu |
|---|---|---|---|---|
| 35 | [anthropics/claude-code](https://github.com/anthropics/claude-code) | 153575 | TypeScript | Claude Code (sous-agents, hooks, skills intégrés) |
| 36 | [Yeachan-Heo/oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) ★ | 40320 | TypeScript | Orchestration multi-agents en équipe pour Claude Code |
| 37 | [ruvnet/ruflo](https://github.com/ruvnet/ruflo) | 79721 | TypeScript | Essaims d'agents coordonnés |
| 38 | [wshobson/agents](https://github.com/wshobson/agents) | 41873 | Python | Marketplace de plugins/agents multi-outils |
| 39 | [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) ★ | 26108 | Shell | 100+ sous-agents spécialisés prêts à l'emploi |
| 40 | [gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done) | 64205 | JS | Développement piloté par spécifications |
| 41 | [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) | 27707 | Python | Planification persistante dans des fichiers |
| 42 | [OrchestratorInc/agent-orchestrator](https://github.com/OrchestratorInc/agent-orchestrator) | 13764 | Go | Orchestrateur pour Claude Code, Codex et 30+ agents |
| 43 | [omnigent-ai/omnigent](https://github.com/omnigent-ai/omnigent) | 11081 | Python | Méta-harnais pour orchestrer Claude Code |
| 44 | [alvinunreal/oh-my-opencode-slim](https://github.com/alvinunreal/oh-my-opencode-slim) | 9825 | TypeScript | Suite multi-agents pour OpenCode |
| 45 | [stellarlinkco/myclaude](https://github.com/stellarlinkco/myclaude) | 2749 | Go | Workflow Claude Code + Codex + Gemini |
| 46 | [moazbuilds/CodeMachine-CLI](https://github.com/moazbuilds/CodeMachine-CLI) | 2512 | TypeScript | Agents de code en workflows reproductibles |
| 47 | [catlog22/Claude-Code-Workflow](https://github.com/catlog22/Claude-Code-Workflow) | 2120 | TypeScript | Équipe multi-agents pilotée par JSON |
| 48 | [awslabs/cli-agent-orchestrator](https://github.com/awslabs/cli-agent-orchestrator) | 1478 | Python | Orchestration de CLI d'agents (AWS) |
| 49 | [Danau5tin/multi-agent-coding-system](https://github.com/Danau5tin/multi-agent-coding-system) | 1469 | Python | Orchestrateur + explorateur + codeur |
| 50 | [gastownhall/gascity](https://github.com/gastownhall/gascity) | 1447 | Go | SDK de workflows de code multi-agents |
| 51 | [yohey-w/multi-agent-shogun](https://github.com/yohey-w/multi-agent-shogun) | 1423 | Shell | Tâches parallèles pour Claude Code |
| 52 | [tintinweb/pi-subagents](https://github.com/tintinweb/pi-subagents) | 1373 | TypeScript | Sous-agents et workflows parallèles |
| 53 | [jayminwest/overstory](https://github.com/jayminwest/overstory) | 1313 | TypeScript | Orchestration avec adaptateurs |
| 54 | [ChesterRa/cccc](https://github.com/ChesterRa/cccc) | 1287 | Rust | Coordination d'agents façon messagerie |
| 55 | [the-open-engine/zeroshot](https://github.com/the-open-engine/zeroshot) | 2048 | Rust | Méta-harnais : workflows et relecteurs sur mesure |
| 56 | [Intrect-io/OpenSwarm](https://github.com/Intrect-io/OpenSwarm) | 869 | TypeScript | Équipe de dev autonome sur Claude Code |
| 57 | [open-mercato/cezar](https://github.com/open-mercato/cezar) | 852 | TypeScript | Orchestrateur de Claude Code, Codex, OpenCode |
| 58 | [Nanako0129/pilotfish](https://github.com/Nanako0129/pilotfish) | 711 | Python | Le gros modèle planifie, les petits exécutent |
| 59 | [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc) | 34637 | JS | Déléguer à Codex depuis Claude Code |
| 60 | [musistudio/claude-code-router](https://github.com/musistudio/claude-code-router) | 37880 | TypeScript | Routage de Claude Code entre modèles |
| 61 | [BloopAI/vibe-kanban](https://github.com/BloopAI/vibe-kanban) | 28477 | Rust | Kanban pour piloter plusieurs agents |
| 62 | [a5c-ai/babysitter](https://github.com/a5c-ai/babysitter) | 1873 | JS | Discipline d'équipes d'agents sur longues tâches |

## 3. Tableaux de bord et plans de contrôle d'agents

| # | Dépôt | ⭐ | Langage | Contenu |
|---|---|---|---|---|
| 63 | [paperclipai/paperclip](https://github.com/paperclipai/paperclip) | 107918 | TypeScript | Gestion d'agents au travail |
| 64 | [stablyai/orca](https://github.com/stablyai/orca) | 107861 | TypeScript | Piloter une flotte d'agents |
| 65 | [herdrdev/herdr](https://github.com/herdrdev/herdr) | 46165 | Rust | Runtime pour agents de code |
| 66 | [slopus/happy](https://github.com/slopus/happy) | 24351 | Swift | Orchestrer Claude, Codex, Grok depuis une app |
| 67 | [ParadevAI/Paradev](https://github.com/ParadevAI/Paradev) | 15634 | TypeScript | IDE pour 100+ agents en parallèle |
| 68 | [mvschwarz/openrig](https://github.com/mvschwarz/openrig) | 8249 | TypeScript | Réseaux d'agents persistants |
| 69 | [builderz-labs/mission-control](https://github.com/builderz-labs/mission-control) | 6401 | TypeScript | Dispatcher des tâches, suivre les coûts |
| 70 | [abhi1693/openclaw-mission-control](https://github.com/abhi1693/openclaw-mission-control) | 4101 | TypeScript | Tableau de bord d'orchestration |
| 71 | [AgentsMesh/AgentsMesh](https://github.com/AgentsMesh/AgentsMesh) | 2362 | Go | Centaine d'agents sur tes machines |
| 72 | [777genius/agent-teams-ai](https://github.com/777genius/agent-teams-ai) | 2357 | TypeScript | Agents en équipe qui se répartissent les tâches |
| 73 | [preset-io/agor](https://github.com/preset-io/agor) | 1471 | TypeScript | Espace multijoueur humains + agents |
| 74 | [SolaceProducts/solace-agent-mesh](https://github.com/SolaceProducts/solace-agent-mesh) | 4916 | Shell | Maillage d'agents événementiel |

## 4. Plateformes visuelles et automatisation

| # | Dépôt | ⭐ | Langage | Contenu |
|---|---|---|---|---|
| 75 | [n8n-io/n8n](https://github.com/n8n-io/n8n) ★ | 208782 | TypeScript | Automatisation visuelle + IA, 400+ intégrations, auto-hébergeable |
| 76 | [langgenius/dify](https://github.com/langgenius/dify) | 159713 | Python | Workflows agentiques et RAG en visuel |
| 77 | [FlowiseAI/Flowise](https://github.com/FlowiseAI/Flowise) | 55531 | TypeScript | Agents en glisser-déposer (**archivé**) |
| 78 | [labring/FastGPT](https://github.com/labring/FastGPT) | 29923 | TypeScript | Plateforme de connaissances + workflows |
| 79 | [windmill-labs/windmill](https://github.com/windmill-labs/windmill) ★ | 18294 | Rust | Scripts, workflows et agents auto-hébergés |
| 80 | [triggerdotdev/trigger.dev](https://github.com/triggerdotdev/trigger.dev) | 16631 | TypeScript | Tâches de fond et agents durables |
| 81 | [iflytek/astron-agent](https://github.com/iflytek/astron-agent) | 8933 | Java | Plateforme de workflows agentiques |
| 82 | [Agenta-AI/agenta](https://github.com/Agenta-AI/agenta) | 4864 | TypeScript | Construire et évaluer agents et automatisations |

## 5. Orchestration de pipelines de données et ML

| # | Dépôt | ⭐ | Langage | Contenu |
|---|---|---|---|---|
| 83 | [apache/airflow](https://github.com/apache/airflow) | 47290 | Python | La référence des pipelines planifiés (DAG) |
| 84 | [kestra-io/kestra](https://github.com/kestra-io/kestra) | 30033 | Java | Workflows déclaratifs en YAML |
| 85 | [PrefectHQ/prefect](https://github.com/PrefectHQ/prefect) ★ | 24085 | Python | Pipelines Python simples et résilients (idéal collecte quotidienne) |
| 86 | [spotify/luigi](https://github.com/spotify/luigi) | 18783 | Python | Pipelines batch avec dépendances |
| 87 | [argoproj/argo-workflows](https://github.com/argoproj/argo-workflows) | 17058 | Go | Workflows sur Kubernetes |
| 88 | [dagster-io/dagster](https://github.com/dagster-io/dagster) ★ | 16337 | Python | Orchestration centrée sur les données (assets) |
| 89 | [apache/dolphinscheduler](https://github.com/apache/dolphinscheduler) | 14538 | Java | Ordonnanceur de données |
| 90 | [kedro-org/kedro](https://github.com/kedro-org/kedro) | 11036 | Python | Structure de projets data science reproductibles |
| 91 | [Netflix/metaflow](https://github.com/Netflix/metaflow) | 10318 | Python | Systèmes ML/IA de bout en bout |
| 92 | [mage-ai/mage-ai](https://github.com/mage-ai/mage-ai) | 8837 | Python | Pipelines ETL avec interface |
| 93 | [flyteorg/flyte](https://github.com/flyteorg/flyte) | 7771 | Go | Pipelines ML et agents typés |
| 94 | [zenml-io/zenml](https://github.com/zenml-io/zenml) | 5628 | Python | MLOps, des pipelines aux agents |
| 95 | [dagucloud/dagu](https://github.com/dagucloud/dagu) ★ | 4463 | Go | Orchestrateur ultra-léger (cron + DAG en YAML) |
| 96 | [apache/hop](https://github.com/apache/hop) | 1514 | Java | Plateforme d'orchestration ETL |

## 6. Workflows durables (moteurs d'exécution)

| # | Dépôt | ⭐ | Langage | Contenu |
|---|---|---|---|---|
| 97 | [temporalio/temporal](https://github.com/temporalio/temporal) | 24019 | Go | Exécution durable, reprise après panne |
| 98 | [hatchet-dev/hatchet](https://github.com/hatchet-dev/hatchet) | 8190 | Go | Tâches de fond, agents, workflows durables |
| 99 | [inngest/inngest](https://github.com/inngest/inngest) | 5995 | Go | Fonctions par étapes avec état |
| 100 | [dbos-inc/dbos-transact-py](https://github.com/dbos-inc/dbos-transact-py) | 1652 | Python | Workflows durables adossés à Postgres |
| 101 | [Netflix/maestro](https://github.com/Netflix/maestro) | 3847 | Java | Orchestrateur de Netflix |
| 102 | [vercel/workflow](https://github.com/vercel/workflow) | 2475 | TypeScript | SDK de workflows durables |

## 7. Listes de ressources

| # | Dépôt | ⭐ | Contenu |
|---|---|---|---|
| 103 | [andyrewlee/awesome-agent-orchestrators](https://github.com/andyrewlee/awesome-agent-orchestrators) ★ | 2294 | Liste d'orchestrateurs d'agents |
| 104 | [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | 56658 | Ressources Claude Code |
| 105 | [ai-boost/awesome-harness-engineering](https://github.com/ai-boost/awesome-harness-engineering) | 4978 | Outils et patterns de harnais d'agents |
| 106 | [jim-schwoebel/awesome_ai_agents](https://github.com/jim-schwoebel/awesome_ai_agents) | 2020 | 1500+ ressources sur les agents |
| 107 | [NirDiamant/GenAI_Agents](https://github.com/NirDiamant/GenAI_Agents) | 24706 | 50+ tutoriels d'agents |
| 108 | [NirDiamant/agents-towards-production](https://github.com/NirDiamant/agents-towards-production) | 21779 | Tutoriels d'agents en production |
