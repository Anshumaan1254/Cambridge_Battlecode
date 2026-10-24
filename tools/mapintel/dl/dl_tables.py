#!/usr/bin/env python3
"""The step-7 group models as tables for the 40 official maps (known_maps.h, through export_headers.py): a champion of a known map looks
up the learned next target after a capture without computing the model's inputs (which need the draft's map analysis).

    python3 -I tools/mapintel/dl/dl_tables.py [--weights experiments/results/mapintel/dl_model_20261024_1722/dl_weights.json]

Writes into maps/catalog/<map>.json:
  "dl": {"sha256": the json's, "rounds": [early, late], "split": round,
         "open": {team: hex of 16 bytes: the opening model's ranking, best first (255 = none)},
         "next": {team: hex of [2 phases][13 body types][ngroups][2]: after capturing group g, a body of type t at phase p goes to these
                  two groups next, best first (the reached groups other than g; 255 = none)}}
Phases: the next model's round input is the 25th / 75th percentile of the rounds of its training samples (329 / 849, LEARNED from the
53,830 next captures of experiments/results/mapintel/dl_data), and a champion uses the early table before the median (571) and the late
one after. Scores come from tools/mapintel/dl/dl_ref.py with its summation order (the inputs cached per map and team), ties to the
lower group, so the tables are what dl_weights.h computes in C++ (test_dmem2.py compares the draft's L block with them)."""
import argparse, hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import compact as CP  # noqa: E402
import dl_ref as dl  # noqa: E402
import mapdata  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ROUNDS, SPLIT, NTYPE = (329, 849), 571, 13


def tables(M, team, arche, J):
	gf, z = dl.group_features(M, team), dl.zfeat(M, team, arche)
	G = len(M.groups)
	out = {}
	if "opening" in J:
		c = dl.mlp_const(z, dl.NGF, J["opening"])
		sc = {g: dl.mlp_split(x, c, J["opening"])[0] for g, x in gf.items()}
		r = dl.rank(sc, 16)
		out["open"] = bytes(r + [255] * (16 - len(r)))
	if "next" in J:
		boxes = [CP.group_box(g) for g in M.groups]
		b = bytearray([255] * (2 * NTYPE * G * 2))
		for ph, rnd in enumerate(ROUNDS):
			for t in range(NTYPE):
				oh = [1.0 if k == t else 0.0 for k in range(NTYPE)]
				c = dl.mlp_const([rnd / 2000.0] + oh + z, dl.NGF + 1, J["next"])
				for prev in range(G):
					if prev not in gf:
						continue
					sc = {g: dl.mlp_split(x + [CP.box_dist(boxes[prev], boxes[g]) / 100.0], c, J["next"])[0] for g, x in gf.items() if g != prev}
					r = dl.rank(sc, 2)
					o = ((ph * NTYPE + t) * G + prev) * 2
					for k, g in enumerate(r):
						b[o + k] = g
		out["next"] = bytes(b)
	return out


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--weights", default=os.path.join(ROOT, "experiments/results/mapintel/dl_model_20261024_1722/dl_weights.json"))
	ap.add_argument("--models", default="opening,next", help="the models to table (the ones dl_weights.h carries)")
	a = ap.parse_args()
	raw = open(a.weights, "rb").read()
	J = {k: m for k, m in json.loads(raw)["models"].items() if k in a.models.split(",")}
	sha = hashlib.sha256(raw).hexdigest()
	arche = json.load(open(os.path.join(ROOT, "maps/catalog/archetypes.json")))
	for n in mapdata.official_names():
		M = mapdata.load(n)
		d = {"sha256": sha, "rounds": list(ROUNDS), "split": SPLIT, "open": {}, "next": {}}
		for team in (0, 1):
			t = tables(M, team, arche, J)
			if "open" in t:
				d["open"][str(team)] = t["open"].hex()
			if "next" in t:
				d["next"][str(team)] = t["next"].hex()
		p = os.path.join(ROOT, "maps/catalog", n + ".json")
		cat = json.load(open(p))
		cat["dl"] = d
		json.dump(cat, open(p, "w"), indent=1)
		print(f"{n}: {len(M.groups)} groups")


if __name__ == "__main__":
	main()
