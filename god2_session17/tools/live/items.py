#!/usr/bin/env python3
"""Item purchase patterns per team and champion: first emblems (order), shards by r300, final items.
python tools/live/items.py TEAM [TEAM...] [--since ISO]"""
import collections, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import load, side
args = [a for a in sys.argv[1:] if not a.startswith("--")]
since = sys.argv[sys.argv.index("--since") + 1] if "--since" in sys.argv else ""
rs = load(since)
def short(it):
    p = it.split()
    fam = p[0][0]  # Monster Power Durability Treasure Jungle Home Bruiser
    stat = p[-1][0].lower()  # strength health focus
    return fam + stat
for name in args:
    if name in (since,): continue
    emb = collections.defaultdict(collections.Counter)
    first3 = collections.defaultdict(collections.Counter)
    shards300 = collections.defaultdict(list)
    stat300 = collections.defaultdict(collections.Counter)
    n = collections.Counter()
    for r in rs:
        tk = side(r, name)
        if not tk: continue
        for c in r["champs"]:
            if c["team"] != tk: continue
            n[c["name"]] += 1
            combos = [x for x in r["combos"] if x[1] == tk and x[3] == c["id"]]
            seq = [short(x[5][2]) for x in combos if isinstance(x[5], list) and x[5][2]]
            first3[c["name"]][" > ".join(seq[:3])] += 1
            for s in seq: emb[c["name"]][s] += 1
            buys = [x for x in r["buys"] if x[1] == tk and x[3] == c["id"] and x[0] <= 300]
            q = sum(int(x[6] or 1) for x in buys)
            shards300[c["name"]].append(q)
            for x in buys:
                it = x[5][2] if isinstance(x[5], list) else str(x[5])
                stat300[c["name"]][it.split()[-1]] += int(x[6] or 1)
    print(f"\n===== {name}")
    for ch, k in n.most_common():
        avg300 = sum(shards300[ch]) / max(1, len(shards300[ch]))
        st = stat300[ch]; tot = sum(st.values()) or 1
        print(f"  {ch:14s} games {k:3d} | shards by r300 {avg300:5.1f} ({', '.join(f'{s} {100*v/tot:.0f}%' for s, v in st.most_common())})")
        print(f"      first emblems: " + " | ".join(f"{s or '-'} x{v}" for s, v in first3[ch].most_common(3)))
        print(f"      emblems/game: " + ", ".join(f"{s} {v/k:.1f}" for s, v in emb[ch].most_common(6)))
