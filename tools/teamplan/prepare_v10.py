#!/usr/bin/env python3
"""The GOD v10 test copy of tools/teamplan (TEAMPLAN.md section 9): bots/god/src + tools/teamplan/cpp/teamplan + v10_adapter.patch, with
optional switch values, built in release mode. bots/god itself is never touched.

    python3 -I tools/teamplan/prepare_v10.py [--name _tp_v10] [KEY=VALUE ...]    e.g. tp_focus=1 tp_tb_cap=150

KEY=VALUE sets a field of the copy's params.h (the tp_* switches or any other GOD parameter). With no KEY=VALUE every tp_* switch is 0
and the copy plays v10's games (checked: 80 of 80 identical, TEAMPLAN.md section 10)."""
import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--name", default="_tp_v10")
	ap.add_argument("--no-build", action="store_true")
	ap.add_argument("sets", nargs="*")
	a = ap.parse_args()
	d = os.path.join(ROOT, "bots", a.name)
	shutil.rmtree(d, ignore_errors=True)
	os.makedirs(d)
	shutil.copytree(os.path.join(ROOT, "bots", "god", "src"), os.path.join(d, "src"))
	gi = os.path.join(ROOT, "bots", "legend", ".gitignore")
	if os.path.exists(gi):
		shutil.copy(gi, d)
	shutil.copytree(os.path.join(HERE, "cpp", "teamplan"), os.path.join(d, "src", "teamplan"))
	r = subprocess.run(["patch", "-p1", "--no-backup-if-mismatch", "-i", os.path.join(HERE, "v10_adapter.patch")], cwd=os.path.join(d, "src"),
					   capture_output=True, text=True)
	if r.returncode != 0:
		sys.exit("v10_adapter.patch does not apply to bots/god/src (GOD changed?):\n" + r.stdout + r.stderr)
	p = os.path.join(d, "src", "params.h")
	s = open(p).read()
	for kv in a.sets:
		k, v = kv.split("=", 1)
		s, n = re.subn(r"^(\s*[a-z]+ " + re.escape(k) + r" = )[^;]*;", lambda m: m.group(1) + v + ";", s, flags=re.M)
		if n != 1:
			sys.exit(f"unknown parameter {k}")
	open(p, "w").write(s)
	if not a.no_build:
		r = subprocess.run(["cambc", "build", a.name, "--release"], cwd=ROOT, capture_output=True, text=True)
		if r.returncode != 0:
			sys.exit("build failed:\n" + (r.stdout + r.stderr)[-3000:])
	print(f"bots/{a.name} ready" + (f" ({' '.join(a.sets)})" if a.sets else " (all tp_* switches 0 = v10)"))


if __name__ == "__main__":
	main()
