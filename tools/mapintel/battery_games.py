#!/usr/bin/env python3
"""A battery archive of run_battery.sh (unpacked) -> games.csv for draft_learn.py --battery (MAPAnalysis.md 7.1 "Open").

    python3 -I tools/mapintel/battery_games.py BATTERY_DIR [--out BATTERY_DIR/games.csv]
    (BATTERY_DIR = the archive's battery/ folder: meta.json, ledger/*.jsonl, keep/<bot>_vs_<opp>/<map>_<side>.json)

One row per ledger game of the cells the meta lists (every ledger file when the meta lists none): battery (roster when the meta lists
the cell as a roster cell, else outcome), bot, opp, map, side, the two rosters as the engine drafted them (from the kept statistics:
champions in draft-pick order, Cassi and Issac as one pick), win, loss, rounds, gems, gold, deaths, kills, faults. Per (map, side) the
LAST ledger row counts (the ledger's latest game: a --quick run's rows of an earlier build come first). Rows whose statistics were not
kept get empty rosters (draft_learn.py and make_dataset.py skip them)."""
import argparse, csv, glob, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import PICK_NAMES  # noqa: E402

FIELDS = ["battery", "bot", "opp", "map", "side", "roster_bot", "roster_opp", "win", "loss", "rounds", "gems_bot", "gems_opp", "gold_bot",
		  "gold_opp", "deaths_bot", "deaths_opp", "kills_bot", "kills_opp", "faults"]


def rosters(stats):
	"""(team A roster, team B roster) as '/'-joined draft names in pick order."""
	out = {"teamA": [], "teamB": []}
	for c in sorted(stats["roster"]["champions"], key=lambda c: c["draftPick"]):
		n = "Cassi & Issac" if c["name"] in ("Cassi", "Issac") else c["name"]
		if n not in out[c["team"]]:
			out[c["team"]].append(n)
	for t in out.values():
		bad = [n for n in t if n not in PICK_NAMES]
		if bad:
			sys.exit(f"unknown champion names {bad}")
	return "/".join(out["teamA"]), "/".join(out["teamB"])


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("dir")
	ap.add_argument("--out", default="")
	a = ap.parse_args()
	meta = json.load(open(os.path.join(a.dir, "meta.json")))
	kind = {(c["bot"], c["opp"]): c["battery"] for c in meta["cells"]}
	cells = {f"{b}_vs_{o}.jsonl" for b, o in kind}
	rows, missing = [], 0
	for f in sorted(glob.glob(os.path.join(a.dir, "ledger", "*.jsonl"))):
		if cells and os.path.basename(f) not in cells:
			continue
		last = {}
		for line in open(f):
			if line.strip():
				r = json.loads(line)
				last[(r["map"], r["side"])] = r
		for _, r in sorted(last.items()):
			sp = os.path.join(a.dir, "keep", f"{r['bot']}_vs_{r['opp']}", f"{r['map']}_{r['side']}.json")
			ra = rb = ""
			if os.path.exists(sp):
				ra, rb = rosters(json.load(open(sp)))
			else:
				missing += 1
			mine, theirs = (ra, rb) if r["side"] == "A" else (rb, ra)
			rows.append({"battery": kind.get((r["bot"], r["opp"]), "outcome"), "bot": r["bot"], "opp": r["opp"], "map": r["map"], "side": r["side"],
						 "roster_bot": mine, "roster_opp": theirs, "win": int(r["win"]), "loss": int(r["loss"]), "rounds": r["rounds"],
						 "gems_bot": r["gems"][0], "gems_opp": r["gems"][1], "gold_bot": r["gold"][0], "gold_opp": r["gold"][1],
						 "deaths_bot": r["deaths"][0], "deaths_opp": r["deaths"][1], "kills_bot": r["kills"][0], "kills_opp": r["kills"][1],
						 "faults": r["faults"]})
	out = a.out or os.path.join(a.dir, "games.csv")
	with open(out, "w", newline="") as f:
		w = csv.DictWriter(f, fieldnames=FIELDS)
		w.writeheader()
		w.writerows(rows)
	print(f"{len(rows)} games -> {out}" + (f" ({missing} without kept statistics: empty rosters)" if missing else ""))


if __name__ == "__main__":
	main()
