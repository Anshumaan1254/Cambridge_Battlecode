#!/usr/bin/env python3
"""The kit table of tools/teamplan (kit.h through its Python twin) for every champion design of the engine: a report, not an input.

    python3 -I tools/teamplan/kit_table.py [--designs FILE] [--md]"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tp import designs, kit, params  # noqa: E402

NAMES = ["Ryth", "Vesper Vale", "Vendetta", "Cassi", "Issac", "Stellar", "Prism", "Marcella", "Willow", "Ren", "Varg", "Tavi", "Heart of Ruin"]
COLS = [("melee", "melee", "{:d}"), ("dps", "dps", "{:.1f}"), ("camp_dps", "camp dps", "{:.1f}"), ("ehp", "eff. health", "{:.0f}"),
		("stun", "stun/rnd", "{:.3f}"), ("reach", "reach", "{:.1f}"), ("gold_mult", "gold x", "{:.2f}"), ("tribute_gold", "tribute gold/gem", "{:.0f}"),
		("w_gold", "value of 1k gold", "{:.3f}"), ("exposure", "exposure", "{:.2f}"), ("front", "front", "{:.0f}")]


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--designs", default=designs.DEFAULT)
	ap.add_argument("--md", action="store_true")
	a = ap.parse_args()
	des, C = designs.load(a.designs)
	P = params.Params()
	rows = []
	for t in sorted(des):
		k = kit.compute_kit(des[t], C, P)
		vals = []
		for f, _, fmt in COLS:
			v = getattr(k, f)
			vals.append(fmt.format(v * 1000 if f == "w_gold" else v))
		rows.append([NAMES[t] if t < len(NAMES) else str(t)] + vals)
	head = ["Champion"] + [c[1] for c in COLS]
	if a.md:
		print("| " + " | ".join(head) + " |")
		print("|" + "---|" * len(head))
		for r in rows:
			print("| " + " | ".join(r) + " |")
	else:
		w = [max(len(x[i]) for x in rows + [head]) for i in range(len(head))]
		for r in [head] + rows:
			print("  ".join(x.rjust(w[i]) for i, x in enumerate(r)))


if __name__ == "__main__":
	main()
