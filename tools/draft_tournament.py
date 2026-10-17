#!/usr/bin/env python3
"""Composition tournament: forced drafts of the same bot code play a round robin on a map pool.

usage: draft_tournament.py --src bots/_dev --maps 'maps/ladder/*.map26a' [--comps NAME=d,d,d,d,d ...]
champion_draft values: ryth 0, vesper_vale 1, vendetta 2, cassi_and_issac 3, stellar 4, prism 5,
marcella 6, willow 7, ren 8, varg 9, tavi 10. Picks are taken in order (first 3/4/5 by team size).
Prints a payoff matrix (row win rate vs column) plus per-map-size breakdowns, and writes JSON results.
"""
import argparse, collections, glob, itertools, json, os, re, subprocess, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEFAULT = {
    'cur': '9,10,4,8,0',     # Varg Tavi Stellar Ren Ryth (legend's draft)
    'ciA': '9,3,4,8,10',     # Varg C&I Stellar Ren Tavi
    'ciB': '3,9,4,8,0',      # C&I Varg Stellar Ren Ryth
    'opp8694': '8,4,3,0,9',  # Ren Stellar C&I Ryth Varg (ladder opponent)
    'opp62e1': '9,3,2,4,0',  # Varg C&I Vendetta Stellar Ryth (ladder opponent)
    'ciS': '4,3,9,10,8',     # Stellar C&I Varg Tavi Ren
}


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default='bots/_dev')
    ap.add_argument('--maps', default='maps/ladder/*.map26a')
    ap.add_argument('--comps', nargs='*', default=[])
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 4)
    ap.add_argument('--out', default=os.path.join(ROOT, 'tune_out', 'draft'))
    args = ap.parse_args()
    comps = dict(DEFAULT)
    if args.comps:
        comps = dict(c.split('=') for c in args.comps)
    os.makedirs(args.out, exist_ok=True)
    for name, d in comps.items():
        r = sh(f'SRC={args.src} tools/variant.sh _dt_{name} --define "LEGEND_DRAFT {d}"')
        if r.returncode:
            sys.exit(r.stderr)
        r = sh(f'cambc build _dt_{name}')
        if r.returncode:
            sys.exit(r.stdout[-3000:])
    maps = sorted({m for pat in args.maps.split(',') for m in glob.glob(os.path.join(ROOT, pat)) if not os.path.basename(m).startswith('zz_')})
    run = os.path.join(args.out, f'run_{int(time.time())}')
    os.makedirs(run)
    rows = []
    with open(os.path.join(run, 'manifest.txt'), 'w') as f:
        for a, b in itertools.combinations(comps, 2):
            for m in maps:
                mn = os.path.splitext(os.path.basename(m))[0]
                for side in 'AB':
                    x, y = (a, b) if side == 'A' else (b, a)
                    st = os.path.join(run, f'{a}__{b}__{mn}_{side}.json')
                    f.write(f'{ROOT}/bots/_dt_{x} {ROOT}/bots/_dt_{y} {m} {os.path.join(run, os.path.basename(st)[:-5] + ".repl26a")} --statistics {st} --json\n')
                    rows.append((a, b, mn, side, st))
    t0 = time.time()
    sh(f'cambc run-batch {os.path.join(run, "manifest.txt")} --jobs {args.jobs} --color never')
    wins = collections.Counter()
    games = collections.Counter()
    gemdiff = collections.Counter()
    per_map = collections.defaultdict(collections.Counter)
    per_map_gd = collections.defaultdict(collections.Counter)  # gem margin per map and composition
    for a, b, mn, side, st in rows:
        if not os.path.exists(st):
            continue
        d = json.load(open(st))
        gems = {t['team']: int(t['submittedGems']) for t in d['teams']}
        a_team = 'teamA' if side == 'A' else 'teamB'
        b_team = 'teamB' if side == 'A' else 'teamA'
        o = d['match']['outcome']
        games[(a, b)] += 1
        games[(b, a)] += 1
        if o == a_team:
            wins[(a, b)] += 1
            per_map[mn][a] += 1
        elif o == b_team:
            wins[(b, a)] += 1
            per_map[mn][b] += 1
        gemdiff[(a, b)] += gems[a_team] - gems[b_team]
        gemdiff[(b, a)] += gems[b_team] - gems[a_team]
        per_map_gd[mn][a] += gems[a_team] - gems[b_team]
        per_map_gd[mn][b] += gems[b_team] - gems[a_team]
    names = list(comps)
    print(f'payoff (row win rate vs column), {len(maps)} maps x 2 sides, {time.time() - t0:.0f}s')
    print(' ' * 9 + ''.join(f'{n:>9s}' for n in names) + '      mean    worst')
    summary = {}
    for r in names:
        vals = [wins[(r, c)] / max(1, games[(r, c)]) for c in names if c != r]
        line = f'{r:9s}' + ''.join((f'{wins[(r, c)] / max(1, games[(r, c)]):9.2f}' if c != r else '        -') for c in names)
        line += f'   {sum(vals) / len(vals):7.3f}  {min(vals):7.3f}'
        summary[r] = {'mean': sum(vals) / len(vals), 'worst': min(vals), 'draft': comps[r]}
        print(line)
    print('\nwins per map (out of', 2 * (len(names) - 1), 'games each):')
    for mn in sorted(per_map):
        print(f'  {mn:30s} ' + ' '.join(f'{n}:{per_map[mn][n]}' for n in names))
    json.dump({'comps': comps, 'summary': summary, 'per_map': {k: dict(v) for k, v in per_map.items()},
               'per_map_gd': {k: dict(v) for k, v in per_map_gd.items()}, 'games_per_map': 2 * (len(names) - 1)}, open(os.path.join(run, 'result.json'), 'w'), indent=1)
    if not os.environ.get('KEEP_DT'):
        for n in names:
            sh(f'rm -rf bots/_dt_{n}')


if __name__ == '__main__':
    main()
