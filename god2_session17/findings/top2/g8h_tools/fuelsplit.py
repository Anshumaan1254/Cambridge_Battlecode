"""Fuel-outs per bot split by round (< 10 init vs >= 10), per map and per champion, from a localbench folder.

  python fuelsplit.py TAG NAME_A NAME_B      (NAME_A = first bot on the localbench command line = teamA in <map>_A.json)
"""
import collections, glob, json, os, sys

tag, na, nb = sys.argv[1], sys.argv[2], sys.argv[3]
out = f"C:/battlecode/cache/bench/{tag}"
stat = {n: dict(games=0, wins=0, gems=0, deaths=0, faults=0, fo=0, fo_init=0, fo_late=0, maps=collections.Counter(),
                maps_init=collections.Counter(), maps_late=collections.Counter(), champs=collections.Counter(),
                rounds=collections.Counter()) for n in (na, nb)}
for f in sorted(glob.glob(f"{out}/*.json")):
    name = os.path.basename(f)[:-5]
    mp, side = name.rsplit("_", 1)
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    team_of = {na: "teamA" if side == "A" else "teamB", nb: "teamB" if side == "A" else "teamA"}
    gems = {t["team"]: int(t["submittedGems"]) for t in d["teams"]}
    deaths = collections.Counter()
    for c in d["champions"]:
        deaths[c["team"]] += int(c["metrics"]["deaths"])
    fl = (d.get("diagnostics") or {}).get("botFaults") or {}
    for n in (na, nb):
        s, t = stat[n], team_of[n]
        s["games"] += 1
        s["wins"] += d["match"]["outcome"] == t
        s["gems"] += gems.get(t, 0)
        s["deaths"] += deaths[t]
        s["faults"] += int(fl.get(t, 0) or 0)
    for e in d.get("events", []):
        if e.get("kind") != "fuelExhausted":
            continue
        t = e["owner"].get("team")
        n = na if t == team_of[na] else nb
        s = stat[n]
        for en in e.get("entries", []):
            r = en["timestamp"]["round"]
            s["fo"] += 1
            s["maps"][mp] += 1
            s["champs"][e["owner"].get("name")] += 1
            s["rounds"][min(r, 9) if r < 10 else (r // 100) * 100 + 100] += 1
            if r < 10:
                s["fo_init"] += 1
                s["maps_init"][mp] += 1
            else:
                s["fo_late"] += 1
                s["maps_late"][mp] += 1
for n in (na, nb):
    s = stat[n]
    g = max(1, s["games"])
    print(f"== {n}: games {s['games']} wins {s['wins']} ({100 * s['wins'] / g:.1f}%) gems/g {s['gems'] / g:.0f} deaths/g {s['deaths'] / g:.1f} faults {s['faults']}")
    print(f"   fuel-outs {s['fo']} = {s['fo'] / g:.2f}/game | rounds<10: {s['fo_init']} = {s['fo_init'] / g:.2f}/game | rounds>=10: {s['fo_late']} = {s['fo_late'] / g:.2f}/game")
    print("   top maps (all):", ", ".join(f"{m} {c}" for m, c in s["maps"].most_common(8)))
    print("   top maps (<10):", ", ".join(f"{m} {c}" for m, c in s["maps_init"].most_common(8)))
    print("   top maps (>=10):", ", ".join(f"{m} {c}" for m, c in s["maps_late"].most_common(8)))
    print("   champions:", ", ".join(f"{m} {c}" for m, c in s["champs"].most_common(12)))
    print("   by round (1-9 exact, then upper bound of 100-round bucket):", sorted(s["rounds"].items()))
