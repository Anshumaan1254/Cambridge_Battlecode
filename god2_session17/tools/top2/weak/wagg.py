"""Aggregate tools/top2/weak/wx.mjs output (an_weak): loss anatomy, tributes, locks, carries, deaths, raids, idle, per map.
   python tools/top2/weak/wagg.py C:/battlecode/cache/an_weak/wx.jsonl [section ...]
   Sections: overview anatomy trib locks carry deaths raids idle maps (default all). T[0] = study team, T[1] = its opponent."""
import json, sys, collections, statistics as st

PATH = sys.argv[1]
SECS = sys.argv[2:] or ['overview', 'anatomy', 'trib', 'locks', 'carry', 'deaths', 'raids', 'idle', 'maps']
G = [json.loads(l) for l in open(PATH, encoding='utf-8') if l.strip()]
G = [g for g in G if 'T' in g]
KEYS = [k for k in ['pbg', 'ifish', 'cm', 'pantheon', 'coo', 'nyx'] if any(g['key'] == k for g in G)]
GEO = {}
for l in open('C:/battlecode/cache/an_strategy/mapgeo2.jsonl', encoding='utf-8'):
    g = json.loads(l); GEO[g['map']] = g['feat']
MT = {}
for l in open('C:/battlecode/cache/an_strategy/maptable.md', encoding='utf-8'):
    p = [x.strip() for x in l.split('|')]
    if len(p) > 3 and p[1].startswith(('00', '01')): MT[p[1]] = p[2]

def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float('nan')
def med(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else float('nan')
def f(x, n=0):
    return 'nan' if x != x else (f'{x:.{n}f}')

def split(key):
    A = [g for g in G if g['key'] == key]
    return A, [g for g in A if g['win']], [g for g in A if not g['win']]

if 'overview' in SECS:
    print('## overview (replay sample)')
    for k in KEYS:
        A, Wn, L = split(k)
        side = collections.Counter((g['side'], g['win']) for g in A)
        mtc = collections.Counter((MT.get(g['map'], '?'), g['win']) for g in A)
        print(f'{k}: n={len(A)} W {len(Wn)} L {len(L)}; side a {side[("a",1)]}-{side[("a",0)]} b {side[("b",1)]}-{side[("b",0)]};',
              ' '.join(f'{t} {mtc[(t,1)]}-{mtc[(t,0)]}' for t in ['fight', 'mixed', 'farm']),
              f'; final round W {f(mean([g["final"] for g in Wn]))} L {f(mean([g["final"] for g in L]))}; loss margin {f(mean([g["sub"][1]-g["sub"][0] for g in L]))}')

def S(g, f_):
    return f_(g['T'][0]), f_(g['T'][1])

if 'anatomy' in SECS:
    print('\n## anatomy: mean per game (study team / opponent), wins vs losses')
    rows = [
        ('banked r200', lambda X: X['bank'].get('200')), ('banked r400', lambda X: X['bank'].get('400')), ('banked r600', lambda X: X['bank'].get('600')),
        ('caps by r200', lambda X: X['capsAt'].get('200', 0)), ('cap gems by r200', lambda X: X['capGemsAt'].get('200', 0)), ('cap gems by r400', lambda X: X['capGemsAt'].get('400', 0)),
        ('cap gems total', lambda X: X['capGems']), ('maxhp r400', lambda X: X['maxhp'].get('400')), ('maxhp r600', lambda X: X['maxhp'].get('600')),
        ('deaths', lambda X: len(X['deaths'])), ('deaths <r200', lambda X: sum(1 for d in X['deaths'] if d['r'] < 200)), ('deaths r200-600', lambda X: sum(1 for d in X['deaths'] if 200 <= d['r'] < 600)),
        ('bag lost on death', lambda X: X['bagLost']), ('deaths with bag>=100', lambda X: sum(1 for d in X['deaths'] if d['bag'] >= 100)),
        ('tributes started', lambda X: len(X['trib'])), ('tributes cancelled', lambda X: sum(1 for t in X['trib'] if t['res'] not in ('done', 'open'))),
        ('gems in cancelled tributes', lambda X: sum(t['bag'] for t in X['trib'] if t['res'] not in ('done', 'open'))),
        ('max bag', lambda X: max([t['bag'] for t in X['trib']] + [0])), ('locks placed', lambda X: len(X['locks'])),
        ('idle rounds', lambda X: X['idle']), ('idle runs>=25', lambda X: len(X['idleRuns'])), ('cluster r20-150', lambda X: X['cluster']['r20_150']), ('cluster r150-400', lambda X: X['cluster']['r150_400']),
        ('raid gems (captures on their own zone)', lambda X: X['raidGems']), ('undefended raid gems', lambda X: X['raidGemsUndef']), ('recalls done', lambda X: X['recallsDone']),
        ('mid-zone cap gems', lambda X: X['capZone']['mid'][1]), ('own-zone cap gems', lambda X: X['capZone']['own'][1]), ('enemy-zone cap gems', lambda X: X['capZone']['enemy'][1]),
    ]
    for k in KEYS:
        A, Wn, L = split(k)
        print(f'### {k} (W {len(Wn)}, L {len(L)})')
        print(f'{"metric":40s} | {"wins S/O":>15s} | {"losses S/O":>15s}')
        for name, fn in rows:
            ws = [S(g, fn) for g in Wn]; ls = [S(g, fn) for g in L]
            print(f'{name:40s} | {f(mean([a for a, b in ws]),1):>7s}/{f(mean([b for a, b in ws]),1):<7s} | {f(mean([a for a, b in ls]),1):>7s}/{f(mean([b for a, b in ls]),1):<7s}')
        fd = collections.Counter()
        for g in A:
            a, b = g['T'][0]['firstDeath'], g['T'][1]['firstDeath']
            who = 'none' if a is None and b is None else 'S' if (b is None or (a is not None and a < b)) else 'O' if (a is None or b < a) else 'same'
            fd[(who, g['win'])] += 1
        print('first death (team that lost a body first): ', ' '.join(f'{w}: W{fd[(w,1)]}-L{fd[(w,0)]}' for w in ['S', 'O', 'same', 'none']))

if 'trib' in SECS:
    print('\n## tributes (study team), per team')
    for k in KEYS:
        A, Wn, L = split(k)
        T = [(g, t) for g in A for t in g['T'][0]['trib']]
        n = len(A)
        bins = [(1, 49), (50, 99), (100, 199), (200, 399), (400, 10000)]
        print(f'### {k}: {len(T)} tribute starts in {n} games ({len(T)/n:.1f}/game)')
        for lo, hi in bins:
            B = [t for g, t in T if lo <= t['bag'] <= hi]
            if not B: continue
            res = collections.Counter(t['res'] for t in B)
            print(f'  bag {lo}-{hi}: n {len(B)} ({len(B)/n:.2f}/game) gems {sum(t["bag"] for t in B)}, need mean {mean([t["need"] for t in B]):.1f}, res {dict(res)}, '
                  f'enemy within 5 at some point {sum(1 for t in B if t["enRounds"]>0)} ({100*sum(1 for t in B if t["enRounds"]>0)/len(B):.0f}%), stunner within 5 {sum(1 for t in B if t["enStunMax"]>0)}, '
                  f'first enemy after {mean([t["firstEn"] for t in B]):.1f} r, dmg taken {mean([t["dmgIn"] for t in B]):.0f}')
        by = collections.Counter(t['ty'] for g, t in T if t['bag'] >= 100)
        print('  bags >= 100 by champion:', dict(by))
        # share of tributed gems in bags >= 100 / >= 200
        done = [t for g, t in T if t['res'] == 'done']
        tot = sum(t['bag'] for t in done) or 1
        print(f'  done gems share in bags>=100 {100*sum(t["bag"] for t in done if t["bag"]>=100)/tot:.0f}%, >=200 {100*sum(t["bag"] for t in done if t["bag"]>=200)/tot:.0f}%')
        # opponents
        TO = [(g, t) for g in A for t in g['T'][1]['trib']]
        resO = collections.Counter(t['res'] for g, t in TO if t['bag'] >= 100)
        print(f'  opponents: {len(TO)} starts, bags>=100 {sum(1 for g,t in TO if t["bag"]>=100)} res {dict(resO)}')
        # list big failed tributes
        for g, t in sorted(T, key=lambda gt: -gt[1]['bag']):
            if t['bag'] >= 150 and t['res'] not in ('done', 'open'):
                print(f'    FAIL {g["file"]} {"W" if g["win"] else "L"} vs {g["opp"]}: r{t["r"]} {t["ty"]} bag {t["bag"]} need {t["need"]} -> {t["res"]} after {t["len"]} (stun by {t["stunBy"]}, en {t["enMax"]}, first en +{t["firstEn"]}, dmg {t["dmgIn"]})')

if 'locks' in SECS:
    print('\n## altar locks')
    for k in KEYS:
        A, Wn, L = split(k)
        sl = [l for g in A for l in g['T'][0]['locks']]; ol = [l for g in A for l in g['T'][1]['locks']]
        print(f'{k}: study team placed {len(sl)} locks in {len(A)} games ({sum(1 for g in A if g["T"][0]["locks"])} games), cancelling {sum(1 for l in sl if l["cancelled"])} tributes ({sum(l["cancelled"] for l in sl)} gems); '
              f'opponents placed {len(ol)} ({sum(1 for g in A if g["T"][1]["locks"])} games), cancelling {sum(1 for l in ol if l["cancelled"])} study tributes ({sum(l["cancelled"] for l in ol)} gems)')
        for g in A:
            for l in g['T'][1]['locks']:
                if l['cancelled']: print(f'    {g["file"]} {"W" if g["win"] else "L"} opp {g["opp"]} r{l["r"]} lock by {l["ty"]} cancelled a {l["cancelled"]}-gem tribute')

if 'carry' in SECS:
    print('\n## carry dependence: per champion of the study team')
    for k in KEYS:
        A, Wn, L = split(k)
        tys = collections.defaultdict(list)
        for g in A:
            X = g['T'][0]; capT = X['capGems'] or 1; kT = X['kills'] or 1
            for b, pb in X['perBody'].items():
                tys[pb['ty']].append((g, pb, pb['capGems'] / capT, pb['kills'] / kT))
        print(f'### {k}')
        for ty, L2 in sorted(tys.items(), key=lambda kv: -len(kv[1])):
            early = [x for x in L2 if x[1]['firstDeath'] is not None and x[1]['firstDeath'] < 200]
            late = [x for x in L2 if not (x[1]['firstDeath'] is not None and x[1]['firstDeath'] < 200)]
            d300 = [x for x in L2 if x[1]['d400'] >= 2]
            print(f'  {ty:12s} n {len(L2):3d} capshare {100*mean([x[2] for x in L2]):4.0f}% killshare {100*mean([x[3] for x in L2]):4.0f}% deaths {mean([x[1]["deaths"] for x in L2]):.2f} '
                  f'| died <r200: {len(early)} games win {100*mean([x[0]["win"] for x in early]) if early else float("nan"):.0f}% vs not {100*mean([x[0]["win"] for x in late]):.0f}% (n {len(late)}) '
                  f'| >=2 deaths <r400: {len(d300)} win {100*mean([x[0]["win"] for x in d300]) if d300 else float("nan"):.0f}%')

if 'deaths' in SECS:
    print('\n## deaths of the study team (and of its opponents) by context')
    for k in KEYS:
        A, Wn, L = split(k)
        for lab, GG in [('wins', Wn), ('losses', L)]:
            for side in [0, 1]:
                D = [d for g in GG for d in g['T'][side]['deaths']]
                n = len(GG)
                if not D: continue
                z = collections.Counter(d['z'] for d in D)
                iso = sum(1 for d in D if d['al6'] == 0 and d['byChamp'])
                outn = sum(1 for d in D if d['byChamp'] and d['en6'] > d['al6'] + 1)
                chase = sum(1 for d in D if d['byChamp'] and d['dOwn10'] is not None and d['dOwn'] is not None and d['dOwn'] - d['dOwn10'] >= 3 and d['hitsC'] > 0)
                flee = sum(1 for d in D if d['byChamp'] and d['dOwn10'] is not None and d['dOwn'] is not None and d['dOwn10'] - d['dOwn'] >= 3 and d['hitsC'] == 0)
                camp = sum(1 for d in D if not d['byChamp'])
                farm = sum(1 for d in D if d['hitsK'] > 0 and d['hitsC'] == 0)
                weak = sum(1 for d in D if d['byChamp'] and d['enMh'] and d['mh'] and d['mh'] < 0.8 * d['enMh'])
                ty = collections.Counter(d['ty'] for d in D)
                print(f'{k} {lab:6s} {"S" if side==0 else "O"}: {len(D)/n:.2f}/game  zone own {z["own"]/n:.2f} mid {z["mid"]/n:.2f} enemy {z["enemy"]/n:.2f} | isolated {iso/n:.2f} outnumbered {outn/n:.2f} '
                      f'chase {chase/n:.2f} flee {flee/n:.2f} farming {farm/n:.2f} camp-kill {camp/n:.2f} weaker-than-killers {weak/n:.2f} | bag {sum(d["bag"] for d in D)/n:.0f} | types {dict(ty.most_common(4))}')

if 'raids' in SECS:
    print('\n## raids: captures by the opponent on the study team\'s own zone (undefended = no study body within 8)')
    for k in KEYS:
        A, Wn, L = split(k)
        for lab, GG in [('wins', Wn), ('losses', L)]:
            n = len(GG) or 1
            print(f'{k} {lab}: opp raids {sum(g["T"][1]["raids"] for g in GG)/n:.2f} ({sum(g["T"][1]["raidGems"] for g in GG)/n:.0f} gems, undefended {sum(g["T"][1]["raidGemsUndef"] for g in GG)/n:.0f}) '
                  f'| study raids {sum(g["T"][0]["raids"] for g in GG)/n:.2f} ({sum(g["T"][0]["raidGems"] for g in GG)/n:.0f} gems, undefended {sum(g["T"][0]["raidGemsUndef"] for g in GG)/n:.0f})')

if 'idle' in SECS:
    print('\n## idle runs >= 25 rounds (alive, off spawn, no move / action / channel)')
    for k in KEYS:
        A, Wn, L = split(k)
        R = [(g, r) for g in A for r in g['T'][0]['idleRuns']]
        print(f'{k}: {len(R)} runs in {len(A)} games, rounds {sum(r["len"] for g, r in R)}; on camp tiles {sum(1 for g, r in R if r["camp"])}; by type {dict(collections.Counter(r["ty"] for g, r in R))}')
        for g, r in sorted(R, key=lambda x: -x[1]['len'])[:6]:
            print(f'    {g["file"]} {"W" if g["win"] else "L"} {r["ty"]} r{r["r"]} {r["len"]} rounds at {r["at"]} camp {r["camp"]} zone {r["z"]}')

if 'maps' in SECS:
    print('\n## per map (study team W-L in the replay sample; opponent winners\' profile in losses)')
    for k in KEYS:
        A, Wn, L = split(k)
        bym = collections.defaultdict(list)
        for g in A: bym[g['map']].append(g)
        print(f'### {k}')
        for m, GG in sorted(bym.items(), key=lambda kv: -sum(1 - g['win'] for g in kv[1])):
            l = [g for g in GG if not g['win']]
            if not l: continue
            ft = GEO.get(m, {})
            print(f'  {m:22s} {sum(g["win"] for g in GG)}-{len(l)} [{MT.get(m,"?")} s2s {ft.get("s2s")} mid {ft.get("midShare")} mono {ft.get("mono")} golem {ft.get("golem")}] losses: ' +
                  '; '.join(f'{g["file"][-15:-8]} {g["side"]} vs {g["opp"][:12]} {g["sub"][0]}-{g["sub"][1]} r{g["final"]} dS/dO {len(g["T"][0]["deaths"])}/{len(g["T"][1]["deaths"])} b400 {g["T"][0]["bank"].get("400")}/{g["T"][1]["bank"].get("400")}' for g in l))
