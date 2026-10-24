# Shared loader for the playbook analysis: joins pb_extract.mjs output (C:/battlecode/cache/top2_playbooks/pb_<key>.jsonl) with the
# platform index (C:/battlecode/cache/t2/<key>/index.jsonl) -> one record per (study team, game) with S (study team) and O (opponent).
import json, os

KEYS = {'pbg': '38e6d8c4', 'ifish': '1890540d', 'pantheon': '547efb5b', 'coo': '1570a113', 'cm': 'ad5474c2', 'nyx': '6f7fd199'}
NAMES = {'pbg': 'prism best girl', 'ifish': 'Intercontinental Fish', 'pantheon': 'Pantheon', 'coo': 'conqueror_of_openai', 'cm': 'Claudus Maximus', 'nyx': 'Nyx'}
RANK = {'pbg': 1, 'ifish': 2, 'pantheon': 6, 'coo': 18, 'cm': 19, 'nyx': 31}
ORDER = ['pbg', 'ifish', 'pantheon', 'coo', 'cm', 'nyx']
CH = {0: 'Ryth', 1: 'Vesper', 2: 'Vendetta', 3: 'C&I', 4: 'Stellar', 5: 'Prism', 6: 'Marcella', 7: 'Willow', 8: 'Ren', 9: 'Varg', 10: 'Tavi', 11: 'HoR'}
BASE = 'C:/battlecode/cache/top2_playbooks'


def size_class(W, H):
    a = W * H
    return 'small' if a <= 1681 else ('medium' if a <= 3000 else 'large')


def load(key):
    idx = {}
    for l in open(f'C:/battlecode/cache/t2/{key}/index.jsonl', encoding='utf-8'):
        r = json.loads(l)
        idx[f"{r['map']}_{r['matchId'][:8]}"] = r
    out = []
    for l in open(f'{BASE}/pb_{key}.jsonl', encoding='utf-8'):
        g = json.loads(l)
        if 'err' in g:
            continue
        r = idx.get(g['file'])
        if r is None:
            continue
        me = [t for t in r['teams'] if t['teamId'].startswith(KEYS[key])][0]
        ot = [t for t in r['teams'] if not t['teamId'].startswith(KEYS[key])][0]
        s = 0 if me['side'] == 'a' else 1
        g['key'] = key
        g['s'] = s
        g['S'] = g['teams'][s]
        g['O'] = g['teams'][1 - s]
        g['win'] = me['result'] == 'win'
        g['opp'] = ot['name']
        g['oppId'] = ot['teamId']
        g['draftS'] = [CH[p] for p in me['draftPicks']]
        g['draftO'] = [CH[p] for p in ot['draftPicks']]
        g['n'] = len(me['draftPicks'])
        g['size'] = size_class(g['W'], g['H'])
        geo = g.get('geo') or {}
        g['obj'] = 'mono' if geo.get('mono') else ('golem' if geo.get('golem') else '')
        if geo.get('mono') and geo.get('golem'):
            g['obj'] = 'mono+golem'
        g['endReason'] = r.get('endReason')
        g['matchId'] = r['matchId']
        g['rolesS'] = [x for x in g['roles'] if x['t'] == s]
        g['rolesO'] = [x for x in g['roles'] if x['t'] != s]
        out.append(g)
    return out


def load_all():
    return {k: load(k) for k in ORDER if os.path.exists(f'{BASE}/pb_{k}.jsonl')}
