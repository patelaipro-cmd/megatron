"""Test de transfert par fichier, uniquement sur des matchs fictifs. Aucun LLM."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

BASE = Path(__file__).resolve().parent
COMMIT = '308f65361b1880e88fb93c6dc2367d25b1c58313'

def digest(b):
    return hashlib.sha256(b).hexdigest()

def hashes(root):
    return {str(p.relative_to(root)): digest(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}

def write(name, obj):
    (BASE / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

def require(ok, message):
    if not ok:
        raise ValueError(message)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True, help='chemin du dépôt MEGATRON')
    ap.add_argument('--etape', choices=['claude', 'retour'], required=True)
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    require(BASE != repo and not BASE.is_relative_to(repo / 'memoire'), 'Extraire hors de la mémoire réelle')
    git = lambda *a: subprocess.check_output(['git', '-C', str(repo), *a], text=True).strip()
    require(subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', COMMIT, 'HEAD']).returncode == 0, 'Base du relais absente : ne pas forcer')
    require(not git('diff', COMMIT, 'HEAD', '--', 'megatron'), 'Cœur Python différent de la base : réexaminer le protocole')
    require(not git('status', '--porcelain', '--untracked-files=no'), 'Modifications suivies présentes : utiliser une copie propre')
    # Bloquer toute connexion réseau dans ce processus, même en présence de clés locales.
    import socket
    def blocked(*a, **kw):
        raise RuntimeError('Réseau interdit pendant ce test de relais')
    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    socket.create_connection = blocked
    real_before = hashes(repo / 'memoire')
    sys.path.insert(0, str(repo))
    from megatron import checkpoint, suivi, synchro
    from megatron.agents import StatsAgent
    from megatron.ledger import Ledger
    from megatron.store import DOMAINS, MemoryStore, parse_dt
    require(synchro.verifier(repo / 'memoire', 'origin/main')['ok'], 'Mémoire réelle refusée par synchro verifier')
    require(synchro.verifier(BASE / 'memoire_fictive', 'origin/main')['ok'], 'Mémoire fictive refusée par synchro verifier')
    manifest = json.loads((BASE / 'depart_codex.json').read_text(encoding='utf-8'))
    require(manifest['commit'] == COMMIT, 'Commit initial altéré')
    require(digest((BASE / 'relais.py').read_bytes()) == manifest['script_sha256'], 'Script différent du départ')
    memory = BASE / 'memoire_fictive'
    st = MemoryStore(memory)
    for name, info in manifest['prefixes_jsonl'].items():
        current = (memory / name).read_bytes()
        require(digest(current[:info['octets']]) == info['sha256'], 'Historique initial modifié : ' + name)
    for domain in DOMAINS:
        require(not st.contradictions(domain), 'Contradiction dans ' + domain)
    def forecasts():
        return {e.id: e.__dict__ for e in st.entries('performances') if e.key.startswith('pred:')}
    require(forecasts() == manifest['previsions'], 'Prévisions initiales altérées ou ajoutées')
    checks = {'historique_initial_preserve': True, 'previsions_identiques': True}
    ko = parse_dt(manifest['coup_envoi_fictif'])
    if args.etape == 'claude':
        require(not (BASE / 'rapport_claude.json').exists(), 'Étape Claude déjà exécutée : utiliser le paquet initial')
        for name, expected in manifest['fichiers_depart'].items():
            require(digest((memory / name).read_bytes()) == expected, 'État de départ différent : ' + name)
        ck = checkpoint.load(st)
        require(ck['id'] == manifest['checkpoint_initial'], 'Checkpoint initial différent')
        checks['checkpoint_repris'] = True
        before = hashes(memory)
        try:
            suivi.prevoir(st, manifest['taches'][0], ko, agents=[StatsAgent()], now=ko - __import__('datetime').timedelta(hours=3))
        except ValueError:
            checks['doublon_refuse_sans_ecriture'] = hashes(memory) == before
        else:
            checks['doublon_refuse_sans_ecriture'] = False
        require(checks['doublon_refuse_sans_ecriture'], 'Doublon non refusé proprement')
        for task, score in zip(manifest['taches'], ['2-0', '1-1', '0-3']):
            suivi.resultat(st, task['match_id'], score, source='simulation-relais-fichier:etape-claude',
                           observed_at=ko + __import__('datetime').timedelta(hours=2))
        st.record('travail', 'relais:fictif:etape-claude', 'Résultats fictifs ajoutés ; détenteur suivant Codex', source='relais.py', status='declare')
        new_ck = checkpoint.save(st, resume='TEST FICTIF : étape Claude terminée, relais vers Codex', prochaines_actions=['Vérifier le paquet retourné dans Codex'])
        checks['checkpoint_transmis'] = checkpoint.load(MemoryStore(memory))['id'] == new_ck['id']
    else:
        report = json.loads((BASE / 'rapport_claude.json').read_text(encoding='utf-8'))
        require(report['commit'] == COMMIT and report['succes'], 'Rapport Claude absent ou en échec')
        require(report['empreintes_retour'] == hashes(memory), 'Fichiers différents du rapport de retour')
        checks['checkpoint_repris'] = checkpoint.load(st)['id'] == report['checkpoint_retour']
    checks['previsions_identiques'] = forecasts() == manifest['previsions']
    summary = suivi.bilan(st, now=ko + __import__('datetime').timedelta(days=1))
    checks['trois_matchs_resolus'] = summary['communs']['n'] == 3 and not summary['resultats_a_saisir']
    checks['memoire_reelle_inchangee'] = hashes(repo / 'memoire') == real_before
    require(all(checks.values()), 'Échec du relais : ' + repr(checks))
    out = {'etape': args.etape, 'commit': COMMIT, 'head_execution': git('rev-parse', 'HEAD'), 'type': 'relais_git_fictif',
           'checks': checks, 'checkpoint_retour': checkpoint.load(st)['id'], 'bilan': summary,
           'empreintes_retour': hashes(memory), 'succes': True,
           'limite': 'Le champ étape est déclaratif ; ce rapport seul ne prouve pas quelle plateforme a exécuté le script.'}
    write('rapport_' + ('claude' if args.etape == 'claude' else 'retour_codex') + '.json', out)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        print('REFUS : ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
