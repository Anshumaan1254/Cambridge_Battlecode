#!/usr/bin/env python3
"""Flag suspicious games in bench runs: our side stalled, starved or ran out the clock.

A stall (champions oscillating between targets, standing next to a group they cannot see, hoarding gems
somewhere without an altar) rarely shows in a win rate against strong opponents, but it loses outright to
weak ones. This scans the statistics JSONs that tools/bench.py writes and lists games where our side:
  - banked fewer than --min-gems, or
  - played more than --max-rounds rounds, or
  - earned less than --min-gold gold.

usage: stall_audit.py [RUN_DIR ...] [--bot NAME] [--min-gems 600] [--max-rounds 1500] [--min-gold 800]
With no RUN_DIR, scans the latest bench_out run of every opponent for --bot (default: legend).
"""
import argparse, glob, json, os


def our_team(fname):
    return 'teamA' if os.path.splitext(fname)[0].endswith('_A') else 'teamB'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('runs', nargs='*')
    ap.add_argument('--bot', default='legend')
    ap.add_argument('--min-gems', type=int, default=600)
    ap.add_argument('--max-rounds', type=int, default=1500)
    ap.add_argument('--min-gold', type=int, default=800)
    a = ap.parse_args()
    runs = a.runs
    if not runs:
        latest = {}
        for d in glob.glob(f'bench_out/{a.bot}_vs_*'):
            opp = d.rsplit('_', 1)[0]
            if opp not in latest or d > latest[opp]:
                latest[opp] = d
        runs = sorted(latest.values())
    total = flagged = 0
    for run in runs:
        for f in sorted(glob.glob(os.path.join(run, '*.json'))):
            try:
                d = json.load(open(f))
            except Exception:
                continue
            total += 1
            us = our_team(os.path.basename(f))
            them = 'teamB' if us == 'teamA' else 'teamA'
            gems = {t['team']: int(t['submittedGems']) for t in d['teams']}
            gold = sum(int(c['metrics']['earnedGold']) for c in d['champions'] if c['team'] == us)
            rounds = d['match']['roundsCompleted']
            why = []
            if gems[us] < a.min_gems:
                why.append(f'banked {gems[us]}')
            if rounds > a.max_rounds:
                why.append(f'{rounds} rounds')
            if gold < a.min_gold:
                why.append(f'gold {gold}')
            if why:
                flagged += 1
                won = d['match']['outcome'] == us
                print(f'{os.path.basename(run):40s} {os.path.basename(f):42s} {"W" if won else "L"} '
                      f'{gems[us]:5d}-{gems[them]:<5d} ' + ', '.join(why))
    print(f'{flagged} of {total} games flagged')


if __name__ == '__main__':
    main()
