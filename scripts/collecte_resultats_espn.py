"""Collecte de résultats ESPN terminés pour audit, sans modification de data/ ni modèle.

Exemple (depuis la racine du dépôt) :
 python scripts/collecte_resultats_espn.py --depuis 2026-09-21 --jusqua 2026-10-29 \
   --base data/matches_top5_2000-2026.csv \
   --complement data/complement_openfootball_2026-27.csv \
   --sortie reports/resultats_espn_a_verifier.csv --rapport reports/audit_espn.json

Ne jamais injecter cette sortie dans data.CURRENT sans vérification multisource et
validation des alias d'équipes et du référentiel des dates. Aucune cote n'est inventée.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import time
import unicodedata
import urllib.request
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

ENDPOINT = 'https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard?dates={jour}'
LEAGUES = {'E0':'eng.1','F1':'fra.1','D1':'ger.1','SP1':'esp.1','I1':'ita.1'}
COLUMNS = ['Division','MatchDate','MatchTime','HomeTeam','AwayTeam','FTHome','FTAway','FTResult',
           'OddHome','OddDraw','OddAway','HomeShots','AwayShots','HomeTarget','AwayTarget']
META = ['espn_event_id','source_url','kickoff_utc','statut','verdict']


def _dt(s):
    if not s:
        raise ValueError('date du match absente')
    return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc)


def _score(v):
    if isinstance(v, dict):
        v = v.get('value')
    if isinstance(v, bool) or v is None:
        raise ValueError('score absent')
    n = float(v)
    if not n.is_integer() or n < 0:
        raise ValueError('score non entier ou négatif')
    return int(n)


def _normalized(s):
    s = unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().casefold()
    s = re.sub(r'\b(fc|afc|cf|sc|ac|sv|club|football|calcio|the|city|town)\b',' ',s)
    return ' '.join(re.findall(r'[a-z0-9]+',s))


def _names_from_existing(paths):
    by_div = {}
    existing = {}
    for path in paths:
        if path is None or not Path(path).exists():
            continue
        with Path(path).open(newline='',encoding='utf-8') as f:
            for r in csv.DictReader(f):
                division = r['Division']
                by_div.setdefault(division,set()).update((r['HomeTeam'],r['AwayTeam']))
                key = (division,r['MatchDate'],r['HomeTeam'],r['AwayTeam'])
                score = (str(r['FTHome']),str(r['FTAway']))
                if key in existing and existing[key] != score:
                    raise ValueError(f'conflit dans les fichiers existants : {key}')
                existing[key] = score
    return by_div,existing


def resolve(name, candidates, aliases):
    """Rapprochement strict : pas d'approximation en cas d'ambiguïté."""
    if name in candidates:
        return name
    if name in aliases:
        candidate=aliases[name]
        if candidate in candidates:
            return candidate
        raise ValueError(f'alias vers une équipe inconnue : {name} -> {candidate}')
    norm = _normalized(name)
    matches = [c for c in candidates if _normalized(c) == norm]
    if len(matches) == 1 and norm:
        return matches[0]
    raise ValueError(f'nom inconnu/ambigu : {name!r}; candidats={matches!r}')


def decode_event(event, slug, fetched_at):
    """Un score n'est accepté que si la rencontre est officiellement terminée."""
    comp = (event.get('competitions') or [{}])[0]
    status = comp.get('status') or event.get('status') or {}
    st = status.get('type') or {}
    if not (st.get('completed') is True and st.get('name') in ('STATUS_FINAL','STATUS_FULL_TIME')):
        return None
    kickoff = _dt(event.get('date') or comp.get('date'))
    if kickoff >= fetched_at:
        return None
    competitors = comp.get('competitors') or []
    sides = {c.get('homeAway'):c for c in competitors}
    if set(sides) != {'home','away'}:
        raise ValueError('domicile/extérieur incorrect ou manquant')
    home, away = sides['home'], sides['away']
    return {'id':str(event.get('id','')), 'kickoff_utc':kickoff.isoformat(),
            'day':kickoff.date().isoformat(), 'time':kickoff.strftime('%H:%M:%S'),
            'home':home.get('team',{}).get('displayName') or home.get('team',{}).get('name'),
            'away':away.get('team',{}).get('displayName') or away.get('team',{}).get('name'),
            'hg':_score(home.get('score')),'ag':_score(away.get('score')),
            'status':st.get('name'), 'url':ENDPOINT.format(slug=slug,jour=kickoff.strftime('%Y%m%d'))}


def collect(depuis, jusqua, base, complement, aliases, fetch_json, now=None, slugs=None):
    """Ne modifie aucune donnée; renvoie (lignes, rapport, rejets)."""
    if depuis > jusqua:
        raise ValueError('intervalle inversé')
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('now doit inclure son fuseau horaire')
    now=now.astimezone(timezone.utc)
    teams, existing=_names_from_existing((base,complement))
    if not teams:
        raise ValueError('aucun historique de référence : arrêt')
    slugs=slugs or LEAGUES
    rows, rejects, events={},[],set()
    counters=Counter()
    d=depuis
    from datetime import timedelta
    while d<=min(jusqua,now.date()):
        for division,slug in slugs.items():
            url=ENDPOINT.format(slug=slug,jour=d.strftime('%Y%m%d'))
            try:
                data=fetch_json(url)
                candidates=data.get('events',[])
                if not isinstance(candidates,list):
                    raise ValueError('events doit être une liste')
            except Exception as exc:
                rejects.append({'division':division,'jour':d.isoformat(),'event_id':'',
                                'raison':f'API_INDISPONIBLE:{type(exc).__name__}:{exc}','source_url':url})
                counters['api_errors']+=1
                continue
            for ev in candidates:
                counters['events_seen']+=1
                try:
                    x=decode_event(ev,slug,now)
                    if x is None:
                        counters['not_completed']+=1
                        continue
                    if not (depuis<=date.fromisoformat(x['day'])<=jusqua):
                        continue
                    event_key=(slug,x['id'])
                    if event_key in events:
                        continue
                    events.add(event_key)
                    home=resolve(x['home'],teams.get(division,set()),aliases)
                    away=resolve(x['away'],teams.get(division,set()),aliases)
                    if home==away:
                        raise ValueError('même club à domicile et extérieur')
                    key=(division,x['day'],home,away)
                    if key in existing:
                        if existing[key] != (str(x['hg']),str(x['ag'])):
                            raise ValueError(f'CONFLIT_SCORE:historique={existing[key]},ESPN={(x["hg"],x["ag"])}')
                        counters['already_known']+=1
                        continue
                    ft='H' if x['hg']>x['ag'] else 'A' if x['ag']>x['hg'] else 'D'
                    row=dict(zip(COLUMNS,[division,x['day'],x['time'],home,away,x['hg'],x['ag'],ft]+['']*7))
                    row.update(dict(zip(META,[x['id'],x['url'],x['kickoff_utc'],x['status'],'A_VERIFIER_MULTISOURCE'])))
                    if key in rows and (rows[key]['FTHome'],rows[key]['FTAway']) != (x['hg'],x['ag']):
                        raise ValueError('CONFLIT_SCORE entre événements ESPN')
                    rows[key]=row
                except Exception as exc:
                    rejects.append({'division':division,'jour':d.isoformat(),'event_id':str(ev.get('id','')),
                                    'raison':str(exc),'source_url':url})
                    counters['event_rejected']+=1
        d+=timedelta(days=1)
    result=sorted(rows.values(),key=lambda r:(r['MatchDate'],r['MatchTime'],r['Division'],r['HomeTeam']))
    counters['new_review_rows']=len(result)
    counters['rejected_rows']=len(rejects)
    report={'source':'ESPN scoreboard API (famille unique)', 'premier_jour':depuis.isoformat(),
            'dernier_jour':jusqua.isoformat(), 'capture_utc':now.isoformat(),
            'statut':'A_VERIFIER_MULTISOURCE', 'compteurs':dict(counters),
            'note':'NE PAS fusionner ni activer data.CURRENT avant rapprochement indépendant.',
            'ligues':slugs}
    return result,report,rejects


def fetch_json(url):
    request=urllib.request.Request(url,headers={'User-Agent':'MEGATRON-data-audit/1.0','Accept':'application/json'})
    with urllib.request.urlopen(request,timeout=25) as f:
        return json.load(f)


def write_csv(path,fields,rows):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with open(path,'w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--depuis',type=date.fromisoformat,default=date(2026,9,21))
    p.add_argument('--jusqua',type=date.fromisoformat,default=datetime.now(timezone.utc).date())
    p.add_argument('--base',type=Path,default=Path('data/matches_top5_2000-2026.csv'))
    p.add_argument('--complement',type=Path,default=Path('data/complement_openfootball_2026-27.csv'))
    p.add_argument('--alias',type=Path,default=None,help='JSON: noms ESPN -> noms de data/')
    p.add_argument('--sortie',type=Path,default=Path('reports/resultats_espn_a_verifier.csv'))
    p.add_argument('--rapport',type=Path,default=Path('reports/audit_resultats_espn.json'))
    p.add_argument('--rejets',type=Path,default=Path('reports/rejets_resultats_espn.csv'))
    opts=p.parse_args(argv)
    aliases=json.loads(opts.alias.read_text(encoding='utf-8')) if opts.alias else {}
    rows,report,rejects=collect(opts.depuis,opts.jusqua,opts.base,opts.complement,aliases,fetch_json)
    write_csv(opts.sortie,COLUMNS+META,rows)
    write_csv(opts.rejets,['division','jour','event_id','raison','source_url'],rejects)
    opts.rapport.parent.mkdir(parents=True,exist_ok=True)
    opts.rapport.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    if not rows:
        report["alerte"] = "AUCUN_RESULTAT_NOUVEAU : vérifier la période, la source et les alias"
        opts.rapport.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    # Pas de promotion possible si aucune rencontre, source en échec ou événement non résolu.
    return 2 if rejects or not rows else 0


if __name__=='__main__':
    raise SystemExit(main())
