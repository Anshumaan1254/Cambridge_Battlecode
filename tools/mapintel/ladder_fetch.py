#!/usr/bin/env python3
"""Current-patch ladder data for the map model: match lists and replays of the top teams (run on the user's machine).

    cambc login                                            # the user, once (never scripted)
    python3 tools/mapintel/ladder_fetch.py [--top 50] [--strong 20] [--max-per-team 300] [--per-map 15] [--max-mb 60]
                                           [--min-engine 1.0.3] [--kinds ranked] [--work DIR] [--out-dir DIR] [--jobs 3]
    python3 tools/mapintel/ladder_fetch.py --dry-run --ladder LADDER.json LIST.jsonl [...]   # no platform calls

Steps (each prints what it did; a step that produces nothing stops the script with an error):
  1. the ladder (`cambc ladder --json`, pages of 100) -> WORK/ladder.json; the top --top teams;
  2. each team's recent matches (`cambc matches list --team ID --kind K --json`, paginated, at most --max-per-team), merged by
     matchId -> WORK/lists/<teamId8>.jsonl (re-runs merge, so a cut run resumes);
  3. filter: finished, kind in --kinds, map in maps/official (platform names use '_' where the files use '-'), and BOTH teams'
     engineVersion >= --min-engine -> WORK/matches_current.jsonl (the draft dataset: picks, sides, results, end reasons);
  4. team strength on those games -> WORK/teams.json; the --strong strongest teams by ladder rating form the strong set;
  5. replay selection, spread over the 40 maps: per map at most --per-map games, games between two strong teams first, then games
     with one strong team, newest first; maps are filled round-robin so every map gets games before any map gets many;
  6. replay downloads (`cambc matches download ID -o FILE`, --jobs threads, existing files skipped) -> WORK/replays/, stopping once
     the gzip-compressed total passes --max-mb;
  7. one archive OUT_DIR/mapintel_ladder_<UTC stamp>.tar.gz (ladder, lists, the filtered matches, teams, the selection, replays) and
     its size. Upload that file.

Standard library only; works with Python 3.8+ on Linux, macOS and Windows (Git Bash / MSYS, cmd)."""
import argparse
import concurrent.futures as cf
import gzip
import json
import os
import random
import re
import subprocess
import sys
import tarfile
import threading
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

_lock = threading.Lock()
_last = [0.0]
MIN_GAP = float(os.environ.get("LIVE_MIN_GAP", "0.35"))


def die(msg, code=1):
	sys.stderr.write("ERROR: " + msg + "\n")
	sys.exit(code)


def cambc(args, retries=40):
	"""Run `cambc ARGS`; retry while the platform says busy / rate limited / unavailable (it names the wait). (rc, stdout, stderr)."""
	r = None
	for attempt in range(retries + 1):
		with _lock:
			wait = _last[0] + MIN_GAP - time.time()
			if wait > 0:
				time.sleep(wait)
			_last[0] = time.time()
		try:
			r = subprocess.run(["cambc"] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
		except FileNotFoundError:
			die("`cambc` is not on PATH (pip install cambc==3.0.5)")
		msg = (r.stderr or "") + (r.stdout if r.returncode else "")
		low = msg.lower()
		busy = r.returncode != 0 and ("429" in msg or "503" in msg or "busy" in low or "rate limit" in low or "unavailable" in low)
		if not busy or attempt == retries:
			return r.returncode, r.stdout, r.stderr
		m = re.search(r"retry after (\d+(?:\.\d+)?) second", msg)
		time.sleep((float(m.group(1)) if m else 2.0) + random.random() * 0.5)
	return r.returncode, r.stdout, r.stderr


def norm_map(name):
	return name.lower().replace("-", "_")


def official_maps():
	d = os.path.join(ROOT, "maps", "official")
	names = sorted(f[:-7] for f in os.listdir(d) if f.endswith(".map26a")) if os.path.isdir(d) else []
	if not names:
		die("no maps in maps/official (git pull the repository first)")
	return {norm_map(n): n for n in names}


def vtuple(v):
	try:
		return tuple(int(x) for x in str(v).split("."))
	except ValueError:
		return ()


def fetch_ladder(top):
	teams, page = [], 1
	while len(teams) < top:
		rc, so, se = cambc(["ladder", "--json", "--limit", "100", "--page", str(page)])
		if rc != 0:
			die("`cambc ladder` failed (run `cambc login` first?):\n" + se.strip())
		d = json.loads(so)
		got = d.get("teams", [])
		teams += got
		if len(got) < 100:
			break
		page += 1
	return {"fetched": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "teams": teams}


def fetch_list(team_id, kind, maxn, out):
	"""Paginated `cambc matches list`; merged with an existing OUT file by matchId (newest first)."""
	seen, rows, cursor = set(), [], None
	while len(rows) < maxn:
		cmd = ["matches", "list", "--json", "--limit", str(min(100, maxn - len(rows))), "--team", team_id]
		if kind:
			cmd += ["--kind", kind]
		if cursor:
			cmd += ["--cursor", cursor]
		rc, so, se = cambc(cmd)
		if rc != 0:
			sys.stderr.write("  matches list failed for %s: %s\n" % (team_id, se.strip()[:200]))
			break
		d = json.loads(so)
		ms = d.get("matches", [])
		for m in ms:
			if m["matchId"] not in seen:
				seen.add(m["matchId"])
				rows.append(m)
		cursor = d.get("nextCursor") or d.get("cursor") or d.get("next")
		if not ms or not cursor:
			break
	old = {}
	if os.path.exists(out):
		for line in open(out, encoding="utf-8"):
			if line.strip():
				m = json.loads(line)
				old[m["matchId"]] = m
	for m in rows:
		old[m["matchId"]] = m
	allm = sorted(old.values(), key=lambda m: m.get("createdAt", ""), reverse=True)
	with open(out, "w", encoding="utf-8") as f:
		for m in allm:
			f.write(json.dumps(m, ensure_ascii=False) + "\n")
	return len(rows), len(allm)


def split_file(path, mb):
	"""Cut path into path.part00, .part01, ... of at most mb megabytes (joined back with `cat path.part* > path`)."""
	parts, i = [], 0
	with open(path, "rb") as f:
		while True:
			b = f.read(int(mb * 1024 * 1024))
			if not b:
				break
			p = "%s.part%02d" % (path, i)
			open(p, "wb").write(b)
			parts.append(p)
			i += 1
	return parts


def main():
	ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	ap.add_argument("lists", nargs="*", help="--dry-run: match-list JSONL files to use instead of fetching")
	ap.add_argument("--top", type=int, default=50, help="teams of the ladder whose match lists are fetched")
	ap.add_argument("--strong", type=int, default=20, help="the strong set (by ladder rating) for replay selection")
	ap.add_argument("--max-per-team", type=int, default=300)
	ap.add_argument("--per-map", type=int, default=15)
	ap.add_argument("--max-mb", type=float, default=60.0, help="stop downloading once the gzip-compressed replays pass this")
	ap.add_argument("--min-engine", default="1.0.3")
	ap.add_argument("--kinds", default="ranked", help="comma list of match kinds to keep (ranked, unranked, tournament)")
	ap.add_argument("--work", default=os.path.join(ROOT, "mapintel_work", "ladder"))
	ap.add_argument("--out-dir", default=ROOT)
	ap.add_argument("--jobs", type=int, default=3)
	ap.add_argument("--ladder", default="", help="use this ladder JSON (a `cambc ladder --json` dump or a list of teams)")
	ap.add_argument("--dry-run", action="store_true", help="no platform calls: filter and select from the given lists, print the plan")
	ap.add_argument("--no-fetch", action="store_true", help="reuse WORK/lists from an earlier run")
	ap.add_argument("--team", default="", help="one-team mode: comma list of team ids; fetch only their match lists and download every one of "
					"their kept matches, newest first, up to --max-mb (e.g. --team 1890540d-1ffc-4847-adbf-d0d08772f268 for Intercontinental Fish)")
	ap.add_argument("--split-mb", type=float, default=20.0, help="also cut the archive into parts of this size for uploading (0 = no parts)")
	a = ap.parse_args()
	kinds = set(k.strip() for k in a.kinds.split(",") if k.strip())
	minv = vtuple(a.min_engine)
	os.makedirs(os.path.join(a.work, "lists"), exist_ok=True)
	os.makedirs(os.path.join(a.work, "replays"), exist_ok=True)
	offi = official_maps()
	print("official maps in the repository: %d" % len(offi))

	# 0. cambc version and login (the ladder call needs a login; the user runs `cambc login` themself)
	if not a.dry_run:
		rc, so, se = cambc(["--version"])
		ver = so.strip().split()[-1] if so.strip() else "?"
		print("cambc %s" % ver)
		if vtuple(ver) < (3, 0, 5):
			print("WARNING: cambc %s is older than 3.0.5 (pip install cambc==3.0.5); continuing" % ver)

	# 1. ladder
	if a.ladder:
		lad = json.load(open(a.ladder, encoding="utf-8"))
		if isinstance(lad, list):
			lad = {"teams": lad}
	elif a.dry_run:
		die("--dry-run needs --ladder FILE")
	else:
		lad = fetch_ladder(a.top)
	teams = sorted([t for t in lad.get("teams", []) if t.get("rank")], key=lambda t: t["rank"])[: a.top]
	if not teams:
		die("the ladder has no teams")
	json.dump(lad, open(os.path.join(a.work, "ladder.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
	print("1. ladder: %d teams taken (rank %d-%d)" % (len(teams), teams[0]["rank"], teams[-1]["rank"]))
	focus = [x.strip() for x in a.team.split(",") if x.strip()]
	if focus:
		known = {t["teamId"]: t for t in lad.get("teams", [])}
		teams = [known.get(i, {"teamId": i, "name": i[:8], "rank": None}) for i in focus]
		print("1. one-team mode: " + ", ".join("%s (rank %s)" % (t.get("name", "?"), t.get("rank")) for t in teams))

	# 2. match lists
	list_files = []
	if a.dry_run:
		list_files = a.lists
		if not list_files:
			die("--dry-run needs match-list files")
	else:
		for t in teams:
			out = os.path.join(a.work, "lists", t["teamId"][:8] + ".jsonl")
			list_files.append(out)
			if a.no_fetch and os.path.exists(out):
				continue
			got = 0
			for kind in sorted(kinds):
				n, tot = fetch_list(t["teamId"], kind, a.max_per_team, out)
				got += n
			print("2. [%2s] %-30s %4d fetched" % (t.get("rank"), t.get("name", "?")[:30], got), flush=True)
	rows, seen = [], set()
	for f in list_files:
		for line in open(f, encoding="utf-8"):
			if not line.strip():
				continue
			m = json.loads(line)
			if m["matchId"] not in seen:
				seen.add(m["matchId"])
				rows.append(m)
	print("2. match lists: %d distinct matches" % len(rows))
	if not rows:
		die("no matches fetched")

	# 3. filter: current engine on both sides, official maps, kinds, finished
	why = {"status": 0, "kind": 0, "map": 0, "engine": 0}
	cur = []
	for m in rows:
		if m.get("status") != "finished":
			why["status"] += 1
			continue
		if m.get("kind") not in kinds:
			why["kind"] += 1
			continue
		if norm_map(m.get("map", "")) not in offi:
			why["map"] += 1
			continue
		if len(m.get("teams", [])) != 2 or any(vtuple(t.get("engineVersion")) < minv for t in m["teams"]):
			why["engine"] += 1
			continue
		m["mapFile"] = offi[norm_map(m["map"])]
		cur.append(m)
	cur.sort(key=lambda m: m.get("createdAt", ""), reverse=True)
	with open(os.path.join(a.work, "matches_current.jsonl"), "w", encoding="utf-8") as f:
		for m in cur:
			f.write(json.dumps(m, ensure_ascii=False) + "\n")
	print("3. kept %d current-patch matches on official maps (dropped: %s)" % (len(cur), why))
	if not cur:
		die("no match passed the filter (engine >= %s, kinds %s, official maps)" % (a.min_engine, sorted(kinds)))

	# 4. team strength on the kept games
	rank = {t["teamId"]: t for t in teams}
	stat = {}
	for m in cur:
		for t in m["teams"]:
			s = stat.setdefault(t["teamId"], {"teamId": t["teamId"], "name": t.get("name", ""), "games": 0, "wins": 0})
			s["games"] += 1
			s["wins"] += t.get("result") == "win"
	for s in stat.values():
		r = rank.get(s["teamId"], {})
		s["rank"], s["rating"] = r.get("rank"), r.get("rating")
		s["wr"] = round(s["wins"] / s["games"], 3) if s["games"] else None
	strong = set(t["teamId"] for t in sorted(teams, key=lambda t: -(t.get("rating") or 0))[: a.strong])
	json.dump({"strong": sorted(strong), "teams": sorted(stat.values(), key=lambda s: (s["rank"] or 999, -s["games"]))},
			open(os.path.join(a.work, "teams.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
	print("4. teams in the kept games: %d; strong set %d" % (len(stat), len(strong)))

	# 5. selection spread over the maps
	def tier(m):
		return sum(t["teamId"] in strong for t in m["teams"])

	by_map = {}
	for m in cur:
		if tier(m) > 0:
			by_map.setdefault(m["mapFile"], []).append(m)
	for v in by_map.values():
		v.sort(key=lambda m: -tier(m))  # stable sort: within a tier newest first (cur is newest first)
	order, k = [], 0
	if focus:
		order = [m for m in cur if any(t["teamId"] in focus for t in m["teams"])]  # every match of the team(s), newest first
		by_map = {}
	while not focus:
		added = False
		for mp in sorted(by_map):
			if k < min(a.per_map, len(by_map[mp])):
				order.append(by_map[mp][k])
				added = True
		if not added:
			break
		k += 1
	both = sum(tier(m) == 2 for m in order)
	if focus:
		print("5. one-team mode: %d matches of the team(s), newest first" % len(order))
	else:
	  print("5. selected %d replays over %d maps (%d strong vs strong, %d strong vs other); maps with none: %s" % (
		len(order), len(by_map), both, len(order) - both, ", ".join(sorted(set(offi.values()) - set(by_map))) or "-"))
	if not order:
		die("no match with a strong team to download")
	with open(os.path.join(a.work, "selection.jsonl"), "w", encoding="utf-8") as f:
		for m in order:
			f.write(json.dumps(m, ensure_ascii=False) + "\n")
	if a.dry_run:
		per = {}
		for m in order:
			per[m["mapFile"]] = per.get(m["mapFile"], 0) + 1
		print("   per map: " + ", ".join("%s %d" % (mp, n) for mp, n in sorted(per.items())))
		print("dry run: no downloads, no archive")
		return

	# 6. downloads (resumable), stop at --max-mb of compressed replays
	rdir = os.path.join(a.work, "replays")
	total = [0]

	def path_of(m):
		return os.path.join(rdir, "%s_%s.repl26a" % (m["mapFile"], m["matchId"][:8]))

	def gz_size(p):
		with open(p, "rb") as f:
			return len(gzip.compress(f.read(), 6))

	for m in order:  # files from an earlier run count toward the budget first
		if os.path.exists(path_of(m)) and os.path.getsize(path_of(m)) > 0:
			total[0] += gz_size(path_of(m))

	def one(m):
		p = path_of(m)
		if os.path.exists(p) and os.path.getsize(p) > 0:
			return p
		with _lock:
			if total[0] > a.max_mb * 1e6:
				return None
		rc, so, se = cambc(["matches", "download", m["matchId"], "-o", p])
		if rc != 0 or not os.path.exists(p) or os.path.getsize(p) == 0:
			sys.stderr.write("  download failed %s: %s\n" % (m["matchId"], (se or so).strip()[:200]))
			return None
		with _lock:
			total[0] += gz_size(p)
		return p

	t0 = time.time()
	done = []
	with cf.ThreadPoolExecutor(a.jobs) as ex:
		for i, p in enumerate(ex.map(one, order)):
			if p:
				done.append((order[i], p))
			if (i + 1) % 25 == 0:
				print("6. %d / %d done, %.1f MB compressed, %.0f s" % (i + 1, len(order), total[0] / 1e6, time.time() - t0), flush=True)
	print("6. replays: %d files, %.1f MB compressed" % (len(done), total[0] / 1e6))
	if not done:
		die("no replay downloaded")
	with open(os.path.join(rdir, "index.jsonl"), "w", encoding="utf-8") as f:
		for m, p in done:
			f.write(json.dumps(dict(m, file=os.path.basename(p)), ensure_ascii=False) + "\n")

	# 7. one archive
	stamp = time.strftime("%Y%m%d_%H%M", time.gmtime())
	arc = os.path.join(a.out_dir, "mapintel_ladder_%s.tar.gz" % stamp)
	with tarfile.open(arc, "w:gz") as tf:
		for name in ("ladder.json", "matches_current.jsonl", "teams.json", "selection.jsonl"):
			tf.add(os.path.join(a.work, name), arcname="ladder/" + name)
		tf.add(os.path.join(a.work, "lists"), arcname="ladder/lists")
		tf.add(os.path.join(rdir, "index.jsonl"), arcname="ladder/replays/index.jsonl")
		for m, p in done:
			tf.add(p, arcname="ladder/replays/" + os.path.basename(p))
	mb = os.path.getsize(arc) / 1e6
	print("7. ARCHIVE %s  %.1f MB  (%d replays, %d current-patch match rows)" % (arc, mb, len(done), len(cur)))
	if a.split_mb and mb > a.split_mb:
		parts = split_file(arc, a.split_mb)
		print("   too big for one upload: cut into %d parts (upload all of them; they are joined with `cat`):" % len(parts))
		for p in parts:
			print("   %s  %.1f MB" % (p, os.path.getsize(p) / 1e6))
	else:
		print("Upload this one file in the chat.")


if __name__ == "__main__":
	main()
