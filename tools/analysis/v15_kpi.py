#!/usr/bin/env python3
"""GOD v15 behaviour KPIs from session 17's gap extractor (one gapx.mjs line per game) for local games kept by tools/ledger.py --keep
(files <map>_<A|B>: 'us' is the side in the name) or ladder games (--ours 0): middle-band captures and gems, farm share and walk share
with an enemy within 8, walk share, deaths, back-and-forth (aba) per body, banks.
    python3 -I tools/analysis/v15_kpi.py GAPX.jsonl [--ours 0]"""
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
fixed = int(sys.argv[sys.argv.index('--ours') + 1]) if '--ours' in sys.argv else None
acc = {}
def add(k, v):
	acc.setdefault(k, []).append(v)
for r in rows:
	if 'T' not in r:
		continue
	ours = fixed if fixed is not None else (1 if r['file'].endswith('_B') else 0)
	for side, t in (('us', ours), ('them', 1 - ours)):
		T = r['T'][str(t)]
		nb = r['nb'][t]
		tb = {}
		for ph in T['tb']:
			for k, v in ph.items():
				tb[k] = tb.get(k, 0) + v
		alive = sum(tb.get(k, 0) for k in ('farm', 'fight', 'trib', 'recall', 'oncamp', 'walk', 'spawn', 'idle'))
		add(side + ' mid caps', sum(z['M'][0] for z in T['zones']))
		add(side + ' mid gems', sum(z['M'][1] for z in T['zones']))
		add(side + ' farm share', tb['farm'] / max(1, alive))
		add(side + ' walk share', tb['walk'] / max(1, alive))
		add(side + ' nearE farm share', tb.get('nearE_farm', 0) / max(1, tb.get('nearE', 0)))
		add(side + ' nearE walk share', tb.get('nearE_walk', 0) / max(1, tb.get('nearE', 0)))
		add(side + ' deaths', len(T['deaths']))
		add(side + ' aba per body', T['mv']['aba'] / max(1, nb))
		add(side + ' banked', r['sub'][t])
for k in sorted(acc, key=lambda s: (s.split(' ', 1)[1], s)):
	v = acc[k]
	print(f'  {k:24s} {sum(v) / len(v):9.3f}  (n {len(v)})')
