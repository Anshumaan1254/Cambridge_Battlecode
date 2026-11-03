#!/usr/bin/env python3
"""Emblem / item choices by champion, phase and match state: top-30 vs us (economy/rows_*.jsonl, builds = per body item deltas).
   nice -n 19 python3 -I emblem.py > emblem_tables.txt
State at an emblem completion round R: gem lead = own captured gems minus the opponent's (phases, cumulative to the phase before R;
first phase: gems150 at R>150), ahead if lead >= +20, behind if <= -20. Enemy roster from the opponent row's draft.
Family groups: ECON = Prospect, Treasure, Capture, Monster, Tribute; DEF = Durab, Jungle; FIGHT = Power, Bruiser, Skirmish, Greed, Hunter,
Collect; UTIL = Home."""
import json
from collections import defaultdict, Counter

ECO = '/home/claude/cambridge_battlecode/experiments/top30_nov3/economy'
FAM = ['Monster', 'Power', 'Durab', 'Treasure', 'Jungle', 'Home', 'Bruiser', 'Tribute', 'Capture', 'Prospect', 'Hunter', 'Skirmish', 'Greed', 'Collect']
ST = ['str', 'foc', 'hp']
GRP = {'Prospect': 'ECON', 'Treasure': 'ECON', 'Capture': 'ECON', 'Monster': 'ECON', 'Tribute': 'ECON', 'Durab': 'DEF', 'Jungle': 'DEF',
       'Power': 'FIGHT', 'Bruiser': 'FIGHT', 'Skirmish': 'FIGHT', 'Greed': 'FIGHT', 'Hunter': 'FIGHT', 'Collect': 'FIGHT', 'Home': 'UTIL'}
RANGED = {'VesperVale', 'Cassi', 'Stellar', 'Prism', 'Willow', 'Tavi'}
MAIN = ['Marcella', 'HeartOfRuin', 'VesperVale', 'Vendetta', 'Ryth']


def load(n):
    return [json.loads(l) for l in open(f'{ECO}/rows_{n}.jsonl') if '"error"' not in l[:40]]


def ph(r):
    return 'p1<=200' if r <= 200 else 'p2<=400' if r <= 400 else 'p3<=700' if r <= 700 else 'p4>700'


def cum_gems(row, R):
    if R <= 150:
        return 0
    g = 0
    for p in row['phases']:
        if p and p['z'] < R:
            g += p['gems']
    return g


def pct(c, n):
    return f'{100 * c / n:4.0f}%' if n else '   -'


def main():
    T = load('top30')
    O = load('ours')
    by = defaultdict(dict)
    for r in T + O:
        by[r['mid']][r['team']] = r
    US = [r for r in O if r['me'] and r['ver'] in ('v84', 'v85', 'v86', 'v87', 'v88')]
    OPP = [r for r in O if not r['me'] and r['ver'] in ('v84', 'v85', 'v86', 'v87', 'v88')]
    sets = (('TW', [r for r in T if r['res'] == 'W']), ('TL', [r for r in T if r['res'] == 'L']), ('US', US), ('OPP', OPP))

    def emblems(r):
        """(R, body, champ, fam, stat, k) for every emblem, k = its order for that body"""
        out = []
        for b, bd in r['builds'].items():
            k = 0
            for (rr, f, s, e, q) in bd['seq']:
                if e:
                    for _ in range(q):
                        out.append((rr, b, bd['champ'], FAM[f], ST[s], k))
                        k += 1
        return out

    # ---- 1. per champion x phase: family group shares of emblems, stat shares of shards
    print('1. EMBLEMS by champion and phase: share by family group ECON/DEF/FIGHT/UTIL, top families; shard stat split (all shards bought in the phase)')
    for c in MAIN:
        print(f'\n  {c}')
        for lab, rows in sets:
            line = []
            for P in ('p1<=200', 'p2<=400', 'p3<=700', 'p4>700'):
                cnt = Counter()
                fam = Counter()
                stc = Counter()
                nb = 0
                for r in rows:
                    for b, bd in r['builds'].items():
                        if bd['champ'] != c:
                            continue
                        for (rr, f, s, e, q) in bd['seq']:
                            if ph(rr) != P:
                                continue
                            w = q * (5 if e else 1)
                            stc[ST[s]] += w
                            if e:
                                cnt[GRP[FAM[f]]] += q
                                fam[FAM[f]] += q
                n = sum(cnt.values())
                ns = sum(stc.values())
                nbod = sum(1 for r in rows for bd in r['builds'].values() if bd['champ'] == c)
                line.append(f"{P}: {n / max(1, nbod):.1f}/body E{pct(cnt['ECON'], n)} D{pct(cnt['DEF'], n)} F{pct(cnt['FIGHT'], n)} "
                            f"[{','.join(k[:4] for k, _ in fam.most_common(2))}] foc{pct(stc['foc'], ns)} str{pct(stc['str'], ns)} hp{pct(stc['hp'], ns)}")
            print(f'   {lab:3s} ' + ' | '.join(line[:2]))
            print(f'       ' + ' | '.join(line[2:]))

    # ---- 2. state dependence (top + ours): family group of the 2nd+ emblems by gem lead at completion; enemy roster; map class
    print('\n2. STATE: family group of emblems k>=1 (after the first) by gem lead at completion (+-20), all champions')
    for lab, rows in sets:
        S = defaultdict(Counter)
        for r in rows:
            opp = by[r['mid']].get(1 - r['team'])
            if not opp:
                continue
            for (R, b, c, f, s, k) in emblems(r):
                if k < 1:
                    continue
                lead = cum_gems(r, R) - cum_gems(opp, R)
                st = 'ahead' if lead >= 20 else 'behind' if lead <= -20 else 'even'
                S[st][GRP[f]] += 1
                S[st]['n'] += 1
        print(f'   {lab:3s} ' + ' | '.join(f"{st} n={S[st]['n']}: E{pct(S[st]['ECON'], S[st]['n'])} D{pct(S[st]['DEF'], S[st]['n'])} F{pct(S[st]['FIGHT'], S[st]['n'])}"
                                         for st in ('ahead', 'even', 'behind')))
    print('\n   enemy roster: DEF (Durability / Jungle) share of emblems k>=1 when the enemy drafts Marcella / >=2 ranged / neither;'
          ' Durability alone in ()')
    for lab, rows in sets:
        S = defaultdict(Counter)
        for r in rows:
            opp = by[r['mid']].get(1 - r['team'])
            if not opp:
                continue
            ed = opp['draft']
            key = 'Marcella' if 'Marcella' in ed else 'ranged2' if sum(1 for x in ed if x in RANGED) >= 2 else 'other'
            for (R, b, c, f, s, k) in emblems(r):
                if k < 1:
                    continue
                S[key]['n'] += 1
                S[key][GRP[f]] += 1
                S[key]['dur'] += f == 'Durab'
        print(f'   {lab:3s} ' + ' | '.join(f"{k} n={S[k]['n']}: DEF {pct(S[k]['DEF'], S[k]['n'])} ({pct(S[k]['dur'], S[k]['n'])})" for k in ('Marcella', 'ranged2', 'other')))
    print('\n   map class: ECON share of all emblems and first-emblem families, by gems per champion on the map (scarce < 50 <= rich)')
    for lab, rows in sets:
        S = defaultdict(Counter)
        F1 = defaultdict(Counter)
        for r in rows:
            gpc = r['mapclass']['gems_total'] / max(1, 2 * r['nbody'])
            key = 'scarce' if gpc < 50 else 'rich'
            for (R, b, c, f, s, k) in emblems(r):
                S[key]['n'] += 1
                S[key][GRP[f]] += 1
                if k == 0:
                    F1[key][f] += 1
        print(f'   {lab:3s} ' + ' | '.join(f"{k} n={S[k]['n']}: ECON {pct(S[k]['ECON'], S[k]['n'])} FIGHT {pct(S[k]['FIGHT'], S[k]['n'])} 1st: "
                                         + ','.join(f'{a[:5]} {pct(v, sum(F1[k].values()))}' for a, v in F1[k].most_common(3)) for k in ('scarce', 'rich')))

    # ---- 3. shop timing and gold
    print('\n3. SHOPS: trips by kind (respawn / recall / walk / at-spawn / start), shards per trip, unspent gold at r300 / r600 by gem lead at r300')
    for lab, rows in sets:
        K = Counter()
        for r in rows:
            for (rr, b, cls, g) in r['shop_list']:
                K[cls] += 1
        n = sum(K.values())
        G = defaultdict(list)
        for r in rows:
            opp = by[r['mid']].get(1 - r['team'])
            if not opp:
                continue
            lead = r['gems300'] - opp['gems300']
            st = 'ahead' if lead >= 20 else 'behind' if lead <= -20 else 'even'
            for cr in ('300', '600'):
                ck = r['checks'].get(cr)
                if ck:
                    G[(st, cr)].append(ck['gold'] / max(1, r['nbody']))
        mean = lambda xs: sum(xs) / len(xs) if xs else float('nan')
        print(f'   {lab:3s} trips/game {n / max(1, len(rows)):.1f}: ' + ', '.join(f'{k} {pct(v, n)}' for k, v in K.most_common()) +
              ' | gold/body r300 ' + ' '.join(f"{st} {mean(G[(st, '300')]):.0f}" for st in ('ahead', 'even', 'behind')) +
              ' ; r600 ' + ' '.join(f"{st} {mean(G[(st, '600')]):.0f}" for st in ('ahead', 'even', 'behind')))

    # ---- 4. what correlates with winning (top only, within the top-30): carry first emblem ECON vs other; Marcella focus share
    print('\n4. OUTCOMES (within the top-30 and within ours): result and gold income r151-400 / 401-800 by choice')

    def income(r, i):
        return r['phases'][i]['gold_income'] if len(r['phases']) > i and r['phases'][i] else None

    for lab, rows in (('TOP', T), ('US', US), ('OPP', OPP)):
        # Marcella stat
        A = defaultdict(lambda: [0, 0, [], []])
        for r in rows:
            for b, bd in r['builds'].items():
                if bd['champ'] != 'Marcella':
                    continue
                stc = Counter()
                n = 0
                for (rr, f, s, e, q) in bd['seq']:
                    if n >= 20:
                        break
                    w = q * (5 if e else 1)
                    stc[ST[s]] += w
                    n += w
                if not n:
                    continue
                key = 'Marc foc-major' if stc['foc'] > n / 2 else 'Marc str/hp'
                A[key][0] += 1
                A[key][1] += r['res'] == 'W'
                if income(r, 1) is not None:
                    A[key][2].append(income(r, 1))
                if income(r, 2) is not None:
                    A[key][3].append(income(r, 2))
        # first emblem of each body: ECON vs DEF vs FIGHT
        for r in rows:
            fe = Counter()
            for b, bd in r['builds'].items():
                e = [(rr, f) for (rr, f, s, ee, q) in bd['seq'] if ee]
                if e:
                    fe[GRP[FAM[e[0][1]]]] += 1
            n = sum(fe.values())
            if not n:
                continue
            key = 'team 1st-emblems ECON>=60%' if fe['ECON'] >= 0.6 * n else 'team 1st-emblems ECON<60%'
            A[key][0] += 1
            A[key][1] += r['res'] == 'W'
            if income(r, 1) is not None:
                A[key][2].append(income(r, 1))
            if income(r, 2) is not None:
                A[key][3].append(income(r, 2))
        mean = lambda xs: sum(xs) / len(xs) if xs else float('nan')
        for k, v in sorted(A.items()):
            print(f'   {lab:3s} {k:28s} n={v[0]:4d} win {pct(v[1], v[0])}  gold income r151-400 {mean(v[2]):5.0f}  r401-800 {mean(v[3]):5.0f}')


if __name__ == '__main__':
    main()
