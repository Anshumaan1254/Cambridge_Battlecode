#!/usr/bin/env python3
"""Summarise bench.py run directories: win rate over all maps and over the 17 official maps (maps/comp) only.
   python3 tools/sum.py DIR...            # one line per run directory (A = the first bot named in the directory)
   python3 tools/sum.py --maps DIR...     # also one line per official map (wins of 2 sides)
DIR may be a bench --out directory (every run inside it) or one run directory."""
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench import load_stats

COMP = {os.path.splitext(os.path.basename(m))[0] for m in glob.glob(os.path.join(os.path.dirname(__file__), '..', 'maps', 'comp', '*.map26a'))}

def runs(paths):
    for p in paths:
        if os.path.exists(os.path.join(p, 'manifest.txt')):
            yield p
        else:
            yield from sorted(d for d in glob.glob(os.path.join(p, '*')) if os.path.exists(os.path.join(d, 'manifest.txt')))

def main():
    per_map = '--maps' in sys.argv
    for d in runs([a for a in sys.argv[1:] if not a.startswith('--')]):
        n = w = cn = cw = 0
        rounds = deaths = odeaths = 0
        maps = {}
        for st in sorted(glob.glob(os.path.join(d, '*_[AB].json'))):
            name, side = os.path.basename(st)[:-7], os.path.basename(st)[-6]
            s = load_stats(st)
            us, them = ('teamA', 'teamB') if side == 'A' else ('teamB', 'teamA')
            won = s['outcome'] == us
            n += 1; w += won
            deaths += s['per'][us]['deaths']; odeaths += s['per'][them]['deaths']
            if name in COMP:
                cn += 1; cw += won
                maps.setdefault(name, []).append(f"{side}{'W' if won else 'L'} {s['gems'][us]}-{s['gems'][them]} r{s['rounds']}")
        tag = os.path.basename(d.rstrip('/')).rsplit('_', 1)[0]
        print(f'{tag:28s} all {100 * w / max(1, n):5.1f} ({w}/{n})  comp {100 * cw / max(1, cn):5.1f} ({cw}/{cn})  deaths {deaths}-{odeaths}')
        if per_map:
            for m in sorted(maps):
                print(f'    {m:22s} ' + ' | '.join(maps[m]))

if __name__ == '__main__':
    main()
