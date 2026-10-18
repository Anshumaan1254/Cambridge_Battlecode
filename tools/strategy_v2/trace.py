#!/usr/bin/env python3
"""Print a round-by-round trace of one match window: positions, HP, actions, damage.

usage: python3 -I trace.py DMG_JSON R0 R1 [X Y RADIUS]
"""
import json
import sys

d = json.load(open(sys.argv[1]))
r0, r1 = int(sys.argv[2]), int(sys.argv[3])
cx = int(sys.argv[4]) if len(sys.argv) > 4 else None
cy = int(sys.argv[5]) if len(sys.argv) > 5 else None
rad = int(sys.argv[6]) if len(sys.argv) > 6 else 99
meta = d['meta']
bt = {b['index']: (b['team'], b['type']) for b in meta['bodies']}
camps = {c['index']: c for c in meta['camps']}
st = {}
for rr in d['rounds']:
    for c in rr['ch']:
        st[(rr['r'], c[0])] = c
evs = [e for e in d['events'] if r0 <= e['r'] <= r1]
dm = [x for x in d['dmg'] if r0 <= x[0] <= r1]


def nm(i):
    t, ty = bt[i]
    return f"{'A' if t == 0 else 'B'}{ty[:4]}{i}"


for r in range(r0, r1 + 1):
    line = []
    for i in sorted(bt):
        c = st.get((r, i))
        if not c:
            continue
        if cx is not None and max(abs(c[3] - cx), abs(c[4] - cy)) > rad:
            continue
        line.append(f"{nm(i)}@{c[3]},{c[4]} {c[5]}/{c[6]}{'' if c[7] else ' DEAD'}{' g' + str(c[8]) if c[8] else ''}")
    print(f"--- r{r}: " + ' | '.join(line))
    for e in evs:
        if e['r'] != r:
            continue
        if e['k'] in ('Move', 'Set priority', 'Place ward', 'Respawn', 'Tick', 'Capture'):
            continue
        who = nm(e['who']) if 'who' in e and e['who'] in bt else (f"camp{e['camp']}" if 'camp' in e else '?')
        extra = ''
        if e['k'] == 'Cast ability':
            extra = f" slot{e.get('slot')} ab{e.get('ability')}"
        if e['k'] == 'Death':
            extra = f" by {nm(e['by']) if isinstance(e.get('by'), int) and e['by'] in bt else e.get('by')} bag {e.get('bag')}"
        print(f"     {e['k']:14} {who:12} {e.get('from', '')} -> {e.get('to', '')}{extra}")
    for x in dm:
        if x[0] != r:
            continue
        rr, kind, ak, ai, slot, tk, ti, dh, alive, tx, ty, ohp, omax = x
        a = nm(ai) if ak == 'c' else f"camp{ai}"
        t = nm(ti) if tk == 'c' else f"{camps[ti]['type']}{ti}"
        if tk == 'm' and ak == 'c' and cx is not None and max(abs(tx - cx), abs(ty - cy)) > rad:
            continue
        print(f"       dmg {kind:12} {a:12} -> {t:12} {dh:8.1f}  (target hp before {ohp})")
