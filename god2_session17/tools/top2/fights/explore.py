# Follow-up checks for experiments/top2/an_fights.md over the flattened situation records (tools/top2/fights/flat.py):
#   Prism big-bag tributes (timing, score, outcome), loaded-Prism deaths, capture-recall combos, guard locks, engagement logit,
#   partial game-level correlations, example picks (file + round) for the report.
#   python tools/top2/fights/explore.py C:/battlecode/cache/top2_fights [section ...]
import os, sys
import numpy as np
import pandas as pd

D = sys.argv[1]
SECS = set(sys.argv[2:])
F = {k: pd.read_pickle(os.path.join(D, 'flat', f'{k}.pkl')) for k in ['cap', 'bnk', 'dth', 'eng', 'rcl', 'pun', 'lck', 'arr', 'sum', 'low', 'chs', 'omt']}
KEYS = ['pbg', 'ifish', 'cm', 'pantheon', 'coo', 'nyx']
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40); pd.set_option('display.max_rows', 200)


def sec(name):
    return not SECS or name in SECS


if sec('prism'):
    b = F['bnk']
    p = b[(b.ty == 'Prism') & (b.bag >= 100)].copy()
    print('\n## Prism tributes with bag >= 100: by team group')
    g = p.groupby(['key', 'grp']).agg(n=('bag', 'size'), bag_med=('bag', 'median'), r_med=('r', 'median'), done=('res', lambda s: (s == 'done').mean()),
                                       hit=('hitIn', lambda s: (s > 0).mean()), enemy8=('nE', lambda s: (s > 0).mean()), dur_med=('dur', 'median'))
    print(g.round(2).to_string())
    print('\noutcomes (all groups):', p.res.value_counts().to_dict())
    big = b.sort_values('bag', ascending=False).head(8)[['key', 'game', 'grp', 'ty', 'r', 'bag', 'dur', 'res', 'nE', 'hitIn']]
    print('\nbiggest tributes:\n', big.to_string())
    # did the Prism tribute decide the game? score of the tributing team before vs after
    d = F['dth']
    lp = d[(d.ty == 'Prism') & (d.bag >= 100)]
    print('\n## Loaded-Prism deaths (bag >= 100): per group, bag lost, killer, mode')
    print(lp.groupby(['key', 'grp']).agg(n=('bag', 'size'), bag_med=('bag', 'median'), bag_sum=('bag', 'sum')).to_string())
    print('killers:', lp.by.value_counts().head(8).to_dict())
    print('modes:', lp['mode'].value_counts().to_dict())
    print('isolated (no ally within 6):', (lp.nA6 == 0).mean().round(2), 'outnumbered within 6:', (lp.nE6 > lp.nA6 + 1).mean().round(2), 'n', len(lp))
    print('examples:\n', lp.sort_values('bag', ascending=False).head(6)[['key', 'game', 'grp', 'r', 'bag', 'by', 'mode', 'nA6', 'nE6', 'act']].to_string())

if sec('combo'):
    c = F['cap']
    print('\n## Capture-recall combos (capture lands while a recall channel runs)')
    print(c.groupby(['key', 'grp']).agg(caps=('rcNow', 'size'), combo=('rcNow', 'mean'), bag_med=('bag', 'median')).round(2).to_string())
    print('by champion (S, combo share):')
    x = c[c.grp == 'S']
    print(x.groupby(['key', 'ty']).rcNow.mean().round(2).unstack().to_string())
    ex = c[(c.key == 'nyx') & (c.grp == 'S') & (c.rcNow == 1)].head(5)[['game', 'ty', 'r', 'gain', 'bag', 'hd', 'nE']]
    print('nyx examples:\n', ex.to_string())
    ex = c[(c.key == 'pbg') & (c.grp == 'S') & (c.rcNow == 1)].head(3)[['game', 'ty', 'r', 'gain', 'bag', 'hd', 'nE']]
    print('pbg examples:\n', ex.to_string())

if sec('locks'):
    l = F['lck']
    print('\n## lock placements by champion and class (S)')
    print(l[l.grp == 'S'].groupby(['key', 'cls']).size().unstack(fill_value=0).to_string())
    print(l[(l.grp == 'S') & (l.key == 'cm')].head(5)[['game', 'ty', 'r', 'cls']].to_string())
    b = F['bnk']
    print('\ntribute outcome vs locks: share of tributes locked/stunned/killed by group')
    print(b.groupby(['key', 'grp']).res.value_counts(normalize=True).unstack(fill_value=0).round(3).to_string())

if sec('englogit'):
    import statsmodels.api as sm
    e = F['eng'].copy()
    e = e[e.dES != e.dEO]
    y = (e.dEO > e.dES).astype(int)
    X = pd.DataFrame({
        'log_mh_ratio': np.log(e.mhS.clip(lower=100) / e.mhO.clip(lower=100)),
        'log_hp_over_mh': np.log((e.hpS / e.mhS.clip(lower=1)).clip(lower=0.05) / (e.hpO / e.mhO.clip(lower=1)).clip(lower=0.05)),
        'S_started': e.sSt,
        'n_diff': e.nS - e.nO,
        'first3_share': e.dealt3S / (e.dealt3S + e.dealt3O).clip(lower=1),
        'focus_diff': e.focusS.fillna(0) - e.focusO.fillna(0),
        'stun3_diff': e.stun3S - e.stun3O,
        'casts_diff': e.castsS - e.castsO,
    })
    Xs = (X - X.mean()) / X.std()
    m = sm.Logit(y, sm.add_constant(Xs)).fit(disp=0)
    print('\n## Decisive engagements: logit of S winning (standardised coefficients), n =', len(y), 'pseudo R2', round(m.prsquared, 3))
    print(pd.DataFrame({'coef': m.params.round(2), 'z': m.tvalues.round(1)}).to_string())
    # without first3 (pre-fight state only)
    X2 = Xs.drop(columns=['first3_share', 'focus_diff', 'stun3_diff', 'casts_diff'])
    m2 = sm.Logit(y, sm.add_constant(X2)).fit(disp=0)
    print('\nPre-fight state only, pseudo R2', round(m2.prsquared, 3))
    print(pd.DataFrame({'coef': m2.params.round(2), 'z': m2.tvalues.round(1)}).to_string())
    # starter value at equal power: S started, |log mh ratio| < 0.15
    x = e[np.abs(np.log(e.mhS.clip(lower=100) / e.mhO.clip(lower=100))) < 0.15]
    print('\nEven power (|log mh ratio| < 0.15): S win% when S started', round((x[x.sSt == 1].dEO > x[x.sSt == 1].dES).mean() * 100, 1), 'n', (x.sSt == 1).sum(),
          '| when O started', round((x[x.sSt == 0].dEO > x[x.sSt == 0].dES).mean() * 100, 1), 'n', (x.sSt == 0).sum())

if sec('gamelogit'):
    import statsmodels.api as sm
    G = pd.read_pickle(os.path.join(D, 'flat', 'gamefeat.pkl'))
    feats = ['mh300', 'badStart', 'first3', 'firstStrike', 'punish4', 'lowRecall', 'chaseKill', 'underFight', 'bagLost', 'keepFarm', 'help8']
    X = pd.DataFrame({f: G[f + 'S'] - G[f + 'O'] for f in feats})
    ok = X.notna().all(axis=1)
    X = X[ok]; y = G.win[ok]
    Xs = (X - X.mean()) / X.std()
    m = sm.Logit(y, sm.add_constant(Xs)).fit(disp=0)
    print('\n## Games: logit of S winning on S-O decision features (standardised), n =', len(y), 'pseudo R2', round(m.prsquared, 3))
    print(pd.DataFrame({'coef': m.params.round(2), 'z': m.tvalues.round(1)}).to_string())

if sec('examples'):
    e = F['eng']
    print('\n## example engagements: S starts at even power with a spell opener and wins (one per key)')
    for k in KEYS:
        x = e[(e.key == k) & (e.sSt == 1) & (e.cast == 1) & (e.dEO >= 2) & (e.dES == 0)]
        if len(x):
            r = x.iloc[0]
            print(k, r.game, 'r', r.r0, '-', r.r1, 'opener', r.aTy, '->', r.vTy, 'mh', r.mhS, r.mhO, 'deaths', r.dES, r.dEO)
    r = F['rcl']
    x = r[(r.spam == 0) & (r.dn <= 2) & (r.res == 'killed')].head(4)
    print('\n## recall started with an enemy within 2 and killed:\n', x[['key', 'game', 'grp', 'ty', 'r', 'hpf', 'dn', 'nE']].to_string())
    p = F['pun']
    x = p[(p.kind == 'trib') & (p.lock > 0) & (p.res == 'locked')].head(4)
    print('\n## enemy tribute cancelled by a lock:\n', x[['key', 'game', 'grp', 'r', 'bag', 'chTy', 'dmin']].to_string())
    x = p[(p.kind == 'trib') & (p.stun > 0) & (p.res == 'stunned')].head(4)
    print('\n## enemy tribute cancelled by a stun:\n', x[['key', 'game', 'grp', 'r', 'bag', 'chTy', 'dmin']].to_string())
    a = F['arr']
    x = a[(a.key == 'cm') & (a.grp == 'S') & (a.hpA < 0.6 * a.hpE) & (a.a == 1) & (a.died20 == 1)].head(3)
    print('\n## cm keeps farming while weaker and dies:\n', x[['game', 'ty', 'r', 'hpA', 'hpE', 'nA', 'nE', 'dn', 'eTy']].to_string())
    ch = F['chs']
    x = ch[(ch.key == 'ifish') & (ch.grp == 'S') & (ch.res == 'kill') & (ch.len >= 6)].head(3)
    print('\n## ifish chase kills:\n', x[['game', 'aTy', 'vTy', 'r', 'len', 'hitsIn']].to_string())

if sec('arr5'):
    a = F['arr'].copy()
    a = a[a.dn <= 5]
    a['ratio'] = a.hpA / a.hpE.clip(lower=1)
    a['rb'] = pd.cut(a.ratio, [0, 0.6, 0.9, 1.2, 2.0, 1e9], labels=['<0.6', '0.6-0.9', '0.9-1.2', '1.2-2', '>=2'], right=False)
    ACTS = ['fight', 'farm', 'away', 'toward', 'hold', 'recall', 'bank', 'dead']
    print('\n## Enemy arrives within 5 of a farmer (fresh): action shares and outcome, pooled S / O and per study team (S)')
    rows = []
    for g in ('S', 'O'):
        for rb in ['<0.6', '0.6-0.9', '0.9-1.2', '1.2-2', '>=2']:
            x = a[(a.grp == g) & (a.rb == rb)]
            if len(x) < 20:
                continue
            vc = x.a.value_counts(normalize=True)
            rows.append({'grp': g, 'ratio': rb, 'n': len(x), **{ACTS[i]: round(vc.get(i, 0) * 100, 1) for i in (0, 1, 2, 4, 5)}, 'died20%': round(x.died20.mean() * 100, 1),
                         'own cap%': round((x.capBy == 0).mean() * 100, 1), 'enemy cap%': round((x.capBy == 1).mean() * 100, 1)})
    print(pd.DataFrame(rows).to_string())
    rows = []
    for k in KEYS:
        for g in ('S', 'O'):
            x = a[(a.key == k) & (a.grp == g)]
            vc = x.a.value_counts(normalize=True)
            w = x[x.ratio < 0.9]; vw = w.a.value_counts(normalize=True)
            rows.append({'key': k, 'grp': g, 'n': len(x), 'farm%': round(vc.get(1, 0) * 100, 1), 'fight%': round(vc.get(0, 0) * 100, 1), 'leave+recall%': round((vc.get(2, 0) + vc.get(5, 0)) * 100, 1),
                         'n weaker(<0.9)': len(w), 'weaker: farm%': round(vw.get(1, 0) * 100, 1), 'weaker: leave+recall%': round((vw.get(2, 0) + vw.get(5, 0)) * 100, 1),
                         'weaker: fight%': round(vw.get(0, 0) * 100, 1), 'weaker died20%': round(w.died20.mean() * 100, 1), 'died20%': round(x.died20.mean() * 100, 1)})
    print(pd.DataFrame(rows).to_string())

if sec('punout'):
    p = F['pun']
    x = p[(p.kind == 'trib') & (p.dmin <= 4)]
    print('\n## Enemy tribute with our body within 4: channel failure by our response (pooled)')
    for lab, cond in (('no hit, no stun, no lock', (x.dmg == 0) & (x.stun == 0) & (x.lock == 0)), ('hit only', (x.dmg > 0) & (x.stun == 0) & (x.lock == 0)),
                      ('stun', x.stun > 0), ('lock', x.lock > 0)):
        y = x[cond]
        print(f'  {lab:28s} n={len(y):5d} failed={((y.res != "done").mean() * 100):5.1f}% killed={y.killed.mean() * 100:5.1f}% bag med={y.bag.median()}')
    x = p[(p.kind == 'rec') & (p.dmin <= 4)]
    print('## Enemy recall with our body within 4: failure by response (pooled)')
    for lab, cond in (('no hit', x.dmg == 0), ('hit', x.dmg > 0)):
        y = x[cond]
        print(f'  {lab:28s} n={len(y):5d} failed={((y.res != "done").mean() * 100):5.1f}% killed={y.killed.mean() * 100:5.1f}%')

if sec('chase2'):
    ch = F['chs'].copy()
    ch['vb'] = pd.cut(ch.vHp, [0, 0.35, 0.7, 1.01], labels=['<35%', '35-70%', '>=70%'], right=False)
    print('\n## Chases: kill% and chaser-death% by target health at the start of the chase (pooled S / O)')
    print(ch.groupby(['grp', 'vb'], observed=True).agg(n=('len', 'size'), len_mean=('len', 'mean'), kill=('res', lambda s: (s == 'kill').mean()), chaser_died=('aDied10', 'mean'),
                                                     deeper=('deeper', 'median')).round(2).to_string())
    print(ch.groupby(['key', 'grp']).agg(n=('len', 'size'), vHp_med=('vHp', 'median'), aHp_med=('aHp', 'median'), zone_their=('z', lambda s: (s == 2).mean())).round(2).to_string())
    ch['lb'] = pd.cut(ch.len, [0, 3, 6, 10, 1000], labels=['1-2', '3-5', '6-9', '10+'], right=False)
    print(ch.groupby(['grp', 'lb'], observed=True).agg(n=('len', 'size'), kill=('res', lambda s: (s == 'kill').mean()), chaser_died=('aDied10', 'mean')).round(2).to_string())

if sec('farm4'):
    s = pd.read_pickle(os.path.join(D, 'flat', 'smp.pkl'))
    s = s[s.busy.isin([1, 2]) & (s.dn <= 4)].copy()
    s['ratio'] = s.hpA / s.hpE.clip(lower=1)
    s['rb'] = pd.cut(s.ratio, [0, 0.6, 0.9, 1.2, 2.0, 1e9], labels=['<0.6', '0.6-0.9', '0.9-1.2', '1.2-2', '>=2'], right=False)
    ACTS = ['fight', 'farm', 'away', 'toward', 'hold', 'recall', 'bank', 'dead']
    print('\n## Farming / capturing body with an enemy within 4 (decision samples): next 3 rounds, by hp ratio within 8 (pooled S / O)')
    rows = []
    for g in ('S', 'O'):
        for rb in ['<0.6', '0.6-0.9', '0.9-1.2', '1.2-2', '>=2']:
            x = s[(s.grp == g) & (s.rb == rb)]
            if len(x) < 30:
                continue
            vc = x.a.value_counts(normalize=True)
            rows.append({'grp': g, 'ratio': rb, 'n': len(x), **{ACTS[i] + '%': round(vc.get(i, 0) * 100, 1) for i in (0, 1, 2, 4, 5)}, 'died10%': round(x.died10.mean() * 100, 1),
                         'kills10/100': round(x.ek10.mean() * 100, 1)})
    print(pd.DataFrame(rows).to_string())
    rows = []
    for g in ('S', 'O'):
        for rb in ['<0.6', '0.6-0.9', '0.9-1.2', '1.2-2', '>=2']:
            for ai in (0, 1, 2):
                x = s[(s.grp == g) & (s.rb == rb) & (s.a == ai)]
                if len(x) < 30:
                    continue
                rows.append({'grp': g, 'ratio': rb, 'action': ACTS[ai], 'n': len(x), 'died10%': round(x.died10.mean() * 100, 1), 'kills10/100': round(x.ek10.mean() * 100, 1),
                             'net/100': round((x.ek10.mean() - x.died10.mean()) * 100, 1)})
    print(pd.DataFrame(rows).to_string())
    rows = []
    for k in KEYS:
        for g in ('S', 'O'):
            x = s[(s.key == k) & (s.grp == g)]
            vc = x.a.value_counts(normalize=True)
            w = x[x.ratio < 0.9]; vw = w.a.value_counts(normalize=True)
            st = x[x.ratio >= 0.9]; vs = st.a.value_counts(normalize=True)
            rows.append({'key': k, 'grp': g, 'n': len(x), 'weaker n': len(w), 'weaker fight/farm/leave+rc': f"{vw.get(0, 0) * 100:.0f}/{vw.get(1, 0) * 100:.0f}/{(vw.get(2, 0) + vw.get(5, 0)) * 100:.0f}",
                         'weaker died10%': round(w.died10.mean() * 100, 1), 'even+ fight/farm/leave+rc': f"{vs.get(0, 0) * 100:.0f}/{vs.get(1, 0) * 100:.0f}/{(vs.get(2, 0) + vs.get(5, 0)) * 100:.0f}",
                         'even+ died10%': round(st.died10.mean() * 100, 1)})
    print(pd.DataFrame(rows).to_string())
