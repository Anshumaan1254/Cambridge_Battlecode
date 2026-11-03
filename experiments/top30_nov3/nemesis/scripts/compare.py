#!/usr/bin/env python3
"""Nemesis (8 teams) vs easy (OneTap, eclipsed Sunlight, SilverSamurai) style table from out/profiles.jsonl.
Strata by our result (the selection is result-stratified: nemesis 12L/4W per team, easy 4L/8W). Usage: python3 -I compare.py"""
import json, collections, statistics as st, sys
P='/home/claude/cambridge_battlecode/experiments/top30_nov3/nemesis/out/profiles.jsonl'
EASY={'OneTap','eclipsed Sunlight','SilverSamurai'}
rows=[json.loads(l) for l in open(P)]
for r in rows: r['grp']='EASY' if r['opp'] in EASY else 'NEM'
def m(xs):
    xs=[x for x in xs if x is not None]
    return (sum(xs)/len(xs), len(xs)) if xs else (float('nan'),0)
cells=[('NEM','L'),('EASY','L'),('NEM','W'),('EASY','W')]
C={c:[r for r in rows if (r['grp'],r['res'])==c] for c in cells}
print('n per cell:', {f'{a}-{b}':len(v) for (a,b),v in C.items()}, 'total', len(rows))
def win_frac(o,lo,hi):
    v=[o['their_half_frac'].get(str(w)) for w in range(lo,hi)]; v=[x for x in v if x is not None]
    return sum(v)/len(v) if v else None
F=[
 ('final round', lambda r:r['final']),
 ('banked we', lambda r:r['sub_we']), ('banked they', lambda r:r['sub_they']),
 ('gap r200 (we-they, banked+carried)', lambda r:r['gap'].get('200')),
 ('gap r400', lambda r:r['gap'].get('400')), ('gap r600', lambda r:r['gap'].get('600')),('gap r1000', lambda r:r['gap'].get('1000')),
 ('behind150 round (loser fell 150 behind)', lambda r:r['behind150']),
]
for side in ('they_','we_'):
    s=side
    F+= [
 (f'{s} first camp hit round', lambda r,s=s:r[s]['first_hit_r_mean']),
 (f'{s} first target group rank (0=nearest)', lambda r,s=s:r[s]['first_target_rank_mean']),
 (f'{s} first target group gems', lambda r,s=s:r[s]['first_target_gems_mean']),
 (f'{s} first-target distinct frac (1=split)', lambda r,s=s:r[s]['first_target_distinct']),
 (f'{s} stack mean', lambda r,s=s:r[s]['stack_mean']),
 (f'{s} first capture round', lambda r,s=s:r[s]['first_capture_r']),
 (f'{s} captured by r150', lambda r,s=s:r[s]['cap150']),
 (f'{s} captured by r200', lambda r,s=s:r[s]['cap_by']['200']),
 (f'{s} captured by r400', lambda r,s=s:r[s]['cap_by']['400']),
 (f'{s} banked by r400', lambda r,s=s:r[s]['bank_by']['400']),
 (f'{s} camp hits by r200', lambda r,s=s:r[s]['camp_hits_by']['200']),
 (f'{s} camp hits by r400', lambda r,s=s:r[s]['camp_hits_by']['400']),
 (f'{s} enemy-half frac r0-299', lambda r,s=s:win_frac(r[s],0,3)),
 (f'{s} enemy-half frac r300-799', lambda r,s=s:win_frac(r[s],3,8)),
 (f'{s} enemy-half frac r800+', lambda r,s=s:win_frac(r[s],8,13)),
 (f'{s} invasions (>=2 bodies >=5 r)', lambda r,s=s:r[s]['inv_n']),
 (f'{s} invasion rounds', lambda r,s=s:r[s]['inv_rounds']),
 (f'{s} first invasion round', lambda r,s=s:r[s]['inv_first_r']),
 (f'{s} champ hits', lambda r,s=s:r[s]['champ_hits']),
 (f'{s} champ hits at range 4', lambda r,s=s:r[s]['hits_range4']),
 (f'{s} spell champ hits', lambda r,s=s:r[s]['spell_champ_hits']),
 (f'{s} spell champ hits r>=4', lambda r,s=s:r[s]['spell_champ_hits_r4']),
 (f'{s} banks', lambda r,s=s:r[s]['banks']),
 (f'{s} bank mean', lambda r,s=s:r[s]['bank_mean']),
 (f'{s} bank max', lambda r,s=s:r[s]['bank_max']),
 (f'{s} carry rounds mean', lambda r,s=s:r[s]['carry_mean']),
 (f'{s} steals (captures of groups the other side killed)', lambda r,s=s:r[s]['steals']),
 (f'{s} steal gems', lambda r,s=s:r[s]['steal_gems']),
 (f'{s} locks', lambda r,s=s:r[s]['locks']),
 (f'{s} wards', lambda r,s=s:r[s]['wards']),
 (f'{s} wards on bush', lambda r,s=s:r[s]['wards_bush']),
 (f'{s} wards in enemy half', lambda r,s=s:r[s]['wards_enemy_half']),
 (f'{s} deaths', lambda r,s=s:r[s]['deaths']),
 (f'{s} deaths by r400', lambda r,s=s:sum(1 for d in r[s]['deaths_list'] if d['r']<=400)),
 (f'{s} gems lost in deaths', lambda r,s=s:r[s]['gems_lost']),
 (f'{s} shards r300', lambda r,s=s:r[s]['shards_r300']),
 (f'{s} shards r600', lambda r,s=s:r[s]['shards_r600']),
 (f'{s} gold r300', lambda r,s=s:r[s]['gold_r300']),
 (f'{s} teleports', lambda r,s=s:r['teleports'][s[:-1] if s=='we_' else 'they']),
 ]
F+= [
 ('fights: exchanges', lambda r:r['fights']['n_exch']),
 ('fights: we hit first frac', lambda r:r['fights']['first_we']/r['fights']['n_exch'] if r['fights']['n_exch'] else None),
 ('fights: we win exch', lambda r:r['fights']['win_we']), ('fights: they win exch', lambda r:r['fights']['win_they']),
 ('fights: they-first on our farm (farm_def_they_first)', lambda r:r['fights']['farm_def_they_first']),
 ('fights: we-first on their farm', lambda r:r['fights']['farm_def_we_first']),
 ('fights: num we', lambda r:r['fights']['num_we']), ('fights: num they', lambda r:r['fights']['num_they']),
 ('dives we', lambda r:r['fights']['dives_we']), ('dives they', lambda r:r['fights']['dives_they']),
 ('chases we', lambda r:r['fights']['chases_we']), ('chases they', lambda r:r['fights']['chases_they']),
 ('lure deaths we', lambda r:r['fights']['lure_deaths_we']),
 ('retreats we', lambda r:r['fights']['retreats_we']),('retreats they', lambda r:r['fights']['retreats_they']),
 ('recalls we', lambda r:r['fights']['recalls_we']),('recalls they', lambda r:r['fights']['recalls_they']),
 ('passing camp hits we', lambda r:r['passing_camp_hits']['we']),('passing camp hits they', lambda r:r['passing_camp_hits']['they']),
]
print(f"{'metric':52s} " + ' '.join(f'{a+"-"+b:>14s}' for a,b in cells))
for name,f in F:
    vals=[]
    for c in cells:
        xs=[]
        for r in C[c]:
            try: xs.append(f(r))
            except Exception: xs.append(None)
        mu,n=m(xs); vals.append(f'{mu:9.2f} ({n:2d})')
    print(f'{name:52s} '+' '.join(f'{v:>14s}' for v in vals))
# drafts
print('\nopponent draft frequency per game (they_) and ours (we_):')
for side in ('they_','we_'):
    for c in cells:
        cnt=collections.Counter(ch for r in C[c] for ch in r[side]['draft'])
        print(side,c,len(C[c]),' '.join(f'{k}:{v/len(C[c]):.2f}' for k,v in cnt.most_common()))
# our deaths context
print('\nour deaths by ctx/band/killer per game:')
for c in cells:
    for key in ('ctx','band','farming','lure','started'):
        cnt=collections.Counter(str(d[key]) for r in C[c] for d in r['we_']['deaths_list'])
        print(c,key,' '.join(f'{k}:{v/len(C[c]):.2f}' for k,v in cnt.most_common(8)))
# per team in losses
print('\nper opponent (all strata): n, res W, they: first hit r, cap r200, enemy-half r0-299, inv_n, spell r4 hits, wards, steals; we: deaths, cap r200; gap r200')
by=collections.defaultdict(list)
for r in rows: by[r['opp']].append(r)
for o,rs in sorted(by.items(), key=lambda kv: kv[0] in EASY):
    g=lambda f: m([f(r) for r in rs])[0]
    print(f"{o[:18]:18s} n{len(rs):3d} W{sum(r['res']=='W' for r in rs):2d}  {g(lambda r:r['they_']['first_hit_r_mean']):5.1f} {g(lambda r:r['they_']['cap_by']['200']):6.1f} {g(lambda r:win_frac(r['they_'],0,3) or 0):5.3f} {g(lambda r:r['they_']['inv_n']):4.1f} {g(lambda r:r['they_']['spell_champ_hits_r4']):5.1f} {g(lambda r:r['they_']['wards']):6.1f} {g(lambda r:r['they_']['steals']):4.1f} | {g(lambda r:r['we_']['deaths']):5.1f} {g(lambda r:r['we_']['cap_by']['200']):6.1f} | {g(lambda r:r['gap'].get('200',0)):+6.1f}  drafts: {collections.Counter(c for r in rs for c in r['they_']['draft']).most_common(5)}")
