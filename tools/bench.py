#!/usr/bin/env python3
"""Run bot A vs bot B on every map, both sides, in parallel, and print a summary table.

usage: bench.py BOT_A BOT_B [--maps glob] [--jobs N] [--rounds R] [--out DIR] [--quiet]
Requires `cambc` on PATH and a cambc project in the current directory (bots/, maps/).
"""
import argparse, glob, json, os, subprocess, sys, time

def load_stats(path):
    with open(path) as f:
        d = json.load(f)
    teams = {t['team']: int(t['submittedGems']) for t in d['teams']}
    champs = d['champions']
    per = {'teamA': {'deaths': 0, 'kills': 0, 'gold': 0, 'names': []}, 'teamB': {'deaths': 0, 'kills': 0, 'gold': 0, 'names': []}}
    for c in champs:
        m = c['metrics']; t = c['team']
        per[t]['deaths'] += int(m['deaths']); per[t]['kills'] += int(m['kills']); per[t]['gold'] += int(m['earnedGold'])
        per[t]['names'].append(c['name'])
    faults = d.get('diagnostics', {}).get('botFaults', {})
    return {
        'outcome': d['match']['outcome'], 'rounds': d['match']['roundsCompleted'],
        'gems': teams, 'per': per, 'faults': faults,
    }

def build_if_stale(name):
    """Build bots/NAME only when its wasm is missing or older than its sources. Several agents share the
    sparring bots; rebuilding an unchanged bot from two benchmarks at once races in the same build dir."""
    wasm = os.path.join('bots', name, '.cambc', 'build', 'bot-injected.wasm')
    src = [os.path.join(d, f) for d, _, fs in os.walk(os.path.join('bots', name, 'src')) for f in fs]
    if os.path.exists(wasm) and src and os.path.getmtime(wasm) >= max(os.path.getmtime(f) for f in src):
        return
    subprocess.run(['cambc', 'build', name], check=True, capture_output=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a'); ap.add_argument('b')
    ap.add_argument('--maps', default='maps/*.map26a')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 4)
    ap.add_argument('--rounds', type=int, default=0)
    ap.add_argument('--out', default='bench_out')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--release', action='store_true', help='run as on the platform (debug_block skipped), like es_train.py')
    args = ap.parse_args()

    maps = sorted({m for pat in args.maps.split(',') for m in glob.glob(pat)})
    maps = [m for m in maps if not os.path.basename(m).startswith('zz_')]
    run_dir = os.path.join(args.out, f'{args.a}_vs_{args.b}_{int(time.time())}')
    os.makedirs(run_dir, exist_ok=True)
    rows = []
    manifest = os.path.join(run_dir, 'manifest.txt')
    with open(manifest, 'w') as f:
        for m in maps:
            name = os.path.splitext(os.path.basename(m))[0]
            for side, (x, y) in (('A', (args.a, args.b)), ('B', (args.b, args.a))):
                st = os.path.join(run_dir, f'{name}_{side}.json')
                rp = os.path.join(run_dir, f'{name}_{side}.repl26a')
                f.write(f'{os.path.abspath(os.path.join("bots", x))} {os.path.abspath(os.path.join("bots", y))} {os.path.abspath(m)} {os.path.abspath(rp)} --statistics {os.path.abspath(st)} --json\n')
                rows.append((name, side, st))
    cmd = ['cambc', 'run-batch', manifest, '--jobs', str(args.jobs), '--color', 'never']
    if args.rounds:
        cmd += ['--rounds', str(args.rounds)]
    if args.release:
        cmd.append('--release')
    build_if_stale(args.a)
    build_if_stale(args.b)
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    produced = sum(os.path.exists(st) for _, _, st in rows)
    if (p.returncode != 0 and not args.quiet) or produced == 0:
        # A batch that produced no statistics at all is an error even in --quiet mode (seen on Windows/MSYS).
        sys.stderr.write(f'run-batch exit {p.returncode}, {produced}/{len(rows)} games produced statistics\n')
        sys.stderr.write(p.stdout[-2000:] + p.stderr[-2000:])
    wins = losses = draws = 0
    win_rounds = []
    tot = {'our_gems': 0, 'their_gems': 0, 'our_deaths': 0, 'their_deaths': 0, 'our_kills': 0, 'our_gold': 0, 'their_gold': 0, 'faults': 0}
    lines = []
    for name, side, st in rows:
        if not os.path.exists(st):
            lines.append(f'{name:28s} {side}  MISSING'); continue
        s = load_stats(st)
        us, them = ('teamA', 'teamB') if side == 'A' else ('teamB', 'teamA')
        won = s['outcome'] == us
        lost = s['outcome'] == them
        wins += won; losses += lost; draws += (not won and not lost)
        if won:
            win_rounds.append(s['rounds'])
        tot['our_gems'] += s['gems'][us]; tot['their_gems'] += s['gems'][them]
        tot['our_deaths'] += s['per'][us]['deaths']; tot['their_deaths'] += s['per'][them]['deaths']
        tot['our_kills'] += s['per'][us]['kills']; tot['our_gold'] += s['per'][us]['gold']; tot['their_gold'] += s['per'][them]['gold']
        tot['faults'] += int(s['faults'].get(us, 0))
        lines.append(f"{name:28s} {side}  {'WIN ' if won else ('LOSS' if lost else 'DRAW')} r={s['rounds']:4d} gems {s['gems'][us]:4d}-{s['gems'][them]:4d} "
                     f"deaths {s['per'][us]['deaths']:2d}-{s['per'][them]['deaths']:2d} kills {s['per'][us]['kills']:2d} gold {s['per'][us]['gold']:5d}-{s['per'][them]['gold']:5d} "
                     f"| {','.join(s['per'][us]['names'])} vs {','.join(s['per'][them]['names'])}")
    if not args.quiet:
        print('\n'.join(lines))
    n = len(rows)
    print(f'== {args.a} vs {args.b}: {wins}W {losses}L {draws}D of {n}  winrate={wins / max(1, n):.3f}  '
          f"gems {tot['our_gems']}-{tot['their_gems']}  deaths {tot['our_deaths']}-{tot['their_deaths']}  kills {tot['our_kills']}  "
          f"gold {tot['our_gold']}-{tot['their_gold']}  faults {tot['faults']}  avg_win_round {sum(win_rounds) / max(1, len(win_rounds)):.0f}  ({time.time() - t0:.0f}s)")

if __name__ == '__main__':
    main()
