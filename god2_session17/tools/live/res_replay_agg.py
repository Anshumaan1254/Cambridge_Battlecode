#!/usr/bin/env python3
"""Aggregate tools/live/res_replay.mjs output: recalls, shopping visits, tributes, max HP / stat points over time; ours vs top teams.
  python tools/live/res_replay_agg.py OURS_FILE[,OURS_FILE2] TOP_FILE  (jsonl from res_replay.mjs)"""
import collections, glob, json, os, statistics as st, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIVE = os.path.join(ROOT, "experiments", "live")
US = "HouseOfCoders"
DRAFT = ['Ryth', 'VesperVale', 'Vendetta', 'CassiAndIssac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin']


def meta_index():
    idx = {}
    for f in glob.glob(os.path.join(LIVE, "lists", "**", "*.jsonl"), recursive=True):
        for l in open(f, encoding="utf-8"):
            if not l.strip():
                continue
            try:
                m = json.loads(l)
            except Exception:
                continue
            if "matchId" in m and "teams" in m:
                idx[m["matchId"][:8]] = m
    return idx


def mean(v):
    v = [a for a in v if a is not None]
    return st.mean(v) if v else float("nan")


def med(v):
    v = [a for a in v if a is not None]
    return st.median(v) if v else float("nan")


def load(files, idx, kind):
    out = []  # (grp, win, game, body)
    for f in files:
        for l in open(f, encoding="utf-8"):
            try:
                g = json.loads(l)
            except Exception:
                continue
            m = idx.get(g["file"].split("_")[-1].split(".")[0])
            if not m:
                continue
            # team 0 = side a (check drafts)
            sides = {t["side"]: t for t in m["teams"]}
            ta, tb = sides.get("a"), sides.get("b")
            if not ta or not tb:
                continue
            da = sorted(DRAFT[int(c)] for c in ta["characters"])
            if da != sorted(g["drafts"][0]) and sorted(DRAFT[int(c)] for c in tb["characters"]) == sorted(g["drafts"][0]):
                ta, tb = tb, ta
            team = {0: ta, 1: tb}
            for b in g["bodies"]:
                t = team[b["team"]]
                win = t["result"] == "win"
                if kind == "ours":
                    grp = "OURS" if t["name"] == US else "OPP"
                else:
                    grp = "TOP"
                out.append((grp, win, g, b))
                if grp == "TOP":
                    out.append(("TOPW" if win else "TOPL", win, g, b))
    return out


def report(rows, types=None):
    G = collections.defaultdict(list)
    for grp, win, g, b in rows:
        if types and b["type"] not in types:
            continue
        G[grp].append((g, b))
    order = [x for x in ["OURS", "OPP", "TOP", "TOPW", "TOPL"] if G[x]]
    hdr = f"{'metric':34s}" + "".join(f"{x:>10s}" for x in order)
    print(hdr)
    print(f"{'bodies (games)':34s}" + "".join(f"{len(G[x]):>6d}({len(set(id(g) for g, b in G[x])):3d})" for x in order))

    def line(name, f, fmt="10.2f"):
        print(f"{name:34s}" + "".join(format(f(G[x]), fmt) for x in order))

    per100 = lambda xs, k: mean([100 * len(b[k]) / max(1, g["final"]) for g, b in xs])
    # recalls
    line("recalls / body / 100 rounds", lambda xs: per100(xs, "recalls"))
    line("recalls / body / game", lambda xs: mean([len(b["recalls"]) for g, b in xs]))
    for res in ["ok", "cancel", "interrupted", "death", "onspawn"]:
        line(f"  recall result {res} %", lambda xs, res=res: 100 * mean([1 if rc["res"] == res else 0 for g, b in xs for rc in b["recalls"]]), "10.1f")
    R = lambda xs: [rc for g, b in xs for rc in b["recalls"]]
    line("  capture-recall %", lambda xs: 100 * mean([1 if rc["cap"] else 0 for rc in R(xs)]), "10.1f")
    line("  hurt (<50% hp) at start %", lambda xs: 100 * mean([1 if rc["hpf"] < 0.5 else 0 for rc in R(xs)]), "10.1f")
    line("  median hp frac at start", lambda xs: med([rc["hpf"] for rc in R(xs)]))
    line("  median dist home at start", lambda xs: med([rc["dh"] for rc in R(xs)]), "10.1f")
    line("  bag >=20 at start %", lambda xs: 100 * mean([1 if rc["gems"] >= 20 else 0 for rc in R(xs)]), "10.1f")
    line("  gold >=90 at start %", lambda xs: 100 * mean([1 if rc["gold"] >= 90 else 0 for rc in R(xs)]), "10.1f")
    line("  ok: shopped on arrival %", lambda xs: 100 * mean([1 if rc.get("shop") else 0 for rc in R(xs) if rc["res"] == "ok"]), "10.1f")
    line("  ok: tribute within 30 r %", lambda xs: 100 * mean([rc.get("bankAfter", 0) for rc in R(xs) if rc["res"] == "ok"]), "10.1f")
    line("  ok: gold on arrival (mean)", lambda xs: mean([rc.get("goldArr") for rc in R(xs) if rc["res"] == "ok"]), "10.0f")
    line("  ok: bag on arrival (mean)", lambda xs: mean([rc.get("gemsArr") for rc in R(xs) if rc["res"] == "ok"]), "10.1f")
    # purposes (exclusive classes, in order)
    def purpose(rc):
        if rc["cap"]:
            return "capture"
        if rc["hpf"] < 0.5:
            return "hurt"
        if rc["gems"] >= 20:
            return "bag"
        if rc["gold"] >= 90:
            return "shop"
        return "other"
    for p in ["capture", "hurt", "bag", "shop", "other"]:
        line(f"  purpose {p} %", lambda xs, p=p: 100 * mean([1 if purpose(rc) == p else 0 for rc in R(xs)]), "10.1f")
    # shopping
    S = lambda xs: [s for g, b in xs for s in b["shops"]]
    line("shop visits / body / game", lambda xs: mean([len(b["shops"]) for g, b in xs]))
    line("shop visits / body / 100 rounds", lambda xs: per100(xs, "shops"))
    for how in ["recall", "dead", "respawn", "walk", "start", "remote"]:
        line(f"  visit via {how} %", lambda xs, how=how: 100 * mean([1 if s["how"] == how else 0 for s in S(xs)]), "10.1f")
    line("  median gold before visit", lambda xs: med([s["goldBefore"] for s in S(xs)]), "10.0f")
    line("  mean shards bought / visit", lambda xs: mean([s["dse"] for s in S(xs)]), "10.2f")
    line("  gold left after visit (mean)", lambda xs: mean([s["goldAfter"] for s in S(xs)]), "10.1f")
    # tributes
    T = lambda xs: [t for g, b in xs for t in b["tributes"] if t.get("res") != "ok-unmatched"]
    line("tribute starts / body / game", lambda xs: mean([len([t for t in b["tributes"] if t.get("res") != "ok-unmatched"]) for g, b in xs]))
    for res in ["ok", "cancel", "death", "restart", "open"]:
        line(f"  result {res} %", lambda xs, res=res: 100 * mean([1 if t["res"] == res else 0 for t in T(xs)]), "10.1f")
    ok = lambda xs: [t for t in T(xs) if t["res"] == "ok"]
    line("  ok: mean bag", lambda xs: mean([t.get("gems") for t in ok(xs)]), "10.1f")
    line("  ok: mean channel rounds", lambda xs: mean([t.get("dur") for t in ok(xs)]), "10.2f")
    line("  channel rounds / body / game", lambda xs: mean([sum(t.get("dur", 0) or 0 for t in b["tributes"] if t.get("res") == "ok") for g, b in xs]), "10.1f")
    line("  median altar dist to spawn", lambda xs: med([t["altarHome"] for t in T(xs) if t.get("altarHome") is not None]), "10.1f")
    line("  altar <=6 from spawn %", lambda xs: 100 * mean([1 if t["altarHome"] <= 6 else 0 for t in T(xs) if t.get("altarHome") is not None]), "10.1f")
    line("  median dist last capture->altar", lambda xs: med([t["capD"] for t in T(xs) if t.get("capD") is not None]), "10.1f")
    line("  median rounds since capture", lambda xs: med([t["sinceCap"] for t in T(xs) if t.get("sinceCap") is not None]), "10.1f")
    line("  mean rounds since capture", lambda xs: mean([min(t["sinceCap"], 300) for t in T(xs) if t.get("sinceCap") is not None]), "10.1f")
    line("  hp frac at start (median)", lambda xs: med([t["hpf"] for t in T(xs) if t.get("hpf") is not None]))
    # deaths
    D = lambda xs: [d for g, b in xs for d in b["deaths"]]
    line("deaths / body / game", lambda xs: mean([len(b["deaths"]) for g, b in xs]))
    line("  gems lost / body / game", lambda xs: mean([sum(d["bag"] for d in b["deaths"]) for g, b in xs]), "10.1f")
    line("  deaths with bag>=20 %", lambda xs: 100 * mean([1 if d["bag"] >= 20 else 0 for d in D(xs)]), "10.1f")
    line("  gold held at death (mean)", lambda xs: mean([d.get("gold") for d in D(xs)]), "10.1f")
    # power over time
    for cp in ["100", "200", "300", "400", "600", "800"]:
        line(f"maxHp r{cp} (per body)", lambda xs, cp=cp: mean([b["cp"][cp]["maxHp"] for g, b in xs if cp in b["cp"]]), "10.0f")
    for cp in ["150", "300", "600"]:
        line(f"stat points r{cp} str/foc/hp", lambda xs, cp=cp: 0, "10.0f") if False else None
        print(f"{'stat pts r' + cp + ' str/foc/hp':34s}" + "".join(
            f"{'/'.join(str(round(mean([b['cp'][cp]['pts'][k] for g, b in G[x] if cp in b['cp']]))) for k in range(3)):>10s}" for x in order))
    for cp in ["100", "200", "300", "600"]:
        line(f"gold held r{cp} (per body)", lambda xs, cp=cp: mean([b["cp"][cp]["gold"] for g, b in xs if cp in b["cp"]]), "10.0f")
        line(f"gold earned r{cp} (per body)", lambda xs, cp=cp: mean([b["cp"][cp]["earned"] for g, b in xs if cp in b["cp"]]), "10.0f")
    line("mean gold held 0-300", lambda xs: mean([b["goldMean"][0] for g, b in xs]), "10.0f")
    line("mean gold held 300-600", lambda xs: mean([b["goldMean"][1] for g, b in xs]), "10.0f")
    line("mean gold held 600+", lambda xs: mean([b["goldMean"][2] for g, b in xs]), "10.0f")
    line("emblems by r300", lambda xs: mean([sum(1 for e in b["emblems"] if e[0] <= 300) for g, b in xs]), "10.2f")
    line("first emblem round (median)", lambda xs: med([b["emblems"][0][0] if b["emblems"] else 2000 for g, b in xs]), "10.0f")


def main():
    idx = meta_index()
    ours = sys.argv[1].split(",") if len(sys.argv) > 1 else ["C:/battlecode/cache/an_resources/rr_bb4D.jsonl", "C:/battlecode/cache/an_resources/rr_ft52D.jsonl"]
    top = sys.argv[2].split(",") if len(sys.argv) > 2 else ["C:/battlecode/cache/an_resources/rr_top.jsonl"]
    ours = [f for f in ours if os.path.exists(f)]
    top = [f for f in top if os.path.exists(f)]
    rows = load(ours, idx, "ours") + load(top, idx, "top")
    print("== ALL BODIES")
    report(rows)
    for t in (sys.argv[3].split(",") if len(sys.argv) > 3 else ["VesperVale", "Vendetta", "HeartOfRuin", "Ryth", "Marcella", "Prism", "Tavi", "Varg"]):
        print(f"\n== {t}")
        report(rows, {t})


if __name__ == "__main__":
    main()
