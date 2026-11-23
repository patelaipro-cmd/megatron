# MEGATRON × SYNDICATE V2

Intégration en cours sur branche dédiée. Dashboard Streamlit autonome : `streamlit run syndicate_v2/dashboard.py`.

Le dashboard lit `syndicate_v2/data/predictions.json`, qui doit être généré à partir de données réelles par le pipeline. Aucune donnée inventée n'est livrée.

**À faire avant production :** importer le pipeline `daily.py` et ses modules depuis le kit V2, configurer `FOOTBALL_DATA_API_KEY` dans les secrets GitHub, tester les résultats, relier la sortie GitHub Actions au stockage accessible par Streamlit, puis déployer sur un hébergeur.

Ne pas confondre BTTS OUI et BLOWOUT : les critères MAX/TTF ne sont pas des probabilités calibrées.
