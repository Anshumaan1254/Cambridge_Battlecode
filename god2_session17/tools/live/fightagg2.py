# Engagement / contact / top-vs-top predictor / conversion tables over tools/live/fightan.mjs output (an.jsonl).
#   python tools/live/fightagg2.py C:/battlecode/cache/an_fights/an.jsonl [engs] [contacts] [top] [conv]
import json, sys, math
from collections import Counter, defaultdict

src = sys.argv[1]
want = set(sys.argv[2:])
G = [json.loads(l) for l in open(src, encoding='utf-8') if l.strip()]
G = [g for g in G if 'engs' in g]
OURS = [g for g in G if g['set'] in ('rp_bb4D', 'rp_ft52D') and g['ours'] is not None]
TOP = [g for g in G if g['set'] == 'rp_top']
print(f'games: ours vs top10 {len(OURS)}, top-vs-top {len(TOP)}')


def pct(a, b):
    return f'{100.0 * a / b:.1f}%' if b else '-'


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float('nan')


def section(name):
    return not want or name in want


def bucket(r):
    if r is None:
        return 'n/a'
    return 'weaker(<0.87)' if r < 0.87 else 'stronger(>1.15)' if r > 1.15 else 'even'


BK = ['weaker(<0.87)', 'even', 'stronger(>1.15)']


def eng_rows(games, lim=2001, persp='ours', lo=0):
    # one row per engagement (>= 3 hits or a death), oriented to side A: our team (ours) / team 0 (top games, 'zero') / the starter
    rows = []
    for g in games:
        for e in g['engs']:
            if e['r0'] > lim or e['r0'] < lo or (sum(e['hits']) < 3 and sum(e['dE']) == 0):
                continue
            st = e['first']['team']
            A = g['ours'] if persp == 'ours' else (st if persp == 'starter' else 0)
            B = 1 - A
            l8 = e['loc8']  # [starter, other]
            mhA, mhB = (l8['mh'][0], l8['mh'][1]) if st == A else (l8['mh'][1], l8['mh'][0])
            hpA, hpB = (l8['hp'][0], l8['hp'][1]) if st == A else (l8['hp'][1], l8['hp'][0])
            nA, nB = (l8['n'][0], l8['n'][1]) if st == A else (l8['n'][1], l8['n'][0])
            d3 = e['dealt3']
            rows.append(dict(game=g['game'], r0=e['r0'], A=A, startA=int(st == A), mhR=(mhA / mhB) if mhB else None, hpR=(hpA / hpB) if hpB else None, nA=nA, nB=nB,
                             mhA=mhA, mhB=mhB, hpA=hpA, hpB=hpB,
                             dA=e['dE'][A], dB=e['dE'][B], d20A=e['d20'][A], d20B=e['d20'][B], bagA=e['bag'][A], bagB=e['bag'][B],
                             d3A=d3[A], d3B=d3[B], dealtA=e['dealt'][A], dealtB=e['dealt'][B], fA=e['focus'][A], fB=e['focus'][B],
                             stA=e['stuns3'][A], stB=e['stuns3'][B], c3A=e['castHits3'][A], c3B=e['castHits3'][B], p5A=e['parts5'][A], p5B=e['parts5'][B],
                             pA=e['parts'][A], pB=e['parts'][B], rdyA=e['rdy'][A], rdyB=e['rdy'][B], burnA=e['burned'][A], burnB=e['burned'][B],
                             n8A=e['n8'][A], n8B=e['n8'][B], atkA=e['attackers'][A], atkB=e['attackers'][B], hitsA=e['hits'][A], hitsB=e['hits'][B],
                             first=e['first'], aftA=e['after'][A], aftB=e['after'][B], dur=e['r1'] - e['r0'] + 1,
                             zone=e['zone0'] if A == 0 else {'own': 'their', 'their': 'own', 'mid': 'mid'}[e['zone0']]))
    return rows


def exec_line(xs, la='us', lb='them'):
    d3s = [x['d3A'] / (x['d3A'] + x['d3B']) for x in xs if x['d3A'] + x['d3B'] > 0]
    dls = [x['dealtA'] / (x['dealtA'] + x['dealtB']) for x in xs if x['dealtA'] + x['dealtB'] > 0]
    return (f'first-3r dmg share {la} {mean(d3s):.2f}, whole-fight share {mean(dls):.2f} | bodies hitting/hit by r0+5 {la} {mean([x["p5A"] for x in xs]):.2f} {lb} {mean([x["p5B"] for x in xs]):.2f} | '
            f'within 8 at start {mean([x["n8A"] for x in xs]):.2f} v {mean([x["n8B"] for x in xs]):.2f} | focus {mean([x["fA"] for x in xs]):.2f} v {mean([x["fB"] for x in xs]):.2f} | '
            f'stuns3 {mean([x["stA"] for x in xs]):.2f} v {mean([x["stB"] for x in xs]):.2f} | spell hits3 {mean([x["c3A"] for x in xs]):.2f} v {mean([x["c3B"] for x in xs]):.2f} | '
            f'slots ready {mean([x["rdyA"] for x in xs]):.2f} v {mean([x["rdyB"] for x in xs]):.2f} | camp casts 8r before {mean([x["burnA"] for x in xs]):.2f} v {mean([x["burnB"] for x in xs]):.2f} | dur {mean([x["dur"] for x in xs]):.1f}')


if section('engs'):
    for lim in (300, 2001):
        R = eng_rows(OURS, lim)
        print(f'\n=== ENGAGEMENTS in our games (r0 <= {lim}): {len(R)} ({len(R)/len(OURS):.1f}/game); A = us')
        print('who starts x local power (our max-hp sum within 8 of the first hit / theirs, at the start)')
        print(f'{"start":6s} {"power":16s} {"n":>5s} {"share":>7s} {"our d/eng":>10s} {"their d/eng":>11s} {"net/eng":>8s} {"net total":>9s} {"bags lost us/them":>18s}')
        for s in (1, 0):
            tot = [x for x in R if x['startA'] == s]
            for b in BK:
                xs = [x for x in tot if bucket(x['mhR']) == b]
                if not xs:
                    continue
                print(f'{"us" if s else "them":6s} {b:16s} {len(xs):5d} {pct(len(xs), len(tot)):>7s} {mean([x["dA"] for x in xs]):10.2f} {mean([x["dB"] for x in xs]):11.2f} {mean([x["dB"]-x["dA"] for x in xs]):8.2f} {sum(x["dB"]-x["dA"] for x in xs):9d} {sum(x["bagA"] for x in xs):9d}/{sum(x["bagB"] for x in xs):<8d}')
            print(f'{"us" if s else "them":6s} {"all":16s} {len(tot):5d} {"":>7s} {mean([x["dA"] for x in tot]):10.2f} {mean([x["dB"] for x in tot]):11.2f} {mean([x["dB"]-x["dA"] for x in tot]):8.2f} {sum(x["dB"]-x["dA"] for x in tot):9d}')
        print('execution (A = us, B = them):')
        for s in (1, 0):
            xs = [x for x in R if x['startA'] == s]
            print(f'  {"we start  " if s else "they start"} n={len(xs)}: ' + exec_line(xs))
        print('first hit: cast share, first victim farming / moving / channel in the 3 rounds before, first victim hp')
        for s in (1, 0):
            xs = [x for x in R if x['startA'] == s]
            f = [x['first'] for x in xs]
            print(f'  {"we start  " if s else "they start"}: cast {mean([y["cast"] for y in f]):.2f} | victim farming {mean([1 if y["vFarm"] else 0 for y in f]):.2f} moving {mean([1 if y["vMove"]>=2 else 0 for y in f]):.2f} chan {mean([1 if y["vChan"] else 0 for y in f]):.2f} | victim hp {mean([y["vHp"] for y in f]):.2f} | attackers ' +
                  ', '.join(f'{a} {b}' for a, b in Counter(y['a'] for y in f).most_common(6)))
        print('zone (from our side) x starter: n, our deaths, their deaths')
        for s in (1, 0):
            for z in ('own', 'mid', 'their'):
                xs = [x for x in R if x['startA'] == s and x['zone'] == z]
                print(f'  {"we start  " if s else "they start"} {z:5s} n={len(xs):4d} our deaths {sum(x["dA"] for x in xs):4d} theirs {sum(x["dB"] for x in xs):4d}')
        print('numbers within 8 at start (us - them) x starter: n, our deaths/eng, theirs/eng')
        for s in (1, 0):
            for lab, cond in (('fewer', lambda x: x['nA'] < x['nB']), ('equal', lambda x: x['nA'] == x['nB']), ('more', lambda x: x['nA'] > x['nB'])):
                xs = [x for x in R if x['startA'] == s and cond(x)]
                print(f'  {"we start  " if s else "they start"} {lab:5s} n={len(xs):4d} {mean([x["dA"] for x in xs]):.2f} {mean([x["dB"] for x in xs]):.2f}')

    for lim in (300, 2001):
        R = eng_rows(TOP, lim, 'starter')
        print(f'\n=== ENGAGEMENTS top-vs-top (r0 <= {lim}): {len(R)} ({len(R)/len(TOP):.1f}/game); A = the starter')
        print(f'{"starter power":16s} {"n":>5s} {"share":>7s} {"starter d":>10s} {"other d":>8s} {"net/eng":>8s}')
        for b in BK:
            xs = [x for x in R if bucket(x['mhR']) == b]
            print(f'{b:16s} {len(xs):5d} {pct(len(xs), len(R)):>7s} {mean([x["dA"] for x in xs]):10.2f} {mean([x["dB"] for x in xs]):8.2f} {mean([x["dB"]-x["dA"] for x in xs]):8.2f}')
        print(f'{"all":16s} {len(R):5d} {"":>7s} {mean([x["dA"] for x in R]):10.2f} {mean([x["dB"] for x in R]):8.2f} {mean([x["dB"]-x["dA"] for x in R]):8.2f}')
        print('  ' + exec_line(R, 'starter', 'other'))
        f = [x['first'] for x in R]
        print(f'  first hit cast {mean([y["cast"] for y in f]):.2f} | victim farming {mean([1 if y["vFarm"] else 0 for y in f]):.2f} moving {mean([1 if y["vMove"]>=2 else 0 for y in f]):.2f} chan {mean([1 if y["vChan"] else 0 for y in f]):.2f} | victim hp {mean([y["vHp"] for y in f]):.2f}')
    # us-started vs them-started in our games, as starter-oriented (comparable to the top table)
    for lim in (300, 2001):
        R = eng_rows(OURS, lim, 'starter')
        for who in ('us', 'them'):
            xs = [x for x in R if (x['A'] == next(g['ours'] for g in OURS if g['game'] == x['game'])) == (who == 'us')]
            print(f'\n  our games r0<={lim}, starter = {who}: n={len(xs)} starter d {mean([x["dA"] for x in xs]):.2f} other d {mean([x["dB"] for x in xs]):.2f} | ' + exec_line(xs, 'starter', 'other'))

# ------------------------------------------------------------------------------------------------ contacts: take / avoid
if section('contacts'):
    for lim in (300, 2001):
        print(f'\n=== CONTACTS (opposing bodies within 4, no champion damage within 10 tiles for 8 rounds), r <= {lim}: who hits first within 5 rounds, by A\'s local max-hp ratio')
        for label, games in (('our games, A = us', OURS), ('our games, A = them', OURS), ('top-vs-top, A = each side', TOP)):
            tab = defaultdict(Counter)
            for g in games:
                for c in g['contacts']:
                    if c['r'] > lim:
                        continue
                    if label.startswith('our'):
                        persp = [g['ours']] if label.endswith('us') else [1 - g['ours']]
                    else:
                        persp = [0, 1]
                    for A in persp:
                        B = 1 - A
                        r = c['mh'][A] / c['mh'][B] if c['mh'][B] else None
                        b = bucket(r)
                        tab[b]['n'] += 1
                        tab[b]['A' if c['first'] == A else 'B' if c['first'] == B else 'none'] += 1
                        tab['all']['n'] += 1
                        tab['all']['A' if c['first'] == A else 'B' if c['first'] == B else 'none'] += 1
            print(f'  [{label}]')
            for b in BK + ['all']:
                t = tab[b]
                print(f'    {b:16s} n={t["n"]:5d} A strikes first {pct(t["A"], t["n"]):>6s}  B strikes first {pct(t["B"], t["n"]):>6s}  nobody {pct(t["none"], t["n"]):>6s}')

# ------------------------------------------------------------------------------------------------ what wins fights (top-vs-top and ours)
if section('top'):
    import numpy as np
    try:
        import statsmodels.api as sm
    except Exception:
        sm = None

    def feats(x):
        lr = lambda a, b: math.log(max(a, 1) / max(b, 1))
        d3 = (x['d3A'] - x['d3B']) / max(1, x['d3A'] + x['d3B'])
        return [lr(x['mhA'], x['mhB']), lr(x['hpA'], x['hpB']), x['nA'] - x['nB'], x['startA'], d3, (x['fA'] or 0) - (x['fB'] or 0),
                x['stA'] - x['stB'], x['c3A'] - x['c3B'], x['p5A'] - x['p5B'], x['rdyA'] - x['rdyB']]
    names = ['log maxhp ratio (8)', 'log hp ratio (8)', 'bodies diff (8)', 'A started', 'first-3r dmg diff share', 'focus diff', 'stuns3 diff', 'spell hits3 diff', 'bodies by r0+5 diff', 'slots ready diff']
    for label, games, persp in (('top-vs-top (A = team 0)', TOP, 'zero'), ('our games (A = us)', OURS, 'ours')):
        R = [x for x in eng_rows(games, 2001, persp) if x['dA'] != x['dB']]
        X = np.array([feats(x) for x in R], dtype=float)
        y = np.array([1 if x['dB'] > x['dA'] else 0 for x in R])
        print(f'\n=== WHAT WINS DECISIVE ENGAGEMENTS ({label}): n={len(R)}, A wins {y.mean():.2f}')
        if sm is not None and len(R) > 30:
            Xs = (X - X.mean(0)) / np.where(X.std(0) > 0, X.std(0), 1)
            try:
                m = sm.Logit(y, sm.add_constant(Xs)).fit(disp=0)
                for i, n in enumerate(names):
                    print(f'   {n:26s} std coef {m.params[i+1]:+.2f}  z {m.tvalues[i+1]:+.1f}   mean {X[:, i].mean():+.2f}')
                print(f'   pseudo R2 {m.prsquared:.3f}')
            except Exception as ex:
                print('   logit failed', ex)
        # univariate: win rate of A when A has the edge on a factor
        for i, n in enumerate(names):
            hi = y[X[:, i] > 0]
            lo = y[X[:, i] < 0]
            print(f'   {n:26s} A ahead: n={len(hi):4d} win {hi.mean() if len(hi) else float("nan"):.2f} | A behind: n={len(lo):4d} win {lo.mean() if len(lo) else float("nan"):.2f}')

# ------------------------------------------------------------------------------------------------ conversion: what happens after
if section('conv'):
    def aft(xs, key):
        s = Counter()
        n = 0
        for x in xs:
            a = x[key]
            for k in ('br', 'farm', 'champ', 'mv', 'home', 'toward', 'recall', 'bank', 'still', 'caps'):
                s[k] += a[k]
            n += 1
        br = max(1, s['br'])
        return (f'body-rounds {s["br"]:6d} farm {s["farm"]/br:.2f} hit champ {s["champ"]/br:.2f} move {s["mv"]/br:.2f} (homeward {s["home"]/max(1,s["mv"]):.2f}, toward enemy {s["toward"]/max(1,s["mv"]):.2f}) '
                f'still {s["still"]/br:.2f} bank {s["bank"]/br:.3f} | captures within 20r per eng {s["caps"]/max(1,n):.2f}')
    print('\n=== AFTER THE ENGAGEMENT (participants alive, 15 rounds after its last hit)')
    R = [x for x in eng_rows(TOP, 2001, 'zero')]
    win = [dict(x, aftW=x['aftA'], aftL=x['aftB']) for x in R if x['dB'] > x['dA']] + [dict(x, aftW=x['aftB'], aftL=x['aftA']) for x in R if x['dA'] > x['dB']]
    even = R and [x for x in R if x['dA'] == x['dB']]
    print('  top-vs-top winner : ' + aft(win, 'aftW'))
    print('  top-vs-top loser  : ' + aft(win, 'aftL'))
    print('  top-vs-top no-kill (team 0 / team 1): ' + aft(even, 'aftA'))
    R = eng_rows(OURS, 2001)
    wU = [x for x in R if x['dB'] > x['dA']]
    wT = [x for x in R if x['dA'] > x['dB']]
    ev = [x for x in R if x['dA'] == x['dB']]
    print(f'  ours, we won ({len(wU)})   us  : ' + aft(wU, 'aftA'))
    print(f'  ours, we won             them: ' + aft(wU, 'aftB'))
    print(f'  ours, they won ({len(wT)}) them: ' + aft(wT, 'aftB'))
    print(f'  ours, they won           us  : ' + aft(wT, 'aftA'))
    print(f'  ours, no kill ({len(ev)})  us  : ' + aft(ev, 'aftA'))
    print(f'  ours, no kill            them: ' + aft(ev, 'aftB'))
