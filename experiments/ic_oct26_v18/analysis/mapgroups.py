"""Per map: which groups each side captures (mirror groups aligned by distance to our / their spawn). Mean per game.
    python3 -I mapgroups.py INDEX MAP [sets] [--res loss|win]"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icx
args = [a for a in sys.argv[1:] if not a.startswith('--')]
res = sys.argv[sys.argv.index('--res') + 1] if '--res' in sys.argv else None
if res:
    args = [a for a in args if a != res]
idx, mp = args[0], args[1]
sets = set(args[2].split(',')) if len(args) > 2 else None
A = collections.defaultdict(collections.Counter)
n = 0; fin = []
for g in icx.games(idx, sets):
    if g.map != mp or not g.D or (res and g.res != res):
        continue
    n += 1; fin.append((g.final, g.res))
    sp = g.D['spawn']; tg = g.D['tile_group']; gid = {x['id']: x for x in g.D['groups']}
    for e in g.ev:
        if e['k'] == 'CaptureGems':
            G = tg.get(tuple(e['at']))
            if G is None:
                continue
            x = gid[G]; c = x['center']
            key = (round(icx.cheb(c, sp[g.ours])), round(icx.cheb(c, sp[g.ic])), x['gems'], x['gold'], x['respawn'], ''.join(f"{k[0]}{v}" for k, v in sorted(x['kinds'].items())))
            s = icx.who_side(g, g.team[e['who']])
            A[key][s + '_n'] += 1; A[key][s] += e['gems']
        if e['k'] == 'Death' and 'who' in e:
            s = icx.who_side(g, g.team[e['who']])
            A[('deaths',)][s] += 1
    # all groups appear even if never captured
    for x in g.D['groups']:
        c = x['center']
        key = (round(icx.cheb(c, sp[g.ours])), round(icx.cheb(c, sp[g.ic])), x['gems'], x['gold'], x['respawn'], ''.join(f"{k[0]}{v}" for k, v in sorted(x['kinds'].items())))
        A[key]['seen'] += 1
print(mp, 'games', n, 'final/result', fin)
print(f"{'d_us':>5s} {'d_op':>5s} {'gems':>5s} {'gold':>5s} {'resp':>4s} kinds    | us caps/g gems/g | them caps/g gems/g")
tu = tt = 0
for k in sorted((k for k in A if len(k) > 1), key=lambda k: (k[0] - k[1], k[0])):
    a = A[k]
    if a['us'] + a['ic'] == 0 and k[2] < 8:
        continue
    print(f"{k[0]:5d} {k[1]:5d} {k[2]:5d} {k[3]:5d} {k[4]:4d} {k[5]:8s} | {a['us_n'] / n:6.1f} {a['us'] / n:7.1f} | {a['ic_n'] / n:6.1f} {a['ic'] / n:7.1f}")
    tu += a['us']; tt += a['ic']
print(f"total captured/game us {tu / n:.0f} them {tt / n:.0f}; deaths/game us {A[('deaths',)]['us'] / n:.1f} them {A[('deaths',)]['ic'] / n:.1f}")
