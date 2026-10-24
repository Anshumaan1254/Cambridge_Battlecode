# Aggregate tools/live/shotdisc.mjs: what a body does in a round that starts with an enemy within its basic reach (ranged: <= 3,
# melee: <= 2 = step + hit) or within 4: hit / step toward / step away / sideways / still / camp; per group (us, them vs us, top vs
# top), champion type, early (r <= 300) / all. Also: rounds with an enemy within 2 by distance and action -> P(died within 10).
#   python tools/live/shotdisc_agg.py C:/battlecode/cache/an_fights/sd.jsonl
import json, sys
from collections import Counter, defaultdict
G = [json.loads(l) for l in open(sys.argv[1], encoding='utf-8') if l.strip()]
RANGED = {'VesperVale', 'Cassi', 'Stellar', 'Prism', 'Willow', 'Tavi'}
ACTS = ['hit', 'hit+move', 'toward', 'away', 'side', 'still', 'camp']
def group_of(g, t):
    if g['set'] == 'rp_top':
        return 'top'
    if g['ours'] is None:
        return None
    return 'us' if t == g['ours'] else 'them'
agg = defaultdict(Counter)  # (grp, type, inreach, phase) -> act counts ; also took / died
died = defaultdict(Counter)
for g in G:
    for k, n in g['c'].items():
        t, ty, dist, act, took, d10, ph = k.split('|')
        grp = group_of(g, int(t))
        if not grp:
            continue
        dist = int(dist)
        reach = 3 if ty in RANGED else 2
        inr = dist <= reach
        for p in (ph, 'all'):
            agg[(grp, ty, inr, p)][act] += n
            agg[(grp, '*', inr, p)][act] += n
            agg[(grp, '*R' if ty in RANGED else '*M', inr, p)][act] += n
            died[(grp, act, inr, p)]['n'] += n
            died[(grp, act, inr, p)]['d'] += int(d10) * n
            died[(grp, act, inr, p)]['took'] += int(took) * n
def line(c):
    n = sum(c.values())
    return f'n={n:6d} ' + ' '.join(f'{a} {100*c[a]/n:4.1f}%' for a in ACTS) if n else 'n=0'
for ph in ('e', 'all'):
    print(f'\n=== ACTION in rounds starting with an enemy IN BASIC REACH (ranged <= 3, melee <= 2), phase {"r<=300" if ph=="e" else "all"}')
    for ty in ('*', '*R', '*M', 'VesperVale', 'Vendetta', 'HeartOfRuin', 'Ryth', 'Marcella', 'Prism', 'Tavi'):
        for grp in ('us', 'them', 'top'):
            c = agg[(grp, ty, True, ph)]
            if sum(c.values()) < 200:
                continue
            print(f'  {ty:11s} {grp:5s} {line(c)}')
    print(f'--- enemy within 4 but outside basic reach')
    for ty in ('*R', '*M', 'VesperVale'):
        for grp in ('us', 'them', 'top'):
            print(f'  {ty:11s} {grp:5s} {line(agg[(grp, ty, False, ph)])}')
print('\n=== P(died within 10 rounds) and P(took champion damage that round) by action, enemy in basic reach, all rounds')
for grp in ('us', 'them', 'top'):
    print(f'  {grp:5s} ' + ' | '.join(f'{a}: died {100*died[(grp,a,True,"all")]["d"]/max(1,died[(grp,a,True,"all")]["n"]):.1f}% hit-on {100*died[(grp,a,True,"all")]["took"]/max(1,died[(grp,a,True,"all")]["n"]):.0f}%' for a in ACTS))
