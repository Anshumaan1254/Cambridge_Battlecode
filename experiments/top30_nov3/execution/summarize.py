#!/usr/bin/env python3
"""Aggregate out/met/*.json: per-game means by side group, gaps, gem-loss estimates, camp handling, examples.
    nice -n 19 python3 -I execution/summarize.py > execution/out/summary.txt
Side groups: top_W / top_L (winner / loser side of a top-30 vs top-30 game), top (both), we_v88 (our side, v88 games: ranked losses +
paired unranked losses), opp_v88, we_old_L / we_old_W / opp_old (v84-v87 ranked, Nov 2-3)."""
import json, os, sys, glob
from collections import Counter, defaultdict
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h30  # noqa: E402

KEYS = ['alive', 'offspawn', 'stall12', 'stall12_n', 'stall_live', 'stall_dead', 'aba', 'aba_pure', 'rev', 'rev_pure', 'passive_n', 'passive_dmg',
        'passive_hits', 'passive_deaths', 'passive_wolf', 'passive_elk', 'passive_golem', 'passive_monolith', 'wake_leave', 'wake_leave_solo',
        'wake_leave_cost', 'deadtile', 'rewtile', 'idle', 'recall_bait', 'recall_held', 'recall_held_cancel', 'tribfail', 'tribfail_died',
        'tribfail_other', 'tribfail_gems', 'submits', 'dash', 'dash_travel', 'dash_wasted', 'noev', 'noev_far', 'noev_off', 'deaths', 'bagloss',
        'collected', 'banked', 'kills', 'kill_gems']
CTYPES = ['wolf', 'elk', 'golem', 'monolith']


def load():
    rows = []
    for f in glob.glob(f'{h30.EXE}/out/met/*.json'):
        rows.append(json.load(open(f)))
    return rows


def sides(rows):
    out = defaultdict(list)   # group -> [(row, t)]
    for r in rows:
        for t in (0, 1):
            s = dict(r['sides'][str(t)])
            s['passive_golem'] = s.get('passive_golem', 0) + s.get('passive_5', 0)
            s['_row'] = r
            s['_t'] = t
            if r['tag'] == 'top':
                out['top'].append(s)
                out['top_W' if r['winner'] == t else 'top_L'].append(s)
            elif r['tag'] == 'v88':
                out['we_v88' if t == r['we'] else 'opp_v88'].append(s)
            else:
                if t == r['we']:
                    out['we_old_L' if r['winner'] != t else 'we_old_W'].append(s)
                    out['we_old'].append(s)
                else:
                    out['opp_old'].append(s)
    return out


def mean(xs, k):
    return float(np.mean([x.get(k, 0) for x in xs])) if xs else 0.0


def per1000(xs, k):
    a = sum(x.get('alive', 0) for x in xs)
    return 1000.0 * sum(x.get(k, 0) for x in xs) / max(1, a)


def main():
    rows = load()
    S = sides(rows)
    groups = ['top_W', 'top_L', 'top', 'we_v88', 'opp_v88', 'we_old_L', 'we_old_W', 'opp_old']
    print(f'games: top-30 {sum(1 for r in rows if r["tag"] == "top")}, v88 {sum(1 for r in rows if r["tag"] == "v88")}, old {sum(1 for r in rows if r["tag"] == "old")}')
    print('side-games per group:', {g: len(S[g]) for g in groups})
    print('\nPER-GAME MEANS (per side-game) and per 1000 alive body-rounds [in brackets]')
    hdr = f"{'metric':20}" + ''.join(f'{g:>22}' for g in groups)
    print(hdr)
    for k in KEYS:
        line = f'{k:20}'
        for g in groups:
            line += f'{mean(S[g], k):12.1f} [{per1000(S[g], k):7.2f}]'
        print(line)
    # ratios
    print('\nRATIOS: passive dmg per passive run, camp hits taken per camp hit given (by type), kills per 1000 body-rounds')
    for g in groups:
        xs = S[g]
        given = Counter()
        taken = Counter()
        far = Counter()
        for x in xs:
            for kk, v in x['camp_given'].items():
                ct, dd = kk.split('@')
                ct = 'golem' if ct == '5' else ct
                given[ct] += v
                if int(dd) >= 4:
                    far[ct] += v
            for ct, v in x['camp_taken'].items():
                taken['golem' if ct == '5' else ct] += v
        print(f'  {g:9} ' + ' '.join(f"{ct}: given {given[ct] / max(1, len(xs)):6.1f}/g taken {taken[ct] / max(1, len(xs)):6.1f}/g ratio {taken[ct] / max(1, given[ct]):.2f} from>=4 {far[ct] / max(1, given[ct]):.2f} |" for ct in CTYPES))
    # kills: attackers
    print('\nGROUP KILLS: attackers per kill and max simultaneous attackers, duration (first hit -> dead), by group gems class; share contested; step-on delay')
    for g in groups:
        xs = S[g]
        by = defaultdict(list)
        for x in xs:
            for k in x['kill_list']:
                cls = 'small<=12' if k[1] <= 12 else 'mid<=40' if k[1] <= 40 else 'big>40'
                by[cls].append(k)
        line = f'  {g:9} '
        for cls in ('small<=12', 'mid<=40', 'big>40'):
            L = by[cls]
            if not L:
                continue
            line += (f"{cls}: n {len(L) / max(1, len(xs)):5.1f}/g attackers {np.mean([k[6] for k in L]):.2f} sim {np.mean([k[7] for k in L]):.2f} "
                     f"dur {np.mean([k[5] - k[4] for k in L]):5.1f} contested {np.mean([k[8] for k in L]):.2f} lost-to-other {np.mean([k[9] == 'other' for k in L]):.2f} "
                     f"delay>8 {np.mean([(k[10] is None or k[10] > 8 + 6) for k in L]):.2f} | ")
        print(line)
    # wake-leave by camp type
    print('\nWAKE-AND-LEAVE by camp group type (per game): n, cost dmg, solo (no team-mate hit it)')
    for g in groups:
        xs = S[g]
        c = Counter()
        cost = Counter()
        for x in xs:
            for w in x['wake_list']:
                ct = 'm' if 'm' in w['types'] else 'e' if 'e' in w['types'] else 'w' if 'w' in w['types'] else 'o'
                c[ct] += 1
                cost[ct] += w['cost']
        print(f'  {g:9} ' + ' '.join(f"{ct}: {c[ct] / max(1, len(xs)):4.2f}/g cost {cost[ct] / max(1, len(xs)):5.0f}" for ct in 'wem'))
    # by champion: stalls / idle / passive per 1000 body-rounds for we_v88 vs top
    print('\nBY CHAMPION (per 1000 body-rounds of that champion): stall12, idle, passive dmg, aba_pure, noev_far -- we_v88 | top')
    # need per-body data: not stored; skip
    # ---- gap table and gem estimate
    print('\nGAP TABLE: we_v88 vs top_L (losers of top-30 games) and vs opp_v88 (opponents in the same games); per game; gem-loss estimate per game')
    unit = {'stall12': 0.2, 'idle': 0.2, 'deadtile': 0.2, 'rewtile': 0.2, 'aba_pure': 0.4, 'rev_pure': 0.2, 'passive_deaths': 45, 'passive_dmg': 0.004,
            'wake_leave_cost': 0.004, 'tribfail_gems': 0.5, 'dash_wasted': 0.3, 'recall_held_cancel': 0.5, 'noev_far': 0.1, 'stall_live': 0.2}
    print(f"  {'metric':20} {'we_v88':>8} {'top_L':>8} {'top_W':>8} {'opp_v88':>8} {'we_old_L':>8} {'d_topL':>8} {'gems/g':>7}  unit")
    est = []
    for k in ['stall12', 'stall_live', 'idle', 'deadtile', 'rewtile', 'aba_pure', 'rev_pure', 'passive_dmg', 'passive_deaths', 'wake_leave_cost', 'tribfail_gems',
              'dash_wasted', 'recall_held_cancel', 'noev_far']:
        a, b, c, d, e = mean(S['we_v88'], k), mean(S['top_L'], k), mean(S['top_W'], k), mean(S['opp_v88'], k), mean(S['we_old_L'], k)
        gems = (a - b) * unit.get(k, 0)
        est.append((gems, k))
        print(f'  {k:20} {a:8.1f} {b:8.1f} {c:8.1f} {d:8.1f} {e:8.1f} {a - b:+8.1f} {gems:+7.1f}  {unit.get(k, 0)}')
    print('  ranked by estimated gems/game lost vs top-30 losers:', [(k, round(g, 1)) for g, k in sorted(est, reverse=True)])
    json.dump({g: {k: mean(S[g], k) for k in KEYS} for g in groups}, open(f'{h30.EXE}/out/summary_means.json', 'w'), indent=1)

    # ---- examples from our v88 games
    print('\nEXAMPLES (our v88 games): stalls >= 20 rounds next to a live group with no enemy within 6 (key, map, body, champ, r, len, at, enemy_d, gstate, camp hits, dashes)')
    ex = []
    for r in rows:
        if r['tag'] != 'v88':
            continue
        for e in r['ex'].get('stall', []):
            if e[0] == r['we'] and e[7] == 'alive' and e[6] > 6:
                ex.append((e[4], r['key'][:8], r['map'], e[1], e[2], e[3], e[5], e[6], e[7], e[8], e[9]))
    for x in sorted(ex, reverse=True)[:20]:
        print('   ', x)
    print('  stalls >= 20 on / next to a dead group (waiting for a respawn):')
    ex = []
    for r in rows:
        if r['tag'] != 'v88':
            continue
        for e in r['ex'].get('stall', []):
            if e[0] == r['we'] and e[7] == 'dead':
                ex.append((e[4], r['key'][:8], r['map'], e[1], e[2], e[3], e[5], e[6]))
    for x in sorted(ex, reverse=True)[:12]:
        print('   ', x)
    print('  passive runs (key, map, body, champ, r0, r1, hits, dmg, camp type, died, at):')
    ex = []
    for r in rows:
        if r['tag'] != 'v88':
            continue
        for e in r['ex'].get('passive', []):
            if e[0] == r['we']:
                ex.append((e[6], r['key'][:8], r['map'], e[1], e[2], e[3], e[4], e[5], e[7], e[8], e[9]))
    for x in sorted(ex, reverse=True)[:15]:
        print('   ', x)
    print('  wake-and-leave (key, map, group types, gems, body, champ, r, last hit, dist, cost):')
    ex = []
    for r in rows:
        if r['tag'] != 'v88':
            continue
        for w in r['sides'][str(r['we'])]['wake_list']:
            ex.append((w['cost'], r['key'][:8], r['map'], w['types'], w['gems'], w['b'], w['champ'], w['r'], w['last'], w['dist'], w['teamhit']))
    for x in sorted(ex, reverse=True)[:15]:
        print('   ', x)
    print('  A-B-A pure (key, map, body, champ, r, from, to, enemy_d):')
    ex = []
    for r in rows:
        if r['tag'] != 'v88':
            continue
        for e in r['ex'].get('aba', []):
            if e[0] == r['we']:
                ex.append((r['key'][:8], r['map'], e[1], e[2], e[3], e[4], e[5], e[6]))
    for x in ex[:15]:
        print('   ', x)
    print('  wasted travel dashes (key, map, body, champ, r, from, to):')
    ex = []
    for r in rows:
        if r['tag'] != 'v88':
            continue
        for e in r['ex'].get('dash', []):
            if e[0] == r['we']:
                ex.append((r['key'][:8], r['map'], e[1], e[2], e[3], e[4], e[5]))
    for x in ex[:12]:
        print('   ', x)
    # per-map for our v88 vs top on the same map (stall, passive, idle)
    print('\nPER MAP (maps with >= 2 of our v88 games and >= 2 top games): stall12/g, idle/g, passive dmg/g, aba_pure/g -- we_v88 | top')
    bym = defaultdict(lambda: defaultdict(list))
    for g in ('we_v88', 'top'):
        for x in S[g]:
            bym[x['_row']['map']][g].append(x)
    for m in sorted(bym):
        a, b = bym[m]['we_v88'], bym[m]['top']
        if len(a) >= 2 and len(b) >= 2:
            print(f"  {m:22} n {len(a):2}/{len(b):2}  stall {mean(a, 'stall12'):5.0f}|{mean(b, 'stall12'):5.0f}  idle {mean(a, 'idle'):5.0f}|{mean(b, 'idle'):5.0f}  passive {mean(a, 'passive_dmg'):6.0f}|{mean(b, 'passive_dmg'):6.0f}  aba {mean(a, 'aba_pure'):5.1f}|{mean(b, 'aba_pure'):5.1f}  deaths {mean(a, 'deaths'):4.1f}|{mean(b, 'deaths'):4.1f}  banked {mean(a, 'banked'):5.0f}|{mean(b, 'banked'):5.0f}")


if __name__ == '__main__':
    main()
