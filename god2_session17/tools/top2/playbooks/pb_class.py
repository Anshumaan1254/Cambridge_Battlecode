# Per study team and map class (team size 3/4/5, map size small/medium/large, objective maps): the playbook features that change with
# the map, S (team) and O (opponents), duplicates (deterministic rematches) removed.
#   python tools/top2/playbooks/pb_class.py
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import pandas as pd
import numpy as np
from pbcommon import ORDER, BASE

df = pd.read_pickle(f'{BASE}/flat.pkl')
S = df[df.X == 'S'].copy()
dup = S.duplicated(subset=['key', 'map', 'side', 'opp', 'final', 'scoreS', 'scoreO'], keep='first')
keep = set(zip(S[~dup].key, S[~dup].file))
df = df[[(k, f) in keep for k, f in zip(df.key, df.file)]]
S = df[df.X == 'S'].set_index(['key', 'file'])
O = df[df.X == 'O'].set_index(['key', 'file'])
S['cls'] = S.apply(lambda r: f"{r.n}p-{r['size']}", axis=1)
S['objc'] = S.obj.map(lambda v: 'obj' if v else 'none')
F = [('win', 'win%'), ('final', 'final r'), ('w1_z_mid', 'mid% r1-100'), ('w2_z_mid', 'mid% r101-300'), ('w1_coh', 'cluster r1-100'), ('w2_coh', 'cluster r101-300'),
     ('firstCap', '1st cap'), ('firstMidCap', '1st mid cap'), ('firstKill', '1st kill'), ('capZ_mid', 'mid gem share'), ('capC_elk', 'elk share'),
     ('capGems1000', 'cap gems/1000r'), ('tot_banks', 'banks'), ('gemsPerBank', 'gems/bank'), ('maxBag', 'max bag'), ('lastBankGems', 'last bank'),
     ('objCaps', 'obj caps'), ('tot_deaths', 'deaths'), ('tot_kills', 'kills'), ('maxHp600', 'maxHp r600'), ('sub300', 'score r300'), ('sub600', 'score r600')]


def row(sub, osub, f):
    s = sub[f].astype(float).mean()
    if f in ('win', 'final'):
        return f'{s:.0%}' if f == 'win' else f'{s:.0f}'
    o = osub[f].astype(float).mean()
    fm = (lambda v: f'{v:.2f}') if abs(s) < 10 else (lambda v: f'{v:.0f}')
    return f'{fm(s)}|{fm(o)}'


for k in ORDER:
    s = S.loc[k]
    o = O.loc[k]
    print(f'\n== {k}')
    groups = []
    for c in ['3p-small', '3p-medium', '4p-small', '4p-medium', '5p-small', '5p-medium', '5p-large']:
        m = (s.cls == c).values
        if m.sum() >= 3:
            groups.append((c, m))
    groups.append(('obj maps', (s.objc == 'obj').values))
    groups.append(('no obj', (s.objc == 'none').values))
    print('feature'.ljust(16) + ''.join(f'{g[0]}({g[1].sum()})'.rjust(16) for g in groups))
    for f, lab in F:
        print(lab.ljust(16) + ''.join(row(s[m], o[m], f).rjust(16) for _, m in groups))
