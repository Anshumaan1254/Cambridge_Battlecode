"""Harness for the execution stream: game lists (top-30 vs top-30 from top30_nov3/, ours from ladder_nov2/), map JSON, camp groups.
   import h30  (sys.path must include execution/).  Every game dict: key (file stem), mid, map, dec (path), mj (dict), we (team index
   of the side under study, or None for top-30 games where both sides are 'top'), res, ver, kind, tag ('top'|'v88'|'old')."""
import json, os, sys, subprocess
ROOT = '/home/claude/cambridge_battlecode'
T30 = f'{ROOT}/experiments/top30_nov3'
L2 = f'{ROOT}/experiments/ladder_nov2'
EXE = f'{T30}/execution'
POOL = '/home/claude/data/mapjson_pool'
sys.path.insert(0, f'{L2}/agent_fights')
sys.path.insert(0, f'{L2}/map_fail')
sys.path.insert(0, f'{L2}/v88_bugs')
import mapgroups  # noqa: E402
ME = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'
MORE = f'{EXE}/half_groups_more.json'
LADDER = json.load(open(f'{T30}/ladder.json'))
RATING = {t['teamId']: t['rating'] for t in LADDER['teams']}
RANK = {t['teamId']: t['rank'] for t in LADDER['teams']}
NAME = {t['teamId']: t['name'] for t in LADDER['teams']}
STRONG = set(json.load(open(f'{T30}/teams.json'))['strong'])


def load_ext():
    for f in (f'{L2}/v88_bugs/half_groups_ext.json', MORE):
        if os.path.exists(f):
            for k, v in json.load(open(f)).items():
                mapgroups.HALF.setdefault(k, v)


def ensure_groups(maps_replays):
    """maps_replays: {map: replay path}; runs map_fail/groups.mjs for maps missing from the half-group tables"""
    more = json.load(open(MORE)) if os.path.exists(MORE) else {}
    for m, rp in maps_replays.items():
        if m in mapgroups.HALF or m in more:
            continue
        out = subprocess.run(['nice', '-n', '19', 'node', f'{L2}/map_fail/groups.mjs', rp], capture_output=True, text=True, cwd=L2)
        line = [l for l in out.stdout.splitlines() if l.startswith('{')]
        if line:
            more[m] = json.loads(line[0])
            print('groups built', m, file=sys.stderr)
        else:
            print('groups fail', m, out.stderr[:300], file=sys.stderr)
    json.dump(more, open(MORE, 'w'))
    load_ext()


def mapjson(m):
    return json.load(open(f'{POOL}/{m}.json'))


def top_games():
    sel = [json.loads(l) for l in open(f'{T30}/selection.jsonl')]
    out = []
    for m in sel:
        key = f"{m['map']}_{m['matchId'][:8]}"
        dec = f'{T30}/dec/{key}.json'
        if not os.path.exists(dec) or os.path.getsize(dec) == 0:
            continue
        ta = [t for t in m['teams'] if t['side'] == 'a'][0]
        tb = [t for t in m['teams'] if t['side'] == 'b'][0]
        out.append({'key': key, 'mid': m['matchId'], 'map': m['map'], 'dec': dec, 'replay': f'{T30}/replays/{key}.repl26a', 'we': None,
                    'res': None, 'ver': 'top', 'kind': 'top', 'tag': 'top', 'created': m['createdAt'],
                    'teams': [ta['teamId'], tb['teamId']], 'names': [ta['name'], tb['name']],
                    'ratings': [RATING.get(ta['teamId']), RATING.get(tb['teamId'])],
                    'winner': 0 if ta['result'] == 'win' else 1 if tb['result'] == 'win' else None})
    return out


SW = [('2026-11-02T21:15:46', 'v84'), ('2026-11-03T01:00:56', 'v85'), ('2026-11-03T01:21:19', 'v86'), ('2026-11-03T02:52', 'v87'), ('9999', 'v88')]


def our_games(which='all'):
    """which: 'v88' (Nov 3 >= 02:52, ranked + paired unranked), 'old' (ranked Nov 2 - Nov 3 02:52, v84-v87), 'all' = both"""
    rows = [json.loads(l) for l in open(f'{L2}/matches_me.jsonl')]
    out = []
    for m in rows:
        if m['status'] != 'finished' or m['createdAt'] < '2026-11-02T00:00':
            continue
        mid = m['matchId']
        dec = f'{L2}/dec/{mid}.json'
        if not (os.path.exists(dec) and os.path.exists(f'{L2}/mj/{mid}.json')):
            continue
        ver = next(v for t, v in SW if m['createdAt'] < t)
        if ver == 'v88':
            tag = 'v88'
        elif m['kind'] == 'ranked':
            tag = 'old'
        else:
            continue
        if which != 'all' and tag != which:
            continue
        us = [t for t in m['teams'] if t['teamId'] == ME][0]
        th = [t for t in m['teams'] if t['teamId'] != ME][0]
        we = 0 if us['side'] == 'a' else 1
        out.append({'key': mid, 'mid': mid, 'map': m['map'], 'dec': dec, 'replay': f'{L2}/replays/{mid}.repl26a', 'we': we,
                    'res': 'W' if us['result'] == 'win' else 'L', 'ver': ver, 'kind': m['kind'], 'tag': tag, 'created': m['createdAt'],
                    'teams': [us['teamId'] if we == 0 else th['teamId'], th['teamId'] if we == 0 else us['teamId']],
                    'names': [us['name'] if we == 0 else th['name'], th['name'] if we == 0 else us['name']],
                    'ratings': [None, None], 'winner': we if us['result'] == 'win' else 1 - we, 'opp': th['name'], 'opp_id': th['teamId']})
    return out


def load(g):
    d = json.load(open(g['dec']))
    mj = mapjson(g['map'])
    return d, mj


load_ext()
