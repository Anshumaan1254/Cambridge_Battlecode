#!/usr/bin/env python3
"""Reference (numpy only, float64, plain loops) of the deep models that can run inside a bot, MAPAnalysis.md 5.7: the same feature
layout and the same summation order as the generated C++ header (dl_export.py -> cpp/mapintel/dl_weights.h), so test_library.py can
check the engine's results against it, and dl_train.py uses the layout for its exportable models.

Exportable models (an MLP on per-group features; relu between layers; weights in dl_weights.json):
  opening   x = group_features (22, model_weights.h) + zfeat (19)                                          -> score per group
  next      x = group_features (22) + box distance from the previous group / 100, then round / 2000 + champion (13 one-hot) + zfeat (19)
  values    x = zfeat (19) -> 12 offsets added to the constant champion values w (draft ids): value_c(map) = w_c + mlp(z)_c
Standardisation: (x - mean) / std with the training data's mean and std, stored with the weights.
Evaluation order of the group models (mlp_split): the per-call inputs (zfeat; for next also the round and the champion) are the tail of
x; their first-layer sums are formed once per call in index order, then each group adds b + that sum + its own inputs in index order.
The same order in C++ makes the two bit-identical, and the per-group cost is the group's own inputs only."""
import json, math, os, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import compact as CP  # noqa: E402
import economy as EC  # noqa: E402
import export_headers as EH  # noqa: E402
import features as FT  # noqa: E402
import first_targets as FTG  # noqa: E402

NGF, NZ, NCH = 22, 19, 13


def group_features(M, team):
	"""{group: 22 float64 features} for the reached groups: first_targets.group_table + camp counts per type, respawn / 100, max camp
	strength / 100 (model_weights.h group_features())."""
	tab = FTG.group_table(M, team)
	out = {}
	for g, x in tab.items():
		grp = M.groups[g]
		cnt = [0] * 6
		for c in grp["camps"]:
			cnt[c[0]] += 1
		out[g] = [float(v) for v in x] + [float(c) for c in cnt] + [grp["respawn"] / 100.0, max(EC.camp_stats(c[0])[1] for c in grp["camps"]) / 100.0]
	return out


def zfeat(M, team, arche):
	return [float(v) for v in EH.zfeat_py(FT.compute(M, team), arche)]


def mlp(x, layers, mean, std):
	"""layers = [[W (out x in), b], ...]; sequential sums in input order (= the C++ loops)."""
	h = [(x[i] - mean[i]) / std[i] for i in range(len(x))]
	for li, (W, b) in enumerate(layers):
		o = []
		for j in range(len(W)):
			v = b[j]
			for i in range(len(h)):
				v += W[j][i] * h[i]
			o.append(v if li == len(layers) - 1 or v > 0 else 0.0)
		h = o
	return h


def mlp_const(xc, p, model):
	"""First-layer sums of the per-call inputs xc (input indices p.. of the model), one per hidden unit."""
	(W0, _), mean, std = model["layers"][0], model["mean"], model["std"]
	c = []
	for j in range(len(W0)):
		s = 0.0
		for i in range(p, p + len(xc)):
			s += W0[j][i] * ((xc[i - p] - mean[i]) / std[i])
		c.append(s)
	return c


def mlp_split(xg, c, model):
	"""The model on one group: its own inputs xg (input indices 0..p-1) and the per-call sums c (mlp_const)."""
	layers, mean, std = model["layers"], model["mean"], model["std"]
	p = len(xg)
	h = [(xg[i] - mean[i]) / std[i] for i in range(p)]
	for li, (W, b) in enumerate(layers):
		o = []
		for j in range(len(W)):
			if li == 0:
				v = b[j] + c[j]
				for i in range(p):
					v += W[j][i] * h[i]
			else:
				v = b[j]
				for i in range(len(h)):
					v += W[j][i] * h[i]
			o.append(v if li == len(layers) - 1 or v > 0 else 0.0)
		h = o
	return h


def opening_scores(M, team, arche, model):
	gf, z = group_features(M, team), zfeat(M, team, arche)
	c = mlp_const(z, NGF, model)
	return {g: mlp_split(x, c, model)[0] for g, x in gf.items()}


def next_scores(M, team, arche, model, prev, champ, rnd, avail=None):
	gf, z = group_features(M, team), zfeat(M, team, arche)
	boxes = [CP.group_box(g) for g in M.groups]
	oh = [1.0 if k == champ else 0.0 for k in range(NCH)]
	c = mlp_const([rnd / 2000.0] + oh + z, NGF + 1, model)
	out = {}
	for g, x in gf.items():
		if avail is not None and not avail[g]:
			continue
		d = CP.box_dist(boxes[prev], boxes[g]) / 100.0
		out[g] = mlp_split(x + [d], c, model)[0]
	return out


def champion_values(M, team, arche, model):
	z = zfeat(M, team, arche)
	off = mlp(z, model["layers"], model["mean"], model["std"])
	return [model["w"][c] + off[c] for c in range(12)]


def rank(scores, n=8):
	return [g for g in sorted(scores, key=lambda g: (-scores[g], g))][:n]


def load(path):
	return json.load(open(path))
