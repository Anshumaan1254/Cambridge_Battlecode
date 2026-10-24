# Decision rules from pb_rules.mjs output (C:/battlecode/cache/top2_playbooks/rules_<key>.jsonl) joined with the platform index:
#   (1) tributes: bag at start, completion by bag and by enemies within 8, game-ending share, altar zone, max-health ratio at the start;
#   (2) objectives (monolith / golem efforts): success, hitters, timing, power and score context at the first hit;
#   (3) leads: win rate by score / max-health lead at r300 / r600 (and comebacks); (4) carry: the team's largest bag over time.
#   python tools/top2/playbooks/pb_rules_agg.py
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from collections import defaultdict
from pbcommon import KEYS, ORDER

BASE = 'C:/battlecode/cache/top2_playbooks'


def load(key):
    idx = {}
    for l in open(f'C:/battlecode/cache/t2/{key}/index.jsonl', encoding='utf-8'):
        r = json.loads(l)
        idx[f"{r['map']}_{r['matchId'][:8]}"] = r
    out = []
    seen = set()
    for l in open(f'{BASE}/rules_{key}.jsonl', encoding='utf-8'):
        g = json.loads(l)
        if 'err' in g or g['file'] not in idx:
            continue
        r = idx[g['file']]
        me = [t for t in r['teams'] if t['teamId'].startswith(KEYS[key])][0]
        s = 0 if me['side'] == 'a' else 1
        sig = (r['map'], s, [t['name'] for t in r['teams'] if not t['teamId'].startswith(KEYS[key])][0], json.dumps(g['t0']['lead'][-1:]))
        if sig in seen:
            continue
        seen.add(sig)
        out.append({'file': g['file'], 'win': me['result'] == 'win', 'S': g['t' + str(s)], 'O': g['t' + str(1 - s)], 'n': len(me['draftPicks'])})
    return out


def q(a, p):
    return float(np.percentile(a, p)) if len(a) else float('nan')


for k in ORDER:
    gs = load(k)
    print(f'\n======== {k} ({len(gs)} games)')
    for lab in ['S', 'O']:
        tr = [t for g in gs for t in g[lab]['trib']]
        bags = [t[2] for t in tr]
        print(f"  [{lab}] tributes {len(tr)} ({len(tr)/len(gs):.1f}/game): bag median {q(bags,50):.0f} p75 {q(bags,75):.0f} p90 {q(bags,90):.0f}; share >= 100: {np.mean([b >= 100 for b in bags]):.0%}")
        for lo, hi in [(0, 50), (50, 100), (100, 200), (200, 400), (400, 99999)]:
            sub = [t for t in tr if lo <= t[2] < hi]
            if not sub:
                continue
            e0 = [t for t in sub if t[7] == 0]
            e1 = [t for t in sub if t[7] >= 1]
            ge = [t for t in sub if t[2] + t[3] >= 1000]
            zm = np.mean([t[8] == 'm' for t in sub])
            hpr = np.median([t[9] for t in sub])
            print(f"     bag {lo}-{hi}: n {len(sub)} done {np.mean([t[5] for t in sub]):.0%} | no enemy within 8: n {len(e0)} done {np.mean([t[5] for t in e0]) if e0 else float('nan'):.0%} | enemy near: n {len(e1)} done {np.mean([t[5] for t in e1]) if e1 else float('nan'):.0%}"
                  f" | game-ending {len(ge)} ({np.mean([t[5] for t in ge]) if ge else float('nan'):.0%} done) | mid altar {zm:.0%} | maxHp ratio med {hpr:.2f} | allies within 8 med {np.median([t[6] for t in sub]):.0f}")
        big = [t for t in tr if t[2] >= 150]
        if big:
            types = defaultdict(int)
            for t in big:
                types[t[1]] += 1
            print(f"     big (>=150) by type: {dict(types)}; start round median {q([t[0] for t in big],50):.0f}; own score at start median {q([t[3] for t in big],50):.0f}; score+bag >= 1000 in {np.mean([t[2]+t[3] >= 1000 for t in big]):.0%}; carry share median {q([t[10] for t in big],50):.2f}")
    # objectives
    for lab in ['S', 'O']:
        ob = [o for g in gs for o in g[lab]['obj']]
        if not ob:
            continue
        for cls in ['mono', 'golem']:
            sub = [o for o in ob if o[0] == cls]
            if not sub:
                continue
            succ = [o for o in sub if o[3] == 1]
            fail = [o for o in sub if o[3] != 1]
            def ctx(xs):
                if not xs:
                    return '-'
                return (f"n {len(xs)} hitters {np.mean([o[4] for o in xs]):.1f} first hit r{q([o[1] for o in xs],50):.0f} maxHp ratio {np.median([o[7]/max(1,o[8]) for o in xs]):.2f}"
                        f" score diff {np.median([o[9] for o in xs]):+.0f} team near at end {np.mean([o[5] for o in xs]):.1f} enemies near {np.mean([o[6] for o in xs]):.1f}")
            print(f"  [{lab}] {cls} efforts {len(sub)}: captured by us {len(succ)} ({len(succ)/len(sub):.0%}), by enemy {sum(1 for o in sub if o[3]==0)}, nobody {sum(1 for o in sub if o[3]==-1)}")
            print(f"        success: {ctx(succ)}")
            print(f"        fail   : {ctx(fail)}")
    # leads
    for r in (300, 600):
        sl = [(g['win'], dict((x[0], x) for x in g['S']['lead']).get(r)) for g in gs]
        sl = [(w, x) for w, x in sl if x]
        if not sl:
            continue
        def wr(cond):
            xs = [w for w, x in sl if cond(x)]
            return f"{np.mean(xs):.0%} (n{len(xs)})" if xs else '-'
        print(f"  lead at r{r}: score ahead {wr(lambda x: x[1] > 0)} behind {wr(lambda x: x[1] < 0)} behind by >100 {wr(lambda x: x[1] < -100)} | maxHp ahead {wr(lambda x: x[2] > 0)} behind {wr(lambda x: x[2] < 0)} | score behind but maxHp ahead {wr(lambda x: x[1] < 0 and x[2] > 0)} | score ahead but maxHp behind {wr(lambda x: x[1] > 0 and x[2] < 0)}")
    # carry
    for lab in ['S', 'O']:
        rows = [c for g in gs for c in g[lab]['carry'] if c[0] >= 300]
        if rows:
            ge100 = np.mean([c[1] >= 100 for c in rows])
            ge300 = np.mean([c[1] >= 300 for c in rows])
            types = defaultdict(int)
            for c in rows:
                if c[1] >= 100:
                    types[c[2]] += 1
            print(f"  [{lab}] carry (r>=300 checkpoints): largest bag >= 100 in {ge100:.0%}, >= 300 in {ge300:.0%}; holders of >=100: {dict(sorted(types.items(), key=lambda kv: -kv[1])[:4])}")
