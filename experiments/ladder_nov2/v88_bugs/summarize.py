#!/usr/bin/env python3
"""Summary of out/det/*.json by set: python3 v88_bugs/summarize.py [set ...]   sets: v88L v88W v84cp old_v84 old_all"""
import json, os, sys, glob
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h88  # noqa: E402

V = h88.V


def load(setname):
    rows = []
    for f in glob.glob(f'{V}/out/det/*.json'):
        r = json.load(open(f))
        if setname == 'v88L' and r['ver'] == 'v88' and r['res'] == 'L':
            rows.append(r)
        elif setname == 'v88W' and r['ver'] == 'v88' and r['res'] == 'W':
            rows.append(r)
        elif setname == 'v88' and r['ver'] == 'v88':
            rows.append(r)
        elif setname == 'v84cp' and r['kind'] == 'v84cp':
            rows.append(r)
        elif setname == 'old_v84' and r['kind'] == 'ranked' and r['ver'] == 'v84':
            rows.append(r)
        elif setname == 'old_all' and r['kind'] == 'ranked' and r['ver'] != 'v88':
            rows.append(r)
        elif setname == 'old_L' and r['kind'] == 'ranked' and r['ver'] != 'v88' and r['res'] == 'L':
            rows.append(r)
    return rows


def rew_line(rows, side, lo=1, hi=99999):
    xs = [k for r in rows for k in r['rew'] if k['side'] == side and lo <= k['r'] <= hi and k['r'] <= r['final'] - 40]
    dl = [k['delay'] for k in xs if k['delay'] is not None]
    n = max(1, len(xs))
    nev = sum(1 for k in xs if k['delay'] is None)
    oth = sum(1 for k in xs if k['by'] == 'other')
    big = [k for k in xs if k['delay'] is None or k['delay'] > 8]
    return (f"{side:4} kills {len(xs):4}  <=1 {100 * sum(1 for x in dl if x <= 1) / n:4.0f}%  2-8 {100 * sum(1 for x in dl if 2 <= x <= 8) / n:4.0f}%  "
            f"9-30 {100 * sum(1 for x in dl if 9 <= x <= 30) / n:4.0f}%  >30 {100 * sum(1 for x in dl if x > 30) / n:4.0f}%  never {100 * nev / n:4.0f}%  "
            f"taken by other team {100 * oth / n:4.0f}%  | >8-or-never {len(big)} ({len(big) / max(1, len(rows)):.1f}/game, "
            f"{sum(k['gems'] for k in big) / max(1, len(rows)):.0f} gems/game)")


def main():
    sets = sys.argv[1:] or ['v88L', 'v84cp', 'old_all']
    for s in sets:
        rows = load(s)
        n = max(1, len(rows))
        print(f'=== {s}: {len(rows)} games ({Counter(r["res"] for r in rows)})')
        print('  reward step-on delay, all kills (to final-40):')
        for side in ('we', 'they'):
            print('   ', rew_line(rows, side))
        print('  ... kills in r1-300:')
        for side in ('we', 'they'):
            print('   ', rew_line(rows, side, 1, 300))
        for side in ('we', 'they'):
            pa = [p for r in rows for p in r['passive'] if p['side'] == side]
            st = [p for r in rows for p in r['stall'] if p['side'] == side]
            di = [p for r in rows for p in r['dither'] if p['side'] == side]
            rc = [p for r in rows for p in r['recamp'] if p['side'] == side]
            bl = [p for r in rows for p in r['blocked'] if p['side'] == side]
            ho = [p for r in rows for p in r['hoard'] if p['side'] == side]
            bg = [p for r in rows for p in r['bagloss'] if p['side'] == side]
            tf = [p for r in rows for p in r['tribfail'] if p['side'] == side]
            print(f"  {side:4} passive runs {len(pa) / n:4.1f}/g dmg {sum(p['dmg'] for p in pa) / n:5.0f}/g died-at-end {sum(p['died'] for p in pa) / n:.2f}/g"
                  f" | stalls {len(st) / n:4.1f}/g {sum(p['len'] for p in st) / n:4.0f} rnd/g (40+ rnd: {sum(1 for p in st if p['len'] >= 40) / n:.2f}/g, dash inside {sum(1 for p in st if p['dashes']) / n:.2f}/g)"
                  f" | dither {len(di) / n:.2f}/g | recamp {len(rc) / n:.2f}/g | blocked-runs {len(bl) / n:.2f}/g (blocked moves {sum(r['blocked_n'][side] for r in rows) / n:.1f}/g)")
            print(f"       hoard(>=150 gold 100+ rnd) {len(ho) / n:.2f}/g | gold carried mean {sum(r['gold_mean'][side] for r in rows) / n:.0f} | shards r300 {sum(r['shards300'][side] for r in rows) / n:.0f} r600 {sum(r['shards600'][side] for r in rows) / n:.0f}"
                  f" | no-shop bodies {sum(1 for r in rows for p in r['noshop'] if p['side'] == side) / n:.2f}/g | deaths {sum(r['deaths'][side] for r in rows) / n:.1f}/g bag lost {sum(p['bag'] for p in bg) / n:.0f} gems/g"
                  f" | tribute fails {len(tf) / n:.2f}/g (died {sum(1 for p in tf if p['died']) / n:.2f}) | wasted spells {sum(r['wasted'].get(side, 0) for r in rows) / n:.1f}/g of {sum(r['casts'].get(side, 0) for r in rows) / n:.1f}")


if __name__ == '__main__':
    main()
