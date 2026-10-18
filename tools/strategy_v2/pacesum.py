#!/usr/bin/env python3
"""Summarise pace runs (BOT vs idle): mean rounds to finish per map and per-champion economy.

usage: python3 tools/strategy_v2/pacesum.py DIR [DIR...]   (each DIR = bench.py --out of BOT vs idle; the first DIR is the baseline)
"""
import collections
import glob
import json
import os
import statistics
import sys


def load(d):
    res = {}
    champs = collections.defaultdict(lambda: collections.Counter())
    for f in glob.glob(os.path.join(d, '*', '*.json')):
        name = os.path.basename(f)[:-5]
        mp, side = name.rsplit('_', 1)
        j = json.load(open(f))
        team = 'teamA' if side == 'A' else 'teamB'
        gems = {t['team']: int(t['submittedGems']) for t in j['teams']}
        rounds = j['match']['roundsCompleted'] if gems[team] >= 1000 else 2000
        res[(mp, side)] = rounds
        for c in j['champions']:
            if c['team'] != team:
                continue
            m = c['metrics']
            k = champs[c['name']]
            k['n'] += 1
            k['gold'] += int(m['earnedGold'])
            k['gems'] += int(m['collectedGems'])
            k['mdmg'] += float(m['monsterDamageDone'])
            k['deaths'] += int(m['deaths'])
    return res, champs


def main():
    base = None
    for d in sys.argv[1:]:
        res, champs = load(d)
        if not res:
            print(d, 'no results')
            continue
        maps = sorted({m for m, _ in res})
        per = {m: statistics.mean([res[(m, s)] for s in 'AB' if (m, s) in res]) for m in maps}
        mean = statistics.mean(per.values())
        line = f"{os.path.basename(d.rstrip('/')):14} mean {mean:6.1f}  " + ' '.join(f"{m[:6]}={per[m]:.0f}" for m in maps)
        print(line)
        if base is None:
            base = per
        else:
            diff = {m: per[m] - base.get(m, per[m]) for m in maps}
            print(' ' * 15 + 'vs first: ' + ' '.join(f"{m[:6]}={diff[m]:+.0f}" for m in maps))
        print(' ' * 15 + '  '.join(f"{k}: gold {v['gold'] / v['n']:.0f} gems {v['gems'] / v['n']:.0f} mdmg {v['mdmg'] / v['n'] / 1000:.1f}k" for k, v in sorted(champs.items())))


if __name__ == '__main__':
    main()
