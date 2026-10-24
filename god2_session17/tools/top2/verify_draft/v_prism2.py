"""v_prism2.py (verify_draft): per-champion W/L bank gaps; does Prism denial predict the loss? Who lands the final tribute?
Usage: python tools/top2/verify_draft/v_prism2.py ROLES.jsonl"""
import sys, collections, math
sys.path.insert(0, 'C:/battlecode/Cambridge_Battlecode/tools/top2/verify_draft')
from vagg import *
G = load(sys.argv[1]); D, _ = dedup(G)
for key in ['pbg', 'pantheon', 'nyx', 'ifish', 'cm', 'coo']:
    gs = [g for g in D if g['key'] == key]
    W = [g for g in gs if g['studyWin']]; L = [g for g in gs if not g['studyWin']]
    types = collections.Counter(b['type'] for g in gs for b in study_bodies(g))
    print(f'== {key} ({len(W)} W / {len(L)} L)')
    for t, n in types.most_common():
        bw = [sum(b['banked'] for b in study_bodies(g, t)) for g in W if study_bodies(g, t)]
        bl = [sum(b['banked'] for b in study_bodies(g, t)) for g in L if study_bodies(g, t)]
        zl = sum(1 for x in bl if x == 0)
        print(f'   {t:12s} games {n:3d}: banked W {mean(bw):5.0f}  L {mean(bl):5.0f}  gap {mean(bw)-mean(bl):5.0f}   L games with 0 bank {zl}/{len(bl)}')
# denial analysis for Prism teams
print()
for key in ['pbg', 'pantheon', 'nyx']:
    gs = [g for g in D if g['key'] == key]
    rows = []
    for g in gs:
        p = study_bodies(g, 'Prism')[0]
        big_death = sum(k[2] for k in p['killers'] if k[2] >= 60)
        cancels = [t for t in p['tributes'] if t['bag'] >= 60 and t['res'] in ('lock', 'stun')]
        denied = big_death > 0 or len(cancels) > 0
        rows.append((g['studyWin'], denied, big_death > 0, len(cancels) > 0, g))
    for nm, f in (('any denial (death w/ bag>=60 or lock/stun cancel of a >=60 tribute)', 1), ('death with bag>=60', 2), ('lock/stun cancel', 3)):
        d1 = [r for r in rows if r[f]]; d0 = [r for r in rows if not r[f]]
        print(f'{key}: {nm}: denied games {len(d1)}, win rate {mean(r[0] for r in d1):.2f}; not denied {len(d0)}, win rate {mean(r[0] for r in d0):.2f}')
    Ls = [r for r in rows if not r[0]]
    print(f'   losses with no denial at all: {sum(1 for r in Ls if not r[1])}/{len(Ls)}')
# final tribute: who crossed 1000 in wins
print()
