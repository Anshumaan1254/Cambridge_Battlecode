#!/usr/bin/env python3
"""Paired cells against the team proxies (tools/ic/make_team_proxy.py) and v10 head-to-head: for each variant and opponent, wins,
the gem margin, and the margin paired with GOD v10's own game against the same opponent, map and side (bootstrap 95%), games turned.

    python3 -I tools/ic/cells.py VARIANT... [--opps _px_ic,_px_pbg,_px_wbg] [--base god]"""
import argparse, json, os, random, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import ledger  # noqa: E402

D = os.path.join(ROOT, "experiments/results/ledger_v3_0_4")


def rows(bot, opp):
	p = os.path.join(D, f"{bot}_vs_{opp}.jsonl")
	if not os.path.exists(p):
		return {}
	bh, oh = ledger.src_hash(bot), ledger.src_hash(opp)
	return {(r["map"], r["side"]): r for r in map(json.loads, open(p)) if r["bot_hash"] == bh and r["opp_hash"] == oh}


def boot(xs, n=2000):
	if not xs:
		return 0, 0, 0
	rnd = random.Random(7)
	ms = sorted(sum(rnd.choice(xs) for _ in xs) / len(xs) for _ in range(n))
	return sum(xs) / len(xs), ms[int(0.025 * n)], ms[int(0.975 * n)]


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("variants", nargs="+")
	ap.add_argument("--opps", default="_px_ic,_px_pbg,_px_wbg")
	ap.add_argument("--base", default="god")
	a = ap.parse_args()
	opps = a.opps.split(",")
	print("| variant | " + " | ".join(f"{o}: wins, paired margin, turned" for o in opps) + " | pooled paired | h2h vs " + a.base + " |")
	print("|---|" + "---|" * (len(opps) + 2))
	for v in a.variants:
		cells, xs_all, g_all, l_all = [], [], 0, 0
		for o in opps:
			va, ra = rows(v, o), rows(a.base, o)
			xs = [(va[k]["gems"][0] - va[k]["gems"][1]) - (ra[k]["gems"][0] - ra[k]["gems"][1]) for k in va if k in ra]
			g = sum(1 for k in va if k in ra and va[k]["win"] and not ra[k]["win"])
			l = sum(1 for k in va if k in ra and ra[k]["win"] and not va[k]["win"])
			m = boot(xs)
			xs_all += xs; g_all += g; l_all += l
			cells.append(f"{sum(r['win'] for r in va.values())}/{len(va)}, {m[0]:+.0f} [{m[1]:+.0f}, {m[2]:+.0f}], {g}/{l}")
		pm = boot(xs_all)
		h = rows(v, a.base)
		hm = boot([r["gems"][0] - r["gems"][1] for r in h.values()])
		print(f"| {v} | " + " | ".join(cells) + f" | {pm[0]:+.0f} [{pm[1]:+.0f}, {pm[2]:+.0f}], {g_all}/{l_all} | {sum(r['win'] for r in h.values())}/{len(h)}, {hm[0]:+.0f} |")


if __name__ == "__main__":
	main()
