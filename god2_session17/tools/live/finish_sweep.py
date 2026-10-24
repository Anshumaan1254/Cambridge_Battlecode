#!/usr/bin/env python3
"""Wait for a sweep label's groups to finish, then fetch its summaries and replays.

    python tools/live/finish_sweep.py LABEL [--since ISO] [--replays DIR] [--timeout 7200]

Polls `groups.py pull LABEL` every 120 s until no game is pending (or the timeout), then `summ.py fetch` on the group games since --since,
and downloads the label's replays into DIR (default C:/battlecode/cache/t2/<label lower-case>) with an index.jsonl of match rows."""
import json, os, subprocess, sys, time
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
label = sys.argv[1]
since = sys.argv[sys.argv.index("--since") + 1] if "--since" in sys.argv else ""
out = sys.argv[sys.argv.index("--replays") + 1] if "--replays" in sys.argv else f"C:/battlecode/cache/t2/{label.lower()}"
tmo = int(sys.argv[sys.argv.index("--timeout") + 1]) if "--timeout" in sys.argv else 7200
env = dict(os.environ, PYTHONIOENCODING="utf-8")
t0 = time.time()
while True:
    r = subprocess.run([sys.executable, "tools/live/groups.py", "pull", label], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env)
    lines = [l for l in r.stdout.splitlines() if f" {label} " in l]
    pending = sum(int(l.split("pending")[1].split()[0]) for l in lines if "pending" in l)
    total = [l for l in r.stdout.splitlines() if l.startswith("TOTAL")]
    print(time.strftime("%H:%M:%S"), f"groups {len(lines)} pending {pending}", total[-1] if total else "", flush=True)
    if lines and pending == 0:
        break
    if time.time() - t0 > tmo:
        print("TIMEOUT", flush=True)
        break
    time.sleep(120)
args = [sys.executable, "tools/live/summ.py", "fetch", "experiments/live/lists/groups_matches.jsonl", "--jobs", "2"]
if since:
    args += ["--since", since]
r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env)
print("summaries:", (r.stdout.strip().splitlines() or ["?"])[-1], flush=True)
r = subprocess.run([sys.executable, "tools/live/fetch_replays.py", out, "--labels", label], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env)
print("replays:", (r.stdout.strip().splitlines() or ["?"])[-1], flush=True)
groups = [json.loads(l) for l in open(os.path.join(ROOT, "experiments/live/groups.jsonl"), encoding="utf-8")]
lab = {g["resp"].get("groupId"): g["label"] for g in groups}
have = {f.rsplit("_", 1)[1][:8] for f in os.listdir(out) if f.endswith(".repl26a")} if os.path.isdir(out) else set()
seen = set()
with open(os.path.join(out, "index.jsonl"), "w", encoding="utf-8") as fo:
    for l in open(os.path.join(ROOT, "experiments/live/lists/groups_matches.jsonl"), encoding="utf-8"):
        m = json.loads(l)
        if lab.get(m.get("groupId")) == label and m["matchId"][:8] in have and m["matchId"] not in seen:
            seen.add(m["matchId"])
            fo.write(json.dumps(m, ensure_ascii=False) + "\n")
print("index rows:", len(seen), flush=True)
