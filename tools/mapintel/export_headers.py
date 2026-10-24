#!/usr/bin/env python3
"""Generate the data headers of the mapintel library (MAPAnalysis.md 5.8, step 8) from the catalog and the step-6 models.

    python3 -I tools/mapintel/export_headers.py [--catalog maps/catalog] [--weights experiments/results/mapintel/draft_model/weights.json]
                                                [--out tools/mapintel/cpp/mapintel]

known_maps.h   the exact-match table (the user's approved hardcoding: ISSUES.md "mapintel"): one entry per official map, keyed by the
               fingerprint the engine computed (experiments/results/mapintel/dump/fingerprints.txt, the C++ function in the engine) and
               sorted by it for find_known(). Per entry, team-relative data for both teams (index 0 = team A = the team whose spawn is
               listed first in the dump, see team_of_spawn()):
                 COMPUTED (catalog: the detailed fight simulation and planner): per group the bank altar and how (walk / recall / dash /
                 crystal), the walking ETA, the contested flag, the priority; plan 4's thresholds; the first contact round; the
                 reference roster's plan-1 first targets.
                 LEARNED (draft_prior.json, the current-patch ladder): games, strong teams' pick rates, and the draft model's champion
                 values for this map (log-odds x 1000, team rating held fixed).
model_weights.h  the fallback for unknown maps: the runtime-feature transform (which features, log / log1p, mean and std), the
               archetype PCA basis and centroids (archetype_of(): the same assignment as archetypes.json's labels), and the draft model
               value_c(map) = w_c + v_c . z(map) (champion_values()). Origins in the comments.
Both headers are plain C++20 + the SDK, include features.h, and cost a few thousand fuel per call."""
import argparse, json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import features as FT  # noqa: E402
import mapdata  # noqa: E402
from archetypes import CLUSTER_FEATURES  # noqa: E402
from engine import PICK_NAMES  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HOW = {"walk": 0, "recall": 1, "dash": 2, "crystal": 3}
TR = {"id": 0, "log": 1, "log1p": 2}


def arr(vals, fmt="{}"):
	return "{ " + ", ".join(fmt.format(v) for v in vals) + " }"


def clamp8(v):
	return 255 if v is None or v < 0 or v > 254 else int(v)


def zfeat_py(F, arche):
	"""The runtime z-vector of model_weights.h from a features.py vector (the C++ function does the same)."""
	out = []
	for j, (col, how) in enumerate(CLUSTER_FEATURES):
		v = float(F[FT.NAMES.index(col[2:])])
		v = np.log(max(v, 1e-6)) if how == "log" else np.log1p(max(v, 0.0)) if how == "log1p" else v
		out.append((v - arche["mean"][j]) / arche["std"][j])
	return np.array(out)


def archetype_py(z, arche):
	y = np.array(arche["pca_components"]) @ z
	c = np.array(arche["centroids_pca"])
	return int(np.argmin(((c - y) ** 2).sum(1)))


def known_maps(cat, prior, weights, arche, fps):
	entries = []
	for name in mapdata.official_names():
		d = json.load(open(os.path.join(cat, name + ".json")))
		G = len(d["groups"])
		if G > 64:
			sys.exit(f"{name}: {G} groups > 64")
		bank = [[255] * G for _ in range(2)]
		how = [[255] * G for _ in range(2)]
		for r in d["bank_routes"]:
			for t in r["teams"]:
				if t.get("altar") is not None:
					bank[t["team"]][r["group"]] = clamp8(t["altar"])
					how[t["team"]][r["group"]] = HOW.get(t.get("how"), 255)
		eta = [[clamp8(g["eta"][t]) for g in d["groups"]] for t in range(2)]
		flags = [(1 if g.get("contested") else 0) | (2 if g.get("middle_band") else 0) | (4 if g.get("race_winner") == "A" else 8 if g.get("race_winner") == "B" else 0)
				 for g in d["groups"]]
		prio = [int(round(100 * min(320.0, g.get("priority", 0.0)))) for g in d["groups"]]
		p4 = d["plan4"]
		thr = [p4["k_abandon"], int(round(100 * p4["p_power"])), p4["d_regroup"], p4["r_enemies"], p4["bank_margin"], p4["contested_groups"],
			   p4["spawn_distance"], d["first_contact"]["round"] if d["first_contact"]["round"] is not None else 65535]
		P = prior["maps"].get(name, {"games": 0, "champions": [{"pick_rate_strong": 0}] * 12})
		pick = [int(round(200 * c["pick_rate_strong"])) for c in P["champions"]]
		vals = weights["per_map_values"].get(name) if weights else None
		value = [int(round(1000 * vals[PICK_NAMES[c]])) for c in range(12)] if vals else [0] * 12
		ref = d["reference_rosters"][0] if d["reference_rosters"] else {"picks": []}
		first = [[255] * 6 for _ in range(2)]
		for p in d["plan1"]:
			if p["roster"] == ref.get("names") and p.get("plan1"):
				for k, g in enumerate(p["plan1"]["first_targets"][:6]):
					first[p["team"]][k] = clamp8(g)
		roster = (list(ref.get("picks", [])) + [255] * 5)[:5]
		M = mapdata.load(name)
		z = zfeat_py(FT.compute(M, 0), arche)
		ys, xs = np.nonzero(M.spawn[0])
		spawn_a = int(min(ys * M.W + xs))
		entries.append(dict(fp=int(fps[name], 16), name=name, ts=d["team_size"], spawn_a=spawn_a, arch=archetype_py(z, arche), G=G, games=P["games"],
							bank=bank, how=how, eta=eta, flags=flags, prio=prio, thr=thr, pick=pick, value=value, roster=roster, first=first))
	entries.sort(key=lambda e: e["fp"])
	L = ["// mapintel/known_maps.h: GENERATED by tools/mapintel/export_headers.py; do not edit (MAPAnalysis.md 5.8).",
		 "// The exact-match table of the official maps (the user's approved hardcoding; ISSUES.md, mapintel section): a map whose fingerprint",
		 "// is here gets the catalog's offline plans and the ladder's draft data; any other map falls back to plans.h / model_weights.h.",
		 "// Team index t: 0 = team A in the engine, 1 = team B (known_team() finds ours from the ally spawn region). Origins: bank / how / eta / flags / prio / thr / first = COMPUTED (catalog);",
		 "// games / pick_strong = LEARNED (current-patch ladder, " + str(sum(e["games"] for e in entries)) + " games); value = " +
		 (weights["origin"] if weights else "none") + ".",
		 "#pragma once", "#include <cambc.h>", "#include <cstdint>", '#include "features.h"', "", "namespace mapintel", "{",
		 "inline constexpr int KNOWN_VERSION = 1;", f"inline constexpr int NKNOWN = {len(entries)};", "",
		 "struct KnownMap", "{",
		 "\tstd::uint64_t fp;",
		 "\tconst char* name;",
		 "\tstd::uint8_t team_size, archetype, ngroups;",
		 "\tstd::int32_t spawn_a;                 // team A's lowest spawn tile index (y * W + x): known_team()",
		 "\tstd::uint16_t games;                  // LEARNED sample size (ranked games on this map)",
		 "\tconst std::uint8_t* bank;             // [2 * ngroups] bank altar per team and group (row-major altar index; 255 none)",
		 "\tconst std::uint8_t* how;              // [2 * ngroups] 0 walk, 1 recall then walk, 2 dash, 3 crystal, 255 none",
		 "\tconst std::uint8_t* eta;              // [2 * ngroups] walking rounds from the team's spawn to the group (255 = none / >= 255)",
		 "\tconst std::uint8_t* flags;            // [ngroups] bit 0 contested, 1 middle band, 2 team A wins the race, 3 team B wins it",
		 "\tconst std::uint16_t* priority;        // [ngroups] plan 3 priority x 100",
		 "\tstd::uint16_t thr[8];                 // plan 4: k_abandon, p_power x 100, d_regroup, r_enemies, bank_margin, contested groups,",
		 "\t                                      //         spawn distance, first contact round",
		 "\tstd::uint8_t pick_strong[12];         // LEARNED: strong teams' pick rate x 200, draft-pick order (champion_draft ids)",
		 "\tstd::int16_t value[12];               // draft model value x 1000 (log-odds; model_weights.h names its origin)",
		 "\tstd::uint8_t ref_roster[5];           // the most frequent strong-team roster (draft ids; 255 = none)",
		 "\tstd::uint8_t ref_first[2][6];         // its plan-1 first target group per body, per team (COMPUTED; 255 = none)",
		 "};", ""]
	for k, e in enumerate(entries):
		G = e["G"]
		L.append(f"inline constexpr std::uint8_t KM{k}_bank[] = {arr(e['bank'][0] + e['bank'][1])};")
		L.append(f"inline constexpr std::uint8_t KM{k}_how[] = {arr(e['how'][0] + e['how'][1])};")
		L.append(f"inline constexpr std::uint8_t KM{k}_eta[] = {arr(e['eta'][0] + e['eta'][1])};")
		L.append(f"inline constexpr std::uint8_t KM{k}_flags[] = {arr(e['flags'])};")
		L.append(f"inline constexpr std::uint16_t KM{k}_prio[] = {arr(e['prio'])};")
	L += ["", "inline constexpr KnownMap KNOWN[NKNOWN] = {"]
	for k, e in enumerate(entries):
		L.append(f"\t{{ 0x{e['fp']:016x}ull, \"{e['name']}\", {e['ts']}, {e['arch']}, {e['G']}, {e['spawn_a']}, {e['games']}, KM{k}_bank, KM{k}_how, KM{k}_eta, KM{k}_flags, "
				 f"KM{k}_prio, {arr(e['thr'])}, {arr(e['pick'])}, {arr(e['value'])}, {arr(e['roster'])}, {{ {arr(e['first'][0])}, {arr(e['first'][1])} }} }}, /* map {e['name']} */")
	L += ["};", "",
		  "// The table entry of this fingerprint (features.h: fingerprint(view)), or -1: a binary search over the sorted fingerprints.",
		  "inline int find_known(std::uint64_t fp)", "{", "\tint lo = 0, hi = NKNOWN - 1;", "\twhile (lo <= hi)", "\t{",
		  "\t\tconst int mid = (lo + hi) / 2;", "\t\tif (KNOWN[mid].fp == fp)", "\t\t\treturn mid;", "\t\tif (KNOWN[mid].fp < fp)", "\t\t\tlo = mid + 1;",
		  "\t\telse", "\t\t\thi = mid - 1;", "\t}", "\treturn -1;", "}", "",
		  "// Our team's index in a table entry: 0 when our spawn region holds team A's lowest spawn tile, else 1.",
		  "inline int known_team(const MapView& m, const KnownMap& e)", "{",
		  "\tfor (const int t : m.spawn_tiles[0])", "\t\tif (t == e.spawn_a)", "\t\t\treturn 0;", "\treturn 1;", "}", "} // namespace mapintel", ""]
	return "\n".join(L), entries


def first_rank_py(M, team, ftw, n=16):
	"""The groups ranked by the LEARNED first-target score (first_targets.py), ties by group index: first_scores() in C++."""
	import first_targets as FTG
	tab = FTG.group_table(M, team)
	mu, sd, w = np.array(ftw["mean"]), np.array(ftw["std"]), np.array(ftw["coef"])
	sc = {}
	for g, x in tab.items():
		if ftw.get("use") == "forest":
			sc[g] = float(FTG.forest_score(ftw["forest"], np.array([x], dtype=float))[0])
			continue
		z = (np.array(x, dtype=float) - mu) / sd
		v = ftw["intercept"]
		for j in range(len(z)):
			v += w[j] * z[j]
		sc[g] = v
	return [g for g in sorted(sc, key=lambda g: (-sc[g], g))][:n]


def tree_expr(tree, k=0):
	"""One tree of the forest as a nested C++ conditional (x[f] <= thr goes left): compiled code, no node walk."""
	f_, thr, l, r, leaf, val = tree[k]
	if leaf:
		return repr(val)
	return f"(x[{f_}] <= {thr!r} ? {tree_expr(tree, l)} : {tree_expr(tree, r)})"


def model_weights(arche, weights, ftw=None):
	nf = len(CLUSTER_FEATURES)
	fi = [FT.NAMES.index(c[2:]) for c, _ in CLUSTER_FEATURES]
	L = ["// mapintel/model_weights.h: GENERATED by tools/mapintel/export_headers.py; do not edit (MAPAnalysis.md 5.8).",
		 "// The fallback for maps the table does not know, computed from the runtime features (features.h):",
		 "//   zfeat()            the standardised feature vector (archetypes.py's features, transforms, mean and std over the 40 official maps)",
		 "//   archetype_of(z)    nearest k-means centroid in the archetypes' PCA space (COMPUTED; = archetypes.json's labels on the 40 maps)",
		 "//   champion_values(z) the draft model's value of each champion on this map, log-odds per champion difference (" +
		 (f"{weights['origin']}, {weights['model']} of tools/mapintel/draft_learn.py" if weights else "not fitted yet: zeros") + ";",
		 "//                      on the ladder no champion model beats team rating alone out of sample, so the values come from a battery)",
		 "//   first_scores(C)    LEARNED score of each group as an opening target (first_targets.py: the top teams' first captures)",
		 "#pragma once", "#include <algorithm>", "#include <array>", "#include <cmath>", "#include <vector>", '#include "features.h"', '#include "plans.h"', "",
		 "namespace mapintel", "{",
		 f"inline constexpr int MW_NF = {nf};",
		 f"inline constexpr int MW_FI[MW_NF] = {arr(fi)};  // indices into FEATURE_NAMES: " + ", ".join(c[2:] for c, _ in CLUSTER_FEATURES),
		 f"inline constexpr int MW_TR[MW_NF] = {arr([TR[t] for _, t in CLUSTER_FEATURES])};  // 0 identity, 1 log(max(v, 1e-6)), 2 log1p(max(v, 0))",
		 f"inline constexpr double MW_MEAN[MW_NF] = {arr(arche['mean'], '{!r}')};",
		 f"inline constexpr double MW_STD[MW_NF] = {arr(arche['std'], '{!r}')};",
		 f"inline constexpr int NARCH = {arche['k']}, MW_NPC = {len(arche['pca_components'])};",
		 "inline constexpr double MW_PCA[MW_NPC][MW_NF] = {"]
	L += ["\t" + arr(r, "{!r}") + "," for r in arche["pca_components"]]
	L += ["};", "inline constexpr double MW_CENT[NARCH][MW_NPC] = {"]
	L += ["\t" + arr(r, "{!r}") + "," for r in arche["centroids_pca"]]
	L += ["};"]
	w = weights["w"] if weights else [0.0] * 12
	v = weights.get("v", [[0.0] * nf for _ in range(12)]) if weights else [[0.0] * nf for _ in range(12)]
	L += [f"inline constexpr double MW_W[12] = {arr(w, '{!r}')};  // per champion (draft ids), log-odds", "inline constexpr double MW_V[12][MW_NF] = {"]
	L += ["\t" + arr(r, "{!r}") + "," for r in v]
	L += ["};", "",
		  "inline void zfeat(const Features& F, double z[MW_NF])", "{", "\tfor (int j = 0; j < MW_NF; ++j)", "\t{",
		  "\t\tdouble v = F.v[static_cast<std::size_t>(MW_FI[j])];",
		  "\t\tv = MW_TR[j] == 1 ? std::log(v > 1e-6 ? v : 1e-6) : MW_TR[j] == 2 ? std::log1p(v > 0.0 ? v : 0.0) : v;",
		  "\t\tz[j] = (v - MW_MEAN[j]) / MW_STD[j];", "\t}", "}", "",
		  "inline int archetype_of(const double z[MW_NF])", "{", "\tint best = 0;", "\tdouble bd = 0;", "\tdouble y[MW_NPC];",
		  "\tfor (int p = 0; p < MW_NPC; ++p)", "\t{", "\t\ty[p] = 0;", "\t\tfor (int j = 0; j < MW_NF; ++j)", "\t\t\ty[p] += MW_PCA[p][j] * z[j];", "\t}",
		  "\tfor (int c = 0; c < NARCH; ++c)", "\t{", "\t\tdouble d = 0;", "\t\tfor (int p = 0; p < MW_NPC; ++p)",
		  "\t\t\td += (MW_CENT[c][p] - y[p]) * (MW_CENT[c][p] - y[p]);", "\t\tif (c == 0 || d < bd)", "\t\t\tbd = d, best = c;", "\t}", "\treturn best;", "}", "",
		  "inline void champion_values(const double z[MW_NF], double out[12])", "{", "\tfor (int c = 0; c < 12; ++c)", "\t{", "\t\tdouble v = MW_W[c];",
		  "\t\tfor (int j = 0; j < MW_NF; ++j)", "\t\t\tv += MW_V[c][j] * z[j];", "\t\tout[c] = v;", "\t}", "}", ""]
	if ftw:
		k = len(ftw["coef"])
		forest = ftw.get("use") == "forest"
		desc = (f"boosted forest, {ftw['forest']['n_trees']} trees of depth {ftw['forest']['depth']}, held-out top-n share {ftw['forest']['cv_share']}"
				if forest else f"logistic, held-out top-n share {ftw['cv_share']}") + f" vs nearest {ftw['nearest_share']}"
		L += [f"// first_targets.py ({ftw['samples']} team-games; {desc}): features " + ", ".join(ftw["features"]),
			  "#define MAPINTEL_FIRST_SCORES 1",
			  f"inline constexpr int FT_NF = {k};",
			  f"inline constexpr double FT_MEAN[FT_NF] = {arr(ftw['mean'], '{!r}')};",
			  f"inline constexpr double FT_STD[FT_NF] = {arr(ftw['std'], '{!r}')};",
			  f"inline constexpr double FT_COEF[FT_NF] = {arr(ftw['coef'], '{!r}')};",
			  f"inline constexpr double FT_B = {ftw['intercept']!r};", ""]
		if forest:
			L += [f"inline constexpr double FT_GB = {ftw['forest']['baseline']!r};  // forest baseline; the trees are the conditionals in first_scores()", ""]
		L += [
			  "// The group features of the step-6 / step-7 models, in the order of first_targets.FEATS then make_dataset.GFEATS' extras:",
			  "// dU, dE (999 = not reached), dU - dE, rank of dU, gems, gold, value, total health, S, camps, heavy, contested, value share,",
			  "// log1p(dU), then the camp counts per type (wolf, elk, gem, gold, monolith, golem), respawn / 100, max camp strength / 100.",
			  "inline constexpr int GF_N = 22;",
			  "inline std::vector<std::array<double, GF_N>> group_features(const Compact& C, const MapView& m, std::vector<char>& reached)", "{",
			  "\tconst int G = static_cast<int>(C.dU.size());", "\tstd::vector<std::array<double, GF_N>> out(static_cast<std::size_t>(G));",
			  "\treached.assign(static_cast<std::size_t>(G), 0);",
			  "\tPlans P;", "\tC.contested(P);", "\tstd::vector<int> order;",
			  "\tdouble total = 0;", "\tfor (int g = 0; g < G; ++g)", "\t\tif (C.dU[static_cast<std::size_t>(g)] >= 0)",
			  "\t\t\torder.push_back(g), total += C.val[static_cast<std::size_t>(g)];",
			  "\tif (total == 0)", "\t\ttotal = 1.0;",
			  "\tstd::sort(order.begin(), order.end(), [&](int a, int b) { return C.dU[static_cast<std::size_t>(a)] != C.dU[static_cast<std::size_t>(b)] ? C.dU[static_cast<std::size_t>(a)] < C.dU[static_cast<std::size_t>(b)] : a < b; });",
			  "\tfor (int r = 0; r < static_cast<int>(order.size()); ++r)", "\t{",
			  "\t\tconst auto g = static_cast<std::size_t>(order[static_cast<std::size_t>(r)]);", "\t\tconst auto& grp = m.groups[g];",
			  "\t\tconst double dU = C.dU[g], dE = C.dE[g] >= 0 ? C.dE[g] : 999;", "\t\tdouble heavy = 0, mx = 0;", "\t\tint cnt[6]{};",
			  "\t\tfor (const auto& c : grp.camps)", "\t\t{", "\t\t\tif (c.type == 4 || c.type == 5)", "\t\t\t\theavy = 1;",
			  "\t\t\tif (c.type >= 0 && c.type < 6)", "\t\t\t\t++cnt[c.type];", "\t\t\tmx = std::max(mx, static_cast<double>(c.str));", "\t\t}",
			  "\t\tout[g] = { dU, dE, dU - dE, static_cast<double>(r), static_cast<double>(grp.gems), static_cast<double>(grp.gold), C.val[g],",
			  "\t\t\tC.prep[g].tot, C.prep[g].S, static_cast<double>(grp.camps.size()), heavy,",
			  "\t\t\tC.dE[g] >= 0 && std::abs(C.dU[g] - C.dE[g]) <= P.band ? 1.0 : 0.0, C.val[g] / total, std::log1p(dU),",
			  "\t\t\tstatic_cast<double>(cnt[0]), static_cast<double>(cnt[1]), static_cast<double>(cnt[2]), static_cast<double>(cnt[3]),",
			  "\t\t\tstatic_cast<double>(cnt[4]), static_cast<double>(cnt[5]), grp.respawn / 100.0, mx / 100.0 };",
			  "\t\treached[g] = 1;", "\t}", "\treturn out;", "}", "",
			  "// LEARNED opening score of every group (higher = the top teams capture it earlier); unreached groups get -1e300.",
			  "inline std::vector<double> first_scores(const Compact& C, const MapView& m, const Features& F)", "{",
			  "\tstd::vector<char> reached;", "\tconst auto gf = group_features(C, m, reached);",
			  "\tstd::vector<double> out(gf.size(), -1e300);", "\tfor (std::size_t g = 0; g < gf.size(); ++g)", "\t{",
			  "\t\tif (!reached[g])", "\t\t\tcontinue;", "\t\tconst double* x = gf[g].data();",
			  ] + (["\t\tdouble v = FT_GB;"] + ["\t\tv += " + tree_expr(tree) + ";" for tree in ftw["forest"]["trees"]]
				   if forest else ["\t\tdouble v = FT_B;", "\t\tfor (int j = 0; j < FT_NF; ++j)", "\t\t\tv += FT_COEF[j] * ((x[j] - FT_MEAN[j]) / FT_STD[j]);"]) + [
			  "\t\tout[g] = v;", "\t}", "\t(void)F;", "\treturn out;", "}", ""]
	L += ["} // namespace mapintel", ""]
	return "\n".join(L)


def champion_values_py(z, weights):
	out = []
	for c in range(12):
		v = weights["w"][c] if weights else 0.0
		if weights and "v" in weights:
			for j in range(len(z)):
				v += weights["v"][c][j] * z[j]
		out.append(v)
	return out


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--catalog", default=os.path.join(ROOT, "maps/catalog"))
	ap.add_argument("--weights", default=os.path.join(ROOT, "experiments/results/mapintel/draft_model/weights.json"))
	ap.add_argument("--out", default=os.path.join(ROOT, "tools/mapintel/cpp/mapintel"))
	a = ap.parse_args()
	arche = json.load(open(os.path.join(a.catalog, "archetypes.json")))
	prior = json.load(open(os.path.join(a.catalog, "draft_prior.json")))
	# the draft values: the roster battery's fit (SIMULATED, strength fixed by design) when present; the ladder's fit has no
	# out-of-sample signal over team rating (draft_learn.py report)
	sim = os.path.join(os.path.dirname(a.weights), "weights_sim.json")
	weights = json.load(open(sim)) if os.path.exists(sim) else json.load(open(a.weights)) if os.path.exists(a.weights) else None
	ftp = os.path.join(ROOT, "experiments/results/mapintel/first_targets/weights.json")
	ftw = json.load(open(ftp)) if os.path.exists(ftp) else None
	fps = {}
	for line in open(os.path.join(ROOT, "experiments/results/mapintel/dump/fingerprints.txt")):
		n, fp, _ = line.split()
		fps[n] = fp
	text, entries = known_maps(a.catalog, prior, weights, arche, fps)
	bad = [e["name"] for e in entries if e["arch"] != arche["labels"][e["name"]]]
	if bad:
		sys.exit(f"archetype_of differs from the labels on {bad}")
	open(os.path.join(a.out, "known_maps.h"), "w").write(text)
	open(os.path.join(a.out, "model_weights.h"), "w").write(model_weights(arche, weights, ftw))
	print(f"known_maps.h: {len(entries)} maps ({sum(e['games'] for e in entries)} LEARNED games); model_weights.h: {len(CLUSTER_FEATURES)} features, "
		  f"{arche['k']} archetypes (labels reproduced on all 40), draft model {weights['model'] if weights else 'none'}")


if __name__ == "__main__":
	main()
