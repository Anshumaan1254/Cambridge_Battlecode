"""Run a traced bot (debug build) vs an opponent on every pool map (one side), keep team logs.
  python trace_all.py BOTDIR OPP OUTDIR [jobs] [side A|B]"""
import concurrent.futures as cf, glob, os, subprocess, sys, zipfile

bot, opp, out = sys.argv[1], sys.argv[2], sys.argv[3]
jobs = int(sys.argv[4]) if len(sys.argv) > 4 else 3
side = sys.argv[5] if len(sys.argv) > 5 else "A"
ROOT = "C:/battlecode/Cambridge_Battlecode"
os.makedirs(out, exist_ok=True)
maps = sorted(glob.glob(ROOT + "/maps/0*.map26a"))
if len(sys.argv) > 6:
    keep = set(sys.argv[6].split(","))
    maps = [m for m in maps if os.path.basename(m)[:-len(".map26a")] in keep]


def run(m):
    name = os.path.basename(m)[:-len(".map26a")]
    d = f"{out}/{name}_{side}"
    if os.path.exists(d + "/done"):
        return name, "cached"
    os.makedirs(d, exist_ok=True)
    a, b = (bot, opp) if side == "A" else (opp, bot)
    r = subprocess.run(["cambc", "run", a, b, "--map", m, "-o", d, "--log-limit", "80000000", "--statistics", d + "/stats.json", "--json"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    zs = [f for f in os.listdir(d) if f.endswith(".repl26a")]
    if not zs:
        return name, "no replay: " + r.stdout[-500:] + r.stderr[-500:]
    z = zipfile.ZipFile(f"{d}/{zs[0]}")
    for n in z.namelist():
        if n.endswith(".stdout") or n.endswith(".fuel"):
            open(f"{d}/{n}", "wb").write(z.read(n))
    open(d + "/done", "w").write("ok")
    return name, "ok"


with cf.ThreadPoolExecutor(jobs) as ex:
    for name, st in ex.map(run, maps):
        print(name, st, flush=True)
