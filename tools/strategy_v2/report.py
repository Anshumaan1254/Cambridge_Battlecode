#!/usr/bin/env python3
"""Strategy-v2 KPI report: us (team 0) against them (team 1), from analyze.py output and the decoded replays.

usage: python3 -I tools/strategy_v2/report.py ANALYSIS_JSON DMG_DIR [MAPGEO_JSON] > report.md

Prints markdown tables: results, the camp-gem decomposition (alive x camp time x camp damage x conversion), items
(damage points per 1,000 gold, emblem families), per champion, fights (by numbers, by phase, first hit), rounds hit
without hitting back and what the body did instead, death causes, respawn wait of home groups, and the KPI table of
docs/strategy_v2/05_TEST_AND_SHIP_PLAN.md section 3.
"""
import collections
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import bfs, mirror, stat_points  # noqa: E402

DMG_STAT = {'Varg': 's', 'Issac': 's', 'Ryth': 's', 'Vendetta': 's', 'Marcella': 's', 'VesperVale': 's',
            'Ren': 'f', 'Stellar': 'f', 'Cassi': 'f', 'Tavi': 'f', 'Prism': 'f', 'Willow': 'f'}
RANGED = {'Cassi', 'Stellar', 'Prism', 'Tavi', 'Willow', 'VesperVale'}


def pct(a, b):
    return 100.0 * a / b if b else 0.0


def load_dmg(dmg_dir, name):
    return json.load(open(os.path.join(dmg_dir, name + '.json')))


def section_results(A):
    print('## Results\n')
    print('| Match | Rounds | Banked us-them | Body deaths | Kills | Camp gems | Gold earned |')
    print('|---|---|---|---|---|---|---|')
    tot = collections.defaultdict(lambda: [0, 0])
    for m in A:
        t0, t1 = m['team']
        print(f"| {m['name']} | {t0['rounds']} | {t0['banked']}-{t1['banked']}{' (win)' if t0['won'] else ''} | {t0['deaths']}-{t1['deaths']} | {t0['kills']}-{t1['kills']} | {t0['camp_gems']}-{t1['camp_gems']} | {t0['gold']}-{t1['gold']} |")
        for k in ('won', 'banked', 'deaths', 'kills', 'camp_gems', 'gold', 'captures', 'recalls', 'banks'):
            tot[k][0] += t0[k]
            tot[k][1] += t1[k]
    print(f"\nTotal over {len(A)} games: wins {tot['won'][0]}-{tot['won'][1]}, banked {tot['banked'][0]}-{tot['banked'][1]}, "
          f"body deaths {tot['deaths'][0]}-{tot['deaths'][1]}, kills {tot['kills'][0]}-{tot['kills'][1]}, camp gems {tot['camp_gems'][0]}-{tot['camp_gems'][1]}, "
          f"gold {tot['gold'][0]}-{tot['gold'][1]}, captures {tot['captures'][0]}-{tot['captures'][1]}, recalls {tot['recalls'][0]}-{tot['recalls'][1]}, banks {tot['banks'][0]}-{tot['banks'][1]}\n")
    return tot


def section_decomp(A):
    tot = [[0] * 6 for _ in range(2)]
    for m in A:
        for t in m['team']:
            k = t['team']
            tb = [b for b in m['body'] if b['team'] == k]
            n = sum(sum(b['act'].values()) for b in tb)
            alive = n - sum(b['act'].get('dead', 0) for b in tb)
            cr = sum(b['act'].get('camp', 0) for b in tb)
            for i, v in enumerate((alive, n, cr, t['dmg_camp'], t['camp_gems'], t['gold'])):
                tot[k][i] += v
    rows = []
    for k in (0, 1):
        alive, n, cr, dm, g, go = tot[k]
        rows.append((alive / max(1, n), cr / max(1, alive), dm / max(1, cr), 1000 * g / max(1, dm)))
    print('## Camp-gem decomposition\n')
    print('| | Us | Them | Ratio |')
    print('|---|---|---|---|')
    names = ('Alive', 'Camp time (share of alive)', 'Camp damage per camp round', 'Gems per 1,000 camp damage')
    prod = 1.0
    for i, nm in enumerate(names):
        r = rows[0][i] / max(1e-9, rows[1][i])
        prod *= r
        f = (lambda v: f'{100 * v:.1f}%') if i < 2 else (lambda v: f'{v:.1f}')
        print(f'| {nm} | {f(rows[0][i])} | {f(rows[1][i])} | {r:.3f} |')
    print(f'| **Product** | | | **{prod:.3f}** |\n')
    return rows


def section_items(A, dmg_dir):
    acc = [collections.Counter(), collections.Counter()]
    fam = [collections.Counter(), collections.Counter()]
    for m in A:
        d = load_dmg(dmg_dir, m['name'])
        fin = {c[0]: c for c in d['rounds'][-1]['ch']}
        for b in m['body']:
            c = fin[b['body']]
            pts, _, spent = stat_points(c[11])
            ds = DMG_STAT.get(b['champ'], 's')
            acc[b['team']]['spent'] += spent
            acc[b['team']]['dmg'] += pts[ds]
            acc[b['team']]['hp'] += pts['h']
            for k, q in c[11]:
                if k % 2 == 1:
                    st = 'sfh'[(k // 2) % 3]
                    fam[b['team']]['MPDTJHB'[k // 6] + ('-dmg' if st == ds else '-hp' if st == 'h' else '-off')] += q
    print('## Items\n')
    print('| | Us | Them |')
    print('|---|---|---|')
    print(f"| Gold spent on shards and emblems | {acc[0]['spent']} | {acc[1]['spent']} |")
    print(f"| Damage-stat points | {acc[0]['dmg']} | {acc[1]['dmg']} |")
    print(f"| Damage points per 1,000 gold | {1000 * acc[0]['dmg'] / max(1, acc[0]['spent']):.1f} | {1000 * acc[1]['dmg'] / max(1, acc[1]['spent']):.1f} |")
    print(f"| Health points per 1,000 gold | {1000 * acc[0]['hp'] / max(1, acc[0]['spent']):.1f} | {1000 * acc[1]['hp'] / max(1, acc[1]['spent']):.1f} |")
    names = {'M': 'Monster', 'P': 'Power', 'D': 'Durability', 'T': 'Treasure', 'J': 'Jungle', 'H': 'Home', 'B': 'Bruiser'}
    for k in (0, 1):
        fam_s = ', '.join(f"{names[f[0]]}{f[1:]} {v}" for f, v in fam[k].most_common())
        print(f"| Emblems ({'us' if k == 0 else 'them'}) | {fam_s} | |" if k == 0 else f"| Emblems (them) | | {fam_s} |")
    print()
    return acc


def section_champions(A):
    by = collections.defaultdict(lambda: [[], []])
    for m in A:
        types = [set(b['champ'] for b in m['body'] if b['team'] == t) for t in (0, 1)]
        for b in m['body']:
            if b['champ'] in types[0] and b['champ'] in types[1]:
                by[b['champ']][b['team']].append(b)
    print('## Per champion (games where both teams had it)\n')
    print('| Champion | Games | Captures us/them | Gold earned | Deaths | Camp damage per camp round | First emblem (median) |')
    print('|---|---|---|---|---|---|---|')
    for ch, (u, t) in sorted(by.items()):
        def f(L, k):
            return statistics.mean(x[k] for x in L)

        def dps(L):
            return statistics.mean(x['dmg_camp'] / max(1, x['act'].get('camp', 0)) for x in L)

        def fe(L):
            return statistics.median([x['first_emblem'] or 999 for x in L])
        print(f"| {ch} | {len(u)} | {f(u, 'caps'):.1f} / {f(t, 'caps'):.1f} | {f(u, 'gold_earned'):.0f} / {f(t, 'gold_earned'):.0f} | {f(u, 'deaths'):.1f} / {f(t, 'deaths'):.1f} | {dps(u):.0f} / {dps(t):.0f} | {fe(u):.0f} / {fe(t):.0f} |")
    print()


def section_fights(A):
    E = [e for m in A for e in m['engagements'] if e['hits'] >= 4]
    print(f'## Fights ({len(E)} with 4+ champion hits)\n')
    if not E:
        return 0.0
    d0 = sum(e['dmg0'] for e in E)
    d1 = sum(e['dmg1'] for e in E)
    print(f"Damage dealt us/them: {d0} / {d1} (ratio {d0 / max(1, d1):.2f}); deaths in fights {sum(e['deaths0'] for e in E)} / {sum(e['deaths1'] for e in E)}\n")
    print('| Group | Fights | Deaths us/them | Damage us/them |')
    print('|---|---|---|---|')
    groups = [('they had more bodies', [e for e in E if e['n1'] > e['n0']]), ('equal', [e for e in E if e['n1'] == e['n0']]),
              ('we had more bodies', [e for e in E if e['n1'] < e['n0']]), ('they hit first', [e for e in E if e['first'] == 1]),
              ('we hit first', [e for e in E if e['first'] == 0])]
    for lo, hi in ((0, 100), (100, 200), (200, 350), (350, 99999)):
        groups.append((f'rounds {lo}-{hi if hi < 99999 else "end"}', [e for e in E if lo <= e['r0'] < hi]))
    for nm, L in groups:
        print(f"| {nm} | {len(L)} | {sum(e['deaths0'] for e in L)} / {sum(e['deaths1'] for e in L)} | {sum(e['dmg0'] for e in L)} / {sum(e['dmg1'] for e in L)} |")
    print()
    return d0 / max(1, d1)


def section_hitback(A, dmg_dir):
    res = [collections.Counter(), collections.Counter()]
    moved = [collections.Counter(), collections.Counter()]
    did = [collections.Counter(), collections.Counter()]
    for m in A:
        d = load_dmg(dmg_dir, m['name'])
        bt = {b['index']: (b['team'], b['type']) for b in d['meta']['bodies']}
        st = {(rr['r'], c[0]): c for rr in d['rounds'] for c in rr['ch']}
        ev = collections.defaultdict(list)
        for e in d['events']:
            if 'who' in e:
                ev[(e['r'], e['who'])].append(e['k'])
        taken = collections.defaultdict(float)
        dealt = collections.defaultdict(float)
        campdealt = collections.defaultdict(float)
        for x in d['dmg']:
            r, kind, ak, ai, slot, tk, ti, dh = x[:8]
            if dh >= 0:
                continue
            if ak == 'c' and tk == 'c' and ai in bt and ti in bt and bt[ai][0] != bt[ti][0]:
                taken[(r, ti)] += -dh
                dealt[(r, ai)] += -dh
            if ak == 'c' and tk == 'm' and ai in bt:
                campdealt[(r, ai)] += -dh
        for (r, b) in taken:
            tm, ty = bt[b]
            res[tm]['hit'] += 1
            if dealt.get((r, b), 0) > 0:
                continue
            res[tm]['no_reply'] += 1
            s0, s1 = st.get((r - 1, b)), st.get((r, b))
            ks = ev.get((r, b), [])
            if s1 and not s1[7]:
                did[tm]['died that round'] += 1
            elif 'Recall' in ks or 'Submit gems' in ks:
                did[tm]['started a recall or bank'] += 1
            elif campdealt.get((r, b), 0) > 0:
                did[tm]['hit a camp instead'] += 1
            elif s0 and s1 and (s0[3], s0[4]) != (s1[3], s1[4]):
                did[tm]['moved, above 50% health' if s0[5] >= 0.5 * s0[6] else 'moved, below 50% health'] += 1
            elif s0 and s1 and not [k for k in ks if k not in ('Set priority', 'Place ward')]:
                did[tm]['no action (stunned, channel or waiting)'] += 1
            else:
                did[tm]['other'] += 1
            if not (s0 and s1 and s0[7] and s1[7]) or (s0[3], s0[4]) == (s1[3], s1[4]) or campdealt.get((r, b), 0) > 0:
                continue
            rng = 3 if ty in RANGED else 1
            foes = [o for o, (t2, _) in bt.items() if t2 != tm and (r - 1, o) in st and st[(r - 1, o)][7]]

            def dmin(p):
                return min((max(abs(st[(r - 1, o)][3] - p[0]), abs(st[(r - 1, o)][4] - p[1])) for o in foes), default=99)
            d_before = dmin((s0[3], s0[4]))
            key = 'enemy in attack range' if d_before <= rng else ('enemy within 4' if d_before <= 4 else 'nothing in reach')
            key += ', moved away' if dmin((s1[3], s1[4])) > d_before else ', moved toward'
            moved[tm][key] += 1
    print('## Rounds hit without hitting back\n')
    print('| | Rounds hit | Hit nobody back | Share | Of those: walked |')
    print('|---|---|---|---|---|')
    for k in (0, 1):
        print(f"| {'Us' if k == 0 else 'Them'} | {res[k]['hit']} | {res[k]['no_reply']} | {pct(res[k]['no_reply'], res[k]['hit']):.0f}% | {sum(moved[k].values())} |")
    print('\nWhere our walking bodies were, before the step:\n')
    for key, v in moved[0].most_common():
        print(f'- {key}: {v} (them: {moved[1][key]})')
    print('\nWhat the body did in its no-hit-back rounds (us / them):\n')
    for key in sorted(set(did[0]) | set(did[1]), key=lambda k: -did[0][k]):
        print(f'- {key}: {did[0][key]} / {did[1][key]}')
    print()
    return res[0]['no_reply'] / max(1, res[0]['hit']), res[1]['no_reply'] / max(1, res[1]['hit'])


def section_deaths(A, dmg_dir):
    tot = [collections.Counter(), collections.Counter()]
    killers = [collections.Counter(), collections.Counter()]
    bags = [0, 0]
    n = [0, 0]
    for m in A:
        d = load_dmg(dmg_dir, m['name'])
        bt = {b['index']: (b['team'], b['type']) for b in d['meta']['bodies']}
        st = {(rr['r'], c[0]): c for rr in d['rounds'] for c in rr['ch']}
        by_r = collections.defaultdict(list)
        for x in d['dmg']:
            by_r[x[0]].append(x)
        seen = set()
        for e in (e for e in d['events'] if e['k'] == 'Death'):
            v, t, r = e['who'], e['team'], e['r']
            if bt[v][1] in ('Cassi', 'Issac'):
                if (r, t) in seen:
                    continue
                seen.add((r, t))
            n[t] += 1
            C = tot[t]
            s4 = st.get((r - 4, v))
            if s4 and s4[7]:
                C['burst (above 60% health 4 rounds before)'] += s4[5] / max(1, s4[6]) >= 0.6
            killer = e.get('by')
            kt = bt[killer][1] if isinstance(killer, int) and killer in bt else 'camp'
            C['killed by a camp' if kt == 'camp' else 'killed by ranged' if kt in RANGED else 'killed by melee'] += 1
            killers[t][kt] += 1
            bags[t] += e.get('bag', 0) + (sum(o.get('bag', 0) for o in d['events'] if o['k'] == 'Death' and o['r'] == r and o['team'] == t and o['who'] != v and {bt[o['who']][1], bt[v][1]} == {'Cassi', 'Issac'}))
            if s4 and s4[7] and s4[5] / max(1, s4[6]) < 0.35:
                near = any(bt[o][0] != t and (r - 4, o) in st and st[(r - 4, o)][7] and max(abs(st[(r - 4, o)][3] - s4[3]), abs(st[(r - 4, o)][4] - s4[4])) <= 6 for o in bt)
                C['failed escape (below 35% health, enemy within 6, 4 rounds before)'] += near
            campd = sum(-x[7] for rr in range(r - 5, r + 1) for x in by_r[rr] if x[5] == 'c' and x[6] == v and x[2] == 'm' and x[7] < 0)
            C['60+ camp damage taken in the last 5 rounds'] += campd >= 60
            for rr in range(r - 5, r + 1):
                hits = collections.defaultdict(set)
                for x in by_r[rr]:
                    if x[2] == 'c' and x[3] in bt and bt[x[3]][1] == 'Varg' and bt[x[3]][0] != t and x[5] == 'c' and x[6] in bt and bt[x[6]][0] == t and x[7] < 0 and x[1] == 'Attack':
                        hits[x[3]].add(x[6])
                if any(len(s) >= 2 and v in s for s in hits.values()):
                    C['Varg splash on victim + ally (last 5 rounds)'] += 1
                    break
    print('## Death incidents (a Cassi & Issac double death counted once)\n')
    print(f'Us {n[0]}, them {n[1]}.\n')
    print('| Cause | Us | Them |')
    print('|---|---|---|')
    keys = sorted(set(tot[0]) | set(tot[1]))
    for k in keys:
        print(f'| {k} | {pct(tot[0][k], n[0]):.0f}% | {pct(tot[1][k], n[1]):.0f}% |')
    print(f'| bag lost at death (gems, total) | {bags[0]} | {bags[1]} |')
    print('\nOur killers: ' + ', '.join(f'{k} {v}' for k, v in killers[0].most_common()) + '. Theirs: ' + ', '.join(f'{k} {v}' for k, v in killers[1].most_common()) + '.\n')


def section_kpis(A, tot, decomp, acc, ratio, nr):
    g = len(A)
    print('## KPIs (targets: docs/strategy_v2/05_TEST_AND_SHIP_PLAN.md section 3)\n')
    print('| KPI | Us | Them |')
    print('|---|---|---|')
    print(f"| Wins | {tot['won'][0]}/{g} | {tot['won'][1]}/{g} |")
    print(f"| Body deaths per game | {tot['deaths'][0] / g:.1f} | {tot['deaths'][1] / g:.1f} |")
    print(f"| Share of hit rounds with no hit back | {nr[0]:.2f} | {nr[1]:.2f} |")
    print(f"| Fight damage ratio (ours / theirs) | {ratio:.2f} | |")
    print(f"| Damage points per 1,000 gold | {1000 * acc[0]['dmg'] / max(1, acc[0]['spent']):.1f} | {1000 * acc[1]['dmg'] / max(1, acc[1]['spent']):.1f} |")
    print(f"| Gold earned per game | {tot['gold'][0] / g:.0f} | {tot['gold'][1] / g:.0f} |")
    print(f"| Time alive | {100 * decomp[0][0]:.1f}% | {100 * decomp[1][0]:.1f}% |")
    print(f"| Time on camps (share of alive) | {100 * decomp[0][1]:.1f}% | {100 * decomp[1][1]:.1f}% |")
    print(f"| Camp damage per camp round | {decomp[0][2]:.1f} | {decomp[1][2]:.1f} |")
    print(f"| Gem captures per game | {tot['captures'][0] / g:.1f} | {tot['captures'][1] / g:.1f} |")
    print()


def section_match_decomp(A):
    print('## Per match: alive, camp rounds, camp damage per camp round, gems per 1,000 camp damage (us / them)\n')
    print('| Match | Alive % | Camp rounds | Camp damage per camp round | Gems per 1k camp damage |')
    print('|---|---|---|---|---|')
    for m in A:
        row = []
        for t in m['team']:
            tb = [b for b in m['body'] if b['team'] == t['team']]
            n = sum(sum(b['act'].values()) for b in tb)
            alive = n - sum(b['act'].get('dead', 0) for b in tb)
            cr = sum(b['act'].get('camp', 0) for b in tb)
            row.append((100 * alive / max(1, n), cr, t['dmg_camp'] / max(1, cr), 1000 * t['camp_gems'] / max(1, t['dmg_camp'])))
        print(f"| {m['name']} | {row[0][0]:.0f} / {row[1][0]:.0f} | {row[0][1]} / {row[1][1]} | {row[0][2]:.0f} / {row[1][2]:.0f} | {row[0][3]:.1f} / {row[1][3]:.1f} |")
    print()
    labs = ['dead', 'recall', 'tribute', 'fight', 'camp', 'capture', 'spawn', 'walk', 'idle']
    acc = collections.defaultdict(lambda: [collections.Counter(), collections.Counter()])
    for m in A:
        for b in m['body']:
            acc['all'][b['team']].update(b['act'])
            acc[b['champ']][b['team']].update(b['act'])
    print('## How bodies spend their time (% of body-rounds)\n')
    print('| Who | ' + ' | '.join(labs) + ' |')
    print('|---' * (len(labs) + 1) + '|')
    for ch in ['all'] + sorted(k for k in acc if k != 'all'):
        for t in (0, 1):
            c = acc[ch][t]
            nn = sum(c.values())
            if nn:
                print(f"| {'us' if t == 0 else 'them'}, {ch} | " + ' | '.join(f'{100 * c[l] / nn:.1f}' for l in labs) + ' |')
    print()


def section_farming(A):
    print('## Gems captured per 100-round window (us / them)\n')
    print('| Match | r0-100 | r100-200 | r200-300 | r300-400 |')
    print('|---|---|---|---|---|')
    for m in A:
        cells = []
        for a, b in ((0, 100), (100, 200), (200, 300), (300, 400)):
            c0 = sum(x['gems'] for x in m['captures'] if x['team'] == 0 and a < x['r'] <= b)
            c1 = sum(x['gems'] for x in m['captures'] if x['team'] == 1 and a < x['r'] <= b)
            cells.append(f'{c0} / {c1}')
        print(f"| {m['name']} | " + ' | '.join(cells) + ' |')
    print()
    tot = [collections.Counter(), collections.Counter()]
    durs = [collections.defaultdict(list), collections.defaultdict(list)]
    for m in A:
        for k in m['group_kills']:
            tot[k['killer']][k['types']] += 1
            durs[k['killer']][k['types']].append(k['dur'])
    print('## Camp-group kills: count and median rounds from first hit to kill (us / them)\n')
    print('| Group | Kills | Rounds |')
    print('|---|---|---|')
    for k in sorted(set(tot[0]) | set(tot[1]), key=lambda k: -(tot[0][k] + tot[1][k]))[:14]:
        d0 = statistics.median(durs[0][k]) if durs[0][k] else '-'
        d1 = statistics.median(durs[1][k]) if durs[1][k] else '-'
        print(f'| {k} | {tot[0][k]} / {tot[1][k]} | {d0} / {d1} |')
    print()
    C = [c for m in A for c in m['captures']]
    R = [r for m in A for r in m['recalls']]
    B = [b for m in A for b in m['banks']]
    print('## Captures, recalls, banks (us / them)\n')
    print('| | Us | Them |')
    print('|---|---|---|')
    side = [collections.Counter(c['side'] for c in C if c['team'] == t) for t in (0, 1)]
    print(f"| Gem captures (home / neutral / enemy side) | {sum(side[0].values())} ({side[0]['own']} / {side[0]['neutral']} / {side[0]['enemy']}) | {sum(side[1].values())} ({side[1]['own']} / {side[1]['neutral']} / {side[1]['enemy']}) |")
    rr = [[r for r in R if r['team'] == t] for t in (0, 1)]
    print(f"| Recalls (median health at start) | {len(rr[0])} ({statistics.median([r['hp_frac'] for r in rr[0]]) if rr[0] else 0:.2f}) | {len(rr[1])} ({statistics.median([r['hp_frac'] for r in rr[1]]) if rr[1] else 0:.2f}) |")
    print(f"| Recalls overlapping a capture | {sum(r['cap_overlap'] for r in rr[0])} | {sum(r['cap_overlap'] for r in rr[1])} |")
    bb = [[b for b in B if b['team'] == t] for t in (0, 1)]
    print(f"| Banks (mean gems) | {len(bb[0])} ({statistics.mean([b['gems'] for b in bb[0]]) if bb[0] else 0:.1f}) | {len(bb[1])} ({statistics.mean([b['gems'] for b in bb[1]]) if bb[1] else 0:.1f}) |")
    print(f"| Banks at neutral altars | {sum(1 for b in bb[0] if b['side'] == 'neutral')} | {sum(1 for b in bb[1] if b['side'] == 'neutral')} |")
    split = [0, 0]
    for m in A:
        caps = m['captures']
        for i, x in enumerate(caps):
            for y in caps[i + 1:]:
                if x['team'] == y['team'] and x['r'] == y['r'] and {x['champ'], y['champ']} != {'Cassi', 'Issac'}:
                    split[x['team']] += 1
    print(f"| Split rewards (two of a team's bodies capture in the same round, not the pair) | {split[0]} | {split[1]} |")
    print()


def section_respawn_wait(A, dmg_dir, geo):
    """Rounds a home group sits untouched after it respawns (home = clearly nearer to that team's spawn)."""
    waits = [[], []]
    for m in A:
        g = geo.get(m['name'])
        if not g:
            continue
        d = load_dmg(dmg_dir, m['name'])
        w, h, sym = g['w'], g['h'], g['sym']
        grid = [list(row.ljust(w, '.')) for row in g['grid']]
        x0, y0, x1, y1 = g['spawnA']
        sp = [set(), set()]
        for y in range(y0, y1):
            for x in range(x0, x1):
                sp[0].add((x, y))
                sp[1].add(mirror(sym, w, h, x, y))
        for t in (0, 1):
            for (x, y) in sp[t]:
                grid[y][x] = '.'
        dist = [bfs(grid, w, h, sp[0]), bfs(grid, w, h, sp[1])]
        camps = d['meta']['camps']
        idx = {c['index']: i for i, c in enumerate(camps)}
        pos2 = {(c['x'], c['y']): c for c in camps}
        seen = set()
        for c in camps:
            if (c['x'], c['y']) in seen:
                continue
            stack, mem = [c], []
            seen.add((c['x'], c['y']))
            while stack:
                cc = stack.pop()
                mem.append(cc)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    o = pos2.get((cc['x'] + dx, cc['y'] + dy))
                    if o and (o['x'], o['y']) not in seen:
                        seen.add((o['x'], o['y']))
                        stack.append(o)
            d0, d1 = dist[0][mem[0]['y']][mem[0]['x']], dist[1][mem[0]['y']][mem[0]['x']]
            owner = 0 if d0 < d1 - 3 else 1 if d1 < d0 - 3 else -1
            if owner < 0:
                continue
            maxhp = sum(x['hp'] for x in mem)
            full_since, first = None, True
            for rr in d['rounds']:
                tot = sum(max(0, rr['campHp'][idx[x['index']]]) for x in mem)
                if tot <= 0:
                    full_since = None
                    continue
                if tot >= maxhp - 0.5:
                    if full_since is None:
                        full_since = rr['r']
                elif full_since is not None:
                    if not first:
                        waits[owner].append(rr['r'] - full_since)
                    first = False
                    full_since = None
    print('## Respawn wait: rounds a home group sits untouched after it respawns\n')
    for t in (0, 1):
        L = waits[t]
        if L:
            print(f"- {'us' if t == 0 else 'them'}: {len(L)} cycles, median {statistics.median(L)}, mean {statistics.mean(L):.1f}")
    print()


def main():
    A = json.load(open(sys.argv[1]))
    dmg_dir = sys.argv[2]
    print(f'# Strategy-v2 report ({len(A)} games, us = team 0)\n')
    tot = section_results(A)
    decomp = section_decomp(A)
    section_match_decomp(A)
    acc = section_items(A, dmg_dir)
    section_champions(A)
    section_farming(A)
    if len(sys.argv) > 3:
        section_respawn_wait(A, dmg_dir, json.load(open(sys.argv[3])))
    ratio = section_fights(A)
    nr = section_hitback(A, dmg_dir)
    section_deaths(A, dmg_dir)
    section_kpis(A, tot, decomp, acc, ratio, nr)


if __name__ == '__main__':
    main()
