#!/usr/bin/env python3
"""E1 mechanism on v95: the objectives stream's contested big-group respawn cycles (top30_nov3/objectives/extract_obj.analyse) on
v95's decoded games, vs the stream's v88 rows (objectives/out/games_me.jsonl, ver v88, loss-heavy). Cache: out/obj/<mid>.json.
Usage: nice -n 19 python3 -I obj_v95.py"""
import json, glob, os, sys
from collections import Counter
ROOT = '/home/claude/cambridge_battlecode'
V95 = f'{ROOT}/experiments/deep_research_nov3/v95'
OBJ = f'{ROOT}/experiments/top30_nov3/objectives'
sys.path.insert(0, OBJ)
import common as C  # noqa: E402
import extract_obj as XO  # noqa: E402
os.makedirs(f'{V95}/out/obj', exist_ok=True)
ME = C.ME

rows = []
for p in glob.glob(f'{V95}/out/g/*.json'):
    gi = json.load(open(p))['info']
    if gi['ver'] != 'v95':
        continue
    mid = gi['mid']
    cache = f'{V95}/out/obj/{mid}.json'
    if not os.path.exists(cache):
        m = None
        for l in open(f'{V95}/all_recent.jsonl'):
            x = json.loads(l)
            if x['matchId'] == mid:
                m = x
                break
        sides, winner = {}, None
        for t in m['teams']:
            s = 0 if t['side'] == 'a' else 1
            sides[s] = {'id': t['teamId'], 'name': t['name'], 'rating': None, 'rank': None}
            if t['result'] == 'win':
                winner = s
        g = {'mid': mid, 'ds': 'me', 'map': m['map'], 'dec': f'{V95}/dec/{mid}.json', 'mj': f'{V95}/mj/{mid}.json', 'sides': sides,
             'winner': winner, 'created': m['createdAt'], 'end': m.get('endReason'), 'kind': m['kind'], 'ver': 'v95'}
        try:
            r = XO.analyse(g)
        except Exception as ex:  # noqa: BLE001
            print('FAIL', mid[:8], repr(ex)[:200])
            continue
        json.dump(r, open(cache, 'w'))
    rows.append(json.load(open(cache)))
v88 = [json.loads(l) for l in open(f'{OBJ}/out/games_me.jsonl')]
v88 = [r for r in v88 if r.get('ver') == 'v88']


def contested(cy):
    d0, d1 = cy['d']
    return d0 is not None and d1 is not None and abs(d0 - d1) <= 0.2 * (d0 + d1)


def stats(label, pairs):
    taken = cap = present = n_cyc = hitfirst_lost = hitfirst = gems = 0
    beh, beh11 = Counter(), Counter()
    for r, t in pairs:
        for c in r['cycles']:
            if c['mono'] or not contested(c):
                continue
            if c['start'] > 1:
                n_cyc += 1
                if c['by'] in (0, 1):
                    taken += 1
                    cap += c['by'] == t
                a = c['arr'].get(str(t))
                present += bool(a and a['wait'] >= 0)
            if c['first_hit'] == t:
                hitfirst += 1
                hitfirst_lost += c['by'] == 1 - t
            if c['by'] == t:
                gems += c.get('gems', 0) or 0
            rc = c['react'].get(str(t))
            if rc:
                beh[rc['beh']] += 1
                if rc['n'] == 1 and rc['n_en'] == 1 and rc['hp'] >= 0.8:
                    beh11[rc['beh']] += 1
    n = len(pairs)
    tb, t11 = sum(beh.values()), sum(beh11.values())
    print(f"{label:10s} n {n:3d} | contested cycles/g {n_cyc / max(1, n):.1f} | captured share of taken {cap / max(1, taken):.2f} | present at respawn {present / max(1, n_cyc):.2f}"
          f" | hit first then lost {hitfirst_lost / max(1, hitfirst):.2f} | gems captured on them/g {gems / max(1, n):.0f}")
    print(f"{'':10s} reaction (all contacts {tb}): " + ', '.join(f'{k} {v / tb:.0%}' for k, v in beh.most_common()) if tb else '')
    print(f"{'':10s} reaction 1v1 hp>=0.8 ({t11}): " + ', '.join(f'{k} {v / t11:.0%}' for k, v in beh11.most_common()) if t11 else '')


def we(r):
    return 0 if r['sides']['0']['id'] == ME else 1


stats('v95 we', [(r, we(r)) for r in rows])
stats('v95 we L', [(r, we(r)) for r in rows if r['winner'] != we(r)])
stats('v95 opp', [(r, 1 - we(r)) for r in rows])
stats('v88 we', [(r, we(r)) for r in v88])
stats('v88 opp', [(r, 1 - we(r)) for r in v88])
