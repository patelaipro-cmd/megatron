"""WININVEST / SYNDICATE : absences, niveaux de victoire, décision, contrôles T-30 / T-5, anti-fuite.

Toutes les données sont fictives (historique synthétique, collecte externe écrite en dossier temporaire).
"""
import csv
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from megatron import absences, controles, data, marges, syndicate, systeme, wininvest
from megatron.ledger import DOMAIN, Ledger, TemporalLeakError
from megatron.store import MemoryStore


def ecrire(dossier, source, quand, lignes):
    f = Path(dossier) / source / quand[:10] / (quand[11:13] + quand[14:16] + ".csv")
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=list(lignes[0]))
        w.writeheader()
        w.writerows(lignes)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.csv = root / "historique.csv"
        last = systeme.synthetic_history(self.csv)
        self.history = data.load(self.csv)
        self.ko = datetime(last.year, last.month, last.day, 15, tzinfo=timezone.utc) + timedelta(days=3)
        self.ext = root / "externe"
        self.store = MemoryStore(root / "memoire")
        self.home, self.away = "Alpha FC", "Zeta Rovers"

    def tearDown(self):
        self.tmp.cleanup()

    def blessure(self, quand, equipe, joueur, type_="Missing Fixture"):
        return {"collecte_le": quand, "fixture_id": "1", "coup_envoi": self.ko.isoformat(), "ligue_id": "0",
                "ligue": "Fictive", "pays": "X", "equipe": equipe, "joueur": joueur, "joueur_id": "1",
                "type": type_, "motif": "Fictif"}

    def compo(self, quand, equipe, titulaires):
        return [{"collecte_le": quand, "fixture_id": "1", "coup_envoi": self.ko.isoformat(), "ligue_id": "0",
                 "ligue": "Fictive", "equipe": equipe, "formation": "4-3-3", "joueur": j, "joueur_id": str(i),
                 "poste": "F", "statut": "titulaire"} for i, j in enumerate(titulaires)]

    def evaluer(self, at, **kw):
        return syndicate.evaluer(systeme.DIVISION, self.home, self.away, self.ko, at=at, history=self.history, **kw)


class TestAbsences(unittest.TestCase):
    def test_absence_importante_pese_plus(self):
        cle = absences.Absent("Buteur", "F", part_minutes=0.95, part_offensive=0.35, remplacant_niveau=0.3)
        marginal = absences.Absent("Remplacant", "F", part_minutes=0.1, part_offensive=0.02, remplacant_niveau=0.9)
        a, b = absences.evaluer_equipe([cle]), absences.evaluer_equipe([marginal])
        self.assertGreater(a["indice_offensif"], 5 * b["indice_offensif"])
        self.assertEqual(absences.evaluer_equipe([])["indice_offensif"], 0.0)

    def test_remplacant_et_incertitude_reduisent_la_perte(self):
        base = dict(joueur="X", poste="D", part_minutes=1.0, part_offensive=0.0)
        pertes = [absences.evaluer_joueur(absences.Absent(**base, remplacant_niveau=r))["perte"] for r in (0.0, 0.5, 1.0)]
        self.assertEqual(pertes, sorted(pertes, reverse=True))
        self.assertEqual(pertes[-1], 0.0)
        incertain = absences.evaluer_joueur(absences.Absent(**base, remplacant_niveau=0.0, statut="incertain"))["perte"]
        self.assertAlmostEqual(incertain, pertes[0] / 2)

    def test_absences_simultanees_meme_ligne(self):
        d = [absences.Absent(f"D{i}", "D", part_minutes=0.9, remplacant_niveau=0.4) for i in range(2)]
        seul = absences.evaluer_equipe(d[:1])["lignes"]["D"]
        deux = absences.evaluer_equipe(d)["lignes"]["D"]
        cumul_simple = 1 - (1 - seul) ** 2
        self.assertGreater(deux, cumul_simple)  # désorganisation : plus que le cumul indépendant
        self.assertLessEqual(deux, 1.0)

    def test_donnees_manquantes_signalees_et_valeurs_invalides_refusees(self):
        r = absences.evaluer_equipe([absences.Absent("Inconnu", None)])
        self.assertIn("Inconnu : poste", r["donnees_manquantes"])
        self.assertIn("Inconnu : part_minutes", r["donnees_manquantes"])
        with self.assertRaises(ValueError):
            absences.evaluer_joueur(absences.Absent("X", "F", part_minutes=1.5))
        with self.assertRaises(ValueError):
            absences.evaluer_joueur(absences.Absent("X", "Z"))

    def test_contradictions(self):
        c = absences.consolider([{"joueur": "A", "statut": "absent", "source": "s1"},
                                 {"joueur": "A", "statut": "incertain", "source": "s2"},
                                 {"joueur": "B", "statut": "absent", "source": "s1"}], titulaires_confirmes={"B"})
        self.assertEqual([a["joueur"] for a in c["absents"]], ["A"])
        self.assertEqual(c["absents"][0]["statut"], "incertain")
        self.assertEqual(len(c["contradictions"]), 2)

    def test_aucun_effet_sans_coefficient_valide(self):
        eq = absences.evaluer_equipe([absences.Absent("Buteur", "F", part_minutes=1, part_offensive=0.4, remplacant_niveau=0)])
        nul = absences.evaluer_equipe([])
        r = absences.ajuster_intensites(1.8, 0.9, eq, nul)
        self.assertEqual((r["lam_equipe"], r["lam_adverse"], r["ajuste"]), (1.8, 0.9, False))
        r2 = absences.ajuster_intensites(1.8, 0.9, eq, nul, alpha_offensif=0.3)
        self.assertLess(r2["lam_equipe"], 1.8)
        self.assertEqual(r2["statut"], "EXPERIMENTAL_NON_VALIDE")


class TestNiveaux(unittest.TestCase):
    def test_recalibration_exp012_emboitee_et_brut_garde(self):
        n = syndicate.niveaux(1.9, 0.8)
        self.assertEqual(n["statut"], "RECALIBRE_EXP-012")
        p, b = n["probabilites"], n["brut"]
        self.assertGreaterEqual(p["victoire_simple"], p["victoire_par_2_ou_plus"])
        self.assertGreaterEqual(p["victoire_par_2_ou_plus"], p["victoire_par_3_ou_plus"])
        self.assertNotEqual(p, b)

    def test_victoire_simple_differente_de_victoire_large(self):
        n = syndicate.niveaux(2.2, 0.7)
        p = n["probabilites"]
        self.assertEqual(n["favori"], "H")
        self.assertGreater(p["victoire_simple"], p["victoire_par_2_ou_plus"])
        self.assertGreater(p["victoire_par_2_ou_plus"], p["victoire_par_3_ou_plus"])
        self.assertAlmostEqual(p["victoire_simple"] + n["risques"]["nul"] + n["risques"]["defaite"], 1, places=3)

    def test_marge_jamais_confondue_avec_total_de_buts(self):
        from megatron.marches import total_au_moins
        n = syndicate.niveaux(1.6, 1.4)
        self.assertNotAlmostEqual(n["probabilites"]["victoire_par_2_ou_plus"], total_au_moins(3.0, 2), places=2)
        self.assertEqual(marges.resoudre([2, 1], "H_MARGE_2PLUS"), "non")  # 3 buts, marge 1
        self.assertEqual(marges.resoudre([1, 4], "A_MARGE_3PLUS"), "oui")

    def test_favori_exterieur(self):
        self.assertEqual(syndicate.niveaux(0.8, 1.9)["favori"], "A")


class TestFicheEtDecision(Base):
    def test_fiche_huit_rubriques_sans_fuite(self):
        at = self.ko - timedelta(hours=3)
        f = wininvest.fiche(systeme.DIVISION, self.home, self.away, self.ko, at=at, history=self.history)
        self.assertEqual(set(f["rubriques"]), set(wininvest.RUBRIQUES))
        self.assertFalse(f["ajustement_probabilites"])
        futur = data.Match(systeme.DIVISION, self.ko.date(), self.ko, self.home, self.away, 0, 9, "A", None)
        f2 = wininvest.fiche(systeme.DIVISION, self.home, self.away, self.ko, at=at, history=self.history + [futur])
        self.assertEqual(f["rubriques"]["forme"], f2["rubriques"]["forme"])  # le score du jour même n'est pas lu
        self.assertEqual(f["intensites_v5"], f2["intensites_v5"])

    def test_analyse_apres_coup_envoi_refusee(self):
        with self.assertRaises(ValueError):
            wininvest.fiche(systeme.DIVISION, self.home, self.away, self.ko, at=self.ko, history=self.history)

    def test_historique_perime_donne_pass(self):
        ko = self.ko + timedelta(days=40)
        e = syndicate.evaluer(systeme.DIVISION, self.home, self.away, ko, at=ko - timedelta(hours=2), history=self.history)
        self.assertEqual(e["decision"]["decision"], "PASS")
        self.assertTrue(any("périmé" in b for b in e["decision"]["bloquants"]))

    def test_decision_jamais_activee_et_go_bloque_sans_calibration(self):
        e = self.evaluer(self.ko - timedelta(hours=2))
        self.assertFalse(e["decision"]["activation_automatique"])
        self.assertFalse(syndicate.ACTIVATION_AUTOMATIQUE)
        self.assertIn(e["decision"]["decision"], ("GO", "SECURE", "WATCH", "PASS"))
        from unittest import mock
        n = {"favori": "H", "statut": "EXPERIMENTAL_NON_CALIBRE",
             "probabilites": {"victoire_simple": 0.8, "victoire_par_2_ou_plus": 0.65, "victoire_par_3_ou_plus": 0.4}}
        fiche = e["fiche"]
        for t in (self.home, self.away):
            fiche["rubriques"]["compositions"]["equipes"][t]["confirmee"] = True
        fiche["rubriques_a_verifier"] = []
        ctx = {"ok": True, "statut": "DOCUMENTE_NON_VERIFIE"}
        d = syndicate.decider(n, fiche, ctx)
        self.assertEqual(d["decision"], "SECURE")
        self.assertTrue(any("GO bloqué" in r for r in d["raisons"]))
        d2 = syndicate.decider({**n, "statut": "RECALIBRE_EXP-012"}, fiche, ctx)
        self.assertEqual(d2["decision"], "SECURE")  # zone P(2+) >= 60 % non validée par EXP-012
        with mock.patch.object(syndicate, "ZONE_GO_VALIDEE", True):
            self.assertEqual(syndicate.decider({**n, "statut": "RECALIBRE_EXP-012"}, fiche, ctx)["decision"], "GO")

    def test_risque_favori_faible_donne_pass(self):
        e = syndicate.evaluer(systeme.DIVISION, "Delta Town", "Epsilon SC", self.ko, at=self.ko - timedelta(hours=2),
                              history=self.history)
        if e["niveaux"]["probabilites"]["victoire_simple"] < 0.5:
            self.assertEqual(e["decision"]["decision"], "PASS")
        self.assertIn("defaite", e["angles_morts"]["questions"])
        self.assertIn("nul", e["angles_morts"]["questions"])

    def test_absences_collectees_et_contradiction_a_t5(self):
        q = (self.ko - timedelta(hours=2)).isoformat()
        ecrire(self.ext, "apifootball/blessures", q, [self.blessure(q, self.home, "Buteur Fictif")])
        q2 = (self.ko - timedelta(minutes=10)).isoformat()
        ecrire(self.ext, "apifootball/compos", q2, self.compo(q2, self.home, ["Buteur Fictif", "Autre"]) +
               self.compo(q2, self.away, ["Z1"]))
        e = self.evaluer(self.ko - timedelta(minutes=5), dossier_externe=self.ext, moment="T-5")
        ab = e["fiche"]["rubriques"]["absences"]["equipes"][self.home]
        self.assertTrue(ab["contradictions"])  # annoncé absent mais titulaire confirmé
        self.assertEqual(ab["joueurs"], [])
        self.assertEqual(e["decision"]["decision"], "PASS")

    def test_statuts_fpl_reels_dans_la_fiche(self):
        # libellés écrits par scripts/collecte_externe.py (FPL_STATUT), news réelles du 29/10/2026
        q = (self.ko - timedelta(hours=2)).isoformat()
        def l(joueur, statut, news):
            return {"collecte_le": q, "joueur_id": "1", "joueur": joueur, "equipe": self.home, "statut": statut,
                    "chance_prochain_match": "", "chance_ce_match": "", "news": news, "news_ajoutee_le": ""}
        ecrire(self.ext, "fpl", q, [l("Blesse", "blesse", "Knee injury - Unknown return date"),
                                    l("Suspendu", "suspendu", "Suspended until 7 Nov"),
                                    l("Doute", "incertain", "Ankle injury - 75% chance of playing"),
                                    l("Parti", "indisponible", "Has joined Hamburger SV permanently"),
                                    l("Libre", "indisponible", "Has departed the club as a free agent."),
                                    l("Hors groupe", "indisponible", "Not included in squad.")])
        e = self.evaluer(self.ko - timedelta(hours=1), dossier_externe=self.ext)
        ab = e["fiche"]["rubriques"]["absences"]["equipes"][self.home]
        self.assertEqual({j["joueur"]: j["statut"] for j in ab["joueurs"]},
                         {"Blesse": "blesse", "Suspendu": "suspendu", "Doute": "incertain", "Hors groupe": "incertain"})
        self.assertEqual(e["niveaux"], self.evaluer(self.ko - timedelta(hours=1))["niveaux"])  # aucune probabilité modifiée


class TestControles(Base):
    def test_initial_t30_t5_conserve_et_detecte_les_changements(self):
        q = (self.ko - timedelta(hours=3)).isoformat()
        ecrire(self.ext, "apifootball/blessures", q, [self.blessure(q, self.away, "Defenseur Fictif")])
        t0 = self.ko - timedelta(hours=2)
        e0 = self.evaluer(t0, dossier_externe=self.ext)
        out0 = controles.enregistrer(self.store, "FICTIF:1", e0, "initial", now=t0)
        self.assertEqual(len(out0["enregistre_registre"]), 2)
        avant = [x.value for x in self.store.active(DOMAIN)]
        # nouvelle information : un absent de plus et la compo publiée
        q1 = (self.ko - timedelta(minutes=40)).isoformat()
        ecrire(self.ext, "apifootball/blessures", q1, [self.blessure(q1, self.away, "Defenseur Fictif"),
                                                      self.blessure(q1, self.home, "Milieu Fictif")])
        ecrire(self.ext, "apifootball/compos", q1, self.compo(q1, self.home, ["H1", "H2"]) + self.compo(q1, self.away, ["A1"]))
        t30 = self.ko - timedelta(minutes=30)
        out30 = controles.enregistrer(self.store, "FICTIF:1", self.evaluer(t30, dossier_externe=self.ext, moment="T-30"), "T-30", now=t30)
        self.assertTrue(any("nouveaux absents" in c for c in out30["changements"]))
        self.assertTrue(any("compo officielle publiée" in c for c in out30["changements"]))
        # compo modifiée entre T-30 et T-5
        q2 = (self.ko - timedelta(minutes=10)).isoformat()
        ecrire(self.ext, "apifootball/compos", q2, self.compo(q2, self.home, ["H1", "H3"]) + self.compo(q2, self.away, ["A1"]))
        t5 = self.ko - timedelta(minutes=5)
        out5 = controles.enregistrer(self.store, "FICTIF:1", self.evaluer(t5, dossier_externe=self.ext, moment="T-5"), "T-5", now=t5)
        self.assertIn(f"{self.home} : compo modifiée", out5["changements"])
        self.assertFalse(out5["activation_automatique"])
        # anciennes prévisions conservées, aucun doublon
        self.assertEqual([x.value for x in self.store.active(DOMAIN)], avant)
        self.assertEqual([e.value["moment"] for e in controles.historique(self.store, "FICTIF:1")], ["initial", "T-30", "T-5"])
        with self.assertRaises(ValueError):
            controles.enregistrer(self.store, "FICTIF:1", self.evaluer(t5, dossier_externe=self.ext), "T-5", now=t5)

    def test_fenetres_et_apres_coup_envoi(self):
        e = self.evaluer(self.ko - timedelta(hours=6))
        with self.assertRaises(ValueError):  # fenêtre de 5 h pas ouverte
            controles.enregistrer(self.store, "FICTIF:2", e, "initial", now=self.ko - timedelta(hours=6))
        e = self.evaluer(self.ko - timedelta(hours=1))
        with self.assertRaises(ValueError):  # T-30 hors de sa plage
            controles.enregistrer(self.store, "FICTIF:2", e, "T-30", now=self.ko - timedelta(hours=1))
        with self.assertRaises(ValueError):  # coup d'envoi passé
            controles.enregistrer(self.store, "FICTIF:2", e, "revision", now=self.ko + timedelta(minutes=1))
        with self.assertRaises(ValueError):  # pas de T-5 sans initial
            controles.enregistrer(self.store, "FICTIF:3", self.evaluer(self.ko - timedelta(minutes=5)), "T-5",
                                  now=self.ko - timedelta(minutes=5))
        with self.assertRaises(TemporalLeakError):
            Ledger(self.store).predict("FICTIF:2", self.ko, {"oui": .5, "non": .5}, model_version="x", source="t",
                                       recorded_at=self.ko + timedelta(minutes=1), market="H_MARGE_2PLUS")
        self.assertEqual(self.store.active(DOMAIN), [])

    def test_cli_evaluer_resume(self):
        import io
        from contextlib import redirect_stdout
        from unittest import mock
        from megatron.__main__ import main
        buf = io.StringIO()
        with mock.patch("megatron.wininvest.historique", return_value=self.history), redirect_stdout(buf):
            code = main(["syndicate", "evaluer", "--division", systeme.DIVISION, "--home", self.home, "--away", self.away,
                         "--coup-envoi", self.ko.isoformat(), "--au", (self.ko - timedelta(hours=1)).isoformat(), "--resume"])
        self.assertEqual(code, 0)
        self.assertIn("victoire_par_3_ou_plus", json.loads(buf.getvalue())["niveaux"]["probabilites"])


if __name__ == "__main__":
    unittest.main()
