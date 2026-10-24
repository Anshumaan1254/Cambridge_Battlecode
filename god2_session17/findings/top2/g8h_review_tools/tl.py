# body timeline from a pk.mjs cache: python tl.py CACHE.json.gz TEAM R0 R1 [STEP] [bodyidx]
import gzip, json, sys
f, team, r0, r1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
step = int(sys.argv[5]) if len(sys.argv) > 5 else 10
only = int(sys.argv[6]) if len(sys.argv) > 6 else None
X = json.loads(gzip.decompress(open(f, "rb").read()))
d, T = X["d"], X["T"]
bodies = [b for b in d["meta"]["bodies"] if b["team"] == team and (only is None or b["index"] == only)]
print("drafts", d["meta"]["drafts"], "final", d["meta"]["finalRound"], "submitted", d["meta"]["submitted"])
byr = {s["r"]: s for s in d["rounds"] if s}
for b in bodies:
    print(f"== body {b['index']} {b['type']}")
    line = []
    for r in range(r0, r1 + 1, step):
        s = byr.get(r)
        if not s: continue
        c = next((q for q in s["ch"] if q[0] == b["index"]), None)
        if not c: continue
        line.append(f"r{r}:({c[3]},{c[4]}){'' if c[7] else 'DEAD'} g{c[8]} hp{c[5]}")
    for i in range(0, len(line), 6):
        print("   " + " | ".join(line[i:i + 6]))
    ev = [e for e in d["events"] if e.get("who") == b["index"] and r0 <= e["r"] <= r1 and e["k"] in ("Recall", "Gems submitted", "Banked", "Death", "Cast ability", "Cancel channel", "Submit gems", "CaptureGems", "Teleport channel", "Teleport complete", "Consumable", "Shop")]
    out = []
    for e in ev:
        if e["k"] == "Cast ability": out.append(f"{e['r']}:cast{e.get('slot')}{e.get('to','')}")
        elif e["k"] == "CaptureGems": out.append(f"{e['r']}:cap+{e['gems']}")
        elif e["k"] == "Banked": out.append(f"{e['r']}:BANK{e['gems']}@{e['at']}")
        elif e["k"] == "Death": out.append(f"{e['r']}:DEATH bag{e['bag']}@{e['at']}")
        elif e["k"] == "Shop": continue
        else: out.append(f"{e['r']}:{e['k']}{e.get('to','')}")
    print("   ev:", " ".join(out)[:3000])
