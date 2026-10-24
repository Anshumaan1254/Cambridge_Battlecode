# E3 verification: pbg Prism bag, big / finisher tributes, outcomes by closest enemy, cancels at ~6, what follows a cancel,
# opponents' disruption, locks, examples. Also Nyx / Pantheon Prisms for comparison.
import sys, os
from collections import defaultdict, Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vagg import *

G = load()


def prisms(g, t):
    return [int(b) for b, v in g['bodies'].items() if v[0] == t and v[1] == 'Prism']


for key in ('pbg', 'nyx', 'pantheon'):
    so = so_games(G, key)
    if not so:
        continue
    print(f'\n######## {key} (games {len(so)})')
    mx, share, ndone, games_with = [], [], [], 0
    big = []
    fin_starts = []
    for g, s in so:
        ps = prisms(g, s)
        if not ps:
            continue
        games_with += 1
        p = ps[0]
        mx.append(g['maxbag'][str(p)])
        tot = sum(c['gems'] for c in g['caps'] if c['team'] == s)
        mine = sum(c['gains'].get(str(p), [0, 0])[1] for c in g['caps'] if c['team'] == s)
        share.append((mine, tot))
        ndone.append(sum(1 for x in g['tribs'] if x['b'] == p and x['out'] == 'done'))
        for x in g['tribs']:
            if x['team'] == s and x['banked0'] + x['bag'] >= 1000:
                fin_starts.append((g['base'], x))
            if x['b'] == p and x['bag'] >= 100:
                big.append((g, s, x))
    print(f'Prism drafted in {games_with}/{len(so)}; max bag median {med(mx)} p75 {pct(mx, .75)} >=200 {mean([1 if m >= 200 else 0 for m in mx]):.0%} >=400 {mean([1 if m >= 400 else 0 for m in mx]):.0%}')
    print(f'Prism share of team captured gems {sum(a for a, b in share)/max(1,sum(b for a, b in share)):.0%}; completed tributes/game {mean(ndone):.2f}')
    print(f'finisher starts (any body; banked + bag >= 1000) per game {len(fin_starts)/len(so):.2f}, bag median {med([x["bag"] for _, x in fin_starts])}, games with one {len({b for b, _ in fin_starts})/len(so):.0%}')
    print(f'  finisher outcomes: {Counter(x["out"] for _, x in fin_starts)}')
    print(f'big Prism starts (bag>=100): {len(big)}; finisher share {mean([1 if x["banked0"] + x["bag"] >= 1000 else 0 for _, _, x in big]):.0%}; start r median {med([x["r0"] for _, _, x in big])}; ally within 4 whole channel {mean([1 if x["ally_all"] else 0 for _, _, x in big]):.0%}')
    cat = defaultdict(Counter)
    for g, s, x in big:
        m = x['mind']
        k = '>8' if m > 8 else ('7-8' if m >= 7 else ('5-6' if m >= 5 else '<=4'))
        cat[k][x['out']] += 1
    for k in ('>8', '7-8', '5-6', '<=4'):
        n = sum(cat[k].values())
        print(f'   closest enemy {k:4s}: n {n:3d} {dict(cat[k])}  done {cat[k]["done"]/max(1,n):.0%} cancel {cat[k]["cancel"]/max(1,n):.0%}')
    dc = Counter()
    for g, s, x in big:
        if x['out'] == 'cancel':
            dc[x['dend2'] if x['dend2'] is not None else x['dend']] += 1
    print('   enemy distance at the cancel (end of cancel round):', sorted(dc.items()))
    dc = Counter()
    for g, s, x in big:
        if x['out'] == 'cancel':
            dc[x['dend']] += 1
    print('   enemy distance at the cancel (end of previous round):', sorted(dc.items(), key=lambda t: (t[0] is None, t[0])))
    hits = [x.get('hit5') for g, s, x in big if x['out'] == 'cancel']
    print(f'   cancels followed by a hit on a champion within 5 rounds: {mean([1 if h else 0 for h in hits]):.0%} (n {len(hits)})')
    allc = [x for g, s in so for x in g['tribs'] if x['team'] == s and x['out'] == 'cancel']
    print(f'   all own cancels by the team {len(allc)}; with hit5 {mean([1 if x.get("hit5") else 0 for x in allc]):.0%}')
    # what follows big-bag own cancels with an enemy at 5-7
    fol = Counter()
    nb_r = []
    epis = defaultdict(list)
    for g, s, x in big:
        epis[g['base']].append((g, s, x))
    for g, s, x in big:
        if x['out'] != 'cancel':
            continue
        d = x['dend2'] if x['dend2'] is not None else x['dend']
        if d is None or not (5 <= d <= 7):
            continue
        fol['n'] += 1
        nb = x.get('next_bank')
        if nb and nb[1] >= 0.8 * x['bag']:
            fol['banked_later'] += 1
            nb_r.append(nb[0] - x['rend'])
        nd = x.get('next_death')
        if nd and nd[0] - x['rend'] <= 20:
            fol['prism_died20'] += 1
        ed = x.get('enemy_died20')
        if ed:
            fol['enemy_died20'] += 1
            if ed[1] == x['b']:
                fol['enemy_killed_by_prism'] += 1
        ds = x.get('enemy_d10') or []
        if len(ds) >= 5 and all(5 <= v <= 7 for v in ds[:5]):
            fol['enemy_stayed_5to7_5r'] += 1
        fol['team_won' if g['win'] == s else 'team_lost'] += 1
    print('   after own cancels with enemy at 5-7:', dict(fol), 'rounds to the later bank median', med(nb_r))
    # per game: big-bag episodes (restarts) and whether the bag was banked eventually, by game result
    eg = Counter()
    for base, lst in epis.items():
        g, s = lst[0][0], lst[0][1]
        anyc = any(x['out'] == 'cancel' for _, _, x in lst)
        anyd = any(x['out'] == 'done' for _, _, x in lst)
        eg[(('cancel' if anyc else 'nocancel'), ('done' if anyd else 'never'), 'W' if g['win'] == s else 'L')] += 1
    print('   games with big Prism starts: (any cancel, any done, result):', sorted(eg.items()))
    # disruption by opponents
    dis = Counter(x['out'] for g, s, x in big)
    print(f'   big Prism starts outcomes overall: {dict(dis)}')
    # locks
    lo = [len([l for l in g['locks'] if l['team'] == 1 - s]) for g, s in so]
    ls = [len([l for l in g['locks'] if l['team'] == s]) for g, s in so]
    ocanc = sum(1 for g, s in so for x in g['tribs'] if x['team'] == s and x['out'] == 'lock')
    print(f'   locks per game: by O {mean(lo):.2f}, by S {mean(ls):.2f}; S tributes ended by an O lock {ocanc} ({ocanc/max(1,sum(lo)):.0%} of O locks)')
    # wins on gems ending with a tribute >= 100
    endb = []
    for g, s in so:
        if g['win'] != s or g['endReason'] != 'gems':
            continue
        dn = [x for x in g['tribs'] if x['team'] == s and x['out'] == 'done']
        if dn:
            last = max(dn, key=lambda x: x['rend'] or 0)
            endb.append(last['got'] or last['bag'])
    print(f'   wins on gems: {len(endb)}; ended by a tribute >= 100: {mean([1 if b >= 100 else 0 for b in endb]):.0%}; game-ending bag median {med(endb)}')

print('\n== examples ==')
for g in G:
    if g['base'].startswith('00quadrants_46848e89') or g['base'].startswith('01gold_rush_2376a4f9'):
        s = g['keys'].get('pbg')
        print(g['base'], 'teams', [t['name'] for t in g['teams']], 'win', g['win'], 'pbg', s, 'sub', g['sub'], 'final', g['final'])
        for x in g['tribs']:
            if x['bag'] >= 100:
                print('   ', {k: x.get(k) for k in ('b', 'type', 'team', 'r0', 'bag', 'banked0', 'out', 'rend', 'got', 'mind', 'dend', 'dend2', 'enemy', 'next_bank', 'enemy_d10')})
