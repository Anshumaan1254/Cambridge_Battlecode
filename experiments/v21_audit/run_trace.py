#!/usr/bin/env python3
"""run_trace.py BOT OPP OUTDIR [--jobs N]: BOT (a trace build) as team A vs OPP on every maps/s3 map in debug mode; keeps team-a stdout."""
import glob, os, subprocess, sys, zipfile
ROOT = "/home/user/Cambridge_Battlecode"
bot, opp, out = sys.argv[1], sys.argv[2], sys.argv[3]
jobs = sys.argv[sys.argv.index("--jobs") + 1] if "--jobs" in sys.argv else "4"
os.makedirs(out, exist_ok=True)
man = os.path.join(out, "manifest.txt")
maps = sorted(glob.glob(ROOT + "/maps/s3/*.map26a"))
with open(man, "w") as f:
    for m in maps:
        mn = os.path.splitext(os.path.basename(m))[0]
        f.write(f"{ROOT}/bots/{bot} {ROOT}/bots/{opp} {m} {out}/{mn}.repl26a --statistics {out}/{mn}.json --json\n")
subprocess.run(["cambc", "run-batch", man, "--jobs", jobs, "--color", "never"], capture_output=True, text=True)
n = 0
for m in maps:
    mn = os.path.splitext(os.path.basename(m))[0]
    rp = f"{out}/{mn}.repl26a"
    try:
        txt = zipfile.ZipFile(rp).read("team-a.stdout").decode(errors="replace").replace("\x00", "")
        open(f"{out}/{mn}.stdout", "w").write(txt); n += 1
    except Exception as e:
        print("no stdout", mn, e)
print("games with stdout", n, "of", len(maps))
