# megatron
auto construction machine d'analyse de football

## MEGATRON CORE

Socle Python (bibliothèque standard, Python 3.10+) : mémoire persistante, checkpoint de reprise,
registre de prévisions anti-fuite temporelle, interface d'agents et Méthode de Fusion.

```bash
python -m megatron reprise      # reprendre là où la dernière session s'est arrêtée
python -m megatron inventaire   # registre d'évaluation des dépôts (docs/registre-depots.md)
python -m megatron fusion '{"match_id": "demo", "xg_home": 1.6, "xg_away": 0.9}'
python -m unittest discover -s tests -t . -v
```

Architecture, diagnostic, plan et journal de décisions : [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
