"""Crystals bought, fuel-outs and results on the hop maps for several bench tags: python hopcmp.py TAG:NAME ..."""
import json, os, sys
MAPS = ["00road-of-riches", "01shortcut", "00quadrants", "00swirl", "01fracture", "01big-world"]
tags = [a.split(":") for a in sys.argv[1:]]
print("map/side".ljust(22) + "".join(n.rjust(16) for _, n in tags))
tot = {n: [0, 0, 0] for _, n in tags}
for m in MAPS:
    for side in "AB":
        row = f"{m}_{side}".ljust(22)
        for t, n in tags:
            f = f"C:/battlecode/cache/bench/{t}/{m}_{side}.json"
            if not os.path.exists(f):
                row += "-".rjust(16)
                continue
            d = json.load(open(f, encoding="utf-8"))
            me = "teamA" if side == "A" else "teamB"
            cr = fo = 0
            for e in d["events"]:
                if e["owner"].get("team") != me:
                    continue
                if e["kind"] == "buyConsumable":
                    cr += sum(1 for x in e["entries"] if x["target"]["name"] == "Teleport Crystal")
                if e["kind"] == "fuelExhausted":
                    fo += len(e["entries"])
            win = d["match"]["outcome"] == me
            tot[n][0] += cr; tot[n][1] += fo; tot[n][2] += win
            row += f"{'W' if win else 'L'} cr{cr:3d} fo{fo:3d}".rjust(16)
        print(row)
print("totals (crystals, fuel-outs, wins on these 12 games):", tot)
