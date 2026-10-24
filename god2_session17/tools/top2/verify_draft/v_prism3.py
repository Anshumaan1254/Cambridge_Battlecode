"""v_prism3.py (verify_draft): Prism gem flow (in = captures + steals; out = bank / death loss / held at end) in W vs L;
timing of Prism banks; whether the Prism's tribute is the game-winning one.  Usage: python v_prism3.py ROLES.jsonl"""
import sys, collections
sys.path.insert(0, 'C:/battlecode/Cambridge_Battlecode/tools/top2/verify_draft')
from vagg import *
G = load(sys.argv[1]); D, _ = dedup(G)
for key in ['pbg', 'pantheon', 'nyx']:
    gs = [g for g in D if g['key'] == key]
    for nm, S in (('W', [g for g in gs if g['studyWin']]), ('L', [g for g in gs if not g['studyWin']])):
        cap = []; steal = []; bank = []; lost = []; held = []; fr = []
        for g in S:
            p = study_bodies(g, 'Prism')[0]
            # gems stolen: bags of enemies this body killed
            st = 0
            for b in opp_bodies(g):
                for (r, killer, bag) in b['killers']:
                    pass
            cap.append(p['capGems']); bank.append(p['banked']); lost.append(p['gemsLost']); held.append(p['bagEnd']); fr.append(g['finalRound'])
        inflow_other = [b + l + h - c for b, l, h, c in zip(bank, lost, held, cap)]
        print(f"{key} {nm} n={len(S)}: Prism captured {mean(cap):.0f}, other inflow (steals etc.) {mean(inflow_other):.0f} | banked {mean(bank):.0f}, lost on death {mean(lost):.0f}, held at end {mean(held):.0f}")
    # timing of Prism banks in wins
    W = [g for g in gs if g['studyWin']]
    first_bank = []; final_is_prism = 0; n = 0
    for g in W:
        p = study_bodies(g, 'Prism')[0]
        tb = [t for t in p['tributes'] if t['res'] == 'bank']
        if tb: first_bank.append(min(t['at'] for t in tb))
        # game-winning tribute = last bank event among study team
        last = None
        for b in study_bodies(g):
            for t in b['tributes']:
                if t['res'] == 'bank' and (last is None or t['at'] > last[0]): last = (t['at'], b['type'], t['bag'])
        if last: n += 1; final_is_prism += last[1] == 'Prism'
    print(f"  {key} wins: Prism first bank round mean {mean(first_bank):.0f} (n={len(first_bank)}); last team tribute is the Prism's in {final_is_prism}/{n} wins; mean final round of wins {mean(g['finalRound'] for g in W):.0f}")
    # team score at the Prism's first bank in wins: how far was the team from 1000?
