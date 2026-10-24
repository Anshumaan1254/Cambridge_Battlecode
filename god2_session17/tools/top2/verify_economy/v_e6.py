# E6 verification: every team's Vesper Vale: share of team gold, gold per game, capture / kill gold shares, captures and gems
# taken, solo captures, gems by class / zone, tributes, deaths, gems lost; controls for team size and map; examples.
import sys, os
from collections import defaultdict, Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vagg import *

G = load()


def earned(src):
    return sum(v for k, v in src.items() if not k.startswith('spent'))


def vesper_rows(pairs):
    rows = []
    for g, t in pairs:
        vs = [int(b) for b, v in g['bodies'].items() if v[0] == t and v[1] == 'VesperVale']
        if not vs:
            continue
        v = vs[0]
        nb = sum(1 for b, x in g['bodies'].items() if x[0] == t)
        team_gold = sum(earned(g['goldsrc'].get(b, {})) for b, x in g['bodies'].items() if x[0] == t)
        vg = earned(g['goldsrc'].get(str(v), {}))
        cap_t = sum(g['goldsrc'].get(b, {}).get('capture', 0) for b, x in g['bodies'].items() if x[0] == t)
        kill_t = sum(g['goldsrc'].get(b, {}).get('kill', 0) for b, x in g['bodies'].items() if x[0] == t)
        caps_t = [c for c in g['caps'] if c['team'] == t]
        mine = [c for c in caps_t if str(v) in c['gains']]
        gems_t = sum(c['gems'] for c in caps_t)
        gems_v = sum(c['gains'][str(v)][1] for c in mine)
        bycls = Counter()
        byzone = Counter()
        for c in mine:
            bycls[c['cls']] += c['gains'][str(v)][1]
            byzone[c['zone']] += c['gains'][str(v)][1]
        tr = [x for x in g['tribs'] if x['b'] == v and x['out'] == 'done']
        dth = [d for d in g['deaths'] if d['who'] == v]
        rows.append({'g': g, 't': t, 'nb': nb, 'share': vg / team_gold if team_gold else None, 'vg': vg, 'team_gold': team_gold,
                     'capsh': g['goldsrc'].get(str(v), {}).get('capture', 0) / cap_t if cap_t else None,
                     'killsh': g['goldsrc'].get(str(v), {}).get('kill', 0) / kill_t if kill_t else None,
                     'capn': len(mine), 'capn_t': len(caps_t), 'solo': sum(1 for c in mine if c['n'] == 1), 'gems_v': gems_v, 'gems_t': gems_t,
                     'bycls': bycls, 'byzone': byzone, 'trib': len(tr), 'bags': [x['got'] for x in tr if x['got']], 'deaths': len(dth),
                     'lost': sum(d['bag'] for d in dth), 'final': g['final'], 'map': g['map'], 'win': g['win'] == t})
    return rows


def show(lab, rows):
    if not rows:
        return
    gv = sum(r['gems_v'] for r in rows)
    cls = Counter()
    zn = Counter()
    for r in rows:
        cls.update(r['bycls'])
        zn.update(r['byzone'])
    print(f"{lab:22s} n {len(rows):3d} team size {mean([r['nb'] for r in rows]):.1f} | gold share {sum(r['vg'] for r in rows)/sum(r['team_gold'] for r in rows):.0%} (mean {mean([r['share'] for r in rows]):.0%})"
          f" gold/game {mean([r['vg'] for r in rows]):5.0f} team gold/game {mean([r['team_gold'] for r in rows]):5.0f} | cap-gold sh {mean([r['capsh'] for r in rows]):.0%} kill-gold sh {mean([r['killsh'] for r in rows]):.0%}"
          f" | captures {sum(r['capn'] for r in rows)/max(1,sum(r['capn_t'] for r in rows)):.0%} gems {gv/max(1,sum(r['gems_t'] for r in rows)):.0%} solo {sum(r['solo'] for r in rows)/max(1,sum(r['capn'] for r in rows)):.0%}"
          f" | elk {cls['elk']/max(1,gv):.0%} mono {cls['monolith']/max(1,gv):.0%} wolf {cls['wolf']/max(1,gv):.0%} | mid {zn['mid']/max(1,gv):.0%} own {zn['own']/max(1,gv):.0%}"
          f" | trib/game {mean([r['trib'] for r in rows]):.1f} bag med {med([b for r in rows for b in r['bags']])} rounds/bank {sum(r['final'] for r in rows)/max(1,sum(r['trib'] for r in rows)):.0f}"
          f" | deaths/game {mean([r['deaths'] for r in rows]):.2f} gems lost/game {mean([r['lost'] for r in rows]):.0f}")


print('== every Vesper, S teams and their opponents ==')
allO = []
for k in KEYS:
    so = so_games(G, k)
    if not so:
        continue
    S = vesper_rows([(g, s) for g, s in so])
    O = vesper_rows([(g, 1 - s) for g, s in so])
    show(k + ' S', S)
    show(k + ' O', O)
    if k == 'ifish':
        ifS, ifO = S, O
# distinct-match pooled non-ifish Vespers
seen = set()
pool = []
for g in G:
    for t in (0, 1):
        if g['keys'].get('ifish') == t:
            continue
        pool.append((g, t))
P = vesper_rows(pool)
show('all non-ifish Vespers', P)

print('\n== controls: ifish Vesper vs other Vespers by team size and same maps ==')
for nb in sorted({r['nb'] for r in ifS}):
    a = [r for r in ifS if r['nb'] == nb]
    b = [r for r in P if r['nb'] == nb]
    print(f"team size {nb}: ifish n {len(a)} share {sum(r['vg'] for r in a)/max(1,sum(r['team_gold'] for r in a)):.0%} | others n {len(b)} share {sum(r['vg'] for r in b)/max(1,sum(r['team_gold'] for r in b)):.0%}")
maps = {r['map'] for r in ifS}
b = [r for r in P if r['map'] in maps]
print(f"others on ifish's maps: n {len(b)} share {sum(r['vg'] for r in b)/max(1,sum(r['team_gold'] for r in b)):.0%}")
# same-game opponent Vesper
pair = []
for r in ifS:
    o = [x for x in ifO if x['g'] is r['g']]
    if o:
        pair.append((r['share'], o[0]['share']))
print(f"games where both teams drafted Vesper: n {len(pair)}; ifish Vesper share {mean([p[0] for p in pair]):.0%} vs opp Vesper {mean([p[1] for p in pair]):.0%}; ifish higher in {mean([1 if p[0] > p[1] else 0 for p in pair]):.0%}")
# ifish Vesper share in wins vs losses
print(f"ifish Vesper share: wins {mean([r['share'] for r in ifS if r['win']]):.0%} (n {sum(1 for r in ifS if r['win'])}), losses {mean([r['share'] for r in ifS if not r['win']]):.0%}")
# ifish team draft composition
comp = Counter(tuple(sorted(r['g']['teams'][r['t']]['picks'])) for r in ifS)
print('ifish drafts (top):', comp.most_common(5))
# Vesper capture share by class and round window (ifish)
print('\n== ifish: share of the team captures taken by the Vesper, by class and window ==')
win = [(0, 200), (200, 500), (500, 1000), (1000, 3000)]
for cls in ('elk', 'wolf', 'gold', 'gem', 'golem', 'monolith'):
    cells = []
    for lo, hi in win:
        n = v = 0
        for r in ifS:
            vs = [b for b, x in r['g']['bodies'].items() if x[0] == r['t'] and x[1] == 'VesperVale'][0]
            for c in r['g']['caps']:
                if c['team'] == r['t'] and c['cls'] == cls and lo <= c['r'] < hi:
                    n += 1
                    v += vs in c['gains']
        cells.append(f'{v}/{n} ({v/max(1,n):.0%})')
    print(f'  {cls:9s} ' + ' | '.join(cells))

print('\n== examples ==')
for r in ifS:
    for pre in ('00contest_16309139', '00interlock_c440041c'):
        if r['g']['base'].startswith(pre):
            g = r['g']
            vs = [int(b) for b, x in g['bodies'].items() if x[0] == r['t'] and x[1] == 'VesperVale'][0]
            tr = [(x['r0'], x['got']) for x in g['tribs'] if x['b'] == vs and x['out'] == 'done']
            print(pre, 'Vesper gold share', f"{r['share']:.0%}", 'tributes', tr, 'win', r['win'], 'sub', g['sub'])
