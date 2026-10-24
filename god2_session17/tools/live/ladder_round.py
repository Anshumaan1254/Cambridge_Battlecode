#!/usr/bin/env python3
"""One in-bot ladder A/B round, end to end (run after `cambc submit`):
  python tools/live/ladder_round.py LABEL N_VARIANTS SINCE_ISO [--set experiments/live/setD_top10.json] [--no-queue]
queues the set (unless --no-queue; waits out the 50-groups-per-hour quota), waits until every group of LABEL has finished, fetches
our ranked games, and prints the per-variant / per-bit results of the variant hash (P.ab_nomask) for unranked and ranked games."""
import json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import groups

label, n, since = sys.argv[1], sys.argv[2], sys.argv[3]
setf = sys.argv[sys.argv.index("--set") + 1] if "--set" in sys.argv else "experiments/live/setD_top10.json"
env = dict(os.environ, PYTHONIOENCODING="utf-8")
py = sys.executable
if "--no-queue" not in sys.argv:
    subprocess.run([py, "tools/live/queue_groups.py", label, "--set", setf], env=env, capture_output=True)
t0 = time.time()
while True:
    out = subprocess.run([py, "tools/live/groups.py", "pull", label], env=env, capture_output=True, text=True, encoding="utf-8").stdout
    rows = [l for l in out.splitlines() if "W-L" in l]
    pend = sum(int(l.split("pending")[1].split()[0]) for l in rows)
    if rows and pend == 0:
        break
    if time.time() - t0 > 4 * 3600:
        print("timeout waiting for groups")
        break
    time.sleep(120)
w = sum(int(l.split("W-L")[1].split()[0].split("-")[0]) for l in rows)
l_ = sum(int(l.split("W-L")[1].split()[0].split("-")[1]) for l in rows)
print(f"{label}: {len(rows)} groups, W-L {w}-{l_} ({100 * w / max(1, w + l_):.1f}%)")
subprocess.run([py, "tools/live/fetch_matches.py", "--team", "me", "--kind", "ranked", "--max", "120", "--out", "experiments/live/lists/us_ranked.jsonl"], env=env, capture_output=True)
r = subprocess.run([py, "tools/live/variant_of.py", n, "--since", since, "--bits", "--nomask"], env=env, capture_output=True, text=True, encoding="utf-8")
print(r.stdout)
