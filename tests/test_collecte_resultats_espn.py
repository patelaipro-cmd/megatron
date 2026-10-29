"""Contrôles hors réseau : score final, identité, doublon et fuite temporelle."""
import csv
import importlib.util
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

FILE=Path(__file__).resolve().parent.parent/'scripts'/'collecte_resultats_espn.py'
sp=importlib.util.spec_from_file_location('collecte_resultats_espn',FILE)
cr=importlib.util.module_from_spec(sp)
sp.loader.exec_module(cr)
NOW=datetime(2026,10,29,20,0,tzinfo=timezone.utc)

def event(eid,home='Hull City',away='Everton',hs=2,as_=0,complete=True,when='2026-10-20T16:00Z'):
    return {'id':str(eid),'date':when,'status':{'type':{'completed':complete,'name':'STATUS_FINAL' if complete else 'STATUS_IN_PROGRESS'}},
        'competitions':[{'competitors':[{'homeAway':'home','team':{'displayName':home},'score':str(hs)},
                                       {'homeAway':'away','team':{'displayName':away},'score':str(as_)}]}]}

class Results(unittest.TestCase):
    def setUp(self):
        self.d=tempfile.TemporaryDirectory()
        self.base=Path(self.d.name)/'base.csv'
        self.complement=Path(self.d.name)/'complement.csv'
        with self.base.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=cr.COLUMNS)
            w.writeheader()
            w.writerow(dict(zip(cr.COLUMNS,['E0','2026-09-20','15:00:00','Hull City','Everton',1,1,'D']+['']*7)))
        with self.complement.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=cr.COLUMNS)
            w.writeheader()
        self.d0=date(2026,10,20)
    def tearDown(self): self.d.cleanup()
    def call(self,events,aliases=None):
        return cr.collect(self.d0,self.d0,self.base,self.complement,aliases or {},
            lambda url:{'events':events},NOW,{'E0':'eng.1'})

    def test_resultat_reel_non_fusionne(self):
        rows,report,rejects=self.call([event(1)])
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]['FTHome'],rows[0]['FTAway'],rows[0]['FTResult']),(2,0,'H'))
        self.assertEqual(rows[0]['verdict'],'A_VERIFIER_MULTISOURCE')
        self.assertEqual(rejects,[])

    def test_jamais_de_match_non_termine_ni_futur(self):
        rows,report,rejects=self.call([event(1,complete=False),event(2,when='2026-10-29T21:00Z')])
        self.assertEqual(rows,[])
        self.assertEqual(rejects,[])
        self.assertEqual(report['compteurs']['not_completed'],2)

    def test_equipes_inconnues_en_quarantaine(self):
        rows,report,rejects=self.call([event(1,home='Hulll City')])
        self.assertEqual(rows,[])
        self.assertEqual(len(rejects),1)
        self.assertIn('inconnu/ambigu',rejects[0]['raison'])

    def test_alias_explicite(self):
        rows,report,rejects=self.call([event(1,home='Hulll City')],{'Hulll City':'Hull City'})
        self.assertEqual(len(rows),1)

    def test_resultat_deja_connu_non_duplique(self):
        rows,report,rejects=self.call([event(1,hs=1,as_=1,when='2026-09-20T15:00Z')])
        self.assertEqual(rows,[])
        self.assertEqual(rejects,[])  # hors fenêtre 20 octobre, volontairement ignoré

    def test_surcharges_meme_match_en_conflit(self):
        rows,report,rejects=self.call([event(1),event(2,hs=1)])
        self.assertEqual(len(rows),1)
        self.assertEqual(len(rejects),1)
        self.assertIn('CONFLIT_SCORE',rejects[0]['raison'])

    def test_deux_messages_meme_id_pas_double_compte(self):
        rows,_,rejects=self.call([event(1),event(1)])
        self.assertEqual((len(rows),len(rejects)),(1,0))

    def test_score_invalide_refuse(self):
        rows,_,rejects=self.call([event(1,hs='')])
        self.assertEqual(rows,[])
        self.assertEqual(len(rejects),1)

if __name__=='__main__':unittest.main()
