#!/usr/bin/env python3
"""In-bot ladder A/B (bots/god/src/strat.cpp): recover which variant each platform game played, and tabulate results.
The bot plays variant strat_hash(W, H, total camps, side (a=0, b=1), enemy draft bitmask) % N.
  python tools/live/variant_of.py N --since ISO [--lists experiments/live/lists/us_ranked.jsonl,...] [--kind ranked|unranked|all]
Map signatures come from experiments/live/map_sig.jsonl (tools/live/map_sig.mjs on one replay per pool map)."""
import argparse, glob, json, math, os, sys, collections

M32 = 0xFFFFFFFF


def strat_hash(w, h, camps, side, emask):
    x = 2166136261
    for v in (w, h, camps, side, emask):
        x ^= v & M32
        x = (x * 16777619) & M32
    x ^= x >> 15
    x = (x * 0x2C1B3C6D) & M32
    x ^= x >> 12
    x = (x * 0x297A2D39) & M32
    x ^= x >> 15
    return x


def load_sigs():
    sigs = {}
    for l in open("experiments/live/map_sig.jsonl", encoding="utf-8"):
        d = json.loads(l)
        name = d["file"].split(".")[0].split("_")[0] if False else d["file"][: -len(".repl26a")]
        sigs[name.replace("-", "_")] = (d["W"], d["H"], d["camps"])
    return sigs


def variant(sigs, m, n, us="HouseOfCoders", nomask=False):
    mp = m["map"].replace("-", "_")
    if mp not in sigs:
        return None
    w, h, camps = sigs[mp]
    me = next(t for t in m["teams"] if t["name"] == us)
    op = next(t for t in m["teams"] if t["name"] != us)
    side = 0 if me["side"] == "a" else 1
    emask = 0
    for d in op.get("draftPicks") or []:
        emask |= 1 << int(d)
    if nomask:
        emask = 0  # P.ab_nomask: the variant hashes the map and side only
    return strat_hash(w, h, camps, side, emask) % n


def wilson(w, n, z=1.96):
    if n == 0:
        return (0, 0, 0)
    p = w / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    hw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, c - hw, c + hw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("--since", default="")
    ap.add_argument("--until", default="9999")
    ap.add_argument("--lists", default="experiments/live/lists/us_ranked.jsonl,experiments/live/lists/groups_matches.jsonl")
    ap.add_argument("--bits", action="store_true", help="also report each strategy bit's main effect (variant v = bits)")
    ap.add_argument("--nomask", action="store_true", help="the bot ran with P.ab_nomask 1 (no enemy draft in the hash)")
    a = ap.parse_args()
    sigs = load_sigs()
    seen, rows = set(), []
    for f in a.lists.split(","):
        if not os.path.exists(f):
            continue
        for l in open(f, encoding="utf-8"):
            m = json.loads(l)
            if m["matchId"] in seen or m.get("status") != "finished" or not (a.since <= m["createdAt"] < a.until):
                continue
            if not any(t["name"] == "HouseOfCoders" for t in m["teams"]):
                continue
            seen.add(m["matchId"])
            v = variant(sigs, m, a.n, nomask=a.nomask)
            if v is None:
                continue
            res = next(t for t in m["teams"] if t["name"] == "HouseOfCoders")["result"]
            rows.append((v, m["kind"], res == "win", m["map"]))
    for kind in ("ranked", "unranked", None):
        tab = collections.defaultdict(lambda: [0, 0])
        for v, k, w, _ in rows:
            if kind and k != kind:
                continue
            tab[v][0] += w
            tab[v][1] += 1
        print(f"--- {kind or 'all'}")
        for v in sorted(tab):
            w, n = tab[v]
            p, lo, hi = wilson(w, n)
            print(f"  variant {v}: {w:3d}-{n - w:3d}  {100 * p:5.1f}%  [{100 * lo:4.1f}, {100 * hi:4.1f}]")
        if a.bits and a.n > 1:
            for b in range(int(math.log2(a.n))):
                on = [r for r in rows if (kind is None or r[1] == kind) and (r[0] >> b) & 1]
                off = [r for r in rows if (kind is None or r[1] == kind) and not (r[0] >> b) & 1]
                if on and off:
                    pon, poff = sum(r[2] for r in on) / len(on), sum(r[2] for r in off) / len(off)
                    se = math.sqrt(pon * (1 - pon) / len(on) + poff * (1 - poff) / len(off)) or 1
                    print(f"  bit {b}: on {100 * pon:5.1f}% (n={len(on)}) off {100 * poff:5.1f}% (n={len(off)})  diff {100 * (pon - poff):+5.1f} +- {196 * se:.1f}")


if __name__ == "__main__":
    main()
