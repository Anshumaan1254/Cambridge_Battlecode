#!/usr/bin/env python3
"""Recent ranked win rates of the ladder's top N teams (to find the teams worth studying).

    python tools/live/top_winrates.py [--top 50] [--max 150] [--since ISO] [--ladder FILE]

Fetches each team's latest ranked games into experiments/live/lists/wr/<teamId8>.jsonl (merged by matchId on re-runs),
then prints rank, rating, games, win rate overall / since --since, and the draft fingerprints of the last 24 games.
Writes experiments/live/top_winrates.json."""
import argparse, collections, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cli
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=50)
    ap.add_argument("--max", type=int, default=150)
    ap.add_argument("--since", default="")
    ap.add_argument("--ladder", default="")
    ap.add_argument("--no-fetch", action="store_true")
    a = ap.parse_args()
    if a.ladder:
        lad = json.load(open(a.ladder, encoding="utf-8"))
    else:
        rc, so, se = cli.run(["ladder", "--json", "--limit", "100"])
        lad = json.loads(so)
    teams = [t for t in lad["teams"] if t["rank"] <= a.top]
    os.makedirs(os.path.join(ROOT, "experiments/live/lists/wr"), exist_ok=True)
    out = []
    for t in teams:
        f = os.path.join(ROOT, "experiments/live/lists/wr", t["teamId"][:8] + ".jsonl")
        if not a.no_fetch:
            subprocess.run([sys.executable, os.path.join(ROOT, "tools/live/fetch_matches.py"), "--team", t["teamId"], "--kind", "ranked",
                            "--max", str(a.max), "--out", f], cwd=ROOT, capture_output=True, text=True)
        rows = []
        if os.path.exists(f):
            rows = [json.loads(l) for l in open(f, encoding="utf-8")]
        rows = [r for r in rows if r.get("status") == "finished"]
        rows.sort(key=lambda r: r["createdAt"], reverse=True)
        rows = rows[: a.max]
        res = []
        drafts = collections.Counter()
        for r in rows:
            me = next((x for x in r["teams"] if x["teamId"] == t["teamId"]), None)
            if not me:
                continue
            res.append((r["createdAt"], me["result"] == "win"))
            if len(drafts) < 24:
                drafts[tuple(sorted(me["draftPicks"]))] += 1
        w = sum(1 for _, x in res if x)
        ws = [x for c, x in res if c >= a.since] if a.since else []
        rec = {"rank": t["rank"], "teamId": t["teamId"], "name": t["name"], "rating": round(t["rating"], 1), "matches": t["matches"],
               "games": len(res), "wins": w, "wr": round(w / len(res), 3) if res else None,
               "since_games": len(ws), "since_wr": round(sum(ws) / len(ws), 3) if ws else None,
               "first": res[-1][0][:16] if res else "", "last": res[0][0][:16] if res else ""}
        out.append(rec)
        print(f"{rec['rank']:3d} {rec['name'][:28]:28s} {rec['rating']:7.1f} n{rec['games']:4d} wr {rec['wr'] if rec['wr'] is not None else '-'}"
              f"  since n{rec['since_games']} wr {rec['since_wr']}  {rec['first']}..{rec['last']}", flush=True)
    json.dump(out, open(os.path.join(ROOT, "experiments/live/top_winrates.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    hi = [r for r in out if r["wr"] is not None and r["wr"] > 0.65]
    print("\nteams with win rate > 65%:", ", ".join(f"{r['name']} ({r['wr']:.0%}, rank {r['rank']})" for r in hi))


if __name__ == "__main__":
    main()
