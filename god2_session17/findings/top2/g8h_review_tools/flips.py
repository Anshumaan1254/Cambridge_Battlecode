import glob, json, os, collections
def load(tag):
    res = {}
    for f in sorted(glob.glob(f"C:/battlecode/cache/bench/{tag}/*.json")):
        name = os.path.basename(f)[:-5]
        mp, side = name.rsplit("_", 1)
        d = json.load(open(f, encoding="utf-8"))
        me = "teamA" if side == "A" else "teamB"; op = "teamB" if side == "A" else "teamA"
        gems = {t["team"]: int(t["submittedGems"]) for t in d["teams"]}
        dm = collections.Counter(); col = collections.Counter(); lost = collections.Counter(); kills = collections.Counter()
        for c in d["champions"]:
            dm[c["team"]] += int(c["metrics"]["deaths"]); col[c["team"]] += int(c["metrics"]["collectedGems"]); kills[c["team"]] += int(c["metrics"]["kills"])
        res[(mp, side)] = dict(win=d["match"]["outcome"] == me, g=gems[me], og=gems[op], r=d["match"]["roundsCompleted"], d=dm[me], od=dm[op], col=col[me], ocol=col[op], k=kills[me])
    return res
a = load("g8h_vs_b54"); b = load("g8_vs_b54")
print(f"{'game':28s} | {'g8h: res score  rnd  deaths col':36s} | {'g8: res score  rnd  deaths col':36s}")
for k in sorted(a):
    x, y = a[k], b[k]
    if x["win"] != y["win"]:
        f = lambda z: f"{'W' if z['win'] else 'L'} {z['g']:4d}-{z['og']:4d} r{z['r']:4d} d{z['d']:2d}-{z['od']:2d} col{z['col']:4d}-{z['ocol']:4d}"
        print(f"{k[0]+'_'+k[1]:28s} | {f(x):36s} | {f(y):36s}")
tot = lambda r, key: sum(v[key] for v in r.values()) / len(r)
for key in ("g", "og", "d", "od", "col", "ocol", "k", "r"):
    print(key, round(tot(a, key), 1), round(tot(b, key), 1))
