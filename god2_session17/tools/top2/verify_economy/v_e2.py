# E2 verification: tribute counts W vs L (and normalised by captured gems), banked by r300, bag sizes, bank decisions after a
# capture (ifish / cm / pbg / opponents / W / L), death rate by bag, pbg-vs-ifish tribute counts, example game.
import sys, os, math
from collections import defaultdict, Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vagg import *

G = load()
print('games', len(G))


def starts(g, t):
    return sum(1 for x in g['tribs'] if x['team'] == t)


def done(g, t):
    return sum(1 for x in g['tribs'] if x['team'] == t and x['out'] == 'done')


def capg(g, t):
    return sum(c['gems'] for c in g['caps'] if c['team'] == t)


def medbag(g, t):
    b = [x['got'] for x in g['tribs'] if x['team'] == t and x['out'] == 'done' and x['got']]
    return med(b) if b else None


print('\n== W vs L ==')
wl_table(G, starts, 'tribute starts')
wl_table(G, done, 'tributes completed')
wl_table(G, lambda g, t: g['sub300'][t], 'banked at r300')
wl_table(G, medbag, 'median banked bag')
wl_table(G, capg, 'captured gems')
wl_table(G, lambda g, t: 100 * done(g, t) / capg(g, t) if capg(g, t) else None, 'completed tributes per 100 captured gems')
wl_table(G, lambda g, t: sum(1 for x in g['tribs'] if x['team'] == t and x['out'] == 'done' and x['r0'] <= 300), 'completed by r300')
wl_table(G, lambda g, t: sum(c['gems'] for c in g['caps'] if c['team'] == t and c['r'] <= 300), 'captured gems by r300')
# matched comparison: matches where both teams captured within 10% of each other
pairs = []
for g in G:
    w = g['win']
    a, b = capg(g, w), capg(g, 1 - w)
    if a and b and abs(a - b) / max(a, b) <= 0.15:
        pairs.append((done(g, w), done(g, 1 - w)))
print(f'matches with captured gems within 15%: n {len(pairs)} completed W {mean([p[0] for p in pairs]):.1f} L {mean([p[1] for p in pairs]):.1f} P(w>l) {pwl(pairs):.2f}')

print('\n== S vs O tributes / banked r300 ==')
for k in KEYS:
    so = so_games(G, k)
    if not so:
        continue
    print(f"{k:9s} n {len(so):3d} completed S {mean([done(g, s) for g, s in so]):5.1f} O {mean([done(g, 1 - s) for g, s in so]):5.1f} | starts S {mean([starts(g, s) for g, s in so]):5.1f} O {mean([starts(g, 1 - s) for g, s in so]):5.1f}"
          f" | banked r300 median S {med([g['sub300'][s] for g, s in so]):5.0f} O {med([g['sub300'][1 - s] for g, s in so]):5.0f}"
          f" | win {mean([1 if g['win'] == s else 0 for g, s in so]):.2f} | wins end median r {med([g['final'] for g, s in so if g['win'] == s])}")

print('\n== bank decision after a capture (share followed by a tribute start before the next capture; n) ==')
BB = [(1, 19), (20, 39), (40, 79), (80, 149), (150, 99999)]
DB = [(0, 5), (6, 10), (11, 20), (21, 9999)]


def table(rows, label):
    print(f'-- {label} (n captures {len(rows)})')
    for lo, hi in BB:
        cells = []
        for dlo, dhi in DB:
            sel = [r for r in rows if lo <= r[3] <= hi and r[4] is not None and dlo <= r[4] <= dhi]
            cells.append(f'{mean([r[5] for r in sel]):4.0%} ({len(sel):4d})' if sel else '   -        ')
        print(f'   bag {lo:3d}-{hi if hi < 9999 else "+":>4}: ' + ' | '.join(cells))


for k in ('ifish', 'cm', 'pbg', 'pantheon'):
    so = so_games(G, k)
    S = [r for g, s in so for r in g['bdec'] if r[1] == s]
    O = [r for g, s in so for r in g['bdec'] if r[1] != s]
    table(S, k + ' S')
    table(O, k + ' O')
Wr = [r for g in G for r in g['bdec'] if r[1] == g['win']]
Lr = [r for g in G for r in g['bdec'] if r[1] != g['win']]
table(Wr, 'pooled winners')
table(Lr, 'pooled losers')
# rule hit rates: share of captures where the proposed rule fires, and how often W / L / ifish bank in those cases
def rule(r):
    bag, d = r[3], r[4]
    if d is None:
        return False
    return (bag >= 20 and d <= 5) or (bag >= 40 and d <= 10) or bag >= 80


for lab, rows in (('ifish S', [r for g, s in so_games(G, 'ifish') for r in g['bdec'] if r[1] == s]),
                  ('ifish O', [r for g, s in so_games(G, 'ifish') for r in g['bdec'] if r[1] != s]), ('W', Wr), ('L', Lr)):
    f = [r for r in rows if rule(r)]
    nf = [r for r in rows if not rule(r)]
    print(f'{lab:8s} rule fires on {len(f)/max(1,len(rows)):.0%} of captures; banked when it fires {mean([r[5] for r in f]):.0%}, when not {mean([r[5] for r in nf]):.0%}')
# start delay after capture
for lab, rows in (('W', Wr), ('L', Lr)):
    d1 = [r[6] for r in rows if r[5] and r[3] < 80 and r[6] is not None]
    d2 = [r[6] for r in rows if r[5] and r[3] >= 80 and r[6] is not None]
    print(f'{lab} start delay after capture: bag<80 median {med(d1)} | bag>=80 median {med(d2)}')

print('\n== champion-kill deaths per 1,000 body-rounds by bag ==')
agg = defaultdict(lambda: [0, 0])
aggW = defaultdict(lambda: [0, 0])
aggL = defaultdict(lambda: [0, 0])
for g in G:
    for t, b, br, d in g['expo']:
        agg[b][0] += br
        agg[b][1] += d
        (aggW if t == g['win'] else aggL)[b][0] += br
        (aggW if t == g['win'] else aggL)[b][1] += d
for b in ('empty', '1-49', '50-149', '150-399', '400+'):
    print(f'{b:8s} all {1000*agg[b][1]/max(1,agg[b][0]):.2f} (deaths {agg[b][1]}, body-rounds {agg[b][0]})  W {1000*aggW[b][1]/max(1,aggW[b][0]):.2f}  L {1000*aggL[b][1]/max(1,aggL[b][0]):.2f}')

print('\n== pbg vs ifish games ==')
cnt = Counter()
for g in G:
    tk = g.get('tkeys', g['keys'])
    if 'pbg' in tk and 'ifish' in tk:
        p, f = tk['pbg'], tk['ifish']
        dp, df = done(g, p), done(g, f)
        cp, cf = capg(g, p), capg(g, f)
        w = 'pbg' if g['win'] == p else 'ifish'
        more = 'pbg' if dp > df else ('ifish' if df > dp else 'tie')
        morecap = 'pbg' if cp > cf else 'ifish'
        cnt[(w, more)] += 1
        cnt[('cap', w == morecap)] += 1
        print(f"  {g['base']:32s} winner {w:5s} completed pbg {dp:3d} ifish {df:3d} | captured pbg {cp:5d} ifish {cf:5d} | final {g['final']} sub {g['sub']} pbg side {p}")
print(dict(cnt))

print('\n== example ifish 00road_of_riches_f2d12f7c ==')
for g in G:
    if g['base'].startswith('00road_of_riches_f2d12f7c'):
        s = g['keys'].get('ifish')
        tr = [x for x in g['tribs'] if x['team'] == s and x['out'] == 'done' and x['r0'] <= 300]
        print('ifish completed starts by r300', len(tr), 'bags', sorted(x['got'] for x in tr), 'banked r300', g['sub300'][s], 'opp', g['sub300'][1 - s])
