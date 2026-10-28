# megatron
auto construction machine d'analyse de football

## MEGATRON CORE

Socle Python (bibliothèque standard, Python 3.10+) : mémoire persistante, checkpoint de reprise,
registre de prévisions anti-fuite temporelle, interface d'agents et Méthode de Fusion.

```bash
python -m megatron reprise      # reprendre là où la dernière session s'est arrêtée
python -m megatron inventaire   # registre d'évaluation des dépôts (docs/registre-depots.md)
python -m megatron llm statut   # fournisseurs LLM : clé présente, réseau ouvert (pip install -r requirements-llm.txt)
python -m megatron llm test --fournisseur gemini
scripts/llama_local.sh            # modèle local sans API (llama.cpp + Qwen3-4B, CPU) ; puis --fournisseur llamacpp
python -m megatron fusion '{"match_id": "demo", "xg_home": 1.6, "xg_away": 0.9}'
python -m megatron backtest --division F1   # backtest chronologique (EXP-001)
python -m unittest discover -s tests -t . -v
```

Architecture, diagnostic, plan et journal de décisions : [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
