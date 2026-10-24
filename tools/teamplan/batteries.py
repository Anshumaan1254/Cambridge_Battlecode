#!/usr/bin/env python3
"""Batteries of the teamplan switches on the GOD v10 test copy (TEAMPLAN.md section 9, step 5). Results are SIMULATED (v10): they say how
a rule changes v10's games, not how it plays on the ladder.

    python3 -I tools/teamplan/batteries.py [--maps 'maps/official/*.map26a'] [--jobs 4] [--only NAME,...] [--report-only]

Variants (tools/teamplan/prepare_v10.py; each switch alone, then together):
  _tp_foc tp_focus=1 | _tp_bag tp_bag=1 | _tp_tim tp_timing=1 | _tp_tb tp_tiebreak=1 | _tp_tb150 tp_tiebreak=1 tp_tb_cap=150 |
  _tp_own tp_own=1 | _tp_all (focus, bag, timing, tiebreak, own)
Opponent families: 1 = GOD v10 (_tp_v10ref = bots/god); 2 = v10 forced to the strong teams' roster per map (_tp_v10F,
tools/teamplan/make_forced_v10.py). Every game both sides, release mode, through tools/ledger.py (a cut run resumes).
Statistics per cell: wins with a 95% Wilson interval; per map (both sides) 2-0 / 1-1 / 0-2 and a two-sided sign test on 2-0 vs 0-2;
the mean gem margin per map (ours minus theirs, both sides averaged) with a bootstrap 95% interval; family 2 also the paired margin
difference against v10's own games on the same map and side (the variant's margin minus v10's).
Writes experiments/results/teamplan/batteries_v10.md."""
import argparse
import math
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import ledger  # noqa: E402

VARIANTS = [
	("_tp_foc", ["tp_focus=1"], "kill-value targeting (focus.h)"),
	("_tp_bag", ["tp_bag=1"], "fight bar rises with the bag (bag.h)"),
	("_tp_tim", ["tp_timing=1"], "step into reach only when we act first (timing.h)"),
	("_tp_tb", ["tp_tiebreak=1"], "tiebreak mode, cap 60 (tiebreak.h)"),
	("_tp_tb150", ["tp_tiebreak=1", "tp_tb_cap=150"], "tiebreak mode, cap 150"),
	("_tp_own", ["tp_own=1"], "soft group ownership via draft memory (assign.h)"),
	("_tp_all", ["tp_focus=1", "tp_bag=1", "tp_timing=1", "tp_tiebreak=1", "tp_own=1"], "all five"),
]
BASE, FORCED = "_tp_v10ref", "_tp_v10F"


def wilson(w, n, z=1.96):
	if n == 0:
		return 0.0, 0.0
	p = w / n
	d = 1 + z * z / n
	c = (p + z * z / (2 * n)) / d
	h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
	return c - h, c + h


def sign_p(a, b):
	n = a + b
	if n == 0:
		return 1.0
	k = min(a, b)
	p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
	return min(1.0, 2 * p)


def boot(xs, n=2000, seed=7):
	if not xs:
		return 0.0, 0.0, 0.0
	rnd = random.Random(seed)
	m = sum(xs) / len(xs)
	bs = sorted(sum(rnd.choice(xs) for _ in xs) / len(xs) for _ in range(n))
	return m, bs[int(0.025 * n)], bs[int(0.975 * n) - 1]


def margin(r):
	g = r["gems"]
	return g[0] - g[1]


def cell(bot, opp):
	rows = ledger.current_rows(bot, opp, True)
	if not rows:
		return None
	w = sum(r["win"] for r in rows.values())
	n = len(rows)
	maps = {}
	for (m, side), r in rows.items():
		maps.setdefault(m, {})[side] = r
	two = one = zero = 0
	mar = []
	for m, d in maps.items():
		if len(d) == 2:
			s = sum(x["win"] for x in d.values())
			two += s == 2
			one += s == 1
			zero += s == 0
			mar.append(sum(margin(x) for x in d.values()) / 2)
	lo, hi = wilson(w, n)
	mm, ml, mh = boot(mar)
	return {"n": n, "w": w, "lo": lo, "hi": hi, "two": two, "one": one, "zero": zero, "p": sign_p(two, zero), "m": mm, "ml": ml, "mh": mh,
			"deaths": (sum(r["deaths"][0] for r in rows.values()), sum(r["deaths"][1] for r in rows.values())), "rows": rows}


def paired(var, base, opp):
	a, b = ledger.current_rows(var, opp, True), ledger.current_rows(base, opp, True)
	per = {}
	for k in set(a) & set(b):
		per.setdefault(k[0], []).append(margin(a[k]) - margin(b[k]))
	xs = [sum(v) / len(v) for v in per.values()]
	wa = sum(a[k]["win"] for k in set(a) & set(b))
	wb = sum(b[k]["win"] for k in set(a) & set(b))
	m, lo, hi = boot(xs)
	return {"m": m, "lo": lo, "hi": hi, "wa": wa, "wb": wb, "n": len(set(a) & set(b))}


def run_cell(bot, opp, maps, jobs):
	r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ledger.py"), "run", bot, opp, "--maps", maps, "--jobs", str(jobs), "--release"],
					   cwd=ROOT, capture_output=True, text=True)
	last = (r.stdout.strip().splitlines() or [""])[-1]
	print(f"  {bot} vs {opp}: {last}", flush=True)


def fmt(c):
	return (f"{c['w']}/{c['n']} = {100 * c['w'] / c['n']:.1f}% [{100 * c['lo']:.1f}, {100 * c['hi']:.1f}] | {c['two']} / {c['one']} / {c['zero']} | "
			f"p {c['p']:.3f} | {c['m']:+.1f} [{c['ml']:+.1f}, {c['mh']:+.1f}] | {c['deaths'][0]}-{c['deaths'][1]}")


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--maps", default="maps/official/*.map26a")
	ap.add_argument("--jobs", type=int, default=4)
	ap.add_argument("--only", default="")
	ap.add_argument("--report-only", action="store_true")
	a = ap.parse_args()
	vs = [v for v in VARIANTS if not a.only or v[0] in a.only.split(",")]
	if not a.report_only:
		for name, sets, _ in vs:
			r = subprocess.run([sys.executable, "-I", os.path.join(HERE, "prepare_v10.py"), "--name", name] + sets, cwd=ROOT, capture_output=True, text=True)
			print(r.stdout.strip() or r.stderr.strip()[-500:], flush=True)
		run_cell(BASE, FORCED, a.maps, a.jobs)
		for name, _, _ in vs:
			run_cell(name, BASE, a.maps, a.jobs)
			run_cell(name, FORCED, a.maps, a.jobs)
	L = ["# Batteries of the teamplan switches on the GOD v10 test copy (SIMULATED (v10); tools/teamplan/batteries.py)", "",
		 f"Maps `{a.maps}`, both sides, release mode, cambc engine of `tools/ledger.py`. Columns: wins [95% Wilson interval] | maps won from "
		 "both sides / split / lost from both sides | sign test on 2-0 vs 0-2 | mean gem margin per map [bootstrap 95%] | deaths ours-theirs.", "",
		 "## Family 1: head-to-head against GOD v10", "", "| Variant | Switch | Result |", "|---|---|---|"]
	for name, sets, what in VARIANTS:
		c = cell(name, BASE)
		if c:
			L.append(f"| `{name}` | {what} | {fmt(c)} |")
	L += ["", "## Family 2: against v10 forced to the strong teams' roster per map", ""]
	c0 = cell(BASE, FORCED)
	if c0:
		L += [f"GOD v10 itself against it: {fmt(c0)}", ""]
	L += ["| Variant | Result | Paired margin vs v10's games [95%] | Wins variant / v10 on the same games |", "|---|---|---|---|"]
	for name, sets, what in VARIANTS:
		c = cell(name, FORCED)
		if c:
			pm = paired(name, BASE, FORCED)
			L.append(f"| `{name}` | {fmt(c)} | {pm['m']:+.1f} [{pm['lo']:+.1f}, {pm['hi']:+.1f}] | {pm['wa']} / {pm['wb']} of {pm['n']} |")
	out = os.path.join(ROOT, "experiments", "results", "teamplan", "batteries_v10.md")
	open(out, "w").write("\n".join(L) + "\n")
	print("\n".join(L))
	print(f"\nwrote {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
	main()
