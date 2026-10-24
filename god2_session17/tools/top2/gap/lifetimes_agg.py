# gap_g8: aggregate tools/top2/gap/lifetimes.mjs: life length before each death, deaths in a life that never damaged a camp ("feeding"),
# distance from spawn at death, by opponent and phase.   python tools/top2/gap/lifetimes_agg.py C:/battlecode/cache/gap_g8/lifetimes.jsonl
import json, sys, collections, statistics as st
SIDES = json.load(open('C:/battlecode/cache/gap_g8/sides.json', encoding='utf-8'))
OPP = {'prism best girl': 'PBG', 'Intercontinental Fish': 'IFish', 'Claudus Maximus': 'CM'}
rows = [json.loads(l) for l in open(sys.argv[1], encoding='utf-8') if l.strip()]
for g in ('ALL', 'PBG', 'IFish', 'CM'):
    G = [r for r in rows if g == 'ALL' or OPP[SIDES[r['file']]['opp']] == g]
    n = len(G)
    for who in ('us', 'them'):
        L = [x for r in G for x in r['lives'] if (x[0] == SIDES[r['file']]['ours']) == (who == 'us') and x[1] != 'Issac']
        ch = [x for x in L if not x[6]]
        short = [x for x in ch if x[2] < 60]
        nofarm = [x for x in ch if not x[4]]
        print('%-5s %-4s deaths %.2f/game (champion %.2f): life median %s rounds; champion deaths after < 60 alive rounds %.2f/game, after a life with no camp damage %.2f/game (%.0f%%), median distance from spawn %s; respawn-feed (no camp damage, life < 60) %.2f/game' % (
            g, who, len(L) / n, len(ch) / n, st.median([x[2] for x in L]) if L else None, len(short) / n, len(nofarm) / n, 100 * len(nofarm) / max(1, len(ch)),
            st.median([x[3] for x in ch]) if ch else None, sum(1 for x in ch if not x[4] and x[2] < 60) / n))
