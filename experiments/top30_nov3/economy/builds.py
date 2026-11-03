#!/usr/bin/env python3
"""Builds and shops by champion: top-30 vs us.   python3 -I economy/builds.py > economy/builds.txt"""
import json, sys, os
from collections import Counter, defaultdict
ECO = os.environ.get('ECO', '/home/claude/cambridge_battlecode/experiments/top30_nov3/economy')
FAM = ['Monster', 'Power', 'Durab', 'Treasure', 'Jungle', 'Home', 'Bruiser', 'Tribute', 'Capture', 'Prospect', 'Hunter', 'Skirmish', 'Greed', 'Collect']
ST = ['str', 'foc', 'hp']


def load(name):
    return [json.loads(l) for l in open(f'{ECO}/rows_{name}.jsonl') if '"error"' not in l[:40]]


def mean(xs):
    xs = [x for x in xs if x is not None and x == x]
    return sum(xs) / len(xs) if xs else float('nan')


def main():
    T = load('top30')
    O = load('ours')
    US = [r for r in O if r['me'] and r['ver'] in ('v84', 'v85', 'v86', 'v87', 'v88')]
    for lab, rows in (('TOP30', T), ('US v84-v88', US)):
        print(f'\n################ {lab} ({len(rows)} team-games)')
        per = defaultdict(lambda: {'n': 0, 'e1': Counter(), 'e2': Counter(), 'e3': Counter(), 'fam20': Counter(), 'stat20': Counter(), 'sh150': [], 'sh300': [], 'sh600': [],
                                   'e1r': [], 'e2r': [], 'gold300': [], 'gold600': [], 'nemb': [], 'first_shop': [], 'trip_size': []})
        for r in rows:
            bodies = {int(b): o['champ'] for b, o in r['opening'].items()}
            idx = sorted(bodies)
            for b, bd in r['builds'].items():
                c = bd['champ']
                p = per[c]
                p['n'] += 1
                emb = [(rr, f, s) for (rr, f, s, e, q) in bd['seq'] if e]
                for k, key in enumerate(('e1', 'e2', 'e3')):
                    if len(emb) > k:
                        p[key][f'{FAM[emb[k][1]]}-{ST[emb[k][2]]}'] += 1
                    else:
                        p[key]['(none)'] += 1
                if emb:
                    p['e1r'].append(emb[0][0])
                if len(emb) > 1:
                    p['e2r'].append(emb[1][0])
                p['nemb'].append(len(emb))
                n = 0
                for (rr, f, s, e, q) in bd['seq']:
                    if n >= 20:
                        break
                    w = q * (5 if e else 1)
                    p['fam20'][FAM[f]] += w
                    p['stat20'][ST[s]] += w
                    n += w
                if bd['seq']:
                    p['first_shop'].append(bd['seq'][0][0])
                bi = idx.index(int(b)) if int(b) in idx else None
                for cr, key in (('150', 'sh150'), ('300', 'sh300'), ('600', 'sh600')):
                    ck = r['checks'].get(cr)
                    if ck and bi is not None and bi < len(ck['per_body']):
                        p[key].append(ck['per_body'][bi])
            # gold unspent per body at r300/600 from shop_list is not per body; use checks (team) / nbody
            for cr, key in (('300', 'gold300'), ('600', 'gold600')):
                ck = r['checks'].get(cr)
                if ck:
                    per['_team'][key].append(ck['gold'])
            per['_team']['trip_size'].append(sum(q for b in r['builds'].values() for (rr, f, s, e, q) in b['seq'] if not e) / max(1, sum(r['shops'].values())))
        for c, p in sorted(per.items(), key=lambda x: -x[1]['n']):
            if c == '_team':
                print(f"  TEAM gold unspent r300 {mean(p['gold300']):.0f} r600 {mean(p['gold600']):.0f}; shards per shop trip {mean(p['trip_size']):.2f}")
                continue
            tot = sum(p['fam20'].values()) or 1
            print(f"\n  {c} (n={p['n']}): shards/body r150 {mean(p['sh150']):.1f} r300 {mean(p['sh300']):.1f} r600 {mean(p['sh600']):.1f}; first shop r{mean(p['first_shop']):.0f}; "
                  f"emblem1 r{mean(p['e1r']):.0f} emblem2 r{mean(p['e2r']):.0f}; emblems/game {mean(p['nemb']):.1f}")
            print('     first 20 shards by family: ' + ', '.join(f'{k} {100 * v / tot:.0f}%' for k, v in p['fam20'].most_common(6)) +
                  ' | by stat: ' + ', '.join(f'{k} {100 * v / tot:.0f}%' for k, v in p['stat20'].most_common()))
            for key in ('e1', 'e2', 'e3'):
                print(f'     {key}: ' + ', '.join(f'{k} {100 * v / p["n"]:.0f}%' for k, v in p[key].most_common(5)))


if __name__ == '__main__':
    main()
