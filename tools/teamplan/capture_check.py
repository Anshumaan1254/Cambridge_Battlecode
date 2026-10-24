#!/usr/bin/env python3
"""Does the risk-matched capturer (capture.h, TEAMPLAN.md 4 U3') pick the body the top teams picked? (LEARNED check, step 3)

    node tools/teamplan/capture_ctx.mjs experiments/ladder_oct24/raw > CTX.jsonl
    python3 -I tools/teamplan/capture_check.py CTX.jsonl [--radius 3] [--walk-bank 25]

For every capture whose team had two or more living bodies within --radius of the capture tile when it began (5 rounds earlier), the
bodies there are the candidates and the capturer(s) the top team's choice. Each rule predicts one candidate:
  rule     capture.py choose_capturer (bags, items, walk to the tile, the same bank walk and danger for all: enemies within 8)
  nearest  the closest candidate (ties: lower index)
  goldx    the highest gold multiplier (ties: nearest)
  low bag  the smallest bag (ties: nearest)
  front    the highest kit front score (ties: nearest);  back: the lowest
A prediction is right when it is one of the capturers. Chance = mean of 1 / candidates."""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tp import capture, designs, kit, params  # noqa: E402


def cheb(a, b):
	return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("ctx")
	ap.add_argument("--radius", type=int, default=3)
	ap.add_argument("--walk-bank", type=int, default=25)
	ap.add_argument("--gold-gems", type=float, default=None, help="override params gold_gems (the rule's gem value of gold)")
	ap.add_argument("--items-half", type=float, default=None, help="override params items_half (diminishing value of gold with items)")
	a = ap.parse_args()
	des, C = designs.load()
	P = params.Params()
	if a.gold_gems is not None:
		P.gold_gems = a.gold_gems
	if a.items_half is not None:
		P.items_half = a.items_half
	K = {t: kit.compute_kit(des[t], C, P) for t in des}
	rows = [json.loads(l) for l in open(a.ctx) if l.strip()]
	# one event per (replay, round, team, tile cluster): the capturers of one reward
	ev = collections.defaultdict(list)
	for r in rows:
		key = (r["replay"], r["r"], r["team"])
		placed = False
		for k2 in [k for k in ev if k[:3] == key]:
			if cheb(ev[k2][0]["at"], r["at"]) <= 3:
				ev[k2].append(r)
				placed = True
				break
		if not placed:
			ev[key + (len([k for k in ev if k[:3] == key]),)].append(r)
	stats = collections.defaultdict(lambda: collections.Counter())
	chance = collections.defaultdict(float)
	for k, rs in ev.items():
		r0 = rs[0]
		at = r0["at"]
		team = r0["team"]
		cands = [c for c in r0["before"] if c[1] == team and c[7] and cheb((c[3], c[4]), at) <= a.radius]
		if len(cands) < 2:
			continue
		takers = {r["who"] for r in rs}
		gems, gold = sum(r["gems"] for r in rs), sum(r["gold"] for r in rs)
		danger = sum(1 for c in r0["before"] if c[1] != team and c[7] and cheb((c[3], c[4]), at) <= 8)
		team_n = sum(1 for c in r0["before"] if c[1] == team)
		cs = [capture.Cand(c[0], c[8], sum(q for _, q in c[11]), cheb((c[3], c[4]), at), a.walk_bank, float(danger), K[c[2]]) for c in cands]
		i, _ = capture.choose_capturer(cs, gems, gold, team_n, C, P)
		near = sorted(cands, key=lambda c: (cheb((c[3], c[4]), at), c[0]))
		pick = {
			"rule": cands[i][0],
			"nearest": near[0][0],
			"goldx": max(near, key=lambda c: K[c[2]].gold_mult)[0],
			"low bag": min(near, key=lambda c: c[8])[0],
			"front": max(near, key=lambda c: K[c[2]].front)[0],
			"back": min(near, key=lambda c: K[c[2]].front)[0],
		}
		kind = "gold-only" if gems == 0 else "gems"
		for grp in ("all", kind):
			stats[grp]["events"] += 1
			chance[grp] += 1.0 / len(cands)
			for name, b in pick.items():
				stats[grp][name] += b in takers
	print(f"capture events with 2+ candidates within {a.radius} when the capture began (25 raw top-team replays):")
	for grp in ("all", "gems", "gold-only"):
		s = stats[grp]
		n = s["events"]
		if not n:
			continue
		print(f"  {grp:9s} {n:5d} events | chance {100 * chance[grp] / n:4.1f}% | " +
			  " | ".join(f"{name} {100 * s[name] / n:4.1f}%" for name in ("rule", "nearest", "goldx", "low bag", "front", "back")))


if __name__ == "__main__":
	main()
