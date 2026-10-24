# Aggregate tools/live/fightfollow.mjs: after the opener, what each side's early participants do (rounds r0+1..3, r0+4..8) and the
# damage split by window, for engagements started by us / by them (our games) / top-vs-top.
#   python tools/live/fightfollow_agg.py C:/battlecode/cache/an_fights/fol.jsonl
import json, sys
from collections import Counter, defaultdict
G = [json.loads(l) for l in open(sys.argv[1], encoding='utf-8') if l.strip()]
tot = Counter()
for g in G:
    for k, n in g['c'].items():
        tot[k] += n
ACTS = ['hit', 'toward', 'away', 'side', 'still', 'farm', 'dead']
for ph in ('e', 'l'):
    print(f'\n=== FOLLOW-THROUGH ({"r0 <= 300" if ph == "e" else "r0 > 300"}): S = starter side, O = other side; share of participant-rounds')
    for lab in ('us', 'them', 'top'):
        for side in ('S', 'O'):
            for w in ('o1-3', 'o4-8'):
                c = {a: tot[f'{lab}|{ph}|act|{side}|{w}|{a}'] for a in ACTS}
                n = sum(c.values())
                if not n:
                    continue
                print(f'  starter={lab:4s} {side} {w}: n={n:6d} ' + ' '.join(f'{a} {100*c[a]/n:4.1f}%' for a in ACTS))
        dm = {(s, w): tot[f'{lab}|{ph}|dmg|{s}|{w}'] for s in 'SO' for w in ('w0', 'w1', 'w2')}
        print(f'  starter={lab:4s} damage share of the starter by window: r0..+2 {dm[("S","w0")]/max(1,dm[("S","w0")]+dm[("O","w0")]):.2f}  +3..+6 {dm[("S","w1")]/max(1,dm[("S","w1")]+dm[("O","w1")]):.2f}  +7.. {dm[("S","w2")]/max(1,dm[("S","w2")]+dm[("O","w2")]):.2f}')
