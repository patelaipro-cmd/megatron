# EXP-018 : xG d'après-match (Understat) dans les forces d'équipes, jugé contre le bookmaker

**Protocole figé le 29/10/2026 avant toute exécution et avant lecture des données xG.**
Suite d'EXP-017 : v5 n'ajoute rien aux cotes. Question : les xG passés apportent-ils une
information que les cotes n'ont pas ?

## Données

- xG Understat par équipe et par match, 5 ligues, 2014/15-2025/26, collecte unique du workflow
  `xg-historique` (branche `donnees-externes`, `externe/understat/historique/`). Chiffre
  d'après-match : seul le passé d'un match sert à le prévoir.
- Résultats et cotes : `data/matches_top5_2000-2026.csv`. Noms Understat reliés à ceux de `data/`
  par les matchs communs (même date à un jour près, même score) ; un match non relié est exclu et
  compté.

## Modèle `xg-v1`

Filtre dyn-v1 d'EXP-016 (`megatron/dynamique.py`), réglage figé d'EXP-016 (q = 0,0001,
q_saison = 0, P0 = 0,05, c = 0,15, sans correction), où l'observation devient
(1 − w) · buts + w · xG (au lieu des tirs cadrés). Avant 2014/15 et pour un match sans xG :
observation sur les buts seuls (w = 0 pour ce match).

Puis fusion avec le marché comme EXP-017 : log p ∝ α · log xg-v1 + β · log cotes + c_o.

## Périodes (l'historique xG commence en 2014/15)

Chauffe 2000/01-2014/15 ; dev 2015/16-2017/18 ; validation 2018/19-2020/21 ; test 2021/22-2025/26.

## Réglage (dev seulement)

w ∈ {0,25 ; 0,5 ; 0,75 ; 1} choisi sur la log-loss 1X2 dev de xg-v1 seul ; puis (α, β, c_H, c_D)
de la fusion appris sur dev, et la fusion de référence sans xG (dyn-v1 d'EXP-016 + cotes, même
périodes) apprise de la même façon.

## Critères (fusion xg − bookmaker), fixés avant exécution

- **X1** validation : borne haute IC 95 % (bootstrap apparié, 2 000 tirages, graine 1) < 0.
- **X2** test : même borne < 0.
- **X3** test : écart moyen < 0 dans au moins 4 ligues sur 5.
- **X4** test : RPS fusion xg ≤ RPS bookmaker.
- Information : α appris (poids des xG face aux cotes) ; fusion xg − fusion sans xG ; xg-v1 seul
  − v5-cal ; nombre de matchs non reliés.

## Décision prévue

- X1-X4 tenus : la fusion xg devient le candidat 1X2 (PR séparée), à confirmer sur la cohorte
  prospective ; aucune bascule automatique.
- Sinon : les xG passés sont déjà dans les cotes ; l'étage suivant ne porte que sur l'information
  postérieure aux cotes (compositions, absents : EXP-013).
- Aucun GO automatique, aucune probabilité de production modifiée.

## Limites connues avant exécution

- Understat peut avoir révisé ses xG après coup : valeurs d'aujourd'hui ≠ valeurs publiées à l'époque.
- Cotes Bet365 de football-data, pas de clôture. Périodes de test déjà vues par le projet.

## Résultats (exécution du 29/10/2026)

Données : workflow `xg-historique` (run 40953408635, 29/10/2026 20:56-20:58 UTC), 21 589 matchs
Understat 2014/15-2025/26 ; 21 471 reliés à `data/`, 117 non reliés, 1 score différent (exclus).
`python scripts/exp018_xg.py --xg <externe/understat/historique> --sortie docs/experiences/EXP-018`.

**Verdict : REJETÉ (X1, X2 non tenus). Les xG passés sont déjà dans les cotes.**

Grille dev (xg-v1 seul) : w = 0,25 → 0,96831 ; **0,5 → 0,96743** ; 0,75 → 0,96827 ; 1 → 0,97092.
Fusion apprise sur dev : α (xg-v1) = −0,138 ; β (cotes) = 1,189. Fusion de référence sans xG :
α (dyn-v1) = −0,083 ; β = 1,137. Poids du modèle légèrement négatif : aucune information ajoutée.

| | validation 2018-21 (5 377) | test 2021-26 (8 906) |
|---|---:|---:|
| fusion xg − bookmaker [IC 95 %] | +0,00021 [−0,00078 ; +0,00129] | −0,00053 [−0,00126 ; +0,00024] |
| fusion xg − fusion sans xG | +0,00008 [−0,00015 ; +0,00030] | +0,00003 [−0,00016 ; +0,00020] |
| RPS fusion xg / bookmaker | 0,19657 / 0,19658 | 0,19519 / 0,19537 |

Par ligue, test : F1 −0,0004 ; E0 0,0000 ; D1 0,0000 ; SP1 −0,0021 ; I1 0,0000 (4/5 < 0, écarts
négligeables). Critères : X1 non ; X2 non ; X3 oui ; X4 oui.

Information, hors critères : **les xG améliorent nettement le modèle statistique seul.**
- xg-v1 − dyn-v1 (tirs cadrés) : validation −0,0025 [−0,0040 ; −0,0009], test −0,0021 [−0,0034 ; −0,0009].
- xg-v1 − v5-cal (matchs d'EXP-008 2018-26, 14 284) : −0,0017 [−0,0031 ; −0,0002].

Ce gain reste sous les cotes (xg-v1 seul ≈ 0,984 contre 0,971 en test). Il ne change rien au 1X2
de production tant que le marché est disponible. Une promotion de xg-v1 à la place de v5-cal, pour
les matchs sans cotes, demanderait son propre protocole.

Conséquence (décision prévue) : l'étage suivant ne porte que sur l'information postérieure aux
cotes : compositions et absents (EXP-013, collecte en cours).
