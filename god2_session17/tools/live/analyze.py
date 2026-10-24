#!/usr/bin/env python3
"""Analyse compact match records (experiments/live/compact/*.json).

  python tools/live/analyze.py team NAME [--since ISO] [--kind ranked] [--vs-top N]   # one team's profile: per map, wins vs losses
  python tools/live/analyze.py compare NAME1 NAME2 ...                                 # side-by-side averages of several teams
  python tools/live/analyze.py game MATCHID                                            # one game: timelines and events
"""
import argparse, collections, glob, json, os, statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COMPACT = os.path.join(ROOT, "experiments", "live", "compact")


def load(since="", kind=None):
    out = []
    for f in glob.glob(os.path.join(COMPACT, "*.json")):
        try:
            r = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if (r.get("created") or "") < since:
            continue
        if kind and r.get("kind") != kind:
            continue
        out.append(r)
    return out


def top_ranks():
    p = os.path.join(ROOT, "experiments", "live", "top40.tsv")
    rk = {}
    for l in open(p, encoding="utf-8"):
        a = l.rstrip("\n").split("\t")
        rk[a[2]] = int(a[0])
    return rk


def side(r, name):
    for t in r["teams"]:
        if t["name"] == name:
            return t["team"]
    return None


def at(points, rnd):
    """value of an RLE point list at round rnd"""
    v = 0
    for t, x in points:
        if t > rnd:
            break
        v = x
    return v


def team_stats(r, tk):
    """Per-team numbers of one game. tk = 'teamA' / 'teamB'."""
    o = "teamB" if tk == "teamA" else "teamA"
    ch = [c for c in r["champs"] if c["team"] == tk]
    S = {}
    S["win"] = r["outcome"] == tk
    S["rounds"] = r["rounds"]
    tl = r["team_tl"].get(tk + ":submittedGems", [])
    tlo = r["team_tl"].get(o + ":submittedGems", [])
    S["gems"] = at(tl, 10 ** 9)
    S["opp_gems"] = at(tlo, 10 ** 9)
    for k in (200, 400, 600, 800, 1000):
        S[f"g{k}"] = at(tl, k)
        S[f"og{k}"] = at(tlo, k)
    S["deaths"] = sum(c["m"]["deaths"] for c in ch)
    S["kills"] = sum(c["m"]["kills"] for c in ch)
    S["collected"] = sum(c["m"]["collectedGems"] for c in ch)
    S["gold"] = sum(c["m"]["earnedGold"] for c in ch)
    S["spent"] = sum(c["m"]["spentGold"] for c in ch)
    S["mdmg"] = sum(c["m"]["monsterDamageDone"] for c in ch)
    S["cdmg"] = sum(c["m"]["championDamageDone"] for c in ch)
    S["ctaken"] = sum(c["m"]["championDamageTaken"] for c in ch)
    S["mtaken"] = sum(c["m"]["monsterDamageTaken"] for c in ch)
    S["heal"] = sum(c["m"]["healingDone"] for c in ch)
    S["shield"] = sum(c["m"]["shieldingDone"] for c in ch)
    S["lost_gems"] = sum(int(x[6] or 0) for x in r["losses"] if x[1] == tk)
    S["lost_to_champ"] = sum(int(x[6] or 0) for x in r["losses"] if x[1] == tk and x[4] == "champion")
    clears = [x for x in r["clears"] if x[1] == tk]
    S["clears"] = len(clears)
    S["first_clear"] = clears[0][0] if clears else 2000
    subs = [x for x in r["subs"] if x[1] == tk]
    S["subs"] = len(subs)
    S["first_sub"] = subs[0][0] if subs else 2000
    S["bag"] = (sum(int(x[6] or 0) for x in subs) / len(subs)) if subs else 0
    camp_c = [x for x in r["colls"] if x[1] == tk and x[4] == "campGroup"]
    champ_c = [x for x in r["colls"] if x[1] == tk and x[4] == "champion"]
    S["camp_gems"] = sum(int(x[6] or 0) for x in camp_c)
    S["steal_gems"] = sum(int(x[6] or 0) for x in champ_c)
    S["wards"] = r["wards"].get(tk, 0)
    S["fuel_ex"] = sum(1 for x in r["fuel"] if x[1] == tk)
    S["faults"] = sum(1 for x in r["faults"] if x[1] == tk)
    S["buys"] = sum(1 for x in r["buys"] if x[1] == tk)
    deaths = [x for x in r["deaths"] if x[1] == tk]
    S["d_early"] = sum(1 for x in deaths if x[0] < 300)
    S["deaths_by_camp"] = sum(1 for x in deaths if x[4] != "champion")
    S["draft"] = ",".join(next(t for t in r["teams"] if t["team"] == tk)["draft"])
    S["n"] = len(next(t for t in r["teams"] if t["team"] == tk)["draft"])
    return S


KEYS = ["rounds", "gems", "opp_gems", "g200", "og200", "g400", "og400", "g600", "og600", "collected", "camp_gems", "steal_gems",
        "lost_gems", "lost_to_champ", "deaths", "kills", "d_early", "deaths_by_camp", "clears", "first_clear", "subs", "first_sub",
        "bag", "gold", "spent", "mdmg", "cdmg", "ctaken", "mtaken", "heal", "shield", "wards", "buys", "fuel_ex", "faults"]


def avg(rows, k):
    v = [x[k] for x in rows]
    return st.mean(v) if v else float("nan")


def cmd_team(a):
    rs = load(a.since, a.kind)
    rk = top_ranks()
    rows = []
    for r in rs:
        tk = side(r, a.name)
        if not tk:
            continue
        opp = next(t for t in r["teams"] if t["team"] != tk)
        if a.vs_top and rk.get(opp["name"], 999) > a.vs_top:
            continue
        S = team_stats(r, tk)
        O = team_stats(r, "teamB" if tk == "teamA" else "teamA")
        S["map"] = r["map"]
        S["opp"] = opp["name"]
        rows.append((S, O))
    if not rows:
        print("no games")
        return
    w = sum(1 for S, O in rows if S["win"])
    print(f"{a.name}: {len(rows)} games, {w} wins ({100 * w / len(rows):.1f}%)")
    # per map
    pm = collections.defaultdict(lambda: [0, 0])
    for S, O in rows:
        pm[S["map"]][0 if S["win"] else 1] += 1
    print("\nper map (W-L, worst first):")
    for m, (ww, ll) in sorted(pm.items(), key=lambda x: (x[1][0] / max(1, sum(x[1])), -sum(x[1]))):
        print(f"  {m:24s} {ww:3d}-{ll:<3d} {100 * ww / max(1, ww + ll):5.1f}%")
    # wins vs losses
    W = [x for x in rows if x[0]["win"]]
    L = [x for x in rows if not x[0]["win"]]
    print(f"\n{'metric':16s} {'us(W)':>9s} {'opp(W)':>9s} {'us(L)':>9s} {'opp(L)':>9s}")
    for k in KEYS:
        print(f"{k:16s} {avg([s for s, o in W], k):9.1f} {avg([o for s, o in W], k):9.1f} {avg([s for s, o in L], k):9.1f} {avg([o for s, o in L], k):9.1f}")
    # by team size
    print("\nby team size: W-L")
    bs = collections.defaultdict(lambda: [0, 0])
    for S, O in rows:
        bs[S["n"]][0 if S["win"] else 1] += 1
    for n, (ww, ll) in sorted(bs.items()):
        print(f"  {n}: {ww}-{ll} ({100 * ww / max(1, ww + ll):.0f}%)")
    print("\nby our draft: W-L")
    bd = collections.defaultdict(lambda: [0, 0])
    for S, O in rows:
        bd[S["draft"]][0 if S["win"] else 1] += 1
    for d, (ww, ll) in sorted(bd.items(), key=lambda x: -sum(x[1]))[:12]:
        print(f"  {d:50s} {ww}-{ll} ({100 * ww / max(1, ww + ll):.0f}%)")
    print("\nby opponent: W-L")
    bo = collections.defaultdict(lambda: [0, 0])
    for S, O in rows:
        bo[S["opp"]][0 if S["win"] else 1] += 1
    for d, (ww, ll) in sorted(bo.items(), key=lambda x: rk.get(x[0], 999))[:40]:
        print(f"  #{rk.get(d, '-')!s:4s} {d:32s} {ww}-{ll}")


def cmd_compare(a):
    rs = load(a.since, a.kind)
    rk = top_ranks()
    prof = {}
    for name in a.names:
        rows = []
        for r in rs:
            tk = side(r, name)
            if not tk:
                continue
            opp = next(t for t in r["teams"] if t["team"] != tk)
            if a.vs_top and rk.get(opp["name"], 999) > a.vs_top:
                continue
            rows.append(team_stats(r, tk))
        prof[name] = rows
    print(f"{'metric':16s}" + "".join(f"{n[:12]:>13s}" for n in a.names))
    print(f"{'games':16s}" + "".join(f"{len(prof[n]):13d}" for n in a.names))
    print(f"{'win%':16s}" + "".join(f"{100 * avg(prof[n], 'win'):13.1f}" for n in a.names))
    for k in KEYS:
        print(f"{k:16s}" + "".join(f"{avg(prof[n], k):13.1f}" for n in a.names))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd")
    t = sp.add_parser("team")
    t.add_argument("name")
    c = sp.add_parser("compare")
    c.add_argument("names", nargs="+")
    for p in (t, c):
        p.add_argument("--since", default="")
        p.add_argument("--kind", default=None)
        p.add_argument("--vs-top", type=int, default=0)
    a = ap.parse_args()
    if a.cmd == "team":
        cmd_team(a)
    elif a.cmd == "compare":
        cmd_compare(a)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
