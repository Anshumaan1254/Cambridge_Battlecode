"""A-B-A walking in G20_TRACE stdout (PT lines: turn-start position + the turn's decision path / engage code / task):
for every body with start(r) = A, start(r+1) = B != A, start(r+2) = A, count the (forth, back) decisions, split by the nearest visible
enemy at turn r (ne). path codes: 1 combat(fight) 2 combat(other) 3 safety 4 tribute 5 home_trip 6 shop 7 alert 8 farm 9 home ...
    python3 -I aba_reasons.py STDOUT..."""
import collections, re, sys
PT = re.compile(rb'PT r=(\d+) i=(\d+) path=(\d+) eng=(\d+) task=(\d+) tg=(-?\d+) hp=(\d+)/(\d+) bag=(\d+) x=(\d+) y=(\d+) ne=(\d+)')
pairs = collections.Counter(); single = collections.Counter(); tot = collections.Counter(); n_aba = collections.Counter()
for f in sys.argv[1:]:
    T = {}
    for m in PT.finditer(open(f, 'rb').read()):
        r, i, path, eng, task, tg, hp, mhp, bag, x, y, ne = map(int, m.groups())
        T[(i, r)] = (path, eng, task, x, y, ne, hp, mhp)
    for (i, r), a in T.items():
        b, c = T.get((i, r + 1)), T.get((i, r + 2))
        zone = 'near' if a[5] <= 6 else 'far'
        tot[zone] += 1
        if not b or not c:
            continue
        if (a[3], a[4]) == (c[3], c[4]) and (b[3], b[4]) != (a[3], a[4]):
            n_aba[zone] += 1
            fk = f"p{a[0]}e{a[1]}t{a[2]}"; bk = f"p{b[0]}e{b[1]}t{b[2]}"
            pairs[(zone, fk, bk)] += 1
            single[(zone, 'forth', fk)] += 1; single[(zone, 'back', bk)] += 1
for z in ('near', 'far'):
    print(f"{z}: {n_aba[z]} A-B-A in {tot[z]} body-turns = {1000 * n_aba[z] / max(1, tot[z]):.1f}/1000")
    for (zz, fk, bk), n in pairs.most_common(60):
        if zz == z and n >= 3:
            print(f"   {n:4d}  forth {fk:12s} back {bk}")
