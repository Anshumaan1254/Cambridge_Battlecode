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


def known_maps(cat, prior, weights, arche, fps, table_first=None):
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
		import p4model
		lt = p4model.apply(FT.compute(mapdata.load(name), 0), [thr[0], thr[1], thr[2], thr[3], thr[4], 30, 0, 0])  # LEARNED where fitted
		thr[0], thr[1], thr[2], thr[4] = lt[0], lt[1], lt[2], lt[4]
		P = prior["maps"].get(name, {"games": 0, "champions": [{"pick_rate_strong": 0}] * 12})
		pick = [int(round(200 * c["pick_rate_strong"])) for c in P["champions"]]
		vals = weights["per_map_values"].get(name) if weights else None
		value = [int(round(1000 * vals[PICK_NAMES[c]])) for c in range(12)] if vals else [0] * 12
		ref = d["reference_rosters"][0] if d["reference_rosters"] else {"picks": []}
		first = [[255] * 6 for _ in range(2)]
		tf = table_first.get(name) if table_first else None
		if tf and tf.get("names", tf.get("roster")) == ref.get("names"):
			# LEARNED: first_scores() ranking + the catalog economy's assignment (plan1_learn.py: held out it beats the catalog's plan 1)
			for t_ in (0, 1):
				for k, g in enumerate(tf["first"][t_][:6]):
					first[t_][k] = clamp8(g) if g is not None else 255
		else:
			for p in d["plan1"]:
				if p["roster"] == ref.get("names") and p.get("plan1"):
					for k, g in enumerate(p["plan1"]["first_targets"][:6]):
						first[p["team"]][k] = clamp8(g)
		roster = (list(ref.get("picks", [])) + [255] * 5)[:5]
		M = mapdata.load(name)
		if "nav" not in d:
			sys.exit(f"{name}: no NAV blocks in the catalog: run python3 -I tools/mapintel/hazards.py --write-catalog")
		nav = list(bytes.fromhex(d["nav"]["0"])) + list(bytes.fromhex(d["nav"]["1"]))
		z = zfeat_py(FT.compute(M, 0), arche)
		ys, xs = np.nonzero(M.spawn[0])
		spawn_a = int(min(ys * M.W + xs))
		entries.append(dict(fp=int(fps[name], 16), name=name, ts=d["team_size"], spawn_a=spawn_a, arch=archetype_py(z, arche), G=G, games=P["games"],
							bank=bank, how=how, eta=eta, flags=flags, prio=prio, thr=thr, pick=pick, value=value, roster=roster, first=first,
							nav=nav))
	entries.sort(key=lambda e: e["fp"])
	L = ["// mapintel/known_maps.h: GENERATED by tools/mapintel/export_headers.py; do not edit (MAPAnalysis.md 5.8).",
		 "// The exact-match table of the official maps (the user's approved hardcoding; ISSUES.md, mapintel section): a map whose fingerprint",
		 "// is here gets the catalog's offline plans and the ladder's draft data; any other map falls back to plans.h / model_weights.h.",
		 "// Team index t: 0 = team A in the engine, 1 = team B (known_team() finds ours from the ally spawn region). Origins: bank / how / eta / flags / prio = COMPUTED (catalog); thr = COMPUTED + LEARNED (plan4_learn.py); first = LEARNED ranking (first_scores) + COMPUTED assignment (plan1_learn.py);",
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
		 "\t                                      //         spawn distance, first contact round (k, p, d, margin: LEARNED where",
		 "\t                                      //         plan4_learn.py beat the formula, for team A's features; w_max: the block)",
		 "\tstd::uint8_t pick_strong[12];         // DEFAULT draft signal, LEARNED: strong teams' pick rate x 200 on this map (champion_draft ids)",
		 "\tstd::int16_t value[12];               // SECONDARY draft signal: champion value x 1000 (log-odds; SIMULATED v10 until your bot's",
		 "\t                                      // battery replaces it; model_weights.h names its origin)",
		 "\tstd::uint8_t ref_roster[5];           // the most frequent strong-team roster (draft ids; 255 = none)",
		 "\tstd::uint8_t ref_first[2][6];         // its plan-1 first target group per body slot, per team: the first_scores() ranking's top",
		 "\t                                      // groups assigned by the catalog economy (plan1_learn.py fs_catalog; 255 = none)",
		 "\tconst std::uint8_t* nav;              // [2 * 64] the NAV draft-memory block per team (hazards.h / hazards.py, COMPUTED; byte 61 = 1:",
		 "\t                                      // dmem2.h nav_from_table() marks the copy)",
		 "};", ""]
	for k, e in enumerate(entries):
		G = e["G"]
		L.append(f"inline constexpr std::uint8_t KM{k}_bank[] = {arr(e['bank'][0] + e['bank'][1])};")
		L.append(f"inline constexpr std::uint8_t KM{k}_how[] = {arr(e['how'][0] + e['how'][1])};")
		L.append(f"inline constexpr std::uint8_t KM{k}_eta[] = {arr(e['eta'][0] + e['eta'][1])};")
		L.append(f"inline constexpr std::uint8_t KM{k}_flags[] = {arr(e['flags'])};")
		L.append(f"inline constexpr std::uint16_t KM{k}_prio[] = {arr(e['prio'])};")
		L.append(f"inline constexpr std::uint8_t KM{k}_nav[] = {arr(e['nav'])};")
	L += ["", "inline constexpr KnownMap KNOWN[NKNOWN] = {"]
	for k, e in enumerate(entries):
		L.append(f"\t{{ 0x{e['fp']:016x}ull, \"{e['name']}\", {e['ts']}, {e['arch']}, {e['G']}, {e['spawn_a']}, {e['games']}, KM{k}_bank, KM{k}_how, KM{k}_eta, KM{k}_flags, "
				 f"KM{k}_prio, {arr(e['thr'])}, {arr(e['pick'])}, {arr(e['value'])}, {arr(e['roster'])}, {{ {arr(e['first'][0])}, {arr(e['first'][1])} }}, KM{k}_nav }}, /* map {e['name']} */")
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


def model_weights(arche, weights, ftw=None, p4=None, pp=None):
	nf = len(CLUSTER_FEATURES)
	fi = [FT.NAMES.index(c[2:]) for c, _ in CLUSTER_FEATURES]
	L = ["// mapintel/model_weights.h: GENERATED by tools/mapintel/export_headers.py; do not edit (MAPAnalysis.md 5.8).",
		 "// The fallback for maps the table does not know, computed from the runtime features (features.h):",
		 "//   zfeat()            the standardised feature vector (archetypes.py's features, transforms, mean and std over the 40 official maps)",
		 "//   archetype_of(z)    nearest k-means centroid in the archetypes' PCA space (COMPUTED; = archetypes.json's labels on the 40 maps)",
		 "//   pick_prior(z)      DEFAULT draft signal for maps the table does not know: the strong teams' pick rate and first-pick share",
		 "//                      per champion from the runtime features (LEARNED, current-patch ranked games; pick_prior.py)",
		 "//   champion_values(z) SECONDARY draft signal until your bot's battery replaces it: the value of each champion on this map,",
		 "//                      log-odds per champion difference (" +
		 (f"{weights['origin']}, {weights['model']} of tools/mapintel/draft_learn.py" if weights else "not fitted yet: zeros") + ";",
		 "//                      on the ladder no champion model beats team rating alone out of sample, so the values come from a battery)",
		 "//   first_scores(C)    LEARNED score of each group as an opening target (first_targets.py: the top teams' first captures)",
		 "//   p4_thresholds()    plan 4's thresholds: the formulas, with the LEARNED ones (plan4_learn.py) written over them where the fit",
		 "//                      beat the formula on held-out maps (plans.h calls it; p4model.py is the Python twin)",
		 "//   econ_constants()   the compact work's heal-trip share and camp damage scale (LEARNED, econ_learn.py; compact.econ_constants)",
		 "#pragma once"] + (["#define MAPINTEL_P4_FITTED 1  // before plans.h: plans.h then leaves p4_thresholds() to this file"] if p4 else []) + [
		 "#define MAPINTEL_ECON_FITTED 1  // before plans.h: plans.h then leaves econ_constants() to this file",
		 "#define MAPINTEL_ECON_BODY 1    // ECON_BANK_BAG / ECON_RETREAT_PCT below (dmem2.h's BODY block)"] + [
		 "#include <algorithm>", "#include <array>", "#include <cmath>", "#include <vector>", '#include "features.h"', '#include "plans.h"', "",
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
	if pp:
		L += ["// the strong teams' pick prior (pick_prior.py, LEARNED): [0] pick rate, [1] first-pick share; per champion (draft ids) the pooled",
			  "// rate (coef 0) or a ridge over z, whichever was better on held-out maps; v = intercept + coef . z (index order), clamped to [0, 1]",
			  "#define MAPINTEL_PICK_PRIOR 1",
			  "inline constexpr double PP_B[2][12] = { " + ", ".join(arr([e["intercept"] for e in pp[k]], "{!r}") for k in ("rate", "first")) + " };",
			  "inline constexpr double PP_W[2][12][MW_NF] = {"]
		for k in ("rate", "first"):
			L += ["\t{"] + ["\t\t" + arr(e["coef"], "{!r}") + "," for e in pp[k]] + ["\t},"]
		L += ["};", "inline void pick_prior(const double z[MW_NF], double rate[12], double first[12])", "{",
			  "\tfor (int k = 0; k < 2; ++k)", "\t\tfor (int c = 0; c < 12; ++c)", "\t\t{", "\t\t\tdouble v = PP_B[k][c];",
			  "\t\t\tfor (int i = 0; i < MW_NF; ++i)", "\t\t\t\tv += PP_W[k][c][i] * z[i];", "\t\t\tv = v < 0.0 ? 0.0 : v > 1.0 ? 1.0 : v;",
			  "\t\t\t(k == 0 ? rate : first)[c] = v;", "\t\t}", "}", ""]
	if p4:
		ks = sorted(p4, key=lambda k: p4[k]["index"])
		L += ["// plan 4, LEARNED (plan4_learn.py: " + ", ".join(f"{k} {p4[k]['use']}" for k in ks) + "): t[index] = floor(intercept + coef . z + 0.5),",
			  "// clamped; the other thresholds stay the formulas (p4_formula)",
			  f"inline constexpr int P4_N = {len(ks)};", f"inline constexpr int P4_IDX[P4_N] = {arr([p4[k]['index'] for k in ks])};",
			  f"inline constexpr int P4_LO[P4_N] = {arr([int(p4[k]['lo']) for k in ks])};", f"inline constexpr int P4_HI[P4_N] = {arr([int(p4[k]['hi']) for k in ks])};",
			  f"inline constexpr double P4_B[P4_N] = {arr([p4[k]['intercept'] for k in ks], '{!r}')};", "inline constexpr double P4_W[P4_N][MW_NF] = {"]
		L += ["\t" + arr(p4[k]["coef"], "{!r}") + "," for k in ks]
		L += ["};", "inline void p4_thresholds(const Features& F, const MapView& m, int t[8])", "{", "\tp4_formula(F, m, t);", "\tdouble z[MW_NF];",
			  "\tzfeat(F, z);", "\tfor (int k = 0; k < P4_N; ++k)", "\t{", "\t\tdouble v = P4_B[k];", "\t\tfor (int i = 0; i < MW_NF; ++i)",
			  "\t\t\tv += P4_W[k][i] * z[i];", "\t\tconst double r = std::floor(v + 0.5);",
			  "\t\tt[P4_IDX[k]] = r < P4_LO[k] ? P4_LO[k] : r > P4_HI[k] ? P4_HI[k] : static_cast<int>(r);", "\t}", "}", ""]
	import compact as CP
	hu, dm = CP.econ_constants()
	import dmem2 as D2
	bb, rp = D2.econ_body()
	L += ["// the BODY block's bank bag (gems) and retreat health (percent): economy.econ()'s bank_bag and retreat line (LEARNED, econ_learn.py)",
		  f"inline constexpr int ECON_BANK_BAG = {bb}, ECON_RETREAT_PCT = {rp};", ""]
	L += ["// the compact work's economy constants (compact.econ_constants: 1 - economy.econ()'s retreat line, its dmg_mult; LEARNED)",
		  "inline void econ_constants(double& heal_use, double& dmg_mult)", "{", f"\theal_use = {hu!r}, dmg_mult = {dm!r};", "}", ""]
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
	tfp = os.path.join(ROOT, "experiments/results/mapintel/plan1/table_first.json")
	table_first = json.load(open(tfp))["maps"] if os.path.exists(tfp) else None
	text, entries = known_maps(a.catalog, prior, weights, arche, fps, table_first)
	bad = [e["name"] for e in entries if e["arch"] != arche["labels"][e["name"]]]
	if bad:
		sys.exit(f"archetype_of differs from the labels on {bad}")
	open(os.path.join(a.out, "known_maps.h"), "w").write(text)
	import p4model
	ppp = os.path.join(ROOT, "experiments/results/mapintel/draft_model/pick_prior.json")
	pp = json.load(open(ppp)) if os.path.exists(ppp) else None
	open(os.path.join(a.out, "model_weights.h"), "w").write(model_weights(arche, weights, ftw, p4model.model() or None, pp))
	print(f"known_maps.h: {len(entries)} maps ({sum(e['games'] for e in entries)} LEARNED games); model_weights.h: {len(CLUSTER_FEATURES)} features, "
		  f"{arche['k']} archetypes (labels reproduced on all 40), draft model {weights['model'] if weights else 'none'}")


if __name__ == "__main__":
	main()
