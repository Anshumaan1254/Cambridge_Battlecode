import glob, os, re, collections
tot = collections.Counter()
for d in sorted(glob.glob("C:/battlecode/cache/g8h_rv/runs/trA/*_A")):
    txt = open(d + "/team-a.stdout", encoding="utf-8", errors="replace").read()
    # per observer body (me), per enemy: sightings by round
    seen = collections.defaultdict(dict)
    for m in re.finditer(r"\bRC r=(\d+) me=(\d+) enemy=(\d+) at=(\d+),(\d+) streak=(\d+) counted=(\d) gems=(\d+)", txt):
        r, me, en, x, y, st, cnt, gems = map(int, m.groups())
        seen[(me, en)][r] = (x, y, st, cnt, gems)
    c = collections.Counter()
    for k, rr in seen.items():
        for r, (x, y, st, cnt, gems) in rr.items():
            if st == 1:
                nxt = rr.get(r + 1)
                if nxt and nxt[2] == 2:
                    c["first sighting suppressed, genuine (seen again next round, same tile)"] += 1
                    if gems >= 20: c["  ... of which carrying >= 20 gems"] += 1
                elif nxt:
                    c["first sighting suppressed, moved next round (cancelled)"] += 1
                else:
                    c["first sighting suppressed, not seen next round by this body"] += 1
            else:
                c["counted (streak >= 2)"] += 1
    tot.update(c)
for k, v in tot.most_common():
    print(f"{v:6d} {k}")
