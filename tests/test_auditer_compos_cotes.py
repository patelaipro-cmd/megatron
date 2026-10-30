import math
import csv
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from scripts.auditer_compos_cotes import auditer, instant, main

AU = instant("2026-10-30T19:59:00Z")


def compo(event="1", heure="19:00", n=11):
    return [{"event_id": event, "division": "F1", "coup_envoi": "2026-10-30T20:00:00Z",
             "collecte_le": f"2026-10-30T{heure}:00Z", "equipe": team,
             "source": "espn", "statut": "titulaire", "joueur_id": str(j)}
            for team in ("A", "B") for j in range(n)]


def cote(heure, h=2, event="1", book="Book", type_ligne="courante"):
    return {"evenement_id": event, "division": "F1", "coup_envoi": "2026-10-30T20:00:00Z",
            "collecte_le": f"2026-10-30T{heure}:00Z", "source": "espn", "type_ligne": type_ligne,
            "bookmaker": book, "domicile": "A", "exterieur": "B", "cote_H": h, "cote_D": 3, "cote_A": 4}


class TestAuditComposCotes(unittest.TestCase):
    def test_paire_sans_marge_et_mouvement_signe(self):
        r = auditer(compo() + compo(heure="19:10"), [cote("18:55"), cote("19:05", 1.5)], AU)
        self.assertEqual(r["matchs_avec_compos_completes"], 1)
        self.assertEqual(r["matchs_apparies"], 1)
        p = r["paires"][0]
        self.assertAlmostEqual(sum(p["probabilites_sans_marge_apres"].values()), 1)
        self.assertGreater(p["mouvement_points"]["H"], 0)
        self.assertAlmostEqual(sum(p["mouvement_points"].values()), 0, places=5)
        self.assertEqual(p["premiere_compo_complete_collectee_le"], "2026-10-30T19:00:00+00:00")

    def test_pas_de_remplacement_par_ouverture_ou_autre_bookmaker(self):
        r = auditer(compo(), [cote("18:55", type_ligne="ouverture"), cote("18:55", book="Autre"), cote("19:05")], AU)
        self.assertEqual(r["paires_match_bookmaker"], 0)

    def test_incomplet_repetitions_et_deux_matchs_simultanes(self):
        cs = compo() * 2 + compo(event="2") + compo(event="3", n=10)
        odds = [cote(t, event=e) for e in ("1", "2", "3") for t in ("18:55", "19:05")]
        r = auditer(cs, odds, AU)
        self.assertEqual(r["matchs_avec_compos_completes"], 2)
        self.assertEqual(r["matchs_apparies"], 2)

    def test_apres_coup_envoi_et_capture_simultanee_exclues(self):
        r = auditer(compo(), [cote("18:55"), cote("19:00"), cote("20:01")], AU)
        self.assertEqual(r["paires_match_bookmaker"], 0)
        self.assertEqual(r["exclusions_lignes_ou_captures"]["cote_hors_temps"], 1)

    def test_dates_naives_cotes_non_finies_et_contradictions(self):
        for v in (math.nan, math.inf, 1):
            r = auditer(compo(), [cote("18:55", v), cote("19:05")], AU)
            self.assertEqual(r["paires_match_bookmaker"], 0)
        r = auditer(compo(), [cote("18:55"), cote("18:55", 2.1), cote("19:05")], AU)
        self.assertEqual(r["series_non_appariees"]["cotes_contradictoires"], 1)
        with self.assertRaises(ValueError):
            instant("2026-10-30T19:00:00")

    def test_sources_marche_identite_et_fenetre(self):
        for field, value, reason in (("division", "E0", "division_ou_coup_envoi_non_concordant"),
                                     ("coup_envoi", "2026-10-30T20:01:00Z", "division_ou_coup_envoi_non_concordant"),
                                     ("domicile", "C", "equipes_non_concordantes")):
            odds = [{**cote(t), field: value} for t in ("18:55", "19:05")]
            r = auditer(compo(), odds, AU)
            self.assertEqual(r["matchs_apparies"], 0)
            self.assertEqual(r["diagnostic_series"][0]["statut"], reason)
        for source in ("autre", ""):
            r = auditer([{**r, "source": source} for r in compo()], [cote("18:55"), cote("19:05")], AU)
            self.assertEqual(r["matchs_apparies"], 0)
        r = auditer(compo(), [{**cote("18:55"), "marche": "corners"}, cote("19:05")], AU)
        self.assertEqual(r["matchs_apparies"], 0)
        r = auditer(compo(), [cote("17:29"), cote("19:05")], AU)
        self.assertEqual(r["series_non_appariees"]["sans_cote_avant"], 1)

    def test_contradiction_brute_meme_distribution(self):
        x = cote("18:55")
        y = {**x, **{f"cote_{o}": 2 * x[f"cote_{o}"] for o in "HDA"}}
        r = auditer(compo(), [x, y, cote("19:05")], AU)
        self.assertEqual(r["series_non_appariees"]["cotes_contradictoires"], 1)

    def test_audit_cutoff_et_onze_non_construits_sur_plusieurs_instants(self):
        cs = compo(n=10) + [{**r, "collecte_le": "2026-10-30T19:01:00Z"} for r in compo() if r["joueur_id"] == "10"]
        self.assertEqual(auditer(cs, [cote("18:55"), cote("19:05")], AU)["matchs_apparies"], 0)
        r = auditer(compo(), [cote("18:55"), cote("19:05")], instant("2026-10-30T19:04:00Z"))
        self.assertEqual(r["matchs_apparies"], 0)

    def test_cli_entrees_absentes_schema_et_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = ["--dossier-externe", tmp, "--au", AU.isoformat()]
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                main(args)
            self.assertEqual(exc.exception.code, 2)
            for folder, rows in (("espn/compos", [{k: v for k, v in r.items() if k != "source"} for r in compo()]),
                                 ("cotes/espn", [cote("18:55"), cote("19:05")])):
                p = root / folder / "2026-10-30/1905.csv"
                p.parent.mkdir(parents=True)
                with p.open("w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=list(rows[0]))
                    w.writeheader()
                    w.writerows(rows)
            out = io.StringIO()
            with redirect_stdout(out):
                main(args)
            import json
            r = json.loads(out.getvalue())
            self.assertEqual(r["matchs_apparies"], 1)
            self.assertEqual(r["entrees"]["compos"]["source_legacy"], 22)
            self.assertIsNone(r["paires"][0]["publication_officielle_le"])
            self.assertEqual(r["paires"][0]["cotes_avant"], {"H": 2, "D": 3, "A": 4})
            p.write_text("bad,header\n1,2\n", encoding="utf-8")
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(args)


if __name__ == "__main__":
    unittest.main()
