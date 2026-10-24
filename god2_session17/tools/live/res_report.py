#!/usr/bin/env python3
"""Tables from res_compact.py's output (rc.json): gold, items, shopping, banking per group and per champion type.
  python tools/live/res_report.py [rc.json] [--tag NEW|OLD|ALL]"""
import collections, json, statistics as st, sys

path = next((a for a in sys.argv[1:] if a.endswith(".json")), "C:/battlecode/cache/an_resources/rc.json")
tag = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else "ALL"
recs = json.load(open(path, encoding="utf-8"))


def grp_of(x):
    g = x["grp"]
    if g == "TOP":
        return ["TOP", "TOPW" if x["win"] else "TOPL"]
    return [g]


def mean(v):
    v = [a for a in v if a is not None]
    return st.mean(v) if v else float("nan")


def med(v):
    v = [a for a in v if a is not None]
    return st.median(v) if v else float("nan")


G = collections.defaultdict(list)
for x in recs:
    if tag != "ALL" and x["tag"] != tag:
        continue
    for g in grp_of(x):
        G[g].append(x)
ORDER = ["OURS", "OPP", "TOP", "TOPW", "TOPL"]
ORDER = [g for g in ORDER if G[g]]
print(f"tag={tag}  games: " + ", ".join(f"{g} {len(G[g])} (win {100 * mean([x['win'] for x in G[g]]):.0f}%)" for g in ORDER))


def team_metric(xs, f):
    return mean([f(x) for x in xs])


def tsum(x, k):
    v = [c.get(k) for c in x["champs"]]
    if any(a is None for a in v):
        return None
    return sum(v)


def per_champ(xs, f):
    return mean([f(c, x) for x in xs for c in x["champs"]])


rows = []
print("\n== Team gold (team sums; per-champion means in brackets)")
print(f"{'metric':28s}" + "".join(f"{g:>12s}" for g in ORDER))
for cp in [100, 200, 300, 600]:
    print(f"{'earned r' + str(cp):28s}" + "".join(f"{team_metric([x for x in G[g] if x['rounds'] >= cp], lambda x: tsum(x, f'earn{cp}')):12.0f}" for g in ORDER))
for cp in [100, 200, 300, 600]:
    print(f"{'  of which kills r' + str(cp):28s}" + "".join(f"{team_metric([x for x in G[g] if x['rounds'] >= cp], lambda x: tsum(x, f'kill{cp}')):12.0f}" for g in ORDER))
for cp in [300, 600]:
    print(f"{'  of which Marcella bank r' + str(cp):28s}" + "".join(f"{team_metric([x for x in G[g] if x['rounds'] >= cp], lambda x: tsum(x, f'marc{cp}')):12.0f}" for g in ORDER))
for cp in [100, 200, 300, 600, 800]:
    print(f"{'held (unspent) r' + str(cp):28s}" + "".join(f"{team_metric([x for x in G[g] if x['rounds'] >= cp], lambda x: tsum(x, f'held{cp}')):12.0f}" for g in ORDER))
for k in ["heldMean0_300", "heldMean300_600", "heldMean600"]:
    print(f"{'per champ ' + k:28s}" + "".join(f"{per_champ(G[g], lambda c, x: c.get(k)):12.0f}" for g in ORDER))
print(f"{'earned/round (whole game)':28s}" + "".join(f"{team_metric(G[g], lambda x: tsum(x, 'earned') / max(1, x['rounds'])):12.2f}" for g in ORDER))
print(f"{'spent/earned (end)':28s}" + "".join(f"{team_metric(G[g], lambda x: tsum(x, 'spent') / max(1, tsum(x, 'earned'))):12.2f}" for g in ORDER))
print(f"{'rounds':28s}" + "".join(f"{team_metric(G[g], lambda x: x['rounds']):12.0f}" for g in ORDER))
print(f"{'bodies':28s}" + "".join(f"{team_metric(G[g], lambda x: x['n']):12.1f}" for g in ORDER))

print("\n== Items per champion (all types)")
for k in ["shards150", "shards300", "shards600"]:
    print(f"{k:28s}" + "".join(f"{per_champ([x for x in G[g] if x['rounds'] >= int(k[6:])], lambda c, x: c[k]):12.1f}" for g in ORDER))


def share(xs, fn):
    tot = collections.Counter()
    for x in xs:
        for c in x["champs"]:
            for k, v in c["famstat"].items():
                tot[fn(k)] += v
    s = sum(tot.values()) or 1
    return {k: 100 * v / s for k, v in tot.items()}


fam = {g: share(G[g], lambda k: k.split("|")[0]) for g in ORDER}
stat = {g: share(G[g], lambda k: k.split("|")[1]) for g in ORDER}
for f in ["Treasure", "Jungle", "Bruiser", "Durability", "Power", "Monster", "Home"]:
    print(f"{'% shards ' + f:28s}" + "".join(f"{fam[g].get(f, 0):12.1f}" for g in ORDER))
for s_ in ["Health", "Strength", "Focus"]:
    print(f"{'% shards ' + s_:28s}" + "".join(f"{stat[g].get(s_, 0):12.1f}" for g in ORDER))

print("\n== Shopping per champion")
print(f"{'visits / game':28s}" + "".join(f"{per_champ(G[g], lambda c, x: c['visits']):12.1f}" for g in ORDER))
print(f"{'visits / 100 rounds':28s}" + "".join(f"{per_champ(G[g], lambda c, x: 100 * c['visits'] / max(1, x['rounds'])):12.2f}" for g in ORDER))
print(f"{'visits by r300':28s}" + "".join(f"{per_champ([x for x in G[g] if x['rounds'] >= 300], lambda c, x: c['visits300']):12.2f}" for g in ORDER))
print(f"{'% visits while dead':28s}" + "".join(f"{100 * sum(c['visits_dead'] for x in G[g] for c in x['champs']) / max(1, sum(c['visits'] for x in G[g] for c in x['champs'])):12.1f}" for g in ORDER))
print(f"{'median gold before visit':28s}" + "".join(f"{med([v for x in G[g] for c in x['champs'] for v in c['gold_before_visit']]):12.0f}" for g in ORDER))
print(f"{'mean gold before visit':28s}" + "".join(f"{mean([v for x in G[g] for c in x['champs'] for v in c['gold_before_visit']]):12.0f}" for g in ORDER))
for cn in ["Altar Lock", "Teleport Crystal"]:
    print(f"{'buys of ' + cn + ' /champ':28s}" + "".join(f"{per_champ(G[g], lambda c, x: c['cons'].get(cn, 0)):12.2f}" for g in ORDER))

print("\n== Banking per team-game")
print(f"{'tributes / game (team)':28s}" + "".join(f"{team_metric(G[g], lambda x: sum(len(c['subs']) for c in x['champs'])):12.1f}" for g in ORDER))
print(f"{'tributes / 100 rounds':28s}" + "".join(f"{team_metric(G[g], lambda x: 100 * sum(len(c['subs']) for c in x['champs']) / max(1, x['rounds'])):12.2f}" for g in ORDER))
print(f"{'mean bag':28s}" + "".join(f"{mean([s[1] for x in G[g] for c in x['champs'] for s in c['subs']]):12.1f}" for g in ORDER))
print(f"{'median bag':28s}" + "".join(f"{med([s[1] for x in G[g] for c in x['champs'] for s in c['subs']]):12.1f}" for g in ORDER))
print(f"{'first tribute round':28s}" + "".join(f"{team_metric(G[g], lambda x: min([s[0] for c in x['champs'] for s in c['subs']] or [2000])):12.0f}" for g in ORDER))
print(f"{'tributes by r300':28s}" + "".join(f"{team_metric([x for x in G[g] if x['rounds'] >= 300], lambda x: sum(1 for c in x['champs'] for s in c['subs'] if s[0] <= 300)):12.1f}" for g in ORDER))
print(f"{'banked gems (final)':28s}" + "".join(f"{team_metric(G[g], lambda x: x['gems']):12.0f}" for g in ORDER))
print(f"{'gems lost on death / game':28s}" + "".join(f"{team_metric(G[g], lambda x: sum(l[1] for c in x['champs'] for l in c['lost'])):12.0f}" for g in ORDER))
print(f"{'  to champions':28s}" + "".join(f"{team_metric(G[g], lambda x: sum(l[1] for c in x['champs'] for l in c['lost'] if l[2] == 'champion')):12.0f}" for g in ORDER))
print(f"{'deaths / game':28s}" + "".join(f"{team_metric(G[g], lambda x: sum(c['deaths'] for c in x['champs'])):12.1f}" for g in ORDER))
print(f"{'lost/collected %':28s}" + "".join(f"{100 * sum(l[1] for x in G[g] for c in x['champs'] for l in c['lost']) / max(1, sum(c['collected'] for x in G[g] for c in x['champs'])):12.1f}" for g in ORDER))
print(f"{'deaths w/ bag>=20 / game':28s}" + "".join(f"{team_metric(G[g], lambda x: sum(1 for c in x['champs'] for l in c['lost'] if l[1] >= 20)):12.2f}" for g in ORDER))

# per champion type
print("\n== Per champion type")
TYPES = ["Vesper Vale", "Vendetta", "Heart of Ruin", "Ryth", "Marcella", "Prism", "Stellar", "Cassi", "Issac", "Ren", "Varg", "Tavi", "Willow"]


def short(n):
    f, _, s = n.partition(" Emblem of ")
    return f[:4] + "-" + s[:3]


for t in TYPES:
    print(f"\n-- {t}")
    for g in ORDER:
        cs = [(c, x) for x in G[g] for c in x["champs"] if c["name"] == t]
        if len(cs) < 5:
            continue
        seq = collections.Counter(" > ".join(short(e[1]) for e in c["emblems"][:3]) for c, x in cs)
        first = [c["emblems"][0][0] for c, x in cs if c["emblems"]]
        third = [c["emblems"][2][0] for c, x in cs if len(c["emblems"]) >= 3]
        fs = collections.Counter()
        for c, x in cs:
            for k, v in c["famstat"].items():
                fs[k] += v
        tot = sum(fs.values()) or 1
        hp = 100 * sum(v for k, v in fs.items() if k.endswith("Health")) / tot
        e300 = mean([c["earn300"] for c, x in cs if x["rounds"] >= 300])
        e600 = mean([c["earn600"] for c, x in cs if x["rounds"] >= 600])
        h300 = mean([c["held300"] for c, x in cs if x["rounds"] >= 300])
        bags = [s[1] for c, x in cs for s in c["subs"]]
        print(f"  {g:5s} n={len(cs):3d} earn300 {e300:5.0f} earn600 {e600:5.0f} held300 {h300:4.0f} heldMean0-300 {mean([c['heldMean0_300'] for c, x in cs]):4.0f} "
              f"sh150 {mean([c['shards150'] for c, x in cs]):4.1f} sh300 {mean([c['shards300'] for c, x in cs if x['rounds'] >= 300]):4.1f} "
              f"1stEmb r{med(first):.0f} 3rdEmb r{med(third):.0f} hp% {hp:3.0f} visits {mean([c['visits'] for c, x in cs]):4.1f} "
              f"subs {mean([len(c['subs']) for c, x in cs]):4.1f} bag {mean(bags):4.1f} deaths {mean([c['deaths'] for c, x in cs]):4.1f}")
        print("        emblems: " + " | ".join(f"{s or '-'} {100 * v / len(cs):.0f}%" for s, v in seq.most_common(4)))
        print("        shards: " + ", ".join(f"{k.replace('|', '-')} {100 * v / tot:.0f}%" for k, v in fs.most_common(6)))
