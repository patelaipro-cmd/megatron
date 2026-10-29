from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from megatron import contexte_favori as am, suivi
from megatron.agents import StatsAgent
from megatron.store import MemoryStore, parse_dt

AT = '2099-01-01T10:00:00Z'
KO = '2099-01-01T12:00:00Z'


def template():
    return am.modele('FICTIF:angles', 'Alpha FC', 'Beta FC', 'H', KO)


def source(famille='fictive'):
    return {'url': f'https://{famille}.example.invalid/preuve', 'famille': famille,
            'publie_le': '2099-01-01T08:00:00Z', 'collecte_le': '2099-01-01T09:00:00Z'}


def complete():
    d = template()
    for a in d['angles']:
        a.update(etat='documente', constat='CONSTAT FICTIF POUR TEST', mecanisme='MÉCANISME FICTIF POUR TEST',
                 effets=['nul'], sources=[source()], informations_manquantes=[])
    for period, e in d['comparateur_h2h'].items():
        e['axes'] = dict.fromkeys(am.AXES_H2H, 'OBSERVATION FICTIVE POUR TEST')
        if period != 'actuel':
            e.update(date='2098-01-01' if period == 'ancien' else '2098-06-01', score=[2, 0], home='Alpha FC', away='Beta FC')
    for scenario in d['scenarios'].values():
        scenario.update(hypothese='HYPOTHÈSE FICTIVE POUR TEST', angles=['style_genant'])
    return d


class AnglesMortsTests(unittest.TestCase):
    def test_modele_incomplet_sans_faits_inventes(self):
        d = template(); r = am.verifier(d, at=AT)
        self.assertTrue(r['ok']); self.assertEqual(r['statut'], 'INCOMPLET')
        self.assertEqual(r['angles_documentes'], 0)
        self.assertFalse(r['ajustement_probabilites'])
        self.assertTrue(all(a['sources'] == [] and a['constat'] == '' for a in d['angles']))

    def test_structure_complete_ne_prouve_pas_sources(self):
        r = am.verifier(complete(), at=AT)
        self.assertTrue(r['ok'], r['erreurs'])
        self.assertEqual(r['statut'], 'DOCUMENTE_NON_VERIFIE')
        self.assertEqual(r['manquants'], [])

    def test_documente_sans_source_refuse(self):
        d = complete(); d['angles'][0]['sources'] = []
        self.assertFalse(am.verifier(d, at=AT)['ok'])

    def test_source_future_ou_sans_fuseau_refusee(self):
        for value in ('2099-01-01T11:00:00Z', '2099-01-01T09:00:00'):
            d = complete(); d['angles'][0]['sources'][0]['collecte_le'] = value
            self.assertFalse(am.verifier(d, at=AT)['ok'])

    def test_absences_exigent_trois_familles_pas_trois_liens(self):
        d = complete(); a=d['angles'][4]; a['categorie_preuve']='absences'
        a['sources']=[source('A'), source('A'), source('A')]
        self.assertEqual(am.verifier(d, at=AT)['statut'], 'INCOMPLET')
        a['sources']=[source('A'), source('B'), source('C')]
        self.assertEqual(am.verifier(d, at=AT)['statut'], 'DOCUMENTE_NON_VERIFIE')

    def test_h2h_pas_de_score_actuel_ni_chronologie_inversee(self):
        d=complete(); d['comparateur_h2h']['actuel']['score']=[1,0]
        self.assertFalse(am.verifier(d, at=AT)['ok'])
        d=complete(); d['comparateur_h2h']['ancien']['date']='2098-12-01'
        self.assertFalse(am.verifier(d, at=AT)['ok'])

    def test_trois_scenarios_quatre_axes_et_angles_sans_doublon(self):
        d=template(); d['angles'][0]=deepcopy(d['angles'][1])
        self.assertFalse(am.verifier(d, at=AT)['ok'])
        d=complete(); del d['scenarios']['nul']
        self.assertFalse(am.verifier(d, at=AT)['ok'])
        d=complete(); del d['comparateur_h2h']['dernier']['axes']['construction_ecart']
        self.assertFalse(am.verifier(d, at=AT)['ok'])

    def test_objets_incorrects_refuses(self):
        for d in (None, [], 1, {'version':am.VERSION}):
            self.assertFalse(am.verifier(d, at=AT)['ok'])

    def test_contexte_autre_match_refuse_avant_agent_et_sans_ecriture(self):
        with tempfile.TemporaryDirectory() as tmp:
            st=MemoryStore(tmp); d=template(); d['match_id']='autre'
            with mock.patch('megatron.suivi.fuse') as fuse, self.assertRaises(ValueError):
                suivi.prevoir(st, {'match_id':'FICTIF:angles','xg_home':1.5,'xg_away':.9},KO,
                              agents=[StatsAgent()],now=parse_dt(AT),contexte_favori=d)
            fuse.assert_not_called(); self.assertEqual(st.entries('performances'), [])

    def test_trace_contexte_sans_changer_probabilites(self):
        task={'match_id':'FICTIF:angles','home':'Alpha FC','away':'Beta FC','xg_home':1.5,'xg_away':.9}
        with tempfile.TemporaryDirectory() as tmp:
            a,b=MemoryStore(Path(tmp)/'a'), MemoryStore(Path(tmp)/'b')
            plain=suivi.prevoir(a,task,KO,agents=[StatsAgent()],now=parse_dt(AT))
            contextual=suivi.prevoir(b,task,KO,agents=[StatsAgent()],now=parse_dt(AT),contexte_favori=template())
            self.assertEqual(plain['probs'],contextual['probs'])
            self.assertEqual(contextual['contexte_favori_statut'],'INCOMPLET')
            trace=b.active('performances','fusion:FICTIF:angles')[0].value
            self.assertEqual(trace['contexte_favori']['donnees'],template())

    def test_cli_et_fichier_illisible(self):
        from megatron.__main__ import main
        with mock.patch('builtins.print') as printer:
            rc=main(['angles-morts','modele','--match-id','FICTIF:angles','--home','Alpha FC',
                     '--away','Beta FC','--favori','H','--coup-envoi',KO])
            self.assertEqual(rc,0)
            self.assertEqual(json.loads(printer.call_args[0][0])['version'],am.VERSION)
            self.assertEqual(main(['angles-morts','verifier','--fichier','/fichier/inexistant']),2)

    def test_orientation_h2h_et_sites_absences(self):
        d=complete(); d['comparateur_h2h']['dernier']['home']=None
        self.assertEqual(am.verifier(d,at=AT)['statut'],'INCOMPLET')
        d=complete(); a=d['angles'][4]; a['categorie_preuve']='absences'
        a['sources']=[source('A'),source('B'),source('C')]
        for s in a['sources']: s['url']='https://unique.example.invalid/preuve'
        self.assertEqual(am.verifier(d,at=AT)['statut'],'INCOMPLET')
