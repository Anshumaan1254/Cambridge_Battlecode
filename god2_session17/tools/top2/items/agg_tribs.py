# Tribute channels: interruption rate (stun / lock / death / manual cancel) by bag and by enemies within 6 at the start, per team
# (S = the study team's tributes, O = its opponents' tributes in the same games). From ix.mjs tribs records.
#   python tools/top2/items/agg_tribs.py C:/battlecode/cache/top2_items/ix_all.jsonl
import sys, json, collections
sys.path.insert(0, 'tools/top2/items')
from common import *
idx = load_index()
T = collections.defaultdict(list)
for l in open(sys.argv[1], encoding='utf-8'):
    g = json.loads(l)
    stem = g['file'].replace('.repl26a', '')
    team = {b['i']: b['t'] for b in g['B']}
    for st in idx.get(stem, []):
        for t in g['tribs']:
            if t[5] in ('restart', 'open'):
                continue
            grp = 'S' if team[t[1]] == st['ti'] else 'O'
            T[(st['key'], grp)].append(t)
def bb(b):
    return '1-49' if b < 50 else '50-149' if b < 150 else '150+'
print('| team | grp | tributes / game | bag median | completed | bag 1-49: interrupted (enemy within 6 at start: yes / no) | bag 50-149 | bag 150+ | by stun / lock / death / cancel |')
print('|---|---|---|---|---|---|---|---|---|')
for key in KEYS:
    for grp in 'SO':
        L = T[(key, grp)]
        if not L:
            continue
        G = len({1 for _ in [0]})
        n = len(L)
        games = sum(1 for s, v in idx.items() for st in v if st['key'] == key)
        cells = []
        for b in ('1-49', '50-149', '150+'):
            sub = [t for t in L if bb(t[4]) == b]
            y = [t for t in sub if t[8] > 0]; nn = [t for t in sub if t[8] == 0]
            f = lambda xs: pct(sum(1 for t in xs if t[5] != 'ok'), len(xs)) + f' ({len(xs)})'
            cells.append(f'{f(y)} / {f(nn)}')
        why = collections.Counter(t[5] for t in L if t[5] != 'ok')
        print(f'| {key} | {grp} | {n/games:.1f} | {med([t[4] for t in L]):.0f} | {pct(sum(1 for t in L if t[5]=="ok"), n)} | ' + ' | '.join(cells) + f' | {why["stun"]} / {why["lock"]} / {why["death"]} / {why["cancel"]} |')
