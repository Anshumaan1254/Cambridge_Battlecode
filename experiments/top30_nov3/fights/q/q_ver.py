#!/usr/bin/env python3
"""v84 vs v88 split (US84 / US88 / OPP) for the step / dive / respawn / camp metrics, the weak+neq/nmore step-ins, and example rows."""
import json, os, random
from collections import defaultdict
from statistics import mean
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = HERE + '/out'
def load(n): return [json.loads(l) for l in open(f'{OUT}/our_{n}.jsonl')]
G = load('games'); GM = {g['mid']: g for g in G}
D = load('deaths'); RT = load('retreats'); DV = load('dives')
P = lambda x: f'{100*x:.0f}%'
def grp(mid, t):
    g = GM[mid]
    if g['ver'] not in ('v84', 'v88'): return None
    return ('US' + g['ver'][1:]) if t == g['we'] else ('OPP' + g['ver'][1:])
n = defaultdict(int)
for g in G:
    for t in (0, 1):
        k = grp(g['mid'], t)
        if k: n[k] += 1
# step stats from games: keys like '0|weak+nmore|toward|n'
st = defaultdict(lambda: defaultdict(int))
for g in G:
    for k, v in g.get('step_stats', {}).items():
        t, band, dirn, what = k.split('|')
        kk = grp(g['mid'], int(t))
        if kk: st[kk][(band, dirn, what)] += v
print('team-games', dict(n))
for kk in sorted(n):
    s = st[kk]
    row = []
    for band in ('weak', 'weak+nmore', 'weak+neq', 'par'):
        tn = s[(band, 'toward', 'n')]; td = s[(band, 'toward', 'died6')]
        row.append(f"{band}: toward {tn/n[kk]:.1f}/g die6 {P(td/max(1,tn))}")
    print(f'  {kk}: ' + ' | '.join(row))
for kk in sorted(n):
    dd = [d for d in D if grp(d['mid'], d['t']) == kk]
    ch = [d for d in dd if d['cause'] != 'camp']
    wi = [d for d in ch if d['tw8'] >= 2]
    ag = [d for d in dd if d['age'] is not None and d['age'] < 40]
    cw = [d for d in dd if d.get('camp_waker') == 'enemy' and d['camp_hits5'] > 0]
    print(f"  {kk}: deaths {len(dd)/n[kk]:.2f}/g, walk-in champion deaths {len(wi)/n[kk]:.2f}/g, respawn<40 {len(ag)/n[kk]:.2f}/g, enemy-woken camp {len(cw)/n[kk]:.2f}/g, stunned3 {P(mean(d['stunned3'] for d in dd))}")
# HoR retreat examples (v88, us, dash ready not used, caught)
random.seed(3)
ex = [r for r in RT if grp(r['mid'], r['t']) == 'US88' and r['champ'] == 'HeartOfRuin' and r['own_dash'] and not r['dash'] and r['died8']]
print('HoR no-dash caught examples (v88):', len(ex))
for r in random.sample(ex, min(4, len(ex))): print('   ', r['mid'], 'r', r['r'], 'body', r['body'], 'hp %.2f' % r['hp'], 'n_en', r['n_en'], 'pw %.2f' % r['pw_ratio'], 'enemy', r['enemy'])
ex = [r for r in RT if grp(r['mid'], r['t']) == 'US88' and r['champ'] in ('VesperVale', 'Vendetta') and r['own_dash'] and not r['dash'] and r['died8']]
print('Vesper/Vendetta no-dash caught examples (v88):', len(ex))
for r in random.sample(ex, min(3, len(ex))): print('   ', r['mid'], 'r', r['r'], 'body', r['body'], r['champ'], 'hp %.2f' % r['hp'], 'd_enemy', r['d_enemy'], 'enemy', r['enemy'])
# walk-in deaths at low power with >= equal bodies (v88)
ex = [d for d in D if grp(d['mid'], d['t']) == 'US88' and d['cause'] != 'camp' and d['tw8'] >= 2 and d['pw5'] is not None and d['pw5'] < 0.67 and d['al5'] >= d['en5']]
print('walk-in deaths pw5<0.67 with al5>=en5 (v88):', len(ex), f"{len(ex)/n['US88']:.2f}/g")
for d in random.sample(ex, min(4, len(ex))): print('   ', d['mid'], 'r', d['r'], 'body', d['body'], d['champ'], 'killer', d['killer'], 'al5 %.1f en5 %.1f pw5 %.2f hp5 %.2f' % (d['al5'], d['en5'], d['pw5'], d['hp5'] or 0))
ex = [d for d in D if grp(d['mid'], d['t']) == 'US88' and d.get('camp_waker') == 'enemy' and d['camp_hits5'] > 0]
print('enemy-woken camp deaths (v88):', len(ex))
for d in random.sample(ex, min(3, len(ex))): print('   ', d['mid'], 'r', d['r'], 'body', d['body'], d['champ'], 'killer', d['killer'], 'tw8', d['tw8'])
ex = [d for d in D if grp(d['mid'], d['t']) == 'US88' and d['age'] is not None and d['age'] < 40]
print('respawn<40 deaths (v88):', len(ex))
for d in random.sample(ex, min(3, len(ex))): print('   ', d['mid'], 'r', d['r'], 'body', d['body'], d['champ'], 'age', d['age'], 'tw8', d['tw8'], 'pw5', d['pw5'], 'd_own', d['d_own'])
