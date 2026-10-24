#!/usr/bin/env python3
"""Mechanism metrics of an in-bot A/B sweep, per module bit (bots/god2b g2ab.h):
    python tools/top2/g2_mech.py REPLAY_DIR N [--bits bank,deny,fight,mid] [--jobs 4] [--upto 1000] [--ref REF_REPLAY_DIR]

Runs tools/live/walks.mjs (walk rounds per body by what came next: farm / fight / bank / ...) and tools/live/timebudget.mjs (body-time:
dead / farm / fight / oncamp / walk / idle; with an enemy within 8: farm / walk) over every replay in REPLAY_DIR (cached in
REPLAY_DIR/_walks.jsonl and _tb.jsonl), finds our side from experiments/live/lists/groups_matches.jsonl, the variant from the map and side
(variant_of.strat_hash % N), and prints our team's means with each bit on vs off. These move far less from game to game than wins do:
they say whether a module changes what it was built to change."""
import json, math, os, subprocess, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "live"))
os.chdir(ROOT)
from variant_of import strat_hash, load_sigs
SALT = int(sys.argv[sys.argv.index("--salt") + 1]) if "--salt" in sys.argv else 0  # P.g2ab_salt of the sweep

rdir, N = sys.argv[1], int(sys.argv[2])
names = sys.argv[sys.argv.index("--bits") + 1].split(",") if "--bits" in sys.argv else ["bank", "deny", "fight", "mid"]
jobs = sys.argv[sys.argv.index("--jobs") + 1] if "--jobs" in sys.argv else "4"
upto = sys.argv[sys.argv.index("--upto") + 1] if "--upto" in sys.argv else "1000"
ref = sys.argv[sys.argv.index("--ref") + 1] if "--ref" in sys.argv else ""
ms = {}
for l in open("experiments/live/lists/groups_matches.jsonl", encoding="utf-8"):
    m = json.loads(l)
    ms[m["matchId"][:8]] = m
sigs = load_sigs()


def load(p):
    out = {}
    if os.path.exists(p):
        for l in open(p, encoding="utf-8"):
            try:
                d = json.loads(l)
                out[os.path.basename(d["file"].replace("\\", "/"))] = d
            except Exception:
                pass
    return out


def build(rdir):
    """per replay of rdir: (opp, map, side) -> our metrics (runs the node tools first; results cached in rdir)"""
    rdir = rdir.replace("\\", "/").rstrip("/")
    files = sorted(f"{rdir}/{f}" for f in os.listdir(rdir) if f.endswith(".repl26a"))
    wj, tj = f"{rdir}/_walks.jsonl", f"{rdir}/_tb.jsonl"
    subprocess.run([sys.executable, "tools/live/par.py", jobs, wj, "tools/live/walks.mjs", "0", upto, "--"] + files, check=False, capture_output=True)
    subprocess.run([sys.executable, "tools/live/par.py", jobs, tj, "tools/live/timebudget.mjs", upto, "--"] + files, check=False, capture_output=True)
    W, T = load(wj), load(tj)
    out = {}
    for f in files:
        b = os.path.basename(f)
        m = ms.get(b.rsplit("_", 1)[1][:8])
        if not m or b not in W or b not in T:
            continue
        us = next(t for t in m["teams"] if t["name"] == "HouseOfCoders")
        op = next(t for t in m["teams"] if t["name"] != "HouseOfCoders")
        ui, oi = ("0", "1") if us["side"] == "a" else ("1", "0")
        mp = m["map"].replace("-", "_")
        if mp not in sigs:
            continue
        w, h, c = sigs[mp]
        v = strat_hash(w, h, c, 0 if us["side"] == "a" else 1, SALT) % N
        wu, tu, to = W[b]["teams"][ui], T[b]["teams"][ui], T[b]["teams"][oi]
        alive = max(1, sum(tu[k] for k in ("farm", "fight", "oncamp", "walk", "idle")))
        ne = max(1, tu.get("nearE", 0))
        out[(op["name"], mp, us["side"])] = {"v": v, "opp": op["name"], "win": us.get("result") == "win",
                 "walk_fight": wu.get("fight", 0), "walk_farm": wu.get("farm", 0), "walk_bank": wu.get("bank", 0), "walk_recall": wu.get("recall", 0),
                 "dead%": 100 * tu["dead"] / max(1, tu["dead"] + alive), "farm%": 100 * tu["farm"] / alive, "walk%": 100 * tu["walk"] / alive,
                 "oncamp%": 100 * tu["oncamp"] / alive, "nearE%": 100 * tu.get("nearE", 0) / alive,
                 "nearE_farm%": 100 * tu.get("nearE_farm", 0) / ne, "nearE_walk%": 100 * tu.get("nearE_walk", 0) / ne,
                 "opp_farm%": 100 * to["farm"] / max(1, sum(to[k] for k in ("farm", "fight", "oncamp", "walk", "idle")))}
    return out, len(files)


G, nfiles = build(rdir)
rows = list(G.values())
print(f"{len(rows)} games with variants (of {nfiles} replays)")
KEYS = ["walk_fight", "walk_farm", "walk_bank", "dead%", "farm%", "walk%", "oncamp%", "nearE%", "nearE_farm%", "nearE_walk%", "opp_farm%"]


def ms_(v):
    if not v:
        return float("nan"), float("nan")
    m = sum(v) / len(v)
    s = math.sqrt(sum((x - m) ** 2 for x in v) / max(1, len(v) - 1))
    return m, s / math.sqrt(len(v))


print("all: " + "  ".join(f"{k} {ms_([r[k] for r in rows])[0]:.1f}" for k in KEYS))
nb = max(1, int(round(math.log2(N))))
for bt in range(nb):
    on = [r for r in rows if (r["v"] >> bt) & 1]
    off = [r for r in rows if not (r["v"] >> bt) & 1]
    print(f"\n{names[bt] if bt < len(names) else bt}: on {len(on)} off {len(off)}")
    for k in KEYS:
        (a, sa), (b, sb) = ms_([r[k] for r in on]), ms_([r[k] for r in off])
        print(f"  {k:12s} on {a:7.1f}  off {b:7.1f}  diff {a - b:+7.1f} +- {math.sqrt(sa * sa + sb * sb):5.1f}")

if ref:
    R, _ = build(ref)
    pairs = [(G[k], R[k]) for k in G if k in R]
    print(f"\nPAIRED vs {ref} ({len(pairs)} cells; delta = this sweep - ref, same opponent / map / side)")
    print("all: " + "  ".join(f"{k} {ms_([g[k] - r[k] for g, r in pairs])[0]:+.1f}" for k in KEYS))
    for bt in range(nb):
        print(f"{names[bt] if bt < len(names) else bt}:")
        for k in KEYS:
            (a, sa) = ms_([g[k] - r[k] for g, r in pairs if (g["v"] >> bt) & 1])
            (b, sb) = ms_([g[k] - r[k] for g, r in pairs if not (g["v"] >> bt) & 1])
            print(f"  {k:12s} delta on {a:+7.1f}  off {b:+7.1f}  effect {a - b:+7.1f} +- {math.sqrt(sa * sa + sb * sb):5.1f}")
