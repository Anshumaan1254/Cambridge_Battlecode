# an_economy special questions from tools/top2/economy/econ_game.py output:
#   (1) prism best girl's Prism bag: bag over time, tribute episodes (timing, location, escort, disruption: stun / lock / death,
#       what happens next), deaths with the bag and where those gems end up;
#   (2) bag chains for every team: deaths with >= 50 gems to a champion, followed until the gems are banked / lost / unbanked;
#   (3) Intercontinental Fish's Vesper: share of the team's gold by source, rewards taken (class / zone / shared), banking cadence;
#       compared with every other Vesper in the data.
#   python tools/top2/economy/econ_special.py > C:/battlecode/cache/t2econ/special.txt
import json, sys, statistics, math
from collections import defaultdict, Counter

CACHE = 'C:/battlecode/cache'
KEYS = ['pbg', 'ifish', 'pantheon', 'coo', 'cm', 'nyx']


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


def load():
    G = {}
    for k in KEYS:
        try:
            G[k] = [json.loads(l) for l in open(f'{CACHE}/t2econ/games_{k}.jsonl', encoding='utf-8')]
        except FileNotFoundError:
            G[k] = []
    return G


def zone(fv):
    return None if fv is None else 'own' if fv < 0.4 else 'enemy' if fv > 0.6 else 'mid'


def episodes(tribs, who):
    """tribute starts of one body grouped into episodes (next start within 12 rounds of the previous end, same altar)"""
    ts = sorted([t for t in tribs if t['who'] == who], key=lambda t: t['r'])
    eps = []
    for t in ts:
        if eps and tuple(eps[-1][-1]['altar']) == tuple(t['altar']) and t['r'] - eps[-1][-1].get('rEnd', t['r']) <= 12 and eps[-1][-1]['res'] != 'done':
            eps[-1].append(t)
        else:
            eps.append([t])
    return eps


def fate_of_bag(g, killer, r0, depth=0):
    """follow a body that just received a bag at round r0: ('banked', team, r) | ('died', ...) recursion | ('end', team)"""
    bt = g['bteam']
    team = bt[str(killer)]
    nxt_bank = min((t for t in g['tribs'] if t['who'] == killer and t['res'] == 'done' and t['rEnd'] >= r0), key=lambda t: t['rEnd'], default=None)
    nxt_death = min((d for d in g['deaths'] if d['who'] == killer and d['r'] > r0), key=lambda d: d['r'], default=None)
    if nxt_bank and (not nxt_death or nxt_bank['rEnd'] <= nxt_death['r']):
        return ('banked', team, nxt_bank['rEnd'], depth)
    if nxt_death:
        if nxt_death['killer'] >= 0 and depth < 8:
            return fate_of_bag(g, nxt_death['killer'], nxt_death['r'], depth + 1)
        return ('camp' if nxt_death['killer'] == -1 else 'other', team, nxt_death['r'], depth)
    return ('end', team, g['final'], depth)


def prism(G):
    print('# (1) prism best girl: the Prism bag\n')
    gs = G['pbg']
    rows = []
    allep = []
    deaths = []
    bags_cp = defaultdict(list)
    maxb = []
    share_cap = []
    share_bank = []
    for g in gs:
        S = g['S']
        pr = [int(b) for b, ty in g['btype'].items() if ty == 'Prism' and g['bteam'][b] == S]
        if not pr:
            continue
        b = pr[0]
        tl = g['bagtl'][str(b)]
        for cp in (100, 200, 300, 400, 500, 600, 800, 1000, 1200):
            i = cp // 10
            if i < len(tl):
                bags_cp[cp].append(tl[i])
        maxb.append(max(tl))
        capS = sum(c['gems'] for c in g['caps'] if c['t'] == S)
        capP = sum(gm for c in g['caps'] if c['t'] == S for ty, gm, gd in c['whoGems'] if ty == 'Prism')
        share_cap.append(capP / capS if capS else None)
        bankS = sum(t['banked'] for t in g['tribs'] if t['t'] == S and t['res'] == 'done')
        bankP = sum(t['banked'] for t in g['tribs'] if t['who'] == b and t['res'] == 'done')
        share_bank.append(bankP / bankS if bankS else None)
        for ep in episodes(g['tribs'], b):
            first, last = ep[0], ep[-1]
            res = last['res']
            dis = [t['res'] for t in ep if t['res'] in ('stun', 'lock', 'death')]
            allep.append({'file': g['file'], 'win': g['win'] == S, 'r': first['r'], 'bag': first['bag'], 'n': len(ep), 'res': res, 'dis': dis,
                          'zone': zone(first.get('altarF')), 'spawnWalk': first.get('altarSpawn'), 'allies4': first['allies4'], 'enemies4': first['enemies4'],
                          'emax6': max(t['emax6'] for t in ep), 'amin4': min(t['amin4'] for t in ep), 'rEnd': last.get('rEnd'),
                          'causes': [t['res'] for t in ep]})
        for d in g['deaths']:
            if d['who'] == b:
                fate = fate_of_bag(g, d['killer'], d['r']) if d['killer'] >= 0 and d['bag'] > 0 else None
                deaths.append({'file': g['file'], 'win': g['win'] == S, 'r': d['r'], 'bag': d['bag'], 'killer': d['killerType'], 'zone': d['zone'],
                               'fate': fate, 'S': S})
    n = len(maxb)
    print(f'pbg games with Prism: {n} of {len(gs)}\n')
    print('| round | 100 | 200 | 300 | 400 | 500 | 600 | 800 | 1000 | 1200 |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    print('| Prism bag median (games still running) | ' + ' | '.join(f'{f(med(bags_cp[cp]), 0)} ({len(bags_cp[cp])})' for cp in (100, 200, 300, 400, 500, 600, 800, 1000, 1200)) + ' |')
    print('| Prism bag p75 | ' + ' | '.join(f(q(bags_cp[cp], 0.75), 0) for cp in (100, 200, 300, 400, 500, 600, 800, 1000, 1200)) + ' |')
    print()
    print(f'- Max bag per game: median {f(med(maxb), 0)}, p25 {f(q(maxb, 0.25), 0)}, p75 {f(q(maxb, 0.75), 0)}, max {max(maxb)}; >= 200 in {pct(sum(1 for x in maxb if x >= 200), n)} of games, >= 400 in {pct(sum(1 for x in maxb if x >= 400), n)}')
    print(f'- Prism share of the team\'s captured gems {f(100 * mean(share_cap), 0)}%, of banked gems {f(100 * mean(share_bank), 0)}%')
    ne = len(allep)
    print(f'- Tribute episodes: {ne} ({f(ne / n)} per game); first-start bag median {f(med([e["bag"] for e in allep]), 0)}, mean {f(mean([e["bag"] for e in allep]), 0)}, p90 {f(q([e["bag"] for e in allep], 0.9), 0)}')
    big = [e for e in allep if e['bag'] >= 100]
    small = [e for e in allep if e['bag'] < 100]
    for lab, E in (('bag >= 100', big), ('bag < 100', small)):
        m = len(E)
        if not m:
            continue
        res = Counter(e['res'] for e in E)
        dis = sum(1 for e in E if e['dis'])
        print(f'  - {lab}: {m} episodes, start round median {f(med([e["r"] for e in E]), 0)}, bag median {f(med([e["bag"] for e in E]), 0)}; altar zone '
              f'{", ".join(f"{z} {pct(c, m)}" for z, c in Counter(e["zone"] for e in E).most_common())}; altar walk from spawn median {f(med([e["spawnWalk"] for e in E]), 0)}; '
              f'ally within 4 at start {pct(sum(1 for e in E if e["allies4"] > 0), m)}, every round {pct(sum(1 for e in E if e["amin4"] > 0), m)}; enemy within 4 at start {pct(sum(1 for e in E if e["enemies4"] > 0), m)}, within 6 during {pct(sum(1 for e in E if e["emax6"] > 0), m)}; '
              f'outcome {", ".join(f"{k} {v}" for k, v in res.most_common())}; disrupted by stun / lock / death at least once {dis} ({pct(dis, m)})')
    # disrupted episodes: what came next
    print('\nDisrupted big-bag episodes (bag >= 100; causes in order; final result):\n')
    for e in sorted(big, key=lambda e: -e['bag']):
        if e['dis'] or e['res'] not in ('done',):
            print(f'  - {e["file"]} r{e["r"]} bag {e["bag"]} zone {e["zone"]} allies4 {e["allies4"]} emax6 {e["emax6"]}: {" > ".join(e["causes"])} (end r{e["rEnd"]}; game {"won" if e["win"] else "lost"})')
    print()
    nd = len(deaths)
    db = [d for d in deaths if d['bag'] > 0]
    print(f'- Prism deaths: {nd} ({f(nd / n, 2)} per game); with a bag {len(db)}; gems lost {sum(d["bag"] for d in deaths)} ({f(sum(d["bag"] for d in deaths) / n, 0)} per game); '
          f'bag >= 100: {sum(1 for d in deaths if d["bag"] >= 100)} deaths, {sum(d["bag"] for d in deaths if d["bag"] >= 100)} gems')
    fates = Counter()
    fg = Counter()
    for d in deaths:
        if d['bag'] >= 50 and d['fate']:
            k = d['fate'][0]
            who = 'pbg' if d['fate'][1] == d['S'] else 'enemy'
            fates[k, who] += 1
            fg[k, who] += d['bag']
    print('- Fate of bags >= 50 lost by the Prism: ' + ', '.join(f'{k} by {w}: {n} ({fg[k, w]} gems)' for (k, w), n in fates.most_common()))
    print('- Big Prism deaths (bag >= 100): ' + '; '.join(f'{d["file"]} r{d["r"]} bag {d["bag"]} by {d["killer"]} in {d["zone"]} -> {d["fate"][0] if d["fate"] else "-"} ({"pbg" if d["fate"] and d["fate"][1] == d["S"] else "enemy"}) game {"won" if d["win"] else "lost"}' for d in sorted(deaths, key=lambda d: -d['bag']) if d['bag'] >= 100))
    # results by max bag
    wins_by = defaultdict(lambda: [0, 0])
    for g in gs:
        S = g['S']
        pr = [b for b, ty in g['btype'].items() if ty == 'Prism' and g['bteam'][b] == S]
        if not pr:
            continue
        mb = max(g['bagtl'][pr[0]])
        lostbig = any(d['who'] == int(pr[0]) and d['bag'] >= 100 for d in g['deaths'])
        k = 'lost a >= 100 bag' if lostbig else ('max bag >= 300' if mb >= 300 else 'max bag 100-299' if mb >= 100 else 'max bag < 100')
        wins_by[k][0] += g['win'] == S
        wins_by[k][1] += 1
    print('- pbg result by Prism bag: ' + ', '.join(f'{k}: {v[0]}/{v[1]} won' for k, v in wins_by.items()))
    print()


def enemy_prism_attacks(G):
    print('# (1b) What opponents do against big pbg bags (tribute starts of any pbg body with bag >= 100)\n')
    gs = G['pbg']
    rows = Counter()
    bagsum = Counter()
    for g in gs:
        S = g['S']
        for t in g['tribs']:
            if t['t'] != S or t['bag'] < 100:
                continue
            rows[t['type'], t['res']] += 1
            bagsum[t['type']] += 1
    for (ty, res), n in sorted(rows.items()):
        print(f'- {ty}: {res} {n}')
    # locks placed by opponents in pbg games and what they hit
    nl = 0
    for g in gs:
        S = g['S']
        nl += sum(1 for L in g['locks'] if L['t'] != S)
    print(f'- altar locks placed by pbg\'s opponents: {nl} in {len(gs)} games ({f(nl / len(gs), 2)} per game); by pbg: {sum(1 for g in gs for L in g["locks"] if L["t"] == g["S"])}')
    print()


def chains(G):
    print('# (2) Bag chains: deaths with a bag >= 50 killed by a champion, followed (through further kills) until the gems are banked, lost to a camp or still carried at the end (counts of deaths)\n')
    print('| team | S big-bag deaths / game (n) | banked by the killer\'s team | recovered and banked by S | carried at the end | lost to camps | S kills O big-bag carriers / game (n) | S banks them | O recovers them |')
    print('|---|---|---|---|---|---|---|---|---|')
    for k, gs in G.items():
        if not gs:
            continue
        lost = Counter(); take = Counter()
        for g in gs:
            S = g['S']
            for d in g['deaths']:
                if d['bag'] < 50 or d['killer'] < 0:
                    continue
                fate = fate_of_bag(g, d['killer'], d['r'])
                victim = fate[1] == d['t']
                key = ('banked' if fate[0] == 'banked' else 'end' if fate[0] == 'end' else 'camp', 'victim' if victim else 'killer')
                if d['t'] == S:
                    lost[key] += 1; lost['n'] += 1
                else:
                    take[key] += 1; take['n'] += 1
        n = len(gs)
        print(f'| {k} | {f(lost["n"] / n, 2)} ({lost["n"]}) | {pct(lost["banked", "killer"], lost["n"])} | {pct(lost["banked", "victim"], lost["n"])} | {pct(lost["end", "killer"] + lost["end", "victim"], lost["n"])} | '
              f'{pct(lost["camp", "killer"] + lost["camp", "victim"], lost["n"])} | {f(take["n"] / n, 2)} ({take["n"]}) | {pct(take["banked", "killer"], take["n"])} | {pct(take["banked", "victim"], take["n"])} |')
    print()


def vesper(G):
    print('# (3) Vesper Vale as the carry\n')
    print('| team | side | Vesper games | gold share of team earned | Vesper gold / game | capture gold share | kill gold share | captures taken % | gems taken % | solo captures % | class mix of its captures (gems) | zone mix (gems) | tributes / game | bag median | rounds between banks (median) | deaths / game | gems lost / game |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for k, gs in G.items():
        if not gs:
            continue
        for lab, tt in (('S', lambda g: g['S']), ('O', lambda g: 1 - g['S'])):
            n = 0
            gsh = []; vg = []; capsh = []; killsh = []; ncap = []; gemsh = []; solo = []
            cls = Counter(); zn = Counter(); tribs = []; gaps = []; deaths = []; lost = []
            for g in gs:
                t = tt(g)
                vs = [b for b, ty in g['btype'].items() if ty == 'VesperVale' and g['bteam'][b] == t]
                if not vs:
                    continue
                b = vs[0]
                n += 1
                T = g['teams'][str(t)]
                ib = T['incBody'].get(b, {})
                earnB = ib.get('cap', 0) + ib.get('kill', 0) + ib.get('bankgold', 0)
                tot = sum(v.get('cap', 0) + v.get('kill', 0) + v.get('bankgold', 0) for v in T['incBody'].values())
                if tot:
                    gsh.append(earnB / tot)
                vg.append(earnB)
                tc = sum(v.get('cap', 0) for v in T['incBody'].values())
                tk = sum(v.get('kill', 0) for v in T['incBody'].values())
                if tc:
                    capsh.append(ib.get('cap', 0) / tc)
                if tk:
                    killsh.append(ib.get('kill', 0) / tk)
                caps = [c for c in g['caps'] if c['t'] == t]
                mine = [c for c in caps if int(b) in c['who']]
                if caps:
                    ncap.append(len(mine) / len(caps))
                    tg = sum(c['gems'] for c in caps)
                    mg = sum(gm for c in mine for ty, gm, gd in c['whoGems'] if ty == 'VesperVale')
                    if tg:
                        gemsh.append(mg / tg)
                if mine:
                    solo.append(sum(1 for c in mine if c['n'] == 1) / len(mine))
                for c in mine:
                    gm = sum(x[1] for x in c['whoGems'] if x[0] == 'VesperVale')
                    gd = sum(x[2] for x in c['whoGems'] if x[0] == 'VesperVale')
                    cls[c['cls']] += gm if c['cls'] != 'gold' else 0
                    cls['gold-cluster gold'] += gd if c['cls'] == 'gold' else 0
                    zn[c['zone']] += gm
                tr = sorted([x for x in g['tribs'] if x['who'] == int(b) and x['res'] == 'done'], key=lambda x: x['rEnd'])
                tribs.append(len(tr))
                for a, c in zip(tr, tr[1:]):
                    gaps.append(c['rEnd'] - a['rEnd'])
                bagsV = [x['banked'] for x in tr]
                tribs[-1] = (len(tr), bagsV)
                dd = [d for d in g['deaths'] if d['who'] == int(b)]
                deaths.append(len(dd))
                lost.append(sum(d['bag'] for d in dd))
            if not n:
                continue
            cg = sum(v for kk, v in cls.items() if kk != 'gold-cluster gold')
            zt = sum(zn.values())
            allbags = [x for c, bl in tribs for x in bl]
            print(f'| {k} | {lab} | {n} | {pct(mean(gsh) or 0, 1)} | {f(mean(vg), 0)} | {pct(mean(capsh) or 0, 1)} | {pct(mean(killsh) or 0, 1)} | {pct(mean(ncap) or 0, 1)} | {pct(mean(gemsh) or 0, 1)} | {pct(mean(solo) or 0, 1)} | '
                  f'{", ".join(f"{c2} {pct(v, cg)}" for c2, v in cls.most_common() if c2 != "gold-cluster gold")} | {", ".join(f"{z} {pct(v, zt)}" for z, v in zn.most_common())} | '
                  f'{f(mean([c for c, bl in tribs]))} | {f(med(allbags), 0)} | {f(med(gaps), 0)} | {f(mean(deaths), 2)} | {f(mean(lost), 0)} |')
    print()


def ifish_vesper_detail(G):
    print('# (3b) Intercontinental Fish Vesper: which rewards, by round window\n')
    gs = G['ifish']
    win = [(0, 200), (200, 500), (500, 1000), (1000, 2001)]
    for a, b in win:
        tot = Counter(); ves = Counter()
        for g in gs:
            S = g['S']
            vs = [int(x) for x, ty in g['btype'].items() if ty == 'VesperVale' and g['bteam'][x] == S]
            if not vs:
                continue
            for c in g['caps']:
                if c['t'] != S or not (a <= c['r'] < b):
                    continue
                tot[c['cls']] += 1
                if vs[0] in c['who']:
                    ves[c['cls']] += 1
        print(f'- r{a}-{b}: Vesper takes ' + ', '.join(f'{k} {ves[k]}/{v} ({pct(ves[k], v)})' for k, v in tot.most_common()))
    # gold-bonus routing: captures by others with Vesper within 4 of the capture (cannot see positions here: use 'near' count proxy)
    print()


def prism_all(G):
    print('# (1c) Every Prism in the data: bag, banking and big-bag deaths (S = the study team\'s Prism, O = opponents\' Prisms)\n')
    print('| team | side | Prism games | max bag median / p75 | bag at r600 (median) | share of team captured gems | of banked gems | tribute starts / game | completed | deaths / game | big-bag (>= 100) deaths / game | gems lost / game | killed while tributing | big-bag killers | team win % |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for k, gs in G.items():
        for lab, tt in (('S', lambda g: g['S']), ('O', lambda g: 1 - g['S'])):
            n = 0; mb = []; b600 = []; shc = []; shb = []; ts = []; td = []; de = []; bd = []; gl = []; kt = 0; killers = Counter(); wins = 0
            for g in gs:
                t = tt(g)
                pr = [int(b) for b, ty in g['btype'].items() if ty == 'Prism' and g['bteam'][b] == t]
                if not pr:
                    continue
                b = pr[0]; n += 1
                tl = g['bagtl'][str(b)]
                mb.append(max(tl))
                if len(tl) > 60:
                    b600.append(tl[60])
                capT = sum(c['gems'] for c in g['caps'] if c['t'] == t)
                capP = sum(gm for c in g['caps'] if c['t'] == t for ty, gm, gd in c['whoGems'] if ty == 'Prism')
                if capT:
                    shc.append(capP / capT)
                bT = sum(x['banked'] for x in g['tribs'] if x['t'] == t and x['res'] == 'done')
                bP = sum(x['banked'] for x in g['tribs'] if x['who'] == b and x['res'] == 'done')
                if bT:
                    shb.append(bP / bT)
                trs = [x for x in g['tribs'] if x['who'] == b]
                ts.append(len(trs)); td.append(sum(1 for x in trs if x['res'] == 'done'))
                dl = [d for d in g['deaths'] if d['who'] == b]
                de.append(len(dl)); bd.append(sum(1 for d in dl if d['bag'] >= 100)); gl.append(sum(d['bag'] for d in dl))
                for d in dl:
                    if d['bag'] >= 100:
                        killers[d['killerType']] += 1
                        if any(x['res'] == 'death' and x['rEnd'] == d['r'] for x in trs):
                            kt += 1
                wins += g['win'] == t
            if not n:
                continue
            print(f'| {k} | {lab} | {n} | {f(med(mb), 0)} / {f(q(mb, 0.75), 0)} | {f(med(b600), 0)} | {pct(mean(shc) or 0, 1)} | {pct(mean(shb) or 0, 1)} | {f(mean(ts))} | {f(mean(td))} | {f(mean(de), 2)} | {f(mean(bd), 2)} | {f(mean(gl), 0)} | {kt} of {sum(bd)} | '
                  f'{", ".join(f"{a} {c}" for a, c in killers.most_common(4))} | {pct(wins, n)} |')
    print()


def finishers(G):
    print('# (4) Finisher tributes: starts with banked + bag >= 1000 (completion wins the game on the spot)\n')
    print('| team | side | finisher starts / game | games with one | bag median | done | own cancel | stunned (by) | locked | killed | other | ally within 4 at start | game-ending tribute bag (median, games won on gems) | wins ended by a bag >= 100 |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for k, gs in G.items():
        if not gs:
            continue
        for lab, tt in (('S', lambda g: g['S']), ('O', lambda g: 1 - g['S'])):
            F = []
            gw = 0
            endbags = []
            for g in gs:
                t = tt(g)
                fs = [x for x in g['tribs'] if x['t'] == t and 'subS' in x and x['subS'] + x['bag'] >= 1000]
                F += fs
                gw += 1 if fs else 0
                if g['win'] == t and g['final'] < 2000:
                    done = [x for x in g['tribs'] if x['t'] == t and x['res'] == 'done']
                    if done:
                        last = max(done, key=lambda x: x['rEnd'])
                        endbags.append(last['banked'])
            n = len(gs)
            res = Counter(x['res'] for x in F)
            by = Counter(x.get('by') for x in F if x['res'] == 'stun')
            m = len(F)
            other = m - res['done'] - res['cancel'] - res['stun'] - res['lock'] - res['death']
            print(f'| {k} | {lab} | {f(m / n, 2)} | {pct(gw, n)} | {f(med([x["bag"] for x in F]), 0)} | {pct(res["done"], m)} | {pct(res["cancel"], m)} | {pct(res["stun"], m)} ({", ".join(f"{a} {b}" for a, b in by.most_common(3))}) | '
                  f'{pct(res["lock"], m)} | {pct(res["death"], m)} | {pct(other, m)} | {pct(sum(1 for x in F if x["allies4"] > 0), m)} | {f(med(endbags), 0)} | {pct(sum(1 for b in endbags if b >= 100), len(endbags))} |')
    print()


def locks(G):
    print('# (5) Altar locks: placed per game, and how many cancelled a tribute channel\n')
    print('| team | S locks / game | S locks that cancelled an O tribute | O locks / game | O locks that cancelled an S tribute | S tributes lost to locks / game | O tributes lost to locks / game |')
    print('|---|---|---|---|---|---|---|')
    for k, gs in G.items():
        if not gs:
            continue
        n = len(gs)
        sl = sum(1 for g in gs for L in g['locks'] if L['t'] == g['S'])
        ol = sum(1 for g in gs for L in g['locks'] if L['t'] != g['S'])
        st = sum(1 for g in gs for x in g['tribs'] if x['t'] == g['S'] and x['res'] == 'lock')
        ot = sum(1 for g in gs for x in g['tribs'] if x['t'] != g['S'] and x['res'] == 'lock')
        print(f'| {k} | {f(sl / n, 2)} | {pct(ot, sl)} | {f(ol / n, 2)} | {pct(st, ol)} | {f(st / n, 2)} | {f(ot / n, 2)} |')
    print()


if __name__ == '__main__':
    G = load()
    prism_all(G)
    finishers(G)
    locks(G)
    prism(G)
    enemy_prism_attacks(G)
    chains(G)
    vesper(G)
    ifish_vesper_detail(G)
