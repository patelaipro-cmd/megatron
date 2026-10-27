# 89 dépôts GitHub pour se connecter à plusieurs LLM

Relevé du 27/10/2026 via la recherche GitHub (tri par étoiles). ⭐ = étoiles, tous actifs en 2026 sauf mention contraire.
★ = recommandé pour Megatron (ex. faire analyser un même match par Claude, GPT, Gemini et un modèle local, puis comparer).
⚠ = détourne des abonnements grand public (Claude, ChatGPT…) en API. Cela peut enfreindre leurs conditions d'utilisation : à éviter pour un projet sérieux.

## 1. SDK unifiés (une seule interface de code, tous les modèles)

| # | Dépôt | ⭐ | Langage | Contenu |
|---|---|---|---|---|
| 1 | [BerriAI/litellm](https://github.com/BerriAI/litellm) ★ | 62164 | Python | Appeler 100+ LLM avec le même code, plus passerelle avec coûts, quotas et repli automatique |
| 2 | [vercel/ai](https://github.com/vercel/ai) | 27542 | TypeScript | AI SDK : tous les fournisseurs en TS/JS |
| 3 | [andrewyng/aisuite](https://github.com/andrewyng/aisuite) ★ | 16361 | Python | Interface unifiée très simple (Andrew Ng) |
| 4 | [567-labs/instructor](https://github.com/567-labs/instructor) ★ | 14067 | Python | Sorties structurées (JSON validé) avec n'importe quel modèle, idéal pour des pronostics chiffrés |
| 5 | [simonw/llm](https://github.com/simonw/llm) | 12676 | Python | Tous les LLM en ligne de commande, avec plugins |
| 6 | [mozilla-ai/any-llm](https://github.com/mozilla-ai/any-llm) | 2231 | Python | Interface unique (Mozilla) |
| 7 | [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) | 20905 | Python | Agents typés multi-fournisseurs |
| 8 | [mastra-ai/mastra](https://github.com/mastra-ai/mastra) | 29122 | TypeScript | Framework d'agents multi-modèles |
| 9 | [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | 30334 | Python | SDK d'agents compatible avec d'autres fournisseurs |
| 10 | [adaline/gateway](https://github.com/adaline/gateway) | 607 | TypeScript | « Super SDK » local unifié |
| 11 | [aimeos/prisma](https://github.com/aimeos/prisma) | 239 | PHP | Intégration multi-LLM en PHP |

## 2. Passerelles API (un seul point d'accès, auto-hébergé)

| # | Dépôt | ⭐ | Langage | Contenu |
|---|---|---|---|---|
| 12 | [QuantumNous/new-api](https://github.com/QuantumNous/new-api) | 50808 | Go | Hub unifié d'agrégation et de distribution de modèles |
| 13 | [songquanpeng/one-api](https://github.com/songquanpeng/one-api) | 37261 | Go | Gestion et distribution d'API (OpenAI, Claude, Gemini, DeepSeek…) |
| 14 | [Portkey-AI/gateway](https://github.com/Portkey-AI/gateway) ★ | 13280 | TypeScript | Passerelle rapide vers 1 600+ LLM avec garde-fous |
| 15 | [tensorzero/tensorzero](https://github.com/tensorzero/tensorzero) ★ | 11708 | Rust | Passerelle + observabilité + évaluation + expériences A/B entre modèles |
| 16 | [coaidev/coai](https://github.com/coaidev/coai) | 9334 | Go | Solution multi-locataires avec facturation |
| 17 | [maximhq/bifrost](https://github.com/maximhq/bifrost) | 9146 | Go | Passerelle haute performance, cache sémantique |
| 18 | [mnfst/llm-gateway](https://github.com/mnfst/llm-gateway) | 7604 | TypeScript | Passerelle LLM open source |
| 19 | [tbphp/gpt-load](https://github.com/tbphp/gpt-load) | 7172 | Go | Multi-canaux et rotation de clés API |
| 20 | [katanemo/plano](https://github.com/katanemo/plano) | 7099 | Rust | Proxy IA avec routage intelligent |
| 21 | [looplj/axonhub](https://github.com/looplj/axonhub) | 5403 | Go | N'importe quel SDK vers 100+ LLM, avec bascule automatique |
| 22 | [TykTechnologies/tyk](https://github.com/TykTechnologies/tyk) | 10870 | Go | Passerelle API et IA (REST, gRPC, MCP) |
| 23 | [theagentrouter/agent-router](https://github.com/theagentrouter/agent-router) | 2304 | Go | Accès unifié bâti sur Envoy |
| 24 | [APIParkLab/APIPark](https://github.com/APIParkLab/APIPark) | 1820 | Go | Passerelle IA et API cloud native |
| 25 | [theopenco/llmgateway](https://github.com/theopenco/llmgateway) | 1713 | TypeScript | Routage et analyse des requêtes multi-fournisseurs |
| 26 | [aklivity/zilla](https://github.com/aklivity/zilla) | 1688 | Java | Passerelle multi-protocoles en streaming |
| 27 | [ENTERPILOT/GoModel](https://github.com/ENTERPILOT/GoModel) | 1277 | Go | Passerelle compatible OpenAI |
| 28 | [bricks-cloud/BricksLLM](https://github.com/bricks-cloud/BricksLLM) | 1230 | Go | Limites de coût et de débit par clé (2025) |
| 29 | [mozilla-ai/otari](https://github.com/mozilla-ai/otari) | 743 | Python | Passerelle compatible OpenAI (Mozilla) |
| 30 | [smg-project/smg](https://github.com/smg-project/smg) | 687 | Rust | Compatible API OpenAI et Anthropic |
| 31 | [Helicone/ai-gateway](https://github.com/Helicone/ai-gateway) | 641 | Rust | Passerelle légère (2025) |
| 32 | [Mirrowel/LLM-API-Key-Proxy](https://github.com/Mirrowel/LLM-API-Key-Proxy) | 557 | Python | Une API pour tous les LLM, compatible OpenAI/Anthropic |
| 33 | [cheaper-inference/OmniRoute](https://github.com/cheaper-inference/OmniRoute) | 81780 | TypeScript | Point d'accès unique vers 375 fournisseurs |
| 34 | [casdoor/casdoor](https://github.com/casdoor/casdoor) | 14681 | Go | Identité et accès, avec passerelle LLM/MCP |

## 3. Routeurs (choisir automatiquement le bon modèle)

| # | Dépôt | ⭐ | Langage | Contenu |
|---|---|---|---|---|
| 35 | [lm-sys/RouteLLM](https://github.com/lm-sys/RouteLLM) | 5641 | Python | Questions simples vers un petit modèle, dures vers un gros (2024) |
| 36 | [NVIDIA-NeMo/Switchyard](https://github.com/NVIDIA-NeMo/Switchyard) | 3456 | Python | Routage du trafic entre modèles et fournisseurs |
| 37 | [CommonstackAI/UncommonRoute](https://github.com/CommonstackAI/UncommonRoute) | 699 | Python | Routeur automatique orienté coût |
| 38 | [NadirRouter/NadirClaw](https://github.com/NadirRouter/NadirClaw) | 660 | Python | Routeur et optimiseur de coûts |

## 4. Plusieurs LLM qui délibèrent (conseil, consensus)

| # | Dépôt | ⭐ | Langage | Contenu |
|---|---|---|---|---|
| 39 | [karpathy/llm-council](https://github.com/karpathy/llm-council) ★ | 25987 | Python | Plusieurs LLM répondent, se notent entre eux, puis un « président » synthétise. Parfait pour un pronostic par consensus |
| 40 | [togethercomputer/MoA](https://github.com/togethercomputer/MoA) | 2992 | Python | Mixture-of-Agents : combiner plusieurs modèles open source (2025) |
| 41 | [Leeroo-AI/mergoo](https://github.com/Leeroo-AI/mergoo) | 515 | Python | Fusionner plusieurs LLM experts (2024) |
| 42 | [99xAgency/GodModeSkill](https://github.com/99xAgency/GodModeSkill) | 239 | — | Revue croisée multi-LLM dans Claude Code |
| 43 | [salutaris91/llm-council-mcp-server](https://github.com/salutaris91/llm-council-mcp-server) | 9 | Python | LLM Council de Karpathy en serveur MCP pour Claude Code |
| 44 | [frescodicredito/rasputin](https://github.com/frescodicredito/rasputin) | 0 | Python | Conseil Gemini + GPT + Mistral pour Claude Code via MCP |
| 45 | [yonk-labs/abe](https://github.com/yonk-labs/abe) | 1 | Rust | Débat multi-modèles et second avis |
| 46 | [bencmorrison/modelguild](https://github.com/bencmorrison/modelguild) | 2 | TypeScript | Claude Code consulte d'autres LLM via opencode |
| 47 | [KingEdwardI/second-opinion](https://github.com/KingEdwardI/second-opinion) | 0 | TypeScript | Second avis via OpenRouter avec classement des modèles |
| 48 | [lm-sys/FastChat](https://github.com/lm-sys/FastChat) | 39548 | Python | Plateforme de Chatbot Arena : comparer des modèles côte à côte |
| 49 | [dezoito/ollama-grid-search](https://github.com/dezoito/ollama-grid-search) | 959 | Rust | Comparer des modèles et des prompts côte à côte |

## 5. Claude Code avec d'autres modèles

| # | Dépôt | ⭐ | Langage | Contenu |
|---|---|---|---|---|
| 50 | [musistudio/claude-code-router](https://github.com/musistudio/claude-code-router) ★ | 37880 | TypeScript | Faire tourner Claude Code sur d'autres modèles selon la tâche |
| 51 | [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc) | 34638 | JS | Déléguer à Codex depuis Claude Code (relecture, tâches) |
| 52 | [farion1231/cc-switch](https://github.com/farion1231/cc-switch) | 149353 | Rust | Basculer de fournisseur pour Claude Code, Codex, OpenCode… |
| 53 | [SeemSeam/claude_codex_bridge](https://github.com/SeemSeam/claude_codex_bridge) | 3595 | Python | Espace CLI mêlant Codex, Claude, Gemini, Kimi, Qwen… |
| 54 | [stellarlinkco/myclaude](https://github.com/stellarlinkco/myclaude) | 2749 | Go | Workflow Claude Code + Codex + Gemini + OpenCode |
| 55 | [Nanako0129/pilotfish](https://github.com/Nanako0129/pilotfish) | 711 | Python | Le gros modèle planifie, les modèles moins chers exécutent |
| 56 | [zhnt/loushang](https://github.com/zhnt/loushang) | 1892 | Python | Harnais de code avec orchestration multi-modèles |
| 57 | [slopus/happy](https://github.com/slopus/happy) | 24351 | Swift | Piloter Claude, Codex et Grok depuis une app |
| 58 | [kittors/CliRelay](https://github.com/kittors/CliRelay) | 1043 | Go | Passerelle auto-hébergée pour les CLI de code |
| 59 | [lidge-jun/opencodex](https://github.com/lidge-jun/opencodex) | 17969 | TypeScript | Proxy pour utiliser n'importe quel LLM dans Codex/Claude Code |
| 60 | [router-for-me/CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) ⚠ | 56623 | Go | Transforme des abonnements CLI en API |
| 61 | [Alishahryar1/free-claude-code](https://github.com/Alishahryar1/free-claude-code) ⚠ | 64218 | Python | Claude Code et autres outils sur des modèles gratuits |
| 62 | [decolua/9router](https://github.com/decolua/9router) ⚠ | 31521 | JS | Connecte les outils de code à des modèles gratuits |
| 63 | [justlovemaki/AIClient2API](https://github.com/justlovemaki/AIClient2API) ⚠ | 8928 | JS | Proxy multi-protocoles à partir de clients IA |

## 6. Outils de code multi-fournisseurs

| # | Dépôt | ⭐ | Langage | Contenu |
|---|---|---|---|---|
| 64 | [cline/cline](https://github.com/cline/cline) | 70919 | TypeScript | Agent de code compatible avec tous les fournisseurs |
| 65 | [Aider-AI/aider](https://github.com/Aider-AI/aider) | 49774 | Python | Agent de code en terminal, tous modèles, mode « architecte + éditeur » à deux modèles |
| 66 | [continuedev/continue](https://github.com/continuedev/continue) | 36347 | TypeScript | Assistant de code open source multi-modèles |
| 67 | [charmbracelet/crush](https://github.com/charmbracelet/crush) | 28832 | Go | Agent de code en terminal multi-modèles |

## 7. Interfaces de chat multi-modèles (auto-hébergées ou bureau)

| # | Dépôt | ⭐ | Langage | Contenu |
|---|---|---|---|---|
| 68 | [open-webui/open-webui](https://github.com/open-webui/open-webui) ★ | 156953 | Python | Interface web auto-hébergée pour Ollama, OpenAI, Claude… avec comparaison de modèles |
| 69 | [ChatGPTNextWeb/NextChat](https://github.com/ChatGPTNextWeb/NextChat) | 88903 | TypeScript | Client multi-modèles multiplateforme |
| 70 | [lobehub/lobehub](https://github.com/lobehub/lobehub) | 83529 | TypeScript | Espace d'agents multi-fournisseurs |
| 71 | [Mintplex-Labs/anything-llm](https://github.com/Mintplex-Labs/anything-llm) | 67638 | JS | Tout-en-un local : chat, RAG, agents, tous LLM |
| 72 | [CherryHQ/cherry-studio](https://github.com/CherryHQ/cherry-studio) | 53031 | TypeScript | Studio de bureau, accès unifié aux modèles de pointe |
| 73 | [chatboxai/chatbox](https://github.com/chatboxai/chatbox) | 42164 | TypeScript | Client de bureau multi-modèles |
| 74 | [janhq/jan](https://github.com/janhq/jan) | 45118 | Rust | Alternative à ChatGPT 100 % hors ligne, plus API distantes |
| 75 | [iOfficeAI/AionUi](https://github.com/iOfficeAI/AionUi) | 33824 | TypeScript | Interface pour Claude Code, Codex, OpenCode… |
| 76 | [EKKOLearnAI/ekko-studio](https://github.com/EKKOLearnAI/ekko-studio) | 11576 | TypeScript | Espace local multi-agents |
| 77 | [sdcb/chats](https://github.com/sdcb/chats) | 616 | C# | Interface + passerelle LLM |
| 78 | [oriveo/oriveo](https://github.com/oriveo/oriveo) | 550 | — | Client multi-modèles mobile, avec tes propres clés |
| 79 | [ChatLunaLab/chatluna](https://github.com/ChatLunaLab/chatluna) | 446 | TypeScript | Plugin de chatbot multi-modèles |

## 8. Plateformes visuelles et automatisation

| # | Dépôt | ⭐ | Langage | Contenu |
|---|---|---|---|---|
| 80 | [n8n-io/n8n](https://github.com/n8n-io/n8n) | 208782 | TypeScript | Automatisation avec nœuds pour tous les LLM |
| 81 | [langgenius/dify](https://github.com/langgenius/dify) | 159713 | Python | Workflows IA multi-modèles en visuel |

## 9. Modèles locaux (à ajouter aux modèles cloud)

| # | Dépôt | ⭐ | Langage | Contenu |
|---|---|---|---|---|
| 82 | [ollama/ollama](https://github.com/ollama/ollama) ★ | 185002 | Go | Lancer des modèles open source en local (Qwen, DeepSeek, Gemma…) |
| 83 | [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) | 132545 | C++ | Moteur d'inférence local de référence |
| 84 | [vllm-project/vllm](https://github.com/vllm-project/vllm) | 95697 | Python | Serveur haute performance compatible OpenAI |
| 85 | [nomic-ai/gpt4all](https://github.com/nomic-ai/gpt4all) | 77356 | C++ | LLM locaux sur tout appareil (2025) |
| 86 | [mudler/LocalAI](https://github.com/mudler/LocalAI) | 50005 | Go | Remplaçant local de l'API OpenAI |
| 87 | [exo-explore/exo](https://github.com/exo-explore/exo) | 48065 | Python | Répartir un gros modèle sur plusieurs machines |
| 88 | [jonigl/mcp-client-for-ollama](https://github.com/jonigl/mcp-client-for-ollama) | 833 | Python | Client MCP pour modèles Ollama |
| 89 | [davidecolombo/local-mcp](https://github.com/davidecolombo/local-mcp) | 4 | Python | Délègue les lectures de fichiers à un modèle local |
