#!/usr/bin/env python3
"""Tables: top-30 teams (rows_top30.jsonl, both teams of top-30 vs top-30 games) vs us (rows_ours.jsonl, me rows, v84-v88).

    python3 -I economy/compare.py > economy/tables.txt

Every table gives the pooled mean over rows and, where it matters, the map-matched mean: the mean over maps of the per-map
difference, each map weighted by min(n_top30, n_ours) (like for like: same map).
"""
import json, sys, os
from collections import Counter, defaultdict
ECO = os.environ.get('ECO', '/home/claude/cambridge_battlecode/experiments/top30_nov3/economy')
FAM = ['Monster', 'Power', 'Durab', 'Treasure', 'Jungle', 'Home', 'Bruiser', 'Tribute', 'Capture', 'Prospect', 'Hunter', 'Skirmish', 'Greed', 'Collect']
STATN = ['str', 'foc', 'hp']
PH = ['1-150', '151-400', '401-800', '801+']


def load(name):
    return [json.loads(l) for l in open(f'{ECO}/rows_{name}.jsonl') if '"error"' not in l[:40]]


def mean(xs):
    xs = [x for x in xs if x is not None and x == x]
    return sum(xs) / len(xs) if xs else float('nan')


def fmt(x, d=1):
    return 'nan' if x != x else f'{x:.{d}f}'


def matched(rows_a, rows_b, f):
    """map-matched mean of f over a and over b, weighted by min(n_a, n_b) per map; returns (mean_a, mean_b, nmaps, weight)"""
    by_a, by_b = defaultdict(list), defaultdict(list)
    for r in rows_a:
        v = f(r)
        if v is not None and v == v:
            by_a[r['map']].append(v)
    for r in rows_b:
        v = f(r)
        if v is not None and v == v:
            by_b[r['map']].append(v)
    sa = sb = w = 0.0
    n = 0
    for m in by_a:
        if m in by_b:
            wm = min(len(by_a[m]), len(by_b[m]))
            sa += wm * mean(by_a[m])
            sb += wm * mean(by_b[m])
            w += wm
            n += 1
    return (sa / w if w else float('nan'), sb / w if w else float('nan'), n, w)


def line(label, A, B, f, d=1, extra=None):
    ma, mb, n, w = matched(A, B, f)
    pa, pb = mean([f(r) for r in A]), mean([f(r) for r in B])
    s = f'{label:44} {fmt(pa, d):>8} {fmt(pb, d):>8} | {fmt(ma, d):>8} {fmt(mb, d):>8}  ({n} maps, w {w:.0f})'
    if extra:
        s += '  ' + extra
    print(s)


def phase_get(r, i, key):
    p = r['phases'][i]
    return None if p is None else p.get(key)


def per100(r, i, key):
    p = r['phases'][i]
    if p is None or p['rounds'] < 30:
        return None
    return 100.0 * p.get(key, 0) / p['rounds']


def share(r, i, st, contested=None):
    p = r['phases'][i]
    if p is None or p['brounds'] < 100:
        return None
    if contested is None:
        return 100.0 * p['st'].get(st, 0) / p['brounds']
    cb = sum(p['st_c'].values())
    if contested:
        return 100.0 * p['st_c'].get(st, 0) / cb if cb >= 20 else None
    ub = p['brounds'] - cb
    return 100.0 * (p['st'].get(st, 0) - p['st_c'].get(st, 0)) / ub if ub >= 20 else None


def main():
    T = load('top30')
    O = load('ours')
    US = [r for r in O if r['me'] and r['ver'] in ('v84', 'v85', 'v86', 'v87', 'v88')]
    US88 = [r for r in US if r['ver'] == 'v88']
    OPP = [r for r in O if not r['me'] and r['ver'] in ('v84', 'v85', 'v86', 'v87', 'v88')]
    print(f'rows: top30 {len(T)} ({len({r["mid"] for r in T})} games, {len({r["map"] for r in T})} maps); us {len(US)} games '
          f'({Counter(r["ver"] for r in US)}), {len({r["map"] for r in US})} maps; v88 {len(US88)}')
    print('top30 team rating mean', fmt(mean([r['rating'] for r in T]), 0), 'our opponents rating mean', fmt(mean([r['rating'] for r in OPP]), 0),
          '(rated opponents only: ', sum(1 for r in OPP if r['rating']), 'of', len(OPP), ')')
    print('columns: pooled top30 | pooled us || map-matched top30 | map-matched us')
    for lab, B in (('US v84-v88', US), ('US v88 only', US88)):
        print(f'\n################ {lab} (n={len(B)}) vs TOP-30 (n={len(T)})')
        print('\n== 1. FARMING PACE per 100 rounds (team of 5) by phase')
        for i, pn in enumerate(PH):
            print(f'-- phase {pn}')
            line('  camp hits /100r', T, B, lambda r, i=i: per100(r, i, 'hits'))
            line('  camp damage /100r', T, B, lambda r, i=i: per100(r, i, 'dmg'), 0)
            line('  gems captured /100r', T, B, lambda r, i=i: per100(r, i, 'gems'))
            line('  gold earned /100r', T, B, lambda r, i=i: per100(r, i, 'gold_earned'), 0)
            line('  captures (gem) /100r', T, B, lambda r, i=i: per100(r, i, 'ncap'), 2)
            line('  gems banked /100r', T, B, lambda r, i=i: per100(r, i, 'banked'))
            line('  gems lost on death /100r', T, B, lambda r, i=i: per100(r, i, 'lost'))
            line('  deaths /100r', T, B, lambda r, i=i: per100(r, i, 'deaths'), 2)
            line('  dmg per hit', T, B, lambda r, i=i: (r['phases'][i]['dmg'] / r['phases'][i]['hits']) if r['phases'][i] and r['phases'][i]['hits'] >= 10 else None)
            for st in ('hit', 'walk', 'wait', 'idle', 'capture', 'recall', 'bank', 'fight', 'spawn', 'dead'):
                line(f'  % body-rounds {st}', T, B, lambda r, i=i, st=st: share(r, i, st))
        print('\n== 2. FIRST CAPTURE AND EARLY CAPTURES')
        line('first capture round (gems)', T, B, lambda r: r['first_cap'], 0)
        line('first capture round (any)', T, B, lambda r: r['first_cap_any'], 0)
        line('gems captured by r150', T, B, lambda r: r['gems150'])
        line('gems captured by r300', T, B, lambda r: r['gems300'])
        line('gem captures by r150', T, B, lambda r: r['ncap150'], 2)
        line('gem captures by r300', T, B, lambda r: r['ncap300'], 2)
        line('first camp hit round (team min)', T, B, lambda r: min([v['first_hit'] for v in r['opening'].values() if v['first_hit']] or [None]), 0)
        line('first camp hit round (body mean)', T, B, lambda r: mean([v['first_hit'] for v in r['opening'].values() if v['first_hit']]), 0)
        line('bodies with no camp hit by r150', T, B, lambda r: sum(1 for v in r['opening'].values() if not v['first_hit']), 2)

        print('\n== 3. CONTESTED (enemy within 6 at round start) vs UNOPPOSED body-rounds, by phase: % of those body-rounds spent hitting a camp')
        for i, pn in enumerate(PH):
            line(f'  {pn} % contested body-rounds', T, B, lambda r, i=i: (100.0 * sum(r['phases'][i]['st_c'].values()) / r['phases'][i]['brounds']) if r['phases'][i] and r['phases'][i]['brounds'] >= 100 else None)
            line(f'  {pn} hit% | contested', T, B, lambda r, i=i: share(r, i, 'hit', True))
            line(f'  {pn} hit% | unopposed', T, B, lambda r, i=i: share(r, i, 'hit', False))
            line(f'  {pn} walk% | contested', T, B, lambda r, i=i: share(r, i, 'walk', True))
            line(f'  {pn} walk% | unopposed', T, B, lambda r, i=i: share(r, i, 'walk', False))
            line(f'  {pn} fight% | contested', T, B, lambda r, i=i: share(r, i, 'fight', True))
            line(f'  {pn} wait% | contested', T, B, lambda r, i=i: share(r, i, 'wait', True))
            line(f'  {pn} wait% | unopposed', T, B, lambda r, i=i: share(r, i, 'wait', False))
            line(f'  {pn} recall% | contested', T, B, lambda r, i=i: share(r, i, 'recall', True))
            line(f'  {pn} camp hits with enemy<=6 (% of hits)', T, B, lambda r, i=i: (100.0 * r['phases'][i]['hits_c'] / r['phases'][i]['hits']) if r['phases'][i] and r['phases'][i]['hits'] >= 10 else None)

        print('\n== 4. ITEMS AND SHOPS')
        for cr in ('150', '300', '600', '900'):
            line(f'shards (team) at r{cr}', T, B, lambda r, cr=cr: r['checks'][cr]['shards'] if r['checks'].get(cr) else None)
            line(f'shards per body at r{cr}', T, B, lambda r, cr=cr: mean(r['checks'][cr]['per_body']) if r['checks'].get(cr) else None)
            line(f'min body shards at r{cr}', T, B, lambda r, cr=cr: min(r['checks'][cr]['per_body']) if r['checks'].get(cr) else None)
            line(f'emblems (team) at r{cr}', T, B, lambda r, cr=cr: r['checks'][cr]['emblems'] if r['checks'].get(cr) else None, 2)
            line(f'gold unspent (team) at r{cr}', T, B, lambda r, cr=cr: r['checks'][cr]['gold'] if r['checks'].get(cr) else None, 0)
        line('first emblem round', T, B, lambda r: r['emblem_rounds'][0][0] if r['emblem_rounds'] else None, 0)
        line('second emblem round', T, B, lambda r: r['emblem_rounds'][1][0] if len(r['emblem_rounds']) > 1 else None, 0)
        line('emblems per game', T, B, lambda r: r['emblems_total'], 1)
        line('emblems per 1000 rounds', T, B, lambda r: 1000.0 * r['emblems_total'] / r['final'], 1)
        for cls in ('recall', 'walk', 'respawn', 'at-spawn', 'start'):
            line(f'shop trips per 1000r: {cls}', T, B, lambda r, cls=cls: 1000.0 * r['shops'].get(cls, 0) / r['final'], 2)
        line('shop trips per 1000r: all', T, B, lambda r: 1000.0 * sum(r['shops'].values()) / r['final'], 2)
        line('held recalls per 1000r', T, B, lambda r: 1000.0 * r['held_recalls'] / r['final'], 1)
        line('gold unspent at shop (mean of trips)', T, B, lambda r: mean([x[3] for x in r['shop_list'] if x[3] is not None]), 0)
        line('shards bought per trip', T, B, lambda r: (sum(q for b in r['builds'].values() for (rr, f, s, e, q) in b['seq'] if not e) / max(1, sum(r['shops'].values()))), 2)

        print('\n== 5. OPENING (r1-150): first target per body and stacking')
        def first_visits(r):
            return [v['visits'][0] for v in r['opening'].values() if v['visits']]
        line('first target: rank by distance (mean)', T, B, lambda r: mean([v['rank'] for v in first_visits(r)]), 2)
        line('first target: % rank 1 (nearest group)', T, B, lambda r: 100.0 * mean([v['rank'] == 1 for v in first_visits(r)]) if first_visits(r) else None)
        line('first target: % rank <= 2', T, B, lambda r: 100.0 * mean([v['rank'] <= 2 for v in first_visits(r)]) if first_visits(r) else None)
        line('first target: value (gems+0.5gold)', T, B, lambda r: mean([v['val'] for v in first_visits(r)]), 0)
        line('first target: gems', T, B, lambda r: mean([v['gems'] for v in first_visits(r)]), 0)
        line('first target: distance from spawn', T, B, lambda r: mean([v['d'] for v in first_visits(r)]), 0)
        line('first target: d_enemy - d_own (own side >0)', T, B, lambda r: mean([(v['d_enemy'] or 0) - (v['d'] or 0) for v in first_visits(r)]), 0)
        line('first target: % on own side (d < d_enemy)', T, B, lambda r: 100.0 * mean([(v['d'] or 0) < (v['d_enemy'] or 0) for v in first_visits(r)]) if first_visits(r) else None)
        line('first target: % richest within 1.5x nearest d', T, B, lambda r: 100.0 * mean([v['g'] == richest_near(r, 1.5) for v in first_visits(r)]) if first_visits(r) else None)
        line('first target: % best val/(d+10)', T, B, lambda r: 100.0 * mean([v['g'] == best_ratio(r) for v in first_visits(r)]) if first_visits(r) else None)
        line('first target: distinct groups / bodies', T, B, lambda r: len({v['g'] for v in first_visits(r)}) / len(first_visits(r)) if first_visits(r) else None, 2)
        line('first target: % all bodies on ONE group', T, B, lambda r: 100.0 * (len({v['g'] for v in first_visits(r)}) == 1) if len(first_visits(r)) >= 3 else None)
        line('first target: bodies on it (mates+1)', T, B, lambda r: mean([len(v['mates']) + 1 for v in first_visits(r)]), 2)
        line('first visit: rounds first hit -> kill', T, B, lambda r: mean([v['kill'] - v['first'] for v in first_visits(r) if v['kill']]), 1)
        line('first visit: % ending in a kill', T, B, lambda r: 100.0 * mean([bool(v['kill']) for v in first_visits(r)]) if first_visits(r) else None)
        line('first visit: % kill captured by own team', T, B, lambda r: 100.0 * mean([v['cap_team'] == 'own' for v in first_visits(r) if v['kill']]) if any(v['kill'] for v in first_visits(r)) else None)
        line('first visit: % contested by enemy bodies', T, B, lambda r: 100.0 * mean([bool(v['enemies']) for v in first_visits(r)]) if first_visits(r) else None)
        line('visits r1-150 per body', T, B, lambda r: mean([len(v['visits']) for v in r['opening'].values()]), 2)
        line('visits r1-150: bodies per visit', T, B, lambda r: mean([len(x['mates']) + 1 for v in r['opening'].values() for x in v['visits']]), 2)
        line('visits r1-150: % ending in a kill', T, B, lambda r: 100.0 * mean([bool(x['kill']) for v in r['opening'].values() for x in v['visits']]) if any(v['visits'] for v in r['opening'].values()) else None)
        line('visits r1-150: hits per visit', T, B, lambda r: mean([x['n'] for v in r['opening'].values() for x in v['visits']]), 1)
        line('kills r1-150 (team, distinct)', T, B, lambda r: len({(x['g'], x['kill']) for v in r['opening'].values() for x in v['visits'] if x['kill']}), 2)
        line('deaths r1-150', T, B, lambda r: sum(len(v['deaths150']) for v in r['opening'].values()), 2)

    # ---- 6. map class breakdown (US v84-v88 vs top30)
    print('\n\n== 6. MAP CLASS BREAKDOWN (US v84-v88 vs top30): camp hits /100r r1-400, gems captured /100r r1-800, shards at r300, first capture')
    def hits400(r):
        p = r['phases']
        if p[1] is None:
            return None
        rounds = p[0]['rounds'] + p[1]['rounds']
        return 100.0 * (p[0]['hits'] + p[1]['hits']) / rounds
    def gems800(r):
        p = r['phases']
        ps = [x for x in p[:3] if x]
        return 100.0 * sum(x['gems'] for x in ps) / sum(x['rounds'] for x in ps)
    def shards300(r):
        return r['checks']['300']['shards'] if r['checks'].get('300') else None
    classes = {
        'area < 2500': lambda r: r['mapclass']['area'] < 2500,
        'area 2500-5000': lambda r: 2500 <= r['mapclass']['area'] < 5000,
        'area >= 5000': lambda r: r['mapclass']['area'] >= 5000,
        'groups <= 8': lambda r: r['mapclass']['ngroups'] <= 8,
        'groups 9-14': lambda r: 9 <= r['mapclass']['ngroups'] <= 14,
        'groups >= 15': lambda r: r['mapclass']['ngroups'] >= 15,
        'monolith maps': lambda r: r['mapclass']['mono'],
        'no altar': lambda r: r['mapclass']['altars'] == 0,
        'big groups (>=30g) <= 2': lambda r: r['mapclass']['nbig'] <= 2,
        'big groups >= 6': lambda r: r['mapclass']['nbig'] >= 6,
    }
    print(f'{"class":28} {"n30/nus":>8} | {"hits400 t30/us":>16} | {"gems800 t30/us":>16} | {"shards300 t30/us":>16} | {"firstcap t30/us":>16}')
    for name, fn in classes.items():
        A = [r for r in T if fn(r)]
        B = [r for r in US if fn(r)]
        if not A or not B:
            continue
        s = f'{name:28} {len(A):>3}/{len(B):<4} |'
        for f in (hits400, gems800, shards300, lambda r: r['first_cap']):
            ma, mb, n, w = matched(A, B, f)
            s += f' {fmt(ma, 1):>7}/{fmt(mb, 1):<8}|'
        print(s)
    print('\n-- per map (maps with >= 3 rows on both sides), sorted by the camp-hit gap r1-400 (top30 - us)')
    by = defaultdict(lambda: {'T': [], 'U': []})
    for r in T:
        by[r['map']]['T'].append(r)
    for r in US:
        by[r['map']]['U'].append(r)
    out = []
    for m, d in by.items():
        if len(d['T']) >= 3 and len(d['U']) >= 3:
            out.append((mean([hits400(r) for r in d['T']]) - mean([hits400(r) for r in d['U']]), m, d))
    out.sort(reverse=True)
    print(f'{"map":24} {"n30/nus":>8} {"hits400":>14} {"gems800":>14} {"shards300":>14} {"firstcap":>12} {"win% us":>8} {"area":>6} {"groups":>6} {"gems":>5}')
    for gap, m, d in out:
        A, B = d['T'], d['U']
        print(f'{m:24} {len(A):>3}/{len(B):<4} {fmt(mean([hits400(r) for r in A])):>6}/{fmt(mean([hits400(r) for r in B])):<7} '
              f'{fmt(mean([gems800(r) for r in A])):>6}/{fmt(mean([gems800(r) for r in B])):<7} '
              f'{fmt(mean([shards300(r) for r in A]), 0):>6}/{fmt(mean([shards300(r) for r in B]), 0):<7} '
              f'{fmt(mean([r["first_cap"] for r in A]), 0):>5}/{fmt(mean([r["first_cap"] for r in B]), 0):<6} '
              f'{100.0 * mean([r["res"] == "W" for r in B]):>7.0f}% {A[0]["mapclass"]["area"]:>6} {A[0]["mapclass"]["ngroups"]:>6} {A[0]["mapclass"]["gems_total"]:>5}')


def richest_near(r, k):
    gs = [g for g in r['groups'] if g['d'] is not None and g['val'] > 0]
    if not gs:
        return None
    dmin = min(g['d'] for g in gs)
    cand = [g for g in gs if g['d'] <= k * dmin + 2]
    return max(cand, key=lambda g: (g['val'], -g['d']))['id']


def best_ratio(r):
    gs = [g for g in r['groups'] if g['d'] is not None and g['val'] > 0]
    if not gs:
        return None
    return max(gs, key=lambda g: g['val'] / (g['d'] + 10))['id']


if __name__ == '__main__':
    main()
