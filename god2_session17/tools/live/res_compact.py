#!/usr/bin/env python3
"""Resources (gold, items, shopping, banking) from compact match records: ours vs the top-10 teams.

  python tools/live/res_compact.py [--out C:/battlecode/cache/an_resources/rc.json]

Groups: OURS = HouseOfCoders vs a top-10 team (engine 1.0.3; NEW = the bb4/ft52 lists of Oct 22 20:50+, OLD = v11..ab3 of Oct 22),
OPP = the top team in those games, TOP = both sides of top-10 vs top-10 games (engine 1.0.3), TOPW / TOPL = their winners / losers.
"""
import collections, glob, json, math, os, statistics as st, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIVE = os.path.join(ROOT, "experiments", "live")
TOP10 = {"Intercontinental Fish", "prism best girl", "procless", "Univardisty of Shingtonwash", "new team(4)", "Pantheon", "policy wonk",
         ":3", "EMPEROR Tung", "Trzy Kwaterki"}
US = "HouseOfCoders"
CPS = [100, 150, 200, 300, 400, 600, 800]


def at(pts, rnd):
    v = 0
    for t, x in pts:
        if t > rnd:
            break
        v = x
    return v


def integ(pts, a, b):
    """mean of an RLE series over rounds [a, b)"""
    if b <= a:
        return None
    tot = 0.0
    for i, (t, x) in enumerate(pts):
        t2 = pts[i + 1][0] if i + 1 < len(pts) else 10 ** 9
        lo, hi = max(a, t), min(b, t2)
        if hi > lo:
            tot += x * (hi - lo)
    return tot / (b - a)


def item_of(row):
    t = row[5]
    return t[2] if isinstance(t, list) else str(t)


def fam_stat(name):
    p = name.split()
    return p[0], p[-1]


def load_groups():
    new_ids = set()
    for l in open(os.path.join(LIVE, "lists", "top10_oct23", "ours_bb4_ft52.jsonl"), encoding="utf-8"):
        if l.strip():
            new_ids.add(json.loads(l)["matchId"])
    tvt_new = set()
    for l in open(os.path.join(LIVE, "lists", "top10_oct23", "top_vs_top.jsonl"), encoding="utf-8"):
        if l.strip():
            tvt_new.add(json.loads(l)["matchId"])
    games = []
    for f in glob.glob(os.path.join(LIVE, "compact", "*.json")):
        try:
            r = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if r.get("engine") != "1.0.3":
            continue
        names = {t["team"]: t["name"] for t in r["teams"]}
        if US in names.values():
            tk = next(k for k, v in names.items() if v == US)
            ok = next(k for k in names if k != tk)
            if names[ok] not in TOP10 or (r.get("created") or "") < "2026-10-22T13":
                continue
            tag = "NEW" if r["id"] in new_ids else "OLD"
            games.append((r, [(tk, "OURS", tag), (ok, "OPP", tag)]))
        elif all(n in TOP10 for n in names.values()):
            tag = "NEW" if r["id"] in tvt_new else "OLD"
            games.append((r, [(k, "TOP", tag) for k in names]))
    return games


def champ_rows(r, tk):
    """per champion of side tk: gold, items, banking, shopping"""
    o = "teamB" if tk == "teamA" else "teamA"
    rows = []
    end = r["rounds"]
    deaths_by = collections.defaultdict(list)
    for x in r["deaths"]:
        deaths_by[x[3]].append(x[0])
    kills_by = collections.defaultdict(list)
    for x in r["kills"]:
        kills_by[x[3]].append(x[0])
    for c in r["champs"]:
        if c["team"] != tk:
            continue
        cid = c["id"]
        eg = r["champ_tl"].get(f"{cid}:earnedGold", [])
        gh = r["champ_tl"].get(f"{cid}:gold", [])
        R = {"name": c["name"], "id": cid, "end": end}
        # gold earned and its sources
        kill_g = collections.Counter()
        marc_g = collections.Counter()
        kr = set(kills_by.get(cid, []))
        for i in range(1, len(eg)):
            t, v = eg[i]
            dv = v - eg[i - 1][1]
            if dv <= 0:
                continue
            if t in kr:
                kill_g[t] += min(dv, 160)
        if c["name"] == "Marcella":
            for s in r["subs"]:
                if s[3] == cid:
                    marc_g[s[0]] += 2 * int(s[6] or 0)
        for cp in CPS + [10 ** 9]:
            key = "end" if cp == 10 ** 9 else cp
            e = at(eg, cp)
            k = sum(v for t, v in kill_g.items() if t <= cp)
            m = sum(v for t, v in marc_g.items() if t <= cp)
            R[f"earn{key}"] = e
            R[f"kill{key}"] = k
            R[f"marc{key}"] = m
            R[f"held{key}"] = at(gh, cp) if cp <= end else None
        R["heldMean0_300"] = integ(gh, 0, min(300, end))
        R["heldMean300_600"] = integ(gh, 300, min(600, end)) if end > 350 else None
        R["heldMean600"] = integ(gh, 600, end) if end > 650 else None
        # spending
        buys = [x for x in r["buys"] if x[3] == cid and x[1] == tk]
        cons = [x for x in r["cons"] if x[3] == cid and x[1] == tk]
        R["shards150"] = sum(int(x[6] or 1) for x in buys if x[0] <= 150)
        R["shards300"] = sum(int(x[6] or 1) for x in buys if x[0] <= 300)
        R["shards600"] = sum(int(x[6] or 1) for x in buys if x[0] <= 600)
        R["shardsEnd"] = sum(int(x[6] or 1) for x in buys)
        fs = collections.Counter()
        for x in buys:
            f, s = fam_stat(item_of(x))
            fs[(f, s)] += int(x[6] or 1)
        R["famstat"] = {f"{a}|{b}": v for (a, b), v in fs.items()}
        R["cons"] = collections.Counter(item_of(x) for x in cons)
        # shopping visits: distinct rounds with a buy (shards or consumables)
        visits = sorted(set(x[0] for x in buys) | set(x[0] for x in cons))
        R["visits"] = len(visits)
        R["visits300"] = sum(1 for v in visits if v <= 300)
        dead_iv = [(d, d + 61) for d in deaths_by.get(cid, [])]
        dead_v = [v for v in visits if any(a <= v <= b for a, b in dead_iv)]
        R["visits_dead"] = len(dead_v)
        # gold before each shard purchase visit (context = gold before)
        gb = {}
        for x in sorted(buys + cons, key=lambda y: y[0]):
            if x[0] not in gb:
                try:
                    gb[x[0]] = float(x[4])
                except Exception:
                    pass
        R["gold_before_visit"] = list(gb.values())
        # emblems (combos)
        R["emblems"] = [(x[0], item_of(x)) for x in r["combos"] if x[3] == cid and x[1] == tk]
        R["final_items"] = c["items"]
        # banking
        subs = [x for x in r["subs"] if x[3] == cid and x[1] == tk]
        R["subs"] = [(x[0], int(x[6] or 0)) for x in subs]
        R["lost"] = [(x[0], int(x[6] or 0), x[4]) for x in r["losses"] if x[3] == cid and x[1] == tk]
        R["deaths"] = len(deaths_by.get(cid, []))
        R["kills"] = len(kills_by.get(cid, []))
        R["collected"] = c["m"].get("collectedGems", 0)
        R["spent"] = c["m"].get("spentGold", 0)
        R["earned"] = c["m"].get("earnedGold", 0)
        rows.append(R)
    return rows


def main():
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "C:/battlecode/cache/an_resources/rc.json"
    games = load_groups()
    recs = []
    for r, sides in games:
        for tk, grp, tag in sides:
            name = next(t["name"] for t in r["teams"] if t["team"] == tk)
            win = r["outcome"] == tk
            recs.append({"id": r["id"], "map": r["map"], "created": r["created"], "rounds": r["rounds"], "team": name, "side": tk, "grp": grp,
                         "tag": tag, "win": win, "n": sum(1 for c in r["champs"] if c["team"] == tk),
                         "gems": at(r["team_tl"].get(tk + ":submittedGems", []), 10 ** 9),
                         "champs": champ_rows(r, tk)})
    json.dump(recs, open(out, "w", encoding="utf-8"), default=lambda o: dict(o) if isinstance(o, collections.Counter) else str(o))
    c = collections.Counter((x["grp"], x["tag"]) for x in recs)
    print("records", len(recs), dict(c))


if __name__ == "__main__":
    main()
