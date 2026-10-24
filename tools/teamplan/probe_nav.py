#!/usr/bin/env python3
"""Navigation fuel probe (TEAMPLAN.md section 6): builds bots/_tp_navprobe (git-ignored) from tools/teamplan/cpp/probe_nav/main.cpp, plays
4 rounds per map in release mode (as on the platform), and prints the median fuel of each measurement per map.

    python3 -I tools/teamplan/probe_nav.py [--maps 'maps/official/01big-world.map26a,...'] [--out FILE.md]

A measurement whose turn ran out of fuel resumes in the next round and reads negative: it is reported as 'rollover'."""
import argparse
import glob
import os
import re
import shutil
import statistics as st
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
KEYS = ["walls_export", "field_full", "field_r3", "field_to", "gets49", "units_walls", "field_units", "bfs7_loop", "bfs7_unrolled"]


def build(name="_tp_navprobe"):
	d = os.path.join(ROOT, "bots", name)
	shutil.rmtree(os.path.join(d, "src"), ignore_errors=True)
	os.makedirs(os.path.join(d, "src"), exist_ok=True)
	shutil.copy(os.path.join(ROOT, "tools/teamplan/cpp/probe_nav/main.cpp"), os.path.join(d, "src", "main.cpp"))
	r = subprocess.run(["cambc", "build", name, "--release"], cwd=ROOT, capture_output=True, text=True)
	if r.returncode != 0:
		sys.exit("probe build failed:\n" + r.stdout[-3000:] + r.stderr[-3000:])
	return name


def stdout_of(replay):
	r = subprocess.run(["node", os.path.join(ROOT, "tools/strategy_v2/s13/stdout.mjs"), replay, "team-a.stdout"], capture_output=True, text=True)
	return r.stdout.replace("\x00", "")


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--maps", default="maps/official/01big-world.map26a,maps/official/01islands.map26a,maps/official/00ambush.map26a,"
					"maps/official/01gold-rush.map26a,maps/official/00lanes.map26a")
	ap.add_argument("--out", default="")
	a = ap.parse_args()
	maps = [m for g in a.maps.split(",") for m in sorted(glob.glob(os.path.join(ROOT, g)))]
	name = build()
	rows = []
	with tempfile.TemporaryDirectory() as tmp:
		for m in maps:
			out = os.path.join(tmp, os.path.basename(m))
			subprocess.run(["cambc", "run", name, name, "--map", m, "--rounds", "4", "--release", "-o", out], cwd=ROOT, capture_output=True, text=True)
			reps = glob.glob(os.path.join(out, "*.repl26a"))
			vals = {k: [] for k in KEYS}
			size = "?"
			for line in (stdout_of(reps[0]) if reps else "").splitlines():
				if not line.startswith("TP nav "):
					continue
				size = line.split()[2]
				for k in KEYS:
					mm = re.search(rf"\b{k} (-?\d+)", line)
					if mm:
						vals[k].append(int(mm.group(1)))
			rows.append((os.path.basename(m).replace(".map26a", ""), size, {k: (("rollover" if min(v) < 0 else f"{st.median(v):.0f}") if v else "-") for k, v in vals.items()}))
	L = ["| Map | Size | " + " | ".join(KEYS) + " |", "|---|---|" + "---|" * len(KEYS)]
	for n, s, v in rows:
		L.append(f"| {n} | {s} | " + " | ".join(v[k] for k in KEYS) + " |")
	text = "\n".join(L) + "\n"
	if a.out:
		open(a.out, "w").write(text)
	print(text)


if __name__ == "__main__":
	main()
