"""v_prism.py (verify_draft): Prism bank dependence of pbg / pantheon / nyx (claim prism_bank).
Usage: python tools/top2/verify_draft/v_prism.py ROLES.jsonl"""
import sys, collections, math
sys.path.insert(0, 'C:/battlecode/Cambridge_Battlecode/tools/top2/verify_draft')
from vagg import *

G = load(sys.argv[1]); D, _ = dedup(G)
for key in ['pbg', 'pantheon', 'nyx', 'coo']:
    gs = [g for g in D if g['key'] == key]
    rows = []
    for g in gs:
        P = study_bodies(g, 'Prism')
        if not P: continue
        p = P[0]
        team_bank = g['submitted'][g['studyTeam']]
        opp_bank = g['submitted'][1 - g['studyTeam']]
        rows.append(dict(win=g['studyWin'], pbank=p['banked'], team=team_bank, opp=opp_bank, fr=g['finalRound'], bagEnd=p['bagEnd'],
                         lost=p['gemsLost'], deaths=p['deaths'], bagAvg=p['bagSum'] / max(1, p['rounds']), bagAlive=p['bagAliveSum'] / max(1, p['aliveRounds']),
                         bagMax=p['bagMax'], ntrib=len(p['tributes']), file=g['file'], others=team_bank - p['banked']))
    if not rows: continue
    W = [r for r in rows if r['win']]; L = [r for r in rows if not r['win']]
    print(f"== {key}: games with Prism {len(rows)} (W {len(W)}, L {len(L)}); without Prism {len(gs)-len(rows)}")
    for nm, S in (('W', W), ('L', L)):
        print(f"  {nm}: Prism banked/game {mean(r['pbank'] for r in S):.0f}; games with Prism bank>0: {sum(r['pbank']>0 for r in S)}/{len(S)}; "
              f"team bank {mean(r['team'] for r in S):.0f} (others {mean(r['others'] for r in S):.0f}); opp {mean(r['opp'] for r in S):.0f}; "
              f"final round {mean(r['fr'] for r in S):.0f}; Prism bag at end {mean(r['bagEnd'] for r in S):.0f}; gems lost on death {mean(r['lost'] for r in S):.0f}; deaths {mean(r['deaths'] for r in S):.2f}")
    print(f"  all: time-avg bag (all rounds) {mean(r['bagAvg'] for r in rows):.1f}; while alive {mean(r['bagAlive'] for r in rows):.1f}; per-game max {mean(r['bagMax'] for r in rows):.0f}")
    # Prism share of team bank, in wins
    print(f"  Prism share of team bank (mean of per-game shares, all games): {mean(r['pbank']/r['team'] for r in rows if r['team']>0):.3f}; wins only {mean(r['pbank']/r['team'] for r in W if r['team']>0):.3f}")
    # in losses: was the Prism holding a big bag when the game ended?
    for thr in (100, 200, 300):
        print(f"  losses with Prism bag at end >= {thr}: {sum(r['bagEnd']>=thr for r in L)}/{len(L)}")
    # what would have happened if the Prism bag at end were added
    print(f"  losses where team bank + Prism end bag >= 1000: {sum(r['team']+r['bagEnd']>=1000 for r in L)}/{len(L)};  where team+bagEnd+gemsLost >= opp: {sum(r['team']+r['bagEnd']+r['lost']>=r['opp'] for r in L)}")
    # bucket losses by game length
    for lo, hi in ((0, 600), (600, 900), (900, 1200), (1200, 2001)):
        s = [r for r in L if lo <= r['fr'] < hi]; w = [r for r in W if lo <= r['fr'] < hi]
        print(f"   final round {lo}-{hi}: L n={len(s)} Prism bank {mean(r['pbank'] for r in s):.0f} | W n={len(w)} Prism bank {mean(r['pbank'] for r in w):.0f}")
