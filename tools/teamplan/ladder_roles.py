#!/usr/bin/env python3
"""Role tables from decoded top-team ladder games (TEAMPLAN.md section 3). LEARNED (current-patch ladder).

    python3 -I tools/teamplan/ladder_roles.py [--summaries DIR] [--caprows FILE.jsonl] [--out FILE.md]

--summaries: the per-game JSON files of tools/mapintel/replays.py (default experiments/results/mapintel/ladder_20261024).
--caprows:   rows of tools/teamplan/capture_rows.mjs (gem and gold-only captures; the summaries miss gold-only captures).
Writes a markdown report (stdout without --out) and a JSON twin next to it (--out X.md -> X.json): per champion capture shares, kills,
gems its kills took, deaths, bags at death, death hazard per body-round; captures shared by two or more bodies; the bag swing between
winners and losers; how games end; gold-only captures per champion (from --caprows)."""
import argparse
import collections
import glob
import json
import os
import statistics as st

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TYPES = ["Ryth", "VesperVale", "Vendetta", "Cassi", "Issac", "Stellar", "Prism", "Marcella", "Willow", "Ren", "Varg", "Tavi", "HeartOfRuin"]
DRAFT_TO_TYPES = {0: [0], 1: [1], 2: [2], 3: [3, 4], 4: [5], 5: [6], 6: [7], 7: [8], 8: [9], 9: [10], 10: [11], 11: [12]}


def bodies(draft):
	# killer index = position in the list of both teams' bodies, each team's bodies in champion-type order (checked: the killer is always
	# on the other team, 9,297 of 9,297 kills)
	return sorted(t for p in draft for t in DRAFT_TO_TYPES[p])


def load_games(d):
	games = []
	for f in sorted(glob.glob(os.path.join(d, "*.json"))):
		try:
			g = json.load(open(f))
		except (OSError, ValueError):
			continue
		if isinstance(g, dict) and "captures" in g and "drafts" in g:
			games.append(g)
	return games


def analyse(games):
	R = {"games": len(games)}
	caps, gold, gems, played, kills, took, died, bag = (collections.Counter() for _ in range(8))
	bags = collections.defaultdict(list)
	rounds_alive_proxy = collections.Counter()
	shared = events = 0
	per = []
	swing = {"win": {"took": [], "lost": []}, "loss": {"took": [], "lost": []}}
	top1 = {"win": [], "loss": []}
	ends = collections.Counter()
	for g in games:
		ends[g.get("end", "?")] += 1
		L = [(0, t) for t in bodies(g["drafts"][0])] + [(1, t) for t in bodies(g["drafts"][1])]
		for side in (0, 1):
			for t in bodies(g["drafts"][side]):
				played[TYPES[t]] += 1
				rounds_alive_proxy[TYPES[t]] += g.get("final_round", 0)
		res = [g["team_A"]["result"], g["team_B"]["result"]]
		took_t, lost_t = [0, 0], [0, 0]
		for d in g["deaths"]:
			r, t, ch, pos, gm, cause = d[:6]
			died[ch] += 1
			bags[ch].append(gm)
			lost_t[t] += gm
			if cause != "camp" and isinstance(cause, int) and cause < len(L):
				k = TYPES[L[cause][1]]
				kills[k] += 1
				took[k] += gm
				took_t[1 - t] += gm
		for t in (0, 1):
			key = "win" if res[t] == "win" else "loss"
			swing[key]["took"].append(took_t[t])
			swing[key]["lost"].append(lost_t[t])
			tg = collections.Counter()
			ev = collections.defaultdict(int)
			for c in g["captures"]:
				if c[1] != t:
					continue
				ev[(c[0], c[3])] += 1
				tg[c[2]] += c[5]
			for v in ev.values():
				events += 1
				shared += v > 1
			if sum(tg.values()):
				top1[key].append(max(tg.values()) / sum(tg.values()))
		for c in g["captures"]:
			caps[c[2]] += 1
			gold[c[2]] += c[5]
			gems[c[2]] += c[4]
	TG, TM = sum(gold.values()) or 1, sum(gems.values()) or 1
	rows = []
	for ch in sorted(played, key=lambda c: -played[c]):
		n = played[ch]
		kg = kills[ch] * 100 * (1.33 if ch == "VesperVale" else 1.0)
		rows.append({
			"champ": ch, "games": n, "captures": caps[ch], "gold_share": gold[ch] / TG, "gem_share": gems[ch] / TM,
			"gold_per_capture": gold[ch] / caps[ch] if caps[ch] else 0.0, "gems_per_capture": gems[ch] / caps[ch] if caps[ch] else 0.0,
			"capture_gold_per_game": gold[ch] / n, "kills_per_game": kills[ch] / n, "gems_taken_per_game": took[ch] / n,
			"kill_gold_share": kg / (kg + gold[ch]) if kg + gold[ch] else 0.0, "deaths_per_game": died[ch] / n,
			"death_hazard_per_round": died[ch] / rounds_alive_proxy[ch] if rounds_alive_proxy[ch] else 0.0,
			"bag_at_death_mean": st.mean(bags[ch]) if bags[ch] else 0.0,
			"bag_at_death_20plus": sum(1 for x in bags[ch] if x >= 20) / len(bags[ch]) if bags[ch] else 0.0})
	R["champions"] = rows
	R["captures_shared"] = {"events": events, "shared": shared, "share": shared / events if events else 0.0}
	R["bag_swing"] = {k: {"took": st.mean(v["took"]) if v["took"] else 0.0, "lost": st.mean(v["lost"]) if v["lost"] else 0.0} for k, v in swing.items()}
	R["gold_top1_share"] = {k: st.mean(v) if v else 0.0 for k, v in top1.items()}
	fr = [g.get("final_round", 0) for g in games]
	R["ends"] = dict(ends)
	R["final_round"] = {"median": st.median(fr) if fr else 0, "mean": st.mean(fr) if fr else 0,
						"share_ge_1990": sum(1 for x in fr if x >= 1990) / len(fr) if fr else 0.0,
						"close_races": sum(1 for g in games if g.get("end") == "gems" and min(g["submitted"]) >= 900) / len(games) if games else 0.0}
	return R


def gold_only(caprows):
	rows = [json.loads(line) for line in open(caprows) if line.strip()]
	gold, go, n, gon = (collections.Counter() for _ in range(4))
	for r in rows:
		gold[r["champ"]] += r["gold"]
		n[r["champ"]] += 1
		if r["kind"] == "gold":
			go[r["champ"]] += r["gold"]
			gon[r["champ"]] += 1
	G = sum(gold.values()) or 1
	return {"games": len({r["replay"] for r in rows}), "captures": len(rows), "gold_only_captures": sum(gon.values()),
			"gold_only_gold_share": sum(go.values()) / G,
			"champions": [{"champ": c, "capture_gold_share": gold[c] / G, "gold_only_share_of_own_gold": go[c] / gold[c] if gold[c] else 0.0,
						   "gold_only_captures": gon[c], "captures": n[c]} for c, _ in gold.most_common()]}


def markdown(R, GO):
	L = [f"# Role tables from {R['games']} decoded top-team games (LEARNED; tools/teamplan/ladder_roles.py)", ""]
	L += ["| Champion | Games | Captures | Gold share | Gem share | Gold / capture | Capture gold / game | Kills / game | Gems its kills took / game | Kill-gold share | Deaths / game | Death hazard / round | Bag at death | Deaths with bag 20+ |",
		  "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
	for r in R["champions"]:
		L.append(f"| {r['champ']} | {r['games']} | {r['captures']} | {100 * r['gold_share']:.1f}% | {100 * r['gem_share']:.1f}% | "
				 f"{r['gold_per_capture']:.1f} | {r['capture_gold_per_game']:.0f} | {r['kills_per_game']:.2f} | {r['gems_taken_per_game']:.1f} | "
				 f"{r['kill_gold_share']:.2f} | {r['deaths_per_game']:.2f} | {r['death_hazard_per_round']:.5f} | {r['bag_at_death_mean']:.1f} | "
				 f"{100 * r['bag_at_death_20plus']:.1f}% |")
	cs, bs, fr = R["captures_shared"], R["bag_swing"], R["final_round"]
	L += ["", f"- Captures shared by two or more bodies: {cs['shared']} of {cs['events']} ({100 * cs['share']:.1f}%).",
		  f"- Bag swing per team-game: winners take {bs['win']['took']:.1f} gems from enemy bags and lose {bs['win']['lost']:.1f}; losers take "
		  f"{bs['loss']['took']:.1f} and lose {bs['loss']['lost']:.1f}.",
		  f"- Top body's share of team capture gold: winners {R['gold_top1_share']['win']:.3f}, losers {R['gold_top1_share']['loss']:.3f}.",
		  f"- Ends: {R['ends']}; final round median {fr['median']}, mean {fr['mean']:.0f}; reaching round 1990+: {100 * fr['share_ge_1990']:.1f}%; "
		  f"close races (loser 900+): {100 * fr['close_races']:.1f}%.",
		  "- The death hazard uses the game length as the exposure (dead time included): a lower bound of the hazard while alive."]
	if GO:
		L += ["", f"## Gold-only captures ({GO['games']} raw replays; the summaries above miss them)", "",
			  f"{GO['gold_only_captures']} of {GO['captures']} captures are gold-only, {100 * GO['gold_only_gold_share']:.1f}% of all capture gold.", "",
			  "| Champion | Capture gold share | Gold-only share of its own capture gold | Gold-only captures / all its captures |", "|---|---|---|---|"]
		for c in GO["champions"]:
			L.append(f"| {c['champ']} | {100 * c['capture_gold_share']:.1f}% | {100 * c['gold_only_share_of_own_gold']:.1f}% | {c['gold_only_captures']} / {c['captures']} |")
	return "\n".join(L) + "\n"


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--summaries", default=os.path.join(ROOT, "experiments", "results", "mapintel", "ladder_20261024"))
	ap.add_argument("--caprows", default="")
	ap.add_argument("--out", default="")
	a = ap.parse_args()
	R = analyse(load_games(a.summaries))
	GO = gold_only(a.caprows) if a.caprows else None
	md = markdown(R, GO)
	if a.out:
		os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
		open(a.out, "w").write(md)
		json.dump({"ladder": R, "gold_only": GO}, open(os.path.splitext(a.out)[0] + ".json", "w"), indent=1)
		print(f"wrote {a.out}")
	else:
		print(md)


if __name__ == "__main__":
	main()
