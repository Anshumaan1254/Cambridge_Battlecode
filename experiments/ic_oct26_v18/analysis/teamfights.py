"""Team fights: rounds where some body of each side has 2+ enemies within 5. Episodes = runs of such rounds (gap <= 3). Per episode:
bodies of each side within 6 of the fight centre at its start, deaths of each side during it (+5 rounds), health lost. Grouped by
the numbers (ours - theirs at the start).
    python3 -I teamfights.py INDEX [sets]"""
import sys, os, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icx
sets = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None
B = collections.defaultdict(lambda: collections.Counter()); n = 0; neps = 0
for g in icx.games(sys.argv[1], sets):
    n += 1
    deaths = collections.defaultdict(list)
    for e in g.ev:
        if e['k'] == 'Death' and 'who' in e:
            deaths[e['r']].append(g.team[e['who']])
    hot = []
    for r in g.rounds:
        s = g.R[r]; al = [c for c in s['ch'] if c[7]]
        found = None
        for c in al:
            en = [q for q in al if q[1] != c[1] and icx.cheb((q[3], q[4]), (c[3], c[4])) <= 5]
            if len(en) >= 2:
                found = (c[3], c[4]); break
        if found:
            hot.append((r, found))
    eps = []
    for r, p in hot:
        if eps and r - eps[-1][-1][0] <= 3:
            eps[-1].append((r, p))
        else:
            eps.append([(r, p)])
    for ep in eps:
        r0, p0 = ep[0]; r1 = ep[-1][0]
        s = g.R[r0]
        cnt = {t: sum(1 for c in s['ch'] if c[7] and c[1] == t and icx.cheb((c[3], c[4]), p0) <= 6) for t in (0, 1)}
        hp0 = {t: sum(c[5] for c in s['ch'] if c[7] and c[1] == t and icx.cheb((c[3], c[4]), p0) <= 6) for t in (0, 1)}
        d = collections.Counter()
        for r in range(r0, r1 + 6):
            for t in deaths.get(r, []):
                d[t] += 1
        us, them = g.ours, g.ic
        diff = cnt[us] - cnt[them]
        k = 'even' if diff == 0 else ('up' if diff > 0 else 'down')
        B[k]['eps'] += 1; B[k]['us_dead'] += d[us]; B[k]['them_dead'] += d[them]
        B[k]['us_n'] += cnt[us]; B[k]['them_n'] += cnt[them]
        B[k]['won'] += 1 if d[them] > d[us] else 0; B[k]['lost'] += 1 if d[us] > d[them] else 0
        B['all']['eps'] += 1; B['all']['us_dead'] += d[us]; B['all']['them_dead'] += d[them]
        B['all']['won'] += 1 if d[them] > d[us] else 0; B['all']['lost'] += 1 if d[us] > d[them] else 0
print('games', n)
for k in ('all', 'up', 'even', 'down'):
    b = B[k]; e = max(1, b['eps'])
    print(f"{k:5s} episodes/game {b['eps'] / n:5.1f}  bodies us/them {b['us_n'] / e:4.2f}/{b['them_n'] / e:4.2f}  deaths/ep us {b['us_dead'] / e:4.2f} them {b['them_dead'] / e:4.2f}  won {b['won'] / e:4.2f} lost {b['lost'] / e:4.2f}")
