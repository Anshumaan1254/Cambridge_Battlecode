"""Per-map results of BOT vs OPP from the ledger (current hashes): wins per side and the mean gem margin.
    python3 -I permap.py BOT OPP [contest]"""
import json, os, sys, collections
sys.path.insert(0, '/home/claude/cambridge_battlecode/tools')
import ledger
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
bot, opp = sys.argv[1], sys.argv[2]
rows = ledger.current_rows(bot, opp, True)
M = collections.defaultdict(list)
for (mp, side), r in rows.items():
    g = r['gems'] if isinstance(r['gems'], list) else [r['gems'], 0]
    M[mp].append((side, r['win'], g[0] - g[1], r.get('deaths')))
ci = {}
if len(sys.argv) > 3:
    import contest_idx
    ci = {k.replace('-', '_'): v for k, v in contest_idx.out.items()}
tot = 0; w = 0; n = 0
for mp in sorted(M, key=lambda m: sum(x[2] for x in M[m])):
    xs = M[mp]; m = sum(x[2] for x in xs) / len(xs)
    tot += m; w += sum(x[1] for x in xs); n += len(xs)
    c = ci.get(mp, (0, 0, 0))[0]
    print(f"{mp:24s} {''.join('W' if x[1] else 'L' for x in sorted(xs))}  margin {m:7.0f}  deaths {[x[3] for x in sorted(xs)]}  contest {c:.2f}")
print(f"maps {len(M)} games {n} wins {w} mean margin {tot / max(1, len(M)):.1f}")
