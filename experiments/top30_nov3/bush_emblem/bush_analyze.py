#!/usr/bin/env python3
"""Tables from out/{top,our}_bush.jsonl.   python3 -I bush_analyze.py > bush_tables.txt
Sides: TW / TL = winning / losing top-30 side (top-30 vs top-30 games); US / OPP = us / our opponent (same games, loss-heavy);
US88 = our v88 games only. Map class by bush share of passable tiles: lo < 0.03 <= mid < 0.06 <= hi."""
import json
from collections import defaultdict

B = '/home/claude/cambridge_battlecode/experiments/top30_nov3/bush_emblem/out'


def mc(f):
    return 'lo' if f < 0.03 else 'mid' if f < 0.06 else 'hi'


def side(g, t):
    if g['we'] is None:
        return 'TW' if g['res'][t] == 'W' else 'TL'
    return 'US' if t == g['we'] else 'OPP'


def load():
    G = []
    for ds in ('top', 'our'):
        for l in open(f'{B}/{ds}_bush.jsonl'):
            G.append(json.loads(l))
    return G


def pct(a, b):
    return f'{100 * a / b:5.1f}% (n={b})' if b else '   -  (n=0)'


def main():
    G = load()
    SIDES = ('TW', 'TL', 'US', 'OPP', 'US88')
    print('games: top', sum(1 for g in G if g['we'] is None), ' ours', sum(1 for g in G if g['we'] is not None),
          ' ours v88', sum(1 for g in G if g['ver'] == 'v88'))
    print('map classes (games):', {c: sum(1 for g in G if mc(g['bush_frac']) == c) for c in ('lo', 'mid', 'hi')})

    def sides_of(g, t):
        s = [side(g, t)]
        if s[0] == 'US' and g['ver'] == 'v88':
            s.append('US88')
        return s

    # ---------- A. openings
    A = defaultdict(lambda: defaultdict(int))
    for g in G:
        c = mc(g['bush_frac'])
        for f in g['fights']:
            for s in sides_of(g, f['first']):
                for cc in (c, 'all'):
                    k = A[(s, cc)]
                    k['open'] += 1
                    k['a_in'] += f['a_in']
                    k['a_from'] += f['a_from']
                    k['hidden'] += f['hidden']
                    if f['exch'] and f['win'] is not None:
                        w = f['win'] == f['first']
                        key = 'in' if f['a_from'] else 'out'
                        k['ex_' + key] += 1
                        k['w_' + key] += w
                        if f['hidden']:
                            k['ex_hid'] += 1
                            k['w_hid'] += w
            # target side defending from a bush
            tt = 1 - f['first']
            if f['exch'] and f['win'] is not None:
                for s in sides_of(g, tt):
                    for cc in (c, 'all'):
                        k = A[(s, cc)]
                        key = 'tin' if f['t_in'] else 'tout'
                        k['dx_' + key] += 1
                        k['dw_' + key] += f['win'] == tt
    print('\nA. OPENINGS by the opener\'s side: share opened from a bush (opener in a bush at s-1 / in one during s-3..s-1 / hidden from'
          ' the target);\n   win share of exchanges (decided ones) opened from a bush (s-3..s-1) vs from open ground; hidden openers; defending'
          ' from a bush (target in a bush at s-1)')
    for cc in ('all', 'lo', 'mid', 'hi'):
        print(f'  [{cc}]')
        for s in SIDES:
            k = A[(s, cc)]
            if not k['open']:
                continue
            print(f"   {s:5s} openings {k['open']:5d}: in bush {100 * k['a_in'] / k['open']:4.1f}%  from bush {100 * k['a_from'] / k['open']:4.1f}%"
                  f"  hidden {100 * k['hidden'] / k['open']:4.1f}% | win from bush {pct(k['w_in'], k['ex_in'])}  open {pct(k['w_out'], k['ex_out'])}"
                  f"  hidden {pct(k['w_hid'], k['ex_hid'])} | defend in bush {pct(k['dw_tin'], k['dx_tin'])} open {pct(k['dw_tout'], k['dx_tout'])}")

    # ---------- B. deaths
    Dd = defaultdict(lambda: defaultdict(int))
    for g in G:
        c = mc(g['bush_frac'])
        for d in g['deaths']:
            if d['cause'] not in ('champion', 'both'):
                continue
            for s in sides_of(g, d['t']):
                for cc in (c, 'all'):
                    k = Dd[(s, cc)]
                    k['n'] += 1
                    k['k_in'] += d['k_in']
                    k['k_in1'] += d['k_in1']
                    k['v_in'] += d['v_in']
                    if d['bag']:
                        k['bag'] += 1
                        k['bag_k_in'] += d['k_in']
    ng = defaultdict(int)
    for g in G:
        for t in (0, 1):
            for s in sides_of(g, t):
                ng[(s, mc(g['bush_frac']))] += 1
                ng[(s, 'all')] += 1
    print('\nB. DEATHS to champions of each side: killer in a bush in r-3..r-1 (and at r-1); victim in a bush; carriers (bag>0) killed from a bush;'
          ' per game = deaths from a bush per team-game')
    for cc in ('all', 'lo', 'mid', 'hi'):
        print(f'  [{cc}]')
        for s in SIDES:
            k = Dd[(s, cc)]
            if not k['n']:
                continue
            print(f"   {s:5s} deaths {k['n']:5d}: killer in bush(3r) {100 * k['k_in'] / k['n']:4.1f}%  (r-1) {100 * k['k_in1'] / k['n']:4.1f}%  victim in bush"
                  f" {100 * k['v_in'] / k['n']:4.1f}% | carriers {k['bag']} killed from bush {pct(k['bag_k_in'], k['bag'])} | from-bush deaths/game"
                  f" {k['k_in'] / max(1, ng[(s, cc)]):.2f} (games {ng[(s, cc)]})")

    # ---------- C. presence
    Pp = defaultdict(lambda: [0] * 8)
    W = defaultdict(lambda: [0, 0])
    for g in G:
        c = mc(g['bush_frac'])
        for b, v in g['pres'].items():
            t = g['team'][b]
            for s in sides_of(g, t):
                for cc in (c, 'all'):
                    p = Pp[(s, cc)]
                    for i in range(8):
                        p[i] += v[i]
                    W[(s, cc)][0] += g['bush_frac'] * v[0]
                    W[(s, cc)][1] += v[0]
    print('\nC. PRESENCE: share of alive body-rounds in a bush (map bush share alive-weighted); bush share of contact rounds (an enemy within 6);'
          '\n   stationary bush rounds within 5 of a camp / altar and with an enemy within 8 per 100 alive rounds; wards in a bush')
    for cc in ('all', 'lo', 'mid', 'hi'):
        print(f'  [{cc}]')
        for s in SIDES:
            p = Pp[(s, cc)]
            if not p[0]:
                continue
            mb = W[(s, cc)][0] / max(1, W[(s, cc)][1])
            print(f"   {s:5s} alive {p[0]:7d}: in bush {100 * p[1] / p[0]:4.1f}% (map {100 * mb:4.1f}%)  contact rounds in bush"
                  f" {100 * p[2] / max(1, p[2] + p[3]):4.1f}% (n={p[2] + p[3]})  holds@obj {100 * p[4] / p[0]:4.2f}  holds@contact {100 * p[5] / p[0]:4.2f}"
                  f"  wards in bush {pct(p[6], p[7])}")

    # ---------- D. retreats
    R = defaultdict(lambda: defaultdict(int))
    for g in G:
        c = mc(g['bush_frac'])
        for r in g['retreats']:
            for s in sides_of(g, r['t']):
                for cc in (c, 'all'):
                    k = R[(s, cc)]
                    k['n'] += 1
                    k[r['kind']] += 1
                    k['d_' + r['kind']] += bool(r['died8'])
    print('\nD. RETREATS (fights stream rows): already in a bush / into a bush within 3 r / open ground; died within 8 r')
    for cc in ('all', 'lo', 'mid', 'hi'):
        print(f'  [{cc}]')
        for s in SIDES:
            k = R[(s, cc)]
            if not k['n']:
                continue
            print(f"   {s:5s} retreats {k['n']:5d}: into bush {100 * k['into'] / k['n']:4.1f}%  was in {100 * k['was_in'] / k['n']:4.1f}% |"
                  f" died8: into {pct(k['d_into'], k['into'])}  was_in {pct(k['d_was_in'], k['was_in'])}  open {pct(k['d_open'], k['open'])}")

    # ---------- E. bush-opened exchanges per champion (top vs us)
    E = defaultdict(lambda: [0, 0, 0])
    for g in G:
        for f in g['fights']:
            s = side(g, f['first'])
            grp = 'TOP' if s in ('TW', 'TL') else s
            E[(grp, f['oc'])][0] += 1
            E[(grp, f['oc'])][1] += f['a_from']
            E[(grp, f['oc'])][2] += f['hidden']
    print('\nE. openers by champion: share of openings from a bush (s-3..s-1) / hidden; TOP = both top-30 sides')
    champs = sorted({c for (_, c) in E}, key=lambda c: -E[('TOP', c)][0])
    for c in champs:
        row = []
        for grp in ('TOP', 'US', 'OPP'):
            n, a, h = E[(grp, c)]
            row.append(f"{grp} {100 * a / n:4.1f}%/{100 * h / n:4.1f}% (n={n})" if n else f'{grp}   -')
        print(f'   {c:12s} ' + '  '.join(row))


if __name__ == '__main__':
    main()


def strat():
    """F. like-with-like: risk difference (Mantel-Haenszel weights) of the opener's exchange win share, from a bush vs open ground,
    within strata of (participant shard gap opener - other: <=-8, -7..-3, -2..2, 3..7, >=8) x (body-count gap -1/0/+1) x map class."""
    G = load()
    from collections import defaultdict as dd
    for feat in ('a_from', 'hidden', 'a_in'):
        print(f'\nF. stratified effect of {feat} on the opener\'s exchange win share (risk difference, MH weights)')
        for grp in ('TOP', 'TW', 'TL', 'US', 'OPP', 'ALL'):
            S = dd(lambda: [0, 0, 0, 0])  # n1, w1, n0, w0
            for g in G:
                c = mc(g['bush_frac'])
                for f in g['fights']:
                    if not f['exch'] or f['win'] is None or not f['sh'] or not f['num']:
                        continue
                    s = side(g, f['first'])
                    if not (grp == 'ALL' or grp == s or (grp == 'TOP' and s in ('TW', 'TL'))):
                        continue
                    a, o = str(f['first']), str(1 - f['first'])
                    gap = f['sh'][a] - f['sh'][o]
                    gb = -2 if gap <= -8 else -1 if gap <= -3 else 0 if gap <= 2 else 1 if gap <= 7 else 2
                    nb = max(-1, min(1, f['num'][a] - f['num'][o]))
                    k = S[(gb, nb, c)]
                    w = f['win'] == f['first']
                    if f[feat]:
                        k[0] += 1; k[1] += w
                    else:
                        k[2] += 1; k[3] += w
            num = den = 0.0
            n1 = n0 = 0
            for k in S.values():
                if k[0] and k[2]:
                    wt = k[0] * k[2] / (k[0] + k[2])
                    num += wt * (k[1] / k[0] - k[3] / k[2])
                    den += wt
                    n1 += k[0]; n0 += k[2]
            print(f'   {grp:4s} {feat}: {100 * num / den if den else float("nan"):+5.1f} points (n bush {n1}, open {n0})')


if __name__ == '__main__':
    strat()
