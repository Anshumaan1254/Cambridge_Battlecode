"""v_carry.py (verify_draft): per-champion shares (bank, capture gold, champion damage, deaths), W/L deaths & gem losses,
max HP at fixed rounds.  Usage: python v_carry.py ROLES.jsonl [team ...]"""
import sys, collections
sys.path.insert(0, 'C:/battlecode/Cambridge_Battlecode/tools/top2/verify_draft')
from vagg import *
G = load(sys.argv[1]); D, _ = dedup(G)
teams = sys.argv[2:] or ['ifish', 'pbg', 'nyx', 'pantheon', 'coo', 'cm']
def share(g, b, f):
    tot = sum(x[f] for x in study_bodies(g)); return b[f] / tot if tot > 0 else None
for key in teams:
    gs = [g for g in D if g['key'] == key]
    W = [g for g in gs if g['studyWin']]; L = [g for g in gs if not g['studyWin']]
    types = collections.Counter(b['type'] for g in gs for b in study_bodies(g))
    print(f'== {key} ({len(W)} W / {len(L)} L)')
    print('   type        n   bank% gold% dmg% deaths% | deaths/g W  L  (ratio) | gemsLost W  L | banked W  L | maxHP r500 r900 final')
    for t, n in types.most_common():
        sh = {f: mean(s for g in gs for b in study_bodies(g, t) if (s := share(g, b, f)) is not None) for f in ('banked', 'capGold', 'dmgOut', 'deaths')}
        dw = mean(b['deaths'] for g in W for b in study_bodies(g, t)); dl = mean(b['deaths'] for g in L for b in study_bodies(g, t))
        lw = mean(b['gemsLost'] for g in W for b in study_bodies(g, t)); ll = mean(b['gemsLost'] for g in L for b in study_bodies(g, t))
        bw = mean(b['banked'] for g in W for b in study_bodies(g, t)); bl = mean(b['banked'] for g in L for b in study_bodies(g, t))
        h5 = mean(b['maxHpAt'].get('500') for g in gs for b in study_bodies(g, t) if b['maxHpAt'].get('500'))
        h9 = mean(b['maxHpAt'].get('900') for g in gs for b in study_bodies(g, t) if b['maxHpAt'].get('900'))
        hf = mean(b['maxHpFinal'] for g in gs for b in study_bodies(g, t))
        print(f'   {t:11s} {n:3d}  {sh["banked"]*100:4.0f}  {sh["capGold"]*100:4.0f}  {sh["dmgOut"]*100:4.0f}  {sh["deaths"]*100:4.0f}  | {dw:4.1f} {dl:4.1f} ({dl/max(dw,0.01):4.1f}) | {lw:5.0f} {ll:5.0f} | {bw:4.0f} {bl:4.0f} | {h5:5.0f} {h9:5.0f} {hf:5.0f}')
    print(f'   team deaths/game W {mean(sum(b["deaths"] for b in study_bodies(g)) for g in W):.1f}  L {mean(sum(b["deaths"] for b in study_bodies(g)) for g in L):.1f}; final round W {mean(g["finalRound"] for g in W):.0f} L {mean(g["finalRound"] for g in L):.0f}')
