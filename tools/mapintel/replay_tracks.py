#!/usr/bin/env python3
"""Current-patch ladder replays -> per-game tracks (positions, health, bags, gold, camp health every round, and the action events), for
the LEARNED plan-4 thresholds and the economy constants (MAPAnalysis.md 7.2, the user's changes of Oct 24: items 1-2).

    python3 -I tools/mapintel/replay_tracks.py REPLAY_DIR [...] [--out mapintel_work/tracks] [--jobs 4]

One compressed npz per replay (git-ignored work folder; ~3 minutes for 600 replays on 4 CPUs). Arrays (R = final round + 1, row r = round r;
B bodies in the replay's index order; C camps in the replay's camp order):
  map, final, winner (0 A / 1 B / -1), drafts [2, 5] (pick ids, -1 = none)
  btype [B] (body type, cambc::champion_type order), bteam [B]
  pos [R, B, 2] int16, hp / maxhp [R, B] int16, alive [R, B] uint8, bag [R, B] int16 (carried gems), gold [R, B] int32 (unspent)
  ctype, cx, cy, cgroup [C] (cgroup = the runtime dump's group index of the camp's tile, -1 if none), chp [R, C] int32
  ev_attack [N, 4] (round, body, x, y of the target tile), ev_cast [N, 5] (round, body, x, y, slot), ev_recall [N, 2], ev_shop [N, 2],
  ev_capture [N, 4] (round, body, group, gems), ev_bank [N, 4] (round, body, gems, altar index), ev_death [N, 3] (round, body, 1 = by a camp)
Rows of rounds the replay does not list repeat the previous row (alive = 0 before round 1)."""
import argparse, concurrent.futures as cf, json, os, subprocess, sys, tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mapdata  # noqa: E402
import replays as RP  # noqa: E402
from engine import BODY_NAMES  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
BODY_OF = {n.replace(" ", "").replace("&", "And").lower(): i for i, n in enumerate(BODY_NAMES)}


def body_type(name):
	k = str(name).replace(" ", "").lower()
	if k not in BODY_OF:
		raise SystemExit(f"unknown champion name {name}")
	return BODY_OF[k]


def tracks(d, mp):
	meta = d["meta"]
	M = mapdata.load(mp)
	final = int(meta.get("finalRound") or max(r["r"] for r in d["rounds"]))
	R = final + 1
	bodies = sorted(meta["bodies"], key=lambda b: b["index"])
	B = len(bodies)
	bix = {b["index"]: k for k, b in enumerate(bodies)}
	camps = meta["camps"]
	C = len(camps)
	byr = {}
	for row in d["rounds"]:
		byr[row["r"]] = row  # later entries win (the replay lists a draft-phase snapshot first)
	pos = np.zeros((R, B, 2), np.int16)
	hp = np.zeros((R, B), np.int16)
	mx = np.zeros((R, B), np.int16)
	alive = np.zeros((R, B), np.uint8)
	bag = np.zeros((R, B), np.int16)
	gold = np.zeros((R, B), np.int32)
	chp = np.zeros((R, C), np.int32)
	chp[0] = [c["hp"] for c in camps]
	for r in range(1, R):
		row = byr.get(r)
		if row is None:
			pos[r], hp[r], mx[r], alive[r], bag[r], gold[r], chp[r] = pos[r - 1], hp[r - 1], mx[r - 1], alive[r - 1], bag[r - 1], gold[r - 1], chp[r - 1]
			continue
		for c in row["ch"]:
			k = bix[c[0]]
			pos[r, k] = (c[3], c[4])
			hp[r, k], mx[r, k], alive[r, k], bag[r, k], gold[r, k] = c[5], c[6], c[7], c[8], c[9]
		chp[r] = row["campHp"]
	evs = {"attack": [], "cast": [], "recall": [], "shop": [], "capture": [], "bank": [], "death": []}
	for e in d["events"]:
		k, w = e["k"], e.get("who")
		if w is None or w not in bix:
			continue
		b = bix[w]
		if k == "Attack" and "to" in e:
			evs["attack"].append((e["r"], b, e["to"][0], e["to"][1]))
		elif k == "Cast ability" and "to" in e:
			evs["cast"].append((e["r"], b, e["to"][0], e["to"][1], e.get("slot", -1)))
		elif k == "Recall":
			evs["recall"].append((e["r"], b))
		elif k == "Shop":
			evs["shop"].append((e["r"], b))
		elif k == "CaptureGems":
			g = M.camp_group.get(tuple(e["at"]), -1)
			evs["capture"].append((e["r"], b, g, e["gems"]))
		elif k == "Banked":
			alt = next((i for i, a in enumerate(M.altar_tiles) if RP.cheb(a, e["at"]) <= 1), -1)
			evs["bank"].append((e["r"], b, e["gems"], alt))
		elif k == "Death":
			evs["death"].append((e["r"], b, 1 if e.get("by") == "camp" else 0))
	width = {"attack": 4, "cast": 5, "recall": 2, "shop": 2, "capture": 4, "bank": 4, "death": 3}
	dr = [[RP.DECODE_PICKS.index(x) if x in RP.DECODE_PICKS else -1 for x in t] + [-1] * (5 - len(t)) for t in meta["drafts"]]
	out = dict(map=np.array(mp), final=np.int32(final), winner=np.int8({1: 0, 2: 1}.get(meta.get("outcome"), -1)),
			   drafts=np.array(dr, np.int8), btype=np.array([body_type(b["type"]) for b in bodies], np.int8),
			   bteam=np.array([b["team"] for b in bodies], np.int8), pos=pos, hp=hp, maxhp=mx, alive=alive, bag=bag, gold=gold,
			   ctype=np.array([RP.DECODE_CAMPS.get(c["type"], c["type"]) for c in camps], np.int8),
			   cx=np.array([c["x"] for c in camps], np.int16), cy=np.array([c["y"] for c in camps], np.int16),
			   cgroup=np.array([M.camp_group.get((c["x"], c["y"]), -1) for c in camps], np.int16), chp=chp)
	for k, v in evs.items():
		out["ev_" + k] = np.array(v, np.int32).reshape(-1, width[k])
	return out


def one(path, out_dir):
	name = os.path.splitext(os.path.basename(path))[0]
	dst = os.path.join(out_dir, name + ".npz")
	if os.path.exists(dst):
		return name, "kept"
	with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
		tmp = tf.name
	r = subprocess.run(["node", os.path.join(ROOT, "tools/replay/decode.mjs"), path, "--out", tmp], capture_output=True, text=True)
	if r.returncode != 0:
		os.unlink(tmp)
		return name, "decode failed: " + (r.stderr or r.stdout)[-200:]
	d = json.load(open(tmp))
	os.unlink(tmp)
	mp = RP.match_map(d["meta"])
	if mp is None:
		return name, "no official map"
	np.savez_compressed(dst, **tracks(d, mp))
	return name, "ok"


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("dirs", nargs="+")
	ap.add_argument("--out", default=os.path.join(ROOT, "mapintel_work/tracks"))
	ap.add_argument("--jobs", type=int, default=4)
	a = ap.parse_args()
	os.makedirs(a.out, exist_ok=True)
	files = sorted(os.path.join(d, f) for d in a.dirs for f in os.listdir(d) if f.endswith(".repl26a"))
	RP.official()
	with cf.ThreadPoolExecutor(a.jobs) as ex:
		res = list(ex.map(lambda p: one(p, a.out), files))
	bad = [f"{n}: {s}" for n, s in res if s not in ("ok", "kept")]
	print(f"{len(res)} replays, {len(res) - len(bad)} tracks in {a.out}" + ("; " + "; ".join(bad) if bad else ""))


if __name__ == "__main__":
	main()
