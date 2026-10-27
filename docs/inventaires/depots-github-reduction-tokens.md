# 103 dépôts GitHub pour réduire la consommation de tokens

Relevé du 27/10/2026 via la recherche GitHub (tri par étoiles). ⭐ = étoiles, tous actifs en 2026 sauf mention contraire.
★ = mes recommandations pour Megatron (Claude Code + gros volumes de stats football à faire lire au modèle).

> Les promesses du type « −90 % de tokens » viennent des auteurs et n'ont pas été vérifiées. Les étoiles de certains dépôts récents paraissent gonflées.

## 1. Compresser les sorties de commandes et d'outils (agents de code)

| # | Dépôt | ⭐ | Contenu |
|---|---|---|---|
| 1 | [rtk-ai/rtk](https://github.com/rtk-ai/rtk) ★ | 84762 | Proxy CLI qui compacte la sortie des commandes courantes (git, tests, ls…) : −60 à 90 % annoncés |
| 2 | [headroomlabs-ai/headroom](https://github.com/headroomlabs-ai/headroom) ★ | 78014 | Compresse logs, fichiers, sorties d'outils et morceaux RAG avant qu'ils n'atteignent le LLM |
| 3 | [mksglu/context-mode](https://github.com/mksglu/context-mode) ★ | 32534 | Isole les sorties d'outils hors du contexte de Claude Code |
| 4 | [open-compress/claw-compactor](https://github.com/open-compress/claw-compactor) | 2004 | Pipeline de compression réversible en 14 étapes |
| 5 | [Paritok-official/paritok-4b-v1](https://github.com/Paritok-official/paritok-4b-v1) | 1441 | Passerelle de compression non destructive |
| 6 | [ojuschugh1/sqz](https://github.com/ojuschugh1/sqz) | 667 | Compresse la sortie des outils avant le modèle |
| 7 | [zdk/lowfat](https://github.com/zdk/lowfat) | 582 | Allège la sortie des commandes |
| 8 | [edouard-claude/snip](https://github.com/edouard-claude/snip) | 472 | Proxy CLI à filtres YAML |
| 9 | [juyterman1000/entroly](https://github.com/juyterman1000/entroly) | 480 | Réduction de contexte vérifiable et réversible |
| 10 | [fajarhide/omni](https://github.com/fajarhide/omni) | 371 | Évite de repayer une sortie déjà vue |
| 11 | [fkiene/llmtrim](https://github.com/fkiene/llmtrim) | 257 | Proxy local qui compresse les requêtes API |
| 12 | [MasuRii/pi-rtk-optimizer](https://github.com/MasuRii/pi-rtk-optimizer) | 283 | Extension RTK pour Pi |
| 13 | [gglucass/headroom-desktop](https://github.com/gglucass/headroom-desktop) | 625 | Headroom en app de barre de menus |
| 14 | [hansipie/ecotokens](https://github.com/hansipie/ecotokens) | 21 | Compression de sorties shell (Claude Code, Gemini CLI) |
| 15 | [AgusRdz/chop](https://github.com/AgusRdz/chop) | 46 | Compresseur de sorties CLI pour Claude Code |

## 2. Faire parler le modèle plus court

| # | Dépôt | ⭐ | Contenu |
|---|---|---|---|
| 16 | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) ★ | 115485 | Skill + proxy pour des réponses ultra-concises (« why use many token when few token do trick ») |
| 17 | [JayPokale/Chisle](https://github.com/JayPokale/Chisle) | 721 | Prose sobre, code minimal, contexte réduit |
| 18 | [Green-PT/honey-for-devs](https://github.com/Green-PT/honey-for-devs) | 343 | Skill multi-outils qui réduit les tokens générés |
| 19 | [gatalifeltd/economizer-skills](https://github.com/gatalifeltd/economizer-skills) | 3 | Règles d'économie de tokens pour agents |

## 3. Optimiser Claude Code (démarrage, mémoire, quotas)

| # | Dépôt | ⭐ | Contenu |
|---|---|---|---|
| 20 | [alexgreensh/token-optimizer](https://github.com/alexgreensh/token-optimizer) ★ | 2748 | Trouve les « tokens fantômes » (CLAUDE.md, MCP, skills chargés pour rien) |
| 21 | [nadimtuhin/claude-token-optimizer](https://github.com/nadimtuhin/claude-token-optimizer) | 633 | Réduit ce que Claude Code charge au démarrage |
| 22 | [thedotmack/claude-mem](https://github.com/thedotmack/claude-mem) | 103649 | Mémoire entre sessions : moins de contexte à répéter |
| 23 | [cytostack/openwolf](https://github.com/cytostack/openwolf) | 2400 | Mémoire de projet portable + économies de tokens |
| 24 | [lucasrosati/claude-code-memory-setup](https://github.com/lucasrosati/claude-code-memory-setup) | 1045 | Obsidian + graphe pour réduire les tokens par session |
| 25 | [GMaN1911/claude-cognitive](https://github.com/GMaN1911/claude-cognitive) | 451 | Mémoire de travail pour Claude Code |
| 26 | [IyadhKhalfallah/clauditor](https://github.com/IyadhKhalfallah/clauditor) | 429 | Empêche Claude Code de griller le quota trop vite |
| 27 | [Maciek-roboblog/Claude-Code-Usage-Monitor](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor) ★ | 8770 | Suivi de consommation en temps réel avec prévisions |
| 28 | [ooples/token-optimizer-mcp](https://github.com/ooples/token-optimizer-mcp) | 563 | Mesure les économies de tokens par agent |
| 29 | [HoangP8/tokless](https://github.com/HoangP8/tokless) | 347 | Configuration d'agent économe en 30 secondes |
| 30 | [oxygen-fragment/claude-modular](https://github.com/oxygen-fragment/claude-modular) | 285 | Framework modulaire avec optimisation de tokens |
| 31 | [ZipengWu365/TOMC](https://github.com/ZipengWu365/TOMC) | 265 | Compression de contexte et mémoire de tâches |
| 32 | [DFKHelper/token-goat](https://github.com/DFKHelper/token-goat) | 144 | Réducteur de consommation multi-agents |
| 33 | [KINGSTAR-OMEGA/claude-token-optimizer](https://github.com/KINGSTAR-OMEGA/claude-token-optimizer) | 121 | Skills économes pour Claude Code |
| 34 | [mikhail-tokarev/greenbelt](https://github.com/mikhail-tokarev/greenbelt) | 22 | Hooks de suivi de consommation |
| 35 | [Growth4U-systems/claude-token-hygiene](https://github.com/Growth4U-systems/claude-token-hygiene) | 10 | Audit du coût caché de chaque conversation |
| 36 | [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) | 27707 | Planification dans des fichiers plutôt que dans le contexte |

## 4. Lire le code sans tout charger (recherche ciblée, index)

| # | Dépôt | ⭐ | Contenu |
|---|---|---|---|
| 37 | [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) | 136797 | Transforme un projet en graphe interrogeable |
| 38 | [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph) | 75593 | Graphe de code pré-indexé pour Claude Code |
| 39 | [oraios/serena](https://github.com/oraios/serena) ★ | 30765 | MCP de recherche sémantique : lit une fonction, pas tout le fichier |
| 40 | [zilliztech/claude-context](https://github.com/zilliztech/claude-context) | 12650 | Recherche de code MCP pour Claude Code |
| 41 | [Aider-AI/aider](https://github.com/Aider-AI/aider) | 49774 | Agent de code avec « repo map » compacte |
| 42 | [jgravelle/jcodemunch-mcp](https://github.com/jgravelle/jcodemunch-mcp) | 2810 | Récupère un symbole précis, pas un fichier entier |
| 43 | [redhat-et/ripwire](https://github.com/redhat-et/ripwire) | 2489 | « ripgrep » du contexte IA (CLI + MCP) |
| 44 | [manojmallick/sigmap](https://github.com/manojmallick/sigmap) | 645 | Carte de signatures du code, 38 langages |
| 45 | [skibidiskib/ai-codex](https://github.com/skibidiskib/ai-codex) | 391 | Index compact du code pour assistants |
| 46 | [AxiomCodeAI/axiomcodegraph](https://github.com/AxiomCodeAI/axiomcodegraph) | 327 | Code en graphe de connaissances |
| 47 | [johunsang/semble_rs](https://github.com/johunsang/semble_rs) | 216 | Recherche de code hybride BM25 + sémantique |
| 48 | [jgravelle/jdocmunch-mcp](https://github.com/jgravelle/jdocmunch-mcp) | 207 | Exploration de documentation économe |
| 49 | [NickCirv/engram](https://github.com/NickCirv/engram) | 143 | Colonne vertébrale de contexte multi-IDE |
| 50 | [efrenbl/code-navigator](https://github.com/efrenbl/code-navigator) | 5 | Navigation de code économe pour Claude Code |

## 5. Moins d'outils MCP chargés

| # | Dépôt | ⭐ | Contenu |
|---|---|---|---|
| 51 | [ratel-ai/ratel](https://github.com/ratel-ai/ratel) | 537 | Évite la surcharge d'outils, −80 % de tokens annoncés |
| 52 | [activeing123/mcptoon](https://github.com/activeing123/mcptoon) | 400 | CLI unique pour serveurs MCP et skills |
| 53 | [elusznik/mcp-server-code-execution-mode](https://github.com/elusznik/mcp-server-code-execution-mode) | 340 | Exécute du code au lieu d'enchaîner les appels d'outils |
| 54 | [Lap-Platform/LAP](https://github.com/Lap-Platform/LAP) | 345 | Specs d'API compactes pour agents |
| 55 | [bug-ops/mcp-execution](https://github.com/bug-ops/mcp-execution) | 46 | Génère des outils TypeScript à partir de MCP |
| 56 | [KGT24k/mcp-tool-search](https://github.com/KGT24k/mcp-tool-search) | 7 | Chargement paresseux des outils MCP |
| 57 | [vdutts7/skills-not-mcp](https://github.com/vdutts7/skills-not-mcp) | 13 | Skills + shell au lieu de MCP |

## 6. Compression de prompts (recherche et bibliothèques)

| # | Dépôt | ⭐ | Contenu |
|---|---|---|---|
| 58 | [microsoft/LLMLingua](https://github.com/microsoft/LLMLingua) ★ | 6775 | Compression de prompts de référence (Microsoft, jusqu'à 20x) |
| 59 | [jia-gao/leanctx](https://github.com/jia-gao/leanctx) | 321 | Compression de prompts prête pour la production |
| 60 | [3DAgentWorld/Toolkit-for-Prompt-Compression](https://github.com/3DAgentWorld/Toolkit-for-Prompt-Compression) | 291 | Boîte à outils de méthodes de compression (2025) |
| 61 | [yvgude/lean-ctx](https://github.com/yvgude/lean-ctx) | 3903 | Passerelle qui ne garde que le contexte utile |
| 62 | [Context-Engine-AI/Context-Engine](https://github.com/Context-Engine-AI/Context-Engine) | 401 | Suite de compression de contexte (MCP) |
| 63 | [iKislay/copium](https://github.com/iKislay/copium) | 20 | Couche d'optimisation de contexte |

## 7. Formats de données compacts (utile pour des stats football)

| # | Dépôt | ⭐ | Contenu |
|---|---|---|---|
| 64 | [toon-format/toon](https://github.com/toon-format/toon) ★ | 25567 | TOON : alternative compacte au JSON pour les tableaux. Idéal pour envoyer des stats de matchs à un LLM |
| 65 | [jgravelle/jdatamunch-mcp](https://github.com/jgravelle/jdatamunch-mcp) ★ | 82 | MCP qui interroge des CSV/Excel au lieu de les charger entiers |
| 66 | [mostafamoq/tooner](https://github.com/mostafamoq/tooner) | 9 | Hook Claude Code qui convertit le JSON en TOON |
| 67 | [openai/tiktoken](https://github.com/openai/tiktoken) | 19529 | Compter les tokens d'un texte |

## 8. Préparer les documents et pages web (Markdown propre)

| # | Dépôt | ⭐ | Contenu |
|---|---|---|---|
| 68 | [microsoft/markitdown](https://github.com/microsoft/markitdown) | 192528 | Convertit PDF, Word, Excel… en Markdown léger |
| 69 | [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) ★ | 86398 | Scraping web en Markdown propre pour LLM (ex. pages d'avant-match) |
| 70 | [docling-project/docling](https://github.com/docling-project/docling) | 69681 | Préparation de documents pour l'IA |
| 71 | [VectifyAI/PageIndex](https://github.com/VectifyAI/PageIndex) | 39843 | Index de documents pour RAG sans vecteurs |
| 72 | [ctrlb-hq/ctrlb-decompose](https://github.com/ctrlb-hq/ctrlb-decompose) | 305 | Résumés de logs lisibles par un LLM |

## 9. Empaqueter un dépôt en un seul prompt

| # | Dépôt | ⭐ | Contenu |
|---|---|---|---|
| 73 | [yamadashy/repomix](https://github.com/yamadashy/repomix) | 29041 | Empaquette un dépôt (avec option de compression) |
| 74 | [coderamp-labs/gitingest](https://github.com/coderamp-labs/gitingest) | 16026 | Remplace « hub » par « ingest » dans une URL GitHub |
| 75 | [mufeedvh/code2prompt](https://github.com/mufeedvh/code2prompt) | 7740 | Code → prompt unique avec arborescence |
| 76 | [yttrium400/reducethemtokens](https://github.com/yttrium400/reducethemtokens) | 11 | Squelette compact d'un dépôt |

## 10. Cache sémantique (ne pas repayer la même question)

| # | Dépôt | ⭐ | Contenu |
|---|---|---|---|
| 77 | [zilliztech/GPTCache](https://github.com/zilliztech/GPTCache) | 8214 | Cache sémantique pour LLM |
| 78 | [codefuse-ai/ModelCache](https://github.com/codefuse-ai/ModelCache) | 933 | Cache sémantique (2025) |
| 79 | [thu-nics/C2C](https://github.com/thu-nics/C2C) | 747 | Communication directe entre caches de modèles (ICLR 2026) |
| 80 | [messkan/prompt-cache](https://github.com/messkan/prompt-cache) | 424 | Cache intelligent, −80 % de coûts annoncés |
| 81 | [upstash/semantic-cache](https://github.com/upstash/semantic-cache) | 305 | Cache par similarité (2024) |

## 11. Routage vers des modèles moins chers

| # | Dépôt | ⭐ | Contenu |
|---|---|---|---|
| 82 | [BerriAI/litellm](https://github.com/BerriAI/litellm) ★ | 62164 | Passerelle 100+ LLM avec suivi des coûts, cache et budgets |
| 83 | [musistudio/claude-code-router](https://github.com/musistudio/claude-code-router) | 37880 | Router Claude Code vers différents modèles selon la tâche |
| 84 | [cheaper-inference/OmniRoute](https://github.com/cheaper-inference/OmniRoute) | 81780 | Passerelle multi-fournisseurs |
| 85 | [maximhq/bifrost](https://github.com/maximhq/bifrost) | 9146 | Passerelle LLM rapide avec cache sémantique |
| 86 | [lm-sys/RouteLLM](https://github.com/lm-sys/RouteLLM) | 5641 | Envoie les questions simples à un petit modèle (2024) |
| 87 | [NVIDIA-NeMo/Switchyard](https://github.com/NVIDIA-NeMo/Switchyard) | 3456 | Routage entre modèles et fournisseurs |
| 88 | [ENTERPILOT/GoModel](https://github.com/ENTERPILOT/GoModel) | 1277 | Passerelle IA en Go |
| 89 | [CommonstackAI/UncommonRoute](https://github.com/CommonstackAI/UncommonRoute) | 699 | Routeur automatique, −82 % de coûts annoncés |
| 90 | [NadirRouter/NadirClaw](https://github.com/NadirRouter/NadirClaw) | 660 | Routeur et optimiseur de coûts |
| 91 | [Nanako0129/pilotfish](https://github.com/Nanako0129/pilotfish) | 711 | Le gros modèle planifie, les petits exécutent |
| 92 | [davidecolombo/local-mcp](https://github.com/davidecolombo/local-mcp) | 4 | Délègue les lectures de fichiers à un modèle local Ollama |

## 12. Mémoire externe (moins de contexte à recharger)

| # | Dépôt | ⭐ | Contenu |
|---|---|---|---|
| 93 | [mem0ai/mem0](https://github.com/mem0ai/mem0) | 67922 | Couche de mémoire pour agents |
| 94 | [getzep/graphiti](https://github.com/getzep/graphiti) | 32278 | Graphes de connaissances temps réel |
| 95 | [topoteretes/cognee](https://github.com/topoteretes/cognee) | 32819 | Plateforme de mémoire IA |
| 96 | [MemTensor/MemOS](https://github.com/MemTensor/MemOS) | 12129 | OS de mémoire pour LLM |
| 97 | [cocoindex-io/cocoindex](https://github.com/cocoindex-io/cocoindex) | 11767 | Indexation incrémentale pour agents longs |

## 13. Guides et listes

| # | Dépôt | ⭐ | Contenu |
|---|---|---|---|
| 98 | [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice) | 68200 | Bonnes pratiques Claude Code (dont gestion du contexte) |
| 99 | [Meirtz/Awesome-Context-Engineering](https://github.com/Meirtz/Awesome-Context-Engineering) | 3330 | Panorama de l'ingénierie de contexte |
| 100 | [jihoo-kim/awesome-context-engineering](https://github.com/jihoo-kim/awesome-context-engineering) | 113 | Bibliothèques d'ingénierie de contexte (2025) |
| 101 | [congvmit/awesome-llm-token-reduction](https://github.com/congvmit/awesome-llm-token-reduction) | 8 | Techniques, outils et recherches de réduction de tokens |
| 102 | [ravinperera/ai-token-efficiency-playbook](https://github.com/ravinperera/ai-token-efficiency-playbook) | 19 | Instructions et workflows économes |
| 103 | [antonio86itna/claude-code-efficiency-guide](https://github.com/antonio86itna/claude-code-efficiency-guide) | 8 | Guide pour réduire le gaspillage dans Claude Code |
