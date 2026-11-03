#!/usr/bin/env python3
"""v95 vs v88 on the god24_plan mechanism metrics (same extractors as the top30_nov3 streams).
v95: out/g/*.json (run_all.py).  v88 reference: top30_nov3 stream outputs tagged v88 (loss-heavy: compare L with L, and each with OPP
in the same games).  Usage: python3 -I aggregate.py > out/summary.txt"""
import json, glob, os, sys, math
from collections import Counter, defaultdict
ROOT = '/home/claude/cambridge_battlecode'
V95 = f'{ROOT}/experiments/deep_research_nov3/v95'
T30 = f'{ROOT}/experiments/top30_nov3'
L2 = f'{ROOT}/experiments/ladder_nov2'
ME = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'
ST = ['str', 'foc', 'hp']
FAM = ['Monster', 'Power', 'Durab', 'Treasure', 'Jungle', 'Home', 'Bruiser', 'Tribute', 'Capture', 'Prospect', 'Hunter', 'Skirmish', 'Greed', 'Collect']
ECONF = {'Prospect', 'Treasure', 'Capture', 'Monster', 'Tribute'}
LAD = {t['teamId']: t for t in json.load(open(f'{T30}/ladder.json'))['teams']}


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def f(x, d=1):
    return '-' if x is None else (f'{x:.{d}f}')


# ---------------------------------------------------------------- load v95
V = [json.load(open(p)) for p in glob.glob(f'{V95}/out/g/*.json')]
V = [r for r in V if 'fights' in r and 'met' in r and 'fl' in r and 'econ' in r]
excl_amb = '--amb' not in sys.argv
if excl_amb:
    V = [r for r in V if r['info']['ver'] == 'v95']

# ---------------------------------------------------------------- load v88 reference
fg = [json.loads(l) for l in open(f'{T30}/fights/out/our_games.jsonl')]
fver = {g['mid']: g['ver'] for g in fg}
F88 = {'games': [g for g in fg if g['ver'] == 'v88']}
m88 = set(g['mid'] for g in F88['games'])
for n in ('deaths', 'retreats'):
    F88[n] = [json.loads(l) for l in open(f'{T30}/fights/out/our_{n}.jsonl')]
    F88[n] = [x for x in F88[n] if x['mid'] in m88]
MET88 = [json.load(open(p)) for p in glob.glob(f'{T30}/execution/out/met/*.json')]
MET88 = [x for x in MET88 if x['tag'] == 'v88']
FL88 = [json.load(open(p)) for p in glob.glob(f'{T30}/confusion/out/fl/*.json')]
FL88 = [x for x in FL88 if x['tag'] == 'v88']
EC88 = [json.loads(l) for l in open(f'{T30}/economy/rows_ours.jsonl')]
EC88 = [x for x in EC88 if x.get('ver') == 'v88' and 'error' not in x]


# ---------------------------------------------------------------- per-side record builders
def side_rows():
    """returns list of dicts, one per (game, side) with label keys: pop in {'v95','v88'}, who in {'we','opp'}, res in {'W','L'}"""
    out = []
    # v95
    for r in V:
        gi = r['info']
        we = gi['we']
        game = r['fights']['games'][0]
        for t in (0, 1):
            who = 'we' if t == we else 'opp'
            res = gi['res'] if who == 'we' else ('L' if gi['res'] == 'W' else 'W')
            e = [x for x in r['econ'] if x.get('team') == t]
            out.append({'pop': 'v95', 'who': who, 'res': res, 'mid': gi['mid'], 'map': gi['map'], 'kind': gi['kind'], 't': t,
                        'game': game, 'deaths': [x for x in r['fights']['deaths'] if x['t'] == t],
                        'retreats': [x for x in r['fights']['retreats'] if x['t'] == t],
                        'met': r['met']['sides'].get(str(t)), 'fl': r['fl']['sides'].get(str(t)), 'econ': e[0] if e else None})
    # v88 (fights games are the frame; met / fl / econ joined by mid where present)
    metd = {x['mid']: x for x in MET88}
    fld = {x['mid']: x for x in FL88}
    ecd = defaultdict(dict)
    for x in EC88:
        ecd[x['mid']][x['team']] = x
    dd = defaultdict(list)
    for x in F88['deaths']:
        dd[x['mid']].append(x)
    rr = defaultdict(list)
    for x in F88['retreats']:
        rr[x['mid']].append(x)
    mids = set(metd) | set(fld) | set(m88) | set(ecd)
    gd = {g['mid']: g for g in F88['games']}
    for mid in mids:
        we = None
        res_we = None
        for src in (gd.get(mid), metd.get(mid), fld.get(mid)):
            if src is not None:
                we = src['we']
                if 'teams' in src and isinstance(src['teams'][0], dict):
                    res_we = src['teams'][we]['result']
                elif src.get('winner') is not None:
                    res_we = 'W' if src['winner'] == we else 'L'
                break
        if we is None:
            e = ecd.get(mid, {})
            for t, x in e.items():
                if x.get('me'):
                    we, res_we = t, x['res']
        if we is None:
            continue
        for t in (0, 1):
            who = 'we' if t == we else 'opp'
            res = res_we if who == 'we' else ('L' if res_we == 'W' else 'W')
            out.append({'pop': 'v88', 'who': who, 'res': res, 'mid': mid, 't': t, 'game': gd.get(mid),
                        'deaths': [x for x in dd.get(mid, []) if x['t'] == t] if mid in gd else None,
                        'retreats': [x for x in rr.get(mid, []) if x['t'] == t] if mid in gd else None,
                        'met': metd[mid]['sides'].get(str(t)) if mid in metd else None,
                        'fl': fld[mid]['sides'].get(str(t)) if mid in fld else None, 'econ': ecd.get(mid, {}).get(t)})
    return out


S = side_rows()
COLS = [('v95 we', lambda s: s['pop'] == 'v95' and s['who'] == 'we'),
        ('v95 we L', lambda s: s['pop'] == 'v95' and s['who'] == 'we' and s['res'] == 'L'),
        ('v95 we W', lambda s: s['pop'] == 'v95' and s['who'] == 'we' and s['res'] == 'W'),
        ('v95 opp', lambda s: s['pop'] == 'v95' and s['who'] == 'opp'),
        ('v88 we(L-heavy)', lambda s: s['pop'] == 'v88' and s['who'] == 'we'),
        ('v88 we L', lambda s: s['pop'] == 'v88' and s['who'] == 'we' and s['res'] == 'L'),
        ('v88 opp', lambda s: s['pop'] == 'v88' and s['who'] == 'opp')]


def row(label, fn, d=2, need=None):
    """fn(side) -> value or None; mean over the sides of each column that have the needed source"""
    cells = []
    for name, sel in COLS:
        xs = []
        for s in S:
            if not sel(s):
                continue
            if need and s.get(need) is None:
                continue
            try:
                v = fn(s)
            except (KeyError, TypeError, ZeroDivisionError):
                v = None
            if v is not None:
                xs.append(v)
        cells.append(f"{f(mean(xs), d)} (n{len(xs)})")
    print(f'{label:46s}' + ''.join(f'{c:>17s}' for c in cells))


def ratio_row(label, num, den, d=1, need=None, scale=100.0):
    """pooled ratio sum(num)/sum(den) per column"""
    cells = []
    for name, sel in COLS:
        a = b = 0.0
        for s in S:
            if not sel(s) or (need and s.get(need) is None):
                continue
            try:
                a += num(s)
                b += den(s)
            except (KeyError, TypeError):
                pass
        cells.append(f"{f(scale * a / b if b else None, d)} ({int(b)})")
    print(f'{label:46s}' + ''.join(f'{c:>17s}' for c in cells))


print('columns:', ', '.join(n for n, _ in COLS))
print('n sides:', {n: sum(1 for s in S if sel(s)) for n, sel in COLS})
print('v95 games used:', len(V), '(ambiguous 12:50:44-12:52:30 group excluded)' if excl_amb else '(ambiguous group included)')

print('\n== RESULT / BANK (fights games rows: sub = banked gems at the end) ==')
row('banked gems at end', lambda s: s['game']['sub'][s['t']], 0, need='game')
row('gem margin (we - them)', lambda s: s['game']['sub'][s['t']] - s['game']['sub'][1 - s['t']], 0, need='game')
row('final round', lambda s: s['game']['final'], 0, need='game')

print('\n== DEATHS (fights stream definitions) ==')
row('deaths / game', lambda s: len(s['deaths']), 2, need='deaths')
row('gems lost on death / game', lambda s: sum(x['bag'] for x in s['deaths']), 1, need='deaths')
row('F2 walk-in deaths (2+ steps toward, last 8 r)', lambda s: sum(1 for x in s['deaths'] if (x.get('tw8') or 0) >= 2), 2, need='deaths')
row('F3 deaths <= 40 r after respawn', lambda s: sum(1 for x in s['deaths'] if x.get('age') is not None and x['age'] <= 40), 2, need='deaths')
row('F4 deaths, enemy-woken camp hit them', lambda s: sum(1 for x in s['deaths'] if x.get('camp_waker') == 'enemy'), 2, need='deaths')
row('deaths killed by enemy Marcella', lambda s: sum(1 for x in s['deaths'] if x.get('killer') == 'Marcella'), 2, need='deaths')
row('deaths with bag >= 40', lambda s: sum(1 for x in s['deaths'] if (x.get('bag') or 0) >= 40), 2, need='deaths')
row('deaths not hitting back (caught)', lambda s: sum(1 for x in s['deaths'] if x.get('hit_back') is False and x.get('killer') not in (None, 'camp')), 2, need='deaths')


def stepn(s, keys):
    g = s['game']
    t = s['t']
    return sum(g['step_stats'].get(f'{t}|{k}', 0) for k in keys)


row('F2 steps toward at R<0.67 w/ >= bodies /g', lambda s: stepn(s, ['weak+neq|toward|n', 'weak+nmore|toward|n']), 1, need='game')
row('   of which died within 6 r /g', lambda s: stepn(s, ['weak+neq|toward|died6', 'weak+nmore|toward|died6']), 2, need='game')

print('\n== F1 RETREATS (own dash ready at retreat start): dash used within 2 rounds, % (n retreats) ==')
for ch in (None, 'HeartOfRuin', 'VesperVale', 'Vendetta', 'Marcella', 'Ryth'):
    lab = f"dash used | {ch or 'all champions'}"
    ratio_row(lab, lambda s, ch=ch: sum(1 for x in s['retreats'] if x.get('own_dash') and x.get('dash') and (ch is None or x['champ'] == ch)),
              lambda s, ch=ch: sum(1 for x in s['retreats'] if x.get('own_dash') and (ch is None or x['champ'] == ch)), 1, need='retreats')
ratio_row('caught (died8) | retreat hp<0.5', lambda s: sum(1 for x in s['retreats'] if x['hp'] < 0.5 and x.get('died8')),
          lambda s: sum(1 for x in s['retreats'] if x['hp'] < 0.5), 1, need='retreats')
ratio_row('caught (died8) | retreat hp<0.5 & dash ready', lambda s: sum(1 for x in s['retreats'] if x['hp'] < 0.5 and x.get('own_dash') and x.get('died8')),
          lambda s: sum(1 for x in s['retreats'] if x['hp'] < 0.5 and x.get('own_dash')), 1, need='retreats')
row('retreats / game', lambda s: len(s['retreats']), 1, need='retreats')

print('\n== WASTED LOOPS (confusion stream; rounds per game) ==')
for cl in ('ENEMY12', 'ENEMY6', 'BAG', 'OPEN', 'LIVEGRP', 'CAMPAGGRO', 'DEADGRP', 'RECALL', 'FIGHT'):
    row(f'wasted rounds {cl}', lambda s, cl=cl: s['fl']['lost'].get(cl, 0), 1, need='fl')
row('wasted rounds ALL but FIGHT', lambda s: sum(v for k, v in s['fl']['lost'].items() if k != 'FIGHT'), 1, need='fl')
ratio_row('ALL-but-FIGHT per 1000 alive body-rounds', lambda s: sum(v for k, v in s['fl']['lost'].items() if k != 'FIGHT'),
          lambda s: s['fl']['alive'], 1, need='fl', scale=1000.0)
row('held recalls cancelled / game', lambda s: s['fl']['held_cancel'], 1, need='fl')

print('\n== WHO CAPTURES (confusion stream: share of the team captured gems / banked gems, pooled) ==')
for ty in ('HeartOfRuin', 'Marcella', 'VesperVale', 'Vendetta', 'Ryth', 'Varg'):
    ratio_row(f'capture share {ty}', lambda s, ty=ty: s['fl']['cap'].get(ty, {}).get('gems', 0) if s['fl']['types'].get(ty) else 0,
              lambda s, ty=ty: s['fl']['cap'].get('_team', {}).get('gems', 0) if s['fl']['types'].get(ty) else 0, 1, need='fl')
for ty in ('Marcella', 'HeartOfRuin'):
    ratio_row(f'banked share {ty}', lambda s, ty=ty: s['fl']['bank'].get(ty, {}).get('gems', 0) if s['fl']['types'].get(ty) else 0,
              lambda s, ty=ty: s['fl']['bank'].get('_team', {}).get('gems', 0) if s['fl']['types'].get(ty) else 0, 1, need='fl')
row('Marcella captured gems / game', lambda s: s['fl']['cap'].get('Marcella', {}).get('gems', 0) if s['fl']['types'].get('Marcella') else None, 0, need='fl')
row('Marcella banked gems / game', lambda s: s['fl']['bank'].get('Marcella', {}).get('gems', 0) if s['fl']['types'].get('Marcella') else None, 0, need='fl')

print('\n== EXECUTION (execution stream metrics; per game) ==')
for k in ('passive_dmg', 'passive_wolf', 'passive_deaths', 'wake_leave_solo', 'aba_pure', 'dash_wasted', 'idle', 'deadtile', 'bagloss',
          'collected', 'banked', 'kills', 'recall_held_cancel', 'submits'):
    row(k, lambda s, k=k: s['met'].get(k), 1, need='met')

print('\n== ECONOMY (economy stream rows) ==')
row('gems captured by r150', lambda s: s['econ']['gems150'], 1, need='econ')
row('gems captured by r300', lambda s: s['econ']['gems300'], 1, need='econ')
row('first gem capture round', lambda s: s['econ']['first_cap'], 1, need='econ')
for i, pn in enumerate(('r1-150', 'r151-400', 'r401-800', 'r801+')):
    row(f'gold income /100r {pn}', lambda s, i=i: (100.0 * s['econ']['phases'][i]['gold_income'] / s['econ']['phases'][i]['rounds'])
        if len(s['econ']['phases']) > i and s['econ']['phases'][i] and s['econ']['phases'][i]['rounds'] >= 50 else None, 0, need='econ')
    row(f'hit% | contested (enemy<=6) {pn}', lambda s, i=i: (100.0 * s['econ']['phases'][i]['st_c'].get('hit', 0) / sum(s['econ']['phases'][i]['st_c'].values()))
        if len(s['econ']['phases']) > i and s['econ']['phases'][i] and sum(s['econ']['phases'][i]['st_c'].values()) >= 20 else None, 1, need='econ')


def opening_alone(s, alone):
    vs = []
    for b, o in s['econ']['opening'].items():
        for v in o['visits']:
            if v['gems'] >= 30:
                vs.append(1 if (len(v['mates']) == 0) == alone else 0)
    return (sum(vs), len(vs))


ratio_row('opening visits to >=30-gem groups: alone %', lambda s: opening_alone(s, True)[0], lambda s: opening_alone(s, True)[1], 1, need='econ')


def marc_focus(s):
    for b, bd in s['econ']['builds'].items():
        if bd['champ'] != 'Marcella':
            continue
        stc = Counter()
        n = 0
        for (rr, fa, st, e, q) in bd['seq']:
            if n >= 20:
                break
            w = q * (5 if e else 1)
            stc[ST[st]] += w
            n += w
        if n:
            return stc['foc'] / n
    return None


row('Marcella: focus share of first 20 shards', marc_focus, 2, need='econ')


def first_emblem(s, champ):
    for b, bd in s['econ']['builds'].items():
        if bd['champ'] != champ:
            continue
        e = [(rr, fa, st) for (rr, fa, st, ee, q) in bd['seq'] if ee]
        if e:
            return e[0]
    return None


for champ in ('Marcella', 'HeartOfRuin', 'Ryth', 'VesperVale', 'Vendetta'):
    row(f'{champ}: first emblem is ECON family', lambda s, c=champ: (1.0 if FAM[first_emblem(s, c)[1]] in ECONF else 0.0) if first_emblem(s, c) else None, 2, need='econ')
    row(f'{champ}: first emblem round', lambda s, c=champ: first_emblem(s, c)[0] if first_emblem(s, c) else None, 0, need='econ')


def shards_at(s, r):
    ch = s['econ'].get('checks')
    if not ch:
        return None
    for c in ch:
        if isinstance(c, dict) and c.get('r') == r:
            return c.get('shards')
    return None


print('\n== DRAFT (v95 games) ==')
dr = Counter()
for r in V:
    g = r['fights']['games'][0]
    dr[tuple(sorted(g['drafts'][r['info']['we']]))] += 1
for k, v in dr.most_common(8):
    print(v, '+'.join(k))
