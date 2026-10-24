#!/usr/bin/env python3
"""Check the economy model's unopposed pace (plans.pace) against a bot's measured unopposed pace: the outcome battery's games against
the idle bot (SIMULATED; GOD v10 as the stand-in, MAPAnalysis 1.8). For every map and side the model is run with the roster the bot
actually drafted in that game (read from the kept statistics). Prints Spearman's rank correlation (target >= 0.8, MAPAnalysis 5.3c)
over the games and over the maps (mean of both sides), and writes a CSV.

    python3 -I tools/mapintel/validate_pace.py WORK [--bot _mi_v10] [--opp _mi_idle] [--out experiments/results/mapintel/pace_check.csv]
WORK = the battery work folder (ledger/ and keep/)."""
import argparse, csv, json, os, sys

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mapdata  # noqa: E402
import plans as P  # noqa: E402
from engine import PICK_NAMES  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def picks_of(stats, team):
	names = [d["champion"] for d in stats["roster"]["draft"] if d["team"] == team]
	return [PICK_NAMES.index(n) for n in names]


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("work")
	ap.add_argument("--bot", default="_mi_v10")
	ap.add_argument("--opp", default="_mi_idle")
	ap.add_argument("--out", default=os.path.join(ROOT, "experiments/results/mapintel/pace_check.csv"))
	a = ap.parse_args()
	rows = [json.loads(l) for l in open(os.path.join(a.work, "ledger", f"{a.bot}_vs_{a.opp}.jsonl"))]
	out = []
	ctxs = {}
	for r in rows:
		st = json.load(open(os.path.join(a.work, "keep", f"{a.bot}_vs_{a.opp}", f"{r['map']}_{r['side']}.json")))
		team = 0 if r["side"] == "A" else 1
		picks = picks_of(st, "teamA" if team == 0 else "teamB")
		if r["map"] not in ctxs:
			ctxs[r["map"]] = P.Ctx(mapdata.load(r["map"]))
		m = P.pace(ctxs[r["map"]], team, picks)
		real = r["rounds"] if r["win"] and r["gems"][0] >= 1000 else 2000
		out.append({"map": r["map"], "side": r["side"], "roster": "/".join(PICK_NAMES[p] for p in picks), "bot_rounds": real,
					"bot_gems": r["gems"][0], "model_pace": m["pace"] or 2000, "model_banked": m["banked"]})
		print(f"{r['map']:22s} {r['side']} bot {real:5d} model {m['pace'] or 2000:5d}   {out[-1]['roster']}", flush=True)
	os.makedirs(os.path.dirname(a.out), exist_ok=True)
	with open(a.out, "w", newline="") as f:
		w = csv.DictWriter(f, fieldnames=list(out[0]))
		w.writeheader()
		w.writerows(out)
	b = np.array([o["bot_rounds"] for o in out])
	m = np.array([o["model_pace"] for o in out])
	print(f"games: Spearman {spearmanr(b, m)[0]:.3f} (n={len(out)}); median model/bot {np.median(m / b):.2f}")
	maps = sorted({o["map"] for o in out})
	bm = [np.mean([o["bot_rounds"] for o in out if o["map"] == mp]) for mp in maps]
	mm = [np.mean([o["model_pace"] for o in out if o["map"] == mp]) for mp in maps]
	print(f"maps:  Spearman {spearmanr(bm, mm)[0]:.3f} (n={len(maps)})")


if __name__ == "__main__":
	main()
