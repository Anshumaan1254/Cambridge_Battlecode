#!/usr/bin/env python3
"""How the top-30 lose: per-team loss anatomy from out/dec_games.jsonl (+ objectives/out/games_top.jsonl for contested big-group
cycles), and the universal counters (what upset winners do). Usage: nice -n 19 python3 -I losses.py -> out/losses.txt, out/losses.json
"""
import json, math, statistics as st
from collections import defaultdict, Counter

BASE = '/home/claude/cambridge_battlecode/experiments/top30_nov3'
OUT = '/home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out'
lad = json.load(open(f'{BASE}/ladder.json'))['teams']
rank = {t['teamId']: t['rank'] for t in lad}
name = {t['teamId']: t['name'] for t in lad}
bt = json.load(open(f'{OUT}/h2h.json'))['bt']
BT = {t['teamId']: bt.get(t['name'], t['rating']) for t in lad}
top10 = [t['teamId'] for t in lad if t['rank'] <= 10]

G = [json.loads(l) for l in open(f'{OUT}/dec_games.jsonl')]
OBJ = {}
with open(f'{BASE}/objectives/out/games_top.jsonl') as f:
    for l in f:
        o = json.loads(l)
        cyc = [c for c in o['cycles'] if c['start'] > 1 and c['gems'] >= 30 and c.get('by') in (0, 1)]
        OBJ[o['mid']] = {'cyc': [Counter(c['by'] for c in cyc)[0], Counter(c['by'] for c in cyc)[1]],
                         'cyc_open': [sum(1 for c in o['cycles'] if c['start'] == 1 and c.get('by') == t and c['gems'] >= 30) for t in (0, 1)],
                         'raids': [sum(1 for x in o['raids'] if x['t'] == t) for t in (0, 1)],
                         'raid_deaths': [sum(1 for x in o['raids'] if x['t'] == t and x['died']) for t in (0, 1)],
                         'cap_band': [o['side'][str(t)].get('cap_gems', {}) for t in (0, 1)]}

out = []
P = lambda *a: out.append(' '.join(str(x) for x in a))


def side_stats(g, t):
    """features of team t (0/1) in game g"""
    o = 1 - t
    f = {}
    D = g['deaths']
    f['deaths'] = sum(1 for d in D if d[1] == t)
    f['deaths_champ'] = sum(1 for d in D if d[1] == t and d[4] != 'camp')
    f['deaths_camp'] = sum(1 for d in D if d[1] == t and d[4] == 'camp')
    f['bag_lost'] = sum(min(300, d[3]) for d in D if d[1] == t)  # capped: boss maps carry 1000+ bags
    f['deaths_r300'] = sum(1 for d in D if d[1] == t and d[0] <= 300)
    f['kills'] = sum(1 for d in D if d[1] == o and d[4] != 'camp')
    C = g['caps']
    f['cap_r300'] = sum(c[3] for c in C if c[1] == t and c[0] <= 300)
    f['cap_r301_800'] = sum(c[3] for c in C if c[1] == t and 300 < c[0] <= 800)
    f['cap_late'] = sum(c[3] for c in C if c[1] == t and c[0] > 800)
    f['cap_all'] = sum(c[3] for c in C if c[1] == t)
    f['ncaps'] = sum(1 for c in C if c[1] == t)
    f['gold_caps'] = sum(c[4] for c in C if c[1] == t) + sum(x[3] for x in g['golds'] if x[1] == t)
    f['marc_cap_share'] = (sum(c[3] for c in C if c[1] == t and c[2] == 'Marcella') / max(1, f['cap_all']))
    f['banks'] = sum(1 for b in g['banks'] if b[1] == t)
    f['bag_at_bank'] = st.mean([b[3] for b in g['banks'] if b[1] == t]) if f['banks'] else 0
    f['canc'] = sum(1 for c in g['canc'] if c[1] == t)
    f['canc_gems'] = sum(min(300, c[3]) for c in g['canc'] if c[1] == t)
    f['locks'] = sum(1 for l in g['locks'] if l[1] == t)
    tl = g['tl']
    def at(r, i):
        r = str(r)
        return tl[r][i] if r in tl else None
    for r in (300, 600, 1000):
        f[f'bank{r}'] = at(r, t)
        f[f'tot{r}'] = at(r, 2 + t)
    it = g['items']
    for r in (300, 600, 1000):
        f[f'items{r}'] = it[str(r)][t] if str(r) in it else None
    ob = OBJ.get(g['mid'])
    f['cyc_taken'] = f['cyc_lost'] = f['cyc_open'] = f['raids'] = None
    if ob:
        f['cyc_taken'] = ob['cyc'][t]
        f['cyc_lost'] = ob['cyc'][o]
        f['cyc_open'] = ob['cyc_open'][t]
        f['raids'] = ob['raids'][t]
    return f


def mean(xs):
    xs = [x for x in xs if x is not None]
    return (sum(xs) / len(xs), len(xs)) if xs else (float('nan'), 0)


def fmt(xs):
    m, n = mean(xs)
    return f'{m:7.1f}' if n else '    n/a'


KEYS = ['deaths', 'deaths_champ', 'deaths_camp', 'bag_lost', 'deaths_r300', 'kills', 'cap_r300', 'cap_r301_800', 'cap_late', 'cap_all',
        'ncaps', 'gold_caps', 'marc_cap_share', 'banks', 'bag_at_bank', 'canc', 'canc_gems', 'locks', 'bank300', 'tot300', 'bank600', 'tot600',
        'bank1000', 'items300', 'items600', 'items1000', 'cyc_taken', 'cyc_lost', 'cyc_open', 'raids']

J = {}
P(f'decoded games: {len(G)}; with objectives cycles: {sum(1 for g in G if g["mid"] in OBJ)}')


def phase(dr):
    if dr is None:
        return 'close'
    return 'r<=300' if dr <= 300 else ('r301-600' if dr <= 600 else ('r601-1000' if dr <= 1000 else 'r>1000'))


def team_block(label, tids):
    tset = set(tids)
    L, W = [], []
    for g in G:
        for t in (0, 1):
            if g['tid'][t] in tset and g['tid'][1 - t] not in tset | {None} or (g['tid'][t] in tset and len(tset) == 1):
                (W if g['win'] == t else L).append((g, t))
    if not L:
        return
    P(f'\n######## {label}: decoded games {len(L) + len(W)} (wins {len(W)}, losses {len(L)})')
    # decisive phases
    ph = Counter(phase(g['dec_tot']) for g, t in L)
    drs = sorted(g['dec_tot'] for g, t in L if g['dec_tot'] is not None)
    q = (drs[len(drs) // 4], drs[len(drs) // 2], drs[3 * len(drs) // 4]) if drs else (None, None, None)
    P(f'  decided (loser >= 150 behind on banked+carried for good): {dict(ph)}; quartiles of the decisive round {q}')
    phb = Counter(phase(g['dec_bank']) for g, t in L)
    P(f'  same on BANKED gems only: {dict(phb)}; mega-bag games (a side carried >= 500 at a checkpoint): '
      f"{sum(1 for g, t in L if any(v[2] - v[0] >= 500 or v[3] - v[1] >= 500 for v in g['tl'].values()))}/{len(L)}")
    blown = [(g, t) for g, t in L if g['max_loser_lead'] >= 100]
    P(f'  blown leads (this team led by >= 100 at some point, then lost): {len(blown)}/{len(L)}; median round of its max lead '
      f'{st.median([g["max_loser_lead_r"] for g, t in blown]) if blown else None}')
    close = [(g, t) for g, t in L if g['dec_tot'] is None]
    if close:
        fin = [g['fin'][t] for g, t in close if g['fin'][t] is not None]
        race = sum(1 for g, t in close if g['fin'][t] is not None and g['fin'][t] >= 850)
        P(f'  close losses: {len(close)}; final banked of this team mean {sum(fin) / max(1, len(fin)):.0f}; lost the race with >= 850 banked: {race}; '
          f'tiebreaks {sum(1 for g, t in close if g["end"] != "gems")}')
    # window before decisive round
    wl = []
    for g, t in L:
        dr = g['dec_tot']
        if dr is None:
            continue
        a, b = dr - 150, dr
        o = 1 - t
        x = {'d_own': sum(1 for d in g['deaths'] if d[1] == t and a < d[0] <= b),
             'd_opp': sum(1 for d in g['deaths'] if d[1] == o and a < d[0] <= b),
             'bag_own': sum(min(300, d[3]) for d in g['deaths'] if d[1] == t and a < d[0] <= b),
             'cap_own': sum(c[3] for c in g['caps'] if c[1] == t and a < c[0] <= b),
             'cap_opp': sum(c[3] for c in g['caps'] if c[1] == o and a < c[0] <= b),
             'canc_own': sum(min(300, c[3]) for c in g['canc'] if c[1] == t and a < c[0] <= b),
             'lock_opp': sum(1 for l in g['locks'] if l[1] == o and a < l[0] <= b),
             'bank_own': sum(bb[3] for bb in g['banks'] if bb[1] == t and a < bb[0] <= b),
             'bank_opp': sum(bb[3] for bb in g['banks'] if bb[1] == o and a < bb[0] <= b)}
        wl.append(x)
    if wl:
        P('  150 rounds before the decisive round (per loss, mean): ' + ', '.join(f'{k} {sum(x[k] for x in wl) / len(wl):.1f}' for k in wl[0]) + f'  (n={len(wl)})')
        swing = sum(1 for x in wl if x['d_own'] - x['d_opp'] >= 2)
        P(f'    losses with a fight swing (>= 2 more deaths than the opponent in that window): {swing}/{len(wl)}; '
          f'capture gap (opp - own) >= 60 in the window: {sum(1 for x in wl if x["cap_opp"] - x["cap_own"] >= 60)}/{len(wl)}')
    # whole game, own features in losses vs wins, opponent features in this team's losses vs wins
    P(f"  {'feature':16} {'own L':>8} {'own W':>8} | {'opp in L':>8} {'opp in W':>8}")
    rows = {}
    for k in KEYS:
        ol = [side_stats(g, t)[k] for g, t in L]
        ow = [side_stats(g, t)[k] for g, t in W]
        pl = [side_stats(g, 1 - t)[k] for g, t in L]
        pw = [side_stats(g, 1 - t)[k] for g, t in W]
        rows[k] = [mean(ol)[0], mean(ow)[0], mean(pl)[0], mean(pw)[0]]
        P(f'  {k:16} {fmt(ol)} {fmt(ow)} | {fmt(pl)} {fmt(pw)}')
    # beaten by
    P('  beaten by (decoded): ' + ', '.join(f'{name.get(g["tid"][1 - t], "?")[:16]} {c}' for (g, t), c in []) +
      ', '.join(f'{n_[:18]} {c}' for n_, c in Counter(name.get(g['tid'][1 - t], '?') for g, t in L).most_common(8)))
    # deaths by killer type in losses
    kt = Counter(d[4] for g, t in L for d in g['deaths'] if d[1] == t)
    P('  this team\'s deaths in losses by killer: ' + ', '.join(f'{k} {v / len(L):.2f}' for k, v in kt.most_common(8)) + ' per game')
    kt2 = Counter(d[4] for g, t in W for d in g['deaths'] if d[1] == t)
    P('  ... in wins: ' + ', '.join(f'{k} {v / max(1, len(W)):.2f}' for k, v in kt2.most_common(8)) + ' per game')
    # losses by map size
    P('  losses by team size: ' + str(dict(Counter(g['n'] for g, t in L))) + '; wins by team size: ' + str(dict(Counter(g['n'] for g, t in W))))
    J[label] = {'nL': len(L), 'nW': len(W), 'phases': dict(ph), 'quart': q, 'blown': len(blown), 'rows': rows}
    return L, W


for t in top10:
    team_block(f'#{rank[t]} {name[t]}', [t])
team_block('ranks 11-20 (vs teams outside the cluster)', [t['teamId'] for t in lad if 11 <= t['rank'] <= 20])
team_block('ranks 21-30 (vs teams outside the cluster)', [t['teamId'] for t in lad if 21 <= t['rank'] <= 30])

# ---------------- universal: features of the winner vs loser, all decoded games, and upsets
P('\n######## UNIVERSAL: share of games won by the side with MORE of X (ties dropped), all decoded games and upsets (winner BT lower by >= 40)')
feats = ['kills', 'deaths', 'bag_lost', 'cap_r300', 'cap_r301_800', 'cap_late', 'gold_caps', 'marc_cap_share', 'banks', 'bag_at_bank', 'canc',
         'locks', 'items300', 'items600', 'cyc_taken', 'cyc_open', 'raids', 'deaths_r300', 'deaths_camp']
ups = [g for g in G if g['tid'][g['win']] in BT and g['tid'][1 - g['win']] in BT and BT[g['tid'][g['win']]] <= BT[g['tid'][1 - g['win']]] - 40]
fav = [g for g in G if g['tid'][g['win']] in BT and g['tid'][1 - g['win']] in BT and BT[g['tid'][g['win']]] >= BT[g['tid'][1 - g['win']]] + 40]
P(f'  games {len(G)}, upsets {len(ups)}, favourite wins {len(fav)}')
P(f"  {'feature':16} {'more->wins all':>16} {'in upsets':>12} {'in fav wins':>12} | mean winner/loser in upsets")
U = {}
for k in feats:
    res = []
    for gs in (G, ups, fav):
        w = n = 0
        for g in gs:
            a = side_stats(g, g['win'])[k]
            b = side_stats(g, 1 - g['win'])[k]
            if a is None or b is None or a == b:
                continue
            n += 1
            w += a > b
        res.append((w, n))
    mw = mean([side_stats(g, g['win'])[k] for g in ups])[0]
    ml = mean([side_stats(g, 1 - g['win'])[k] for g in ups])[0]
    U[k] = res
    P(f'  {k:16} {res[0][0]:>6}/{res[0][1]:<6} {res[0][0] / max(1, res[0][1]):.2f} {res[1][0]:>4}/{res[1][1]:<4} {res[1][0] / max(1, res[1][1]):.2f} '
      f'{res[2][0]:>4}/{res[2][1]:<4} {res[2][0] / max(1, res[2][1]):.2f} | {mw:7.1f} / {ml:7.1f}')
# decisive phase across all games
P('\n  decisive phase, all decoded games: ' + str(dict(Counter(phase(g['dec_tot']) for g in G))))
P('  decisive phase, upsets: ' + str(dict(Counter(phase(g['dec_tot']) for g in ups))))
P('  blown leads (loser led by >= 100): all ' + f"{sum(1 for g in G if g['max_loser_lead'] >= 100)}/{len(G)}; upsets {sum(1 for g in ups if g['max_loser_lead'] >= 100)}/{len(ups)}")
# who is ahead at r300 / r600 wins how often
for r in ('300', '600', '1000'):
    w = n = 0
    for g in G:
        if r in g['tl']:
            x = g['tl'][r]
            d = x[2] - x[3]
            if abs(d) >= 30:
                n += 1
                w += (d > 0) == (g['win'] == 0)
    P(f'  side ahead by >= 30 (banked+carried) at r{r} wins {w}/{n}')
J['universal'] = U

# ---------------- nemesis pairs (who beats whom above BT expectation in matches_current), decoded games
P('\n######## NEMESIS PAIRS (decoded games): nemesis features vs victim features, in the nemesis wins and losses')
tid = {t['name']: t['teamId'] for t in lad}
PAIRS = [('Ad Astra', 'Mite'), ('Univardisty of Shingtonwash', 'Intercontinental Fish'), ('NEETCoders', 'Univardisty of Shingtonwash'),
         ('Sponge(Albert and Bob)', 'Ad Astra'), ('Intercontinental Fish', 'newer team'), ('newer team', 'NEETCoders'),
         ('Trzy Kwaterki', 'BattleCats'), ('Mite', 'test4'), ('Intercontinental Fish', 'print dont int'), ('BattleCats', 'Sponge(Albert and Bob)')]
FK = ['kills', 'deaths', 'bag_lost', 'cap_r300', 'cap_r301_800', 'cap_late', 'gold_caps', 'locks', 'canc', 'items600', 'bag_at_bank', 'cyc_taken', 'raids']
for nn, vv in PAIRS:
    a, b = tid[nn], tid[vv]
    gs = [(g, 0 if g['tid'][0] == a else 1) for g in G if set(g['tid']) == {a, b}]
    if not gs:
        continue
    wn = [(g, t) for g, t in gs if g['win'] == t]
    P(f'  {nn} vs {vv}: decoded {len(gs)}, nemesis wins {len(wn)}; decisive phases of nemesis wins {dict(Counter(phase(g["dec_tot"]) for g, t in wn))}')
    P('    nemesis/victim means in nemesis wins: ' + ', '.join(f"{k} {mean([side_stats(g, t)[k] for g, t in wn])[0]:.1f}/{mean([side_stats(g, 1 - t)[k] for g, t in wn])[0]:.1f}" for k in FK))
    ls_ = [(g, t) for g, t in gs if g['win'] != t]
    if ls_:
        P('    nemesis/victim means in nemesis losses: ' + ', '.join(f"{k} {mean([side_stats(g, t)[k] for g, t in ls_])[0]:.1f}/{mean([side_stats(g, 1 - t)[k] for g, t in ls_])[0]:.1f}" for k in FK))
    P('    maps of nemesis wins: ' + ', '.join(sorted(g['map'] for g, t in wn)))
open(f'{OUT}/losses.txt', 'w').write('\n'.join(out) + '\n')
json.dump(J, open(f'{OUT}/losses.json', 'w'), indent=1, default=str)
print('\n'.join(out))
