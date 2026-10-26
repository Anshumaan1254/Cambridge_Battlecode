#!/usr/bin/env python3
"""Candidate rosters per map of the pool (every dumped map: the 70 of patch 2.0.0) for the roster battery (tools/mapintel/run_battery.sh).

    python3 -I tools/mapintel/battery_rosters.py LIST.jsonl [...] [--real 4] [--total 8] [--teams TEAMS.json] [--exclude-team NAME]
                                                  [--out tools/mapintel/data/battery_rosters.json]

Per map, C = --total rosters (both teams of a battery game get one of them):
  * LEARNED: the rosters strong teams drafted on that map in current-patch real games (match rows from fetch_ladder.sh's
    matches_current.jsonl, or session 17's groups_matches.jsonl), most frequent first, at most --real; a team that is in more than 90% of
    the rows (the requester's own team in match groups: an old bot of ours) and --exclude-team are not counted; with --teams (fetch_ladder's
    teams.json) only its strong set counts;
  * COMPUTED: rosters balanced over the four kit classes (attack range 1 / 3 x dash or not, read from the engine probe), the same set for
    every map of a team size, filling the list up to C: greedy, at least three of the four classes in each roster (all four would force
    Vesper Vale, the only ranged dash kit, into every roster), then the champions used least so far, then one class not dominating.
    A map without LEARNED rows (the 30 maps new in patch 2.0.0 until a ladder download of that patch is fed in) gets COMPUTED rosters
    only; meta.computed_only lists those maps and their entries say so.
Each map's entry holds its fingerprint (experiments/results/mapintel/dump/fingerprints.txt and fingerprints_s3_new.txt, from the C++
function in the engine).
Regenerate the committed file (40 maps LEARNED from session 17's groups, i.e. engine 1.0.3; the 30 new maps COMPUTED):
    python3 -I tools/mapintel/battery_rosters.py god2_session17/findings/live/groups_matches.jsonl
With a patch-2.0.0 download instead (LEARNED wherever its strong teams played; fetch_ladder.sh's files):
    python3 -I tools/mapintel/battery_rosters.py mapintel_work/ladder/matches_current.jsonl --teams mapintel_work/ladder/teams.json"""
import argparse, collections, itertools, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mapdata  # noqa: E402
from engine import Engine, PICK_NAMES, pick_bodies  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DUMP = os.path.join(ROOT, "experiments/results/mapintel/dump")


def norm(name):
	return name.lower().replace("-", "_")


def balanced(E, n, k):
	cls = E.classes()
	combos = list(itertools.combinations(range(12), n))
	use = collections.Counter()
	out = []
	for _ in range(k):
		def score(c):
			hist = collections.Counter(cls[b] for p in c for b in pick_bodies(p))
			return (min(len(hist), 3), -sum(use[p] for p in c), -max(hist.values()))
		best = max((c for c in combos if list(c) not in out), key=lambda c: (score(c), [-x for x in c]))
		out.append(list(best))
		use.update(best)
	return out


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("lists", nargs="+")
	ap.add_argument("--real", type=int, default=4)
	ap.add_argument("--total", type=int, default=8)
	ap.add_argument("--teams", default="")
	ap.add_argument("--exclude-team", action="append", default=[])
	ap.add_argument("--out", default=os.path.join(ROOT, "tools/mapintel/data/battery_rosters.json"))
	a = ap.parse_args()
	E = Engine()
	fps = mapdata.fingerprints()
	by_norm = {norm(m): m for m in fps}
	rows = []
	for f in a.lists:
		rows += [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
	cnt = collections.Counter(t["name"] for r in rows for t in r["teams"])
	excl = set(a.exclude_team) | {n for n, c in cnt.items() if c > 0.9 * len(rows)}
	strong = None
	if a.teams:
		strong = set(json.load(open(a.teams, encoding="utf-8"))["strong"])
	seen = collections.defaultdict(collections.Counter)
	wins = collections.defaultdict(collections.Counter)
	order = collections.defaultdict(dict)
	used = 0
	for r in rows:
		mp = by_norm.get(norm(r["map"]))
		if not mp:
			continue
		for t in r["teams"]:
			if t["name"] in excl or (strong is not None and t["teamId"] not in strong):
				continue
			picks = [int(x) for x in t["draftPicks"]]
			if len(picks) != fps[mp][1]:
				continue
			key = tuple(sorted(picks))
			seen[mp][key] += 1
			wins[mp][key] += t.get("result") == "win"
			order[mp].setdefault(key, collections.Counter())[tuple(picks)] += 1
			used += 1
	bal = {n: balanced(E, n, a.total) for n in sorted({ts for _, ts in fps.values()})}
	computed_only = sorted(mp for mp in fps if not seen[mp])
	out = {"meta": {"sources": [os.path.relpath(f, ROOT).replace(os.sep, "/") for f in a.lists], "rows": len(rows), "team_sides_used": used,
					"excluded_teams": sorted(excl), "real": a.real, "total": a.total,
					"note": "LEARNED rosters: real games of strong teams in the sources; COMPUTED: balanced over kit classes (engine probe). "
							"Maps in computed_only had no LEARNED rows in the sources (the maps new in patch 2.0.0 have no ladder data here "
							"yet): COMPUTED rosters only",
					"computed_only": computed_only},
		   "maps": {}}
	for mp, (fp, ts) in sorted(fps.items()):
		ros = []
		for key, c in sorted(seen[mp].items(), key=lambda kv: (-kv[1], -wins[mp][kv[0]], kv[0]))[: a.real]:
			picks = list(order[mp][key].most_common(1)[0][0])
			ros.append({"picks": picks, "names": [PICK_NAMES[p] for p in picks], "origin": "LEARNED", "games": c, "wins": wins[mp][key]})
		for picks in bal[ts]:
			if len(ros) >= a.total:
				break
			if any(sorted(r["picks"]) == sorted(picks) for r in ros):
				continue
			ros.append({"picks": picks, "names": [PICK_NAMES[p] for p in picks], "origin": "COMPUTED", "classes":
						sorted(E.kit_class(b) for p in picks for b in pick_bodies(p))})
		out["maps"][mp] = {"fingerprint": fp, "team_size": ts, "rosters": ros}
		if mp in computed_only:
			out["maps"][mp]["note"] = "no LEARNED rosters in the sources: COMPUTED (balanced over kit classes) only"
	os.makedirs(os.path.dirname(a.out), exist_ok=True)
	json.dump(out, open(a.out, "w"), indent=1)
	nl = sum(sum(r["origin"] == "LEARNED" for r in v["rosters"]) for v in out["maps"].values())
	print(f"{len(out['maps'])} maps, {nl} LEARNED + {sum(len(v['rosters']) for v in out['maps'].values()) - nl} COMPUTED rosters "
		  f"({used} team-sides of {len(rows)} rows; excluded {sorted(excl)}; {len(computed_only)} maps COMPUTED only) -> {os.path.relpath(a.out, ROOT)}")


if __name__ == "__main__":
	main()
