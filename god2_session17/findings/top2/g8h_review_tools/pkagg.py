import json, sys, collections
def agg(f):
    own = dict(pr=0, runs=[], games=0); opp = dict(pr=0)
    for l in open(f, encoding="utf-8"):
        r = json.loads(l)
        side = r["file"].rsplit("_", 1)[1][0]
        me, op = ("0", "1") if side == "A" else ("1", "0")
        own["games"] += 1
        own["pr"] += r["teams"][me]["pocketRounds"]; opp["pr"] += r["teams"][op]["pocketRounds"]
        for x in r["teams"][me]["runs"]:
            own["runs"].append((x["rounds"], x["maxIdle"], r["file"], x["type"], x["from"], x["at"], x["last"], x["acts"], x["endHow"], x["gems0"], x["gems1"]))
    return own, opp
for name, f in (("g8h", sys.argv[1]), ("g8", sys.argv[2])):
    own, opp = agg(f)
    runs = own["runs"]
    g = own["games"]
    idle12 = [x for x in runs if x[1] >= 12]
    idle25 = [x for x in runs if x[1] >= 25]
    print(f"== {name}: games {g}, own pocket body-rounds {own['pr']} ({own['pr']/g:.1f}/game; opp {opp['pr']/g:.1f}), pocket runs >= 5 rounds: {len(runs)}, "
          f"runs with >= 12 idle rounds: {len(idle12)}, >= 25 idle: {len(idle25)}, idle body-rounds (max idle per run) {sum(x[1] for x in runs)}")
    bymap = collections.Counter()
    for x in runs: bymap[x[2].rsplit('_',1)[0]] += x[0]
    print("   pocket rounds by map:", bymap.most_common(8))
    print("   longest idle stretches in a pocket:")
    for x in sorted(runs, key=lambda x: -x[1])[:8]:
        print("     idle", x[1], "run", x[0], x[2], x[3], "from r", x[4], "at", x[5], "->", x[6], "acts", x[7], x[8], "gems", x[9], "->", x[10])
