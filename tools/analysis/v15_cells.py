#!/usr/bin/env python3
"""GOD v15 screen table: per variant, head-to-head against GOD v14 (_f4ec) and the gem margin paired with v14's own game against each
proxy (same map and side), bootstrap 95%, games turned, deaths.
    python3 -I tools/analysis/v15_cells.py VARIANT... [--opps _px_ic,_px_pbg,_px_wbg] [--base _f4ec]"""
import argparse, json, os, random, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import ledger  # noqa: E402
D = os.path.join(ROOT, "experiments/results/ledger_v3_0_4")
def rows(bot, opp):
	p = os.path.join(D, f"{bot}_vs_{opp}.jsonl")
	if not os.path.exists(p):
		return {}
	bh = ledger.src_hash(bot) if os.path.isdir(os.path.join(ROOT, "bots", bot)) else None
	oh = ledger.src_hash(opp) if os.path.isdir(os.path.join(ROOT, "bots", opp)) else None
	out = {}
	for r in map(json.loads, open(p)):
		if (bh and r["bot_hash"] != bh) or (oh and r["opp_hash"] != oh):
			continue
		out[(r["map"], r["side"])] = r
	return out
def boot(xs, n=2000):
	if not xs:
		return 0, 0, 0
	rnd = random.Random(7)
	ms = sorted(sum(rnd.choice(xs) for _ in xs) / len(xs) for _ in range(n))
	return sum(xs) / len(xs), ms[int(0.025 * n)], ms[int(0.975 * n)]
ap = argparse.ArgumentParser()
ap.add_argument("variants", nargs="+")
ap.add_argument("--opps", default="_px_ic,_px_pbg,_px_wbg")
ap.add_argument("--base", default="_f4ec")
a = ap.parse_args()
opps = a.opps.split(",")
print(f"| variant | h2h vs {a.base}: wins, margin [95%], deaths us-them | " + " | ".join(f"{o}: wins, paired [95%], turned" for o in opps) + " | pooled paired [95%], turned |")
print("|---|---|" + "---|" * len(opps) + "---|")
for v in a.variants:
	h = rows(v, a.base)
	hm = boot([r["gems"][0] - r["gems"][1] for r in h.values()])
	hd = (sum(r["deaths"][0] for r in h.values()) / max(1, len(h)), sum(r["deaths"][1] for r in h.values()) / max(1, len(h)))
	cells, xa, ga, la = [], [], 0, 0
	for o in opps:
		va, ra = rows(v, o), rows(a.base, o)
		ks = [k for k in va if k in ra]
		xs = [(va[k]["gems"][0] - va[k]["gems"][1]) - (ra[k]["gems"][0] - ra[k]["gems"][1]) for k in ks]
		g = sum(1 for k in ks if va[k]["win"] and not ra[k]["win"])
		l = sum(1 for k in ks if ra[k]["win"] and not va[k]["win"])
		m = boot(xs)
		xa += xs; ga += g; la += l
		cells.append(f"{sum(r['win'] for r in va.values())}/{len(va)}, {m[0]:+.0f} [{m[1]:+.0f}, {m[2]:+.0f}], {g}/{l}")
	pm = boot(xa)
	print(f"| {v} | {sum(r['win'] for r in h.values())}/{len(h)}, {hm[0]:+.0f} [{hm[1]:+.0f}, {hm[2]:+.0f}], {hd[0]:.1f}-{hd[1]:.1f} | " + " | ".join(cells) + f" | {pm[0]:+.0f} [{pm[1]:+.0f}, {pm[2]:+.0f}], {ga}/{la} |")
