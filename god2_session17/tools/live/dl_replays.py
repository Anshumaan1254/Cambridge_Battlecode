#!/usr/bin/env python3
"""Download replays of any platform matches listed in match-list JSONL files (tools/live/fetch_matches.py output).

    python tools/live/dl_replays.py OUT_DIR LIST.jsonl [LIST2.jsonl ...] [--team NAME_OR_ID] [--since ISO] [--per-map K]
                                    [--max N] [--jobs 3]

--team keeps matches with that team; --per-map K keeps the K newest matches per map (spreads a sample over the pool);
files are OUT_DIR/<map>_<matchId8>.repl26a (existing files are skipped). Writes OUT_DIR/index.jsonl (one list row per file)."""
import argparse, concurrent.futures as cf, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cli


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("lists", nargs="+")
    ap.add_argument("--team", default="")
    ap.add_argument("--since", default="")
    ap.add_argument("--per-map", type=int, default=0)
    ap.add_argument("--max", type=int, default=10 ** 9)
    ap.add_argument("--jobs", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    seen, ms = set(), []
    for f in a.lists:
        for l in open(f, encoding="utf-8"):
            m = json.loads(l)
            if m["matchId"] in seen or m.get("status") != "finished" or m["createdAt"] < a.since:
                continue
            if a.team and not any(a.team in (t.get("name"), t.get("teamId")) for t in m["teams"]):
                continue
            seen.add(m["matchId"])
            ms.append(m)
    ms.sort(key=lambda m: m["createdAt"], reverse=True)
    if a.per_map:
        cnt, keep = {}, []
        for m in ms:
            if cnt.get(m["map"], 0) < a.per_map:
                cnt[m["map"]] = cnt.get(m["map"], 0) + 1
                keep.append(m)
        ms = keep
    ms = ms[: a.max]

    def one(m):
        path = os.path.join(a.out, f"{m['map']}_{m['matchId'][:8]}.repl26a")
        if os.path.exists(path):
            return 0
        rc, o, e = cli.run(["matches", "download", m["matchId"], "-o", path])
        return int(rc == 0 and os.path.exists(path))

    with cf.ThreadPoolExecutor(a.jobs) as ex:
        n = sum(ex.map(one, ms))
    idx = os.path.join(a.out, "index.jsonl")
    have = set()
    if os.path.exists(idx):
        have = {json.loads(l)["matchId"] for l in open(idx, encoding="utf-8")}
    with open(idx, "a", encoding="utf-8") as f:
        for m in ms:
            if m["matchId"] not in have and os.path.exists(os.path.join(a.out, f"{m['map']}_{m['matchId'][:8]}.repl26a")):
                f.write(json.dumps(m, ensure_ascii=False) + "\n")
    print(f"downloaded {n} new of {len(ms)} selected into {a.out}")


if __name__ == "__main__":
    main()
