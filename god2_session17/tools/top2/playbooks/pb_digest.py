# Compact digest of selected games (pb_select.SEL) per study team from pb_extract.mjs output: score / max-health at checkpoints, first events,
# kills-deaths per phase, captures by zone and class, banks (count, biggest, last), big bags lost, objectives, locks, recalls, presence.
#   python tools/top2/playbooks/pb_digest.py [key...]
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from pbcommon import load_all, ORDER
from pb_select import SEL

G = load_all()
keys = sys.argv[1:] or ORDER


def ph(r):
    return 0 if r <= 300 else (1 if r <= 600 else 2)


for k in keys:
    gs = {g['file']: g for g in G[k]}
    print(f'\n######## {k}')
    for f in SEL[k]:
        g = gs[f]
        S, O = g['S'], g['O']
        es, eo = S['ev'], O['ev']
        cp = lambda X, r: X['cp'].get(str(r))
        line = []
        for r in (100, 300, 600, 900):
            a, b = cp(S, r), cp(O, r)
            if a and not a['ended']:
                line.append(f"r{r} {a['sub']}-{b['sub']} hp{a['maxHp'] - b['maxHp']:+d} bag{a['maxBag']}/{b['maxBag']}")
        kd = [[0, 0], [0, 0], [0, 0]]
        for d in es['deaths']:
            kd[ph(d[0])][1] += 1
        for d in eo['deaths']:
            kd[ph(d[0])][0] += 1
        big_lost = [f"r{d[0]} {d[1]}:{d[2]}" for d in es['deaths'] if d[2] >= 100]
        big_stolen = [f"r{d[0]} {d[1]}:{d[2]}" for d in eo['deaths'] if d[2] >= 100]
        capz = {}
        for c in es['caps']:
            capz[c[3]] = capz.get(c[3], 0) + c[1]
        capzo = {}
        for c in eo['caps']:
            capzo[c[3]] = capzo.get(c[3], 0) + c[1]
        bl = es['banksList']
        big = max(bl, key=lambda b: b[1]) if bl else None
        obj = [f"{o['cls']}{o['z'][0]} hit{o['firstHit']} caps{o['caps']} enemy{o['ecaps']}" for o in es['obj'] if o['firstHit'] or o['caps'] or o['ecaps']]
        lk = [f"r{x['r']}{x['kind'][0]}" for x in es['locks']]
        lko = [f"r{x['r']}{x['kind'][0]}" for x in eo['locks']]
        w2 = S['win'][1]
        print(f"{'W' if g['win'] else 'L'} {f} n{g['n']} {g['size']} {g['obj'] or '-'} vs {g['opp']} | {g['submitted'][g['s']]}-{g['submitted'][1 - g['s']]} r{g['final']} | {' '.join(g['draftS'])} vs {' '.join(g['draftO'])}")
        print(f"   {' | '.join(line)}")
        print(f"   first: cap {es['firstCap']}/{eo['firstCap']} midcap {es['firstMidCap']}/{eo['firstMidCap']} kill {es['firstKill']}/{eo['firstKill']} contact {es['firstContact']} | K-D r1-300 {kd[0][0]}-{kd[0][1]} r301-600 {kd[1][0]}-{kd[1][1]} r601+ {kd[2][0]}-{kd[2][1]}")
        print(f"   caps gems own/mid/their {capz.get('o',0)}/{capz.get('m',0)}/{capz.get('t',0)} vs {capzo.get('o',0)}/{capzo.get('m',0)}/{capzo.get('t',0)} | banks {len(bl)} biggest {big} last {es['lastBank']['gems'] if es['lastBank'] else None}@r{es['lastBank']['r'] if es['lastBank'] else None} {es['lastBank']['type'] if es['lastBank'] else ''} | opp banks {len(eo['banksList'])}")
        print(f"   big bags lost {big_lost} stolen {big_stolen} | obj {obj} | locks {lk} opp {lko} | coh r101-300 {w2['coh']/max(1,w2['cohR']):.1f} mid {w2['zone']['mid']/max(1,w2['aliveBR']):.2f}")
