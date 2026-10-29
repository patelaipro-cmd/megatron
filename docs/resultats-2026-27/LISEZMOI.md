# Résultats 2026/27 depuis le 21/09/2026 : audit du 29/10/2026

Règle d'admission : au moins deux familles indépendantes donnent le même score final pour la même
affiche (division, domicile, extérieur), à un jour près, et aucune ne les contredit. Sinon : quarantaine.

| Fichier | Contenu |
|---|---|
| `audit.json` | compteurs, noms reliés par source, décalages horaires, manifeste de la collecte |
| `admis_sources.csv` | 152 matchs admis et les familles qui les confirment |
| `quarantaine.csv` | 1 match : Frosinone – Lecce 5-1 (I1, 29/10), ESPN seul, football-data pas encore à jour |
| `rejets.csv` | 1 match : Rayo Vallecano – Athletic Club (SP1, 10/10), `STATUS_ABANDONED` chez ESPN, absent de football-data |

Constats :
- 403 matchs terminés chez ESPN, 402 chez football-data depuis le 01/08 ; 250 déjà connus de `data/`
  (500 vérifications, 0 conflit de score avec l'historique) ; 152 nouveaux admis ; 0 désaccord de score ; 0 désaccord de date.
- Aucun match de championnat entre le 21/09 et le 08/10 : les deux sources concordent (pause du calendrier).
- API-Football : 5 requêtes refusées (plan gratuit sans accès à la saison 2026 par `season=`).
- Coupes et compétitions européennes : hors du périmètre (championnats seulement).
