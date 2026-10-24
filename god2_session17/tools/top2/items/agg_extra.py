# Extra item / consumable tables from ix.mjs output: long-tail emblem sequences, who places locks, lock-over-lock, crystals by map,
# consumable purchase context, ward cadence, and examples with file + round.
#   python tools/top2/items/agg_extra.py C:/battlecode/cache/top2_items/ix_all.jsonl
import sys, json, collections
sys.path.insert(0, 'tools/top2/items')
from common import *

IX = sys.argv[1]
idx = load_index()
games = []
for l in open(IX, encoding='utf-8'):
    try:
        g = json.loads(l)
    except Exception:
        continue
    stem = g['file'].replace('.repl26a', '')
    if stem in idx:
        games.append((stem, g))
P = print

# ------------------------------------------------------------ long tail
P('## A. Emblem sequences (first 8 emblems, completion order), most common per team x champion (study team only)')
seqs = collections.defaultdict(collections.Counter)
for stem, g in games:
    for st in idx[stem]:
        for b in g['B']:
            if b['t'] != st['ti']:
                continue
            e = [x[1] for x in emblem_order(b['buys'])]
            seqs[(st['key'], b['ty'])]['>'.join(e[:8]) or '(none)'] += 1
for (key, ty), c in sorted(seqs.items(), key=lambda kv: (KEYS.index(kv[0][0]), -sum(kv[1].values()))):
    n = sum(c.values())
    if n < 5:
        continue
    P(f'{key} {SHORT[ty]} (n={n}): ' + ' | '.join(f'{s} x{v}' for s, v in c.most_common(3)))

# ------------------------------------------------------------ emblem family share over the whole game (study vs opp), per champion
P('\n## B. Final emblem families per body (mean count per body at game end), study team vs its opponents, all champions')
for key in KEYS:
    for grp in 'SO':
        fam = collections.Counter(); nb = 0
        for stem, g in games:
            for st in idx[stem]:
                if st['key'] != key:
                    continue
                for b in g['B']:
                    if (b['t'] == st['ti']) != (grp == 'S'):
                        continue
                    nb += 1
                    for rr, c in emblem_order(b['buys']):
                        fam[c[0]] += 1
        if nb:
            P(f'{key} {grp} bodies {nb}: ' + ', '.join(f'{f} {v/nb:.2f}' for f, v in fam.most_common()))

# ------------------------------------------------------------ who places locks, lock over lock, lock timing
P('\n## C. Lock placers by champion (study team), lock-over-lock, lock round distribution')
pl = collections.defaultdict(collections.Counter)
ov = collections.Counter()
rounds = collections.defaultdict(list)
lockbuy = collections.defaultdict(list)
for stem, g in games:
    team = {b['i']: b['t'] for b in g['B']}
    ty = {b['i']: b['ty'] for b in g['B']}
    byalt = collections.defaultdict(list)
    for x in g['locks']:
        byalt[tuple(x['a'])].append(x)
    for a, L in byalt.items():
        L.sort(key=lambda x: x['r'])
        for i in range(1, len(L)):
            p, c = L[i - 1], L[i]
            if p['t'] != c['t'] and (p['cleared'] < 0 or p['cleared'] > c['r']):
                ov[(stem, c['t'])] += 1
    for st in idx[stem]:
        for x in g['locks']:
            if team[x['who']] == st['ti']:
                pl[st['key']][SHORT[ty[x['who']]]] += 1
                rounds[st['key']].append(x['r'])
        for b in g['B']:
            if b['t'] == st['ti']:
                for q in b['buys']:
                    if q[1] == 102:
                        lockbuy[st['key']].append((q[0], q[3], q[4]))
for key in KEYS:
    if pl[key]:
        rs = sorted(rounds[key])
        P(f'{key}: placers {dict(pl[key].most_common())}; placement round quartiles {rs[len(rs)//4]}/{rs[len(rs)//2]}/{rs[3*len(rs)//4]}; '
          f'buys {len(lockbuy[key])}, gold before median {med([x[1] for x in lockbuy[key]])}, bought while dead {pct(sum(1 for x in lockbuy[key] if x[2]==0), len(lockbuy[key]))}')
P(f'lock placed on an altar holding an uncleared enemy lock: {sum(ov.values())} cases in {len(ov)} team-games')

# ------------------------------------------------------------ crystals by map and champion
P('\n## D. Teleport crystal uses by map and champion (study teams only)')
cm = collections.defaultdict(collections.Counter)
cc = collections.defaultdict(collections.Counter)
mapsn = collections.defaultdict(collections.Counter)
tex = collections.defaultdict(list)
for stem, g in games:
    ty = {b['i']: b['ty'] for b in g['B']}
    team = {b['i']: b['t'] for b in g['B']}
    for st in idx[stem]:
        mapsn[st['key']][st['map']] += 1
        for x in g['tele']:
            if team[x['who']] == st['ti']:
                cm[st['key']][st['map']] += 1
                cc[st['key']][SHORT[ty[x['who']]]] += 1
                if len(tex[st['key']]) < 8:
                    tex[st['key']].append((stem, x['r'], SHORT[ty[x['who']]], x['from'], x['to'], x['walk'], x['bag'], x['campD']))
for key in KEYS:
    if cm[key]:
        tot = sum(cm[key].values())
        P(f'{key}: {tot} uses; by champion {dict(cc[key].most_common())}; by map (uses per game) ' + ', '.join(f'{m} {v/mapsn[key][m]:.1f}' for m, v in cm[key].most_common(10)))
        for e in tex[key][:5]:
            P(f'   ex: {e}')

# ------------------------------------------------------------ ward cadence
P('\n## E. Ward cadence: rounds between consecutive wards of the same body (charge recharges in 10 turns)')
for key in KEYS:
    for grp in 'SO':
        gaps = []
        for stem, g in games:
            for st in idx[stem]:
                if st['key'] != key:
                    continue
                T = st['ti'] if grp == 'S' else 1 - st['ti']
                mine = {b['i'] for b in g['B'] if b['t'] == T}
                by = collections.defaultdict(list)
                for w in g['wards']:
                    if w[1] in mine:
                        by[w[1]].append(w[0])
                for L in by.values():
                    L.sort()
                    gaps += [L[i] - L[i - 1] for i in range(1, len(L))]
        if gaps:
            gaps.sort()
            P(f'{key} {grp}: {len(gaps)} gaps; quartiles {gaps[len(gaps)//4]}/{gaps[len(gaps)//2]}/{gaps[3*len(gaps)//4]}; share <= 12 rounds {pct(sum(1 for x in gaps if x <= 12), len(gaps))}')

# ------------------------------------------------------------ Prism bag economy
P('\n## F. Prism bag economy (bag = carried gems; focus +1.5 per gem): bag at checkpoints, tributes, deaths with bags')
for key in KEYS:
    for grp in 'SO':
        bags = collections.defaultdict(list); tr = []; dth = []; n = 0; mx = []
        for stem, g in games:
            for st in idx[stem]:
                if st['key'] != key:
                    continue
                T = st['ti'] if grp == 'S' else 1 - st['ti']
                for b in g['B']:
                    if b['t'] != T or b['ty'] != 'Prism':
                        continue
                    n += 1
                    for r in (200, 400, 600, 800, 1000):
                        c = b['cp'].get(str(r))
                        if c and c[2]:
                            bags[r].append(c[4])
                    tr += [t for t in g['tribs'] if t[1] == b['i'] and t[5] == 'ok']
                    dth += b['deaths']
                    mx.append(max([c[4] for c in b['cp'].values()] or [0]))
        if n < 3:
            continue
        P(f'{key} {grp}: {n} Prism bodies; mean bag (alive) r200/400/600/800/1000: ' + '/'.join(fmt(mean(bags[r])) for r in (200, 400, 600, 800, 1000))
          + f'; max checkpoint bag median {fmt(med(mx))}; tributes/body {len(tr)/n:.2f} mean gems {fmt(mean([t[7] for t in tr]))}; deaths/body {len(dth)/n:.2f}, mean bag lost {fmt(mean([d[1] for d in dth]))}, bags >= 100 lost {sum(1 for d in dth if d[1] >= 100)}')
