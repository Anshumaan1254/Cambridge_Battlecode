#!/usr/bin/env python3
"""How far the runtime fallback (plans.h = compact.py) is from the catalog's full model, and which missing mechanic would close it (the
user's change 5 of Oct 24). COMPUTED.

    python3 -I tools/mapintel/fallback_gap.py [--out experiments/results/mapintel/fallback_gap]

Per official map and team, the reference roster (the catalog's first; both teams):
  work      every body type of the roster x every reached group: the compact work (kill + heal trips + capture) against the catalog's
            solo fight (economy.fight with the fitted constants: rounds incl. heal trips, + the 6 capture rounds); the log ratio
  plan 1    the first targets of compact.plan1(picks, rank) against the same ranking assigned by the catalog economy (plan1_learn's
            fs_catalog: the table's `ref_first`): bodies with the same first target, maps with any difference
  plan 2    compact.bank_altars() against the catalog's plan-2 altar per group (`bank_routes`): groups with the same altar
Mechanics tried one at a time on top of the compact model (Python only; a mechanic goes into plans.h when it changes plan 1 or plan 2
on several maps toward the catalog and its fuel fits):
  econ      the fitted economy constants: heal trips usable down to the retreat line (1 - retreat of economy.econ() instead of 0.7) and
            the damage scale on camps (dmg_mult)
  shield    Varg / Heart of Ruin shields absorb mod x focus per cooldown of the damage taken
  stun      a camp stunned skips its attacks: damage taken x (1 - stuns per round)
  ren       Ren's retaliation: + ren_ret x focus x half the group's striking camps, per round, as damage dealt
  hor       Heart of Ruin's missing-health bonus: + 25% damage (the mean of 0 to 50% over a fight from full to the retreat line)
  walk2     plan 2 by the walk from the group to the approach tiles (one BFS per altar) instead of the Chebyshev box distance
Writes report.md and results.json."""
import argparse, json, math, os, statistics, sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compact as CP  # noqa: E402
import economy as EC  # noqa: E402
import export_headers as EH  # noqa: E402
import geometry as G  # noqa: E402
import mapdata  # noqa: E402
from engine import pick_bodies  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
MECH = ["none", "econ", "shield", "stun", "ren", "hor", "all"]


class Variant(CP.Compact):
	"""compact.Compact with one mechanic added to work()."""

	def __init__(self, M, team, mech):
		super().__init__(M, team)
		self.mech = mech

	def work(self, b, g):
		key = ("v", b, g)
		if key in self._bm:
			return self._bm[key]
		if self.mech == "none":
			v = super().work(b, g)
			self._bm[key] = v
			return v
		E = EC.engine()
		d = E.champs[b]
		S = EC.settings()
		adj, tot, Ssum = self.prep[g]
		reset = any(a["kind"] == "reset" for a in d["abilities"])
		dm = EC.econ()["dmg_mult"] if self.mech in ("econ", "all") else 1.0
		basic = d["str"] * (1.0 + (1.0 / 8.0 if reset else 0.0)) * (1.0 + (adj if b == CP.VARG else 0.0))
		single = area = shield = stun = 0.0
		for a in d["abilities"]:
			m = a.get("mod", 0.0)
			if a["kind"] == "shield":
				shield += m * d["foc"] / a["cd"]
			if a["kind"] == "cc" or (a["kind"] == "aoe" and a.get("dur", 0)) or (a["kind"] == "dash" and a.get("dur", 0)):
				stun += 1.0 / a["cd"]
			if m <= 0 or a["kind"] == "shield":
				continue
			if a["kind"] in ("damage", "cc"):
				single += m * d["foc"] / a["cd"]
			elif a["kind"] in ("aoe", "dash"):
				area += m * d["foc"] / a["cd"]
		dps = (basic + single + area * (1.0 + adj)) * dm
		if self.mech in ("hor", "all") and b == 12:
			dps *= 1.25
		kill = tot / dps
		dmg = Ssum / dps
		if self.mech in ("ren", "all") and b == 9:
			# each striking camp that hits Ren takes ren_ret x focus back; about half the striking camps are alive on average
			nstr = sum(1 for c in self.M.groups[g]["camps"] if EC.camp_stats(c[0])[1] > 0)
			dps += S["ren_ret"] * d["foc"] * dm * nstr / 2.0
			kill, dmg = tot / dps, Ssum / dps
		if self.mech in ("shield", "all"):
			dmg = max(0.0, dmg - shield * kill)
		if self.mech in ("stun", "all"):
			dmg *= max(0.0, 1.0 - min(1.0, stun))
		use = (1.0 - EC.econ()["retreat"]) if self.mech in ("econ", "all") else 0.7
		trips = max(0, math.ceil(dmg / (use * d["hp"])) - 1)
		dU = self.dU[g]
		v = kill + trips * (min(dU, 6) + 1 + dU) + 6.0
		self._bm[key] = v
		return v

	def row(self, b):
		key = ("row", b)
		if key not in self._bm:
			E = EC.engine()
			rng = E.attack_range(b)
			rate = {g: self.val[g] / (max(0, self.dU[g] - rng) + self.work(b, g)) for g in range(len(self.M.groups)) if self.dU[g] >= 0}
			self._bm[key] = (sorted(rate, key=lambda g: (-rate[g], g))[:CP.NTOP], rate)
		return self._bm[key]


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--out", default=os.path.join(ROOT, "experiments/results/mapintel/fallback_gap"))
	a = ap.parse_args()
	os.makedirs(a.out, exist_ok=True)
	import catalog as CT
	import plans as P
	R = json.load(open(os.path.join(ROOT, "tools/mapintel/data/battery_rosters.json")))
	ftw = json.load(open(os.path.join(ROOT, "experiments/results/mapintel/first_targets/weights.json")))
	tf = json.load(open(os.path.join(ROOT, "experiments/results/mapintel/plan1/table_first.json")))["maps"]
	res = {m: {"work_logratio": [], "plan1_same": 0, "plan1_bodies": 0, "plan1_maps_diff": 0, "plan1_changed_maps": 0} for m in MECH}
	p2 = {"compact": [0, 0], "walk2": [0, 0]}
	per_map = {}
	for mp in mapdata.official_names():
		M = mapdata.load(mp)
		refs = CT.reference_rosters(mp, M.team_size, R)
		if not refs or mp not in tf:
			continue
		picks = refs[0]["picks"]
		ctx = P.Ctx(M)
		cat = json.load(open(os.path.join(ROOT, "maps/catalog", mp + ".json")))
		gid = {grp["id"]: i for i, grp in enumerate(M.groups)}
		row = {}
		for t in (0, 1):
			rank = EH.first_rank_py(M, t, ftw, 16)
			target = [gid.get(g) if g is not None else None for g in tf[mp]["first"][t]]
			base_first = None
			bodies = [b for p in picks for b in pick_bodies(p)][:CP.NSLOT]
			for mech in MECH:
				V = Variant(M, t, mech)
				_, pl = V.plan1(picks, rank)
				first = [x[0][0] if x else None for x in pl]
				if mech == "none":
					base_first = first
				same = sum(1 for x, y in zip(first, target) if x == y)
				res[mech]["plan1_same"] += same
				res[mech]["plan1_bodies"] += len(bodies)
				res[mech]["plan1_maps_diff"] += 1 if same < len(bodies) else 0
				res[mech]["plan1_changed_maps"] += 1 if first != base_first else 0
				row[(t, mech)] = same
				if t == 0:
					for b in sorted(set(bodies)):
						for g in range(len(M.groups)):
							if V.dU[g] < 0:
								continue
							r = EC.fight(M, t, [EC.Champ(b)], M.groups[g], ctx.home(t))
							if r.cleared:
								res[mech]["work_logratio"].append(math.log(V.work(b, g) / (r.rounds + 6.0)))
			# plan 2
			C = CP.Compact(M, t)
			bank_c = C.bank_altars()
			want = {}
			for r_ in cat["bank_routes"]:
				for tt in r_["teams"]:
					if tt["team"] == t and tt.get("altar") is not None and r_["group"] in gid:
						want[gid[r_["group"]]] = tt["altar"]
			ok = ~(M.walls | M.holes | M.altars)
			af = []
			for (ax, ay) in M.altar_tiles:
				msk = np.zeros_like(M.walls)
				msk[max(0, ay - 1):ay + 2, max(0, ax - 1):ax + 2] = True
				af.append(G.bfs(C.C[t], msk & ok & C.C[t]))
			for g, alt in want.items():
				p2["compact"][1] += 1
				p2["compact"][0] += 1 if bank_c[g] == alt else 0
				best = None
				for k, f in enumerate(af):
					ds = [int(f[c[2], c[1]]) for c in M.groups[g]["camps"] if f[c[2], c[1]] >= 0]
					sp = [int(f[y, x]) for y, x in zip(*np.nonzero(M.spawn[t])) if f[y, x] >= 0]
					cost = min(([min(ds)] if ds else []) + ([6 + min(sp)] if sp else []), default=None)
					if cost is not None and (best is None or cost < best[0]):
						best = (cost, k)
				p2["walk2"][1] += 1
				p2["walk2"][0] += 1 if best and best[1] == alt else 0
		per_map[mp] = {f"{t}_{m}": v for (t, m), v in row.items()}
	out = {m: {"work_log_ratio_median": float(np.median(v["work_logratio"])) if v["work_logratio"] else None,
			   "work_abs_log_ratio_median": float(np.median(np.abs(v["work_logratio"]))) if v["work_logratio"] else None,
			   "plan1_body_agreement": v["plan1_same"] / max(1, v["plan1_bodies"]), "plan1_map_teams_differing": v["plan1_maps_diff"],
			   "plan1_map_teams_changed": v["plan1_changed_maps"]} for m, v in res.items()}
	out["plan2"] = {k: v[0] / max(1, v[1]) for k, v in p2.items()}
	out["per_map"] = per_map
	json.dump(out, open(os.path.join(a.out, "results.json"), "w"), indent=1)
	L = ["# The runtime fallback (plans.h) against the catalog's full model\n",
		 "Reference roster per map, both teams. work: log(compact work / catalog solo fight rounds + 6) over body x group; plan 1: bodies "
		 "whose compact first target equals the table's (same ranking, catalog economy); map-teams whose plan 1 the mechanic changes.\n",
		 "| mechanic | work log ratio (median) | abs (median) | plan 1 body agreement | map-teams differing | map-teams changed by it |",
		 "|---|---|---|---|---|---|"]
	for m in MECH:
		o = out[m]
		L.append(f"| {m} | {o['work_log_ratio_median']:+.3f} | {o['work_abs_log_ratio_median']:.3f} | {o['plan1_body_agreement']:.3f} | "
				 f"{o['plan1_map_teams_differing']} | {o['plan1_map_teams_changed']} |")
	L += ["", f"Plan 2 (the bank altar per group equal to the catalog's): compact box distance {out['plan2']['compact']:.3f}, walk from the group "
		  f"(one BFS per altar) {out['plan2']['walk2']:.3f}."]
	open(os.path.join(a.out, "report.md"), "w").write("\n".join(L) + "\n")
	print("\n".join(L))


if __name__ == "__main__":
	main()
