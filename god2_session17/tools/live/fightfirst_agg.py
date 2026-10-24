# Aggregate tools/live/fightfirst.mjs output: how first strikes happen (who closed the gap, whether the victim could have hit
# first, ranged holds), and how killers close on their victims.   python tools/live/fightfirst_agg.py C:/battlecode/cache/an_fights/ff.jsonl
import json, sys
from collections import Counter
G = [json.loads(l) for l in open(sys.argv[1], encoding='utf-8') if l.strip()]
OURS = [g for g in G if g['set'] in ('rp_bb4D', 'rp_ft52D') and g['ours'] is not None]
TOP = [g for g in G if g['set'] == 'rp_top']
RANGED = {'VesperVale', 'Cassi', 'Stellar', 'Prism', 'Willow', 'Tavi'}
def pct(a, b): return f'{100.0*a/b:.1f}%' if b else '-'
def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float('nan')
def rows(games, who, lim=2001):
    out = []
    for g in games:
        for x in g['firsts']:
            if x['r0'] > lim or x['n'] < 2 and sum(x['dE']) == 0:
                continue
            if who == 'us' and x['st'] != g['ours']: continue
            if who == 'them' and x['st'] == g['ours']: continue
            out.append(x)
    return out
for lim in (300, 2001):
    print(f'\n=== FIRST STRIKES (engagements with >= 2 hits or a death), r0 <= {lim}')
    for lab, games, who in (('we strike first', OURS, 'us'), ('they strike first (vs us)', OURS, 'them'), ('top-vs-top', TOP, 'all')):
        R = rows(games, who, lim)
        n = len(R)
        vwalk = sum(1 for x in R if x['vClose'] > 0 and x['aClose'] == 0)
        awalk = sum(1 for x in R if x['aClose'] > 0 and x['vClose'] == 0)
        both = sum(1 for x in R if x['aClose'] > 0 and x['vClose'] > 0)
        none = n - vwalk - awalk - both
        could = sum(x['vCould1'] for x in R)
        inb = sum(x['aBasic1'] for x in R)
        own_first = sum(1 for x in R if x['first'] == x['st'])
        vstep0 = sum(1 for x in R if x['vClose0'] > 0)
        ra = [x for x in R if x['a'] in RANGED]
        ra_hold = sum(1 for x in ra if x['aClose'] == 0 and x['aClose0'] == 0)
        print(f'  [{lab}] n={n}: in r0-3..r0-1 only the victim closed {pct(vwalk,n)}, only the attacker {pct(awalk,n)}, both {pct(both,n)}, neither {pct(none,n)} | '
              f'victim stepped in during r0 {pct(vstep0,n)} | victim already in the attacker\'s basic range at r0-1 {pct(inb,n)} | victim could have struck first (in its own reach at r0-1) {pct(could,n)} | '
              f'starter\'s team acted first in r0 {pct(own_first,n)} | first hit is a cast {pct(sum(x["cast"] for x in R),n)} | ranged first hitter that did not move {pct(ra_hold,len(ra))} of {len(ra)} | '
              f'dist r0-1 {mean([x["dist"][0] for x in R]):.2f} | attacker spell up {pct(sum(x["aReady"] for x in R),n)} victim spell up {pct(sum(x["vReady"] for x in R),n)} | victim farming {pct(sum(1 for x in R if x["vFarm"]),n)}')
        # outcomes by how it started
        for lab2, cond in (('victim walked in', lambda x: x['vClose'] > 0 and x['aClose'] == 0), ('attacker walked in', lambda x: x['aClose'] > 0 and x['vClose'] == 0), ('both closed', lambda x: x['aClose'] > 0 and x['vClose'] > 0), ('neither', lambda x: x['aClose'] == 0 and x['vClose'] == 0)):
            xs = [x for x in R if cond(x)]
            st = [x['st'] for x in xs]
            sd = sum(x['dE'][x['st']] for x in xs); od = sum(x['dE'][1 - x['st']] for x in xs)
            print(f'      {lab2:18s} n={len(xs):5d} starter deaths/eng {sd/max(1,len(xs)):.2f} victim-side deaths/eng {od/max(1,len(xs)):.2f}')
print('\n=== KILLER / VICTIM CLOSING in the 8 rounds before a champion kill')
for lab, games, who in (('our deaths', OURS, 'us'), ('their deaths (vs us)', OURS, 'them'), ('top-vs-top', TOP, 'all')):
    K = []
    for g in games:
        for x in g['kd']:
            if who == 'us' and x['team'] != g['ours']: continue
            if who == 'them' and x['team'] == g['ours']: continue
            K.append(x)
    n = len(K)
    print(f'  [{lab}] n={n}: victim closing moves {mean([x["vClose"] for x in K]):.2f} away {mean([x["vAway"] for x in K]):.2f} killer closing {mean([x["kClose"] for x in K]):.2f} | victim hit while closing (>=1 round) {pct(sum(1 for x in K if x["hitWhileClosing"]>0), n)} (>=2 {pct(sum(1 for x in K if x["hitWhileClosing"]>=2), n)}) | victim own hit rounds {mean([x["ownHits"] for x in K]):.2f}, none {pct(sum(1 for x in K if x["ownHits"]==0), n)}')
    for vt in ('VesperVale', 'Vendetta', 'HeartOfRuin', 'Ryth', 'Marcella', 'Prism'):
        xs = [x for x in K if x['v'] == vt]
        if len(xs) < 20: continue
        print(f'      {vt:12s} n={len(xs):4d} hit while closing {pct(sum(1 for x in xs if x["hitWhileClosing"]>0), len(xs))} own hit rounds {mean([x["ownHits"] for x in xs]):.2f} none {pct(sum(1 for x in xs if x["ownHits"]==0), len(xs))} killer ranged {pct(sum(1 for x in xs if x["k"] in RANGED), len(xs))}')
