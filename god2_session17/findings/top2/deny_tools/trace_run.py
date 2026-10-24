#!/usr/bin/env python3
"""God2 deny module: traced debug games (G2D_TRACE build) on a map list, both sides, bundles kept.

  python experiments/top2/deny_tools/trace_run.py BOT OPP TAG [--maps 'maps/0*.map26a'] [--jobs 3]

Writes C:/battlecode/cache/deny/<TAG>/<map>_<side>/*.repl26a and <TAG>/g2d.txt (BOT's 'G2D ' stdout lines, prefixed by map and side)."""
import argparse, glob, os, subprocess, zipfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def one(job):
    bot, opp, m, side, out = job
    d = os.path.join(out, f"{os.path.basename(m)[:-7]}_{side}")
    os.makedirs(d, exist_ok=True)
    if not glob.glob(os.path.join(d, "*.repl26a")):
        a, b = (bot, opp) if side == "A" else (opp, bot)
        subprocess.run(["cambc", "run", a, b, "--map", m, "-o", d], cwd=ROOT, capture_output=True, text=True)
    reps = sorted(glob.glob(os.path.join(d, "*.repl26a")))
    if not reps:
        return m, side, None
    t = zipfile.ZipFile(reps[-1]).read(f"team-{side.lower()}.stdout").decode(errors="replace").replace("\x00", "")
    return m, side, [l.strip() for l in t.split("\n") if l.startswith("G2D ")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bot")
    ap.add_argument("opp")
    ap.add_argument("tag")
    ap.add_argument("--maps", default="maps/0*.map26a")
    ap.add_argument("--jobs", type=int, default=3)
    a = ap.parse_args()
    out = f"C:/battlecode/cache/deny/{a.tag}"
    os.makedirs(out, exist_ok=True)
    maps = sorted(sum((glob.glob(os.path.join(ROOT, g)) for g in a.maps.split(",")), []))
    jobs = [(a.bot, a.opp, m, s, out) for m in maps for s in ("A", "B")]
    with ThreadPoolExecutor(a.jobs) as ex, open(os.path.join(out, "g2d.txt"), "w") as f:
        for m, side, lines in ex.map(one, jobs):
            name = os.path.basename(m)[:-7]
            if lines is None:
                print("FAILED", name, side)
                continue
            for l in lines:
                f.write(f"{name} {side} {l}\n")
            print(name, side, len(lines))


if __name__ == "__main__":
    main()
