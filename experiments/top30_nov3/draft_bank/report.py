#!/usr/bin/env python3
"""Tables from extract_all.py's output: banking, champion use, endgame; top-30 vs ours (v88 / v84-87) vs our opponents.
Usage: python3 -I report.py > out/tables.txt"""
import json, sys, statistics as st
from collections import Counter, defaultdict
OUT = '/home/claude/cambridge_battlecode/experiments/top30_nov3/draft_bank/out'
GROUPS = ['top30', 'ours_v88', 'ours_v84', 'opp', 't30opp']


def load(name):
    return [json.loads(l) for l in open(f'{OUT}/{name}.jsonl')]


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float('nan')


def med(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else float('nan')


def q(xs, p):
    xs = sorted(x for x in xs if x is not None)
    return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else float('nan')


def pct(a, b):
    return 100 * a / b if b else float('nan')


def main():
    T = load('teams')
    TR = load('tributes')
    L = load('locks')
    B = load('bodies')
    by = {g: [t for t in T if t['grp'] == g] for g in GROUPS}
    # restart flag: a cancelled tribute followed by another start of the same body within 12 rounds
    seq = defaultdict(list)
    for x in TR:
        seq[(x['mid'], x['body'])].append(x)
    for v in seq.values():
        v.sort(key=lambda x: x['r'])
        for a, b in zip(v, v[1:]):
            a['restart'] = a['outcome'] == 'cancelled' and b['r'] - a['r'] <= 12
        v[-1].setdefault('restart', False)
    hoard = Counter((x['grp'], x['champ']) for x in TR if x['bag'] > 300)
    print('tributes with bag > 300 (hoards) by group/champ:', dict(hoard))
    print('team-games per group:', {g: len(v) for g, v in by.items()})
    print('games (top30 set):', len({t['mid'] for t in T if t['set'] == 'top30'}), ' (ours set):', len({t['mid'] for t in T if t['set'] == 'ours'}))
    print('our versions:', Counter(t['ver'] for t in T if t['grp'].startswith('ours')))

    # ================= BANKING
    print('\n=== B1. Banking per team-game (means; n = team-games) ===')
    hdr = f"{'metric':38s}" + ''.join(f'{g:>11s}' for g in GROUPS)
    print(hdr)

    def row(name, f, fmt='{:11.1f}'):
        print(f'{name:38s}' + ''.join(fmt.format(f(by[g])) for g in GROUPS))
    row('n team-games', lambda v: len(v), '{:11d}')
    row('final round', lambda v: mean(t['final'] for t in v))
    row('banked (final sub)', lambda v: mean(t['sub'] for t in v))
    row('banks landed per game', lambda v: mean(t['n_banked'] for t in v))
    row('banks per 100 gems banked', lambda v: 100 * sum(t['n_banked'] for t in v) / max(1, sum(t['sub'] for t in v)))
    row('mean bag (per landed bank)', lambda v: mean(x for t in v for x in t['bags']))
    row('median bag', lambda v: med(x for t in v for x in t['bags']))
    row('bag p25 / p75', lambda v: q([x for t in v for x in t['bags']], 0.25), '{:11.0f}')
    row('bag p75', lambda v: q([x for t in v for x in t['bags']], 0.75), '{:11.0f}')
    row('share of bags < 30', lambda v: pct(sum(1 for t in v for x in t['bags'] if x < 30), sum(len(t['bags']) for t in v)))
    row('share of bags >= 80', lambda v: pct(sum(1 for t in v for x in t['bags'] if x >= 80), sum(len(t['bags']) for t in v)))
    row('tributes started per game', lambda v: mean(t['n_sub'] for t in v))
    row('cancelled per game', lambda v: mean(t['n_cancel'] for t in v))
    row('cancel rate % of starts', lambda v: pct(sum(t['n_cancel'] for t in v), sum(t['n_sub'] for t in v)))
    for c in ('death', 'lock', 'stun', 'self', 'unknown'):
        row(f'  cancel cause {c} per game', lambda v, c=c: mean(t['cancel_cause'].get(c, 0) for t in v), '{:11.2f}')
    row('deaths per game', lambda v: mean(t['deaths'] for t in v))
    row('gems lost on death per game', lambda v: mean(t['gems_lost'] for t in v))
    row('deaths with bag >= 20 per game', lambda v: mean(t['deaths_bag20'] for t in v), '{:11.2f}')
    row('gems lost per 100 captured', lambda v: 100 * sum(t['gems_lost'] for t in v) / max(1, sum(t['captured'] for t in v)))
    row('carried gem-rounds / round (exposure)', lambda v: mean(t['carried_rounds'] / max(1, t['final']) for t in v))
    row('carried at the end', lambda v: mean(t['carried_end'] for t in v))
    row('carried at end, losers only', lambda v: mean(t['carried_end'] for t in v if t['res'] == 'loss'))
    row('mean rounds carried (bag start->bank)', lambda v: mean(x['carried'] for t in v for x in [] ) if False else float('nan'))
    row('locks placed per game', lambda v: mean(t['locks'] for t in v), '{:11.2f}')
    row('locks that hit a tribute per game', lambda v: mean(t['locks_hit'] for t in v), '{:11.2f}')
    row('banks via spawn (recall) %', lambda v: pct(sum(t['via_spawn'] for t in v), sum(t['n_banked'] for t in v)))
    row('banks with enemy within 6 %', lambda v: pct(sum(t['en6_banks'] for t in v), sum(t['n_banked'] for t in v)))
    row('Marcella share of team banked (has M)', lambda v: 100 * mean(t['marc_share'] for t in v if t['marc_share'] is not None))
    row('games with Marcella %', lambda v: pct(sum(1 for t in v if t['has_marc']), len(v)))
    row('win rate %', lambda v: pct(sum(1 for t in v if t['res'] == 'win'), len(v)))

    print('\n=== B2. Per tribute (Submit gems events) ===')
    trb = {g: [x for x in TR if x['grp'] == g] for g in GROUPS}
    print(f"{'metric':38s}" + ''.join(f'{g:>11s}' for g in GROUPS))

    def trow(name, f, fmt='{:11.1f}'):
        print(f'{name:38s}' + ''.join(fmt.format(f(trb[g])) for g in GROUPS))
    trow('n tributes', lambda v: len(v), '{:11d}')
    trow('bag mean', lambda v: mean(x['bag'] for x in v))
    trow('rounds carried since bag start (mean)', lambda v: mean(x['carried'] for x in v))
    trow('  median', lambda v: med(x['carried'] for x in v))
    trow('  p90', lambda v: q([x['carried'] for x in v], 0.9), '{:11.0f}')
    trow('rounds since last capture (mean)', lambda v: mean(x['since_cap'] for x in v))
    trow('walk from last capture to altar (mean)', lambda v: mean(x['walk'] for x in v))
    trow('  median', lambda v: med(x['walk'] for x in v))
    trow('  share walk > 25 steps %', lambda v: pct(sum(1 for x in v if x['walk'] is not None and x['walk'] > 25), sum(1 for x in v if x['walk'] is not None)))
    trow('gems per round carried (bag/carried)', lambda v: mean(x['bag'] / x['carried'] for x in v if x['carried']), '{:11.2f}')
    trow('altar: own spawn altar %', lambda v: pct(sum(1 for x in v if x['aclass'] == 'spawnaltar'), len(v)))
    trow('altar: field own half %', lambda v: pct(sum(1 for x in v if x['aclass'] == 'field_own'), len(v)))
    trow('altar: field mid %', lambda v: pct(sum(1 for x in v if x['aclass'] == 'field_mid'), len(v)))
    trow('altar: field their half %', lambda v: pct(sum(1 for x in v if x['aclass'] == 'field_their'), len(v)))
    trow('altar: enemy spawn altar %', lambda v: pct(sum(1 for x in v if x['aclass'] == 'enemyspawnaltar'), len(v)))
    trow('via spawn (recall then bank) %', lambda v: pct(sum(1 for x in v if x['via_spawn']), len(v)))
    trow('enemy within 6 at start %', lambda v: pct(sum(1 for x in v if x['en6'] > 0), len(v)))
    trow('enemy within 10 at start %', lambda v: pct(sum(1 for x in v if x['en10'] > 0), len(v)))
    trow('  cancel rate when enemy within 6 %', lambda v: pct(sum(1 for x in v if x['en6'] > 0 and x['outcome'] == 'cancelled'), sum(1 for x in v if x['en6'] > 0)))
    trow('  cancel rate when no enemy within 10 %', lambda v: pct(sum(1 for x in v if x['en10'] == 0 and x['outcome'] == 'cancelled'), sum(1 for x in v if x['en10'] == 0)))
    trow('ally within 5 at start %', lambda v: pct(sum(1 for x in v if x['allies5'] > 0), len(v)))
    trow('hp at start (mean)', lambda v: mean(x['hp'] for x in v), '{:11.2f}')
    trow('cancelled %', lambda v: pct(sum(1 for x in v if x['outcome'] == 'cancelled'), len(v)))
    trow('cancelled, not restarted within 12r %', lambda v: pct(sum(1 for x in v if x['outcome'] == 'cancelled' and not x['restart']), len(v)))
    trow('gems in final cancels (<=300) / game', lambda v: sum(x['bag'] for x in v if x['outcome'] == 'cancelled' and not x['restart'] and x['bag'] <= 300) / max(1, len({x['mid'] + str(x['team']) for x in v})))
    trow('bag mean, bags <= 300', lambda v: mean(x['bag'] for x in v if x['bag'] <= 300))
    trow('gems in cancelled tributes / game', lambda v: sum(x['bag'] for x in v if x['outcome'] == 'cancelled') / max(1, len({x['mid'] + str(x['team']) for x in v})))
    trow('bag >= 60 share %', lambda v: pct(sum(1 for x in v if x['bag'] >= 60), len(v)))
    trow('  cancel rate for bags >= 60 %', lambda v: pct(sum(1 for x in v if x['bag'] >= 60 and x['outcome'] == 'cancelled'), sum(1 for x in v if x['bag'] >= 60)))
    trow('  cancel rate for bags < 30 %', lambda v: pct(sum(1 for x in v if x['bag'] < 30 and x['outcome'] == 'cancelled'), sum(1 for x in v if x['bag'] < 30)))

    print('\n=== B3. Bag size by round band (mean bag of landed tributes started in the band) ===')
    bands = [(0, 150), (150, 400), (400, 800), (800, 1200), (1200, 2001)]
    print(f"{'band':12s}" + ''.join(f'{g:>16s}' for g in GROUPS))
    for a, b in bands:
        print(f'{a:4d}-{b:4d}   ' + ''.join(f"{mean(x['bag'] for x in trb[g] if a <= x['r'] < b and x['outcome'] == 'banked'):8.1f} n={sum(1 for x in trb[g] if a <= x['r'] < b):4d}  " for g in GROUPS))

    print('\n=== B4. By champion: bag mean, carried rounds, cancel %, share of the team\'s banks (top30 vs ours) ===')
    for ch in ['Marcella', 'HeartOfRuin', 'VesperVale', 'Vendetta', 'Ryth', 'Willow', 'Varg', 'Tavi', 'Cassi', 'Issac', 'Prism', 'Ren']:
        line = f'{ch:12s}'
        for g in ('top30', 'ours_v88', 'ours_v84', 'opp'):
            v = [x for x in trb[g] if x['champ'] == ch]
            line += f"  {g}: n={len(v):4d} bag {mean(x['bag'] for x in v):5.1f} carried {mean(x['carried'] for x in v):5.0f} cancel {pct(sum(1 for x in v if x['outcome'] == 'cancelled'), len(v)):4.1f}%"
        print(line)

    print('\n=== B5. Banking by team size (champs per team) ===')
    for n in (3, 4, 5):
        print(f'-- {n} champions')
        print(f"{'metric':38s}" + ''.join(f'{g:>11s}' for g in GROUPS))
        for name, f, fmt in (('n team-games', lambda v: len(v), '{:11d}'), ('banks landed per game', lambda v: mean(t['n_banked'] for t in v), '{:11.1f}'),
                             ('mean bag', lambda v: mean(x for t in v for x in t['bags']), '{:11.1f}'),
                             ('cancel rate %', lambda v: pct(sum(t['n_cancel'] for t in v), sum(t['n_sub'] for t in v)), '{:11.1f}'),
                             ('gems lost on death per game', lambda v: mean(t['gems_lost'] for t in v), '{:11.1f}'),
                             ('deaths per game', lambda v: mean(t['deaths'] for t in v), '{:11.1f}'),
                             ('carried exposure / round', lambda v: mean(t['carried_rounds'] / max(1, t['final']) for t in v), '{:11.1f}'),
                             ('locks per game', lambda v: mean(t['locks'] for t in v), '{:11.2f}'),
                             ('final round', lambda v: mean(t['final'] for t in v), '{:11.0f}'),
                             ('win rate %', lambda v: pct(sum(1 for t in v if t['res'] == 'win'), len(v)), '{:11.1f}')):
            print(f'{name:38s}' + ''.join(fmt.format(f([t for t in by[g] if t['champs'] == n])) for g in GROUPS))

    print('\n=== B6. Locks: when and on what ===')
    lk = {g: [x for x in L if x['grp'] == g] for g in GROUPS}
    print(f"{'metric':38s}" + ''.join(f'{g:>11s}' for g in GROUPS))
    for name, f, fmt in (('n locks', lambda v: len(v), '{:11d}'),
                         ('locks per team-game', lambda v: len(v) / max(1, len(by[v[0]['grp']])) if v else 0, '{:11.2f}'),
                         ('hit an enemy tribute %', lambda v: pct(sum(1 for x in v if x['victim']), len(v)), '{:11.1f}'),
                         ('  victim bag mean', lambda v: mean(x['victim']['bag'] for x in v if x['victim']), '{:11.1f}'),
                         ('enemy within 3 of altar at placement %', lambda v: pct(sum(1 for x in v if x['en3'] > 0), len(v)), '{:11.1f}'),
                         ('on own spawn altar %', lambda v: pct(sum(1 for x in v if x['aclass'] == 'spawnaltar'), len(v)), '{:11.1f}'),
                         ('on enemy spawn altar %', lambda v: pct(sum(1 for x in v if x['aclass'] == 'enemyspawnaltar'), len(v)), '{:11.1f}'),
                         ('on field altar %', lambda v: pct(sum(1 for x in v if x['aclass'].startswith('field')), len(v)), '{:11.1f}'),
                         ('round mean', lambda v: mean(x['r'] for x in v), '{:11.0f}'),
                         ('placed when enemy sub >= 700 %', lambda v: pct(sum(1 for x in v if x['sub_en'] >= 700), len(v)), '{:11.1f}')):
        print(f'{name:38s}' + ''.join(fmt.format(f(lk[g])) for g in GROUPS))
    print('locks by champion:', {g: dict(Counter(x['champ'] for x in lk[g])) for g in ('top30', 'ours_v88', 'ours_v84')})
    # which top-30 teams lock
    tl = Counter(x['name'] if 'name' in x else None for x in [])
    teams_locks = defaultdict(lambda: [0, 0, 0])
    for t in by['top30']:
        teams_locks[t['name']][0] += 1
        teams_locks[t['name']][1] += t['locks']
        teams_locks[t['name']][2] += t['locks_hit']
    print('top-30 teams: games, locks, locks that hit a tribute:')
    for n, (a, b, c) in sorted(teams_locks.items(), key=lambda kv: -kv[1][1] / max(1, kv[1][0]))[:30]:
        print(f'  {n:32s} {a:3d} {b:3d} {c:3d}  {b / a:.2f}/game')

    # ================= CHAMPION USE
    print('\n=== C1. Champion use per champion type (per 100 alive rounds), top30 vs ours_v88 vs ours_v84 vs opp ===')
    bb = {g: [x for x in B if x['grp'] == g] for g in GROUPS}
    for ch in ['HeartOfRuin', 'VesperVale', 'Vendetta', 'Marcella', 'Ryth', 'Willow', 'Varg', 'Tavi', 'Cassi', 'Issac', 'Prism', 'Ren']:
        print(f'\n-- {ch}')
        print(f"{'metric':40s}" + ''.join(f'{g:>11s}' for g in GROUPS))
        rows = []
        for g in GROUPS:
            v = [x for x in bb[g] if x['champ'] == ch]
            al = sum(x['alive'] for x in v) / 100 or 1e-9
            camp = sum(sum(x['camp_hits'].values()) for x in v)
            champ = sum(x['champ_hits'].get(k, 0) for x in v for k in x['champ_hits'] if k != 'miss')
            casts = Counter()
            for x in v:
                for k, n in x['casts'].items():
                    casts[k] += n
            dash = Counter()
            for x in v:
                for k, n in x['dash'].items():
                    dash[k] += n
            stn = Counter()
            for x in v:
                for k, n in x['stuns'].items():
                    stn[k] += n
            msd = Counter()
            for x in v:
                for k, n in x['marc_spell_dist'].items():
                    msd[k] += n
            rows.append({'n': len(v), 'alive': sum(x['alive'] for x in v) / max(1, len(v)), 'camp': camp / al, 'champ': champ / al,
                         'camp_atk': sum(x['camp_hits'].get('atk', 0) for x in v) / al, 'champ_atk': sum(x['champ_hits'].get('atk', 0) for x in v) / al,
                         'casts': {k: n / al for k, n in casts.items()}, 'cast_total': sum(casts.values()) / al,
                         'dash': {k: n / al for k, n in dash.items()}, 'dash_tot': sum(dash.values()), 'dash_fight%': pct(dash['fight'], sum(dash.values())),
                         'dash_camp%': pct(dash['camp'], sum(dash.values())), 'dash_travel%': pct(dash['travel'] + dash['near'], sum(dash.values())),
                         'stun_n': stn['n'] / al, 'stun_kill3%': pct(stn['kill3'], stn['n']), 'stun_trib%': pct(stn['on_tribute'], stn['n']),
                         'msd4%': pct(msd['4'], sum(msd.values())), 'msd_le2%': pct(msd['0'] + msd['1'] + msd['2'], sum(msd.values())),
                         'spell_kills': sum(x['spell_kills'] for x in v) / max(1, len(v)), 'kills': sum(x['kills'] for x in v) / max(1, len(v)),
                         'deaths': sum(x['deaths'] for x in v) / max(1, len(v)), 'banked': sum(x['banked'] for x in v) / max(1, len(v)),
                         'captured': sum(x['captured'] for x in v) / max(1, len(v)), 'gold': sum(x['gold_cap'] for x in v) / max(1, len(v)),
                         'shops': sum(x['shops'] for x in v) / max(1, len(v)), 'shops_field': sum(x['shops_field'] for x in v) / max(1, len(v)),
                         'fight_r': sum(x['fight_rounds'] for x in v) / al, 'farm_r': sum(x['farm_rounds'] for x in v) / al,
                         'lock_atk': sum(x['lock_attacks'] for x in v) / max(1, len(v)), 'tele': sum(x['teleports'] for x in v) / max(1, len(v))})

        def prow(name, key, fmt='{:11.2f}'):
            print(f'{name:40s}' + ''.join(fmt.format(r[key]) if not isinstance(key, tuple) else fmt.format(r[key[0]].get(key[1], 0)) for r in rows))
        prow('n bodies', 'n', '{:11d}')
        prow('alive rounds per game', 'alive', '{:11.0f}')
        prow('camp hits /100r (all kinds)', 'camp')
        prow('  basic attacks on camps /100r', 'camp_atk')
        prow('champion hits /100r (all kinds)', 'champ')
        prow('  basic attacks on champions /100r', 'champ_atk')
        prow('casts /100r (all abilities)', 'cast_total')
        keys = sorted({k for r in rows for k in r['casts']})
        for k in keys:
            prow(f'  cast {k} /100r', ('casts', k))
        prow('dash: fight %', 'dash_fight%', '{:11.1f}')
        prow('dash: on camp %', 'dash_camp%', '{:11.1f}')
        prow('dash: travel/near %', 'dash_travel%', '{:11.1f}')
        prow('stuns landed /100r', 'stun_n')
        prow('  stun -> target dead within 3 %', 'stun_kill3%', '{:11.1f}')
        prow('  stun on a tributing target %', 'stun_trib%', '{:11.1f}')
        if ch == 'Marcella':
            prow('Marcella spell at range 4 %', 'msd4%', '{:11.1f}')
            prow('Marcella spell at range <= 2 %', 'msd_le2%', '{:11.1f}')
        prow('spell kills per game', 'spell_kills')
        prow('kills per game', 'kills')
        prow('deaths per game', 'deaths')
        prow('gems banked per game', 'banked', '{:11.0f}')
        prow('gems captured per game', 'captured', '{:11.0f}')
        prow('gold captured per game', 'gold', '{:11.0f}')
        prow('shop visits per game', 'shops')
        prow('  shops away from spawn (Tavi)', 'shops_field')
        prow('fight rounds /100r', 'fight_r')
        prow('farm rounds /100r', 'farm_r')
        prow('lock attacks per game', 'lock_atk')
        prow('teleports per game', 'tele')

    # Vesper gold share
    print('\n=== C2. Vesper gold: share of the team\'s captured gold taken by Vesper (teams with Vesper) ===')
    for g in GROUPS:
        tot = defaultdict(lambda: [0, 0])
        for x in bb[g]:
            key = (x['mid'], x['team'])
            tot[key][0] += x['gold_cap']
            if x['champ'] == 'VesperVale':
                tot[key][1] += x['gold_cap']
        v = [b / a for a, b in tot.values() if a > 0 and b > 0]
        n_v = sum(1 for a, b in tot.values() if b > 0)
        print(f'  {g:10s} team-games with Vesper {n_v:4d}: Vesper share of team gold {100 * mean(v):5.1f}%  (1/n_champs reference)')

    # ================= ENDGAME
    print('\n=== E1. Endgame: end reason, round the winner reached 1000, games ending at r2000 ===')
    for g in GROUPS:
        v = by[g]
        n = len(v)
        r2000 = sum(1 for t in v if t['end'] != 'gems')
        win = [t for t in v if t['res'] == 'win']
        rr = [t['reach1000'] for t in win if t['reach1000']]
        print(f"  {g:10s} n={n:4d} ends by gems {pct(n - r2000, n):5.1f}%  at r2000 {pct(r2000, n):5.1f}% (tiebreak gold {sum(1 for t in v if t['end'] == 'tiebreak_gold')})  "
              f"winner reached 1000 at: mean {mean(rr):6.0f} median {med(rr):6.0f} p25 {q(rr, 0.25):5.0f} p75 {q(rr, 0.75):5.0f}; wins at r2000 {sum(1 for t in win if t['end'] != 'gems')}, losses at r2000 {sum(1 for t in v if t['res'] == 'loss' and t['end'] != 'gems')}")
        for n_ch in (3, 4, 5):
            vv = [t for t in win if t['champs'] == n_ch and t['reach1000']]
            print(f"      {n_ch}c: winner reach1000 mean {mean(t['reach1000'] for t in vv):6.0f} median {med(t['reach1000'] for t in vv):6.0f} n={len(vv)}; loser final sub mean {mean(t['sub'] for t in v if t['champs'] == n_ch and t['res'] == 'loss'):5.0f}")
    print('\n=== E2. Last 200 rounds: what the loser and the winner do (share of body-rounds; where: own/mid/their half) ===')
    for g in GROUPS:
        for res in ('loss', 'win'):
            v = [t for t in by[g] if t['res'] == res]
            beh = Counter()
            half = Counter()
            for t in v:
                beh.update(t['beh200'])
                half.update(t['half200'])
            tb = sum(beh.values()) or 1
            th = sum(half.values()) or 1
            print(f"  {g:10s} {res:4s} n={len(v):4d} " + ' '.join(f'{k} {pct(beh[k], tb):4.1f}%' for k in ('farm', 'fight', 'walk', 'still', 'spawn', 'dead')) +
                  '  | ' + ' '.join(f'{k} {pct(half[k], th):4.1f}%' for k in ('own', 'mid', 'their')) +
                  f"  locks in last 200r {mean(sum(1 for r in t['lock_rounds'] if r >= t['final'] - 200) for t in v):.2f}")
    print('\n=== E3. Close games (final margin < 150 gems) and games lost with >= 60 gems carried at the end ===')
    for g in GROUPS:
        v = by[g]
        close = [t for t in v if abs(t['sub'] - t['sub_en']) < 150]
        lost_carry = [t for t in v if t['res'] == 'loss' and t['carried_end'] >= 60]
        lost_close_carry = [t for t in close if t['res'] == 'loss' and t['carried_end'] + t['sub'] >= t['sub_en']]
        print(f"  {g:10s} close games {len(close):4d}/{len(v)} ({pct(len(close), len(v)):4.1f}%)  lost with >= 60 carried {len(lost_carry):3d} ({pct(len(lost_carry), len(v)):4.1f}%)  lost close with banked+carried >= winner's banked {len(lost_close_carry):3d}")
        for t in lost_close_carry[:6]:
            print(f"      {t['mid'][:8]} {t['map']:20s} {t['sub']}-{t['sub_en']} carried {t['carried_end']} final r{t['final']} end {t['end']}")


if __name__ == '__main__':
    main()
