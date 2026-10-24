# Champion roles per study team (pb_extract.mjs roles): per champion type, games drafted, share of the team's captured gems / banked gems /
# kills / deaths / champion damage / camp damage, mean max bag, rounds carrying >= 100 gems, forwardness (mean f r101-1000), recalls,
# shops and wards per game; the same for the opponents pooled.
#   python tools/top2/playbooks/pb_roles.py
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from collections import defaultdict
from pbcommon import load_all, ORDER

games = load_all()


def agg(rows_by_game):
    acc = defaultdict(lambda: defaultdict(float))
    for R in rows_by_game:
        tot = {k: sum(x[k] for x in R) or 1 for k in ['capGems', 'banked', 'kills', 'deaths', 'dmgOut', 'campDmg', 'caps']}
        seen = set()
        for x in R:
            t = x['type']
            if t in ('Cassi', 'Issac'):
                t = 'C&I:' + t
            a = acc[t]
            if t not in seen:
                a['games'] += 1
                seen.add(t)
            for k in tot:
                a[k + 'Sh'] += x[k] / tot[k]
                a[k] += x[k]
            a['maxBag'] += x['maxBag']
            a['carryR'] += x['carryR']
            a['adv'] += x['adv'] or 0
            a['recalls'] += x['recalls']
            a['shops'] += x['shops']
            a['wards'] += x['wards']
            a['locks'] += x['locks']
            a['bagLost'] += x['bagLost']
    return acc


def show(acc, label):
    print(f'  {label}: type games | capGems% banked% kills% deaths% dmg% campDmg% | caps/g capGems/g banked/g | maxBag carryR | adv | recalls shops wards locks /g | bagLost/g')
    for t, a in sorted(acc.items(), key=lambda kv: -kv[1]['games']):
        n = a['games']
        if n < 5:
            continue
        print(f"    {t:12s} {int(n):3d} | {a['capGemsSh']/n:.2f} {a['bankedSh']/n:.2f} {a['killsSh']/n:.2f} {a['deathsSh']/n:.2f} {a['dmgOutSh']/n:.2f} {a['campDmgSh']/n:.2f} |"
              f" {a['caps']/n:.1f} {a['capGems']/n:.0f} {a['banked']/n:.0f} | {a['maxBag']/n:.0f} {a['carryR']/n:.0f} | {a['adv']/n:.3f} | {a['recalls']/n:.1f} {a['shops']/n:.1f} {a['wards']/n:.1f} {a['locks']/n:.2f} | {a['bagLost']/n:.0f}")


for k in ORDER:
    gs = games.get(k, [])
    print(f'\n== {k} ({len(gs)} games)')
    show(agg([g['rolesS'] for g in gs]), 'team')
    show(agg([g['rolesS'] for g in gs if g['win']]), 'team in wins')
    show(agg([g['rolesS'] for g in gs if not g['win']]), 'team in losses')
    show(agg([g['rolesO'] for g in gs]), 'opponents')
