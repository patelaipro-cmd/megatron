import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

from megatron import contexte_favori, externe
from megatron.__main__ import main

KO = '2099-01-01T15:00:00+00:00'
AT = '2099-01-01T14:30:00+00:00'


def ecrire(dossier, source, nom, lignes):
    f = Path(dossier) / source / '2099-01-01' / nom
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open('w', encoding='utf-8', newline='') as h:
        w = csv.DictWriter(h, fieldnames=list(lignes[0]))
        w.writeheader()
        w.writerows(lignes)


def blessure(collecte, equipe, joueur, ko=KO):
    return {'collecte_le': collecte, 'fixture_id': '11', 'coup_envoi': ko, 'ligue_id': '61', 'ligue': 'Ligue 1',
            'pays': 'France', 'equipe': equipe, 'joueur': joueur, 'joueur_id': '1', 'type': 'Missing Fixture',
            'motif': 'Knee Injury'}


def compo(collecte, equipe, joueur):
    return {'collecte_le': collecte, 'fixture_id': '11', 'coup_envoi': KO, 'ligue_id': '61', 'ligue': 'Ligue 1',
            'equipe': equipe, 'formation': '4-3-3', 'joueur': joueur, 'joueur_id': '2', 'poste': 'F', 'statut': 'titulaire'}


class TestExterne(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        ecrire(self.d, 'apifootball/blessures', '0600.csv', [blessure('2099-01-01T06:00:00+00:00', 'Alpha Externe', 'Ancien Fictif')])
        ecrire(self.d, 'apifootball/blessures', '1200.csv', [
            blessure('2099-01-01T12:00:00+00:00', 'Alpha Externe', 'Blesse Fictif'),
            blessure('2099-01-01T12:00:00+00:00', 'Alpha Externe', 'Autre Match', ko='2099-01-05T15:00:00+00:00')])
        ecrire(self.d, 'apifootball/blessures', '1800.csv', [blessure('2099-01-01T18:00:00+00:00', 'Alpha Externe', 'Apres Coup Fictif')])
        ecrire(self.d, 'apifootball/compos', '1400.csv', [compo('2099-01-01T14:00:00+00:00', 'Beta FC', 'Titulaire Fictif')])
        ecrire(self.d, 'espn/compos', '1420.csv', [{'collecte_le': '2099-01-01T14:20:00+00:00', 'event_id': '77', 'ligue': 'fra.1',
                                                   'division': 'F1', 'coup_envoi': '2099-01-01T15:00:00+00:00', 'equipe': 'Beta',
                                                   'formation': '4-4-2', 'joueur': 'Titulaire Espn', 'joueur_id': '3',
                                                   'poste': 'F', 'statut': 'titulaire'}])
        self.doc = contexte_favori.modele('FICTIF:externe', 'Alpha FC', 'Beta FC', 'H', KO)

    def tearDown(self):
        self.tmp.cleanup()

    def test_dernier_instantane_avant_analyse_et_meme_match(self):
        f = externe.faits(self.d, 'Alpha Externe', KO, at=AT)
        self.assertEqual([l['joueur'] for l in f['absences']], ['Blesse Fictif'])  # ni 06:00 (remplacé), ni 18:00 (après), ni autre match
        self.assertEqual(externe.faits(self.d, 'Alpha Externe', KO, at='2099-01-01T10:00:00+00:00')['absences'][0]['joueur'], 'Ancien Fictif')
        self.assertEqual(externe.faits(self.d, 'Beta FC', KO, at='2099-01-01T13:00:00+00:00')['compo'], [])  # compo pas encore collectée

    def test_jamais_apres_le_coup_envoi(self):
        f = externe.faits(self.d, 'Alpha Externe', KO, at='2099-01-02T00:00:00+00:00')
        self.assertEqual([l['joueur'] for l in f['absences']], ['Blesse Fictif'])

    def test_enrichir_grille_sans_toucher_aux_autres_angles(self):
        out = externe.enrichir(self.doc, self.d, at=AT, noms={'Alpha FC': 'Alpha Externe'})
        angle = next(a for a in out['angles'] if a['id'] == 'informations_manquantes')
        self.assertEqual(angle['etat'], 'a_verifier')
        self.assertIn('Blesse Fictif', angle['constat'])
        self.assertIn('Titulaire Fictif', angle['constat'])
        self.assertIn('Titulaire Espn', angle['constat'])
        self.assertEqual({s['famille'] for s in angle['sources']}, {'api-football', 'espn'})
        self.assertIn('https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/summary?event=77', [s['url'] for s in angle['sources']])
        self.assertEqual(self.doc['angles'], contexte_favori.modele('FICTIF:externe', 'Alpha FC', 'Beta FC', 'H', KO)['angles'])  # copie
        v = contexte_favori.verifier(out, at=AT)
        self.assertTrue(v['ok'], v['erreurs'])
        self.assertFalse(v['ajustement_probabilites'])
        self.assertTrue(any('trois sites' in m for m in v['manquants']))  # une seule famille : règle des 3 sources

    def test_nom_inconnu_signale(self):
        out = externe.enrichir(self.doc, self.d, at=AT)
        angle = next(a for a in out['angles'] if a['id'] == 'informations_manquantes')
        self.assertTrue(any('Alpha FC' in m for m in angle['informations_manquantes']))

    def test_cli(self):
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as h:
            json.dump(self.doc, h)
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(['angles-morts', 'externe', '--fichier', h.name, '--dossier-externe', str(self.d),
                         '--nom-home', 'Alpha Externe', '--au', AT])
        Path(h.name).unlink()
        self.assertEqual(code, 0)
        self.assertIn('Blesse Fictif', buf.getvalue())


class TestNoms(unittest.TestCase):
    def test_resolution(self):
        r = externe.resoudre
        self.assertEqual(r('Paris SG', {'Paris Saint Germain', 'Lens'}), ('Paris Saint Germain', 'alias'))
        self.assertEqual(r('Paris FC', {'Paris Saint Germain'})[0], None)  # jamais rapproché du PSG
        self.assertEqual(r('Mainz', {'FSV Mainz 05', 'SV Elversberg'}), ('FSV Mainz 05', 'normalise'))
        self.assertEqual(r('Hull', {'Hull City', 'Ipswich Town'}), ('Hull City', 'normalise'))
        self.assertEqual(r('Monchengladbach', {'Borussia Mönchengladbach'}), ('Borussia Mönchengladbach', 'inclusion'))
        self.assertEqual(r('Tottenham', {'Spurs', 'Arsenal'}), ('Spurs', 'alias'))
        self.assertTrue(r('Borussia', {'Borussia Dortmund', 'Borussia Mönchengladbach'})[1].startswith('ambigu'))
        self.assertEqual(r('Inconnu', {'Lens'}), (None, 'introuvable'))

    def test_alias_valides(self):
        alias = externe.charger_alias()
        self.assertTrue(alias and all(isinstance(v, list) and v for v in alias.values()))

    def test_faits_avec_nom_megatron(self):
        with tempfile.TemporaryDirectory() as d:
            ecrire(d, 'apifootball/blessures', '1200.csv', [blessure('2099-01-01T12:00:00+00:00', 'Paris Saint Germain', 'Blesse Fictif')])
            f = externe.faits(Path(d), 'Paris SG', KO, at=AT)
            self.assertEqual([l['joueur'] for l in f['absences']], ['Blesse Fictif'])
            self.assertEqual(f['noms']['apifootball/blessures'], {'nom': 'Paris Saint Germain', 'methode': 'alias'})


if __name__ == '__main__':
    unittest.main()
