#!/usr/bin/env python3
"""One body, round by round: python3 v88_bugs/trace.py <mid-prefix> <body> <r0> <r1> [rad]
Each line: round, position, hp, gems/gold, its own events, camp hits on it (camp index/type/group), enemies and allies within rad,
groups within 4 (state: A alive / R reward up / D dead-respawning; camp hp sum)."""
import json, os, sys, glob
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h88  # noqa: E402
import mapgroups  # noqa: E402

BASE = h88.BASE


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


pref, body, r0, r1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
rad = int(sys.argv[5]) if len(sys.argv) > 5 else 8
f = [x for x in glob.glob(f'{BASE}/dec/{pref}*.json')][0]
mid = os.path.basename(f)[:-5]
m = [json.loads(l) for l in open(f'{BASE}/matches_me.jsonl') if mid in l][0]
d = json.load(open(f))
mj = json.load(open(f'{BASE}/mj/{mid}.json'))
h88.ensure_groups([{'map': m['map'], 'mid': mid}])
G = mapgroups.full_groups(m['map'], d['meta'], mj['sym'])
camp_group = {ci: gg['id'] for gg in G for ci in gg['idx']}
types = {b['index']: b['type'] for b in d['meta']['bodies']}
team = {b['index']: b['team'] for b in d['meta']['bodies']}
camps = {c['index']: c for c in d['meta']['camps']}
S = {rr['r']: {c[0]: c for c in rr['ch']} for rr in d['rounds'][1:]}
R = {rr['r']: rr for rr in d['rounds'][1:]}
ev = defaultdict(list)
for e in d['events']:
    if r0 - 1 <= e['r'] <= r1:
        ev[e['r']].append(e)
t = team[body]
print(f"== {mid[:8]} {m['map']} body {body} {types[body]} team {t}  (we = team {[x['side'] for x in m['teams'] if x['teamId'] == h88.ME][0]})")
for r in range(r0, r1 + 1):
    s = S.get(r - 1, {})
    me = s.get(body)
    if not me:
        continue
    if not me[7]:
        print(f'r{r} dead')
        continue
    p = (me[3], me[4])
    own = []
    hits = []
    for e in ev[r]:
        w = e.get('who')
        if w is None:
            if e['k'] == 'Attack' and e.get('camp') is not None and tuple(e['to']) == p:
                ci = e['camp']
                hits.append(f"c{ci}{camps[ci]['type'][:2]}G{camp_group.get(ci)}")
            continue
        if w == body and e['k'] not in ('Set priority',):
            k = e['k']
            if k == 'Move':
                own.append(f"mv{tuple(e['to'])}")
            elif k == 'Attack':
                tg = [i for i, c in s.items() if c[7] and (c[3], c[4]) == tuple(e['to']) and i != body]
                own.append(f"atk{tuple(e['to'])}{'E' + str(tg[0]) if tg else ''}")
            elif k == 'Cast ability':
                own.append(f"cast{e.get('ability')}{tuple(e['to']) if 'to' in e else ''}")
            elif k in ('Recall', 'Cancel channel'):
                own.append({'Recall': 'rec', 'Cancel channel': 'cxl'}[k])
            else:
                own.append(k.replace(' ', '_') + (str(e.get('gems', '')) if 'gems' in e else ''))
        elif w != body and e['k'] in ('Attack', 'Cast ability') and 'to' in e and tuple(e['to']) == p:
            own.append(f"<-hit by {w}{types[w][:4]}")
    near = []
    for i, c in sorted(s.items()):
        if i != body and c[7] and cheb((c[3], c[4]), p) <= rad:
            near.append(f"{'a' if team[i] == t else 'E'}{i}{types[i][:3]}@{c[3]},{c[4]}:{c[5]}")
    gs = []
    rr = R.get(r - 1)
    if rr:
        for gg in G:
            dd = min(cheb(p, x) for x in gg['tiles'])
            if dd <= 4:
                hp = sum(rr['campHp'][i] for i in gg['idx'])
                st = 'A' if hp > 0 else ('R' if rr['gr'][gg['id']] else 'D')
                gs.append(f"G{gg['id']}{st}{hp}d{dd}")
    print(f"r{r} {p} hp{me[5]}/{me[6]} g{me[8]} ${me[9]} | {' '.join(own)} | {'HIT ' + ','.join(hits) if hits else ''} | {' '.join(near)} | {' '.join(gs)}")
