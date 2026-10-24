#!/usr/bin/env python3
"""Plan 4's thresholds, LEARNED where the fit beat the formula (plan4_learn.py -> experiments/results/mapintel/plan4/weights.json): the
Python twin of model_weights.h p4_thresholds() (the same order of operations: v = intercept, then + coef[i] x z[i] in index order, then
floor(v + 0.5) clamped to [lo, hi]). compact.thresholds(), plans.plan4() and export_headers.py read it; without weights.json every
threshold stays the formula (plans.h p4_formula())."""
import json, math, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PATH = os.path.join(ROOT, "experiments/results/mapintel/plan4/weights.json")
_W, _A = None, None


def model():
	"""{threshold key: {index, use, lo, hi, intercept, coef}} for the learned thresholds, or {} (no fit / file)."""
	global _W
	if _W is None:
		_W = json.load(open(PATH))["thresholds"] if os.path.exists(PATH) else {}
	return _W


def apply(F, thr):
	"""thr (8 formula thresholds, a list) with the learned ones written over it, from the runtime feature vector F (features.compute)."""
	W = model()
	if not W:
		return thr
	global _A
	if _A is None:
		_A = json.load(open(os.path.join(ROOT, "maps/catalog/archetypes.json")))
	import export_headers as EH
	z = EH.zfeat_py(F, _A)
	out = list(thr)
	for key in sorted(W, key=lambda k: W[k]["index"]):
		m = W[key]
		v = m["intercept"]
		for i in range(len(z)):
			v += m["coef"][i] * z[i]
		out[m["index"]] = int(min(max(math.floor(v + 0.5), m["lo"]), m["hi"]))
	return out
