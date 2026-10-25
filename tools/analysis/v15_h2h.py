#!/usr/bin/env python3
"""Head-to-head summary over every ledger row of VARIANT vs BASE (all map pools played): wins, Wilson 95%, gem margin with a bootstrap 95%,
per pool. python3 -I tools/analysis/v15_h2h.py VARIANT... [--base _f4ec]"""
import json, math, os, random, sys, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import ledger  # noqa: E402
D = os.path.join(ROOT, "experiments/results/ledger_v3_0_4")
args = [a for a in sys.argv[1:] if not a.startswith('--')]
base = sys.argv[sys.argv.index('--base') + 1] if '--base' in sys.argv else '_f4ec'
args = [a for a in args if a != base]
pools = {}
for d in os.listdir(os.path.join(ROOT, 'maps')):
	p = os.path.join(ROOT, 'maps', d)
	if os.path.isdir(p):
		for f in os.listdir(p):
			if f.endswith('.map26a'):
				pools.setdefault(f[:-7], d)
def wilson(k, n):
	if n == 0:
		return 0, 0
	z = 1.96; p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
	return (c - h) / d, (c + h) / d
for v in args:
	bh, oh = ledger.src_hash(v), ledger.src_hash(base)
	rs = [r for r in map(json.loads, open(os.path.join(D, f'{v}_vs_{base}.jsonl'))) if r['bot_hash'] == bh and r['opp_hash'] == oh]
	by = collections.defaultdict(list)
	for r in rs:
		by[pools.get(r['map'], '?')].append(r)
	m = [r['gems'][0] - r['gems'][1] for r in rs]
	rnd = random.Random(7); bs = sorted(sum(rnd.choice(m) for _ in m) / len(m) for _ in range(2000))
	w = sum(r['win'] for r in rs); lo, hi = wilson(w, len(rs))
	print(f'{v} vs {base}: {w}/{len(rs)} = {100 * w / len(rs):.1f}% [{100 * lo:.1f}, {100 * hi:.1f}], margin {sum(m) / len(m):+.0f} [{bs[50]:+.0f}, {bs[1949]:+.0f}], deaths {sum(r["deaths"][0] for r in rs) / len(rs):.1f}-{sum(r["deaths"][1] for r in rs) / len(rs):.1f}, faults {sum(r.get("faults", 0) for r in rs)}')
	for p, g in sorted(by.items()):
		mm = [r['gems'][0] - r['gems'][1] for r in g]
		print(f'    {p:10s} {sum(r["win"] for r in g)}/{len(g)}  margin {sum(mm) / len(mm):+.0f}')
