#!/usr/bin/env python3
"""Unopposed pace benchmark: BOT vs idle on every pool map (BOT as team A), rounds to 1000 banked gems (2000 + penalty when
it never gets there). Pure farming efficiency, no proxy opponent involved.
  python tools/live/pace.py BOT [--pool 'maps/0*.map26a'] [--jobs 7] [--tag NAME]
  python tools/live/pace.py --compare TAG1 TAG2"""
import argparse, glob, json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load(tag):
    out = {}
    for f in glob.glob(f"C:/battlecode/cache/pace/{tag}/*.json"):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        gems = {t["team"]: int(t["submittedGems"]) for t in d["teams"]}
        r = d["match"]["roundsCompleted"]
        g = gems.get("teamA", 0)
        out[os.path.basename(f)[:-5]] = r if g >= 1000 else 2000 + (1000 - g)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bot", nargs="?")
    ap.add_argument("--pool", default="maps/0*.map26a")
    ap.add_argument("--jobs", type=int, default=7)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--compare", nargs=2)
    a = ap.parse_args()
    if a.compare:
        x, y = load(a.compare[0]), load(a.compare[1])
        ks = sorted(set(x) & set(y))
        print(f"{len(ks)} maps: {a.compare[0]} {sum(x[k] for k in ks) / len(ks):.1f}  {a.compare[1]} {sum(y[k] for k in ks) / len(ks):.1f}")
        for k in ks:
            flag = " <<<" if y[k] - x[k] > 60 else (" >>>" if x[k] - y[k] > 60 else "")
            print(f"  {k:28s} {x[k]:5d} {y[k]:5d} {y[k] - x[k]:+5d}{flag}")
        return
    tag = a.tag or a.bot
    out = f"C:/battlecode/cache/pace/{tag}"
    os.makedirs(out, exist_ok=True)
    rows = []
    for m in sorted(sum((glob.glob(os.path.join(ROOT, p)) for p in a.pool.split(",")), [])):
        name = os.path.basename(m)[:-len(".map26a")]
        if os.path.exists(f"{out}/{name}.json"):
            continue
        rows.append(f'bots/{a.bot} bots/idle "{os.path.relpath(m, ROOT)}" "{out}/{name}.repl26a" --statistics "{out}/{name}.json" --json')
    if rows:
        man = os.path.join(ROOT, f".bench_pace_{tag}.txt")
        open(man, "w").write("\n".join(rows) + "\n")
        t0 = time.time()
        r = subprocess.run(["cambc", "run-batch", man, "--jobs", str(a.jobs), "--release", "--color", "never"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        os.remove(man)
        if r.returncode != 0:
            print(r.stdout[-2000:], r.stderr[-2000:])
        print(f"ran {len(rows)} in {time.time() - t0:.0f}s")
    res = load(tag)
    print(f"{tag}: {len(res)} maps, mean pace {sum(res.values()) / max(1, len(res)):.1f}, never-finished {sum(1 for v in res.values() if v > 2000)}")


if __name__ == "__main__":
    main()
