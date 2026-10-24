#!/usr/bin/env python3
"""Current-patch ladder replays -> compact per-game summaries for the LEARNED parts of the map model (MAPAnalysis.md 3C, step 6).

    python3 -I tools/mapintel/replays.py REPLAY_DIR [REPLAY_DIR ...] --out experiments/results/mapintel/ladder [--jobs 4]
                                         [--index index.jsonl]     (fetch_ladder.sh's replays/index.jsonl: team names, ids, sides)

Each replay is decoded with tools/replay/decode.mjs (the engine's own wasm; replays of engine 1.0.3 decode with v1_0_3) and summarised:
  map             matched exactly to one of the 40 official maps by its camp layout (positions and types) and size
  drafts, winner, final round, submitted gems, end ('gems' or 'tiebreak'), engine, team names / ids when the index has them
  banked          each team's banked gems every 25 rounds
  captures        (round, team, champion, group id, gems, gold, tile)   group ids = the runtime dump's (mapdata) group index
  first_capture   per team and group: the first capture round
  banks           (round, team, champion, gems, tile, altar)            the altar is the nearest altar tile within Chebyshev 1
  deaths          (round, team, champion, tile, bag, by: 'camp' / body index)
  recalls, shops  (round, team, champion)
  stand           per team, champion and group: tiles it attacked that group's camps from, with counts (LEARNED standing tiles)
  heat            per team and champion: tiles where it attacked camps / attacked champions / captured / died (counts)
Writes OUT/<replay name>.json and OUT/summary.jsonl (one line per game without the heat and stand tables)."""
import argparse, concurrent.futures as cf, json, os, subprocess, sys, tempfile
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mapdata  # noqa: E402
from engine import PICK_NAMES  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DECODE_PICKS = ['Ryth', 'VesperVale', 'Vendetta', 'CassiAndIssac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin']
DECODE_CAMPS = {"wolf": 0, "elk": 1, "gem": 2, "gold": 3, "monolith": 4, 5: 5, "golem": 5}

_maps = None


def official():
	global _maps
	if _maps is None:
		_maps = {}
		for n in mapdata.official_names():
			M = mapdata.load(n)
			_maps[n] = (M, frozenset((c[0], c[1], c[2]) for c in M.camp_list))
	return _maps


def match_map(meta):
	camps = frozenset((DECODE_CAMPS.get(c["type"], c["type"]), c["x"], c["y"]) for c in meta["camps"])
	for n, (M, cs) in official().items():
		if M.W == meta["width"] and M.H == meta["height"] and cs == camps:
			return n
	return None


def cheb(a, b):
	return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def summarise(d, name, index_row=None):
	meta = d["meta"]
	mp = match_map(meta)
	S = {"replay": name, "engine": meta.get("engine"), "map": mp, "W": meta["width"], "H": meta["height"],
		 "drafts": [[DECODE_PICKS.index(x) if x in DECODE_PICKS else x for x in t] for t in meta["drafts"]],
		 "winner": {1: "A", 2: "B"}.get(meta.get("outcome")), "final_round": meta.get("finalRound"), "submitted": meta.get("submitted")}
	S["end"] = "gems" if max(S["submitted"] or [0]) >= 1000 else "tiebreak"
	if index_row:
		for t in index_row.get("teams", []):
			S["team_" + t["side"].upper()] = {"name": t.get("name"), "id": t.get("teamId"), "result": t.get("result")}
		S["matchId"] = index_row.get("matchId")
	if mp is None:
		return S
	M = official()[mp][0]
	body_team = {b["index"]: b["team"] for b in meta["bodies"]}
	body_type = {b["index"]: b["type"] for b in meta["bodies"]}
	S["banked"] = [[r["r"], r["sub"][0], r["sub"][1]] for r in d["rounds"] if r["r"] % 25 == 0]
	caps, banks, deaths, recalls, shops = [], [], [], [], []
	stand = defaultdict(Counter)
	heat = defaultdict(Counter)
	first = {}
	camp_tiles = set(M.camp_group)
	for e in d["events"]:
		k = e["k"]
		if k in ("CaptureGems", "CaptureGold"):  # CaptureGold: a gold-only group (decode.mjs --gold-captures)
			g = M.camp_group.get(tuple(e["at"]))
			caps.append([e["r"], e["team"], e["champ"], g, e["gems"], e["gold"], e["at"]])
			if g is not None:
				first.setdefault((e["team"], g), e["r"])
			heat[(e["team"], e["champ"], "capture")][tuple(e["at"])] += 1
		elif k == "Banked":
			alt = next((i for i, a in enumerate(M.altar_tiles) if cheb(a, e["at"]) <= 1), None)
			banks.append([e["r"], e["team"], e["champ"], e["gems"], e["at"], alt])
		elif k == "Death":
			deaths.append([e["r"], e["team"], e["champ"], e["at"], e["bag"], e["by"]])
			heat[(e["team"], e["champ"], "death")][tuple(e["at"])] += 1
		elif k == "Recall":
			recalls.append([e["r"], e.get("team"), e.get("champ")])
		elif k == "Shop":
			shops.append([e["r"], e.get("team"), e.get("champ")])
		elif k == "Attack" and "from" in e and "to" in e and e.get("who") is not None:
			to = tuple(e["to"])
			if to in camp_tiles:
				g = M.camp_group[to]
				stand[(e["team"], e["champ"], g)][tuple(e["from"])] += 1
				heat[(e["team"], e["champ"], "hit_camp")][tuple(e["from"])] += 1
			else:
				heat[(e["team"], e["champ"], "hit_champ")][tuple(e["from"])] += 1
	S.update(captures=caps, banks=banks, deaths=deaths, recalls=recalls, shops=shops,
			 first_capture=[[t, g, r] for (t, g), r in sorted(first.items())])
	S["stand"] = [[t, ch, g, [[x, y, n] for (x, y), n in c.most_common()]] for (t, ch, g), c in sorted(stand.items())]
	S["heat"] = [[t, ch, kind, [[x, y, n] for (x, y), n in c.most_common()]] for (t, ch, kind), c in sorted(heat.items())]
	return S


def decode_one(path, index_row, out_dir):
	name = os.path.splitext(os.path.basename(path))[0]
	dst = os.path.join(out_dir, name + ".json")
	if os.path.exists(dst):
		return json.load(open(dst))
	with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
		tmp = tf.name
	r = subprocess.run(["node", os.path.join(ROOT, "tools/replay/decode.mjs"), path, "--out", tmp, "--gold-captures"], capture_output=True, text=True)
	if r.returncode != 0:
		os.unlink(tmp)
		return {"replay": name, "error": (r.stderr or r.stdout)[-400:]}
	d = json.load(open(tmp))
	os.unlink(tmp)
	S = summarise(d, name, index_row)
	json.dump(S, open(dst, "w"))
	return S


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("dirs", nargs="+")
	ap.add_argument("--out", default=os.path.join(ROOT, "experiments/results/mapintel/ladder"))
	ap.add_argument("--jobs", type=int, default=4)
	ap.add_argument("--index", default="")
	a = ap.parse_args()
	os.makedirs(a.out, exist_ok=True)
	idx = {}
	for p in ([a.index] if a.index else []) + [os.path.join(d, "index.jsonl") for d in a.dirs]:
		if p and os.path.exists(p):
			for line in open(p, encoding="utf-8"):
				row = json.loads(line)
				if "file" in row:
					idx[os.path.splitext(row["file"])[0]] = row
	files = sorted(os.path.join(d, f) for d in a.dirs for f in os.listdir(d) if f.endswith(".repl26a"))
	official()
	with cf.ThreadPoolExecutor(a.jobs) as ex:
		res = list(ex.map(lambda p: decode_one(p, idx.get(os.path.splitext(os.path.basename(p))[0]), a.out), files))
	with open(os.path.join(a.out, "summary.jsonl"), "w") as f:
		for S in res:
			f.write(json.dumps({k: v for k, v in S.items() if k not in ("heat", "stand", "captures", "banks", "deaths", "recalls", "shops")}) + "\n")
	bad = [S["replay"] for S in res if S.get("error") or not S.get("map")]
	print(f"{len(res)} replays, {len(res) - len(bad)} summarised" + (f"; not matched / failed: {', '.join(bad)}" if bad else ""))


if __name__ == "__main__":
	main()
