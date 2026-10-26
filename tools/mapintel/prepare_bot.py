#!/usr/bin/env python3
"""Make a battery-ready copy of a bot: bots/DST = bots/SRC + tools/mapintel/cpp/mapintel/ in src/mapintel/ + the forced-roster call as the
first statement of its draft pick (MAPAnalysis.md 1.8: a GOD version may stand in for the user's new bot).

    python3 tools/mapintel/prepare_bot.py SRC DST [--func NAME] [--pick FUNC]       e.g.  prepare_bot.py god18 _mi_v18

Where the call goes (found in src/*.cpp unless --func is given):
  * GOD bots (v12 and later: `void play_draft_pick()` picks through `note_pick()`, defined above it, and `play_draft()` around it
    writes the draft memory after the pick): the first statement of play_draft_pick(), picking through note_pick(), so the bot still
    writes its draft memory (plans, TEAM / OWN blocks, mapintel's block) for the forced roster and plays that roster as it plays one it
    drafted itself;
  * any other bot: the first statement of `void play_draft()` (the cambc starter's name), picking with cambc::draft::pick().
--func NAME / --pick FUNC override that (FUNC takes a cambc::champion_draft). The source bot is not changed. Prints the copy's path and
the place of the call; exits non-zero when the function is not found exactly once."""
import argparse, glob, os, re, shutil, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def line(pick):
	return ("\tif (const int mi_p = mapintel::forced_pick(); mi_p >= 0) { " + pick + "(static_cast<cambc::champion_draft>(mi_p)); return; }"
			"  // tools/mapintel/prepare_bot.py\n")


def definitions(d, func):
	pat = re.compile(r"^void\s+" + re.escape(func) + r"\s*\(\s*\)\s*\n?\s*\{\s*\n", re.M)
	hits = []
	for f in sorted(glob.glob(os.path.join(d, "src", "*.cpp"))):
		hits += [(f, m) for m in pat.finditer(open(f).read())]
	return hits


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("src")
	ap.add_argument("dst")
	ap.add_argument("--func", default="", help="the draft function (default: play_draft_pick in a GOD bot, else play_draft)")
	ap.add_argument("--pick", default="", help="the pick call (default: note_pick in a GOD bot, else cambc::draft::pick)")
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
	func, pick = a.func, a.pick
	if not func:
		god = definitions(d, "play_draft_pick")
		if len(god) == 1:
			f, m = god[0]
			note = re.search(r"^\s*void\s+note_pick\s*\(", open(f).read(), re.M)
			if note and note.start() < m.start():
				func, pick = "play_draft_pick", pick or "note_pick"
		func = func or "play_draft"
	pick = pick or "cambc::draft::pick"
	hits = definitions(d, func)
	if len(hits) != 1:
		sys.exit(f"found `void {func}()` {len(hits)} times in bots/{a.dst}/src/*.cpp (need exactly one; pass --func NAME)")
	f, m = hits[0]
	txt = open(f).read()
	txt = '#include "mapintel/force_roster.h"\n' + txt[: m.end()] + line(pick) + txt[m.end():]
	open(f, "w").write(txt)
	print(f"bots/{a.dst} ready (forced-roster call added to {os.path.relpath(f, ROOT).replace(os.sep, '/')}: first statement of {func}(), "
		  f"picking with {pick}())")


if __name__ == "__main__":
	main()
