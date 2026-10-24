import json, sys, collections
def agg(f):
    own = dict(aba=0, games=0, longest=[], per=[]); opp = dict(aba=0, per=[])
    permap = {}
    for l in open(f, encoding="utf-8"):
        r = json.loads(l)
        fn = r["file"].split("\\")[-1].split("/")[-1]
        side = fn.rsplit("_", 1)[1][0]
        me, op = ("0", "1") if side == "A" else ("1", "0")
        t = r["teams"]
        own["aba"] += t[me]["aba"]; own["games"] += 1; own["per"].append(t[me]["per_body"]); own["longest"].append((t[me]["longest"], fn))
        opp["aba"] += t[op]["aba"]; opp["per"].append(t[op]["per_body"])
        permap[fn] = (t[me]["per_body"], t[me]["longest"])
    return own, opp, permap
a = agg(sys.argv[1]); b = agg(sys.argv[2])
for name, (own, opp, pm) in (("g8h", a), ("g8", b)):
    g = own["games"]
    print(f"{name}: games {g} A-B-A per body per game {sum(own['per'])/g:.1f} (opp _b54 {sum(opp['per'])/g:.1f}); longest runs {sorted(own['longest'], reverse=True)[:6]}")
print("maps where g8h per-body A-B-A exceeds g8 by > 10:")
for k in sorted(a[2]):
    x, y = a[2][k], b[2].get(k)
    if y and x[0] - y[0] > 10: print("   ", k, "g8h", x, "g8", y)
