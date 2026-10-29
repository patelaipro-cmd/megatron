"""Pondération des absences : méthode expérimentale, non calibrée, sans effet par défaut.

L'ancien barème WININVEST de septembre 2026 est introuvable dans les sources accessibles
(dépôt, fichiers du projet, mémoire) : il n'est pas reconstitué de tête. Ce module propose une
méthode transparente à calibrer (protocole docs/experiences/EXP-013-absences.md) :

1. importance d'un joueur = temps de jeu × (0,5 + 0,5 × apport), où l'apport est la part
   offensive de l'équipe (buts + passes, ou xG + xA) pour un joueur de champ, et une base
   défensive par poste ; une donnée inconnue prend une valeur prudente et est signalée ;
2. perte = importance × (1 − niveau du remplaçant) × probabilité d'absence ;
3. absences simultanées d'une même ligne : cumul non additif 1 − Π(1 − perte), majoré de
   ``BONUS_SIMULTANE`` par absent supplémentaire de la ligne (désorganisation) ;
4. indices d'équipe offensif et défensif = moyenne des lignes pondérée par poste, entre 0 et 1.

Les paramètres ci-dessous sont des choix de départ, pas des résultats. ``ajuster_intensites``
n'applique un effet que si des coefficients non nuls lui sont passés explicitement ; ``prevoir``
ne l'appelle pas. Aucune probabilité n'est modifiée sans expérience validée.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

VERSION = "absences-exp-v0"
STATUT = "EXPERIMENTAL_NON_CALIBRE"
POSTES = ("G", "D", "M", "F")
BASE_DEFENSIVE = {"G": 1.0, "D": 0.6, "M": 0.3, "F": 0.0}  # apport défensif supposé par poste
POIDS_OFFENSIF = {"G": 0.0, "D": 0.1, "M": 0.35, "F": 0.55}  # part de chaque ligne dans l'indice offensif
POIDS_DEFENSIF = {"G": 0.35, "D": 0.45, "M": 0.2, "F": 0.0}
PART_OFFENSIVE_PLEINE = 0.30  # un joueur qui pèse 30 % des buts + passes de l'équipe a un apport offensif de 1
BONUS_SIMULTANE = 0.15
PROBA_ABSENCE = {"absent": 1.0, "suspendu": 1.0, "blesse": 1.0, "incertain": 0.5}
DEFAUT = {"part_minutes": 0.5, "part_offensive": 0.0, "remplacant_niveau": 0.5}  # valeurs prudentes si inconnu


@dataclass
class Absent:
    joueur: str
    poste: str | None  # G, D, M, F ; None = inconnu (traité comme M, signalé)
    statut: str = "absent"  # absent, suspendu, blesse, incertain
    part_minutes: float | None = None  # minutes jouées / minutes possibles sur les derniers matchs (0-1)
    part_offensive: float | None = None  # part des buts + passes (ou xG + xA) de l'équipe (0-1)
    remplacant_niveau: float | None = None  # niveau du remplaçant disponible relatif à l'absent (0-1)
    chance_jouer: float | None = None  # si une source la donne (FPL) : remplace la probabilité du statut
    sources: list[str] = field(default_factory=list)


def _borne(x: float, nom: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not 0 <= x <= 1:
        raise ValueError(f"{nom} attendu entre 0 et 1, reçu {x!r}")
    return float(x)


def evaluer_joueur(a: Absent) -> dict:
    manquants, val = [], {}
    poste = a.poste
    if poste is None:
        manquants.append("poste")
        poste = "M"
    if poste not in POSTES:
        raise ValueError(f"{a.joueur} : poste {a.poste!r} inconnu (G, D, M, F)")
    if a.statut not in PROBA_ABSENCE:
        raise ValueError(f"{a.joueur} : statut {a.statut!r} inconnu")
    for champ in ("part_minutes", "part_offensive", "remplacant_niveau"):
        v = getattr(a, champ)
        if v is None:
            manquants.append(champ)
            v = DEFAUT[champ]
        val[champ] = _borne(v, champ)
    p_abs = 1 - _borne(a.chance_jouer, "chance_jouer") if a.chance_jouer is not None else PROBA_ABSENCE[a.statut]
    apport_off = min(1.0, val["part_offensive"] / PART_OFFENSIVE_PLEINE)
    apport = max(apport_off, BASE_DEFENSIVE[poste])
    importance = val["part_minutes"] * (0.5 + 0.5 * apport)
    perte = importance * (1 - val["remplacant_niveau"]) * p_abs
    return {"joueur": a.joueur, "poste": poste, "statut": a.statut, "probabilite_absence": round(p_abs, 4),
            "importance": round(importance, 4), "apport_offensif": round(apport_off, 4), "perte": round(perte, 4),
            "donnees_manquantes": manquants, "sources": list(a.sources)}


def evaluer_equipe(absents: list[Absent]) -> dict:
    """Indices offensif et défensif de l'équipe (0 = aucune perte, 1 = perte totale), détail par joueur."""
    joueurs = [evaluer_joueur(a) for a in absents]
    lignes = {}
    for poste in POSTES:
        pertes = [j["perte"] for j in joueurs if j["poste"] == poste]
        reste = 1.0
        for p in pertes:
            reste *= 1 - p
        cumul = 1 - reste
        n = sum(1 for j in joueurs if j["poste"] == poste and j["probabilite_absence"] >= 0.5)
        lignes[poste] = round(min(1.0, cumul * (1 + BONUS_SIMULTANE * max(0, n - 1))), 4)
    offensif = sum(POIDS_OFFENSIF[p] * lignes[p] for p in POSTES)
    defensif = sum(POIDS_DEFENSIF[p] * lignes[p] for p in POSTES)
    manquants = sorted({f"{j['joueur']} : {c}" for j in joueurs for c in j["donnees_manquantes"]})
    return {"version": VERSION, "statut": STATUT, "indice_offensif": round(offensif, 4),
            "indice_defensif": round(defensif, 4), "lignes": lignes, "joueurs": joueurs,
            "donnees_manquantes": manquants, "effet_probabilites": "aucun (coefficients non calibrés)"}


def consolider(absences: list[dict], titulaires_confirmes: set[str] | None = None) -> dict:
    """Fusionne des déclarations d'absence de plusieurs sources et signale les contradictions.

    ``absences`` : dicts {joueur, statut, source}. Une compo officielle prime : un joueur annoncé
    absent mais titulaire confirmé est retiré des absents et la contradiction est rapportée.
    Deux sources en désaccord sur le statut gardent le statut le plus prudent (incertain).
    """
    titulaires = titulaires_confirmes or set()
    par_joueur: dict[str, list[dict]] = {}
    for d in absences:
        par_joueur.setdefault(d["joueur"], []).append(d)
    retenus, contradictions = {}, []
    for joueur, decl in par_joueur.items():
        statuts = {d["statut"] for d in decl}
        sources = sorted({d.get("source", "?") for d in decl})
        if joueur in titulaires:
            contradictions.append(f"{joueur} annoncé {'/'.join(sorted(statuts))} ({', '.join(sources)}) mais titulaire confirmé")
            continue
        if len(statuts) > 1:
            contradictions.append(f"{joueur} : statuts divergents {sorted(statuts)} ({', '.join(sources)}) → incertain")
            retenus[joueur] = {"joueur": joueur, "statut": "incertain", "sources": sources}
        else:
            retenus[joueur] = {"joueur": joueur, "statut": statuts.pop(), "sources": sources}
    return {"absents": list(retenus.values()), "contradictions": contradictions}


def ajuster_intensites(lam_equipe: float, lam_adverse: float, eq: dict, adv: dict, *,
                       alpha_offensif: float = 0.0, alpha_defensif: float = 0.0) -> dict:
    """Buts attendus après absences : λ_eq × (1 − α_off · off_eq) × (1 + α_def · def_adv), et symétrique.

    Coefficients nuls par défaut : aucun effet. Des coefficients non nuls ne sont admis qu'avec
    un résultat d'expérience validée (EXP-013) ; la sortie le rappelle.
    """
    for a in (alpha_offensif, alpha_defensif):
        if not 0 <= a <= 1:
            raise ValueError("coefficients attendus entre 0 et 1")
    le = lam_equipe * (1 - alpha_offensif * eq["indice_offensif"]) * (1 + alpha_defensif * adv["indice_defensif"])
    la = lam_adverse * (1 - alpha_offensif * adv["indice_offensif"]) * (1 + alpha_defensif * eq["indice_defensif"])
    actif = bool(alpha_offensif or alpha_defensif)
    return {"lam_equipe": le, "lam_adverse": la, "ajuste": actif,
            "statut": "EXPERIMENTAL_NON_VALIDE" if actif else "SANS_EFFET",
            "coefficients": {"alpha_offensif": alpha_offensif, "alpha_defensif": alpha_defensif}}


def depuis_dict(d: dict) -> Absent:
    champs = {k: d[k] for k in asdict(Absent("x", None)) if k in d}
    return Absent(**champs)
