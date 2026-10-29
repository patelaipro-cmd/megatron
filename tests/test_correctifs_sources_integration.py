"""À exécuter dans le vrai dépôt, APRÈS application du correctif."""
import unittest
from megatron import wininvest, externe
from scripts import collecte_externe

class TestsSourcesReelles(unittest.TestCase):
    def test_codes_fpl_collectes(self):
        f=wininvest._statut_absence_fpl
        self.assertEqual(f({'statut':'blesse'}),'blesse')
        self.assertEqual(f({'statut':'suspendu'}),'suspendu')
        self.assertEqual(f({'statut':'incertain'}),'incertain')
        self.assertEqual(f({'statut':'indisponible'}),'incertain')
        self.assertIsNone(f({'statut':'indisponible','news':'Has joined Tottenham permanently'}))

    def test_postes_espn_rassemblage(self):
        data={'rosters':[{'team':{'displayName':'Equipe fictive'},'formation':'4-4-2',
             'roster':[{'starter':True,'athlete':{'displayName':'A','position':{'abbreviation':'DF'}},'position':{'abbreviation':'SUB'}},
                       {'starter':False,'athlete':{'displayName':'B','position':{'abbreviation':'MF'}},'position':{'abbreviation':'SUB'}}]}]}
        lines=collecte_externe.lignes_compos_espn({'event_id':'1'},data,'2026-10-29T19:17:00Z')
        self.assertEqual([(x['poste'],x['statut']) for x in lines],[('DF','titulaire'),('MF','remplacant')])
        self.assertEqual(externe.poste_simple('DF'),'D')
        self.assertEqual(externe.poste_simple('MF'),'M')
        self.assertEqual(externe.poste_simple('FW'),'F')

if __name__=='__main__':unittest.main()
