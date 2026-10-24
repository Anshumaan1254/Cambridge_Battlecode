"""Aggregate traced runs: python tragg.py RUNDIR"""
import collections, glob, json, os, re, sys

rd = sys.argv[1]
tot = collections.Counter()
rows = []
for d in sorted(glob.glob(rd + "/*_A")) + sorted(glob.glob(rd + "/*_B")):
    f = d + "/team-a.stdout" if d.endswith("_A") else d + "/team-b.stdout"
    if not os.path.exists(f):
        continue
    txt = open(f, encoding="utf-8", errors="replace").read()
    c = collections.Counter()
    for k in ("NP", "US", "PG", "CT", "PD", "OB", "DH", "PI", "BANK", "NB"):
        c[k] = len(re.findall(r"\b" + k + r" r=", txt))
    np_dash = len(re.findall(r"\bNP r=\d+ b=\d+ ty=\d+ task=\d+ g=-?\d+ pos=\S+ d=\d+ best=\d+ since=-?\d+ doff=(-?\d+) dash=([01])", txt))
    np_off = 0
    for m in re.finditer(r"\bNP r=(\d+) b=\d+ ty=\d+ task=\d+ g=-?\d+ pos=\S+ d=\d+ best=\d+ since=-?\d+ doff=(-?\d+) dash=(-?\d+) home=(\d+)", txt):
        r, doff, dash, home = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
        if dash >= 0 and doff < r and home < (1 << 20):
            np_off += 1
    rc_sup = len(re.findall(r"\bRC r=\d+ me=\d+ enemy=\d+ at=\S+ streak=1 counted=0", txt))
    rc_all = len(re.findall(r"\bRC r=", txt))
    # first full turn per body, dash-off body-rounds
    first = {}
    doff_rounds = 0
    turns = 0
    for m in re.finditer(r"\bT r=(\d+) b=(\d+) ty=\d+ task=\d+ g=-?\d+ pos=\S+ hp=\S+ gems=\d+ gold=\d+ doff=(-?\d+)", txt):
        r, b, doff = int(m.group(1)), int(m.group(2)), int(m.group(3))
        first.setdefault(b, r)
        turns += 1
        if doff >= r:
            doff_rounds += 1
    stats = json.load(open(d + "/stats.json", encoding="utf-8"))
    me = "teamA" if d.endswith("_A") else "teamB"
    gems = {t["team"]: int(t["submittedGems"]) for t in stats["teams"]}
    win = stats["match"]["outcome"] == me
    c["np_off"] = np_off
    c["rc_sup"] = rc_sup
    c["rc_all"] = rc_all
    c["doff_rounds"] = doff_rounds
    c["turns"] = turns
    tot.update(c)
    rows.append((os.path.basename(d), "W" if win else "L", gems.get(me), gems.get("teamB" if me == "teamA" else "teamA"), sorted(first.values()), c))
print(f"{'map':26s} res  score      first-turns          NP np_off US  PG CT PD  OB  DH  RCsup/all doff%  BANK NB")
for name, res, g, og, ft, c in rows:
    pct = 100.0 * c["doff_rounds"] / max(1, c["turns"])
    print(f"{name:26s} {res}  {g:4d}-{og:4d}  {str(ft):20s} {c['NP']:3d} {c['np_off']:3d} {c['US']:3d} {c['PG']:3d} {c['CT']:2d} {c['PD']:3d} {c['OB']:4d} {c['DH']:3d} {c['rc_sup']:4d}/{c['rc_all']:<4d} {pct:5.1f} {c['BANK']:5d} {c['NB']:4d}")
print("TOTAL", dict(tot))
print(f"dash-off share of body-turns: {100.0 * tot['doff_rounds'] / max(1, tot['turns']):.1f}%")
