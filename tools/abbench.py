#!/usr/bin/env python3
"""Local A/B bench on cambc run-batch: BOT_A vs BOT_B on every map of a pool, both sides, in parallel; summary + per-game jsonl.

    python tools/abbench.py BOT_A BOT_B [--maps 'maps/s3/*.map26a'] [--jobs 6] [--tag NAME] [--release] [--keep-replays] [--log-limit BYTES]

Writes experiments/ab/<tag>/rows.jsonl (one row per game, from BOT_A's point of view) and prints: wins, mean gem margin with a
bootstrap 95% interval, deaths, mean final round. Rows already present (same map and side) are reused, so a cut run resumes.
"""
import argparse
import glob
import json
import os
import random
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def stats_row(path, a_side):
    d = json.load(open(path, encoding='utf-8'))
    gems = {t['team']: int(t['submittedGems']) for t in d['teams']}
    per = {'teamA': [0, 0], 'teamB': [0, 0]}
    for c in d['champions']:
        m = c['metrics']
        per[c['team']][0] += int(m['deaths'])
        per[c['team']][1] += int(m['kills'])
    us, them = ('teamA', 'teamB') if a_side == 'a' else ('teamB', 'teamA')
    out = d['match']['outcome']
    win = (out == 'teamA' and a_side == 'a') or (out == 'teamB' and a_side == 'b')
    faults = d.get('diagnostics', {}).get('botFaults', {})
    return {'win': bool(win), 'gems': [gems.get(us, 0), gems.get(them, 0)], 'deaths': [per[us][0], per[them][0]],
            'rounds': int(d['match']['roundsCompleted']), 'outcome': out, 'faults': faults}


def boot(xs, n=2000):
    if not xs:
        return (0, 0)
    random.seed(1)
    ms = sorted(sum(random.choice(xs) for _ in xs) / len(xs) for _ in range(n))
    return ms[int(0.025 * n)], ms[int(0.975 * n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('--maps', default='maps/s3/*.map26a')
    ap.add_argument('--jobs', type=int, default=6)
    ap.add_argument('--tag', default='')
    ap.add_argument('--release', action='store_true')
    ap.add_argument('--keep-replays', action='store_true')
    ap.add_argument('--log-limit', default='0')
    ap.add_argument('--sides', default='ab')
    a = ap.parse_args()
    tag = a.tag or '%s_vs_%s' % (a.a, a.b)
    out = os.path.join(ROOT, 'experiments', 'ab', tag)
    os.makedirs(os.path.join(out, 'g'), exist_ok=True)
    rows_p = os.path.join(out, 'rows.jsonl')
    have = {}
    if os.path.exists(rows_p):
        for l in open(rows_p, encoding='utf-8'):
            r = json.loads(l)
            have[(r['map'], r['side'])] = r
    maps = sorted(glob.glob(os.path.join(ROOT, a.maps)))
    todo = []
    for mp in maps:
        mn = os.path.basename(mp)[:-7]
        for side in a.sides:
            if (mn, side) not in have:
                todo.append((mn, mp, side))
    stamp = str(int(time.time()))
    man = os.path.join(ROOT, 'experiments', 'ab', tag, 'manifest_%s.txt' % stamp)
    rel = lambda p: os.path.relpath(p, os.path.dirname(man)).replace('\\', '/')
    with open(man, 'w', encoding='utf-8') as f:
        for mn, mp, side in todo:
            A, B = (a.a, a.b) if side == 'a' else (a.b, a.a)
            rp = os.path.join(out, 'g', '%s_%s_%s.repl26a' % (mn, side, stamp))
            sp = os.path.join(out, 'g', '%s_%s_%s.json' % (mn, side, stamp))
            f.write('%s %s %s %s --statistics %s --json\n' % (rel(os.path.join(ROOT, 'bots', A)), rel(os.path.join(ROOT, 'bots', B)), rel(mp), rel(rp), rel(sp)))
    if todo:
        for bot in {a.a, a.b}:
            r = subprocess.run(['cambc', 'build', bot] + (['--release'] if a.release and False else []), cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if r.returncode != 0:
                sys.exit('build failed for %s:\n%s' % (bot, r.stdout[-2000:] + r.stderr[-2000:]))
        cmd = ['cambc', 'run-batch', man, '--jobs', str(a.jobs), '--log-limit', a.log_limit] + (['--release'] if a.release else [])
        t0 = time.time()
        subprocess.run(cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print('ran %d games in %.0f s' % (len(todo), time.time() - t0))
        with open(rows_p, 'a', encoding='utf-8') as f:
            for mn, mp, side in todo:
                sp = os.path.join(out, 'g', '%s_%s_%s.json' % (mn, side, stamp))
                rp = os.path.join(out, 'g', '%s_%s_%s.repl26a' % (mn, side, stamp))
                if not os.path.exists(sp):
                    print('missing result', mn, side)
                    continue
                try:
                    r = stats_row(sp, side)
                except Exception as e:  # noqa
                    print('bad stats', mn, side, e)
                    continue
                r.update({'map': mn, 'side': side, 'a': a.a, 'b': a.b, 'replay': os.path.relpath(rp, ROOT) if a.keep_replays else None})
                have[(mn, side)] = r
                f.write(json.dumps(r) + '\n')
                os.remove(sp)
                if not a.keep_replays and os.path.exists(rp):
                    os.remove(rp)
    rows = [r for (mn, s), r in have.items() if any(os.path.basename(m)[:-7] == mn for m in maps)]
    n = len(rows)
    if not n:
        print('no rows')
        return
    w = sum(r['win'] for r in rows)
    mar = [r['gems'][0] - r['gems'][1] for r in rows]
    lo, hi = boot(mar)
    fl = sum(1 for r in rows if (sum(r['faults'].values()) if isinstance(r['faults'], dict) else r['faults']))
    print('%s vs %s: %d/%d = %.1f%% | margin %+.0f [%+.0f, %+.0f] | deaths %.1f-%.1f | rounds %.0f | games with faults %d' % (
        a.a, a.b, w, n, 100 * w / n, sum(mar) / n, lo, hi, sum(r['deaths'][0] for r in rows) / n, sum(r['deaths'][1] for r in rows) / n,
        sum(r['rounds'] for r in rows) / n, fl))


if __name__ == '__main__':
    main()
