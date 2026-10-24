"""verify_items: item claims (C1, C3 builds, C7 items) from vx_all.jsonl (+ vd_all.jsonl for deaths).
   python tools/top2/verify_items/vagg_items.py"""
import collections, statistics as stt, sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
from vlib import groups, vx, vd, code, BASE, pct

G = groups(); X = vx(); D = vd()
ORDER = ['pbg', 'pbg14', 'pbg07', 'nyx', 'ifish', 'pantheon', 'coo', 'cm']


def emb_order(b):
    """Emblem completions in order; within one shop step, an emblem whose shards were already in progress comes first."""
    by_r = collections.defaultdict(list)
    for r, i, dq in b['buys']:
        by_r[r].append((i, dq))
    seq = []
    for r in sorted(by_r):
        ch = by_r[r]
        done = [i for i, dq in ch if i % 2 and dq > 0 for _ in range(dq)]
        if not done:
            continue
        shard_d = {i: dq for i, dq in ch if i % 2 == 0}
        # in progress: the shard count of the same type dropped in this step
        done.sort(key=lambda i: (0 if shard_d.get(i - 1, 0) < 0 else 1, i))
        seq += [code(i) for i in done]
    return seq


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float('nan')


def str_val(b, c):
    base = BASE[b['type']]
    return base[2] + base[3] * c['pts'][0]


rows = []
print('=== C1/C7: stat points share (final items and r600), max HP per body, deaths per body per 1000 alive rounds')
print(f"{'grp':9s} {'n':>4s} {'side':4s} {'final str/foc/hp':>18s} {'r600 str/foc/hp':>18s} {'maxHp r300':>10s} {'r600':>6s} {'r1000':>6s} {'deaths/1000 alive':>8s}")
for g in ORDER:
    games = [x for x in G[g] if x['base'] in X]
    for side in ('S', 'O'):
        ptsF = [0, 0, 0]; pts6 = [0, 0, 0]; hp = {300: [], 600: [], 1000: []}
        dth = 0; alive = 0
        for x in games:
            t = x['S'] if side == 'S' else 1 - x['S']
            v = X[x['base']]
            for b in v['bodies']:
                if b['team'] != t:
                    continue
                f = b['cp']['final']['pts']
                for s in range(3): ptsF[s] += f[s]
                c6 = b['cp'].get('600')
                if c6:
                    for s in range(3): pts6[s] += c6['pts'][s]
                for cp in hp:
                    c = b['cp'].get(str(cp))
                    if c: hp[cp].append(c['maxHp'])
            dd = D.get(x['base'])
            if dd:
                tm = {bb[0]: bb[1] for bb in dd['bodies']}
                for bi, a in dd['alive'].items():
                    if tm[int(bi)] == t: alive += a
                dth += sum(1 for de in dd['deaths'] if tm[de[1]] == t)
        sF = sum(ptsF) or 1; s6 = sum(pts6) or 1
        print(f"{g:9s} {len(games):4d} {side:4s} {'/'.join(f'{100*p/sF:.0f}' for p in ptsF):>18s} {'/'.join(f'{100*p/s6:.0f}' for p in pts6):>18s} "
              f"{mean(hp[300]):10.0f} {mean(hp[600]):6.0f} {mean(hp[1000]):6.0f} {1000*dth/max(1,alive):8.2f}")

print('\n=== Vesper (study team Vesper vs opponents\' Vesper in the same games)')
print(f"{'grp':9s} {'side':4s} {'bodies':>6s} {'maxHp300':>8s} {'600':>6s} {'1000':>6s} {'str600':>6s} {'bonusHP/100g r600 (ratio of sums)':>12s} {'mean of ratios':>8s} {'deaths/game':>11s} {'champ dmg/game':>14s}")
for g in ORDER:
    games = [x for x in G[g] if x['base'] in X]
    for side in ('S', 'O'):
        h3, h6, h10, s6, bh, sp, rat, nb, nd, cd = [], [], [], [], 0, 0, [], 0, 0, []
        for x in games:
            t = x['S'] if side == 'S' else 1 - x['S']
            v = X[x['base']]; dd = D.get(x['base'])
            for b in v['bodies']:
                if b['team'] != t or b['type'] != 'VesperVale':
                    continue
                nb += 1
                c3, c6, c10 = b['cp'].get('300'), b['cp'].get('600'), b['cp'].get('1000')
                if c3: h3.append(c3['maxHp'])
                if c6:
                    h6.append(c6['maxHp']); s6.append(str_val(b, c6))
                    if c6['spent'] > 0:
                        bh += c6['maxHp'] - 1000; sp += c6['spent']; rat.append(100 * (c6['maxHp'] - 1000) / c6['spent'])
                if c10: h10.append(c10['maxHp'])
                if dd:
                    nd += sum(1 for de in dd['deaths'] if de[1] == b['index'])
                    cd.append(dd['cdmg_champ'][str(b['index'])])
        print(f"{g:9s} {side:4s} {nb:6d} {mean(h3):8.0f} {mean(h6):6.0f} {mean(h10):6.0f} {mean(s6):6.0f} {100*bh/max(1,sp):12.0f} {mean(rat):8.0f} {nd/max(1,nb):11.2f} {mean(cd):14.0f}")

print('\n=== Team max-HP ratio at r600 (S per-body mean / O per-body mean) and S win rate')
for g in ORDER:
    buck = collections.defaultdict(lambda: [0, 0]); ratios = []
    for x in G[g]:
        v = X.get(x['base'])
        if not v:
            continue
        hs = [b['cp']['600']['maxHp'] for b in v['bodies'] if b['team'] == x['S'] and '600' in b['cp']]
        ho = [b['cp']['600']['maxHp'] for b in v['bodies'] if b['team'] != x['S'] and '600' in b['cp']]
        if not hs or not ho:
            buck['ended<600'][0] += 1; buck['ended<600'][1] += x['win']; continue
        r = mean(hs) / mean(ho); ratios.append(r)
        k = '>=1.1' if r >= 1.1 else '<0.9' if r < 0.9 else '0.9-1.1'
        buck[k][0] += 1; buck[k][1] += x['win']
    print(f"{g:9s} median {stt.median(ratios):.2f} | " + ' | '.join(f"{k}: {pct(buck[k][1], buck[k][0])} ({buck[k][0]})" for k in ('>=1.1', '0.9-1.1', '<0.9', 'ended<600')))

print('\n=== Builds: first three emblems (completion order) and emblems 4-8, shard-equivalent shares at the end')
WANT = {'pbg': ['VesperVale', 'Prism', 'Marcella', 'HeartOfRuin', 'Ryth', 'Vendetta'], 'pbg14': ['VesperVale', 'HeartOfRuin', 'Prism', 'Marcella'],
        'pbg07': ['VesperVale', 'Prism'], 'nyx': ['VesperVale', 'Prism', 'Marcella', 'HeartOfRuin'],
        'ifish': ['VesperVale', 'Vendetta', 'HeartOfRuin', 'Cassi', 'Issac', 'Ryth'],
        'pantheon': ['VesperVale', 'Prism', 'Willow'], 'coo': ['VesperVale', 'Vendetta', 'HeartOfRuin'], 'cm': ['VesperVale', 'Vendetta', 'HeartOfRuin', 'Tavi']}
for g in ORDER:
    games = [x for x in G[g] if x['base'] in X]
    for T in WANT[g]:
        f3 = collections.Counter(); tail = collections.Counter(); share = collections.Counter(); n = 0; none = 0; treas = 0
        for x in games:
            for b in X[x['base']]['bodies']:
                if b['team'] != x['S'] or b['type'] != T:
                    continue
                n += 1
                seq = emb_order(b)
                if not seq: none += 1
                f3['>'.join(seq[:3])] += 1
                if len(seq) > 3: tail['>'.join(seq[3:8])] += 1
                treas += sum(1 for s in seq if s[0] == 'T')
                fin = collections.Counter()
                # final shard equivalents by code from the buys ledger
                cnt = collections.Counter()
                for r, i, dq in b['buys']:
                    cnt[i] += dq
                for i, q in cnt.items():
                    if q > 0: share[code(i)] += q * (5 if i % 2 else 1)
        tot = sum(share.values()) or 1
        print(f"{g:9s} {T:12s} bodies {n:3d} | first3 " + ', '.join(f'{k or "-"} {v}' for k, v in f3.most_common(3)) +
              f" | no emblem {none} | Treasure emblems {treas} | tail " + ', '.join(f'{k} {v}' for k, v in tail.most_common(2)) +
              ' | shards ' + ', '.join(f'{k} {100*v/tot:.0f}' for k, v in share.most_common(5)))
