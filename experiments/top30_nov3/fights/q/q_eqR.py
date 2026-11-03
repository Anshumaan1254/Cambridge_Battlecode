#!/usr/bin/env python3
"""Equal-R exchange decomposition: what differs between US / OPP / TOP when the opener's local R is 0.67-1.5.
usage: python3 -I q/q_eqR.py  (reads ../out via analyze-style loaders)"""
import json, os, sys, math
from collections import Counter, defaultdict
from statistics import mean, median
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = HERE + '/out'
def load(ds, n): return [json.loads(l) for l in open(f'{OUT}/{ds}_{n}.jsonl')]
G = {ds: load(ds, 'games') for ds in ('top', 'our')}
F = {ds: load(ds, 'fights') for ds in G}
HT = {ds: load(ds, 'hits') for ds in G}
def pred(group):
    if group == 'TOP': return 'top', lambda g, t: True
    if group == 'TOPl': return 'top', lambda g, t: g['teams'][t]['result'] == 'L'
    if group == 'US': return 'our', lambda g, t: g['ver'] in ('v84', 'v88') and t == g['we']
    if group == 'US88': return 'our', lambda g, t: g['ver'] == 'v88' and t == g['we']
    if group == 'OPP': return 'our', lambda g, t: g['ver'] in ('v84', 'v88') and t != g['we']
def keys(group):
    ds, p = pred(group)
    return ds, {(g['mid'], t) for g in G[ds] for t in (0, 1) if p(g, t)}
# hits per fight per team: kinds, stun count, distinct targets, share of hits on the most-hit target
hidx = {}
for ds in HT:
    d = defaultdict(lambda: {0: [], 1: []})
    for h in HT[ds]:
        if h.get('fid') is None: continue
        d[(h['mid'], h['fid'])][h['t']].append(h)
    hidx[ds] = d
def side_stats(ds, f, t):
    hs = hidx[ds].get((f['mid'], f['fid']), {0: [], 1: []})[t]
    kinds = Counter(h['kind'] for h in hs)
    tg = Counter(h['tgt'] for h in hs)
    top = tg.most_common(1)[0][1] / len(hs) if hs else None
    return kinds, len(tg), top, len(hs)
def run(group, role, lo, hi):
    ds, K = keys(group)
    rows = []
    for f in F[ds]:
        if not f['exchange'] or f['win'] is None: continue
        t = f['first'] if role == 'open' else 1 - f['first']
        if (f['mid'], t) not in K: continue
        o = 1 - t
        if role == 'open': R = f['r_open']
        else:
            pe = f['pw'][str(o)]; R = f['pw'][str(t)] / pe if pe > 0 else None
        if R is None or not (lo <= R < hi): continue
        k_t, nt_t, foc_t, nh_t = side_stats(ds, f, t)
        k_o, nt_o, foc_o, nh_o = side_stats(ds, f, o)
        sh_t = f['shards'][str(t)] / max(1, f['parts'][str(t)]); sh_o = f['shards'][str(o)] / max(1, f['parts'][str(o)])
        rows.append(dict(win=f['win'] == t, gap=sh_t - sh_o, ans=f['answer'], st_t=f['stuns'][str(t)], st_o=f['stuns'][str(o)],
                         nh_t=nh_t, nh_o=nh_o, dmg_t=f['dmg'][str(t)], dmg_o=f['dmg'][str(o)], parts_t=f['parts'][str(t)], parts_o=f['parts'][str(o)],
                         dead_t=f['dead'][str(t)], dead_o=f['dead'][str(o)], foc_t=foc_t, foc_o=foc_o, nt_t=nt_t, nt_o=nt_o,
                         spell_t=k_t.get('spell', 0), spell_o=k_o.get('spell', 0), area_t=k_t.get('area', 0), atk_t=k_t.get('atk', 0),
                         dash_t=k_t.get('dash', 0), dash_o=k_o.get('dash', 0), kinds_t=k_t, t_hp=f['t_hp'], a_hp=f['a_hp'], dur=f['end'] - f['start'],
                         approach=f['approach'], hp0_t=f['hp0'][str(t)], hp0_o=f['hp0'][str(o)]))
    return rows
P = lambda x: f'{100*x:.0f}%'
def summ(rows):
    n = len(rows)
    if not n: return 'n=0'
    w = mean(r['win'] for r in rows)
    eqg = [r for r in rows if abs(r['gap']) < 3]
    neg = [r for r in rows if r['gap'] <= -5]
    out = [f"n={n} win {P(w)}", f"gap mean {mean(r['gap'] for r in rows):+.1f} (<=-5: {P(len(neg)/n)})",
           f"win|gap+-3 {P(mean(r['win'] for r in eqg)) if eqg else '-'} (n={len(eqg)})",
           f"stuns t/o {mean(r['st_t'] for r in rows):.2f}/{mean(r['st_o'] for r in rows):.2f}",
           f"hits t/o {mean(r['nh_t'] for r in rows):.1f}/{mean(r['nh_o'] for r in rows):.1f}",
           f"dmg t/o {mean(r['dmg_t'] for r in rows):.0f}/{mean(r['dmg_o'] for r in rows):.0f}",
           f"dmg/hit t/o {sum(r['dmg_t'] for r in rows)/max(1,sum(r['nh_t'] for r in rows)):.0f}/{sum(r['dmg_o'] for r in rows)/max(1,sum(r['nh_o'] for r in rows)):.0f}",
           f"parts t/o {mean(r['parts_t'] for r in rows):.2f}/{mean(r['parts_o'] for r in rows):.2f}",
           f"focus(top-target share) t/o {mean(r['foc_t'] for r in rows if r['foc_t'] is not None):.2f}/{mean(r['foc_o'] for r in rows if r['foc_o'] is not None):.2f}",
           f"targets t/o {mean(r['nt_t'] for r in rows):.2f}/{mean(r['nt_o'] for r in rows):.2f}",
           f"spells t/o {mean(r['spell_t'] for r in rows):.2f}/{mean(r['spell_o'] for r in rows):.2f}",
           f"deaths t/o {mean(r['dead_t'] for r in rows):.2f}/{mean(r['dead_o'] for r in rows):.2f}",
           f"ans<=1 {P(mean((r['ans'] is not None and r['ans']<=1) for r in rows))}",
           f"dur {mean(r['dur'] for r in rows):.1f}",
           f"hp0/body t {mean(r['hp0_t']/max(1,r['parts_t']) for r in rows):.0f} o {mean(r['hp0_o']/max(1,r['parts_o']) for r in rows):.0f}"]
    return ' | '.join(out)
for role in ('open', 'recv'):
    for lo, hi in ((0.67, 1.5), (0.8, 1.25), (1.25, 2.0), (2.0, 99)):
        print(f'## {role} R {lo}-{hi}')
        for g in ('TOP', 'TOPl', 'US', 'US88', 'OPP'):
            rows = run(g, role, lo, hi)
            print(f'  {g:5s} {summ(rows)}')
# kinds overall
print('## hit kinds per exchange side (all exchanges)')
for g in ('TOP', 'US', 'OPP'):
    rows = run(g, 'open', 0, 999) + run(g, 'recv', 0, 999)
    c = Counter()
    for r in rows: c.update(r['kinds_t'])
    tot = sum(c.values()); print(' ', g, {k: P(v / tot) for k, v in c.most_common()})
