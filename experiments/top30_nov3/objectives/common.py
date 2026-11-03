"""Loaders shared by the objectives stream (top-30 benchmark vs our v84-v88 games).
   Game rows: {mid, ds ('top'|'me'), map, dec (path), mj (map json path), sides: {0: {id, name, rating, rank}, 1: ...}, winner}
   Groups: mapgroups.full_groups with the extended half-group tables (map_fail + v88_bugs + objectives/half_groups_top30.json)."""
import json, os, sys
from collections import deque
BASE = '/home/claude/cambridge_battlecode/experiments'
TOP = f'{BASE}/top30_nov3'
LAD = f'{BASE}/ladder_nov2'
OBJ = f'{TOP}/objectives'
POOL = '/home/claude/data/mapjson_pool'
ME = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'
sys.path.insert(0, f'{LAD}/map_fail')
import mapgroups  # noqa: E402
for fn in (f'{LAD}/v88_bugs/half_groups_ext.json', f'{OBJ}/half_groups_top30.json'):
    if os.path.exists(fn):
        for k, v in json.load(open(fn)).items():
            mapgroups.HALF.setdefault(k, v)
full_groups = mapgroups.full_groups
BIG = 10 ** 6

_ladder = json.load(open(f'{TOP}/ladder.json'))['teams']
RATING = {t['teamId']: (t['rating'], t['rank'], t['name']) for t in _ladder}
OUR_SINCE = '2026-11-02T00:00'


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def bfs(rows, starts, w, h):
    d = [[-1] * w for _ in range(h)]
    q = deque()
    for x, y in starts:
        if 0 <= x < w and 0 <= y < h and d[y][x] < 0:
            d[y][x] = 0
            q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and d[ny][nx] < 0 and rows[ny][nx] not in '#oA':
                    d[ny][nx] = d[y][x] + 1
                    q.append((nx, ny))
    return d


def top_games():
    """top-30 vs top-30 games with a decode: dec file <map>_<mid8>.json"""
    sel = {}
    for l in open(f'{TOP}/selection.jsonl'):
        m = json.loads(l)
        sel[m['matchId']] = m
    out = []
    for f in sorted(os.listdir(f'{TOP}/dec')):
        if not f.endswith('.json') or os.path.getsize(f'{TOP}/dec/{f}') < 1000:
            continue
        mapname, mid8 = f[:-5].rsplit('_', 1)
        ms = [m for mid, m in sel.items() if mid.startswith(mid8)]
        if not ms:
            continue
        m = ms[0]
        if m['status'] != 'finished' or not os.path.exists(f'{POOL}/{mapname}.json') or mapname not in mapgroups.HALF:
            continue
        sides = {}
        winner = None
        for t in m['teams']:
            s = 0 if t['side'] == 'a' else 1
            r = RATING.get(t['teamId'], (None, None, t['name']))
            sides[s] = {'id': t['teamId'], 'name': t['name'], 'rating': r[0], 'rank': r[1]}
            if t['result'] == 'win':
                winner = s
        out.append({'mid': m['matchId'], 'ds': 'top', 'map': mapname, 'dec': f'{TOP}/dec/{f}', 'mj': f'{POOL}/{mapname}.json',
                    'sides': sides, 'winner': winner, 'created': m['createdAt'], 'end': m.get('endReason')})
    return out


def our_games(since=OUR_SINCE):
    """our games since Nov 2 (v84-v88) with a decode; sides[we]['id'] == ME"""
    out = []
    for l in open(f'{LAD}/matches_me.jsonl'):
        m = json.loads(l)
        if m['status'] != 'finished' or m['createdAt'] < since:
            continue
        mid = m['matchId']
        if not (os.path.exists(f'{LAD}/dec/{mid}.json') and os.path.getsize(f'{LAD}/dec/{mid}.json') > 1000):
            continue
        if m['map'] not in mapgroups.HALF or not os.path.exists(f'{POOL}/{m["map"]}.json'):
            continue
        sides = {}
        winner = None
        for t in m['teams']:
            s = 0 if t['side'] == 'a' else 1
            r = RATING.get(t['teamId'], (None, None, t['name']))
            sides[s] = {'id': t['teamId'], 'name': t['name'], 'rating': r[0], 'rank': r[1]}
            if t['result'] == 'win':
                winner = s
        ver = 'v88' if m['createdAt'] >= '2026-11-03T02:30' else 'v84-87'
        out.append({'mid': mid, 'ds': 'me', 'map': m['map'], 'dec': f'{LAD}/dec/{mid}.json', 'mj': f'{POOL}/{m["map"]}.json',
                    'sides': sides, 'winner': winner, 'created': m['createdAt'], 'end': m.get('endReason'), 'kind': m['kind'], 'ver': ver})
    return out


def load(g):
    d = json.load(open(g['dec']))
    mj = json.load(open(g['mj']))
    return d, mj
