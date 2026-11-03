#!/usr/bin/env python3
"""Example episodes (match id, body, round) for each pattern of REPORT.txt, from out/our_*.jsonl (v88 games first).

Usage: nice -n 19 python3 -I examples.py [n_per_pattern]
"""
import json, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE + '/out'
N = int(sys.argv[1]) if len(sys.argv) > 1 else 4
load = lambda ds, n: [json.loads(l) for l in open(f'{OUT}/{ds}_{n}.jsonl')]
G = {g['mid']: g for g in load('our', 'games')}
ok = lambda r: G[r['mid']]['ver'] in ('v84', 'v88') and r['t'] == G[r['mid']]['we']
D = [d for d in load('our', 'deaths') if ok(d)]
DV = [d for d in load('our', 'dives') if ok(d)]
CH = [d for d in load('our', 'chases') if ok(d)]
RT = [d for d in load('our', 'retreats') if ok(d)]
F = load('our', 'fights')
key = lambda r: (G[r['mid']]['ver'] != 'v88', -r.get('bag', 0))


def show(title, rows, fmt):
    rows = sorted(rows, key=key)
    print(f'\n{title}: {len(rows)} episodes (v88 {sum(1 for r in rows if G[r["mid"]]["ver"] == "v88")})')
    for r in rows[:N]:
        g = G[r['mid']]
        print(f"  {r['mid']} ({g['ver']} {g['map']} vs {g['teams'][1 - g['we']]['name']} {g['teams'][g['we']]['result']}) body {r['body']} {r['champ']} r{r['r']}: {fmt(r)}")


ck = [d for d in D if d['cause'] != 'camp']
show('A. never hit back (champion kill, no hit landed in the last 10 r), bag >= 10', [d for d in ck if not d['hit_back'] and d['bag'] >= 10],
     lambda d: f"killer {d['killer']} ({d['n_attackers10']} attackers, {d['n_taken10']} hits taken), bag {d['bag']}, hp5 {d['hp5']:.0%}, allies/enemies within 6 {d['al5']:.1f}/{d['en5']:.1f}, steps toward/away 8r {d['tw8']}/{d['aw8']}, farming {d['farming']}, stunned {d['stunned3']}")
show('B. dive deaths (2+ steps toward the nearest enemy at R < 0.67, dead within 8 r)', [d for d in DV if d['died8']],
     lambda d: f"R {d['ratio']}, target {d['target']}, bodies {d['n_own']} vs {d['n_en']}, hp {d['hp']:.0%}, killer {d['killer']}, bag {d['bag']}")
show('C. Marcella pattern (within 4 of her 3+ of the last 5 r, took her spell)', [d for d in ck if d['marcella_pattern']],
     lambda d: f"killer Marcella, killer distance 3 r before {d['kd3']}, steps toward the killer 4r {d['tw_killer4']}, hp5 {d['hp5']:.0%}, hit back {d['hit_back']}, bag {d['bag']}, R5 {d['pw5'] if d['pw5'] is None else round(d['pw5'], 2)}")
show('D. chase deaths (3+ steps after a target that kept its distance; killed by another body)', [c for c in CH if c['died10'] and not c['killer_is_target']],
     lambda c: f"target {c['target']}, steps {c['steps']}, d0 {c['d0']} -> {c['dend']}, enemies within 6 at start/end {c['n_en0']}/{c['n_en1']}, hp {c['hp']:.0%}, killer {c['killer']}")
show('E. burst from healthy (hp5 >= 60%) with no retreat step in the last 10 r', [d for d in ck if d['hp5'] is not None and d['hp5'] >= 0.6 and d['ret_r'] is None],
     lambda d: f"killer {d['killer']}, {d['n_attackers10']} attackers, R3 {d['pw3'] if d['pw3'] is None else round(d['pw3'], 2)}, allies/enemies {d['al5']:.1f}/{d['en5']:.1f}, stunned {d['stunned3']}, spell/dash in last 3 r {d['kinds3']}, bag {d['bag']}")
show('F. retreat started under 40% hp and caught (dead within 8 r)', [r for r in RT if r['hp'] < 0.4 and r['died8']],
     lambda r: f"hp {r['hp']:.0%}, enemies within 4 {r['en4']}, dash/stun ready vs us {r['dash4']}/{r['stun5']}, own dash ready {r['own_dash']} used {r['dash']}, toward ally {r['to_ally']}, pursued {r['pursued']}, R {r['pw_ratio'] if r['pw_ratio'] is None else round(r['pw_ratio'], 2)}, gems {r['gems']}")
show('G. died within 40 r of respawn', [d for d in D if d['age'] is not None and d['age'] <= 40],
     lambda d: f"age {d['age']}, killer {d['killer']}, allies/enemies {d['al5']}/{d['en5']}, hp5 {d['hp5']}, d_own {d['d_own']}")
show('H. killed by a camp the enemy woke', [d for d in D if d['camp_waker'] in ('enemy', 'both')],
     lambda d: f"killer {d['killer']}, camp hits 5r {d['camp_hits5']} ({d['camp_dmg5']} dmg), champ dmg 5r {d['champ_dmg5']}, enemies within 6 {d['en5']}, bag {d['bag']}")

# fights we opened at R < 0.67 and lost a body
lost = []
for f in F:
    g = G[f['mid']]
    if g['ver'] not in ('v84', 'v88') or f['first'] != g['we'] or not f['exchange']:
        continue
    if f['r_open'] is not None and f['r_open'] < 0.67 and f['dead'][str(g['we'])] > 0:
        lost.append({'mid': f['mid'], 't': g['we'], 'body': f['opener'], 'champ': f['opener_champ'], 'r': f['start'], 'bag': f['bag'][str(g['we'])], 'f': f})
show('I. exchanges we opened at R < 0.67 that cost a body', lost,
     lambda x: f"R {x['f']['r_open']:.2f}, approach {x['f']['approach']}, bodies {x['f']['num'][str(x['t'])]} vs {x['f']['num'][str(1 - x['t'])]}, opener hp {x['f']['a_hp']:.0%}, nearest ally {x['f']['a_ally']}, target {x['f']['target_champ']}, dead {x['f']['dead']}, gems lost {x['bag']}")
