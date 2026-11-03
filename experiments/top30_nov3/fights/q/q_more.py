#!/usr/bin/env python3
"""Extra queries for REPORT.txt: retreat dash use, answer latency by context, dmg per hit by champion, stun / walk-in / camp / respawn deaths."""
import json, os
from collections import Counter, defaultdict
from statistics import mean, median
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = HERE + '/out'
def load(ds, n): return [json.loads(l) for l in open(f'{OUT}/{ds}_{n}.jsonl')]
G = {ds: load(ds, 'games') for ds in ('top', 'our')}
GM = {g['mid']: g for ds in G for g in G[ds]}
def pred(group):
    if group == 'TOP': return 'top', lambda g, t: True
    if group == 'TOPl': return 'top', lambda g, t: g['teams'][t]['result'] == 'L'
    if group == 'US': return 'our', lambda g, t: g['ver'] in ('v84', 'v88') and t == g['we']
    if group == 'US88': return 'our', lambda g, t: g['ver'] == 'v88' and t == g['we']
    if group == 'OPP': return 'our', lambda g, t: g['ver'] in ('v84', 'v88') and t != g['we']
GR = ('TOP', 'TOPl', 'US', 'US88', 'OPP')
def keys(group):
    ds, p = pred(group)
    return ds, {(g['mid'], t) for g in G[ds] for t in (0, 1) if p(g, t)}
P = lambda x: f'{100*x:.0f}%'
which = os.environ.get('Q', 'all')
if which in ('all', 'ret'):
    RT = {ds: load(ds, 'retreats') for ds in G}
    print('## retreats of dashers with own dash ready: used dash / caught (died8) used vs not, by champion')
    for g in GR:
        ds, K = keys(g)
        rows = [r for r in RT[ds] if (r['mid'], r['t']) in K and r['own_dash']]
        by = defaultdict(list)
        for r in rows: by[r['champ']].append(r)
        s = []
        for c, rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
            u = [r for r in rs if r['dash']]; nu = [r for r in rs if not r['dash']]
            s.append(f"{c} n={len(rs)} used {P(len(u)/len(rs))} caught used {P(mean(r['died8'] for r in u)) if u else '-'} / not {P(mean(r['died8'] for r in nu)) if nu else '-'}")
        u = [r for r in rows if r['dash']]; nu = [r for r in rows if not r['dash']]
        lo = [r for r in rows if r['hp'] < 0.5]; lou = [r for r in lo if r['dash']]; lon = [r for r in lo if not r['dash']]
        print(f"  {g}: n={len(rows)} used {P(len(u)/len(rows))}, caught used {P(mean(r['died8'] for r in u))} / not {P(mean(r['died8'] for r in nu))}; hp<50%: n={len(lo)} used {P(len(lou)/max(1,len(lo)))} caught used {P(mean(r['died8'] for r in lou)) if lou else '-'} / not {P(mean(r['died8'] for r in lon)) if lon else '-'}; enemy within4 ready-stun: {P(mean(r['stun5']>0 for r in rows))}")
        for x in s[:5]: print('     ', x)
if which in ('all', 'fights'):
    F = {ds: load(ds, 'fights') for ds in G}
    HT = {ds: load(ds, 'hits') for ds in G}
    print('## received exchanges: answered <= 1 round, by opener kind0 / d1 (opener-target distance 1 round before) / target champion')
    for g in GR:
        ds, K = keys(g)
        rows = [f for f in F[ds] if f['exchange'] and (f['mid'], 1 - f['first']) in K]
        a1 = lambda rs: f"{P(mean(f['answer'] is not None and f['answer'] <= 1 for f in rs))} ({len(rs)})" if rs else '-'
        byk = defaultdict(list); byd = defaultdict(list); byt = defaultdict(list)
        for f in rows:
            byk[f['kind0']].append(f); byd['na' if f['d1'] is None else 'd<=1' if f['d1'] <= 1 else 'd2-3' if f['d1'] <= 3 else 'd4+'].append(f); byt[f['target_champ']].append(f)
        print(f"  {g}: all {a1(rows)} | kind " + ', '.join(f'{k} {a1(v)}' for k, v in sorted(byk.items())) + ' | d1 ' + ', '.join(f'{k} {a1(v)}' for k, v in sorted(byd.items())))
        print('      target: ' + ', '.join(f'{k} {a1(v)}' for k, v in sorted(byt.items(), key=lambda kv: -len(kv[1]))[:7]))
        # answer latency vs win
        a_fast = [f for f in rows if f['answer'] is not None and f['answer'] <= 1 and f['win'] is not None]
        a_slow = [f for f in rows if (f['answer'] is None or f['answer'] > 1) and f['win'] is not None]
        print(f"      win when answered <=1: {P(mean(f['win'] == 1 - f['first'] for f in a_fast))} ({len(a_fast)}), later: {P(mean(f['win'] == 1 - f['first'] for f in a_slow))} ({len(a_slow)})")
    print('## damage per champion hit by attacker champion and kind (all hits with dmg)')
    for g in ('TOP', 'US', 'US88', 'OPP'):
        ds, K = keys(g)
        d = defaultdict(lambda: [0, 0.0])
        for h in HT[ds]:
            if (h['mid'], h['t']) not in K or h.get('dmg') is None: continue
            k = (h['champ'], h['kind']); d[k][0] += 1; d[k][1] += h['dmg']
        tops = sorted(d.items(), key=lambda kv: -kv[1][0])[:10]
        print(f'  {g}: ' + ', '.join(f'{c}/{k} {v[1]/v[0]:.0f} ({v[0]})' for (c, k), v in tops))
if which in ('all', 'deaths'):
    D = {ds: load(ds, 'deaths') for ds in G}
    print('## deaths: stunned in last 3 r by killer champion (like-with-like: US vs OPP)')
    for g in GR:
        ds, K = keys(g)
        rows = [d for d in D[ds] if (d['mid'], d['t']) in K]
        n = len({k for k in K})
        byk = defaultdict(list)
        for d in rows: byk[d['killer']].append(d)
        print(f"  {g} ({len(rows)}): " + ', '.join(f"{k} {P(mean(d['stunned3'] for d in v))} ({len(v)})" for k, v in sorted(byk.items(), key=lambda kv: -len(kv[1]))[:7]))
        st = [d for d in rows if d['stunned3']]
        print(f"     stunned deaths: walked in (tw8>=2) {P(mean(d['tw8']>=2 for d in st))}, tw_killer4>=2 {P(mean((d['tw_killer4'] or 0)>=2 for d in st))}, hp5 {mean(d['hp5'] or 0 for d in st):.2f}, alone {P(mean(d['al5']<=1.0 for d in st))}; per team-game {len(st)/n:.2f}")
    print('## walk-in deaths (tw8 >= 2): context')
    for g in GR:
        ds, K = keys(g)
        rows = [d for d in D[ds] if (d['mid'], d['t']) in K and d['cause'] != 'camp']
        n = len(K)
        wi = [d for d in rows if d['tw8'] >= 2]
        c = Counter(d['started'] for d in wi)
        print(f"  {g}: champion deaths {len(rows)/n:.2f}/g, walk-in {len(wi)/n:.2f}/g ({P(len(wi)/len(rows))}); started by own {P(c['own']/max(1,len(wi)))}; hp5 mean {mean(d['hp5'] or 0 for d in wi):.2f}; pw5<0.67 {P(mean((d['pw5'] or 0)<0.67 for d in wi if d['pw5'] is not None))}; bag>0 {P(mean(d['bag']>0 for d in wi))}; kills10 {P(mean(d['kills10']>0 for d in wi))}; age<40 {P(mean(d['age'] is not None and d['age']<40 for d in wi))}; tw_killer4>=2 {P(mean((d['tw_killer4'] or 0)>=2 for d in wi))}; enemy half {P(mean(d['enemy_half'] for d in wi))}")
    print('## camp the enemy woke (last 5 r): per team-game, champion, farming, tw8')
    for g in GR:
        ds, K = keys(g)
        rows = [d for d in D[ds] if (d['mid'], d['t']) in K]
        n = len(K)
        cw = [d for d in rows if d.get('camp_waker') == 'enemy' and d['camp_hits5'] > 0]
        print(f"  {g}: {len(cw)/n:.2f}/g ({P(len(cw)/len(rows))}); waker counts {dict(Counter(d.get('camp_waker') for d in rows if d['camp_hits5']>0))}; of these tw8>=2 {P(mean(d['tw8']>=2 for d in cw)) if cw else '-'}, farming {P(mean(d['farming'] for d in cw)) if cw else '-'}, started own {P(mean(d['started']=='own' for d in cw)) if cw else '-'}")
    print('## deaths within 40 r of respawn (age<40)')
    for g in GR:
        ds, K = keys(g)
        rows = [d for d in D[ds] if (d['mid'], d['t']) in K]
        n = len(K)
        ag = [d for d in rows if d['age'] is not None and d['age'] < 40]
        print(f"  {g}: {len(ag)/n:.2f}/g; tw8>=2 {P(mean(d['tw8']>=2 for d in ag))}, started own {P(mean(d['started']=='own' for d in ag))}, d_own<=8 {P(mean((d['d_own'] if d['d_own'] is not None else 99)<=8 for d in ag))}, pw5<0.67 {P(mean((d['pw5'] or 9)<0.67 for d in ag))}")
    print('## deaths per team-game by map size class (spawn_dist / area), like-with-like US vs OPP same games')
    for g in GR:
        ds, K = keys(g)
        by = defaultdict(lambda: [0, 0, 0])
        for (mid, t) in K:
            gm = GM[mid]; a = gm['mf']['passable']
            c = 'small<1600' if a < 1600 else 'mid<4000' if a < 4000 else 'big'
            by[c][0] += 1; by[c][1] += gm['deaths'][str(t)] if isinstance(gm['deaths'], dict) else 0; by[c][2] += gm['final']
        print(f"  {g}: " + ', '.join(f"{c}: {v[1]/v[0]:.1f}/g, {1000*v[1]/v[2]:.1f}/1000r (n={v[0]})" for c, v in sorted(by.items())))
