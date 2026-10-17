#!/usr/bin/env python3
"""Summarise bench.py output directories for gem-scarce (tiebreak) maps.

usage: gold_stats.py DIR [DIR...] [--bot NAME] [--per-game]

Each DIR is a bench run (`BOT_vs_OPP_<time>`; side A = BOT is team A). For every game it reads the match
statistics JSON and infers how the game was decided, using the engine's order (strings in the cambc binary):
  gems   : someone reached winning_gems before the round limit, or the round limit with more banked gems
  gold   : round limit, tied on gems, more gold EARNED (sum of the champions' earnedGold)
  kills  : tied on gems and gold, more kills
  side   : tied on everything, team B wins
Prints one line per game (--per-game) and a summary per directory: wins, reasons, banked gems, earned gold,
kills, deaths, our faults.
"""
import glob, json, os, sys

def num(x):
    try:
        return int(float(x))
    except Exception:
        return 0

def game(path):
    d = json.load(open(path))
    gems = {t['team']: num(t['submittedGems']) for t in d['teams']}
    per = {'teamA': dict(gold=0, kills=0, deaths=0, dmg=0, collected=0), 'teamB': dict(gold=0, kills=0, deaths=0, dmg=0, collected=0)}
    for c in d['champions']:
        m = c['metrics']; p = per[c['team']]
        p['gold'] += num(m['earnedGold']); p['kills'] += num(m['kills']); p['deaths'] += num(m['deaths'])
        p['dmg'] += num(m.get('monsterDamageDone', 0)); p['collected'] += num(m.get('collectedGems', 0))
    rounds = num(d['match']['roundsCompleted'])
    out = d['match']['outcome']
    if max(gems.values()) >= 1000 or gems['teamA'] != gems['teamB']:
        reason = 'gems' if max(gems.values()) >= 1000 else 'limit-gems'
    elif per['teamA']['gold'] != per['teamB']['gold']:
        reason = 'gold'
    elif per['teamA']['kills'] != per['teamB']['kills']:
        reason = 'kills'
    else:
        reason = 'sideB'
    faults = d.get('diagnostics', {}).get('botFaults', {})
    return dict(out=out, rounds=rounds, gems=gems, per=per, reason=reason, faults=faults)

def summarise(run, per_game):
    files = sorted(glob.glob(os.path.join(run, '*.json')))
    name = os.path.basename(run.rstrip('/'))
    tot = dict(w=0, l=0, n=0, reasons={}, our_gems=0, their_gems=0, our_gold=0, their_gold=0, our_k=0, their_k=0, our_d=0, their_d=0, faults=0, our_col=0, their_col=0)
    for f in files:
        base = os.path.basename(f)[:-5]
        side = base[-1]
        mp = base[:-2]
        g = game(f)
        us, them = ('teamA', 'teamB') if side == 'A' else ('teamB', 'teamA')
        won = g['out'] == us
        tot['n'] += 1; tot['w'] += won; tot['l'] += (g['out'] == them)
        key = g['reason'] + ('+' if won else '-')
        tot['reasons'][key] = tot['reasons'].get(key, 0) + 1
        tot['our_gems'] += g['gems'][us]; tot['their_gems'] += g['gems'][them]
        tot['our_gold'] += g['per'][us]['gold']; tot['their_gold'] += g['per'][them]['gold']
        tot['our_k'] += g['per'][us]['kills']; tot['their_k'] += g['per'][them]['kills']
        tot['our_d'] += g['per'][us]['deaths']; tot['their_d'] += g['per'][them]['deaths']
        tot['our_col'] += g['per'][us]['collected']; tot['their_col'] += g['per'][them]['collected']
        tot['faults'] += num(g['faults'].get(us, 0))
        if per_game:
            print(f"  {mp:30s} {side} {'WIN ' if won else 'LOSS'} r={g['rounds']:4d} by {g['reason']:10s} gems {g['gems'][us]:4d}-{g['gems'][them]:4d} "
                  f"gold {g['per'][us]['gold']:5d}-{g['per'][them]['gold']:5d} kills {g['per'][us]['kills']:2d}-{g['per'][them]['kills']:2d} "
                  f"collected {g['per'][us]['collected']:4d}-{g['per'][them]['collected']:4d}")
    n = max(1, tot['n'])
    rs = ' '.join(f'{k}:{v}' for k, v in sorted(tot['reasons'].items()))
    print(f"== {name}: {tot['w']}W {tot['l']}L of {tot['n']} ({100.0 * tot['w'] / n:.1f}%) | {rs} | gems {tot['our_gems']}-{tot['their_gems']} "
          f"gold {tot['our_gold']}-{tot['their_gold']} kills {tot['our_k']}-{tot['their_k']} deaths {tot['our_d']}-{tot['their_d']} "
          f"collected {tot['our_col']}-{tot['their_col']} faults {tot['faults']}")
    return tot

if __name__ == '__main__':
    args = sys.argv[1:]
    per_game = '--per-game' in args
    dirs = [a for a in args if not a.startswith('--')]
    for d in dirs:
        summarise(d, per_game)
