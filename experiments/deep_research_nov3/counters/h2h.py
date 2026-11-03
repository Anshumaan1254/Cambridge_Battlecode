#!/usr/bin/env python3
"""Head-to-head structure of the top-30 (CAMBC 2026a, engine 2.0.0) from experiments/top30_nov3/matches_current.jsonl.

Bradley-Terry (Elo-scale) fit on all 6,795 ranked matches of the 45 teams, then per top-30 team:
  pair residuals (W - E), non-transitive triples, map and map-class residuals, side residuals, opponent-draft residuals.
Usage: nice -n 19 python3 -I h2h.py   -> out/h2h.txt, out/h2h.json
"""
import json, math, csv, itertools
from collections import defaultdict, Counter

BASE = '/home/claude/cambridge_battlecode/experiments/top30_nov3'
OUT = '/home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out'
CH = ['Ryth', 'Vesper', 'Vendetta', 'C&I', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HoR']

lad = json.load(open(f'{BASE}/ladder.json'))['teams']
rank = {t['teamId']: t['rank'] for t in lad}
name = {t['teamId']: t['name'] for t in lad}
lrat = {t['teamId']: t['rating'] for t in lad}
top30 = [t['teamId'] for t in lad if t['rank'] <= 30]
top10 = [t['teamId'] for t in lad if t['rank'] <= 10]
rows = [json.loads(l) for l in open(f'{BASE}/matches_current.jsonl')]

mf = {}
with open(f'{BASE}/draft_bank/out/map_features.csv') as f:
    for r in csv.DictReader(f):
        mf[r['map']] = r

# ---------------- games list
G = []
for m in rows:
    a, b = m['teams']
    if a['result'] == b['result']:
        continue
    w = a if a['result'] == 'win' else b
    l = b if w is a else a
    G.append({'mid': m['matchId'], 'map': m['map'], 'w': w['teamId'], 'l': l['teamId'], 'wside': w['side'], 'end': m['endReason'],
              'wd': tuple(sorted(w['draftPicks'])), 'ld': tuple(sorted(l['draftPicks'])), 'n': len(w['draftPicks']),
              'created': m['createdAt']})
teams = sorted({g['w'] for g in G} | {g['l'] for g in G})

# ---------------- Bradley-Terry by MM with a prior (1 win + 1 loss vs a virtual 1.0 team)
p = {t: 1.0 for t in teams}
wins = Counter(g['w'] for g in G)
pairs = Counter()
for g in G:
    pairs[tuple(sorted((g['w'], g['l'])))] += 1
for it in range(500):
    newp = {}
    for t in teams:
        den = 2.0 / (p[t] + 1.0)
        for (x, y), n in pairs.items():
            if t == x:
                den += n / (p[t] + p[y])
            elif t == y:
                den += n / (p[t] + p[x])
        newp[t] = (wins[t] + 1.0) / den
    gm = math.exp(sum(math.log(v) for v in newp.values()) / len(newp))
    newp = {t: v / gm for t, v in newp.items()}
    diff = max(abs(math.log(newp[t] / p[t])) for t in teams)
    p = newp
    if diff < 1e-9:
        break
R = {t: 400 * math.log10(p[t]) for t in teams}
kt = [t for t in teams if t in lrat]
off = sum(lrat[t] for t in kt) / len(kt) - sum(R[t] for t in kt) / len(kt)
R = {t: v + off for t, v in R.items()}


def E(a, b):
    return 1 / (1 + 10 ** ((R[b] - R[a]) / 400))


for g in G:
    g['pw'] = E(g['w'], g['l'])  # expected prob the winner wins

out = []
P = lambda *a: out.append(' '.join(str(x) for x in a))
J = {}

# ---------------- per team summary
P('=== 1. Team strength: ladder rating, BT rating fitted on these 6,795 games, record vs all / vs top-30 / vs top-10')
P(f"{'rk':>3} {'team':28} {'ladder':>6} {'BT':>6} {'all W/N':>9} {'top30 W/N':>10} {'top10 W/N':>10}")
rec = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # t -> bucket -> [w, n]
for g in G:
    for t, o, won in ((g['w'], g['l'], 1), (g['l'], g['w'], 0)):
        for bk, ok in (('all', True), ('t30', rank.get(o, 99) <= 30), ('t10', rank.get(o, 99) <= 10)):
            if ok:
                rec[t][bk][0] += won
                rec[t][bk][1] += 1
for t in top30:
    r = rec[t]
    P(f"{rank[t]:>3} {name[t][:28]:28} {lrat[t]:6.0f} {R[t]:6.0f} {r['all'][0]:>4}/{r['all'][1]:<4} {r['t30'][0]:>4}/{r['t30'][1]:<5} {r['t10'][0]:>4}/{r['t10'][1]:<5}")
J['bt'] = {name.get(t, t[:8]): round(R[t], 1) for t in teams}

# ---------------- pair matrix among top-30 + residuals
pw = defaultdict(lambda: [0, 0, 0.0])  # (a,b) -> [a wins, n, expected a wins]
for g in G:
    a, b = g['w'], g['l']
    pw[(a, b)][0] += 1
    pw[(a, b)][1] += 1
    pw[(a, b)][2] += g['pw']
    pw[(b, a)][1] += 1
    pw[(b, a)][2] += 1 - g['pw']
P('\n=== 2. Top-10 head-to-head matrix (row team wins / games vs column team), all maps')
hdr = '      ' + ' '.join(f'{rank[t]:>6}' for t in top10)
P(hdr)
for a in top10:
    cells = []
    for b in top10:
        if a == b:
            cells.append('     -')
        else:
            w, n, e = pw[(a, b)]
            cells.append(f'{w:>3}/{n:<2}' if n else '     .')
    P(f'{rank[a]:>3} {name[a][:2]:2} ' + ' '.join(cells))

P('\n=== 3. Biggest pair residuals among the top-30 (wins - BT expectation; n >= 6). Negative = the row team underperforms vs that opponent')
resid_pairs = []
for a in top30:
    for b in top30:
        if a == b:
            continue
        w, n, e = pw[(a, b)]
        if n >= 6:
            sd = math.sqrt(max(1e-9, sum(1 for _ in range(1)) * e * (1 - e / n)))
            z = (w - e) / math.sqrt(max(1e-6, e * (1 - e / n)))
            resid_pairs.append((z, a, b, w, n, e))
resid_pairs.sort()
seen = set()
k = 0
for z, a, b, w, n, e in resid_pairs:
    key = tuple(sorted((a, b)))
    if key in seen:
        continue
    seen.add(key)
    P(f"  #{rank[a]:>2} {name[a][:22]:22} vs #{rank[b]:>2} {name[b][:22]:22}: {w}/{n} wins, expected {e:.1f}, resid {w - e:+.1f}, z {z:+.2f}")
    k += 1
    if k >= 30:
        break

# ---------------- non-transitive triples among top-30: A beats B (>= 60%, n >= 5) for each edge
P('\n=== 4. Non-transitive triples among the top-30 (each edge: >= 60% wins, n >= 5 games)')
beats = {}
for a in top30:
    for b in top30:
        if a != b:
            w, n, e = pw[(a, b)]
            if n >= 5 and w / n >= 0.6:
                beats[(a, b)] = (w, n)
cyc = []
for a, b, c in itertools.permutations(top30, 3):
    if a < b and a < c and (a, b) in beats and (b, c) in beats and (c, a) in beats:
        s = min(beats[(a, b)][0] / beats[(a, b)][1], beats[(b, c)][0] / beats[(b, c)][1], beats[(c, a)][0] / beats[(c, a)][1])
        cyc.append((s, a, b, c))
cyc.sort(reverse=True)
P(f'  {len(cyc)} cycles; total directed dominance edges {len(beats)}')
top10cyc = [x for x in cyc if sum(1 for t in x[1:] if rank[t] <= 10) >= 2]
for s, a, b, c in (top10cyc[:25]):
    P(f"  #{rank[a]} {name[a][:18]} > #{rank[b]} {name[b][:18]} ({beats[(a, b)][0]}/{beats[(a, b)][1]}) > #{rank[c]} {name[c][:18]} ({beats[(b, c)][0]}/{beats[(b, c)][1]}) > #{rank[a]} ({beats[(c, a)][0]}/{beats[(c, a)][1]})")
J['cycles'] = [[name[a], name[b], name[c]] for s, a, b, c in cyc]

# ---------------- teams that beat each top team above expectation (any opponent of the 45, n >= 6)
P('\n=== 5. For each top-10 team: opponents with the largest positive residual against it (n >= 5), i.e. who beats it more than ratings predict')
for t in top10:
    lst = []
    for o in teams:
        if o == t:
            continue
        w, n, e = pw[(o, t)]
        if n >= 5:
            lst.append((w - e, o, w, n, e))
    lst.sort(reverse=True)
    P(f"  #{rank[t]} {name[t]}: " + '; '.join(f"#{rank.get(o, '?')} {name.get(o, o[:8])[:16]} {w}/{n} (E {e:.1f}, {w - e:+.1f})" for d, o, w, n, e in lst[:6]))

# ---------------- maps: per team per map residual; map classes
P('\n=== 6. Map residuals per top-30 team: maps where the team scores below its BT expectation (sum over games; n >= 4, resid <= -1.5)')
tm = defaultdict(lambda: [0, 0, 0.0])
for g in G:
    for t, won, e in ((g['w'], 1, g['pw']), (g['l'], 0, 1 - g['pw'])):
        x = tm[(t, g['map'])]
        x[0] += won
        x[1] += 1
        x[2] += e
J['maps'] = {}
for t in top30:
    lst = []
    for (tt, mp), (w, n, e) in tm.items():
        if tt == t and n >= 4:
            lst.append((w - e, mp, w, n, e))
    lst.sort()
    bad = [x for x in lst if x[0] <= -1.5][:8]
    good = [x for x in sorted(lst, reverse=True) if x[0] >= 1.5][:5]
    J['maps'][name[t]] = {'bad': [(mp, w, n, round(e, 1)) for d, mp, w, n, e in bad], 'good': [(mp, w, n, round(e, 1)) for d, mp, w, n, e in good]}
    P(f"  #{rank[t]:>2} {name[t][:24]:24} worst: " + ', '.join(f"{mp} {w}/{n} (E{e:.1f})" for d, mp, w, n, e in bad))
    P(f"      {'':24} best:  " + ', '.join(f"{mp} {w}/{n} (E{e:.1f})" for d, mp, w, n, e in good))

# map classes
def classes(mp):
    f = mf.get(mp)
    if not f:
        return {}
    c = {}
    c['size'] = {'3': '3v3', '4': '4v4', '5': '5v5'}[f['champs']]
    c['altars'] = 'alt1' if int(f['altars']) <= 1 else ('alt2' if int(f['altars']) == 2 else 'alt3+')
    c['altarpos'] = f['altar_class']
    c['groups'] = 'grp<=8' if int(f['groups']) <= 8 else ('grp9-14' if int(f['groups']) <= 14 else 'grp15+')
    c['mono'] = 'mono' if f['mono'] == '1' else 'nomono'
    c['spawn'] = 'near(<45)' if int(f['spawn_dist']) < 45 else ('mid' if int(f['spawn_dist']) < 90 else 'far(>=90)')
    c['conc'] = 'concentrated' if int(f['max_group_gems']) >= 0.25 * int(f['gems']) else 'spread'
    c['gold'] = 'goldrich' if int(f['gold']) >= 2.5 * max(1, int(f['gems'])) else 'goldpoor'
    return c

P('\n=== 7. Map-class residuals per top-30 team (wins - BT expected; only classes with n >= 10; flagged when resid/n <= -0.06)')
tc = defaultdict(lambda: [0, 0, 0.0])
for g in G:
    cl = classes(g['map'])
    for t, won, e in ((g['w'], 1, g['pw']), (g['l'], 0, 1 - g['pw'])):
        for dim, v in cl.items():
            x = tc[(t, dim, v)]
            x[0] += won
            x[1] += 1
            x[2] += e
J['classes'] = {}
for t in top30:
    lst = [((w - e) / n, dim, v, w, n, e) for (tt, dim, v), (w, n, e) in tc.items() if tt == t and n >= 10]
    lst.sort()
    J['classes'][name[t]] = [(dim, v, w, n, round(e, 1)) for d, dim, v, w, n, e in lst]
    weak = [x for x in lst if x[0] <= -0.06][:6]
    strong = [x for x in sorted(lst, reverse=True) if x[0] >= 0.06][:4]
    P(f"  #{rank[t]:>2} {name[t][:24]:24} weak: " + ', '.join(f"{v} {w}/{n} (E{e:.1f})" for d, dim, v, w, n, e in weak))
    P(f"      {'':24} strong: " + ', '.join(f"{v} {w}/{n} (E{e:.1f})" for d, dim, v, w, n, e in strong))

# ---------------- side
P('\n=== 8. Side effects. Side a wins overall: ' + f"{sum(1 for g in G if g['wside'] == 'a')}/{len(G)}")
for n_ in (3, 4, 5):
    gg = [g for g in G if g['n'] == n_]
    P(f"  {n_}v{n_}: side a wins {sum(1 for g in gg if g['wside'] == 'a')}/{len(gg)}")
ts = defaultdict(lambda: [0, 0, 0.0])
for g in G:
    ls = 'b' if g['wside'] == 'a' else 'a'
    for t, won, e, s in ((g['w'], 1, g['pw'], g['wside']), (g['l'], 0, 1 - g['pw'], ls)):
        x = ts[(t, s)]
        x[0] += won
        x[1] += 1
        x[2] += e
for t in top30:
    a_, b_ = ts[(t, 'a')], ts[(t, 'b')]
    P(f"  #{rank[t]:>2} {name[t][:24]:24} side a {a_[0]}/{a_[1]} (E{a_[2]:.1f}, {a_[0] - a_[2]:+.1f})  side b {b_[0]}/{b_[1]} (E{b_[2]:.1f}, {b_[0] - b_[2]:+.1f})")
# tiebreak games
tb = [g for g in G if g['end'] != 'gems']
P(f"  round-2000 tiebreak games: {len(tb)} ({Counter(g['end'] for g in tb)}); side b wins {sum(1 for g in tb if g['wside'] == 'b')}/{len(tb)}")

# ---------------- drafts
P('\n=== 9. Drafts. Each top-30 team: its rosters (5v5 / 4v4 / 3v3 most common) and win% by roster')
J['drafts'] = {}
def nm(d):
    return '+'.join(CH[i] for i in d)
for t in top30:
    dd = defaultdict(lambda: [0, 0, 0.0])
    for g in G:
        for tt, d, won, e in ((g['w'], g['wd'], 1, g['pw']), (g['l'], g['ld'], 0, 1 - g['pw'])):
            if tt == t:
                x = dd[d]
                x[0] += won
                x[1] += 1
                x[2] += e
    top = sorted(dd.items(), key=lambda kv: -kv[1][1])[:4]
    J['drafts'][name[t]] = [(nm(d), w, n, round(e, 1)) for d, (w, n, e) in top]
    P(f"  #{rank[t]:>2} {name[t][:24]:24} " + ' | '.join(f"{nm(d)} {w}/{n} (E{e:.1f})" for d, (w, n, e) in top))

P('\n=== 10. Opponent champion effect: for each top-10 team, residual of its games when the OPPONENT drafted champion c vs did not (n_with >= 8)')
for t in top10:
    eff = []
    for c in range(12):
        wv = [0, 0, 0.0]
        wo = [0, 0, 0.0]
        for g in G:
            for tt, od, won, e in ((g['w'], g['ld'], 1, g['pw']), (g['l'], g['wd'], 0, 1 - g['pw'])):
                if tt != t:
                    continue
                x = wv if c in od else wo
                x[0] += won
                x[1] += 1
                x[2] += e
        if wv[1] >= 8 and wo[1] >= 8:
            eff.append(((wv[0] - wv[2]) / wv[1] - (wo[0] - wo[2]) / wo[1], c, wv, wo))
    eff.sort()
    P(f"  #{rank[t]} {name[t]}: " + '; '.join(f"opp {CH[c]}: with {wv[0]}/{wv[1]} (E{wv[2]:.1f}) vs without {wo[0]}/{wo[1]} (E{wo[2]:.1f}) d={d:+.2f}" for d, c, wv, wo in eff[:3]))

# whole-population champion effect (winner vs loser presence, BT-adjusted), top-30 vs top-30 only
P('\n=== 11. Champion presence, games between two top-30 teams, mirror excluded: picked by one side only -> that side wins W/N (BT expected)')
for c in range(12):
    w = n = 0
    e = 0.0
    for g in G:
        if rank.get(g['w'], 99) > 30 or rank.get(g['l'], 99) > 30:
            continue
        iw, il = c in g['wd'], c in g['ld']
        if iw and not il:
            w += 1; n += 1; e += g['pw']
        elif il and not iw:
            n += 1; e += 1 - g['pw']
    if n >= 20:
        P(f"  {CH[c]:9} {w}/{n} = {w / n:.2f} (E {e:.1f}, resid {w - e:+.1f})")

# body-count / roster-size effect: teams that field fewer champions than allowed?
P('\n=== 12. End reasons for top-10 losses')
for t in top10:
    ls = [g for g in G if g['l'] == t]
    P(f"  #{rank[t]} {name[t]}: losses {len(ls)}: {dict(Counter(g['end'] for g in ls))}; by size {dict(Counter(g['n'] for g in ls))}")

open(f'{OUT}/h2h.txt', 'w').write('\n'.join(out) + '\n')
json.dump(J, open(f'{OUT}/h2h.json', 'w'), indent=1)
print('\n'.join(out))
