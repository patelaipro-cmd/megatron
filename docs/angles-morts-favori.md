# Comment le favori peut-il perdre ou faire nul ?

La grille documente des scénarios sportifs. Elle n'attribue ni points de risque,
ni décalage numérique arbitraire, ni signal GO. Chaque information inconnue
reste inconnue. Le modèle quantitatif ne voit pas ses probabilités modifiées.

| Angle | Vérification concrète |
|---|---|
| Favori surévalué | Niveau des derniers adversaires et occasions derrière les scores |
| Adversaire en progression | Coach, retours, changement tactique et forme sous-jacente |
| Adaptation depuis les H2H | Faiblesses corrigées, schéma et personnel différents |
| Style gênant | Bloc bas, pressing ciblé, transitions, jeu aérien |
| Dépendance joueur/duo | Création, finition, organisation et qualité des remplaçants |
| Fragilité défensive | Latéraux hauts, défense lente, pertes axiales et mauvais repli |
| Rotation/fatigue | Minutes jouées, récupération, voyages et prochain match |
| Enjeu asymétrique | Conséquence concrète d'un nul, d'une victoire ou d'une défaite |
| Terrain/déplacement | Rendement extérieur et conditions locales |
| Coups de pied arrêtés | Duels aériens, marquage et spécialistes disponibles |
| Construction de l'écart | Expulsions, penalties, buts tardifs derrière les anciens cartons |
| Gestion de l'avantage | Attitude après le premier but, égalisations encaissées |
| Informations manquantes | Composition, absences et changements non suffisamment documentés |

## Comparateur obligatoire

Ancien H2H → dernier H2H → situation actuelle, avec quatre axes : adaptation
adverse, construction de l'écart, dépendance joueur/duo, contexte du match.
Chaque score H2H précise ses équipes domicile/extérieur ; orientation inconnue = dossier incomplet.
Dates et scores H2H inconnus restent nuls ; ce comparateur ne remplace pas
l'examen des cinq derniers H2H lorsque ces données sont disponibles.
Le score final actuel est interdit dans cette analyse pré-match.
Les dates anciennes peuvent être insuffisantes pour décrire l'équipe actuelle :
expliquer explicitement ce qui a changé plutôt que réutiliser un ancien carton.

## Trois contre-scénarios

- Défaite : comment l'adversaire pourrait-il gagner ?
- Nul : comment peut-il empêcher le favori de gagner ?
- Victoire courte : qu'est-ce qui empêche un succès du favori par deux buts ou plus ?

Chaque hypothèse référence des angles et décrit un mécanisme sportif. Une
hypothèse n'est pas transformée en observation. Un 4-1 historique doit être
expliqué (construction de l'écart, contexte), pas uniquement compté.

## Format et commandes

L'exemple `examples/contexte_favori_v1.json` est entièrement fictif et vide de
constats. Le modèle s'obtient sans écriture ni réseau :

```sh
python -m megatron angles-morts modele --match-id '<id>' --home '<domicile>' --away '<extérieur>' --favori H --coup-envoi '<date avec fuseau>'
python -m megatron angles-morts verifier --fichier contexte.json
```

Pour une relecture historique explicitement datée, ajouter `--au <date avec
fuseau>` au vérificateur. Cela ne prouve pas qu'une prévision a effectivement
été enregistrée à cette date. `prevoir` applique sa propre heure d'exécution et
ses contrôles temporels.

Pour un angle documenté : `constat`, `mecanisme`, effets parmi `defaite`, `nul`,
`victoire_courte`, et sources structurées `{url, famille, publie_le, collecte_le}`.
Une information manque ? Utiliser `inconnu` ou `a_verifier`, expliquer les
`informations_manquantes`, sans inventer de constat ou de source. Pour une
preuve de catégorie `absences`, trois sites et familles distinctes sont requis avant
que le dossier soit considéré structurellement documenté. L'identité de famille
est déclarative : trois domaines qui recopient la même dépêche ne sont pas
indépendants. L'accessibilité, le contenu réel, la pertinence et la fraîcheur des
informations restent à vérifier par la collecte et le lecteur. Le validateur ne
navigue pas sur les URL et n'authentifie aucune source.

Statuts : `INVALIDE` (code 1 du vérificateur), `INCOMPLET` (code 0, travail à
compléter), `DOCUMENTE_NON_VERIFIE` (code 0, sources déclarées). Aucun de ces
statuts ne constitue une validation sportive ni une probabilité d'événement.
Le code 0 signifie seulement absence d'erreur de structure détectée.

## Intégration au parcours

```sh
python -m megatron prevoir '<tache JSON>' --coup-envoi '<date>' --contexte-favori contexte.json --acces codex --jeton '<id actif>'
```

Le contexte est facultatif pour conserver les parcours existants. Le contexte
fourni doit correspondre à l'identifiant, au coup d'envoi et aux équipes de la
tâche lorsqu'elles sont renseignées. Un document invalide est refusé avant appel
aux agents et sans écriture du registre. Un document incomplet est conservé
comme tel ; le résultat ne doit pas être présenté comme une analyse sportive
complète. Sans document : `contexte_favori_statut = NON_FOURNI`.

La trace fusion du registre conserve le document et le rapport de structure ;
le retour de prevoir expose son statut. Les probabilités sont strictement celles
des agents et ne sont pas modifiées par la grille. Les règles de jeton, de
fenêtre de cinq heures et de doublons restent appliquées. Tester uniquement
en mémoire temporaire ; aucune activation d'API LLM n'est nécessaire.

Cette étape rend les angles inspectables. Leur collecte automatique, leur
comparaison à des sources indépendantes et la mesure d'un éventuel gain sur les
pronostics restent à construire et à évaluer sur une cohorte prospective.
