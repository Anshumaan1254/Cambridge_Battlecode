#!/usr/bin/env python3
"""Death context for one team in a set of games: half (own/center/enemy by distance to spawns), phase, killers involved,
camp deaths, gems lost. python tools/live/deaths.py TEAM [--list groups|all] [--since ISO]"""
import collections, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import load, side
name = sys.argv[1]
which = sys.argv[sys.argv.index("--list") + 1] if "--list" in sys.argv else "groups"
since = sys.argv[sys.argv.index("--since") + 1] if "--since" in sys.argv else ""
rs = load(since)
if which == "groups":
    ids = {json.loads(l)["matchId"] for l in open("experiments/live/lists/groups_matches.jsonl", encoding="utf-8")}
    rs = [r for r in rs if r["id"] in ids]
spawn = {}  # map -> (teamA spawn centre, teamB spawn centre) estimated from early positions of death? use first deaths? use symmetric: teamA spawn = map not known
# Estimate spawn centres from the map files' spawn area (mapinfo prints them); cache via node only once per map.
import subprocess
cache_f = "experiments/live/spawns.json"
cache = json.load(open(cache_f)) if os.path.exists(cache_f) else {}
def spawns(m, w, h):
    if m in cache: return cache[m]
    f = "maps/" + m.replace("_", "-") + ".map26a"
    if not os.path.exists(f):
        return None
    env = dict(os.environ, CAMBC_CACHE="C:/Users/Anjali Gupta/AppData/Local/cambc/assets")
    out = subprocess.run(["node", "tools/replay/mapinfo.mjs", f], capture_output=True, text=True, env=env).stdout.splitlines()
    sa = sb = None
    xs = [];  ys = []; xb = []; yb = []
    for y, line in enumerate(out[1:]):
        row = line[3:]
        for x, ch in enumerate(row):
            if ch == "S": xs.append(x); ys.append(y)
            if ch == "s": xb.append(x); yb.append(y)
    if xs and xb:
        cache[m] = [[sum(xs) / len(xs), sum(ys) / len(ys)], [sum(xb) / len(xb), sum(yb) / len(yb)]]
        json.dump(cache, open(cache_f, "w"))
        return cache[m]
    return None
tot = collections.Counter(); ctx = collections.Counter(); phase = collections.Counter(); inv = collections.Counter(); lost = 0; ndeath = 0
games = 0
opp_ctx = collections.Counter()
for r in rs:
    tk = side(r, name)
    if not tk: continue
    games += 1
    sp = spawns(r["map"], r["w"], r["h"])
    def where(x, y, team):
        if not sp: return "?"
        a, b = sp if team == "teamA" else sp[::-1]
        da = ((x - a[0]) ** 2 + (y - a[1]) ** 2) ** 0.5; db = ((x - b[0]) ** 2 + (y - b[1]) ** 2) ** 0.5
        f = da / (da + db + 1e-9)
        return "own" if f < 0.4 else ("enemy" if f > 0.6 else "middle")
    for d in r["deaths"]:
        if d[1] == tk:
            ndeath += 1
            w = where(d[8], d[9], tk)
            ctx[(w, "camp" if d[4] != "champion" else "champ")] += 1
            ph = "r<150" if d[0] < 150 else ("r150-400" if d[0] < 400 else ("r400-800" if d[0] < 800 else "r800+"))
            phase[ph] += 1
            # enemies involved: killer + assists on this victim within 3 rounds
            vid = d[3]
            n_ass = sum(1 for a in r.get("assists", []) if False)
            inv_n = 1 + sum(1 for k in r["kills"] if False)
        else:
            w = where(d[8], d[9], d[1])
            opp_ctx[(w, "camp" if d[4] != "champion" else "champ")] += 1
    lost += sum(int(x[6] or 0) for x in r["losses"] if x[1] == tk)
print(f"{name}: {games} games, {ndeath} deaths ({ndeath/max(1,games):.1f}/game), gems lost {lost/max(1,games):.0f}/game")
print("our deaths by (where, cause):", sorted(ctx.items(), key=lambda x: -x[1]))
print("by phase:", sorted(phase.items()))
print("opponent deaths by (where relative to them, cause):", sorted(opp_ctx.items(), key=lambda x: -x[1]))
