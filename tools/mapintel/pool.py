#!/usr/bin/env python3
"""The map pool of patch 2.0.0 (every dumped map: the 40 catalog maps + the 30 of fingerprints_s3_new.txt = maps/s3) for the scripts that
learn per map with leave-maps-out folds (dl/make_dataset.py, draft_learn.py). COMPUTED.

    import pool;  P = pool.extend(arche, folds)     # arche = maps/catalog/archetypes.json, folds = maps/catalog/splits.json "folds"
    P.names (sorted), P.labels[map], P.folds (5 lists), P.fold_of[map], P.added (maps outside the catalog),
    P.z[map] (np.array: the given z of the catalog maps + the runtime z of the added maps)
    python3 -I tools/mapintel/pool.py               # prints the maps the catalog lacks: archetype and fold

A catalog map keeps the catalog's archetype label and fold. A map outside the catalog gets the runtime z-vector of model_weights.h
(zfeat of features.py on its dump, team A: on the 40 catalog maps it equals the catalog's z to 4e-5, both teams alike), the archetype
a bot computes for it (archetype_of(), the nearest PCA centroid: it reproduces the catalog's label on all 40), and a fold: in name order
within each archetype, each map joins the fold with the fewest maps of that archetype, then the fewest maps, then the lowest index (the
catalog's folds are archetype-stratified the same way). After a catalog rebuild over the whole pool nothing is added."""
import json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_headers as EH  # noqa: E402
import features as FT  # noqa: E402
import mapdata  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


class Pool:
	pass


def runtime_z(name, arche):
	return np.asarray(EH.zfeat_py(FT.compute(mapdata.load(name), 0), arche), float)


def extend(arche, folds, names=None, z=None):
	"""Pool of `names` (default: every dumped map). z: {map: z} of the catalog maps (draft_learn.py's catalog z), kept as given."""
	P = Pool()
	P.names = sorted(names if names is not None else mapdata.pool_names())
	P.labels = dict(arche["labels"])
	P.folds = [list(f) for f in folds]
	P.z = dict(z or {})
	P.added = [n for n in P.names if n not in P.labels or not any(n in f for f in P.folds)]
	for n in P.added:
		if n not in P.z:
			P.z[n] = runtime_z(n, arche)
		P.labels[n] = P.labels.get(n, EH.archetype_py(P.z[n], arche))
	for n in sorted(P.added, key=lambda n: (P.labels[n], n)):
		if any(n in f for f in P.folds):
			continue
		k = min(range(len(P.folds)), key=lambda k: (sum(P.labels.get(m) == P.labels[n] for m in P.folds[k]), len(P.folds[k]), k))
		P.folds[k].append(n)
	P.fold_of = {n: k for k, f in enumerate(P.folds) for n in f}
	return P


def from_catalog(catalog=os.path.join(ROOT, "maps/catalog"), names=None):
	arche = json.load(open(os.path.join(catalog, "archetypes.json")))
	folds = json.load(open(os.path.join(catalog, "splits.json")))["folds"]
	return extend(arche, folds, names), arche


if __name__ == "__main__":
	P, _ = from_catalog()
	print(f"{len(P.names)} maps, {len(P.added)} outside the catalog; fold sizes {[len(f) for f in P.folds]}")
	for n in P.added:
		print(f"  {n:22s} archetype {P.labels[n]}  fold {P.fold_of[n]}")
