#!/usr/bin/env python3
"""Local A-vs-B bench on Windows: every map of a pool, both sides, via `cambc run-batch` (parallel, release mode).

  python tools/live/localbench.py A B [--pool 'maps/0*.map26a'] [--jobs 6] [--tag NAME] [--rounds N]

Writes C:/battlecode/cache/bench/<tag>/ (replays + statistics JSON) and prints win rate, gems, deaths, per-map results.
A sanity filter only: the real judge is the platform (tools/live/groups.py)."""
import argparse, glob, json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--pool", default="maps/0*.map26a")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--rounds", type=int, default=0)
    a = ap.parse_args()
    tag = a.tag or f"{a.a}_vs_{a.b}_{time.strftime('%H%M%S')}"
    out = f"C:/battlecode/cache/bench/{tag}"
    os.makedirs(out, exist_ok=True)
    maps = []
    for pat in a.pool.split(","):
        maps += sorted(glob.glob(os.path.join(ROOT, pat)))
    rows = []
    for m in maps:
        name = os.path.basename(m)[:-len(".map26a")]
        for side in ("A", "B"):
            x, y = (a.a, a.b) if side == "A" else (a.b, a.a)
            stem = f"{out}/{name}_{side}"
            if os.path.exists(stem + ".json"):
                continue
            rows.append(f'bots/{x} bots/{y} "{os.path.relpath(m, ROOT)}" "{stem}.repl26a" --statistics "{stem}.json" --json')
    man = f"{out}/manifest.txt"
    with open(os.path.join(ROOT, "bench_manifest.txt") if False else man, "w") as f:
        f.write("\n".join(rows) + "\n")
    if rows:
        # run-batch resolves manifest paths relative to the manifest file: write it in ROOT
        rel = os.path.join(ROOT, f".bench_{tag}.txt")
        with open(rel, "w") as f:
            f.write("\n".join(r.replace(f'"{out}', f'"{out}') for r in rows) + "\n")
        cmd = ["cambc", "run-batch", rel, "--jobs", str(a.jobs), "--release", "--color", "never"]
        if a.rounds:
            cmd += ["--rounds", str(a.rounds)]
        t0 = time.time()
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        os.remove(rel)
        if r.returncode != 0:
            print(r.stdout[-3000:], r.stderr[-3000:])
        print(f"ran {len(rows)} games in {time.time() - t0:.0f}s")
    summarize(out, a.a, a.b)


def summarize(out, A, B):
    wins = games = 0
    gA = gB = dA = dB = 0
    per = {}
    rounds = []
    faults = [0, 0]
    fuelx = [0, 0]
    for f in sorted(glob.glob(f"{out}/*.json")):
        name = os.path.basename(f)[:-5]
        mp, side = name.rsplit("_", 1)
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        ta = "teamA" if side == "A" else "teamB"  # team of bot A
        tb = "teamB" if side == "A" else "teamA"
        gems = {t["team"]: int(t["submittedGems"]) for t in d["teams"]}
        deaths = {"teamA": 0, "teamB": 0}
        for c in d["champions"]:
            deaths[c["team"]] += int(c["metrics"]["deaths"])
        win = d["match"]["outcome"] == ta
        games += 1
        wins += win
        gA += gems.get(ta, 0)
        gB += gems.get(tb, 0)
        dA += deaths[ta]
        dB += deaths[tb]
        rounds.append(d["match"]["roundsCompleted"])
        for e in d.get("events", []):
            if e.get("kind") == "fuelExhausted":
                fuelx[0 if e["owner"].get("team") == ta else 1] += len(e.get("entries", []))
        fl = (d.get("diagnostics") or {}).get("botFaults") or {}
        faults[0] += int(fl.get(ta, 0) or 0)
        faults[1] += int(fl.get(tb, 0) or 0)
        per.setdefault(mp, []).append("W" if win else "L")
    if not games:
        print("no results")
        return
    print(f"{A} vs {B}: {wins}/{games} = {100 * wins / games:.1f}% | gems {gA / games:.0f}-{gB / games:.0f} | deaths {dA / games:.1f}-{dB / games:.1f} | rounds {sum(rounds) / len(rounds):.0f} | faults {faults[0]}-{faults[1]} | fuel-out {fuelx[0] / games:.1f}-{fuelx[1] / games:.1f}")
    line = []
    for mp, r in sorted(per.items()):
        line.append(f"{mp.replace('.map26a', '')}:{''.join(r)}")
    print(" ".join(line))


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--summary":
        summarize(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        main()
