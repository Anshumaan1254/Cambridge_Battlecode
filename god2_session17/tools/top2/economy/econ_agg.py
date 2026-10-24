# an_economy stage 2: tables from tools/top2/economy/econ_game.py output (C:/battlecode/cache/t2econ/games_<KEY>.jsonl).
#   python tools/top2/economy/econ_agg.py [KEY...] > C:/battlecode/cache/t2econ/agg.txt
# S = the study team, O = its opponents in the same games; W / L = winner / loser of a game (pooled over every distinct match).
import json, sys, statistics, collections, math
from collections import defaultdict, Counter

CACHE = 'C:/battlecode/cache'
KEYS = sys.argv[1:] or ['pbg', 'ifish', 'pantheon', 'coo', 'cm', 'nyx']
CP = [100, 200, 300, 400, 500, 600, 800, 1000, 1200, 1500, 2000]


def med(a):
    a = [x for x in a if x is not None]
    return statistics.median(a) if a else None


def mean(a):
    a = [x for x in a if x is not None]
    return sum(a) / len(a) if a else None


def q(a, p):
    a = sorted(x for x in a if x is not None)
    if not a:
        return None
    k = (len(a) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return a[lo] + (a[hi] - a[lo]) * (k - lo)


def f(x, d=1):
    if x is None:
        return '-'
    if isinstance(x, float):
        return f'{x:.{d}f}'
    return str(x)


def pct(n, d):
    return '-' if not d else f'{100.0 * n / d:.0f}%'


def load(keys):
    G = {}
    for k in keys:
        try:
            G[k] = [json.loads(l) for l in open(f'{CACHE}/t2econ/games_{k}.jsonl', encoding='utf-8')]
        except FileNotFoundError:
            G[k] = []
    return G


def zrel(c_zone):
    return c_zone


def table(head, rows):
    print('| ' + ' | '.join(head) + ' |')
    print('|' + '---|' * len(head))
    for r in rows:
        print('| ' + ' | '.join(f(x) if not isinstance(x, str) else x for x in r) + ' |')
    print()


def side(g, t):
    return g['teams'][str(t)] if str(t) in g['teams'] else g['teams'][t]


def per_team_game(g, t):
    """economy numbers of team t in game g"""
    T = side(g, t)
    fin = g['final']
    o = {}
    inc = T['inc']
    o['cap'] = inc.get('cap', 0)
    o['kill'] = inc.get('kill', 0)
    o['mg'] = inc.get('bankgold', 0)
    o['earn'] = o['cap'] + o['kill'] + o['mg'] + inc.get('other', 0)
    o['spend'] = inc.get('spend', 0)
    o['earn100'] = 100 * o['earn'] / fin
    caps = [c for c in g['caps'] if c['t'] == t]
    o['ncap'] = len(caps)
    o['capgems'] = sum(c['gems'] for c in caps)
    o['capgold'] = sum(c['gold'] for c in caps)
    for z in ('own', 'mid', 'enemy'):
        o['gems_' + z] = sum(c['gems'] for c in caps if c['zone'] == z)
        o['n_' + z] = sum(1 for c in caps if c['zone'] == z)
        o['gold_' + z] = sum(c['gold'] for c in caps if c['zone'] == z)
    o['midshare'] = o['gems_mid'] / o['capgems'] if o['capgems'] else None
    mids = [c['r'] for c in caps if c['zone'] == 'mid']
    o['firstmid'] = min(mids) if mids else None
    o['firstcap'] = min((c['r'] for c in caps), default=None)
    o['steals'] = T.get('steals', 0)
    dl = [d for d in g['deaths'] if d['t'] == t]
    o['deaths'] = len(dl)
    o['lost'] = sum(d['bag'] for d in dl)
    o['lostCamp'] = sum(d['bag'] for d in dl if d['killer'] == -1)
    o['bigLost'] = max((d['bag'] for d in dl), default=0)
    o['banked'] = T['subFinal']
    o['carried'] = T['carriedEnd']
    o['sub'] = T['sub']
    o['reach'] = T['reach']
    o['maxbag'] = max(T['maxBag'].values()) if T['maxBag'] else 0
    tr = [x for x in g['tribs'] if x['t'] == t]
    o['tstart'] = len(tr)
    done = [x for x in tr if x['res'] == 'done']
    o['tdone'] = len(done)
    o['firstbank'] = min((x['rEnd'] for x in done), default=None)
    o['bags'] = [x['banked'] for x in done]
    o['fail'] = Counter(x['res'] for x in tr if x['res'] not in ('done', 'open'))
    o['_t'] = t
    o['spendCP'] = T['spendCP']
    o['incCP'] = T['incCP']
    o['maxHpCP'] = T['maxHpCP']
    return o


def overview(G):
    print('## Overview (S = study team, O = its opponents in the same games)\n')
    rows = []
    for k, gs in G.items():
        if not gs:
            continue
        n = len(gs)
        w = sum(1 for g in gs if g['win'] == g['S'])
        fw = med([g['final'] for g in gs if g['win'] == g['S']])
        fl = med([g['final'] for g in gs if g['win'] != g['S']])
        S = [per_team_game(g, g['S']) for g in gs]
        O = [per_team_game(g, 1 - g['S']) for g in gs]
        r1000 = med([s['reach']['1000'] for s, g in zip(S, gs) if g['win'] == g['S'] and s['reach'].get('1000')])
        rows.append([k, n, pct(w, n), fw, fl, f'{f(med([s["sub"][2] for s in S]))} / {f(med([s["sub"][2] for s in O]))}',
                     f'{f(med([s["sub"][5] for s in S]))} / {f(med([s["sub"][5] for s in O]))}',
                     f'{f(med([s["sub"][7] for s in S]))} / {f(med([s["sub"][7] for s in O]))}', r1000])
    table(['team', 'games', 'S win', 'final round (S wins)', '(S losses)', 'banked r300 S / O (median)', 'r600', 'r1000', 'S reaches 1000 (median round, wins)'], rows)


def gold(G):
    print('## Gold income and spend (per game means; per 100 rounds in brackets)\n')
    rows = []
    for k, gs in G.items():
        if not gs:
            continue
        for lab, tt in (('S', lambda g: g['S']), ('O', lambda g: 1 - g['S'])):
            X = [per_team_game(g, tt(g)) for g in gs]
            fin = [g['final'] for g in gs]
            e = mean([x['earn'] for x in X])
            r = lambda key: mean([100 * x[key] / fn for x, fn in zip(X, fin)])
            e300 = mean([sum(x['incCP'][s][2] for s in x['incCP']) for x, g in zip(X, gs) if g['final'] >= 300])
            e600 = mean([sum(x['incCP'][s][5] for s in x['incCP']) for x, g in zip(X, gs) if g['final'] >= 600])
            k300 = mean([x['incCP'].get('kill', [0] * 11)[2] for x, g in zip(X, gs) if g['final'] >= 300])
            shares = [mean([x['cap'] / x['earn'] for x in X if x['earn']]), mean([x['kill'] / x['earn'] for x in X if x['earn']]), mean([x['mg'] / x['earn'] for x in X if x['earn']])]
            rows.append([f'{k} {lab}', f'{f(e, 0)} ({f(r("earn"))})', f(e300, 0), f(e600, 0), f(k300, 0),
                         '/'.join(f(100 * s, 0) for s in shares), f(mean([x['spend'] / x['earn'] for x in X if x['earn']]), 2),
                         f(mean([x['maxHpCP'][2] for x, g in zip(X, gs) if g['final'] >= 300]), 0),
                         f(mean([x['maxHpCP'][5] for x, g in zip(X, gs) if g['final'] >= 600]), 0)])
    table(['team', 'gold earned / game (per 100 r)', 'earned by r300', 'by r600', 'kill gold by r300', 'capture / kill / Marcella-bank share %', 'spent / earned', 'team max-hp r300', 'r600'], rows)


def captures(G):
    print('## Captures by zone (per game means; zone relative to the capturing team, walking distance)\n')
    rows = []
    for k, gs in G.items():
        if not gs:
            continue
        for lab, tt in (('S', lambda g: g['S']), ('O', lambda g: 1 - g['S'])):
            X = [per_team_game(g, tt(g)) for g in gs]
            rows.append([f'{k} {lab}', f(mean([x['ncap'] for x in X])), f(mean([x['capgems'] for x in X]), 0),
                         f'{f(mean([x["gems_own"] for x in X]), 0)} / {f(mean([x["gems_mid"] for x in X]), 0)} / {f(mean([x["gems_enemy"] for x in X]), 0)}',
                         f'{f(mean([x["n_own"] for x in X]))} / {f(mean([x["n_mid"] for x in X]))} / {f(mean([x["n_enemy"] for x in X]))}',
                         f(mean([x['midshare'] for x in X]), 2), f(med([x['firstcap'] for x in X]), 0), f(med([x['firstmid'] for x in X]), 0),
                         f(mean([x['capgold'] for x in X]), 0)])
    table(['team', 'captures', 'captured gems', 'gems own / mid / enemy', 'captures own / mid / enemy', 'mid share of gems', 'first capture (median r)', 'first mid capture', 'capture gold'], rows)


def gemflow(G):
    print('## Gem flow per game (means)\n')
    rows = []
    for k, gs in G.items():
        if not gs:
            continue
        for lab, tt in (('S', lambda g: g['S']), ('O', lambda g: 1 - g['S'])):
            X = [per_team_game(g, tt(g)) for g in gs]
            rows.append([f'{k} {lab}', f(mean([x['capgems'] for x in X]), 0), f(mean([x['steals'] for x in X]), 0), f(mean([x['banked'] for x in X]), 0),
                         f(mean([x['lost'] for x in X]), 0), f(mean([x['lostCamp'] for x in X]), 0), f(mean([x['carried'] for x in X]), 0),
                         f(mean([x['deaths'] for x in X])), f(med([x['maxbag'] for x in X]), 0), f(mean([x['bigLost'] for x in X]), 0)])
    table(['team', 'captured', 'stolen by kills', 'banked (final)', 'lost on death', 'of which to camps', 'carried at end', 'deaths', 'biggest bag (median game)', 'biggest bag lost (mean)'], rows)


def banking(G):
    print('## Banking (tributes; per game means unless marked)\n')
    rows = []
    for k, gs in G.items():
        if not gs:
            continue
        for lab, tt in (('S', lambda g: g['S']), ('O', lambda g: 1 - g['S'])):
            X = [per_team_game(g, tt(g)) for g in gs]
            bags = [b for x in X for b in x['bags']]
            tribs = [tr for g in gs for tr in g['tribs'] if tr['t'] == tt(g)]
            done = [tr for tr in tribs if tr['res'] == 'done']
            big = sum(b for b in bags if b >= 100)
            fails = Counter()
            for x in X:
                fails.update(x['fail'])
            nf = sum(fails.values())
            un = [tr.get('usedNearest') for tr in done if tr.get('usedNearest') is not None]
            caw = [tr.get('capAltarWalk') for tr in done if tr.get('capAltarWalk') is not None]
            zones = Counter(('own' if tr['altarF'] < 0.4 else 'enemy' if tr['altarF'] > 0.6 else 'mid') for tr in done if tr.get('altarF') is not None)
            nz = sum(zones.values())
            esc = sum(1 for tr in done if tr['allies4'] > 0)
            en = sum(1 for tr in tribs if tr['emax6'] > 0)
            rows.append([f'{k} {lab}', f(mean([x['tstart'] for x in X])), f(mean([x['tdone'] for x in X])), f(med([x['firstbank'] for x in X]), 0),
                         f'{f(med(bags), 0)} / {f(mean(bags), 0)} / {f(q(bags, 0.9), 0)}', pct(big, sum(bags)),
                         pct(sum(un), len(un)), f(med(caw), 0),
                         f'{pct(zones["own"], nz)} / {pct(zones["mid"], nz)} / {pct(zones["enemy"], nz)}',
                         f(med([tr.get('altarSpawn') for tr in done]), 0), pct(esc, len(done)), pct(en, len(tribs)),
                         f'{pct(nf, len(tribs))} ({", ".join(f"{a} {b}" for a, b in fails.most_common())})'])
    table(['team', 'tribute starts', 'completed', 'first bank (median r)', 'bag median / mean / p90', 'banked gems in bags >= 100', 'used the altar nearest the last capture',
           'last capture -> altar walk (median)', 'altar zone own / mid / enemy', 'altar walk from spawn (median)', 'ally within 4 at start', 'enemy within 6 during channel', 'failed starts (causes)'], rows)


def carriers(G):
    print('## Who carries and banks (share of the team\'s banked gems by champion; mean max bag per body-game)\n')
    for k, gs in G.items():
        if not gs:
            continue
        for lab, tt in (('S', lambda g: g['S']), ('O', lambda g: 1 - g['S'])):
            banked = Counter()
            maxb = defaultdict(list)
            capg = Counter()
            ngame = Counter()
            for g in gs:
                t = tt(g)
                T = side(g, t)
                for tr in g['tribs']:
                    if tr['t'] == t and tr['res'] == 'done':
                        banked[tr['type']] += tr['banked']
                for b, m in T['maxBag'].items():
                    maxb[T['bodyType'][b]].append(m)
                    ngame[T['bodyType'][b]] += 1
                for c in g['caps']:
                    if c['t'] == t:
                        for ty, gm, gd in c['whoGems']:
                            capg[ty] += gm
            tot = sum(banked.values())
            ctot = sum(capg.values())
            s = ', '.join(f'{ty} {pct(v, tot)} (cap {pct(capg[ty], ctot)}, max bag {f(mean(maxb[ty]), 0)}, n {ngame[ty]})' for ty, v in banked.most_common())
            print(f'- {k} {lab}: {s}')
    print()


def deaths_bags(G):
    print('## Deaths with bags\n')
    rows = []
    for k, gs in G.items():
        if not gs:
            continue
        for lab, tt in (('S', lambda g: g['S']), ('O', lambda g: 1 - g['S'])):
            D = [d for g in gs for d in g['deaths'] if d['t'] == tt(g)]
            n = len(gs)
            withbag = [d for d in D if d['bag'] > 0]
            big = [d for d in D if d['bag'] >= 100]
            rows.append([f'{k} {lab}', f(len(D) / n), f(len(withbag) / n), f(sum(d['bag'] for d in D) / n, 0), f(len(big) / n, 2),
                         f(sum(d['bag'] for d in big) / n, 0), ', '.join(f'{a} {b}' for a, b in Counter(d['type'] for d in big).most_common(4)),
                         ', '.join(f'{a} {b}' for a, b in Counter(d['zone'] for d in D).most_common())])
    table(['team', 'deaths / game', 'with a bag', 'gems lost / game', 'deaths with bag >= 100 / game', 'gems lost in those', 'who (bag >= 100)', 'death zones'], rows)


def cycles(G):
    print('## Farming cycles (groups captured; medians in rounds: respawn->first hit (wait) / first hit->dead (kill) / dead->capture (cap); opening cycles excluded)\n')
    rows = []
    for k, gs in G.items():
        if not gs:
            continue
        for lab, tt in (('S', lambda g: g['S']), ('O', lambda g: 1 - g['S'])):
            byz = defaultdict(lambda: defaultdict(list))
            contested = Counter()
            for g in gs:
                t = tt(g)
                for c in g['cycles']:
                    if c['end'] != 'cap' or c['capT'] != t:
                        continue
                    f0 = c['f0'] if t == 0 else 1 - c['f0']
                    z = 'own' if f0 < 0.4 else 'enemy' if f0 > 0.6 else 'mid'
                    contested[z, 'n'] += 1
                    if c['hc'][1 - t] > 0:
                        contested[z, 'c'] += 1
                    if c['hitT'] == 1 - t:
                        contested[z, 'f'] += 1
                    if c['tFull'] == 0:
                        continue
                    byz[z]['wait'].append(c['tHit'] - c['tFull'])
                    byz[z]['kill'].append(c['tDead'] - c['tHit'])
                    byz[z]['cap'].append(c['tCap'] - c['tDead'])
            cells = []
            for z in ('own', 'mid', 'enemy'):
                b = byz[z]
                cells.append(f'{f(med(b["wait"]), 0)} / {f(med(b["kill"]), 0)} / {f(med(b["cap"]), 0)} (n {len(b["wait"])})')
            cells += [f'{pct(contested["mid", "c"], contested["mid", "n"])} / {pct(contested["mid", "f"], contested["mid", "n"])}']
            rows.append([f'{k} {lab}'] + cells)
    table(['team', 'own: wait / kill / cap', 'mid', 'enemy', 'mid captures the enemy also hit / enemy hit first'], rows)


def idle(G):
    print('## Idle groups (share of the game a group stands full and untouched, weighted by gem rate gems/respawn; zone relative to S)\n')
    rows = []
    for k, gs in G.items():
        if not gs:
            continue
        acc = defaultdict(lambda: [0.0, 0.0])
        accg = defaultdict(lambda: [0.0, 0.0])
        for g in gs:
            S = g['S']
            for gr in g['groups']:
                f0 = gr['f0'] if S == 0 else 1 - gr['f0']
                z = 'own' if f0 < 0.4 else 'enemy' if f0 > 0.6 else 'mid'
                w = gr['gems'] / gr['resp']
                acc[z][0] += w * gr['idle'] / g['final']
                acc[z][1] += w
                wg = gr['gold'] / gr['resp']
                accg[z][0] += wg * gr['idle'] / g['final']
                accg[z][1] += wg
        rows.append([k] + [f'{f(100 * acc[z][0] / acc[z][1], 0) if acc[z][1] else "-"}% / {f(100 * accg[z][0] / accg[z][1], 0) if accg[z][1] else "-"}%' for z in ('own', 'mid', 'enemy')])
    table(['team', 'S own zone: gem-rate idle / gold-rate idle', 'mid', 'S enemy zone (= O own)'], rows)


def midhold(G):
    print('## Respawning middle groups: who re-takes them (consecutive cycles of the same mid group)\n')
    rows = []
    for k, gs in G.items():
        if not gs:
            continue
        stat = Counter()
        rehit = defaultdict(list)
        presS = defaultdict(list)
        for g in gs:
            S = g['S']
            byg = defaultdict(list)
            for c in g['cycles']:
                if c['end'] == 'cap':
                    byg[c['g']].append(c)
            for gi, cl in byg.items():
                cl.sort(key=lambda c: c['tCap'])
                f0 = cl[0]['f0']
                if not (0.4 <= f0 <= 0.6):
                    continue
                for a, b in zip(cl, cl[1:]):
                    if a.get('tResp') is None:
                        continue
                    who = 'S' if a['capT'] == S else 'O'
                    nxt = 'S' if b['capT'] == S else 'O'
                    stat[who, 'n'] += 1
                    if who == nxt:
                        stat[who, 'keep'] += 1
                    hs, ho = a['hold'][S], a['hold'][1 - S]
                    key = 'S only' if hs and not ho else 'O only' if ho and not hs else 'both' if hs and ho else 'none'
                    stat['hold', key] += 1
                    if nxt == 'S':
                        stat['holdS', key] += 1
                    if b['tFull'] == a['tResp'] and b.get('tHit') is not None:
                        rehit[who].append(b['tHit'] - b['tFull'])
                    presS[who].append(a['pres'][S] if who == 'S' else a['pres'][1 - S])
        rows.append([k, f'{pct(stat["S", "keep"], stat["S", "n"])} (n {stat["S", "n"]})', f'{pct(stat["O", "keep"], stat["O", "n"])} (n {stat["O", "n"]})',
                     f'{f(med(rehit["S"]), 0)} / {f(med(rehit["O"]), 0)}', f'{f(mean(presS["S"]), 2)} / {f(mean(presS["O"]), 2)}',
                     ', '.join(f'{h}: {stat["hold", h]} -> S takes {pct(stat["holdS", h], stat["hold", h])}' for h in ('S only', 'O only', 'both', 'none'))])
    table(['team', 'S captured it -> S takes the next cycle too', 'O captured -> O keeps', 're-hit wait after respawn (median) S-held / O-held', 'capturer bodies within 4 in the last 20 rounds before respawn (S / O)', 'bodies within 4 at the respawn round -> next capture'], rows)


def budget(G):
    print('## Body-time budget (share of rounds per body, mean over bodies; walk steps per captured gem)\n')
    rows = []
    for k, gs in G.items():
        if not gs:
            continue
        for lab, tt in (('S', lambda g: g['S']), ('O', lambda g: 1 - g['S'])):
            acc = Counter()
            nb = 0
            steps = 0
            capg = 0
            for g in gs:
                t = tt(g)
                for b, v in g['budget'].items():
                    if g['bteam'][b] != t:
                        continue
                    tot = sum(x for kk, x in v.items() if kk != 'steps')
                    for kk in ('dead', 'walk', 'farm', 'fight', 'oncamp', 'still', 'spawn'):
                        acc[kk] += v.get(kk, 0) / max(1, tot)
                    nb += 1
                    steps += v.get('steps', 0)
                capg += sum(c['gems'] for c in g['caps'] if c['t'] == t)
            rows.append([f'{k} {lab}'] + [f(100 * acc[kk] / nb, 1) for kk in ('dead', 'walk', 'farm', 'fight', 'oncamp', 'still', 'spawn')] + [f(steps / max(1, capg), 2)])
    table(['team', 'dead %', 'walk %', 'farm %', 'fight %', 'on camp tile %', 'still off-camp %', 'on spawn %', 'walk steps per captured gem'], rows)


def objectives(G):
    print('## Objectives (hit episodes on golem / monolith / elk groups, gap > 30 rounds splits an episode; captured within 40 rounds of the last hit)\n')
    rows = []
    for k, gs in G.items():
        if not gs:
            continue
        for cls in ('golem', 'mono', 'elk'):
            gm = [g for g in gs if any(gr['cls'] == cls for gr in g['groups'])]
            if not gm:
                continue
            for lab, tt in (('S', lambda g: g['S']), ('O', lambda g: 1 - g['S'])):
                A = [a for g in gm for a in g['atts'] if a['t'] == tt(g) and a['cls'] == cls]
                won = [a for a in A if a['res'] == 'won']
                caps = [c for g in gm for c in g['caps'] if c['t'] == tt(g) and c['cls'] == cls]
                first = []
                for g in gm:
                    cs = [c['r'] for c in g['caps'] if c['t'] == tt(g) and c['cls'] == cls]
                    first.append(min(cs) if cs else None)
                rows.append([f'{k} {lab}', cls, len(gm), f(len(A) / len(gm)), f(mean([a['n'] for a in A]), 2), f(mean([a['n'] for a in won]), 2), pct(len(won), len(A)),
                             pct(sum(1 for a in A if a['res'] == 'stolen'), len(A)), f(len(caps) / len(gm)), f(med(first), 0),
                             pct(sum(1 for x in first if x is not None), len(gm)), f(mean([c['n'] for c in caps]), 2)])
    table(['team', 'class', 'games with it', 'attempts / game', 'bodies per attempt', 'bodies per won attempt', 'won', 'stolen', 'captures / game', 'first capture (median r)', 'games with a capture', 'sharers per capture'], rows)


def winner_loser(G):
    print('## Winner vs loser, every distinct match (P = share of games where the winner\'s value is higher; ties 0.5)\n')
    seen = {}
    for k, gs in G.items():
        for g in gs:
            seen.setdefault(g['matchId'], g)
    gl = list(seen.values())
    W = [per_team_game(g, g['win']) for g in gl]
    L = [per_team_game(g, 1 - g['win']) for g in gl]
    def P(a, b):
        s = 0
        n = 0
        for x, y in zip(a, b):
            if x is None or y is None:
                continue
            n += 1
            s += 1 if x > y else 0.5 if x == y else 0
        return s / n if n else None
    rows = []
    def row(name, fn):
        a = [fn(x, g) for x, g in zip(W, gl)]
        b = [fn(x, g) for x, g in zip(L, gl)]
        rows.append([name, f(mean(a), 1), f(mean(b), 1), f(med(a), 1), f(med(b), 1), f(P(a, b), 2)])
    row('captured gems', lambda x, g: x['capgems'])
    row('own-zone gems', lambda x, g: x['gems_own'])
    row('mid-zone gems', lambda x, g: x['gems_mid'])
    row('enemy-zone gems', lambda x, g: x['gems_enemy'])
    row('captures', lambda x, g: x['ncap'])
    row('gold earned per 100 r', lambda x, g: x['earn100'])
    row('kill gold', lambda x, g: x['kill'])
    row('earned by r300', lambda x, g: sum(x['incCP'][s][2] for s in x['incCP']) if g['final'] >= 300 else None)
    row('stolen gems', lambda x, g: x['steals'])
    row('gems lost on death', lambda x, g: x['lost'])
    row('deaths', lambda x, g: x['deaths'])
    row('tributes completed', lambda x, g: x['tdone'])
    row('median bag banked', lambda x, g: med(x['bags']))
    row('biggest bag carried', lambda x, g: x['maxbag'])
    row('first bank round', lambda x, g: x['firstbank'])
    row('elk-group gems', lambda x, g: sum(c['gems'] for c in g['caps'] if c['t'] == x['_t'] and c['cls'] == 'elk'))
    row('monolith captures', lambda x, g: sum(1 for c in g['caps'] if c['t'] == x['_t'] and c['cls'] == 'mono'))
    row('golem captures', lambda x, g: sum(1 for c in g['caps'] if c['t'] == x['_t'] and c['cls'] == 'golem'))
    row('gold-cluster captures', lambda x, g: sum(1 for c in g['caps'] if c['t'] == x['_t'] and c['cls'] == 'gold'))
    row('tribute starts', lambda x, g: x['tstart'])
    row('altar locks placed', lambda x, g: sum(1 for L in g['locks'] if L['t'] == x['_t']))
    row('first capture round', lambda x, g: x['firstcap'])
    row('first mid capture round', lambda x, g: x['firstmid'])
    row('banked r300', lambda x, g: x['sub'][2])
    row('team max hp r300', lambda x, g: x['maxHpCP'][2] if g['final'] >= 300 else None)
    row('team max hp r600', lambda x, g: x['maxHpCP'][5] if g['final'] >= 600 else None)
    print(f'{len(gl)} distinct matches\n')
    table(['metric', 'winner mean', 'loser mean', 'winner median', 'loser median', 'P(w > l)'], rows)


def capclass(G):
    print('## Captures by camp class (per game: captures / gems / gold)\n')
    rows = []
    for k, gs in G.items():
        if not gs:
            continue
        for lab, tt in (('S', lambda g: g['S']), ('O', lambda g: 1 - g['S'])):
            acc = defaultdict(lambda: [0, 0, 0])
            for g in gs:
                for c in g['caps']:
                    if c['t'] == tt(g):
                        a = acc[c['cls']]
                        a[0] += 1; a[1] += c['gems']; a[2] += c['gold']
            n = len(gs)
            rows.append([f'{k} {lab}'] + [f'{f(acc[c][0] / n)} / {f(acc[c][1] / n, 0)} / {f(acc[c][2] / n, 0)}' for c in ('elk', 'wolf', 'gem', 'gold', 'golem', 'mono')])
    table(['team', 'elk groups', 'wolf groups', 'gem clusters', 'gold clusters', 'golem', 'monolith'], rows)


def bankdecision(G):
    print('## Bank decision after a capture: share of captures (bag > 0 after it) followed by a tribute start before the body\'s next capture, by bag after the capture x walking distance to the nearest altar (n in brackets)\n')
    BAG = [(1, 19), (20, 39), (40, 79), (80, 149), (150, 10 ** 6)]
    ALT = [(0, 5), (6, 10), (11, 20), (21, 999)]
    for k, gs in G.items():
        if not gs:
            continue
        for lab, tt in (('S', lambda g: g['S']), ('O', lambda g: 1 - g['S'])):
            cnt = defaultdict(lambda: [0, 0])
            dl = defaultdict(list)
            for g in gs:
                for d in g.get('bdec', []):
                    if d['t'] != tt(g) or d['bag'] <= 0 or d['alt'] is None:
                        continue
                    bi = next(i for i, (a, b) in enumerate(BAG) if a <= d['bag'] <= b)
                    ai = next(i for i, (a, b) in enumerate(ALT) if a <= d['alt'] <= b)
                    cnt[bi, ai][1] += 1
                    cnt[bi, ai][0] += d['bankNext']
                    if d['bankNext'] and d['delay'] is not None:
                        dl[bi].append(d['delay'])
            print(f'**{k} {lab}**\n')
            head = ['bag after capture'] + [f'altar {a}-{b}' if b < 999 else f'altar {a}+' for a, b in ALT] + ['rounds to the tribute start (median)']
            rows = []
            for bi, (a, b) in enumerate(BAG):
                rows.append([f'{a}-{b}' if b < 10 ** 6 else f'{a}+'] + [f'{pct(cnt[bi, ai][0], cnt[bi, ai][1])} ({cnt[bi, ai][1]})' for ai in range(len(ALT))] + [f(med(dl[bi]), 0)])
            table(head, rows)


def tribcancel(G):
    print('## Tribute channels vs nearest enemy (Chebyshev): ended by own cancel (distance at the cancel round) vs completed (closest enemy during the channel)\n')
    rows = []
    for k, gs in G.items():
        if not gs:
            continue
        for lab, tt in (('S', lambda g: g['S']), ('O', lambda g: 1 - g['S'])):
            T = [tr for g in gs for tr in g['tribs'] if tr['t'] == tt(g) and 'dEe' in tr]
            canc = [tr for tr in T if tr['res'] == 'cancel']
            done = [tr for tr in T if tr['res'] == 'done']
            big = [tr for tr in T if tr['bag'] >= 100]
            dc = Counter(min(tr['dEe'], 12) if tr['dEe'] is not None else 99 for tr in canc)
            # cancel rate by the closest enemy distance during the channel
            byd = defaultdict(lambda: [0, 0])
            for tr in T:
                if tr['res'] not in ('done', 'cancel'):
                    continue
                dm = tr['dEmin'] if tr['dEmin'] is not None else 99
                kk = 'le4' if dm <= 4 else '5-6' if dm <= 6 else '7-8' if dm <= 8 else 'gt8'
                byd[kk][1] += 1
                byd[kk][0] += tr['res'] == 'cancel'
            rows.append([f'{k} {lab}', len(T), len(canc), f(med([tr['dEe'] for tr in canc]), 0), f(q([tr['dEe'] for tr in canc if tr['dEe'] is not None], 0.9), 0),
                         f(med([tr['dEmin'] for tr in done]), 0)] + [f'{pct(byd[kk][0], byd[kk][1])} ({byd[kk][1]})' for kk in ('le4', '5-6', '7-8', 'gt8')] +
                        [pct(sum(tr['fightAfter'] for tr in canc), len(canc)), f(med([tr['bag'] for tr in canc]), 0)])
    table(['team', 'tribute starts', 'own cancels', 'enemy distance at cancel (median)', 'p90', 'closest enemy in completed channels (median)', 'cancel rate: closest enemy <= 4', '5-6', '7-8', '> 8 / none', 'cancels followed by a hit on a champion within 5 r', 'bag of cancelled (median)'], rows)


def goldshare(G):
    print('## Who earns the gold (share of the team\'s earned gold by champion, captures + kills + Marcella bank gold; mean over games with that champion)\n')
    for k, gs in G.items():
        if not gs:
            continue
        for lab, tt in (('S', lambda g: g['S']), ('O', lambda g: 1 - g['S'])):
            sh = defaultdict(list)
            for g in gs:
                T = g['teams'][str(tt(g))]
                tot = sum(v.get('cap', 0) + v.get('kill', 0) + v.get('bankgold', 0) for v in T['incBody'].values())
                if not tot:
                    continue
                for b, v in T['incBody'].items():
                    sh[T['bodyType'][b]].append((v.get('cap', 0) + v.get('kill', 0) + v.get('bankgold', 0)) / tot)
            s = ', '.join(f'{ty} {f(100 * mean(v), 0)}% (n {len(v)})' for ty, v in sorted(sh.items(), key=lambda x: -mean(x[1])))
            print(f'- {k} {lab}: {s}')
    print()


def curves(G):
    print('## Banked-gem curves (median banked gems at round; games still running at that round)\n')
    rows = []
    idx = [1, 2, 3, 4, 5, 6, 7]
    for k, gs in G.items():
        if not gs:
            continue
        for lab, sel, tt in (('S wins', lambda g: g['win'] == g['S'], lambda g: g['S']), ('S losses', lambda g: g['win'] != g['S'], lambda g: g['S']),
                             ('O when S wins', lambda g: g['win'] == g['S'], lambda g: 1 - g['S']), ('O when S loses', lambda g: g['win'] != g['S'], lambda g: 1 - g['S'])):
            X = [(g, side(g, tt(g))) for g in gs if sel(g)]
            cells = []
            for i in idx:
                cp = CP[i]
                v = [T['sub'][i] for g, T in X if g['final'] >= cp]
                cells.append(f'{f(med(v), 0)}')
            carried = [sum(T['bagCP'][b][4] for b in T['bagCP']) for g, T in X if g['final'] >= 500]
            rows.append([f'{k} {lab}', len(X)] + cells + [f(med(carried), 0)])
    table(['team', 'games'] + [f'r{CP[i]}' for i in idx] + ['unbanked gems carried at r500 (median)'], rows)


def objdur(G):
    print('## Heavy objectives taken: rounds from the first hit to the capture, and the takers\' bodies (won attempts)\n')
    rows = []
    for k, gs in G.items():
        if not gs:
            continue
        for lab, tt in (('S', lambda g: g['S']), ('O', lambda g: 1 - g['S'])):
            for cls in ('golem', 'mono'):
                A = [a for g in gs for a in g['atts'] if a['t'] == tt(g) and a['cls'] == cls and a['res'] == 'won']
                if not A:
                    continue
                rows.append([f'{k} {lab}', cls, len(A), f(med([a['capR'] - a['s'] for a in A]), 0), f(med([a['n'] for a in A]), 0),
                             f(med([a['s'] for a in A]), 0), ', '.join(f'{z} {c}' for z, c in Counter(a['zone'] for a in A).most_common())])
    table(['team', 'class', 'won attempts', 'first hit -> capture (median rounds)', 'hitters (median)', 'start round (median)', 'zone'], rows)


def distinct(G):
    seen = {}
    for k, gs in G.items():
        for g in gs:
            seen.setdefault(g['matchId'], g)
    return list(seen.values())


def pooled_hold(G):
    print('## Respawning middle groups, pooled over every distinct match (team-agnostic): who holds the group at its respawn round and who takes it\n')
    stat = Counter()
    wait = defaultdict(list)
    for g in distinct(G):
        byg = defaultdict(list)
        for c in g['cycles']:
            if c['end'] == 'cap':
                byg[c['g']].append(c)
        for gi, cl in byg.items():
            cl.sort(key=lambda c: c['tCap'])
            if not (0.4 <= cl[0]['f0'] <= 0.6):
                continue
            for a, b in zip(cl, cl[1:]):
                if a.get('tResp') is None:
                    continue
                X = a['capT']
                hx, hy = a['hold'][X], a['hold'][1 - X]
                key = 'capturer only' if hx and not hy else 'other team only' if hy and not hx else 'both' if hx and hy else 'nobody'
                stat[key, 'n'] += 1
                stat[key, 'keep'] += b['capT'] == X
                if b['tFull'] == a['tResp'] and b.get('tHit') is not None:
                    wait[key].append(b['tHit'] - b['tFull'])
                stat['holders', min(hx, 3), 'n'] += 1
                stat['holders', min(hx, 3), 'keep'] += b['capT'] == X
    rows = []
    for key in ('capturer only', 'other team only', 'both', 'nobody'):
        rows.append([key, stat[key, 'n'], pct(stat[key, 'keep'], stat[key, 'n']), f(med(wait[key]), 0), f(q(wait[key], 0.25), 0)])
    table(['bodies within 4 at the respawn round', 'cycles', 'previous capturer takes it again', 're-hit wait after respawn (median)', 'p25'], rows)
    rows = []
    for h in (0, 1, 2, 3):
        rows.append([f'{h}{"+" if h == 3 else ""}', stat['holders', h, 'n'], pct(stat['holders', h, 'keep'], stat['holders', h, 'n'])])
    table(['capturer bodies within 4 at respawn', 'cycles', 'capturer takes it again'], rows)


def objctx(G):
    print('## Heavy-objective attempts: context at the first hit (won vs not won); every distinct match pooled\n')
    gl = distinct(G)
    rows = []
    for cls in ('golem', 'mono'):
        for res in ('won', 'none', 'stolen'):
            A = [a for g in gl for a in g['atts'] if a['cls'] == cls and a['res'] == res and 'aliveT' in a]
            if not A:
                continue
            rows.append([cls, res, len(A), f(mean([a['n'] for a in A]), 2), f(mean([a['aliveT'] - a['aliveO'] for a in A]), 2),
                         f(med([a['mhT'] / a['mhO'] for a in A if a['mhO']]), 2), pct(sum(1 for a in A if a['en8'] > 0), len(A)), f(med([a['al8'] for a in A]), 0),
                         f(med([a['s'] for a in A]), 0), pct(sum(1 for a in A if a['subT'] >= a['subO']), len(A))])
    table(['class', 'result', 'attempts', 'hitters', 'alive bodies: own - enemy (mean)', 'max-hp ratio own / enemy (median)', 'enemy within 8 of the group at the start',
           'own bodies within 8 (median)', 'start round (median)', 'own banked >= enemy banked'], rows)
    rows = []
    for cls in ('golem', 'mono', 'elk'):
        by = defaultdict(lambda: [0, 0])
        for g in gl:
            for a in g['atts']:
                if a['cls'] != cls:
                    continue
                k2 = min(a['n'], 5)
                by[k2][1] += 1
                by[k2][0] += a['res'] == 'won'
        rows.append([cls] + [f'{pct(by[k2][0], by[k2][1])} ({by[k2][1]})' for k2 in (1, 2, 3, 4, 5)])
    table(['class: attempts won by number of hitters', '1 hitter', '2', '3', '4', '5+'], rows)


if __name__ == '__main__':
    G = load(KEYS)
    pooled_hold(G)
    objctx(G)
    capclass(G)
    bankdecision(G)
    tribcancel(G)
    goldshare(G)
    curves(G)
    objdur(G)
    overview(G)
    gold(G)
    captures(G)
    gemflow(G)
    banking(G)
    carriers(G)
    deaths_bags(G)
    cycles(G)
    idle(G)
    midhold(G)
    budget(G)
    objectives(G)
    winner_loser(G)
