#!/usr/bin/env python3
"""Tables: top-30 vs our v84-v88 games, from out/{top,our}_*.jsonl (extract2.py).

Usage: nice -n 19 python3 -I analyze.py > tables.txt

Groups (a 'team-game' = one team's side of one game):
  TOP   = both sides of the top-30 vs top-30 games (every body is a top-30 body)
  TOPw / TOPl = the winning / losing side of those games
  US    = HouseOfCoders in our v84-v88 games (v84 = Nov 2 ranked + unranked on v84-v87, v88 = Nov 3 paired + ranked on v88)
  OPP   = our opponents in the same games (ladder teams around rank 40-120)
  US88  = HouseOfCoders in the v88 games only
"""
import json, os, math, sys
from collections import Counter, defaultdict
from statistics import mean, median
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE + '/out'


def load(ds, name):
    p = f'{OUT}/{ds}_{name}.jsonl'
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


G = {ds: load(ds, 'games') for ds in ('top', 'our')}
GM = {g['mid']: g for ds in G for g in G[ds]}
D = {ds: load(ds, 'deaths') for ds in G}
F = {ds: load(ds, 'fights') for ds in G}
RT = {ds: load(ds, 'retreats') for ds in G}
DV = {ds: load(ds, 'dives') for ds in G}
CH = {ds: load(ds, 'chases') for ds in G}
HT = {ds: load(ds, 'hits') for ds in G}
PT = {ds: load(ds, 'parts') for ds in G}

OUR_VERS = ('v84', 'v88')


def sel(group):
    """-> (dataset, predicate(game, t)) for the team-games of a group"""
    if group == 'TOP':
        return 'top', lambda g, t: True
    if group == 'TOPw':
        return 'top', lambda g, t: g['teams'][t]['result'] == 'W'
    if group == 'TOPl':
        return 'top', lambda g, t: g['teams'][t]['result'] == 'L'
    if group == 'TOP10':
        return 'top', lambda g, t: (g['teams'][t]['rank'] or 99) <= 10
    if group == 'US':
        return 'our', lambda g, t: g['ver'] in OUR_VERS and t == g['we']
    if group == 'US88':
        return 'our', lambda g, t: g['ver'] == 'v88' and t == g['we']
    if group == 'US84':
        return 'our', lambda g, t: g['ver'] == 'v84' and t == g['we']
    if group == 'OPP':
        return 'our', lambda g, t: g['ver'] in OUR_VERS and t != g['we']
    if group == 'USw':
        return 'our', lambda g, t: g['ver'] in OUR_VERS and t == g['we'] and g['teams'][t]['result'] == 'W'
    if group == 'USl':
        return 'our', lambda g, t: g['ver'] in OUR_VERS and t == g['we'] and g['teams'][t]['result'] == 'L'
    raise KeyError(group)


def team_games(group):
    ds, pred = sel(group)
    return ds, [(g, t) for g in G[ds] for t in (0, 1) if pred(g, t)]


def rows_of(group, table):
    """rows of a per-body table (with 'mid' and 't') belonging to the group's team-games"""
    ds, tg = team_games(group)
    keys = {(g['mid'], t) for g, t in tg}
    return [r for r in table[ds] if (r['mid'], r['t']) in keys], len(tg)


pct = lambda x: f'{100 * x:.0f}%'
f1 = lambda x: f'{x:.1f}'
f2 = lambda x: f'{x:.2f}'


def mean_or(xs, d=float('nan')):
    xs = [x for x in xs if x is not None]
    return mean(xs) if xs else d


def table(title, cols, rows):
    print(f'\n### {title}')
    print('| | ' + ' | '.join(cols) + ' |')
    print('|---|' + '---|' * len(cols))
    for name, vals in rows:
        print(f'| {name} | ' + ' | '.join(str(v) for v in vals) + ' |')


GROUPS = [g for g in ['TOP', 'TOPw', 'TOPl', 'US', 'US88', 'OPP'] if team_games(g)[1]]

# ------------------------------------------------------------------ data summary
print('# Fights and deaths: top-30 vs our v84-v88 games')
for ds in G:
    print(f'{ds}: {len(G[ds])} games, deaths {len(D[ds])}, fights {len(F[ds])}, exchanges {sum(f["exchange"] for f in F[ds])}')
print('our games by version:', dict(Counter(g['ver'] for g in G['our'])))
print('top games: ranks of the teams', Counter(min(30, (g['teams'][t]['rank'] or 99)) // 10 * 10 for g in G['top'] for t in (0, 1)))

# ------------------------------------------------------------------ Q1 deaths


def q1(group):
    rows, n = rows_of(group, D)
    ds, tg = team_games(group)
    rounds = sum(g['final'] for g, t in tg)
    bodies = sum(g['champs'] for g, t in tg)
    body_rounds = sum(g['final'] * g['champs'] for g, t in tg)
    ck = [d for d in rows if d['cause'] != 'camp']
    out = [
        ('team-games', n),
        ('deaths per team-game', f1(len(rows) / n)),
        ('deaths per 1000 rounds', f1(1000 * len(rows) / rounds)),
        ('deaths per 1000 body-rounds', f2(1000 * len(rows) / body_rounds)),
        ('cause: champion / camp / both', ' / '.join(pct(sum(d['cause'] == c for d in rows) / max(1, len(rows))) for c in ('champion', 'camp', 'both'))),
        ('champion deaths: victim never hit back (10 r)', pct(sum(not d['hit_back'] for d in ck) / max(1, len(ck)))),
        ('  ...per team-game', f2(sum(not d['hit_back'] for d in ck) / n)),
        ('champion deaths: landed <= 1 hit in 10 r', pct(sum(d['n_dealt10'] <= 1 for d in ck) / max(1, len(ck)))),
        ('champion deaths in a fight the victim\'s team opened', pct(sum(d['started'] == 'own' for d in ck if d['started']) / max(1, sum(1 for d in ck if d['started'])))),
        ('carrying gems / gems lost per death', f"{pct(sum(d['bag'] > 0 for d in rows) / max(1, len(rows)))} / {f1(mean_or([d['bag'] for d in rows], 0))}"),
        ('gems lost per team-game', f1(sum(d['bag'] for d in rows) / n)),
        ('gems lost per team-game, bags >= 20', f1(sum(d['bag'] for d in rows if d['bag'] >= 20) / n)),
        ('no ally within 6 (r-5..r-1)', pct(sum(d['al5'] is not None and d['al5'] < 0.5 for d in rows) / max(1, len(rows)))),
        ('outnumbered by >= 0.5 body', pct(sum(d['al5'] is not None and d['en5'] - (d['al5'] + 1) >= 0.5 for d in rows) / max(1, len(rows)))),
        ('local R at r-5 (median, champion deaths)', f2(median([d['pw5'] for d in ck if d['pw5'] is not None] or [0]))),
        ('>= 2 steps toward the nearest enemy, last 8 r', pct(sum(d['tw8'] >= 2 for d in rows) / max(1, len(rows)))),
        ('no retreat step in the last 10 r (champion deaths)', pct(sum(d['ret_r'] is None for d in ck) / max(1, len(ck)))),
        ('hp 5 r before: mean / < 50%', f"{pct(mean_or([d['hp5'] for d in rows], 0))} / {pct(sum(1 for d in rows if d['hp5'] is not None and d['hp5'] < 0.5) / max(1, len(rows)))}"),
        ('hit by a camp the enemy woke (last 5 r)', pct(sum(d['camp_waker'] in ('enemy', 'both') for d in rows) / max(1, len(rows)))),
        ('stunned in the last 3 r', pct(sum(d['stunned3'] for d in rows) / max(1, len(rows)))),
        ('died within 40 r of respawn', pct(sum(1 for d in rows if d['age'] is not None and d['age'] <= 40) / max(1, len(rows)))),
        ('killed someone in the last 10 r', pct(sum(d['kills10'] > 0 for d in rows) / max(1, len(rows)))),
        ('on the enemy half', pct(sum(d['enemy_half'] for d in rows) / max(1, len(rows)))),
        ('was farming when first hit', pct(sum(d['farming'] for d in rows) / max(1, len(rows)))),
        ('attackers\' shards per body minus victim\'s (champion deaths, mean)', f1(mean_or([mean(d['att_shards']) - d['shards'] for d in ck if d['att_shards']], 0))),
    ]
    return out


print('\n## Q1 Deaths')
res = {g: q1(g) for g in GROUPS}
table('deaths', GROUPS, [(name, [res[g][i][1] for g in GROUPS]) for i, (name, _) in enumerate(res['TOP'])])

# deaths per 1000 rounds by map size class (like with like)


def size_class(g):
    a = g['mf']['area']
    return 'small<1600' if a < 1600 else 'mid<4000' if a < 4000 else 'big'


print('\n### deaths per 1000 rounds by map size class and champions per team (team-games in brackets)')
for key, fn in (('size', size_class), ('champs', lambda g: str(g['champs']))):
    for group in [x for x in ('TOP', 'US', 'US88', 'OPP') if x in GROUPS]:
        ds, tg = team_games(group)
        rows, n = rows_of(group, D)
        by = defaultdict(lambda: [0, 0, 0])
        for g, t in tg:
            by[fn(g)][1] += g['final']
            by[fn(g)][2] += 1
        for d in rows:
            by[fn(GM[d['mid']])][0] += 1
        print(f'{key} {group}: ' + ', '.join(f'{k}: {1000 * v[0] / max(1, v[1]):.1f} ({v[2]})' for k, v in sorted(by.items())))

# ------------------------------------------------------------------ Q2 engagement


def opener_rows(group):
    """exchanges opened by a team of the group, from the opener's side"""
    ds, tg = team_games(group)
    keys = {(g['mid'], t) for g, t in tg}
    out = []
    for f in F[ds]:
        t = f['first']
        if (f['mid'], t) not in keys:
            continue
        o = 1 - t
        out.append({'f': f, 't': t, 'R': f['r_open'], 'num_o': f['num'][str(t)], 'num_e': f['num'][str(o)], 'win': f['win'],
                    'dead_o': f['dead'][str(t)], 'dead_e': f['dead'][str(o)], 'approach': f['approach'], 'a_hp': f['a_hp'], 'a_ally': f['a_ally'],
                    'exch': f['exchange'], 'answer': f['answer'], 'sh_o': f['shards'][str(t)] / max(1, f['parts'][str(t)]),
                    'sh_e': f['shards'][str(o)] / max(1, f['parts'][str(o)])})
    return out, len(tg)


def receiver_rows(group):
    ds, tg = team_games(group)
    keys = {(g['mid'], t) for g, t in tg}
    out = []
    for f in F[ds]:
        t = 1 - f['first']
        if (f['mid'], t) not in keys:
            continue
        o = 1 - t
        pw_t, pw_o = f['pw'][str(t)], f['pw'][str(o)]
        out.append({'f': f, 't': t, 'R': (pw_t / pw_o) if pw_o > 0 else None, 'win': f['win'], 'dead_o': f['dead'][str(t)], 'dead_e': f['dead'][str(o)],
                    'exch': f['exchange'], 'answer': f['answer'], 'approach': f['approach'], 't_hp': f['t_hp'], 't_ally': f['t_ally']})
    return out, len(tg)


def rband(R):
    if R is None:
        return 'n/a'
    return '<0.5' if R < 0.5 else '0.5-0.8' if R < 0.8 else '0.8-1.25' if R < 1.25 else '1.25-2' if R < 2 else '>2'


def wr(rows, t_key='t'):
    """win share of the side 't' among decided fights"""
    dec = [r for r in rows if r['win'] is not None]
    return (sum(r['win'] == r['t'] for r in dec) / len(dec)) if dec else float('nan'), len(dec)


print('\n## Q2 Engagement rules')
cols = GROUPS
data = {g: opener_rows(g) for g in cols}
rdata = {g: receiver_rows(g) for g in cols}


def q2(g):
    op, n = data[g]
    rc, _ = rdata[g]
    ds, tg = team_games(g)
    keys = {(x['mid'], t) for x, t in tg}
    allf = [f for f in F[ds] if (f['mid'], 0) in keys or (f['mid'], 1) in keys]
    exch_all = [f for f in allf if f['exchange']]
    ng = len({x['mid'] for x, t in tg})
    opx = [r for r in op if r['exch']]
    rcx = [r for r in rc if r['exch']]
    share_open = len(opx) / max(1, len(opx) + len(rcx))
    out = [
        ('fights per game / exchanges per game', f"{len(allf) / ng:.1f} / {len(exch_all) / ng:.1f}"),
        ('we hit first (share of our exchanges)', pct(share_open)),
        ('opened exchanges: win share (decided)', pct(wr(opx)[0])),
        ('received exchanges: win share (decided)', pct(wr(rcx)[0])),
        ('one-sided fights we opened (no answer) per team-game', f1(sum(1 for r in op if not r['exch']) / n)),
        ('one-sided fights we took (never hit back) per team-game', f1(sum(1 for r in rc if not r['exch']) / n)),
        ('opener: R at contact median', f2(median([r['R'] for r in opx if r['R'] is not None] or [0]))),
        ('opener: share R < 0.67', pct(sum(1 for r in opx if r['R'] is not None and r['R'] < 0.67) / max(1, len(opx)))),
        ('opener: share R < 1.0', pct(sum(1 for r in opx if r['R'] is not None and r['R'] < 1.0) / max(1, len(opx)))),
        ('opener: bodies within 6: ours / theirs (mean)', f"{mean_or([r['num_o'] for r in opx], 0):.2f} / {mean_or([r['num_e'] for r in opx], 0):.2f}"),
        ('opener: fewer bodies than them', pct(sum(1 for r in opx if r['num_o'] < r['num_e']) / max(1, len(opx)))),
        ('opener: hp fraction (mean)', pct(mean_or([r['a_hp'] for r in opx], 0))),
        ('opener: hp < 50%', pct(sum(1 for r in opx if r['a_hp'] is not None and r['a_hp'] < 0.5) / max(1, len(opx)))),
        ('opener: nearest ally > 6 tiles', pct(sum(1 for r in opx if r['a_ally'] is not None and r['a_ally'] > 6) / max(1, len(opx)))),
        ('opener: nearest ally distance (median)', f1(median([r['a_ally'] for r in opx if r['a_ally'] is not None] or [0]))),
        ('opener approach: walk-in / received / mutual / static', ' / '.join(pct(sum(1 for r in opx if r['approach'] == a) / max(1, len(opx))) for a in ('walkin', 'received', 'mutual', 'static'))),
        ('walk-ins per team-game', f1(sum(1 for r in op if r['approach'] == 'walkin') / n)),
        ('walk-in exchanges: win share', pct(wr([r for r in opx if r['approach'] == 'walkin'])[0])),
        ('walk-in exchanges at R < 0.8: share / win share', f"{pct(sum(1 for r in opx if r['approach'] == 'walkin' and r['R'] is not None and r['R'] < 0.8) / max(1, len(opx)))} / {pct(wr([r for r in opx if r['approach'] == 'walkin' and r['R'] is not None and r['R'] < 0.8])[0])}"),
        ('received exchanges: answer latency (rounds, mean)', f1(mean_or([r['answer'] for r in rcx], 0))),
        ('received exchanges: answered within 1 round', pct(sum(1 for r in rcx if r['answer'] is not None and r['answer'] <= 1) / max(1, len(rcx)))),
        ('opener: shards per participant, ours - theirs (mean)', f1(mean_or([r['sh_o'] - r['sh_e'] for r in opx], 0))),
        ('deaths in opened exchanges per team-game: ours / theirs', f"{sum(r['dead_o'] for r in opx) / n:.2f} / {sum(r['dead_e'] for r in opx) / n:.2f}"),
        ('deaths in received exchanges per team-game: ours / theirs', f"{sum(r['dead_o'] for r in rcx) / n:.2f} / {sum(r['dead_e'] for r in rcx) / n:.2f}"),
    ]
    return out


res = {g: q2(g) for g in cols}
table('engagement (opener = the team that landed the first champion hit of the fight)', cols, [(name, [res[g][i][1] for g in cols]) for i, (name, _) in enumerate(res['TOP'])])

print('\n### win share of the opener by R band (opener side power / enemy power within 6 of the opener; decided exchanges; n in brackets)')
bands = ['<0.5', '0.5-0.8', '0.8-1.25', '1.25-2', '>2']
for g in cols:
    opx = [r for r in data[g][0] if r['exch']]
    tot = len(opx)
    print(f'{g}: ' + ' | '.join(f"{b}: {pct(sum(1 for r in opx if rband(r['R']) == b) / max(1, tot))} of openings, win {pct(wr([r for r in opx if rband(r['R']) == b])[0])} ({wr([r for r in opx if rband(r['R']) == b])[1]})" for b in bands))
print('\n### win share of the receiver by its R band (its power / theirs within 6 of the contact tile)')
for g in cols:
    rcx = [r for r in rdata[g][0] if r['exch']]
    tot = len(rcx)
    print(f'{g}: ' + ' | '.join(f"{b}: {pct(sum(1 for r in rcx if rband(r['R']) == b) / max(1, tot))}, win {pct(wr([r for r in rcx if rband(r['R']) == b])[0])} ({wr([r for r in rcx if rband(r['R']) == b])[1]})" for b in bands))

print('\n### steps toward the nearest enemy within 6 by local power band (per team-game; death within 6 rounds after the step)')
for g in GROUPS:
    ds, tg = team_games(g)
    n = len(tg)
    c = Counter()
    for gm, t in tg:
        for k, v in gm['step_stats'].items():
            tt, rb, dirn, what = k.split('|')
            if int(tt) == t:
                c[(rb, dirn, what)] += v
    parts = []
    kbr = sum(gm['final'] * gm['champs'] for gm, t in tg) / 1000.0
    for rb in ('weak', 'par', 'strong'):
        nn = c[(rb, 'toward', 'n')]
        parts.append(f"{rb}: toward {nn / n:.1f}/g ({nn / kbr:.1f} per 1000 body-r) die6 {pct(c[(rb, 'toward', 'died6')] / max(1, nn))}, away {c[(rb, 'away', 'n')] / n:.1f}/g")
    for rb in ('weak+nmore', 'weak+neq', 'weak+nless'):
        nn = c[(rb, 'toward', 'n')]
        parts.append(f"{rb}: toward {nn / n:.1f}/g die6 {pct(c[(rb, 'toward', 'died6')] / max(1, nn))}")
    print(f'{g}: ' + ' | '.join(parts))

print('\n### dives (>= 2 steps toward the nearest enemy within 4 rounds at R < 0.67) and chases (3+ steps after a target that keeps its distance)')
for g in GROUPS:
    dv, n = rows_of(g, DV)
    ch, _ = rows_of(g, CH)
    print(f"{g}: dives {len(dv) / n:.1f}/g, die8 {pct(sum(d['died8'] for d in dv) / max(1, len(dv)))}, deaths {sum(d['died8'] for d in dv) / n:.2f}/g, gems lost {sum(d['bag'] for d in dv) / n:.1f}/g; "
          f"dives with fewer bodies {pct(sum(1 for d in dv if d['n_own'] is not None and d['n_own'] < d['n_en']) / max(1, len(dv)))}; "
          f"chases {len(ch) / n:.1f}/g, die10 {pct(sum(c['died10'] for c in ch) / max(1, len(ch)))}, deaths {sum(c['died10'] for c in ch) / n:.2f}/g, killer = target {pct(sum(c['killer_is_target'] for c in ch if c['died10']) / max(1, sum(c['died10'] for c in ch)))}")

# ------------------------------------------------------------------ Q3 disengage
print('\n## Q3 Disengage (retreat = first away step from an enemy within 5 after taking a champion hit in the last 3 rounds)')


def q3(g):
    rt, n = rows_of(g, RT)
    dd, _ = rows_of(g, D)
    ck = [d for d in dd if d['cause'] != 'camp']
    hp = [r['hp'] for r in rt]
    out = [
        ('retreats per team-game', f1(len(rt) / n)),
        ('hp at retreat start: mean / median', f"{pct(mean_or(hp, 0))} / {pct(median(hp or [0]))}"),
        ('retreat starts at hp >= 60% / 40-60% / < 40%', ' / '.join(pct(x / max(1, len(rt))) for x in (sum(1 for h in hp if h >= 0.6), sum(1 for h in hp if 0.4 <= h < 0.6), sum(1 for h in hp if h < 0.4)))),
        ('caught (dead within 8 r)', pct(sum(r['died8'] for r in rt) / max(1, len(rt)))),
        ('caught: hp >= 60% / 40-60% / < 40%', ' / '.join(pct(sum(r['died8'] for r in rt if c(r['hp'])) / max(1, sum(1 for r in rt if c(r['hp'])))) for c in (lambda h: h >= 0.6, lambda h: 0.4 <= h < 0.6, lambda h: h < 0.4))),
        ('caught when a dash/stun was ready within reach', pct(sum(r['died8'] for r in rt if (r['dash4'] or 0) + (r['stun5'] or 0) > 0) / max(1, sum(1 for r in rt if (r['dash4'] or 0) + (r['stun5'] or 0) > 0)))),
        ('caught when none ready', pct(sum(r['died8'] for r in rt if (r['dash4'] or 0) + (r['stun5'] or 0) == 0) / max(1, sum(1 for r in rt if (r['dash4'] or 0) + (r['stun5'] or 0) == 0)))),
        ('step toward an ally / toward spawn / neither', ' / '.join(pct(x / max(1, len(rt))) for x in (sum(r['to_ally'] for r in rt), sum(r['to_spawn'] for r in rt), sum(1 for r in rt if not r['to_ally'] and not r['to_spawn'])))),
        ('caught: step toward an ally / not', f"{pct(sum(r['died8'] for r in rt if r['to_ally']) / max(1, sum(r['to_ally'] for r in rt)))} / {pct(sum(r['died8'] for r in rt if not r['to_ally']) / max(1, sum(1 for r in rt if not r['to_ally'])))}"),
        ('used a dash (0..+2 r) / stun (-1..+2) / recall (0..+3)', ' / '.join(pct(sum(r[k] for r in rt) / max(1, len(rt))) for k in ('dash', 'stun', 'recall'))),
        ('dash available (dasher, ready) and used', f"{pct(sum(1 for r in rt if r['own_dash'] and r['dash']) / max(1, sum(1 for r in rt if r['own_dash'])))} (of {sum(1 for r in rt if r['own_dash'])})"),
        ('pursued (nearest enemy stepped after us in 0..+3 r)', pct(sum(1 for r in rt if r['pursued'] > 0) / max(1, len(rt)))),
        ('caught when pursued / not pursued', f"{pct(sum(r['died8'] for r in rt if r['pursued'] > 0) / max(1, sum(1 for r in rt if r['pursued'] > 0)))} / {pct(sum(r['died8'] for r in rt if r['pursued'] == 0) / max(1, sum(1 for r in rt if r['pursued'] == 0)))}"),
        ('enemies within 4 three rounds later (mean)', f2(mean_or([r['en4_3'] for r in rt], 0))),
        ('retreat starts with R < 0.67 / 0.67-1.5 / > 1.5', ' / '.join(pct(sum(1 for r in rt if r['pw_ratio'] is not None and c(r['pw_ratio'])) / max(1, len(rt))) for c in (lambda x: x < 0.67, lambda x: 0.67 <= x <= 1.5, lambda x: x > 1.5))),
        ('champion deaths: hp when the last retreat began (mean)', pct(mean_or([d['ret_hp'] for d in ck], 0))),
        ('champion deaths: no retreat step in the last 10 r', pct(sum(d['ret_r'] is None for d in ck) / max(1, len(ck)))),
        ('champion deaths: last retreat began at hp < 30%', pct(sum(1 for d in ck if d['ret_hp'] is not None and d['ret_hp'] < 0.3) / max(1, len(ck)))),
    ]
    return out


res = {g: q3(g) for g in cols}
table('disengage', cols, [(name, [res[g][i][1] for g in cols]) for i, (name, _) in enumerate(res['TOP'])])

# ------------------------------------------------------------------ Q4 focus / group play
print('\n## Q4 Focus and group play')


def q4(g):
    ht, n = rows_of(g, HT)
    pt, _ = rows_of(g, PT)
    px = [p for p in pt if p['exchange']]
    alone = [p for p in px if p['al6'] == 0]
    out = [
        ('champion hits per team-game', f1(len(ht) / n)),
        ('allies hitting the same target within +-2 r (mean per hit)', f2(mean_or([h['helpers'] for h in ht], 0))),
        ('hits with >= 1 helper / >= 2', f"{pct(sum(h['helpers'] >= 1 for h in ht) / max(1, len(ht)))} / {pct(sum(h['helpers'] >= 2 for h in ht) / max(1, len(ht)))}"),
        ('hits with an ally within 6 but no helper', pct(sum(1 for h in ht if h['al6'] > 0 and h['helpers'] == 0) / max(1, len(ht)))),
        ('hits landed with no ally within 6', pct(sum(h['al6'] == 0 for h in ht) / max(1, len(ht)))),
        ('hits landed outnumbered (enemies within 6 > allies + 1)', pct(sum(h['en6'] > h['al6'] + 1 for h in ht) / max(1, len(ht)))),
        ('exchange participations per team-game', f1(len(px) / n)),
        ('participations alone (no ally within 6 at first own hit)', pct(len(alone) / max(1, len(px)))),
        ('  died in the fight: alone / with allies', f"{pct(sum(p['died'] for p in alone) / max(1, len(alone)))} / {pct(sum(p['died'] for p in px if p['al6'] > 0) / max(1, sum(1 for p in px if p['al6'] > 0)))}"),
        ('participations alone against 2+ enemies within 6', pct(sum(1 for p in px if p['al6'] == 0 and p['en6'] >= 2) / max(1, len(px)))),
        ('  died', pct(sum(p['died'] for p in px if p['al6'] == 0 and p['en6'] >= 2) / max(1, sum(1 for p in px if p['al6'] == 0 and p['en6'] >= 2)))),
        ('participations with an ally within 8 but none within 6', pct(sum(1 for p in px if p['al6'] == 0 and p['al8'] > 0) / max(1, len(px)))),
        ('bodies per side in an exchange (mean participants)', f2(mean_or([f['parts'][str(t)] for f in F[sel(g)[0]] if f['exchange'] for t in (0, 1) if (f['mid'], t) in {(x['mid'], tt) for x, tt in team_games(g)[1]}], 0))),
    ]
    return out


res = {g: q4(g) for g in cols}
table('focus / group', cols, [(name, [res[g][i][1] for g in cols]) for i, (name, _) in enumerate(res['TOP'])])

# ------------------------------------------------------------------ Q5 champion matchups
print('\n## Q5 Champion matchups')
for g in [x for x in ('TOP', 'US', 'US88', 'OPP') if x in GROUPS]:
    dd, n = rows_of(g, D)
    ds, tg = team_games(g)
    drafted = Counter()
    for gm, t in tg:
        for c in gm['drafts'][t]:
            if c == 'CassiAndIssac':
                drafted['Cassi'] += 1
                drafted['Issac'] += 1
            else:
                drafted[c] += 1
    print(f'\n{g}: deaths per team-game by victim champion (deaths per drafted body in brackets)')
    byv = Counter(d['champ'] for d in dd)
    print('  ' + ', '.join(f'{c}: {byv[c] / n:.2f} ({byv[c] / max(1, drafted[c]):.1f})' for c, _ in byv.most_common()))
    byk = Counter(d['killer'] for d in dd)
    print(f'  killer: ' + ', '.join(f'{c}: {byk[c] / n:.2f}' for c, _ in byk.most_common()))
    # kills by our champions (deaths of the other side)
    keys = {(x['mid'], 1 - t) for x, t in tg}
    kills = [d for d in D[ds] if (d['mid'], d['t']) in keys and d['killer'] != 'camp']
    byk2 = Counter(d['killer'] for d in kills)
    print(f'  kills per team-game by our champion: ' + ', '.join(f'{c}: {byk2[c] / n:.2f} ({byk2[c] / max(1, drafted[c]):.1f} per drafted body)' for c, _ in byk2.most_common()))

print('\n### victim x killer matrix (US, champion deaths per team-game) and the situation of the top pairs')
dd, n = rows_of('US', D)
mat = Counter((d['champ'], d['killer']) for d in dd if d['killer'] != 'camp')
top_pairs = mat.most_common(12)
print('  ' + ', '.join(f'{v}<-{k}: {c / n:.2f}' for (v, k), c in top_pairs))
ddt, nt = rows_of('TOP', D)
matt = Counter((d['champ'], d['killer']) for d in ddt if d['killer'] != 'camp')
print('  TOP: ' + ', '.join(f'{v}<-{k}: {c / nt:.2f}' for (v, k), c in matt.most_common(12)))


def situ(rows):
    ck = [d for d in rows if d['killer'] != 'camp']
    if not ck:
        return 'n/a'
    return (f"n={len(ck)}: chased the killer (2+ steps toward it in 4 r) {pct(sum(1 for d in ck if (d['tw_killer4'] or 0) >= 2) / len(ck))}, "
            f"killer 5+ tiles away 3 r before {pct(sum(1 for d in ck if d['kd3'] is not None and d['kd3'] >= 5) / len(ck))}, "
            f"took a spell in the last 3 r {pct(sum(1 for d in ck if d['kinds3'].get('spell', 0) + d['kinds3'].get('area', 0) > 0) / len(ck))}, "
            f"took a dash {pct(sum(1 for d in ck if d['kinds3'].get('dash', 0) > 0) / len(ck))}, stunned {pct(sum(d['stunned3'] for d in ck) / len(ck))}, "
            f"never hit back {pct(sum(not d['hit_back'] for d in ck) / len(ck))}, alone {pct(sum(1 for d in ck if d['al5'] is not None and d['al5'] < 0.5) / len(ck))}, "
            f"hp5 {pct(mean_or([d['hp5'] for d in ck], 0))}")


for killer in ('Marcella', 'HeartOfRuin', 'Vendetta', 'VesperVale', 'Ryth', 'Tavi', 'Stellar', 'Willow', 'Ren', 'Varg', 'Prism', 'Cassi', 'Issac'):
    us = [d for d in dd if d['killer'] == killer]
    tp = [d for d in ddt if d['killer'] == killer]
    if len(us) >= 10:
        print(f'  killed by {killer}: US {len(us) / n:.2f}/g, TOP {len(tp) / nt:.2f}/g')
        print(f'    US  {situ(us)}')
        print(f'    TOP {situ(tp)}')
marc_us = sum(d['marcella_pattern'] for d in dd) / n
marc_top = sum(d['marcella_pattern'] for d in ddt) / nt
print(f'  Marcella pattern (within 4 of her for 3+ of the last 5 r and took her spell): US {marc_us:.2f}/g, TOP {marc_top:.2f}/g')

# ------------------------------------------------------------------ Q6 item gap and the exchange model
print('\n## Q6 Item gap at fight time and the exchange model')


def exch_rows(group):
    """one row per decided exchange from the group team's side"""
    ds, tg = team_games(group)
    keys = {(g['mid'], t) for g, t in tg}
    out = []
    for f in F[ds]:
        if not f['exchange'] or f['win'] is None:
            continue
        for t in (0, 1):
            if (f['mid'], t) not in keys:
                continue
            o = 1 - t
            pw_t, pw_o = f['pw'][str(t)], f['pw'][str(o)]
            R = (pw_t / max(1.0, pw_o)) if pw_o > 0 else 9.0
            sh_t = f['shards'][str(t)] / max(1, f['parts'][str(t)])
            sh_o = f['shards'][str(o)] / max(1, f['parts'][str(o)])
            out.append({'y': 1 if f['win'] == t else 0, 'first': 1 if f['first'] == t else 0, 'logR': math.log(max(0.05, min(20, R))),
                        'gap': sh_t - sh_o, 'nd': f['num'][str(t)] - f['num'][str(o)], 'pd': f['parts'][str(t)] - f['parts'][str(o)],
                        'sh_t': sh_t, 'sh_o': sh_o, 'start': f['start'], 'mid': f['mid'], 'dead_t': f['dead'][str(t)], 'dead_o': f['dead'][str(o)]})
    return out, len(tg)


def logit_fit(X, y, l2=1e-3, iters=200):
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    Xb = np.hstack([np.ones((len(X), 1)), X])
    w = np.zeros(Xb.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-Xb @ w))
        grad = Xb.T @ (p - y) + l2 * w
        Wd = p * (1 - p)
        H = (Xb * Wd[:, None]).T @ Xb + l2 * np.eye(Xb.shape[1])
        step = np.linalg.solve(H, grad)
        w -= step
        if np.abs(step).max() < 1e-8:
            break
    p = 1 / (1 + np.exp(-Xb @ w))
    Wd = p * (1 - p)
    H = (Xb * Wd[:, None]).T @ Xb + l2 * np.eye(Xb.shape[1])
    se = np.sqrt(np.diag(np.linalg.inv(H)))
    return w, se, p


FEATS = ['first', 'logR', 'gap', 'nd']
for g in [x for x in ('TOP', 'US', 'OPP', 'US88') if x in GROUPS]:
    ex, n = exch_rows(g)
    if len(ex) < 50:
        continue
    X = [[e[k] for k in FEATS] for e in ex]
    y = [e['y'] for e in ex]
    w, se, p = logit_fit(X, y)
    print(f'\n{g}: {len(ex)} decided exchanges, win share {pct(mean(y))}; shards per participant ours {mean(e["sh_t"] for e in ex):.1f} vs theirs {mean(e["sh_o"] for e in ex):.1f} '
          f'(gap {mean(e["gap"] for e in ex):+.1f}); hit first {pct(mean(e["first"] for e in ex))}; mean logR {mean(e["logR"] for e in ex):+.2f}; body diff {mean(e["nd"] for e in ex):+.2f}')
    print('  logistic win model: ' + ', '.join(f'{k} {w[i + 1]:+.3f} (z {w[i + 1] / se[i + 1]:+.1f})' for i, k in enumerate(FEATS)) + f', const {w[0]:+.2f}')
    print('  win share by item gap band: ' + ', '.join(f'{lo}..{hi}: {pct(mean([e["y"] for e in ex if lo <= e["gap"] < hi] or [0]))} ({sum(1 for e in ex if lo <= e["gap"] < hi)})' for lo, hi in ((-99, -10), (-10, -3), (-3, 3), (3, 10), (10, 99))))
    print('  win share hit first / second: ' + f'{pct(mean([e["y"] for e in ex if e["first"]] or [0]))} / {pct(mean([e["y"] for e in ex if not e["first"]] or [0]))}')
    print('  win share by R band: ' + ', '.join(f'{b}: {pct(mean([e["y"] for e in ex if rband(math.exp(e["logR"])) == b] or [0]))} ({sum(1 for e in ex if rband(math.exp(e["logR"])) == b)})' for b in bands))
    print('  item gap by game phase: ' + ', '.join(f'r{lo}-{hi}: {mean([e["gap"] for e in ex if lo <= e["start"] < hi] or [0]):+.1f} ({sum(1 for e in ex if lo <= e["start"] < hi)})' for lo, hi in ((0, 200), (200, 400), (400, 700), (700, 1000), (1000, 3000))))

# counterfactual: fit the TOP model, score our exchanges; then swap one factor at a time to the top distribution
ex_top, _ = exch_rows('TOP')
ex_us, _ = exch_rows('US')
if len(ex_top) >= 50 and len(ex_us) >= 50:
    w, se, _ = logit_fit([[e[k] for k in FEATS] for e in ex_top], [e['y'] for e in ex_top])
    Xu = np.array([[e[k] for k in FEATS] for e in ex_us], float)
    yu = np.array([e['y'] for e in ex_us], float)
    score = lambda X: float(np.mean(1 / (1 + np.exp(-(w[0] + X @ w[1:])))))
    base = score(Xu)
    print(f'\ncounterfactual with the TOP model on our {len(ex_us)} exchanges: predicted win share {pct(base)} (actual {pct(yu.mean())}, TOP actual {pct(mean(e["y"] for e in ex_top))})')
    means_top = np.array([mean(e[k] for e in ex_top) for k in FEATS])
    for i, k in enumerate(FEATS):
        X2 = Xu.copy()
        X2[:, i] += means_top[i] - Xu[:, i].mean()
        print(f'  shift {k} to the TOP mean ({Xu[:, i].mean():+.2f} -> {means_top[i]:+.2f}): {pct(score(X2))} ({100 * (score(X2) - base):+.1f} pts)')
    # deaths per exchange decomposition
    print(f"  deaths per decided exchange: US {mean(e['dead_t'] for e in ex_us):.2f} (they {mean(e['dead_o'] for e in ex_us):.2f}); TOP {mean(e['dead_t'] for e in ex_top):.2f}")
    for name, cond in (('hit first', lambda e: e['first'] == 1), ('hit second', lambda e: e['first'] == 0), ('R < 0.67', lambda e: math.exp(e['logR']) < 0.67),
                       ('R >= 1.5', lambda e: math.exp(e['logR']) >= 1.5), ('gap <= -5', lambda e: e['gap'] <= -5), ('gap >= 5', lambda e: e['gap'] >= 5)):
        a = [e for e in ex_us if cond(e)]
        b = [e for e in ex_top if cond(e)]
        print(f"  {name}: US share {pct(len(a) / len(ex_us))} deaths/exch {mean_or([e['dead_t'] for e in a], 0):.2f} win {pct(mean_or([e['y'] for e in a], 0))}; "
              f"TOP share {pct(len(b) / len(ex_top))} deaths/exch {mean_or([e['dead_t'] for e in b], 0):.2f} win {pct(mean_or([e['y'] for e in b], 0))}")
