import glob, json, os, re, collections
TY = {0: "Ryth", 1: "Vesper Vale", 2: "Vendetta", 5: "Stellar", 6: "Prism", 7: "Marcella", 8: "Willow", 9: "Ren", 10: "Varg", 11: "Tavi", 12: "Heart of Ruin"}
tot_g8 = tot_g8h = 0; n = 0; later = []; earlier = []
for d in sorted(glob.glob("C:/battlecode/cache/g8h_rv/runs/trA/*_A")):
    mp = os.path.basename(d)[:-2]
    txt = open(d + "/team-a.stdout", encoding="utf-8", errors="replace").read()
    first = {}
    for m in re.finditer(r"\bT r=(\d+) b=\d+ ty=(\d+) ", txt):
        first.setdefault(TY.get(int(m.group(2)), m.group(2)), int(m.group(1)))
    st = json.load(open(f"C:/battlecode/cache/bench/g8_vs_b54/{mp}_A.json", encoding="utf-8"))
    lastfo = collections.Counter()
    for e in st["events"]:
        if e["kind"] == "fuelExhausted" and e["owner"]["team"] == "teamA":
            for en in e["entries"]:
                r = en["timestamp"]["round"]
                if r < 12:
                    lastfo[e["owner"]["name"]] = max(lastfo[e["owner"]["name"]], r)
    champs = [c["name"] for c in st["champions"] if c["team"] == "teamA"]
    g8 = {c: max(2, lastfo.get(c, 0) + 1) for c in champs}
    row = []
    for c in champs:
        a, b = first.get(c), g8[c]
        if a is None: continue
        row.append(f"{c.split()[0][:4]} {b}->{a}")
        tot_g8 += b; tot_g8h += a; n += 1
        if a > b: later.append((mp, c, b, a))
        if a < b: earlier.append((mp, c, b, a))
    print(f"{mp:24s} g8->g8h first turn: {', '.join(row)}")
print(f"mean first turn g8 {tot_g8/n:.2f}  g8h {tot_g8h/n:.2f}  (bodies {n})")
print("g8h later than g8:", len(later), later)
print("g8h earlier than g8:", len(earlier))
