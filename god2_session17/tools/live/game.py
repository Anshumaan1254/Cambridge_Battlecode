#!/usr/bin/env python3
"""Timeline of one compact match: python tools/live/game.py MATCHID|prefix [--us NAME] [--to ROUND]"""
import glob, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
args = sys.argv[1:]
mid = args[0]
us = args[args.index("--us") + 1] if "--us" in args else "HouseOfCoders"
to = int(args[args.index("--to") + 1]) if "--to" in args else 99999
f = glob.glob(os.path.join(ROOT, "experiments", "live", "compact", mid + "*.json"))[0]
r = json.load(open(f, encoding="utf-8"))
SH = {'Ryth': 'Ry', 'Vesper Vale': 'Ve', 'Vendetta': 'Vd', 'Cassi': 'Ca', 'Issac': 'Is', 'Stellar': 'St', 'Prism': 'Pr', 'Marcella': 'Ma', 'Willow': 'Wi', 'Ren': 'Re', 'Varg': 'Va', 'Tavi': 'Ta', 'Heart of Ruin': 'HoR'}
tk = {t["team"]: ("US" if t["name"] == us else "TH") for t in r["teams"]}
print(r["map"], f"{r['w']}x{r['h']}", "rounds", r["rounds"], "outcome", tk[r["outcome"]], {tk[t['team']]: (t['name'], t['draft'], t['gems']) for t in r['teams']})
ev = []
for x in r["deaths"]:
    k = x[5]
    ev.append((x[0], f"{tk[x[1]]} {SH.get(x[2],x[2])} DIES at ({x[8]},{x[9]}) by {x[4]}:{(SH.get(k[2],k[2]) if isinstance(k,list) else k)}"))
for x in r["clears"]:
    ev.append((x[0], f"{tk[x[1]]} {SH.get(x[2],x[2])} clear grp{x[5][3] if isinstance(x[5],list) else x[5]} at ({x[8]},{x[9]})"))
for x in r["colls"]:
    if x[4] == "campGroup":
        ev.append((x[0], f"{tk[x[1]]} {SH.get(x[2],x[2])} +{x[6]} gems from grp{x[5][3]} at ({x[8]},{x[9]})"))
    else:
        ev.append((x[0], f"{tk[x[1]]} {SH.get(x[2],x[2])} +{x[6]} gems from kill"))
for x in r["subs"]:
    ev.append((x[0], f"{tk[x[1]]} {SH.get(x[2],x[2])} BANKS {x[6]} at ({x[8]},{x[9]})"))
for x in r["losses"]:
    if int(x[6] or 0) > 0:
        ev.append((x[0], f"{tk[x[1]]} {SH.get(x[2],x[2])} LOSES {x[6]} gems ({x[4]})"))
for x in r["buys"]:
    ev.append((x[0], f"{tk[x[1]]} {SH.get(x[2],x[2])} buys {x[5][2] if isinstance(x[5],list) else x[5]} x{x[6]} for {x[7]}"))
for x in r["fuel"]:
    ev.append((x[0], f"{tk[x[1]]} {SH.get(x[2],x[2])} FUEL EXHAUSTED"))
ev.sort(key=lambda e: e[0])
for t, s in ev:
    if t <= to:
        print(f"r{t:4d} {s}")
