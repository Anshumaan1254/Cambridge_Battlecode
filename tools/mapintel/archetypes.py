#!/usr/bin/env python3
"""Map archetypes (MAPAnalysis.md 5.4, step 4) on the official maps' catalog features. COMPUTED (the per-archetype draft table is LEARNED).

    python3 -I tools/mapintel/archetypes.py [--catalog maps/catalog] [--kmax 8] [--boot 300]

Features: the 'f_*' columns of maps.csv that a bot computes at run time (features.h), a fixed curated subset (CLUSTER_FEATURES),
log-scaled where they are sizes, then standardised (z-scores). PCA keeps the components that explain 90% of the variance. k-means
(k = 2..kmax, 50 restarts) is scored by silhouette; with 40 maps the chosen k is the best silhouette among k >= 3 unless k = 2 is
clearly better (+0.05), and its stability is reported (bootstrap: refit on resampled maps, adjusted Rand index of the original maps'
labels against the full fit; and each map's co-assignment rate with its own cluster). HDBSCAN (min cluster size 3) marks outliers.
Outputs (maps/catalog/):
  archetypes.json   features, transforms, scaling (mean, std), PCA basis, k-means centroids in z-space and in PCA space, labels per map,
                    silhouette per k, stability, HDBSCAN labels, per-archetype summary (members, feature means) and the strong teams'
                    drafts per archetype when real-game rows are given (--matches)
  splits.json       5 folds stratified by archetype (leave-maps-out cross-validation grouped by archetype)"""
import argparse, csv, json, os, sys
from collections import Counter

import numpy as np
from sklearn.cluster import HDBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.model_selection import StratifiedKFold

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import PICK_NAMES  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
CLUSTER_FEATURES = [  # (column, transform): runtime features (features.py = features.h), so a bot can find its nearest archetype
	("f_area", "log"), ("f_team", "id"), ("f_walk_share", "id"), ("f_hole_share", "id"), ("f_bush_share", "id"),
	("f_gems", "log"), ("f_gold_per_gem", "log1p"), ("f_gem_rate", "log1p"), ("f_gems_heavy_share", "id"),
	("f_mono_golem_gem_share", "id"), ("f_gems_mid_share", "id"), ("f_spawn_dist", "log1p"), ("f_dist_gem_weighted", "log1p"),
	("f_altars", "log1p"), ("f_wide_contested_value_share", "id"), ("f_groups", "log"), ("f_max_group_gems", "log1p"),
	("f_cluster_only_gem_share", "id"), ("f_safe_area_share", "id"),
]


def transform(v, how):
	v = float(v)
	return np.log(max(v, 1e-6)) if how == "log" else np.log1p(max(v, 0.0)) if how == "log1p" else v


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--catalog", default=os.path.join(ROOT, "maps/catalog"))
	ap.add_argument("--kmax", type=int, default=8)
	ap.add_argument("--boot", type=int, default=300)
	ap.add_argument("--matches", nargs="*", default=[os.path.join(ROOT, "god2_session17/findings/live/groups_matches.jsonl")])
	a = ap.parse_args()
	rows = list(csv.DictReader(open(os.path.join(a.catalog, "maps.csv"))))
	names = [r["map"] for r in rows]
	X = np.array([[transform(r[c], t) for c, t in CLUSTER_FEATURES] for r in rows])
	mu, sd = X.mean(0), X.std(0)
	sd[sd == 0] = 1.0
	Z = (X - mu) / sd
	pca = PCA().fit(Z)
	nc = int(np.searchsorted(np.cumsum(pca.explained_variance_ratio_), 0.90) + 1)
	pca = PCA(n_components=nc).fit(Z)
	Y = pca.transform(Z)
	sil, fits = {}, {}
	for k in range(2, a.kmax + 1):
		km = KMeans(n_clusters=k, n_init=50, random_state=0).fit(Y)
		fits[k] = km
		sil[k] = float(silhouette_score(Y, km.labels_))
	k3 = max((k for k in sil if k >= 3), key=lambda k: sil[k])
	k = 2 if sil[2] > sil[k3] + 0.05 else k3
	km = fits[k]
	lab = km.labels_
	# stability
	rng = np.random.default_rng(0)
	aris, co = [], np.zeros((len(names), len(names)))
	cnt = np.zeros((len(names), len(names)))
	for _ in range(a.boot):
		idx = rng.choice(len(names), len(names), replace=True)
		kb = KMeans(n_clusters=k, n_init=10, random_state=int(rng.integers(1 << 30))).fit(Y[idx])
		lb = kb.predict(Y)
		aris.append(adjusted_rand_score(lab, lb))
		same = lb[:, None] == lb[None, :]
		co += same
		cnt += 1
	co /= np.maximum(cnt, 1)
	stab = []
	for i in range(len(names)):
		mates = [j for j in range(len(names)) if lab[j] == lab[i] and j != i]
		stab.append(float(np.mean(co[i, mates])) if mates else 1.0)
	hd = HDBSCAN(min_cluster_size=3).fit(Y)
	# centroids in z-space (the bot's nearest-archetype fallback works in standardised feature space; PCA basis kept too)
	cz = np.array([Z[lab == c].mean(0) for c in range(k)])
	# strong teams' drafts per archetype (LEARNED; opponent side of session 17's match rows: our old bot's side is not counted)
	draft = {c: Counter() for c in range(k)}
	nrows = Counter()
	byname = {n.lower().replace("-", "_"): i for i, n in enumerate(names)}
	for p in a.matches:
		if not os.path.exists(p):
			continue
		ms = [json.loads(l) for l in open(p) if l.strip()]
		cnt_team = Counter(t["name"] for m in ms for t in m["teams"])
		own = {n for n, c in cnt_team.items() if c > 0.9 * len(ms)}
		for m in ms:
			i = byname.get(m["map"].lower().replace("-", "_"))
			if i is None:
				continue
			for t in m["teams"]:
				if t["name"] in own:
					continue
				for pk in t["draftPicks"]:
					draft[lab[i]][PICK_NAMES[int(pk)]] += 1
				nrows[lab[i]] += 1
	arche = []
	for c in range(k):
		mem = [names[i] for i in range(len(names)) if lab[i] == c]
		means = {CLUSTER_FEATURES[j][0]: round(float(X[lab == c, j].mean()), 3) for j in range(len(CLUSTER_FEATURES))}
		top = [[n, round(v / max(1, nrows[c]), 3)] for n, v in draft[c].most_common(8)]
		arche.append({"id": c, "members": mem, "feature_means": means, "strong_team_pick_rate": top, "team_sides": nrows[c]})
	out = {
		"origin": "COMPUTED (clusters); strong_team_pick_rate LEARNED (current-patch opponent drafts)",
		"features": [c for c, _ in CLUSTER_FEATURES], "transforms": [t for _, t in CLUSTER_FEATURES],
		"mean": mu.round(6).tolist(), "std": sd.round(6).tolist(),
		"pca_components": pca.components_.round(6).tolist(), "pca_explained": pca.explained_variance_ratio_.round(4).tolist(),
		"k": k, "silhouette": {str(kk): round(v, 4) for kk, v in sil.items()},
		"centroids_z": cz.round(6).tolist(), "centroids_pca": km.cluster_centers_.round(6).tolist(),
		"labels": {names[i]: int(lab[i]) for i in range(len(names))},
		"stability": {"bootstrap_ari_mean": round(float(np.mean(aris)), 3), "bootstrap_ari_p10": round(float(np.percentile(aris, 10)), 3),
					  "per_map_coassignment": {names[i]: round(stab[i], 3) for i in range(len(names))}},
		"hdbscan": {names[i]: int(hd.labels_[i]) for i in range(len(names))},
		"archetypes": arche,
	}
	json.dump(out, open(os.path.join(a.catalog, "archetypes.json"), "w"), indent=1)
	skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
	folds = [[names[i] for i in te] for _, te in skf.split(Z, lab)]
	json.dump({"origin": "COMPUTED", "k_archetypes": k, "folds": folds}, open(os.path.join(a.catalog, "splits.json"), "w"), indent=1)
	print(f"{len(names)} maps, {len(CLUSTER_FEATURES)} features, PCA {nc} components; silhouette " +
		  ", ".join(f"k{kk} {v:.3f}" for kk, v in sil.items()) + f"; chosen k = {k}; bootstrap ARI {np.mean(aris):.3f} (p10 {np.percentile(aris, 10):.3f})")
	for c in arche:
		print(f"  archetype {c['id']} ({len(c['members'])}): {', '.join(c['members'])}")
		print(f"     strong teams pick: {', '.join(f'{n} {v:.2f}' for n, v in c['strong_team_pick_rate'][:6])}")
	print("  HDBSCAN outliers:", ", ".join(n for n, l in out["hdbscan"].items() if l < 0) or "-")


if __name__ == "__main__":
	main()
