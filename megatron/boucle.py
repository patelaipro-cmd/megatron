"""Balayage par lots : objectif de cinq dominations, sans assouplir le protocole."""
from __future__ import annotations

from . import syndicate


def boucler(rencontres, evaluer, *, objectif=5, lot=10):
    """Épuise le calendrier fourni ou s'arrête à l'objectif ; jamais de boucle à vide.

    L'appelant fournit un calendrier de matchs futurs vérifié et l'évaluateur.
    Aucun réseau, aucune écriture au registre, aucune promotion de modèle.
    """
    if objectif < 5 or lot < 1:
        raise ValueError("objectif >= 5 et lot >= 1 requis")
    confirmes, analyses, erreurs, passages, vus = [], [], [], [], set()
    queue = list(rencontres)
    for debut in range(0, len(queue), lot):
        passage = {"numero": len(passages) + 1, "examines": 0, "confirmes": 0}
        for rencontre in queue[debut:debut + lot]:
            ident = rencontre["id"]
            if ident in vus:
                continue
            vus.add(ident)
            passage["examines"] += 1
            try:
                analyse = evaluer(rencontre)
            except (ValueError, OSError, KeyError) as exc:
                erreurs.append({"id": ident, "raison": str(exc)})
                continue
            decision = analyse["decision"]
            p2 = analyse["niveaux"]["probabilites"]["victoire_par_2_ou_plus"]
            confirme = (syndicate.ZONE_GO_VALIDEE and decision["decision"] == "GO"
                        and not decision["bloquants"] and not decision["raisons"]
                        and p2 >= syndicate.SEUILS["go_marge_2"])
            ligne = {"rencontre": rencontre, "analyse": analyse, "domination_confirmee": confirme}
            analyses.append(ligne)
            if confirme:
                confirmes.append(ligne)
                passage["confirmes"] += 1
            if len(confirmes) >= objectif:
                break
        passages.append(passage)
        if len(confirmes) >= objectif:
            break
    return {"objectif": objectif, "confirmes": len(confirmes), "manquants": max(0, objectif - len(confirmes)),
            "statut": "OBJECTIF_ATTEINT" if len(confirmes) >= objectif else "CALENDRIER_EPUISE",
            "blocages_globaux": [] if syndicate.ZONE_GO_VALIDEE else ["ZONE_GO_NON_VALIDEE"],
            "passages": passages, "analyses": analyses, "erreurs": erreurs,
            "surveillance_active": False,
            "limite": "Pas de répétition sans nouvelles données ; aucune domination forcée pour remplir le quota."}
