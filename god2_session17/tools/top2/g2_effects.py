#!/usr/bin/env python3
"""Per-module effects of an in-bot factorial A/B sweep (bots/god2b g2ab.h): python tools/top2/g2_effects.py LABEL N [--ref G2A,S0] [--bits names]

Each game of LABEL played variant strat_hash(W, H, camps, side, 0) % N (tools/live/variant_of.py), bit k = module k on. For every bit:
mean of the metric with the bit on vs off (raw), and the same on per-cell deltas against each reference label (same opponent, map and
side: the map and side fix the variant, so raw on/off compares different maps; the deltas remove the cell). Also a least-squares fit
delta ~ intercept + bits (joint main effects with standard errors). Metrics: win, our banked gems, gem margin (ours - theirs), deaths."""
import json, math, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "live"))
os.chdir(ROOT)
from analyze import team_stats, side, COMPACT
from variant_of import strat_hash, load_sigs
SALT = int(sys.argv[sys.argv.index("--salt") + 1]) if "--salt" in sys.argv else 0  # P.g2ab_salt of the sweep

label, N = sys.argv[1], int(sys.argv[2])
refs = sys.argv[sys.argv.index("--ref") + 1].split(",") if "--ref" in sys.argv else ["G2A", "S0"]
names = sys.argv[sys.argv.index("--bits") + 1].split(",") if "--bits" in sys.argv else ["bank", "deny", "fight", "mid"]
nb = max(1, int(round(math.log2(N))))
sigs = load_sigs()
groups = [json.loads(l) for l in open("experiments/live/groups.jsonl", encoding="utf-8")]
lab = {(g["resp"].get("groupId") or g["resp"].get("id")): g["label"] for g in groups}
cells = {}  # label -> (opp, map, side) -> stats
for l in open("experiments/live/lists/groups_matches.jsonl", encoding="utf-8"):
    m = json.loads(l)
    L = lab.get(m.get("groupId"))
    if L not in [label] + refs:
        continue
    p = os.path.join(COMPACT, m["matchId"] + ".json")
    if not os.path.exists(p):
        continue
    r = json.load(open(p, encoding="utf-8"))
    us = side(r, "HouseOfCoders")
    them = "teamB" if us == "teamA" else "teamA"
    a, b = team_stats(r, us), team_stats(r, them)
    opp = next(t["name"] for t in r["teams"] if t["team"] == them)
    sd = next(t for t in m["teams"] if t["name"] == "HouseOfCoders")["side"]
    mp = m["map"].replace("-", "_")
    row = {"win": float(a["win"]), "gems": a["gems"], "margin": a["gems"] - b["gems"], "deaths": a["deaths"], "camp": a["camp_gems"],
           "kills": a["kills"], "opp_gems": b["gems"]}
    if mp in sigs:
        w, h, c = sigs[mp]
        row["v"] = strat_hash(w, h, c, 0 if sd == "a" else 1, SALT) % N
    cells.setdefault(L, {})[(opp, mp, sd)] = row
G = cells.get(label, {})
if len(refs) > 1:
    # the mean of the references per cell (cells present in all of them): less reference noise than any one
    common = set.intersection(*(set(cells.get(x, {})) for x in refs))
    cells["MEAN"] = {k: {m: sum(cells[x][k][m] for x in refs) / len(refs) for m in ("win", "gems", "margin", "deaths", "camp", "kills", "opp_gems")}
                     for k in common}
    refs = refs + ["MEAN"]
print(f"{label}: {len(G)} games, wins {sum(r['win'] for r in G.values()):.0f}; refs " + ", ".join(f"{x} {len(cells.get(x, {}))}" for x in refs))
METRICS = ["win", "gems", "margin", "deaths", "camp"]


def mean_se(v):
    if not v:
        return float("nan"), float("nan")
    m = sum(v) / len(v)
    if len(v) < 2:
        return m, float("nan")
    s = math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))
    return m, s / math.sqrt(len(v))


def diff(on, off):
    (m1, s1), (m0, s0) = mean_se(on), mean_se(off)
    return m1 - m0, math.sqrt(s1 * s1 + s0 * s0)


def ols(X, y):
    """least squares with standard errors (normal equations, tiny Gauss-Jordan)"""
    k = len(X[0])
    A = [[sum(X[i][a] * X[i][b] for i in range(len(X))) for b in range(k)] for a in range(k)]
    z = [sum(X[i][a] * y[i] for i in range(len(X))) for a in range(k)]
    inv = [[float(a == b) for b in range(k)] for a in range(k)]
    M = [row[:] for row in A]
    for c in range(k):
        piv = max(range(c, k), key=lambda r: abs(M[r][c]))
        M[c], M[piv] = M[piv], M[c]
        inv[c], inv[piv] = inv[piv], inv[c]
        d = M[c][c]
        if abs(d) < 1e-12:
            return None
        for j in range(k):
            M[c][j] /= d
            inv[c][j] /= d
        for r in range(k):
            if r != c:
                f = M[r][c]
                for j in range(k):
                    M[r][j] -= f * M[c][j]
                    inv[r][j] -= f * inv[c][j]
    beta = [sum(inv[a][b] * z[b] for b in range(k)) for a in range(k)]
    res = [y[i] - sum(beta[a] * X[i][a] for a in range(k)) for i in range(len(X))]
    dof = max(1, len(X) - k)
    s2 = sum(e * e for e in res) / dof
    return [(beta[a], math.sqrt(max(0.0, s2 * inv[a][a]))) for a in range(k)]


rows = [r for r in G.values() if "v" in r]
print("\nRAW (different maps on / off):")
for b in range(nb):
    nm = names[b] if b < len(names) else f"bit{b}"
    on = [r for r in rows if (r["v"] >> b) & 1]
    off = [r for r in rows if not (r["v"] >> b) & 1]
    print(f"  {nm:6s} on {len(on):3d} off {len(off):3d} | " + "  ".join(f"{k} {diff([r[k] for r in on], [r[k] for r in off])[0]:+7.2f}" for k in METRICS))
for ref in refs:
    R = cells.get(ref, {})
    pairs = [(key, G[key], R[key]) for key in G if key in R and "v" in G[key]]
    if not pairs:
        continue
    print(f"\nPAIRED vs {ref} ({len(pairs)} cells; delta = {label} - {ref}): mean delta " +
          "  ".join(f"{k} {mean_se([g[k] - r[k] for _, g, r in pairs])[0]:+.2f}" for k in METRICS))
    for b in range(nb):
        nm = names[b] if b < len(names) else f"bit{b}"
        on = [(g, r) for _, g, r in pairs if (g["v"] >> b) & 1]
        off = [(g, r) for _, g, r in pairs if not (g["v"] >> b) & 1]
        out = []
        for k in METRICS:
            d, se = diff([g[k] - r[k] for g, r in on], [g[k] - r[k] for g, r in off])
            out.append(f"{k} {d:+7.2f}+-{se:5.2f}")
        print(f"  {nm:6s} on {len(on):3d} off {len(off):3d} | " + "  ".join(out))
    print(f"  OLS delta ~ bits (joint):")
    X = [[1.0] + [float((g["v"] >> b) & 1) for b in range(nb)] for _, g, r in pairs]
    for k in ("win", "gems", "margin", "deaths"):
        fit = ols(X, [g[k] - r[k] for _, g, r in pairs])
        if fit:
            print(f"    {k:7s} " + "  ".join(f"{(['const'] + names)[i] if i < len(names) + 1 else i}: {be:+7.2f}+-{se:5.2f}" for i, (be, se) in enumerate(fit)))
print("\nPER OPPONENT (paired vs first ref, margin delta by bit on - off):")
R = cells.get(refs[0], {})
for opp in sorted({k[0] for k in G}):
    pairs = [(G[k], R[k]) for k in G if k[0] == opp and k in R and "v" in G[k]]
    if not pairs:
        continue
    s = []
    for b in range(nb):
        on = [g["margin"] - r["margin"] for g, r in pairs if (g["v"] >> b) & 1]
        off = [g["margin"] - r["margin"] for g, r in pairs if not (g["v"] >> b) & 1]
        s.append(f"{names[b] if b < len(names) else b} {diff(on, off)[0]:+6.0f}")
    print(f"  {opp[:22]:22s} n={len(pairs):3d} wins {sum(g['win'] for g, _ in pairs):.0f} vs {sum(r['win'] for _, r in pairs):.0f} | " + "  ".join(s))
