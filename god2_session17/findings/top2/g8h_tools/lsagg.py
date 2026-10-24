"""Aggregate longstand.mjs JSON lines per bot: python lsagg.py FILE.jsonl NAME_A NAME_B [games]
team 0 = teamA = the bot named first on the localbench line in <map>_A replays (second bot in <map>_B)."""
import collections, json, sys

f, na, nb = sys.argv[1], sys.argv[2], sys.argv[3]
games = int(sys.argv[4]) if len(sys.argv) > 4 else 80
rows = [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
agg = {n: dict(n=0, rounds=0, camp=0, worst=[], types=collections.Counter(), maps=collections.Counter(), ge100=0) for n in (na, nb)}
for r in rows:
    side = r["file"].rsplit("_", 1)[1][0]
    bot = (na if r["team"] == 0 else nb) if side == "A" else (nb if r["team"] == 0 else na)
    a = agg[bot]
    a["n"] += 1
    a["rounds"] += r["rounds"]
    a["camp"] += bool(r["campTile"])
    a["ge100"] += r["rounds"] >= 100
    a["types"][r["type"]] += 1
    a["maps"][r["file"].rsplit("_", 1)[0]] += 1
    a["worst"].append((r["rounds"], r["file"], r["type"], r["from"], tuple(r["at"]), r["hp"], r["gems"], r["campTile"]))
for n in (na, nb):
    a = agg[n]
    print(f"== {n}: stands >= 40 rounds: {a['n']} ({a['n'] / games:.2f}/game), body-rounds {a['rounds']}, >= 100 rounds: {a['ge100']}, on a camp tile: {a['camp']}")
    print("   types:", dict(a["types"].most_common()))
    print("   maps:", ", ".join(f"{m} {c}" for m, c in a["maps"].most_common(8)))
    for w in sorted(a["worst"], reverse=True)[:6]:
        print("   ", w)
