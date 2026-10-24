# What is common to winning at this level: for each feature, the paired in-game difference d = S - O (study team minus its opponent in the
# same game) and the study team's win rate when d > 0 vs d < 0, per team; plus the within-team win-vs-loss standardized difference of S.
# Features whose sign agrees for all six teams are candidates for "essential"; features where the teams differ are style.
#   python tools/top2/playbooks/pb_common.py
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import pandas as pd
import numpy as np
from pbcommon import ORDER, BASE

df = pd.read_pickle(f'{BASE}/flat.pkl')
S0 = df[df.X == 'S']
dup = S0.duplicated(subset=['key', 'map', 'side', 'opp', 'final', 'scoreS', 'scoreO'], keep='first')
keep = set(zip(S0[~dup].key, S0[~dup].file))
df = df[[(k, f) in keep for k, f in zip(df.key, df.file)]]
S = df[df.X == 'S'].set_index(['key', 'file']).sort_index()
O = df[df.X == 'O'].set_index(['key', 'file']).sort_index()
FEATS = ['w1_z_mid', 'w2_z_mid', 'w3_z_mid', 'w1_coh', 'w2_coh', 'w3_coh', 'w2_tog3', 'w1_a_farm', 'w2_a_farm', 'w3_a_farm', 'all_a_idle', 'all_a_walk',
         'caps_r100', 'caps_r200', 'caps_r300', 'capGems_r200', 'capGems_r300', 'capZ_mid', 'capGems1000', 'gemsPerCap', 'capC_elk', 'objCaps',
         'firstCap', 'firstMidCap', 'firstKill', 'firstDeath', 'sub200', 'sub300', 'sub600', 'maxHp300', 'maxHp600', 'maxHp1000', 'tot_goldIn',
         'tot_banks', 'gemsPerBank', 'maxBag', 'bagLost', 'bagStolen', 'deaths1000', 'kills1000', 'recalls1000b', 'shops1000b', 'wards1000', 'locks',
         'w2_deaths100', 'w2_kills100', 'w3_deaths100', 'w3_kills100', 'all_z_their', 'capNear', 'capContested', 'bankMidShare']
LOWER_BETTER = {'firstCap', 'firstMidCap', 'firstKill', 'deaths1000', 'w2_deaths100', 'w3_deaths100', 'bagLost'}
print('feature'.ljust(16) + ' | ' + ' | '.join(f'{k:>16s}' for k in ORDER) + ' | agree')
print(' ' * 16 + ' | ' + ' | '.join(f'{"P(w|d>0)/P(w|d<0)":>16s}' for _ in ORDER))
rows = []
for f in FEATS:
    cells = []
    signs = []
    for k in ORDER:
        s = S.loc[k][f].astype(float)
        o = O.loc[k][f].astype(float)
        w = S.loc[k].win
        if f in ('firstKill', 'firstCap', 'firstMidCap', 'firstDeath'):
            # missing = never happened: treat as late (final round)
            fin = S.loc[k].final.astype(float)
            s = s.fillna(fin + 1)
            o = o.fillna(fin + 1)
        d = s - o
        pos = d > 0
        neg = d < 0
        a = w[pos].mean() if pos.sum() >= 5 else np.nan
        b = w[neg].mean() if neg.sum() >= 5 else np.nan
        cells.append(f'{a:5.0%}/{b:5.0%} n{int(pos.sum()):3d}/{int(neg.sum()):3d}' if not (np.isnan(a) or np.isnan(b)) else '        -       ')
        if not (np.isnan(a) or np.isnan(b)):
            signs.append(np.sign(a - b))
    agree = int(abs(sum(signs)))
    rows.append((f, agree, len(signs)))
    print(f.ljust(16) + ' | ' + ' | '.join(f'{c:>16s}' for c in cells) + f' | {agree}/{len(signs)}')

print('\n# within-team: S in wins vs S in losses (difference in pooled SDs of S), per team; then O in those games')
for f in FEATS:
    cells = []
    for k in ORDER:
        s = S.loc[k][f].astype(float)
        w = S.loc[k].win
        sd = s.std()
        z = (s[w].mean() - s[~w].mean()) / sd if sd else np.nan
        cells.append(f'{z:+.2f}')
    print(f.ljust(16) + ' | ' + ' | '.join(f'{c:>6s}' for c in cells))
