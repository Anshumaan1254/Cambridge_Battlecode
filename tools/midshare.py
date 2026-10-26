#!/usr/bin/env python3
"""Middle control in local A/B games: gems captured by round R in each zone (own half / middle band / their half) for bot A and bot B.

    python tools/midshare.py TAG [--round 300] [--band 4]     (experiments/ab/TAG/rows.jsonl with --keep-replays rows)

The middle band: |chebyshev distance to our spawn centre - to theirs| <= band (the ladder study's definition, doc 28).
"""
import argparse
import collections
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tag')
    ap.add_argument('--round', type=int, default=300)
    ap.add_argument('--band', type=int, default=4)
    a = ap.parse_args()
    d0 = os.path.join(ROOT, 'experiments', 'ab', a.tag)
    rows = [json.loads(l) for l in open(os.path.join(d0, 'rows.jsonl'), encoding='utf-8')]
    os.makedirs(os.path.join(d0, 'dec'), exist_ok=True)
    C = collections.Counter()
    n = 0
    for r in rows:
        if not r.get('replay'):
            continue
        rp = os.path.join(ROOT, r['replay'])
        out = os.path.join(d0, 'dec', os.path.basename(rp) + '.json')
        if not os.path.exists(out):
            if not os.path.exists(rp):
                continue
            subprocess.run(['node', os.path.join(ROOT, 'tools', 'replay', 'decode.mjs'), rp, '--out', out], check=True, capture_output=True)
        d = json.load(open(out))
        a_side = 0 if r['side'] == 'a' else 1
        R = d['rounds']
        s0 = R[0] if R[0]['r'] <= 1 else R[1]
        pos = {0: [], 1: []}
        for c in s0['ch']:
            pos[c[1]].append((c[3], c[4]))
        cen = {t: (sum(p[0] for p in pos[t]) / len(pos[t]), sum(p[1] for p in pos[t]) / len(pos[t])) for t in (0, 1)}
        n += 1
        for e in d['events']:
            if e['k'] != 'CaptureGems' or e['r'] > a.round or 'team' not in e:
                continue
            side = e['team']
            p = tuple(e['at'])
            x, y = cheb(p, cen[side]), cheb(p, cen[1 - side])
            z = 'mid' if abs(x - y) <= a.band else ('own' if x < y else 'their')
            C[('A' if side == a_side else 'B', z)] += e['gems']
    if not n:
        print('no replays')
        return
    print('%s: %d games, gems by r%d per game: ' % (a.tag, n, a.round) + ' | '.join('%s own %.0f mid %.0f their %.0f' % (w, C[(w, 'own')] / n, C[(w, 'mid')] / n, C[(w, 'their')] / n) for w in 'AB'))


if __name__ == '__main__':
    main()
