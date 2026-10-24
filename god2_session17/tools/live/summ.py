#!/usr/bin/env python3
"""Download platform match summaries and reduce them to compact JSON records.

Binary summaries are cached outside the repo (default C:/battlecode/cache/summ, env LIVE_CACHE);
compact records go to experiments/live/compact/<matchId>.json (a few KB each).

Usage:
  python tools/live/summ.py fetch LIST.jsonl [--filter-team NAME_OR_ID ...] [--both-in TEAMFILE] [--max N] [--jobs 4]
  python tools/live/summ.py compact <matchId>        # (re)build one compact record from the cache
Match lists come from tools/live/fetch_matches.py.
"""
import argparse, json, os, subprocess, sys, tempfile, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cli

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.environ.get("LIVE_CACHE", "C:/battlecode/cache/summ")
COMPACT = os.path.join(ROOT, "experiments", "live", "compact")


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr


def run_points(runs, every=None):
    """RLE runs [{duration, value}] -> [(round, value)] at change points."""
    pts, t = [], 0
    for r in runs:
        v = float(r["value"])
        if not pts or pts[-1][1] != v:
            pts.append((t, v))
        t += int(r["duration"])
    return pts


def compact(meta, d):
    m = d["match"]
    side_of = {"teamA": "a", "teamB": "b"}
    teams = []
    by_side = {t["side"]: t for t in meta["teams"]} if meta else {}
    gems = {t["team"]: int(t["submittedGems"]) for t in d.get("teams", [])}
    for tk in ("teamA", "teamB"):
        mt = by_side.get(side_of[tk], {})
        teams.append({
            "team": tk, "name": mt.get("name"), "teamId": mt.get("teamId"), "result": mt.get("result"),
            "draft": [x["champion"] for x in d["roster"]["draft"] if x["team"] == tk],
            "gems": gems.get(tk),
        })
    champs = []
    for c in d["champions"]:
        champs.append({
            "id": c["id"], "team": c["team"], "name": c["name"],
            "m": {k: (float(v) if isinstance(v, (int, float)) or "." in str(v) else int(v)) for k, v in c["metrics"].items()},
            "items": [[i["item"], int(i["quantity"])] for i in c["items"]],
        })
    cname = {c["id"]: (c["team"], c["name"]) for c in d["champions"]}
    ev = {}
    for e in d["events"]:
        o = e["owner"]
        for x in e["entries"]:
            ev.setdefault(e["kind"], []).append((o, x))

    def tgt(x):
        t = x.get("target")
        if isinstance(t, dict):
            return [t.get("kind"), t.get("team"), t.get("name"), t.get("id")]
        return t

    out = {
        "id": meta.get("matchId") if meta else None, "map": meta.get("map") if meta else None,
        "created": meta.get("createdAt") if meta else None, "kind": meta.get("kind") if meta else None,
        "endReason": meta.get("endReason") if meta else None,
        "rounds": m["roundsCompleted"], "outcome": m["outcome"], "w": m["width"], "h": m["height"],
        "engine": m.get("engineVersion"), "teams": teams, "champs": champs,
    }
    simple = {
        "death": "deaths", "kill": "kills", "campClear": "clears", "gemSubmission": "subs",
        "gemCollection": "colls", "gemLoss": "losses", "buyItem": "buys", "buyConsumable": "cons",
        "sellItem": "sells", "itemCombination": "combos", "botFault": "faults", "fuelExhausted": "fuel",
        "resignation": "resign",
    }
    for k, name in simple.items():
        rows = []
        for o, x in ev.get(k, []):
            rows.append([x["timestamp"]["round"], o.get("team"), o.get("name"), o.get("id"), x.get("context"),
                         tgt(x), x.get("value"), x.get("amount"), x.get("x"), x.get("y")])
        rows.sort(key=lambda r: r[0])
        out[name] = rows
    wards = {}
    for o, x in ev.get("wardPlacement", []):
        wards.setdefault(o.get("team"), []).append([x["timestamp"]["round"], x.get("x"), x.get("y")])
    out["wards"] = {k: len(v) for k, v in wards.items()}
    out["ward_first"] = {k: sorted(v)[:20] for k, v in wards.items()}
    out["team_tl"] = {t["owner"] + ":" + t["metric"]: run_points(t["runs"]) for t in d.get("teamTimelines", [])}
    ctl = {}
    for t in d.get("championTimelines", []):
        if t["metric"] in ("gems", "collectedGems", "submittedGems", "earnedGold", "deaths", "gold"):
            ctl[str(t["owner"]["id"]) + ":" + t["metric"]] = run_points(t["runs"])
    out["champ_tl"] = ctl
    out["diag"] = d.get("diagnostics")
    return out


def fetch_one(meta):
    mid = meta["matchId"]
    cpath = os.path.join(COMPACT, mid + ".json")
    if os.path.exists(cpath):
        return mid, "cached"
    bpath = os.path.join(CACHE, mid + ".bin")
    if not os.path.exists(bpath):
        rc, o, e = cli.run(["matches", "summary", mid, "-o", bpath])
        if rc != 0 or not os.path.exists(bpath):
            return mid, "download failed: " + (e or o).strip()[:200]
    fd, jpath = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        rc, o, e = sh(["cambc", "summary", bpath, "-o", jpath])
        if rc != 0:
            return mid, "convert failed: " + (e or o).strip()[:200]
        with open(jpath, encoding="utf-8") as f:
            d = json.load(f)
        rec = compact(meta, d)
        with open(cpath, "w", encoding="utf-8") as f:
            json.dump(rec, f, separators=(",", ":"))
        return mid, "ok"
    except Exception as ex:  # noqa: BLE001
        return mid, "error: %r" % (ex,)
    finally:
        try:
            os.remove(jpath)
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    f = sub.add_parser("fetch")
    f.add_argument("lists", nargs="+")
    f.add_argument("--kind", default=None)
    f.add_argument("--teams", default=None, help="file with one team name per line: keep matches where BOTH teams are listed")
    f.add_argument("--any", default=None, help="file with team names: keep matches where ANY team is listed")
    f.add_argument("--since", default=None)
    f.add_argument("--max", type=int, default=100000)
    f.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(COMPACT, exist_ok=True)
    if a.cmd != "fetch":
        ap.print_help()
        return
    both = set(l.strip() for l in open(a.teams, encoding="utf-8") if l.strip()) if a.teams else None
    anyt = set(l.strip() for l in open(a.any, encoding="utf-8") if l.strip()) if a.any else None
    metas, seen = [], set()
    for lst in a.lists:
        for line in open(lst, encoding="utf-8"):
            if not line.strip():
                continue
            m = json.loads(line)
            if m["matchId"] in seen or m.get("status") != "finished":
                continue
            if a.kind and m.get("kind") != a.kind:
                continue
            if a.since and m.get("createdAt", "") < a.since:
                continue
            names = [t["name"] for t in m["teams"]]
            if both is not None and not all(n in both for n in names):
                continue
            if anyt is not None and not any(n in anyt for n in names):
                continue
            seen.add(m["matchId"])
            metas.append(m)
    metas = metas[: a.max]
    print(f"{len(metas)} matches to fetch", flush=True)
    stats = {}
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for i, (mid, st) in enumerate(ex.map(fetch_one, metas)):
            k = st.split(":")[0]
            stats[k] = stats.get(k, 0) + 1
            if not st.startswith(("ok", "cached")):
                print(mid, st, flush=True)
            if (i + 1) % 50 == 0:
                print(f"{i + 1}/{len(metas)} {stats}", flush=True)
    print("done", stats, flush=True)


if __name__ == "__main__":
    main()
