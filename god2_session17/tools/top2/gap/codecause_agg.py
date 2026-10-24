# gap_g8_code: aggregate tools/top2/gap/codecause.mjs (one JSON line per S0 game) into the tables of experiments/top2/gap_g8_code.md.
#   python tools/top2/gap/codecause_agg.py [C:/battlecode/cache/gap_g8/codecause.jsonl]
import json, sys
from collections import defaultdict

src = sys.argv[1] if len(sys.argv) > 1 else 'C:/battlecode/cache/gap_g8/codecause.jsonl'
tot = defaultdict(float)
per_opp = defaultdict(lambda: defaultdict(float))
games = 0
for line in open(src, encoding='utf-8'):
    try:
        g = json.loads(line)
    except Exception:
        continue
    if 'c' not in g:
        continue
    games += 1
    for k, v in g['c'].items():
        tot[k] += v
        per_opp[g['opp']][k] += v
print(f'games {games}')

def pct(a, b):
    return f'{100.0 * a / b:5.1f}%' if b else '   - '

# A: arrivals by bag
print('\n== A: arrival at a farmer (enemy comes within 8), response in the next 12 rounds, by bag and round')
print('side  round  bag    n      sub     rec     keep    alt     other   per game')
for s in ('us', 'them'):
    for rd in ('e', 'l'):
        for bag in ('0-9', '10-21', '22-53', '54+'):
            k = f'A|{s}|{rd}|{bag}'
            n = tot[k + '|n']
            if not n:
                continue
            row = [pct(tot[f'{k}|{r}'], n) for r in ('sub', 'rec', 'keep', 'alt', 'other')]
            print(f'{s:5} {"<150" if rd == "e" else ">=150":6} {bag:6} {int(n):6} ' + ' '.join(f'{x:7}' for x in row) + f'  {n / games:6.2f}')
    # pooled over rounds
    for bag in ('0-9', '10-21', '22-53', '54+'):
        n = sum(tot[f'A|{s}|{rd}|{bag}|n'] for rd in ('e', 'l'))
        if not n:
            continue
        row = [pct(sum(tot[f'A|{s}|{rd}|{bag}|{r}'] for rd in ('e', 'l')), n) for r in ('sub', 'rec', 'keep', 'alt', 'other')]
        print(f'{s:5} {"all":6} {bag:6} {int(n):6} ' + ' '.join(f'{x:7}' for x in row) + f'  {n / games:6.2f}')

# C: capture -> recall
print('\n== C: gem capture followed by a recall of the capturer (combo: started r-6..r-1, after: r..r+10)')
for s in ('us', 'them'):
    for far in ('near', 'far', None):
        keys = ('near', 'far') if far is None else (far,)
        n = sum(tot[f'C|{s}|{f}|{c}'] for f in keys for c in ('combo', 'after', 'none'))
        if not n:
            continue
        combo = sum(tot[f'C|{s}|{f}|combo'] for f in keys)
        after = sum(tot[f'C|{s}|{f}|after'] for f in keys)
        print(f'{s:5} {far or "all":5} captures {int(n):6} ({n / games:5.1f}/game)  combo {pct(combo, n)}  after {pct(after, n)}  none {pct(n - combo - after, n)}')
for opp, t in sorted(per_opp.items()):
    for s in ('us', 'them'):
        n = sum(t[f'C|{s}|{f}|{c}'] for f in ('near', 'far') for c in ('combo', 'after', 'none'))
        combo = sum(t[f'C|{s}|{f}|combo'] for f in ('near', 'far'))
        after = sum(t[f'C|{s}|{f}|after'] for f in ('near', 'far'))
        print(f'   {opp[:22]:22} {s:5} n {int(n):5} combo {pct(combo, n)} after {pct(after, n)}')

# R: rally walk-in
print('\n== R: farmers 3-9 tiles from an ally that starts hitting a champion; next 5 rounds')
print('side  hp   dist   n      toward  keep    hit')
for s in ('us', 'them'):
    for hp in ('hi', 'lo'):
        for dB in ('d3-5', 'd6-9'):
            k = f'R|{s}|{hp}|{dB}'
            n = tot[k + '|n']
            if not n:
                continue
            print(f'{s:5} {hp:4} {dB:6} {int(n):6} {pct(tot[k + "|tow"], n):7} {pct(tot[k + "|keep"], n):7} {pct(tot[k + "|hit"], n):7}')

# F: fight propensity by prior deaths
print('\n== F: own health >= 35%, enemy within 4, r < 1000 (every 3rd round): share that deals champion damage in r..r+2, by prior deaths')
for s in ('us', 'them'):
    for rb in ('a<.67', 'b.67-.87', 'c.87-1.15', 'd1.15-1.5', 'e>1.5'):
        cells = []
        for pd in ('d0', 'd1', 'd2', 'd3'):
            n = sum(tot[f'F|{s}|{rb}|{ph}|{pd}|n'] for ph in ('p0', 'p1', 'p2'))
            f = sum(tot[f'F|{s}|{rb}|{ph}|{pd}|fight'] for ph in ('p0', 'p1', 'p2'))
            cells.append(f'{pd}: {pct(f, n)} ({int(n)})')
        print(f'{s:5} {rb:10} ' + '  '.join(cells))
    # phase-controlled: r300-999 only
    for ph in ('p0', 'p1', 'p2'):
        cells = []
        for pd in ('d0', 'd1', 'd2', 'd3'):
            n = sum(tot[f'F|{s}|{rb}|{ph}|{pd}|n'] for rb in ('a<.67', 'b.67-.87', 'c.87-1.15', 'd1.15-1.5', 'e>1.5'))
            f = sum(tot[f'F|{s}|{rb}|{ph}|{pd}|fight'] for rb in ('a<.67', 'b.67-.87', 'c.87-1.15', 'd1.15-1.5', 'e>1.5'))
            cells.append(f'{pd}: {pct(f, n)} ({int(n)})')
        print(f'{s:5} {ph:10} ' + '  '.join(cells))
    # ratio 0.67-1.5 and phase 1-2 (r300-999)
    cells = []
    for pd in ('d0', 'd1', 'd2', 'd3'):
        n = sum(tot[f'F|{s}|{rb}|{ph}|{pd}|n'] for rb in ('b.67-.87', 'c.87-1.15', 'd1.15-1.5') for ph in ('p1', 'p2'))
        f = sum(tot[f'F|{s}|{rb}|{ph}|{pd}|fight'] for rb in ('b.67-.87', 'c.87-1.15', 'd1.15-1.5') for ph in ('p1', 'p2'))
        cells.append(f'{pd}: {pct(f, n)} ({int(n)})')
    print(f'{s:5} {"0.67-1.5 r300-999":10} ' + '  '.join(cells))

# T: tribute starts
print('\n== T: tribute starts by bag, enemy within 8 in the 12 rounds before, recall in the 25 rounds before')
for s in ('us', 'them'):
    n_all = sum(v for k, v in tot.items() if k.startswith(f'T|{s}|'))
    print(f'{s}: {int(n_all)} starts ({n_all / games:.1f}/game)')
    for rd in ('e', 'l'):
        for bag in ('1-21', '22-53', '54-99', '100+'):
            row = {}
            for en in ('en', 'no'):
                for via in ('viaR', 'walk'):
                    row[(en, via)] = tot[f'T|{s}|{rd}|{bag}|{en}|{via}']
            n = sum(row.values())
            if not n:
                continue
            print(f'   {"<150" if rd == "e" else ">=150":6} {bag:6} n {int(n):5} ({n / games:5.2f}/game)  enemy-near walk {pct(row[("en", "walk")], n)}  enemy-near via-recall {pct(row[("en", "viaR")], n)}  quiet walk {pct(row[("no", "walk")], n)}  quiet via-recall {pct(row[("no", "viaR")], n)}')
