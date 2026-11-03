#!/usr/bin/env python3
"""map_fail/analyze.py's per-game analysis on v88's games (cached per game in out/ana/<mid>.json).
   nice -n 19 python3 v88_bugs/run_analyze.py [L|W|all]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h88  # noqa: E402
import analyze  # noqa: E402
which = sys.argv[1] if len(sys.argv) > 1 else 'L'
gs = h88.games(None if which == 'all' else which)
h88.ensure_groups(gs)
os.makedirs(f'{h88.V}/out/ana', exist_ok=True)
for g in gs:
    f = f"{h88.V}/out/ana/{g['mid']}.json"
    if os.path.exists(f):
        continue
    try:
        row, dl = analyze.analyse(g)
    except Exception as e:  # noqa: BLE001
        print('FAIL', g['mid'], g['map'], repr(e)[:200], flush=True)
        continue
    json.dump({'row': row, 'deaths': dl}, open(f, 'w'))
    print(g['map'], g['mid'][:8], g['res'], row['sub_we'], row['sub_they'], 'deaths', row['deaths_we'], row['deaths_they'], flush=True)
