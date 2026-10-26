"""Deaths in context: per side, deaths per game by phase and zone, allies / enemies within 5 at the death, killer type.
    python3 -I deaths_ctx.py INDEX [sets]"""
import sys, os, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icx
sets = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None
D = collections.Counter(); C = collections.defaultdict(list); n = 0
for g in icx.games(sys.argv[1], sets):
    if not g.D:
        continue
    n += 1; sp = g.D['spawn']
    for e in g.ev:
        if e['k'] != 'Death' or 'who' not in e:
            continue
        t = g.team[e['who']]; s = icx.who_side(g, t); at = tuple(e['at'])
        da, db = icx.cheb(at, sp[t]), icx.cheb(at, sp[1 - t])
        z = 'M' if abs(da - db) <= 4 else ('O' if da < db else 'T')
        ph = 'p0' if e['r'] < 150 else 'p1' if e['r'] < 400 else 'p2'
        D[(s, ph, z)] += 1
        snap = g.R.get(e['r'] - 1) or g.R.get(e['r'])
        if snap:
            al = sum(1 for c in snap['ch'] if c[1] == t and c[7] and c[0] != e['who'] and icx.cheb((c[3], c[4]), at) <= 5)
            en = sum(1 for c in snap['ch'] if c[1] != t and c[7] and icx.cheb((c[3], c[4]), at) <= 5)
            C[(s, 'allies5')].append(al); C[(s, 'enemies5')].append(en); C[(s, 'outnum')].append(1 if en > al + 1 else 0)
        C[(s, 'bag')].append(e.get('bag', 0))
print('games', n)
for s in ('us', 'ic'):
    print(s, ' '.join(f"{ph}{z}:{D[(s, ph, z)] / n:4.1f}" for ph in ('p0', 'p1', 'p2') for z in 'OMT'),
          '| allies5', round(st.mean(C[(s, 'allies5')]), 2), 'enemies5', round(st.mean(C[(s, 'enemies5')]), 2), 'outnumbered', round(st.mean(C[(s, 'outnum')]), 2), 'bag', round(st.mean(C[(s, 'bag')]), 1))
