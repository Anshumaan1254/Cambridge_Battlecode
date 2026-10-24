"""verify_items shared helpers: study-team game index (side -> team index, result, opponent, time) and per-game records."""
import json, os, collections

KEYS = ['pbg', 'ifish', 'pantheon', 'coo', 'cm', 'nyx']
T2 = 'C:/battlecode/cache/t2'
OUT = 'C:/battlecode/cache/top2_vitems'
FAM = 'MPDTJHB'  # Monster Power Durability Treasure Jungle Home Bruiser
STAT = 'sfh'
BASE = {  # engine probe: hp, +hp, str, +str, foc, +foc
    'Ryth': (1200, 100, 45, 5, 100, 10), 'VesperVale': (1000, 100, 55, 5, 100, 10), 'Vendetta': (1000, 100, 70, 6, 100, 10),
    'Cassi': (600, 65, 30, 3, 70, 13), 'Issac': (900, 80, 40, 3, 100, 10), 'Stellar': (650, 65, 30, 3.5, 70, 7),
    'Prism': (700, 60, 35, 2.5, 80, 8), 'Marcella': (1200, 100, 45, 5, 60, 15), 'Willow': (700, 50, 55, 3, 120, 5),
    'Ren': (900, 100, 35, 5, 100, 9), 'Varg': (1000, 100, 40, 5, 100, 10), 'Tavi': (900, 75, 45, 5, 110, 10),
    'HeartOfRuin': (1000, 100, 30, 3.5, 100, 12),
}


def code(item_id):
    return FAM[item_id // 6] + STAT[(item_id % 6) // 2]


def games(key):
    """Study-team games: list of dicts {key, mid8, base, map, S, win, opp, created}."""
    res = []
    for l in open(f'{T2}/{key}/index.jsonl', encoding='utf-8'):
        j = json.loads(l)
        st = [t for t in j['teams'] if t['teamId'][:8] == TEAMID[key][:8]]
        if not st:
            continue
        st = st[0]
        ot = [t for t in j['teams'] if t is not st][0]
        S = 0 if st['side'] == 'a' else 1
        res.append({'key': key, 'mid8': j['matchId'][:8], 'base': f"{j['map']}_{j['matchId'][:8]}", 'map': j['map'], 'S': S,
                    'win': st['result'] == 'win', 'opp': ot['name'], 'created': j['createdAt'], 'oppId': ot['teamId'],
                    'nS': len(st['draftPicks']), 'nO': len(ot['draftPicks'])})
    return res


TEAMID = {'pbg': '38e6d8c4-1608-44f5-956b-08390f564336', 'ifish': '1890540d-1ffc-4847-adbf-d0d08772f268',
          'pantheon': '547efb5b-57e5-4355-8501-3b331f506d62', 'coo': '1570a113-57fd-4f15-84fb-0d764b12799b',
          'cm': 'ad5474c2-784c-4f91-b8da-5fec554e4de4', 'nyx': '6f7fd199-4115-4fe0-8752-525bd8ccad8d'}


def groups():
    """Study groups: the six keys plus pbg14 (pbg games created from 14:00 UTC)."""
    g = {k: games(k) for k in KEYS}
    g['pbg14'] = [x for x in g['pbg'] if x['created'] >= '2026-10-23T14:00']
    g['pbg07'] = [x for x in g['pbg'] if x['created'] < '2026-10-23T14:00']
    return g


def load(path, keyf):
    d = {}
    for l in open(path, encoding='utf-8'):
        j = json.loads(l)
        if 'err' in j:
            continue
        d[keyf(j['file'])] = j
    return d


def vx():
    return load(f'{OUT}/vx_all.jsonl', lambda f: f.replace('.repl26a', ''))


def vd():
    return load(f'{OUT}/vd_all.jsonl', lambda f: f)


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else '-'
