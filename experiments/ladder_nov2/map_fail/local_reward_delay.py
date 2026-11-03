#!/usr/bin/env python3
"""Kill -> step-on delay in LOCAL games (same logic as reward_delay.py, which reads ladder replays).

    python3 -I experiments/ladder_nov2/map_fail/local_reward_delay.py DIR [DIR ...]

DIR holds replays named <map>_<side>.repl26a from `cambc run-batch` (bot A on side <side>), e.g. a bench2 g/ folder kept with
--keep. Each replay is decoded once (node tools/replay/decode.mjs --gold-captures) into DIR/dec/<name>.json. Only maps listed in
map_fail/half_groups.json can be analysed. Prints, per DIR, A's and B's kills in rounds 1-300 and their step-on delays.
"""
import glob
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict

BASE = '/home/claude/cambridge_battlecode/experiments/ladder_nov2'
ROOT = '/home/claude/cambridge_battlecode'
sys.path.insert(0, f'{BASE}/map_fail')
from mapgroups import full_groups, HALF  # noqa: E402

cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))  # noqa: E731


def delays(dec, mj, mapname, we):
    d = json.load(open(dec))
    G = full_groups(mapname, d['meta'], mj['sym'])
    R = {rr['r']: rr for rr in d['rounds'][1:]}
    tile_group = {t: gg['id'] for gg in G for t in gg['tiles']}
    camp_at = {(c['x'], c['y']) for c in d['meta']['camps']}
    hits, caps = defaultdict(list), defaultdict(list)
    for e in d['events']:
        if e['r'] > 420:
            break
        if e['k'] == 'Attack' and e.get('who') is not None and tuple(e['to']) in tile_group:
            hits[tile_group[tuple(e['to'])]].append((e['r'], e['team'], e['who']))
        elif e['k'] == 'Cast ability' and e.get('who') is not None and 'to' in e and e.get('ability') != 6:
            P = tuple(e['to'])
            for q in camp_at:
                if cheb(q, P) <= (1 if e.get('ability') == 3 else 0) and q in tile_group:
                    hits[tile_group[q]].append((e['r'], e['team'], e['who']))
        elif e['k'] in ('CaptureGems', 'CaptureGold'):
            caps[tile_group.get(tuple(e['at']))].append((e['r'], e['team'], e['who'], e['gems'], e['gold']))
    out = []
    for gg in G:
        prev = False
        for r in range(1, 301):
            rr = R.get(r)
            if rr is None:
                continue
            dead = all(rr['campHp'][i] == 0 for i in gg['idx'])
            if dead and not prev:
                hs = [h for h in hits[gg['id']] if r - 3 <= h[0] <= r]
                if hs:
                    kt = Counter(h[1] for h in hs).most_common(1)[0][0]
                    cs = [c for c in caps[gg['id']] if c[0] >= r]
                    c0 = cs[0] if cs else None
                    delay = (c0[0] - 6 - r) if c0 else None
                    by = None if c0 is None else ('same' if c0[1] == kt else 'other')
                    out.append(('A' if kt == we else 'B', delay, by, gg['gems'], gg['gold']))
            prev = dead
    return out


def main():
    for D in sys.argv[1:]:
        os.makedirs(f'{D}/dec', exist_ok=True)
        agg = defaultdict(list)
        n = 0
        for f in sorted(glob.glob(f'{D}/*.repl26a')):
            name = os.path.basename(f)[:-8]
            mapname, side = name.rsplit('_', 1)
            if mapname not in HALF:
                continue
            mjp = f'/home/claude/data/mapjson_pool/{mapname}.json'
            if not os.path.exists(mjp):
                continue
            out = f'{D}/dec/{name}.json'
            if not os.path.exists(out):
                subprocess.run(['node', f'{ROOT}/tools/replay/decode.mjs', f, '--gold-captures', '--out', out], capture_output=True)
            if not os.path.exists(out):
                print('decode failed', f)
                continue
            we = 0 if side == 'a' else 1
            for t, delay, by, gems, gold in delays(out, json.load(open(mjp)), mapname, we):
                agg[t].append((delay, by))
            n += 1
        print(f'{D}: {n} games')
        for t in ('A', 'B'):
            xs = agg[t]
            dl = [x[0] for x in xs if x[0] is not None]
            print(f"  {t} kills {len(xs):4}  step-on <=1 {sum(1 for x in dl if x <= 1):4}  2-8 {sum(1 for x in dl if 2 <= x <= 8):3}"
                  f"  9-30 {sum(1 for x in dl if 9 <= x <= 30):3}  >30 {sum(1 for x in dl if x > 30):3}  never {sum(1 for x in xs if x[0] is None):3}"
                  f" | taken by the other team {sum(1 for x in xs if x[1] == 'other'):3} | mean delay {sum(dl) / max(1, len(dl)):.1f}")


if __name__ == '__main__':
    main()
