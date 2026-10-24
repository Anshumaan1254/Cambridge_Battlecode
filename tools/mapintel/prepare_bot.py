#!/usr/bin/env python3
"""Make a battery-ready copy of a bot: bots/DST = bots/SRC + tools/mapintel/cpp/mapintel/ in src/mapintel/ + the forced-roster call as the
first statement of its draft function (MAPAnalysis.md 1.8: GOD v10 may stand in for the user's new bot).

    python3 tools/mapintel/prepare_bot.py SRC DST [--func play_draft]       e.g.  prepare_bot.py god _mi_v10

The draft function is found as `void <func>()` in src/*.cpp (default play_draft: the cambc starter's and GOD v10's name). The source bot
is not changed. Prints the copy's path; exits non-zero when the function is not found exactly once."""
import argparse, glob, os, re, shutil, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LINE = ("\tif (const int mi_p = mapintel::forced_pick(); mi_p >= 0) { cambc::draft::pick(static_cast<cambc::champion_draft>(mi_p)); return; }"
		"  // tools/mapintel/prepare_bot.py\n")


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("src")
	ap.add_argument("dst")
	ap.add_argument("--func", default="play_draft")
	a = ap.parse_args()
	s, d = os.path.join(ROOT, "bots", a.src), os.path.join(ROOT, "bots", a.dst)
	if not os.path.isdir(os.path.join(s, "src")):
		sys.exit(f"bots/{a.src}/src does not exist")
	shutil.rmtree(os.path.join(d, "src"), ignore_errors=True)
	os.makedirs(d, exist_ok=True)
	shutil.copytree(os.path.join(s, "src"), os.path.join(d, "src"))
	for f in (".gitignore", ".clangd"):
		if os.path.exists(os.path.join(s, f)):
			shutil.copy(os.path.join(s, f), os.path.join(d, f))
	shutil.rmtree(os.path.join(d, "src", "mapintel"), ignore_errors=True)
	shutil.copytree(os.path.join(ROOT, "tools/mapintel/cpp/mapintel"), os.path.join(d, "src", "mapintel"))
	pat = re.compile(r"^void\s+" + re.escape(a.func) + r"\s*\(\s*\)\s*\n?\s*\{\s*\n", re.M)
	hits = []
	for f in sorted(glob.glob(os.path.join(d, "src", "*.cpp"))):
		txt = open(f).read()
		hits += [(f, m) for m in pat.finditer(txt)]
	if len(hits) != 1:
		sys.exit(f"found `void {a.func}()` {len(hits)} times in bots/{a.dst}/src/*.cpp (need exactly one; pass --func NAME)")
	f, m = hits[0]
	txt = open(f).read()
	txt = '#include "mapintel/force_roster.h"\n' + txt[: m.end()] + LINE + txt[m.end():]
	open(f, "w").write(txt)
	print(f"bots/{a.dst} ready (forced-roster call added to {os.path.relpath(f, ROOT)})")


if __name__ == "__main__":
	main()
