# Playbook tables from flat.pkl (pb_flat.py): per study team, S (team) vs O (its opponents in the same games), wins vs losses, by map
# class, and a distinctiveness ranking (team mean vs the other five study teams, in pooled SDs).
#   python tools/top2/playbooks/pb_tables.py [section...]   -> stdout
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import pandas as pd
import numpy as np
from pbcommon import ORDER, BASE

df = pd.read_pickle(f'{BASE}/flat.pkl')
S = df[df.X == 'S'].set_index(['key', 'file'])
O = df[df.X == 'O'].set_index(['key', 'file'])
secs = sys.argv[1:] or ['overview', 'phase', 'opening', 'econ', 'fights', 'obj', 'end', 'distinct', 'classes']


def fmt(v, k=''):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return '-'
    if isinstance(v, (int, np.integer)):
        return str(v)
    if abs(v) >= 100:
        return f'{v:.0f}'
    if abs(v) >= 10:
        return f'{v:.1f}'
    return f'{v:.2f}'


def table(title, feats, groups=None):
    print(f'\n### {title}')
    hdr = ['feature'] + [f'{k} S|O' for k in ORDER]
    print(' | '.join(hdr))
    for f in feats:
        cells = [f]
        for k in ORDER:
            if k not in S.index.get_level_values(0):
                cells.append('-')
                continue
            s = S.loc[k][f]
            o = O.loc[k][f]
            if s.dtype == object:
                cells.append(f'{s.mode().iat[0] if len(s.dropna()) else "-"}|{o.mode().iat[0] if len(o.dropna()) else "-"}')
            else:
                cells.append(f'{fmt(s.mean())}|{fmt(o.mean())}')
        print(' | '.join(cells))


def table_wl(title, feats):
    print(f'\n### {title} (S in wins | S in losses | O in S wins | O in S losses)')
    for f in feats:
        cells = [f]
        for k in ORDER:
            s = S.loc[k]
            o = O.loc[k]
            w = s.win
            cells.append(f'{fmt(s[f][w].mean())}/{fmt(s[f][~w].mean())}')
        print(' | '.join(cells))


if 'overview' in secs:
    print('## overview')
    for k in ORDER:
        s = S.loc[k]
        print(f"{k}: n={len(s)} W={int(s.win.sum())} ({s.win.mean():.0%}); final round wins med {s.final[s.win].median():.0f} losses med {s.final[~s.win].median():.0f};"
              f" score S/O wins {s.scoreS[s.win].median():.0f}/{s.scoreO[s.win].median():.0f} losses {s.scoreS[~s.win].median():.0f}/{s.scoreO[~s.win].median():.0f}")
        for cls in ['n', 'size', 'obj']:
            parts = []
            for v, grp in s.groupby(cls):
                parts.append(f"{v or 'none'} {int(grp.win.sum())}/{len(grp)}")
            print(f"   by {cls}: " + ', '.join(parts))

if 'phase' in secs:
    for p in ['w1', 'w2', 'w3', 'w4', 'w5']:
        table(f'phase {p}', [f'{p}_z_mid', f'{p}_z_their', f'{p}_adv', f'{p}_a_farm', f'{p}_a_fight', f'{p}_a_walk', f'{p}_a_idle', f'{p}_a_bank', f'{p}_a_home', f'{p}_dead',
                             f'{p}_coh', f'{p}_cohN', f'{p}_squads', f'{p}_tog3', f'{p}_caps100', f'{p}_capGems100', f'{p}_capMid', f'{p}_capTheir', f'{p}_deaths100', f'{p}_kills100',
                             f'{p}_banks100', f'{p}_bankGems100', f'{p}_recall100b', f'{p}_shops100b', f'{p}_wards100', f'{p}_dmgOut100', f'{p}_goldIn100'])

if 'opening' in secs:
    table('opening', ['firstContact', 'firstHitMed', 'firstCap', 'firstMidCap', 'firstTheirCap', 'firstKill', 'firstDeath', 'firstBank', 'adv20', 'adv40', 'adv60', 'adv100',
                      'caps_r100', 'capGems_r100', 'caps_r200', 'capGems_r200', 'caps_r300', 'capGems_r300', 'sub200', 'sub300', 'maxHp300', 'firstGroupCls', 'firstGroupZone', 'firstGroupHitters'])

if 'econ' in secs:
    table('economy', ['tot_caps', 'tot_capGems', 'caps1000', 'capGems1000', 'gemsPerCap', 'capZ_own', 'capZ_mid', 'capZ_their', 'capC_cluster', 'capC_wolf', 'capC_elk', 'capC_golem', 'capC_mono',
                      'capNear', 'capContested', 'tot_banks', 'gemsPerBank', 'tribRate', 'bigTrib', 'bigTribDone', 'bigBankShare', 'maxBankShare', 'bankOwnShare', 'bankMidShare',
                      'maxBag', 'maxBagType', 'topCapType', 'topCapShare', 'topBankType', 'topBankShare', 'bagLost', 'bagStolen', 'bagLostShare',
                      'tot_goldIn', 'tot_goldSpent', 'maxHp600', 'maxHp1000', 'shops1000b', 'recalls1000b', 'recallSpam', 'wards1000', 'wardsMidTheir', 'locks', 'locksGuard', 'locksOff'])

if 'fights' in secs:
    table('fights', ['deaths1000', 'kills1000', 'tot_deaths', 'tot_kills', 'tot_dmgOut', 'tot_dmgIn', 'all_dead', 'all_a_fight', 'all_a_farm', 'all_a_walk', 'all_a_idle', 'all_z_mid', 'all_z_their'])

if 'obj' in secs:
    print('\n### objective maps (S|O)')
    for k in ORDER:
        s = S.loc[k]
        o = O.loc[k]
        m = s.obj != ''
        print(f"{k}: games {m.sum()} W {int(s.win[m].sum())}; objCaps S {s.objCaps[m].mean():.2f} O {o.objCaps[m].mean():.2f}; golem S {s.golemCaps[m].mean():.2f} O {o.golemCaps[m].mean():.2f}; mono S {s.monoCaps[m].mean():.2f} O {o.monoCaps[m].mean():.2f};"
              f" games with an obj cap S {(s.objCaps[m] > 0).mean():.0%} O {(o.objCaps[m] > 0).mean():.0%}; first obj cap med S {s.objFirstCap[m].median()} O {o.objFirstCap[m].median()}; first obj hit med S {s.objFirstHit[m].median()} O {o.objFirstHit[m].median()}; hitters S {s.objHitters[m].mean():.2f}")
        mw = m & s.win
        ml = m & ~s.win
        print(f"     wins: objCaps S {s.objCaps[mw].mean():.2f} O {o.objCaps[mw].mean():.2f}; losses: S {s.objCaps[ml].mean():.2f} O {o.objCaps[ml].mean():.2f}")

if 'end' in secs:
    print('\n### endgame')
    for k in ORDER:
        s = S.loc[k]
        w = s[s.win]
        lb = w.lastBankGems
        fin = w.lastBankGems / 1000
        print(f"{k}: wins {len(w)}: last bank gems med {lb.median():.0f} mean {lb.mean():.0f}; last bank >= 150 in {(lb >= 150).mean():.0%}; >= 300 {(lb >= 300).mean():.0%};"
              f" last bank type {w.lastBankType.value_counts().head(3).to_dict()}; bigBankShare {w.bigBankShare.mean():.2f}; final round med {w.final.median():.0f}")
        l = s[~s.win]
        ol = O.loc[k][~s.win]
        print(f"     losses {len(l)}: opp last bank med {ol.lastBankGems.median():.0f}, >=150 {(ol.lastBankGems >= 150).mean():.0%}; S score at end med {l.scoreS.median():.0f}; S carry at r600 {l.carry600.mean():.0f}")

if 'classes' in secs:
    print('\n### wins by class: team size x map size')
    for k in ORDER:
        s = S.loc[k]
        tab = s.groupby(['n', 'size']).win.agg(['sum', 'count'])
        print(k, '; '.join(f"{i[0]}p {i[1]}: {int(r['sum'])}/{int(r['count'])}" for i, r in tab.iterrows()))

if 'distinct' in secs:
    print('\n### distinctive features: team mean (S) vs the other five study teams (S), in SDs of the pooled S distribution')
    feats = [c for c in df.columns if df[c].dtype != object and c not in ('win', 'n', 'final', 'W', 'H', 's2s', 'midShareMap', 'scoreS', 'scoreO', 'side')]
    SS = df[df.X == 'S']
    res = {}
    for f in feats:
        col = SS[f].astype(float)
        sd = col.std()
        if not sd or np.isnan(sd):
            continue
        for k in ORDER:
            a = col[SS.key == k].mean()
            b = col[SS.key != k].mean()
            res.setdefault(k, []).append(((a - b) / sd, f, a, b))
    for k in ORDER:
        r = sorted([x for x in res[k] if not np.isnan(x[0])], key=lambda x: -abs(x[0]))[:40]
        print(f'\n{k}:')
        for z, f, a, b in r:
            print(f'   {f:22s} z {z:+.2f}  team {fmt(a)}  others {fmt(b)}')
