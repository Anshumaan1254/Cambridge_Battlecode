"""Harness for the v88 bug hunt: game list, extended half-map camp groups, loaders.
   import h88  (sys.path must include v88_bugs/)"""
import json, os, sys, subprocess
BASE = '/home/claude/cambridge_battlecode/experiments/ladder_nov2'
V = f'{BASE}/v88_bugs'
sys.path.insert(0, f'{BASE}/agent_fights')
sys.path.insert(0, f'{BASE}/map_fail')
import mapgroups  # noqa: E402
EXT = f'{V}/half_groups_ext.json'
ME = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'


def load_ext():
    if os.path.exists(EXT):
        for k, v in json.load(open(EXT)).items():
            mapgroups.HALF.setdefault(k, v)


def ensure_groups(games):
    """run map_fail/groups.mjs on one replay per map missing from half_groups (engine wasm, read-only)"""
    ext = json.load(open(EXT)) if os.path.exists(EXT) else {}
    need = {}
    for g in games:
        if g['map'] not in mapgroups.HALF and g['map'] not in ext and g['map'] not in need:
            need[g['map']] = g['mid']
    for m, mid in need.items():
        out = subprocess.run(['node', f'{BASE}/map_fail/groups.mjs', f'{BASE}/replays/{mid}.repl26a'], capture_output=True, text=True, cwd=f'{BASE}')
        line = [l for l in out.stdout.splitlines() if l.startswith('{')]
        if line:
            ext[m] = json.loads(line[0])
        else:
            print('groups fail', m, out.stderr[:300], file=sys.stderr)
    json.dump(ext, open(EXT, 'w'))
    load_ext()


def games(res=None, decoded=True):
    rows = json.load(open(f'{V}/games.json'))
    out = []
    for r in rows:
        if r['status'] != 'finished':
            continue
        if res and r['res'] != {'L': 'loss', 'W': 'win'}.get(res, res):
            continue
        if decoded and not (os.path.exists(f"{BASE}/dec/{r['mid']}.json") and os.path.exists(f"{BASE}/mj/{r['mid']}.json")):
            continue
        out.append({'mid': r['mid'], 'map': r['map'], 'we': 0 if r['side'] == 'a' else 1, 'res': 'W' if r['res'] == 'win' else 'L',
                    'opp': r['opp'], 'created': r['created'], 'ver': 'v88', 'kind': r['kind'], 'old': r['old'], 'v87': r['v87']})
    return out


load_ext()
