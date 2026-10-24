#!/usr/bin/env python3
"""3C of MAPAnalysis.md: the economy model and the plans against the current-patch top teams' real games (LEARNED), and the per-group
behaviour targets for step 6.

    python3 -I tools/mapintel/validate_ladder.py [--summaries experiments/results/mapintel/ladder_20261024] [--catalog maps/catalog]
                                                 [--out experiments/results/mapintel/ladder_validation]

Inputs: replays.py's per-game summaries of the downloaded replays (strong vs strong first) and the catalog (COMPUTED). Checks:
  pace       per map: the model's unopposed pace (catalog 'pace', the reference rosters) vs the games' finish (the winner's round to 1000
             banked gems; games ended on the round limit count as 2000) and vs each team's banked gems at round 400; Spearman over maps
  first      per game and team: the model's plan-1 first targets (catalog 'plan1' of the reference roster, that team) vs the groups the team
             captured first (its first n distinct groups, n = bodies): the share of the model's targets among them, against a baseline
             (the same share for the n nearest groups by walking distance)
  bank       plan 2's bank altars (catalog 'bank_routes', per team) vs the altars the team banked at: the share of bank events at an
             altar plan 2 names for some group, and at the altar nearest to the spawn
Outputs: report.md, per_map.csv, and maps/catalog/behaviour.json (per map, team and group: games, how often captured first-n, median
first-capture round, captures per game; per map and team: bank events per altar) for the table and step 6."""
import argparse, csv, glob, json, os, statistics, sys
from collections import Counter, defaultdict

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mapdata  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def finish_round(S):
	"""The winner's first round at >= 1000 banked gems (the banked series every 25 rounds; the final round when it ends by gems)."""
	if S.get("end") == "gems":
		return S["final_round"]
	return 2000


def banked_at(S, team, rnd):
	best = 0
	for row in S["banked"]:
		if row[0] <= rnd:
			best = row[1 + team]
	return best


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--summaries", default=os.path.join(ROOT, "experiments/results/mapintel/ladder_20261024"))
	ap.add_argument("--catalog", default=os.path.join(ROOT, "maps/catalog"))
	ap.add_argument("--out", default=os.path.join(ROOT, "experiments/results/mapintel/ladder_validation"))
	a = ap.parse_args()
	os.makedirs(a.out, exist_ok=True)
	games = defaultdict(list)
	for f in sorted(glob.glob(os.path.join(a.summaries, "*.json"))):
		S = json.load(open(f))
		if S.get("map") and not S.get("error"):
			games[S["map"]].append(S)
	rows, beh = [], {}
	share_m, share_b, bank_plan, bank_near, nfirst = [], [], [], [], 0
	for mp in mapdata.official_names():
		gs = games.get(mp, [])
		d = json.load(open(os.path.join(a.catalog, mp + ".json")))
		M = mapdata.load(mp)
		model_pace = statistics.median([p["pace"] if p["pace"] is not None else 2000 for p in d["pace"]]) if d["pace"] else None  # unfinished = the round limit
		fin = [finish_round(S) for S in gs]
		b400 = [banked_at(S, t, 400) for S in gs for t in (0, 1)]
		# per team: plan-1 first targets of the reference roster; nearest-n baseline from the catalog's walking ETAs
		ref = d["reference_rosters"][0]["names"] if d["reference_rosters"] else None
		model_first = {p["team"]: p["plan1"]["first_targets"] for p in d["plan1"] if p["roster"] == ref and p.get("plan1")}
		eta = {t: [g["eta"][t] if g["eta"][t] is not None else 9999 for g in d["groups"]] for t in (0, 1)}
		plan_alt = {t: {r_["altar"] for r in d["bank_routes"] for r_ in r["teams"] if r_["team"] == t and r_.get("altar") is not None} for t in (0, 1)}
		G = len(d["groups"])
		first_n = {t: Counter() for t in (0, 1)}
		first_round = {t: defaultdict(list) for t in (0, 1)}
		caps = {t: Counter() for t in (0, 1)}
		bank_alt = {t: Counter() for t in (0, 1)}
		for S in gs:
			fc = defaultdict(dict)
			for t, g, r in S["first_capture"]:
				fc[t][g] = r
			for t in (0, 1):
				n = len(S["drafts"][t]) + (1 if 3 in S["drafts"][t] else 0) if isinstance(S["drafts"][t], list) and S["drafts"][t] and isinstance(S["drafts"][t][0], int) else M.team_size
				order = [g for g, _ in sorted(fc[t].items(), key=lambda kv: (kv[1], kv[0]))][:n]
				for g in order:
					first_n[t][g] += 1
				for g, r in fc[t].items():
					first_round[t][g].append(r)
				if t in model_first and order:
					mf = model_first[t][:n]
					share_m.append(len(set(mf) & set(order)) / max(1, len(mf)))
					near = sorted(range(G), key=lambda g: (eta[t][g], g))[:len(mf)]
					share_b.append(len(set(near) & set(order)) / max(1, len(near)))
					nfirst += 1
			for c in S["captures"]:
				caps[c[1]][c[3]] += 1
			for b in S["banks"]:
				t, alt = b[1], b[5]
				bank_alt[t][alt] += 1
				if alt is not None:
					bank_plan.append(alt in plan_alt[t])
		for t in (0, 1):
			if bank_alt[t]:
				near_alt = min(range(len(M.altar_tiles)), key=lambda k: min(max(abs(M.altar_tiles[k][0] - x), abs(M.altar_tiles[k][1] - y))
																			  for y, x in zip(*np.nonzero(M.spawn[t]))))
				tot = sum(bank_alt[t].values())
				bank_near.append(bank_alt[t][near_alt] / tot)
		beh[mp] = {"games": len(gs), "teams": [{"first_n": {str(g): c for g, c in first_n[t].most_common()},
												"first_capture_median": {str(g): statistics.median(v) for g, v in sorted(first_round[t].items())},
												"captures_per_game": {str(g): round(c / max(1, len(gs)), 2) for g, c in caps[t].most_common()},
												"bank_events_per_altar": {str(k): c for k, c in bank_alt[t].most_common()}} for t in (0, 1)]}
		rows.append({"map": mp, "games": len(gs), "model_pace": model_pace, "finish_median": statistics.median(fin) if fin else None,
					 "banked_r400_median": statistics.median(b400) if b400 else None, "ends_by_gems": sum(1 for S in gs if S.get("end") == "gems")})
	ok = [r for r in rows if r["games"] and r["model_pace"]]
	rho_f = spearmanr([r["model_pace"] for r in ok], [r["finish_median"] for r in ok])[0]
	rho_b = spearmanr([r["model_pace"] for r in ok], [-r["banked_r400_median"] for r in ok])[0]
	ratio = statistics.median([r["finish_median"] / r["model_pace"] for r in ok])
	with open(os.path.join(a.out, "per_map.csv"), "w", newline="") as f:
		w = csv.DictWriter(f, fieldnames=list(rows[0]))
		w.writeheader()
		w.writerows(rows)
	json.dump({"origin": "LEARNED (current-patch ladder replays, strong vs strong first)", "summaries": os.path.relpath(a.summaries, ROOT), "maps": beh},
			  open(os.path.join(a.catalog, "behaviour.json"), "w"), indent=1)
	L = ["# The map model against the current-patch ladder (3C)\n",
		 f"{sum(r['games'] for r in rows)} decoded games on {sum(1 for r in rows if r['games'])} maps (strong vs strong first).\n",
		 f"- **Pace**: Spearman(model pace, real finish round) over {len(ok)} maps **{rho_f:.3f}**; Spearman(model pace, -banked at "
		 f"r400) **{rho_b:.3f}**; median real finish / model pace {ratio:.2f} (the model plays against the LEARNED opposition share of economy.econ()["contest"]; without it the ratio was 1.20).",
		 f"- **First targets**: over {nfirst} team-games, the share of the model's plan-1 first targets among the groups the team captured first "
		 f"is **{np.mean(share_m):.3f}** (baseline: the nearest groups by walk, {np.mean(share_b):.3f}).",
		 f"- **Bank altars**: {np.mean(bank_plan):.3f} of {len(bank_plan)} bank events are at an altar plan 2 names for some group; the share "
		 f"at the altar nearest to the team's spawn is {np.mean(bank_near):.3f} (median over map-teams).", "",
		 "| map | games | model pace | real finish (median) | banked at r400 (median) | ended by gems |", "|---|---|---|---|---|---|"]
	for r in rows:
		L.append(f"| {r['map']} | {r['games']} | {r['model_pace']} | {r['finish_median']} | {r['banked_r400_median']} | {r['ends_by_gems']} |")
	open(os.path.join(a.out, "report.md"), "w").write("\n".join(L) + "\n")
	print("\n".join(L[:6]))


if __name__ == "__main__":
	main()
