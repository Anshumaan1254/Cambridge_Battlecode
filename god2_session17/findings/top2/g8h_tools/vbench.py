"""Variant bench for bots/g8h switch ablations (session 17, g8h port; see experiments/top2/g8h_port.md).

Copies bots/g8h/src to C:/battlecode/cache/g8h_vars/NAME/src (outside the repo) with params.h overrides, plays it vs an opponent bot
on every pool map, both sides (release, deterministic), into C:/battlecode/cache/bench/<tag>/ and prints the localbench summary.

  python experiments/top2/g8h_tools/vbench.py NAME [KEY=VALUE ...] [--opp g8] [--tag TAG] [--jobs 6]
  e.g. python experiments/top2/g8h_tools/vbench.py no_rc real_channel=0        (tag g8hv_no_rc_vs_g8)
"""
import argparse, glob, os, re, shutil, subprocess, sys, time

ROOT = "C:/battlecode/Cambridge_Battlecode"
VARS = "C:/battlecode/cache/g8h_vars"  # variant copies live outside the repo
sys.path.insert(0, ROOT + "/tools/live")
from localbench import summarize  # noqa: E402


def make_variant(name, overrides, src):
    dst = f"{VARS}/{name}"
    if os.path.exists(dst + "/src"):
        shutil.rmtree(dst + "/src")
    os.makedirs(dst, exist_ok=True)
    shutil.copytree(src, dst + "/src")
    p = dst + "/src/params.h"
    s = open(p, encoding="utf-8").read()
    for kv in overrides:
        k, v = kv.split("=", 1)
        s, n = re.subn(r"^(\s*[a-z]+(?: [a-z]+)? " + re.escape(k) + r" = )[^;]*;", lambda m: m.group(1) + v + ";", s, flags=re.M)
        if n != 1:
            sys.exit(f"param {k}: {n} matches")
    open(p, "w", encoding="utf-8").write(s)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("kv", nargs="*")
    ap.add_argument("--opp", default="g8")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--src", default=ROOT + "/bots/g8h/src")
    ap.add_argument("--pool", default="maps/0*.map26a")
    a = ap.parse_args()
    tag = a.tag or f"g8hv_{a.name}_vs_{a.opp}"
    out = f"C:/battlecode/cache/bench/{tag}"
    os.makedirs(out, exist_ok=True)
    bot = make_variant(a.name, a.kv, a.src)
    opp = a.opp if (":" in a.opp or a.opp.startswith("/")) else f"{ROOT}/bots/{a.opp}"
    rows = []
    for m in sorted(glob.glob(os.path.join(ROOT, a.pool))):
        m = m.replace("\\", "/")
        name = os.path.basename(m)[:-len(".map26a")]
        for side in ("A", "B"):
            x, y = (bot, opp) if side == "A" else (opp, bot)
            stem = f"{out}/{name}_{side}"
            if os.path.exists(stem + ".json"):
                continue
            rows.append(f'"{x}" "{y}" "{m}" "{stem}.repl26a" --statistics "{stem}.json" --json')
    if rows:
        man = f"{VARS}/{a.name}_manifest.txt"
        open(man, "w").write("\n".join(rows) + "\n")
        t0 = time.time()
        r = subprocess.run(["cambc", "run-batch", man, "--jobs", str(a.jobs), "--release", "--color", "never"], cwd=ROOT, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(r.stdout[-3000:], r.stderr[-3000:])
        print(f"ran {len(rows)} games in {time.time() - t0:.0f}s")
    summarize(out, a.name, a.opp)


if __name__ == "__main__":
    main()
