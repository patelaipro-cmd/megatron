"""Ligne de commande : python -m megatron <commande>."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

from . import angles_morts, backtest, checkpoint, data, inventory, jeton, llm, marches, marges, suivi, synchro, systeme
from .agents import StatsAgent, fuse
from .store import MemoryStore

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="megatron")
    parser.add_argument("--memoire", default=str(ROOT / "memoire"))
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("reprise", help="affiche le dernier checkpoint")
    sub.add_parser("inventaire", help="régénère docs/registre-depots.md")
    lp = sub.add_parser("llm", help="connexion LLM : statut des fournisseurs ou appel de test")
    lp.add_argument("action", choices=["statut", "test"])
    lp.add_argument("--fournisseur", default="gemini", choices=sorted(llm.PROVIDERS))
    f = sub.add_parser("fusion", help="Méthode de Fusion sur un match (JSON)")
    f.add_argument("tache", help='ex. {"match_id": "x", "xg_home": 1.6, "xg_away": 0.9}')
    pv = sub.add_parser("prevoir", help="fusion puis prévision immuable dans le registre, dans les 5 h avant le coup d'envoi")
    pv.add_argument("tache", help='ex. {"match_id": "F1:2026-11-01:Lens-Lille", "division": "F1", "home": "Lens", "away": "Lille", "date": "2026-11-01"}')
    pv.add_argument("--coup-envoi", required=True, help="date-heure avec fuseau, ex. 2026-11-01T20:00:00+00:00")
    pv.add_argument("--execution", choices=["stats", "multi-llm"], default="stats",
                    help="stats par défaut : Python seul, aucun appel LLM ; multi-llm doit être demandé explicitement")
    pv.add_argument("--contexte-favori", help="JSON des angles morts ; aucune correction de probabilité")
    am = sub.add_parser("angles-morts", help="grille qualitative du favori, sans écriture ni appel réseau")
    am.add_argument("action", choices=["modele", "verifier"])
    am.add_argument("--fichier", help="contexte JSON à vérifier")
    am.add_argument("--match-id")
    am.add_argument("--home")
    am.add_argument("--away")
    am.add_argument("--favori", choices=["H", "A"])
    am.add_argument("--coup-envoi")
    am.add_argument("--au", help="date-heure de vérification avec fuseau")
    rs = sub.add_parser("resultat", help="saisit le résultat d'un match prévu (après le coup d'envoi)")
    rs.add_argument("match_id")
    rs.add_argument("score", help="H, D, A ou score 2-1")
    rs.add_argument("--source", required=True, help="provenance du résultat, ex. URL")
    rs.add_argument("--correction", action="store_true", help="remplace un résultat déjà saisi (historique gardé)")
    for write_parser in (pv, rs):
        write_parser.add_argument("--acces", choices=jeton.ACCES)
        write_parser.add_argument("--jeton", dest="jeton_id", help="identifiant actif du jeton synchronisé")
    jt = sub.add_parser("jeton", help="détenteur coopératif du registre")
    jt.add_argument("action", choices=["statut", "initialiser", "transmettre"])
    jt.add_argument("--acces", choices=jeton.ACCES)
    jt.add_argument("--jeton", dest="jeton_id")
    jt.add_argument("--a", dest="destinataire", choices=jeton.ACCES)
    jt.add_argument("--source")
    sub.add_parser("bilan", help="scores par version, matchs communs, résultats à saisir")
    sub.add_parser("systeme", help="test système de bout en bout sur un match fictif (Fusion + registre)")
    b = sub.add_parser("backtest", help="protocole chronologique dev / validation / test")
    b.add_argument("--division", default="F1")
    b.add_argument("--donnees", default="experiences", choices=["experiences", "complet"],
                   help="experiences = extrait 2020-2026 figé (EXP-001 à 004) ; complet = 2000-2026 + saison en cours")
    b.add_argument("--dev", default="2022/23")
    b.add_argument("--val", default="2023/24")
    b.add_argument("--test", default="2024/25,2025/26")
    b.add_argument("--half-lives", default="90,180,365,730")
    b.add_argument("--shrinks", default="1,3,10")
    b.add_argument("--dixon-coles", default="0", help="valeurs testées sur le dev, ex. 0,1")
    b.add_argument("--a-priori", default="moyenne", help="a priori des équipes nouvelles testés, ex. moyenne,faibles3")
    b.add_argument("--proxys", default="cadres:0", help="proxy:poids des pseudo-buts testés (EXP-004), ex. cadres:0,cadres:0.5,tirs:1")
    b.add_argument("--fixe", help="candidat déjà figé, ex. 90,3,0 ou 90,3,0,faibles3 ou 90,3,0,moyenne,cadres,0.5 : saute la recherche sur le dev")
    b.add_argument("--reference", help="modèle de référence évalué en parallèle, ex. 90,3,0")
    b.add_argument("--sortie", help="dossier où écrire resultats.json et predictions.csv")
    bs = sub.add_parser("bootstrap", help="bootstrap apparié groupé sur plusieurs predictions.csv")
    bs.add_argument("fichiers", nargs="+")
    bs.add_argument("--saisons", default="2024/25,2025/26")
    bs.add_argument("--a", default="candidat")
    bs.add_argument("--b", default="reference")
    mb = sub.add_parser("marches", help="backtest des marchés 2+ et 3+ buts (EXP-006), poisson-v4 figé")
    mb.add_argument("--division", default="F1")
    mb.add_argument("--saisons", required=True, help="ex. 2008/09,2009/10")
    mb.add_argument("--sortie", required=True, help="dossier où écrire predictions_buts.csv et resultats.json")
    mbb = sub.add_parser("marches-bilan", help="critères M1-M3 d'EXP-006 sur plusieurs predictions_buts.csv")
    mbb.add_argument("fichiers", nargs="+")
    mbb.add_argument("--saisons", required=True)
    mr = sub.add_parser("marches-recalibrer", help="EXP-007 : recalibration de Platt apprise puis testée")
    mr.add_argument("--apprentissage", nargs="+", required=True)
    mr.add_argument("--test", nargs="+", required=True)
    mr.add_argument("--saisons-apprentissage", required=True)
    mr.add_argument("--sortie", help="dossier où écrire recalibration.json")
    mg = sub.add_parser("marges", help="calcul brut expérimental des marges de victoire ; aucune écriture")
    mg.add_argument("--xg-home", type=float, required=True)
    mg.add_argument("--xg-away", type=float, required=True)
    sy = sub.add_parser("synchro", help="contrôles de la mémoire avant reprise (rien n'est écrit)")
    sy.add_argument("action", choices=["verifier"])
    sy.add_argument("--reference", help="branche de référence, ex. origin/main : signale un retard")
    args = parser.parse_args(argv)

    if args.cmd == "reprise":
        ckpt = checkpoint.load(MemoryStore(args.memoire))
        print(json.dumps(ckpt, indent=2, ensure_ascii=False) if ckpt else "aucun checkpoint")
    elif args.cmd == "inventaire":
        rows, counts = inventory.build(ROOT / "docs" / "inventaires", ROOT / "docs" / "evaluations.json")
        (ROOT / "docs" / "registre-depots.md").write_text(inventory.render_markdown(rows, counts), encoding="utf-8")
        with (ROOT / "docs" / "registre-depots.csv").open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"{sum(counts.values())} entrées, {len(rows)} dépôts uniques")
    elif args.cmd == "llm":
        if args.action == "statut":
            print(json.dumps(llm.status(), indent=2, ensure_ascii=False))
        else:
            rep = llm.complete_with_fallback(args.fournisseur, [{"role": "user", "content": "Réponds juste : ok"}],
                               max_tokens=5, use_cache=False)
            print(json.dumps(asdict(rep), indent=2, ensure_ascii=False))
    elif args.cmd == "fusion":
        result = fuse(json.loads(args.tache))
        result["reponses"] = [asdict(r) for r in result["reponses"]]
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.cmd in ("prevoir", "resultat"):
        try:
            if args.cmd == "prevoir":
                out = suivi.prevoir(MemoryStore(args.memoire), json.loads(args.tache), args.coup_envoi,
                                    agents=[StatsAgent()] if args.execution == "stats" else None,
                                    acces=args.acces, jeton_id=args.jeton_id,
                                    contexte_favori=angles_morts.charger(args.contexte_favori) if args.contexte_favori else None)
            else:
                out = suivi.resultat(MemoryStore(args.memoire), args.match_id, args.score, source=args.source,
                                     correction=args.correction, acces=args.acces, jeton_id=args.jeton_id).value
        except ValueError as exc:  # anti-fuite, doublon, saisie invalide : rien n'est écrit
            print(f"refus : {exc}")
            return 2
        print(json.dumps(out, indent=2, ensure_ascii=False))
    elif args.cmd == "jeton":
        try:
            if args.action == "statut" and not Path(args.memoire).exists():
                out = {"protege": Path(args.memoire).resolve() == jeton.REAL_MEMORY.resolve(),
                       "initialise": False, "id": None, "detenteur": None}
            elif args.action == "statut":
                out = jeton.statut(MemoryStore(args.memoire))
            elif args.action == "initialiser":
                out = asdict(jeton.initialiser(MemoryStore(args.memoire), args.acces, source=args.source))
            else:
                out = asdict(jeton.transmettre(MemoryStore(args.memoire), args.acces, args.jeton_id, args.destinataire, source=args.source))
        except ValueError as exc:
            print(f"refus : {exc}")
            return 2
        print(json.dumps(out, indent=2, ensure_ascii=False))
    elif args.cmd == "bilan":
        print(json.dumps(suivi.bilan(MemoryStore(args.memoire)), indent=2, ensure_ascii=False))
    elif args.cmd == "systeme":
        rapport = systeme.run()
        print(json.dumps(rapport, indent=2, ensure_ascii=False))
        return 0 if rapport["succes"] else 1
    elif args.cmd == "backtest":
        print(json.dumps(run_backtest(args), indent=2, ensure_ascii=False))
    elif args.cmd == "marches":
        rows = marches.predict_seasons(data.load(data.CURRENT, divisions={args.division}), args.division,
                                       set(args.saisons.split(",")), marches.load_cotes())
        folder = Path(args.sortie)
        folder.mkdir(parents=True, exist_ok=True)
        marches.write_predictions(rows, folder / "predictions_buts.csv")
        out = {"division": args.division, "saisons": args.saisons, "modele": marches.V4,
               "bilan": marches.bilan(marches.read_predictions(folder / "predictions_buts.csv"))}
        (folder / "resultats.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({m: {k: v[k] for k in ("M1_v4_moins_frequences", "M3_ecart_max")}
                          for m, v in out["bilan"].items()}, ensure_ascii=False))
    elif args.cmd == "marches-bilan":
        keep = set(args.saisons.split(","))
        rows = [r for f in args.fichiers for r in marches.read_predictions(Path(f)) if r["saison"] in keep]
        print(json.dumps(marches.bilan(rows), indent=2, ensure_ascii=False))
    elif args.cmd == "marches-recalibrer":
        keep = set(args.saisons_apprentissage.split(","))
        train = [r for f in args.apprentissage for r in marches.read_predictions(Path(f)) if r["saison"] in keep]
        test = [r for f in args.test for r in marches.read_predictions(Path(f))]
        out = marches.recalibrer(train, test)
        text = json.dumps(out, indent=2, ensure_ascii=False)
        if args.sortie:
            (Path(args.sortie) / "recalibration.json").write_text(text + "\n", encoding="utf-8")
        print(text)
    elif args.cmd == "angles-morts":
        try:
            if args.action == "modele":
                out = angles_morts.modele(args.match_id, args.home, args.away, args.favori, args.coup_envoi)
            else:
                if not args.fichier:
                    raise ValueError("--fichier requis")
                out = angles_morts.verifier(angles_morts.charger(args.fichier), at=args.au)
        except (ValueError, TypeError, AttributeError) as exc:
            print(f"refus : {exc}")
            return 2
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0 if args.action == "modele" or out["ok"] else 1
    elif args.cmd == "marges":
        try:
            out = marges.calculer(args.xg_home, args.xg_away)
        except ValueError as exc:
            print(f"refus : {exc}")
            return 2
        print(json.dumps(out, indent=2, ensure_ascii=False))
    elif args.cmd == "synchro":
        rapport = synchro.verifier(args.memoire, args.reference)
        print(json.dumps(rapport, indent=2, ensure_ascii=False))
        return 0 if rapport["ok"] else 1
    elif args.cmd == "bootstrap":
        keep = set(args.saisons.split(","))
        rows = [r for f in args.fichiers for r in backtest.read_predictions(Path(f)) if r["saison"] in keep]
        print(json.dumps(backtest.paired_bootstrap(rows, args.a, args.b), ensure_ascii=False))
    return 0


def _config(text: str) -> backtest.Config:
    hl, k, *rest = text.split(",")
    dc = bool(int(rest[0])) if rest else False
    extra = (rest[1],) if len(rest) > 1 else ()
    if len(rest) > 3:
        extra += (rest[2], float(rest[3]))
    return (float(hl), float(k), dc) + extra


def run_backtest(args) -> dict:
    path = data.DEFAULT_CSV if args.donnees == "experiences" else data.CURRENT
    matches = data.load(path, divisions={args.division})
    out = {"division": args.division,
           "donnees": path.name if args.donnees == "experiences" else [p.name for p in path]}
    if args.fixe:
        candidate = _config(args.fixe)
    else:
        grid = backtest.grid_search(matches, args.division, {args.dev},
                                    [float(x) for x in args.half_lives.split(",")],
                                    [float(x) for x in args.shrinks.split(",")],
                                    [bool(int(x)) for x in args.dixon_coles.split(",")],
                                    tuple(args.a_priori.split(",")),
                                    tuple((x.split(":")[0], float(x.split(":")[1])) for x in args.proxys.split(",")))
        out["grille_dev"] = grid
        g = grid[0]
        candidate = (g["half_life"], g["shrink"], g["dixon_coles"], g["a_priori"], g["proxy"], g["poids_proxy"])
    configs = {"candidat": candidate}
    if args.reference:
        configs["reference"] = _config(args.reference)
    out["modeles"] = {name: dict(zip(("half_life", "shrink", "dixon_coles", "a_priori", "proxy", "poids_proxy"), c))
                      for name, c in configs.items()}
    all_rows = []
    for role, seasons in (("dev", args.dev), ("validation", args.val), ("test", args.test)):
        rows = backtest.predict_seasons(matches, args.division, set(seasons.split(",")), configs)
        all_rows += rows
        out[role] = {"saisons": seasons, **backtest.summarize(rows)}
        if args.reference:
            out[role]["bootstrap_candidat_moins_reference"] = backtest.paired_bootstrap(rows, "candidat", "reference")
    if args.sortie:
        folder = Path(args.sortie)
        folder.mkdir(parents=True, exist_ok=True)
        backtest.write_predictions(all_rows, folder / "predictions.csv")
        (folder / "resultats.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    raise SystemExit(main())
