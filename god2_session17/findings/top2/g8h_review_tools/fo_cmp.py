import glob, json, os, sys, collections
def load(tag, me):
    out = f"C:/battlecode/cache/bench/{tag}"
    res = {}
    for f in sorted(glob.glob(f"{out}/*.json")):
        name = os.path.basename(f)[:-5]
        mp, side = name.rsplit("_", 1)
        d = json.load(open(f, encoding="utf-8"))
        t = "teamA" if side == "A" else "teamB"
        init = late = 0
        lates = []
        rounds = collections.Counter()
        for e in d.get("events", []):
            if e.get("kind") != "fuelExhausted" or e["owner"].get("team") != t:
                continue
            for en in e.get("entries", []):
                r = en["timestamp"]["round"]
                if r < 10:
                    init += 1; rounds[r] += 1
                else:
                    late += 1; lates.append((r, e["owner"].get("name")))
        champs = sorted(c["name"] for c in d["champions"] if c["team"] == t)
        res[(mp, side)] = dict(init=init, late=late, lates=lates, win=d["match"]["outcome"] == t, champs=champs, rounds=dict(rounds),
                               gems={x["team"]: int(x["submittedGems"]) for x in d["teams"]}, me=t)
    return res
a = load("g8h_vs_b54", "g8h"); b = load("g8_vs_b54", "g8")
print(f"{'map/side':32s} {'g8h init':>8s} {'g8 init':>8s} {'g8h late':>8s} {'g8 late':>8s}  res(g8h,g8)  g8h-rounds   champs(g8h)")
tot = collections.Counter()
for k in sorted(a):
    x, y = a[k], b.get(k)
    flag = " <-- g8h worse init" if x["init"] > y["init"] else ""
    print(f"{k[0]+'_'+k[1]:32s} {x['init']:8d} {y['init']:8d} {x['late']:8d} {y['late']:8d}  {'W' if x['win'] else 'L'}{'W' if y['win'] else 'L'}  {str(x['rounds']):24s} {','.join(x['champs'])}{flag}")
    if x["lates"]: print("    g8h late:", x["lates"])
