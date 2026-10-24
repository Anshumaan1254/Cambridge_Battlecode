#!/usr/bin/env python3
"""Opening captures: for each team, captures before round R: count, gems, where (own/middle/enemy half), solo vs shared.
python tools/live/open_caps.py TEAM [TEAM...] [--R 200] [--groups-only] [--vs-top N]"""
import collections, json, os, sys, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import load, side, top_ranks
args = [a for a in sys.argv[1:] if not a.startswith("--")]
R = int(sys.argv[sys.argv.index("--R") + 1]) if "--R" in sys.argv else 200
vs_top = int(sys.argv[sys.argv.index("--vs-top") + 1]) if "--vs-top" in sys.argv else 0
args = [a for a in args if a != str(R) and a != str(vs_top)]
rs = load()
rk = top_ranks()
if "--groups-only" in sys.argv:
    ids = {json.loads(l)["matchId"] for l in open("experiments/live/lists/groups_matches.jsonl", encoding="utf-8")}
    rs = [r for r in rs if r["id"] in ids]
sp = json.load(open("experiments/live/spawns.json")) if os.path.exists("experiments/live/spawns.json") else {}
for name in args:
    n = 0; caps = []; first = []; where = collections.Counter(); shared = 0; ncap = 0; gem0 = 0
    for r in rs:
        tk = side(r, name)
        if not tk: continue
        opp = next(t for t in r["teams"] if t["team"] != tk)
        if vs_top and rk.get(opp["name"], 999) > vs_top: continue
        n += 1
        s = sp.get(r["map"])
        cs = [x for x in r["colls"] if x[1] == tk and x[4] == "campGroup" and x[0] <= R]
        # group captures by (round, group id): shared captures appear as several entries with same round & group
        by = collections.defaultdict(list)
        for x in cs: by[(x[0], x[5][3])].append(x)
        caps.append(len(by))
        for (rnd, gid), xs in by.items():
            ncap += 1
            g = sum(int(x[6] or 0) for x in xs)
            gem0 += g == 0
            shared += len(xs) > 1
            if s:
                a, b = s if tk == "teamA" else s[::-1]
                x, y = xs[0][8], xs[0][9]
                da = ((x - a[0]) ** 2 + (y - a[1]) ** 2) ** .5; db = ((x - b[0]) ** 2 + (y - b[1]) ** 2) ** .5
                f = da / (da + db + 1e-9)
                where["own" if f < 0.4 else ("enemy" if f > 0.6 else "middle")] += 1
        fr = sorted(by.keys())
        first.append(fr[0][0] if fr else R)
    if not n: print(name, "no games"); continue
    tot = sum(where.values()) or 1
    print(f"{name:24s} games {n:3d} | captures<r{R}: {st.mean(caps):4.1f} | first capture r{st.median(first):.0f} | gold-only {100*gem0/max(1,ncap):3.0f}% | shared {100*shared/max(1,ncap):3.0f}% | own {100*where['own']/tot:3.0f}% mid {100*where['middle']/tot:3.0f}% enemy {100*where['enemy']/tot:3.0f}%")
