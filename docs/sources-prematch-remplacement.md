# Remplacement d'API-Football — sources Web prématch

État : **importation locale/GitHub de fiches attribuées opérationnelle** ; **extraction
HTML et accès Premium NON opérationnels**. Le workflow `collecte-externe.yml` ne
sélectionne plus `apifootball` et n'injecte plus `API_FOOTBALL_KEY`. Les archives
historiques et le vieux lecteur restent lisibles, sans être effacés. Le workflow
`resultats.yml` relève d'un autre circuit et reste inchangé.

| Site | Usage autorisé dans MEGATRON | Interprétation / limite |
|---|---|---|
| [Sports Mole](https://www.sportsmole.co.uk/football/) | Analyse, enjeu, absences rapportées, XI probable | Prévision journalistique, **pas** XI officiel |
| [SportsGambler](https://www.sportsgambler.com/lineups/football/) | XI probables, XI « confirmed » selon le fournisseur, analyse | Confirmation du fournisseur à revérifier auprès du club/ligue |
| [PianetaFanta](https://www.pianetafanta.it/probabili-formazioni-fantacalcio) | XI probables et analyse, surtout Serie A | Probable, **jamais** confirmé automatiquement |
| [180Score](https://180score.com/faq/) | Classements, H2H, XI fournisseur, probabilités **1X2** | Premium seulement via relevé autorisé ; 1X2 **≠ V+2** |
| [Xpertstats](https://xpertstats.com/faq) | Classements général/domicile/extérieur, forme, trois H2H, analyses | Relevé autorisé ; aucun XI confirmé attribué sans preuve |

## Voie de collecte effectivement implémentée

1. Consulter réellement une page, relever un **fait court** et son URL, puis
   noter **la vraie heure de consultation** (`collecte_le`) et le coup d'envoi.
2. Préparer une fiche JSON dans `externe/imports/<source>/<nom>.json` sur la
   branche **de données** `donnees-externes`, ou dans un dossier local dédié.
   Ne copier ni pages complètes, ni secrets, ni cookies de session dans Git.
3. Exécuter `python scripts/collecte_externe.py --sortie /CHEMIN/externe
   --sources sportsmole,sportsgambler,pianetafanta,180score,xpertstats`.
   Chaque fiche valide est archivée sans écrasement dans
   `externe/sites/<source>/<AAAA-MM-JJ>/<HHMMSS>-<empreinte>.json`.
   Une source sans fiche donne **`attente`**, jamais `ok`.
4. Pour les XI, transférer vers l'archive EXP-022 :
   `python scripts/exp022_compositions.py importer-sites --dossier /CHEMIN/externe
   --archive /CHEMIN/exp022-xi.jsonl --au 2026-11-14T18:10:00+01:00`.

### Exemple de fiche : analyse Sports Mole

Cet exemple est **illustratif, à ne pas déposer tel quel** : sa date de capture
doit être remplacée par l'heure réelle d'une consultation et l'identité d'un
match effectivement vérifié.

```json
{
  "source": "sportsmole",
  "type": "analyse",
  "source_url": "https://www.sportsmole.co.uk/football/sweden/uefa-nations-league/preview/sweden-vs-bosnia-hvina-prediction-team-news-lineups_608998.html",
  "match_id": "observation:sweden-bosnia-2026-11-14",
  "domicile": "Suède",
  "exterieur": "Bosnie-Herzégovine",
  "competition": "UEFA Nations League",
  "coup_envoi": "2026-11-14T19:45:00+00:00",
  "collecte_le": "2026-11-14T17:00:00+00:00",
  "publie_le": null,
  "donnees": {"enjeu": "Première place du groupe et promotion en Ligue A"}
}
```

Autres `type` :

- `xi` : `donnees={"statut":"probable|confirmee_fournisseur",
  "equipes":{"H":{"titulaires":[...]},"A":{"titulaires":[...]}}}` ;
  validation EXP-022, jamais `confirmee_officielle` sur un site tiers.
- `classement` : `classement_au`, `rang_domicile`, `rang_exterieur`, `portee`.
- `h2h` : une à trois rencontres datées, score complet et, **seulement si
  vérifié**, `classement_avant={au, rang_domicile, rang_exterieur, source_url}`
  où `au` précède strictement le H2H. Le classement actuel n'est jamais substitué
  à un classement historique.
- `prediction` : seulement le marché `1X2`, somme H/D/A proche de 1 ; opinion
  externe non calibrée, sans effet automatique sur le modèle V+2.

## Limites et risque de fausse complétude

Le 14/11/2026, les tests d'accès HTTP depuis le runtime Python ont rencontré des
**429** pour PianetaFanta/180Score et des expirations de délai pour les autres.
En revanche, **TinyFish a réussi à lire les pages publiques des cinq sites**,
y compris l'exemple Sports Mole (enjeu, absences, XI probables) et une fiche
PianetaFanta (XI probables et indisponibles). Cette lecture ponctuelle via le
connecteur ChatGPT **n'est pas accessible automatiquement depuis GitHub Actions**
et n'est pas un test du collecteur Python en production. Il n'y a ni
API publique vérifiée pour les cinq sites, ni session Premium disponible dans
GitHub Actions ; aucun contournement de restriction ou reproduction massive
de contenu ne doit être entrepris. Les captures déclarées ne prouvent pas à
elles seules leur authenticité : un analyste vérifie la page et les horodatages.

Les profils TinyFish visibles actuellement n'ont pas de connexion **180score.com**
ou **xpertstats.com** confirmée dans leur inventaire ; on ne peut pas prétendre
que les onglets Premium y soient accessibles sans vérification de connexion.

Une nouvelle fiche n'améliore **aucune probabilité** sans protocole EXP-023 :
comparaison à historique antérieur, test chronologique indépendant, Brier/
log-loss et calibration par championnat. Les XI probables, XI confirmés par un
fournisseur et compositions officielles doivent demeurer distincts.
