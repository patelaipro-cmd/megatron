# Marges de victoire — protocole v0 avant évaluation

État : contrat fonctionnel et calcul brut ; aucune calibration, aucune
promotion, aucun résultat d'expérience revendiqué. Ce protocole est commité
avant de calculer des performances historiques. EXP-008 est un travail distinct.

## Événements

Équipe désignée avant le match, domicile H ou extérieur A. Sur les scores de fin
du temps réglementaire (arrêts de jeu inclus, prolongation et tirs au but exclus) :

| Événement | Domicile | Extérieur |
|---|---|---|
| Victoire simple | h > a (1X2 : H) | a > h (1X2 : A) |
| Victoire par au moins deux buts | h - a >= 2 (`H_MARGE_2PLUS`) | a - h >= 2 (`A_MARGE_2PLUS`) |
| Victoire par au moins trois buts | h - a >= 3 (`H_MARGE_3PLUS`) | a - h >= 3 (`A_MARGE_3PLUS`) |

Ce sont des événements emboîtés : P(3+) <= P(2+) <= P(victoire simple).
Les lignes ne sont pas exclusives et ne se somment pas à 100 %. Un nul ou une
défaite résout toutes les marges du côté concerné à « non ».
Le score 2-1 est un total 3+ mais pas une victoire par 2+ ; 4-1 valide les deux
marges H ; 1-4 valide les deux marges A. Aucun favori choisi après le résultat.
Les anciennes clés `2+` / `3+` gardent strictement leur sens de total de buts.

## Étape technique autorisée

- Contrat de résolution à partir du score ; refus des scores invalides.
- Calcul brut depuis deux intensités Poisson fournies explicitement, sans appel
  réseau, sans source inventée et sans paramètre appris sur les scores futurs.
- Tests exacts sur des cas limites et une loi de référence ; marchés distincts
  dans le registre bas niveau pour une future évaluation en mémoire isolée.
- Aucune activation dans prevoir, aucun seuil GO automatique. La calibration
  du total de buts d'EXP-007 n'est jamais réutilisée pour les marges.

## Évaluation à effectuer séparément (non exécutée)

Avant toute expérience, publier le script, le manifeste de données (SHA, ligue,
période, heures/fuseaux et scores réglementaires), les exclusions et les critères.
Chaque match ne fournit qu'une observation ; le bootstrap doit apparier les
prévisions et respecter le groupement des matchs/saisons, pas traiter les quatre
marchés du même match comme des observations indépendantes.

Plan initial : réglage sur 2008-2016, calibration sur 2016-2020, réévaluation
rétrospective figée sur 2020-2026. Ces périodes ont déjà servi aux travaux du
projet : la dernière n'est pas un test vierge. Une cohorte prospective horodatée,
non utilisée dans le développement, est indispensable pour juger la généralisation.
Données strictement antérieures au coup d'envoi, contrôle de fraîcheur, aucune
réécriture des prévisions ; résultats et absences provenant de sources vérifiées.

Comparer par côté et seuil : fréquences historiques antérieures et Poisson brut,
puis candidat calibré. Rapporter effectifs, Brier, log-loss, courbes de calibration,
IC appariés, ligues/saisons et tranche P >= 0,60. Sans cotes correspondant aux
marges exactes, aucune conclusion de rentabilité ni comparaison bookmaker.

Critères proposés pour une promotion (à figer avec l'expérience avant exécution) :
borne haute de l'IC95 de l'écart de log-loss candidat moins fréquences < 0,
amélioration dans au moins 4 ligues sur 5, erreur de calibration <= 0,03 dans
chaque tranche comptant au moins 500 matchs. Une tranche moins fournie est
insuffisamment documentée, elle n'est pas déclarée validée. Rapporter aussi les
écarts au brut ; pas de sélection de seuil ou de ligue après observation du test.
Le seuil métier expérimental de 60 % pour la victoire par 2+ ne prouve pas la
calibration du modèle et reste inactif tant que cette validation n'est pas faite.
