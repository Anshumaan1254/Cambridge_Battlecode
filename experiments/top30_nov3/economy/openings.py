#!/usr/bin/env python3
"""Opening order (r1-150): which rule picks the team's first groups, how many bodies stack, time to kill; examples.

    python3 -I economy/openings.py > economy/openings.txt
    python3 -I economy/openings.py dump <map>   # per-game body sequences on one map (top30 games then ours)
"""
import json, sys
from collections import Counter, defaultdict
ECO = '/home/claude/cambridge_battlecode/experiments/top30_nov3/economy'


def load(name):
    return [json.loads(l) for l in open(f'{ECO}/rows_{name}.jsonl') if '"error"' not in l[:40]]


def mean(xs):
    xs = [x for x in xs if x is not None and x == x]
    return sum(xs) / len(xs) if xs else float('nan')


def team_sequence(r, horizon=150):
    """groups in the order the team first hits them (r1-horizon): [(gid, first_hit, bodies, kill, cap_team, val, d, rank)]"""
    first = {}
    bodies = defaultdict(set)
    info = {}
    for b, o in r['opening'].items():
        for v in o['visits']:
            if v['first'] > horizon:
                continue
            g = v['g']
            if g not in first or v['first'] < first[g]:
                first[g] = v['first']
            bodies[g].add(b)
            if g not in info or (v['kill'] and not info[g].get('kill')):
                info[g] = v
    out = []
    for g in sorted(first, key=lambda g: first[g]):
        v = info[g]
        out.append({'g': g, 'first': first[g], 'bodies': len(bodies[g]), 'kill': v['kill'], 'cap': v['cap_team'], 'val': v['val'], 'gems': v['gems'],
                    'gold': v['gold'], 'd': v['d'], 'd_enemy': v['d_enemy'], 'rank': v['rank'], 'types': v['types'], 'ttk': (v['kill'] - first[g]) if v['kill'] else None})
    return out


def rules(r):
    gs = [g for g in r['groups'] if g['d'] is not None and g['val'] > 0]
    if not gs:
        return {}
    own = [g for g in gs if g['d'] <= g['d_enemy']] or gs
    dmin = min(g['d'] for g in gs)
    R = {}
    R['nearest'] = min(gs, key=lambda g: (g['d'], -g['val']))['id']
    gem = [g for g in gs if g['gems'] > 0]
    R['nearest_gems'] = min(gem, key=lambda g: (g['d'], -g['val']))['id'] if gem else None
    R['richest_own_side'] = max(own, key=lambda g: (g['val'], -g['d']))['id']
    R['richest_gems_own_side'] = max(own, key=lambda g: (g['gems'], -g['d']))['id']
    R['richest_within_1.5xnear'] = max([g for g in gs if g['d'] <= 1.5 * dmin + 2], key=lambda g: (g['val'], -g['d']))['id']
    R['richest_within_2xnear'] = max([g for g in gs if g['d'] <= 2 * dmin + 2], key=lambda g: (g['val'], -g['d']))['id']
    R['best_val/(d+10)'] = max(gs, key=lambda g: g['val'] / (g['d'] + 10))['id']
    R['best_val/(d+25)'] = max(gs, key=lambda g: g['val'] / (g['d'] + 25))['id']
    R['best_gems/(d+10)'] = max(gs, key=lambda g: g['gems'] / (g['d'] + 10))['id']
    R['best_val/(d+10) own side'] = max(own, key=lambda g: g['val'] / (g['d'] + 10))['id']
    return R


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'dump':
        m = sys.argv[2]
        for name in ('top30', 'ours'):
            for r in load(name):
                if r['map'] != m or (name == 'ours' and r['ver'] not in ('v84', 'v85', 'v86', 'v87', 'v88')):
                    continue
                tag = 'US' if r.get('me') else ('OPP' if name == 'ours' else 'T30')
                print(f"\n== {name} {r['mid']} {tag} {r['name']} ({r['rating'] and round(r['rating'])}) {r['res']} side {r['team']} first cap r{r['first_cap']} gems150 {r['gems150']} gems300 {r['gems300']} shards300 {r['checks'].get('300', {}) and r['checks']['300']['shards']}")
                gl = sorted([g for g in r['groups'] if g['val'] > 0 and g['d'] is not None], key=lambda g: g['d'])
                print('  groups by d: ' + '; '.join(f"G{g['id']} {g['types']} {g['gems']}g/{g['gold']}$ d{g['d']}/{g['d_enemy']}" for g in gl[:10]))
                for b, o in r['opening'].items():
                    s = ' -> '.join(f"G{v['g']}[{v['types']} {v['gems']}g d{v['d']} #{v['rank']}] r{v['first']}-{v['last']}({v['n']})" + (f" kill r{v['kill']}" if v['kill'] else '') +
                                    (f" cap {v['cap_team']} r{v['cap_r']}" if v['cap_r'] else '') + (f" +{len(v['mates'])}" if v['mates'] else '') + (' CONTEST' if v['enemies'] else '')
                                    for v in o['visits'] if v['first'] <= 150)
                    print(f"  b{b} {o['champ'][:5]:5} {s or '(no hit)'}" + (f"  died {o['deaths150']}" if o['deaths150'] else ''))
        return
    T = load('top30')
    O = load('ours')
    US = [r for r in O if r['me'] and r['ver'] in ('v84', 'v85', 'v86', 'v87', 'v88')]
    sets = [('TOP30', T), ('US v84-v88', US), ('US v88', [r for r in US if r['ver'] == 'v88'])]
    print('== A. Which rule picks the team FIRST group (the group most of the team hits first; ties: earliest)? % of team-games')
    for lab, rows in sets:
        hit = Counter()
        n = 0
        for r in rows:
            seq = team_sequence(r)
            if not seq:
                continue
            # team first group = the group with most bodies among the first 2 groups hit, earliest first
            fg = max(seq[:2], key=lambda s: (s['bodies'], -s['first']))['g']
            R = rules(r)
            if not R:
                continue
            n += 1
            for k, v in R.items():
                hit[k] += (v == fg)
        print(f'-- {lab} (n={n})')
        for k, v in sorted(hit.items(), key=lambda x: -x[1]):
            print(f'   {k:32} {100.0 * v / n:5.1f}%')
    print('\n== B. Team first group: bodies on it, value, distance, time to kill, captured by own team; second group')
    for lab, rows in sets:
        S = defaultdict(list)
        for r in rows:
            seq = team_sequence(r)
            if not seq:
                continue
            s0 = seq[0]
            S['bodies on 1st group'].append(s0['bodies'])
            S['bodies on 1st group (of nbody)'].append(s0['bodies'] / r['nbody'])
            S['% 1st group has >= 3 bodies'].append(100.0 * (s0['bodies'] >= 3))
            S['% 1st group has all bodies'].append(100.0 * (s0['bodies'] >= r['nbody']))
            S['1st group value'].append(s0['val'])
            S['1st group gems'].append(s0['gems'])
            S['1st group d'].append(s0['d'])
            S['1st group rank'].append(s0['rank'])
            S['1st group first hit r'].append(s0['first'])
            S['1st group time to kill'].append(s0['ttk'])
            S['% 1st group killed'].append(100.0 * bool(s0['kill']))
            S['% 1st group captured by own'].append(100.0 * (s0['cap'] == 'own'))
            if len(seq) > 1:
                s1 = seq[1]
                S['2nd group bodies'].append(s1['bodies'])
                S['2nd group value'].append(s1['val'])
                S['2nd group d'].append(s1['d'])
                S['2nd group first hit r'].append(s1['first'])
                S['2nd group first - 1st kill (overlap<0)'].append((s1['first'] - s0['kill']) if s0['kill'] else None)
            S['groups hit by r150'].append(len(seq))
            S['groups killed by r150'].append(sum(1 for s in seq if s['kill']))
            S['% of hit groups killed'].append(100.0 * sum(1 for s in seq if s['kill']) / len(seq))
            S['mean bodies per group hit'].append(mean([s['bodies'] for s in seq]))
            S['mean ttk of killed groups'].append(mean([s['ttk'] for s in seq if s['kill']]))
            S['gems of groups killed by r150'].append(sum(s['gems'] for s in seq if s['kill']))
            S['gems killed & captured own by r150'].append(sum(s['gems'] for s in seq if s['kill'] and s['cap'] == 'own'))
            S['gems killed & captured by ENEMY by r150'].append(sum(s['gems'] for s in seq if s['kill'] and s['cap'] == 'enemy'))
        print(f'-- {lab} (n={len(S["bodies on 1st group"])})')
        for k, v in S.items():
            print(f'   {k:44} {mean(v):7.1f}')
    print('\n== C. Stacking by group value: bodies on the group vs its gems (visits r1-150)')
    for lab, rows in sets:
        by = defaultdict(list)
        for r in rows:
            for s in team_sequence(r):
                band = '<10g' if s['gems'] < 10 else '10-29g' if s['gems'] < 30 else '30-59g' if s['gems'] < 60 else '60g+'
                by[band].append((s['bodies'], s['ttk'], bool(s['kill'])))
        print(f'-- {lab}: ' + '; '.join(f"{b}: n={len(v)} bodies {mean([x[0] for x in v]):.2f} ttk {mean([x[1] for x in v]):.1f} killed {100 * mean([x[2] for x in v]):.0f}%" for b, v in sorted(by.items())))
    print('\n== D. Per-body first target by champion (top30): rank by distance and value')
    for lab, rows in sets[:2]:
        by = defaultdict(list)
        for r in rows:
            for b, o in r['opening'].items():
                if o['visits']:
                    v = o['visits'][0]
                    by[o['champ']].append((v['rank'], v['val'], v['d'], v['first'], len(v['mates']) + 1))
        print(f'-- {lab}')
        for c, v in sorted(by.items(), key=lambda x: -len(x[1])):
            print(f"   {c:12} n={len(v):4} rank {mean([x[0] for x in v]):.2f} val {mean([x[1] for x in v]):.0f} d {mean([x[2] for x in v]):.0f} first hit r{mean([x[3] for x in v]):.0f} bodies {mean([x[4] for x in v]):.2f}")


if __name__ == '__main__':
    main()
