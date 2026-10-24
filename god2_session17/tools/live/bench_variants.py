#!/usr/bin/env python3
"""Per-variant / per-bit split of a local localbench.py run of an in-bot A/B package (P.ab_variants N; bot A is the package).
  python tools/live/bench_variants.py TAG N [--nomask]
The variant of each game is recomputed like strat.cpp: hash(W, H, total camps, side, enemy draft mask) % N, the enemy mask from the
statistics' roster (bot A's opponent picks)."""
import glob, json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from variant_of import strat_hash, load_sigs

DRAFT = {"Ryth": 0, "Vesper Vale": 1, "Vendetta": 2, "Cassi": 3, "Issac": 3, "Stellar": 4, "Prism": 5, "Marcella": 6, "Willow": 7, "Ren": 8,
         "Varg": 9, "Tavi": 10, "Heart of Ruin": 11}
tag, n = sys.argv[1], int(sys.argv[2])
nomask = "--nomask" in sys.argv
sigs = load_sigs()
res = collections.defaultdict(lambda: [0, 0, 0.0, 0.0, 0.0])  # wins, games, gems us, gems them, deaths us
for f in glob.glob(f"C:/battlecode/cache/bench/{tag}/*.json"):
    name = os.path.basename(f)[:-5]
    mp, side = name.rsplit("_", 1)
    d = json.load(open(f, encoding="utf-8"))
    us = "teamA" if side == "A" else "teamB"
    them = "teamB" if us == "teamA" else "teamA"
    w, h, c = sigs[mp.replace("-", "_")]
    em = 0
    if not nomask:
        for x in d["roster"]["champions"]:
            if x["team"] == them and x["name"] in DRAFT:
                em |= 1 << DRAFT[x["name"]]
    v = strat_hash(w, h, c, 0 if side == "A" else 1, em) % n
    gems = {t["team"]: int(t["submittedGems"]) for t in d["teams"]}
    deaths = sum(int(ch["metrics"]["deaths"]) for ch in d["champions"] if ch["team"] == us)
    r = res[v]
    r[0] += d["match"]["outcome"] == us
    r[1] += 1
    r[2] += gems[us]
    r[3] += gems[them]
    r[4] += deaths
for v in sorted(res):
    w_, g, a, b, dd = res[v]
    print(f"variant {v:2d}: {w_}/{g}  gems {a / g:.0f}-{b / g:.0f}  deaths {dd / g:.1f}")
bits = max(1, (n - 1).bit_length())
for b in range(bits):
    on = [res[v] for v in res if v >> b & 1]
    off = [res[v] for v in res if not v >> b & 1]
    won, gon = sum(x[0] for x in on), sum(x[1] for x in on)
    woff, goff = sum(x[0] for x in off), sum(x[1] for x in off)
    don = sum(x[4] for x in on) / max(1, gon)
    doff = sum(x[4] for x in off) / max(1, goff)
    print(f"bit {b}: on {won}/{gon} ({100 * won / max(1, gon):.0f}%) deaths {don:.1f} | off {woff}/{goff} ({100 * woff / max(1, goff):.0f}%) deaths {doff:.1f}")
