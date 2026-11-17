# MEGATRON × SYNDICATE V2 — déploiement proposé

Cette branche prépare l'intégration de SYNDICATE DAILY 10 avec MEGATRON.

## Source du kit
Archive locale de conversation : `megatron_syndicate_v2_deploiement_pret.zip`. Les fichiers du kit **ne sont pas encore importés dans cette branche**.

## Étapes avant activation
1. Importer `dashboard.py`, `daily.py`, `fusion.py`, `btts_oui_v4/`, `requirements.txt`, `tests/`, et `SYNDICATE_ARCHIVE.md` du kit.
2. Ajouter `FOOTBALL_DATA_API_KEY` dans GitHub Actions Secrets ; ne jamais publier la clé.
3. Vérifier les tests et les permissions des compétitions.
4. Ajouter le workflow de planification après validation de l'exécution manuelle.
5. Déployer `dashboard.py` sur un hébergeur Streamlit et fournir un stockage partagé pour `data/predictions.json`.

## Précautions
- Le workflow du kit produit un artefact GitHub Actions, **pas** un fichier automatiquement disponible dans Streamlit.
- Les probabilités BTTS/BLOWOUT ne sont pas calibrées sur un historique validé.
- Aucune mise ni pari automatique.
- Ne pas annoncer un service en ligne avant publication et test de son URL.
