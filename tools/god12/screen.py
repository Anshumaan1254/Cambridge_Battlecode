#!/usr/bin/env python3
"""GOD v12 screens (bots/god12 variants, tools/variant.sh): head-to-head against GOD v10 (bots/god) and paired against v10's own games
versus the forced strong-team rosters (tools/teamplan/make_forced_v10.py: _tp_v10F, _tp_v10F1..7; v10's games are the ledger cells
_tp_v10ref_vs__tp_v10F<k>, which bots/god12 with every switch off replays exactly, 80 of 80).

    python3 -I tools/god12/screen.py VARIANT... [--slots 0,1,...]

Rows: the current sources' rows of experiments/results/ledger_v3_0_4 (tools/ledger.py src_hash). Margin = our banked gems minus
theirs per game; paired = the variant's margin minus v10's in the same game (map, side, opponent), mean with a bootstrap 95% interval;
turned = games the variant won where v10 lost / the reverse."""
import argparse, json, os, random, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import ledger  # noqa: E402

D = os.path.join(ROOT, "experiments/results/ledger_v3_0_4")


def rows(bot, opp, bh=None):
	p = os.path.join(D, f"{bot}_vs_{opp}.jsonl")
	if not os.path.exists(p):
		return {}
	bh = bh or ledger.src_hash(bot)
	oh = ledger.src_hash(opp) if os.path.isdir(os.path.join(ROOT, "bots", opp)) else None
	out = {}
	for l in open(p):
		r = json.loads(l)
		if r["bot_hash"] != bh or (oh and r["opp_hash"] != oh):
			continue
		out[(r["map"], r["side"])] = r
	return out


def margin(r):
	g = r["gems"]
	return (g[0] - g[1]) if isinstance(g, list) else 0


def boot(xs, n=2000):
	if not xs:
		return 0, 0, 0
	rnd = random.Random(7)
	ms = sorted(sum(rnd.choice(xs) for _ in xs) / len(xs) for _ in range(n))
	return sum(xs) / len(xs), ms[int(0.025 * n)], ms[int(0.975 * n)]


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("variants", nargs="+")
	ap.add_argument("--slots", default="0")
	ap.add_argument("--h2h", default="god", help="head-to-head opponent (default god = GOD v10)")
	a = ap.parse_args()
	slots = [int(x) for x in a.slots.split(",")]
	ref_h = json.loads(open(os.path.join(D, "_tp_v10ref_vs__tp_v10F.jsonl")).readline())["bot_hash"]
	print(f"| variant | h2h vs {a.h2h}: wins | margin [95%] | faults | paired vs v10, rosters " + ",".join(map(str, slots)) + ": margin [95%] | turned | games |")
	print("|---|---|---|---|---|---|---|")
	for v in a.variants:
		h = rows(v, a.h2h)
		w = sum(1 for r in h.values() if r["win"])
		m = boot([margin(r) for r in h.values()])
		faults = sum(int(r.get("faults", 0) or 0) for r in h.values())
		xs, gain, loss, n = [], 0, 0, 0
		for k in slots:
			opp = "_tp_v10F" + ("" if k == 0 else str(k))
			va, ra = rows(v, opp), rows("_tp_v10ref", opp, ref_h)
			for key, r in va.items():
				if key not in ra:
					continue
				b = ra[key]
				xs.append(margin(r) - margin(b))
				gain += 1 if r["win"] and not b["win"] else 0
				loss += 1 if b["win"] and not r["win"] else 0
				n += 1
				faults += int(r.get("faults", 0) or 0)
		pm = boot(xs)
		print(f"| {v} | {w}/{len(h)} | {m[0]:+.1f} [{m[1]:+.0f}, {m[2]:+.0f}] | {faults} | {pm[0]:+.1f} [{pm[1]:+.0f}, {pm[2]:+.0f}] | {gain} / {loss} | {n} |")


if __name__ == "__main__":
	main()
