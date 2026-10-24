# Opening analysis tables from tools/top2/opening/open_flat.py output (teamgame.csv, bodies.csv, caps.csv, decisions.csv, banktrips.csv,
# eng.csv).   python tools/top2/opening/open_an.py FLATDIR [section...]
# Sections: teams (study vs opponents per team), wl (study wins vs losses), pooled (winner vs loser over unique games, P(W>L)),
#           strata (by map size / team size / camp mix), first (first hits per body), caps, bank, fight, cohesion, lead (win rate when ahead).
import sys, os
import numpy as np, pandas as pd

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 80); pd.set_option('display.max_rows', 1000)
D = sys.argv[1]
SECS = sys.argv[2:] or ['teams', 'wl', 'pooled', 'lead', 'strata', 'first', 'caps', 'bank', 'fight', 'cohesion']
tg = pd.read_csv(os.path.join(D, 'teamgame.csv'))
ORDER = ['pbg', 'ifish', 'pantheon', 'coo', 'cm', 'nyx']
keys = [k for k in ORDER if k in set(tg.key)]

def sizecls(a):
    return 'S' if a <= 1400 else ('M' if a <= 2600 else 'L')
tg['size'] = tg.area.map(sizecls)
tg['nb'] = tg.n.clip(upper=5)

def paired(df, m):
    """study vs opp in the same game: arrays aligned by (key, match)."""
    a = df[df.study == 1].set_index(['key', 'match'])[m]
    b = df[df.study == 0].set_index(['key', 'match'])[m]
    j = pd.concat([a.rename('s'), b.rename('o')], axis=1)
    return j

def pgt(x, y):
    ok = ~(pd.isna(x) | pd.isna(y))
    x, y = x[ok], y[ok]
    if len(x) == 0: return np.nan
    return ((x > y).sum() + 0.5 * (x == y).sum()) / len(x)

def fmt(v, nd=1):
    if v is None or (isinstance(v, float) and np.isnan(v)): return '-'
    if isinstance(v, (int, np.integer)): return str(v)
    if abs(v) >= 100: return f'{v:.0f}'
    return f'{v:.{nd}f}' if abs(v) >= 1 else f'{v:.2f}'

METRICS = [
    ('first_move_med', 'first move (median body)'), ('first_hit_team', 'first camp hit (team)'), ('first_hit_med', 'first camp hit (median body)'),
    ('hit_d_med', 'walk dist to 1st hit group'), ('hit_nearest_share', 'share 1st hit = nearest group'), ('hit_zone_M', 'share 1st hit in mid zone'),
    ('hit_cls_elk', 'share 1st hit on elk group'), ('squads', 'opening squads (distinct 1st groups)'), ('squad_max_share', 'largest squad / bodies'),
    ('first_cap_r', 'first capture round'), ('first_cap_gems', 'first capture gems'), ('first_mid_r', 'first body in mid band'),
    ('first_mid_cap_r', 'first mid-zone capture'), ('first_bank_r', 'first bank round'), ('first_bank_gems', 'first bank gems'),
    ('first_home_med', 'first arrival home (median body)'),
    ('caps_100', 'captures r100'), ('caps_200', 'captures r200'), ('caps_300', 'captures r300'),
    ('capGems_100', 'captured gems r100'), ('capGems_200', 'captured gems r200'), ('capGems_300', 'captured gems r300'),
    ('midGems_300', 'mid-zone gems r300'), ('ownGems_300', 'own-zone gems r300'), ('enemyGems_300', 'enemy-zone gems r300'),
    ('banked_100', 'banked r100'), ('banked_200', 'banked r200'), ('banked_300', 'banked r300'), ('banks_300', 'banks r300'),
    ('carried_300', 'carried r300'),
    ('gold_100', 'gold earned r100'), ('gold_200', 'gold earned r200'), ('gold_300', 'gold earned r300'),
    ('hp0', 'base max-HP sum (draft)'), ('hpGain_100', 'max-HP bought r100'), ('hpGain_200', 'max-HP bought r200'), ('hpGain_300', 'max-HP bought r300'),
    ('spent_200', 'gold spent r200'), ('spent_300', 'gold spent r300'), ('held_300', 'gold unspent r300'),
    ('kills_100', 'kills r100'), ('kills_300', 'kills r300'), ('deaths_100', 'deaths r100'), ('deaths_300', 'deaths r300'),
    ('bagLost_300', 'gems lost in bags r300'), ('homes_300', 'arrivals home r300'),
    ('w1-50_lcf', 'largest cluster share r1-50'), ('w51-100_lcf', 'largest cluster share r51-100'), ('w101-150_lcf', 'cluster share r101-150'),
    ('w151-200_lcf', 'cluster share r151-200'), ('w201-300_lcf', 'cluster share r201-300'),
    ('w1-50_disp', 'dispersion r1-50'), ('w51-100_disp', 'dispersion r51-100'), ('w201-300_disp', 'dispersion r201-300'),
    ('w1-50_mid', 'bodies in mid r1-50'), ('w51-100_mid', 'bodies in mid r51-100'), ('w101-150_mid', 'bodies in mid r101-150'),
    ('w151-200_mid', 'bodies in mid r151-200'), ('w201-300_mid', 'bodies in mid r201-300'),
    ('w1-50_sites', 'camp sites worked /10r r1-50'), ('w51-100_sites', 'sites r51-100'), ('w201-300_sites', 'sites r201-300'),
    ('ff_r', 'first fight round'), ('ff_me_first', 'struck first in 1st fight'), ('ff_result', '1st fight won (deaths)'),
    ('fk_me', 'got first kill (r<=300)'), ('fk_r', 'first kill round'), ('n_eng', 'engagements r<=300'), ('eng_me_first', 'share of engagements opened'),
]

def table_teams(df):
    out = []
    for m, lab in METRICS:
        if m not in df: continue
        row = {'metric': lab}
        for k in keys:
            j = paired(df[df.key == k], m)
            row[k] = f"{fmt(j.s.mean())} / {fmt(j.o.mean())} ({fmt(pgt(j.s, j.o))})"
        out.append(row)
    return pd.DataFrame(out).set_index('metric')

def table_wl(df):
    out = []
    for m, lab in METRICS:
        if m not in df: continue
        row = {'metric': lab}
        for k in keys:
            g = df[(df.key == k) & (df.study == 1)]
            w, l = g[g.won == 1][m], g[g.won == 0][m]
            row[k] = f"{fmt(w.mean())} / {fmt(l.mean())}"
        out.append(row)
    return pd.DataFrame(out).set_index('metric')

def unique_games(df):
    # one row pair per match: prefer the first study key that has it
    seen = set(); keep = []
    for (k, mt), g in df.groupby(['key', 'match'], sort=False):
        if mt in seen: continue
        seen.add(mt); keep.append(g)
    return pd.concat(keep)

def table_pooled(df, metrics=METRICS):
    u = unique_games(df)
    W = u[u.won == 1].set_index('match'); L = u[u.won == 0].set_index('match')
    out = []
    for m, lab in metrics:
        if m not in u: continue
        x, y = W[m], L.loc[W.index, m]
        out.append({'metric': lab, 'winner': fmt(x.mean()), 'loser': fmt(y.mean()), 'P(W>L)': fmt(pgt(x, y)),
                    'n': int((~(x.isna() | y.isna())).sum())})
    return pd.DataFrame(out).set_index('metric'), len(W)

def lead_table(df, ms):
    """win rate of the team ahead in metric m (ties excluded), pooled unique games, and per study team (study ahead -> study win rate)."""
    u = unique_games(df)
    out = []
    for m, better in ms:
        a = u[u.t == 0].set_index('match'); b = u[u.t == 1].set_index('match').loc[a.index]
        x, y, wa = a[m], b[m], a.won
        ok = ~(x.isna() | y.isna()) & (x != y)
        ahead_a = (x > y) if better == 'high' else (x < y)
        wins_ahead = ((ahead_a & (wa == 1)) | (~ahead_a & (wa == 0)))[ok]
        row = {'metric': m, 'n': int(ok.sum()), 'ahead wins': fmt(wins_ahead.mean())}
        for k in keys:
            g = df[df.key == k]
            j = paired(g, m); w = g[g.study == 1].set_index(['key', 'match']).won
            ok2 = ~(j.s.isna() | j.o.isna()) & (j.s != j.o)
            ah = (j.s > j.o) if better == 'high' else (j.s < j.o)
            row[k] = f"{fmt(w[ok2 & ah].mean())}|{fmt(w[ok2 & ~ah].mean())} ({int((ok2 & ah).sum())}/{int((ok2 & ~ah).sum())})"
        out.append(row)
    return pd.DataFrame(out).set_index('metric')

if 'teams' in SECS:
    s = tg[tg.study == 1]
    print('== study teams: games, win rate, bodies')
    print(s.groupby('key').agg(n=('won', 'size'), wr=('won', 'mean'), bodies=('n', 'mean'), opp_bodies=('n_opp', 'mean')).loc[keys].round(2))
    print('\n== study / opponent means in the same games (P(study > opp), ties 0.5)')
    print(table_teams(tg))
if 'wl' in SECS:
    print('\n== study team metric: in its wins / in its losses')
    print(tg[tg.study == 1].groupby('key').won.agg(['sum', 'size']).loc[keys].T)
    print(table_wl(tg))
if 'pooled' in SECS:
    t, n = table_pooled(tg)
    print(f'\n== pooled unique games (n={n}): winner / loser means, P(W>L)')
    print(t)
if 'lead' in SECS:
    ms = [('first_hit_team', 'low'), ('first_cap_r', 'low'), ('first_mid_r', 'low'), ('first_mid_cap_r', 'low'), ('first_bank_r', 'low'),
          ('capGems_100', 'high'), ('capGems_200', 'high'), ('capGems_300', 'high'), ('midGems_300', 'high'), ('banked_200', 'high'), ('banked_300', 'high'),
          ('gold_100', 'high'), ('gold_200', 'high'), ('gold_300', 'high'), ('hpGain_200', 'high'), ('hpGain_300', 'high'),
          ('kills_300', 'high'), ('deaths_300', 'low'), ('w1-50_mid', 'high'), ('w51-100_mid', 'high'), ('w201-300_mid', 'high'),
          ('w1-50_lcf', 'high'), ('w51-100_lcf', 'high'), ('w201-300_lcf', 'high')]
    print('\n== win rate of the team ahead (pooled unique games, ties excluded); per study team: win% when study ahead | behind (n)')
    print(lead_table(tg, ms))

STRATA_M = [('first_hit_team', 'first hit (team)'), ('hit_d_med', 'walk to 1st group'), ('hit_cls_elk', '1st hit elk share'),
            ('squad_max_share', 'largest squad share'), ('first_cap_r', 'first capture'), ('first_mid_r', 'first mid entry'),
            ('first_mid_cap_r', 'first mid capture'), ('first_bank_r', 'first bank'), ('first_bank_gems', 'first bank gems'),
            ('capGems_300', 'cap gems r300'), ('midGems_300', 'mid gems r300'), ('gold_300', 'gold r300'), ('hpGain_300', 'HP bought r300'),
            ('banked_300', 'banked r300'), ('kills_300', 'kills r300'), ('ff_r', 'first fight round'), ('fk_r', 'first kill round'),
            ('w51-100_lcf', 'cluster share r51-100'), ('w51-100_mid', 'mid bodies r51-100'), ('n_eng', 'engagements r<=300')]

def strata(df):
    u = unique_games(df)
    u['mixcls'] = np.where(u.mono > 0, 'mono', np.where(u.golem > 0, 'golem', 'elk/wolf only'))
    u['midcls'] = pd.cut(u.midShare, [-0.01, 0.45, 0.75, 1.01], labels=['mid<0.45', 'mid0.45-0.75', 'mid>0.75'])
    # team size: per team row (both teams of every unique game), metric means and win rate by own body count vs opponent body count
    print('\n== by team size (bodies; Cassi&Issac = 2): per team mean, win rate; rows = own bodies, cols = opponent bodies')
    wr = u.pivot_table(index='n', columns='n_opp', values='won', aggfunc=['mean', 'size'])
    print(wr.round(2))
    out = []
    for m, lab in STRATA_M:
        row = {'metric': lab}
        for v, g in u.groupby('n'):
            row[f'n={v} ({len(g)})'] = f"{fmt(g[g.won == 1][m].mean())}/{fmt(g[g.won == 0][m].mean())}"
        out.append(row)
    print('per own team size: mean in wins / in losses')
    print(pd.DataFrame(out).set_index('metric'))
    for col in ['size', 'mixcls', 'midcls']:
        print(f'\n== by {col}: winner / loser means (P(W>L)); n games')
        out = []
        for m, lab in STRATA_M:
            row = {'metric': lab}
            for v, g in u.groupby(col, observed=True):
                W = g[g.won == 1].set_index('match'); L = g[g.won == 0].set_index('match')
                L = L.loc[W.index]
                row[f'{v} (n={len(W)})'] = f"{fmt(W[m].mean())}/{fmt(L[m].mean())} ({fmt(pgt(W[m], L[m]))})"
            out.append(row)
        print(pd.DataFrame(out).set_index('metric'))

if 'strata' in SECS:
    strata(tg)

CHOICES = ['first_move_med', 'first_hit_med', 'hit_d_med', 'hit_nearest_share', 'hit_zone_M', 'hit_cls_elk', 'hit_vrank_med', 'squads',
           'squad_max_share', 'w1-50_lcf', 'w51-100_lcf', 'w101-150_lcf', 'w201-300_lcf', 'w51-100_disp', 'first_mid_r', 'w1-50_mid',
           'w51-100_mid', 'w101-150_mid', 'w201-300_mid', 'w1-50_sites', 'w51-100_sites', 'first_cap_r', 'first_bank_r', 'first_bank_gems',
           'banks_300', 'carried_300', 'homes_300', 'first_home_med', 'first_shop_med', 'hpGain_100', 'hpGain_200', 'spent_200', 'held_300',
           'ff_me_first', 'eng_me_first', 'n_eng']
OUTS = ['capGems_300', 'midGems_300', 'gold_300', 'hpGain_300', 'banked_300', 'kd_300', 'won']

def choices(df):
    """within-game differences (team 0 - team 1): Spearman correlation of each choice difference with outcome differences."""
    from scipy.stats import spearmanr
    u = unique_games(df).copy()
    u['kd_300'] = u.kills_300 - u.deaths_300
    a = u[u.t == 0].set_index('match'); b = u[u.t == 1].set_index('match').loc[a.index]
    out = []
    for c in CHOICES:
        row = {'choice diff': c}
        for o in OUTS:
            x = a[c] - b[c]; y = a[o] - b[o] if o != 'won' else a[o]
            ok = ~(x.isna() | y.isna())
            if ok.sum() < 30: row[o] = '-'; continue
            rho, p = spearmanr(x[ok], y[ok])
            row[o] = f"{rho:+.2f}{'*' if p < 0.01 else ''}"
        row['n'] = int((~(a[c] - b[c]).isna()).sum())
        out.append(row)
    print('\n== within-game differences (team0 - team1, unique games): Spearman rho of choice diff vs outcome diff (* p<0.01)')
    print(pd.DataFrame(out).set_index('choice diff'))

if 'choices' in SECS:
    choices(tg)

def ugames(df):
    u = unique_games(df)
    a = u[u.t == 0].set_index('match'); b = u[u.t == 1].set_index('match').loc[a.index]
    return u, a, b

if 'ts' in SECS:
    ts = pd.read_csv(os.path.join(D, 'ts.csv'))
    u, a, b = ugames(tg)
    km = u[['key', 'match']].drop_duplicates()
    t2 = ts.merge(km, on=['key', 'match'])
    w = t2[t2.won == 1].set_index(['match', 'r']); l = t2[t2.won == 0].set_index(['match', 'r'])
    j = w.join(l, lsuffix='_w', rsuffix='_l', how='inner')
    out = []
    for r, g in j.groupby(level='r'):
        if r not in (20, 40, 50, 60, 80, 100, 150, 200, 250, 300): continue
        row = {'r': r}
        for c in ['gold', 'capGems', 'midGems', 'banked', 'kills', 'deaths', 'hpGain', 'mid', 'lcf', 'alive']:
            row[c] = f"{g[c + '_w'].mean():.1f}/{g[c + '_l'].mean():.1f}"
        out.append(row)
    print('\n== winner / loser means by round (unique games)')
    print(pd.DataFrame(out).set_index('r'))

if 'buckets' in SECS:
    u, a, b = ugames(tg)
    def bucket(lab, diff, bins, labels):
        x = pd.cut(diff, bins, labels=labels)
        r = pd.DataFrame({'b': x, 'w': a.won}).groupby('b', observed=True).w.agg(['mean', 'size']).round(2).T
        print(f'\n== {lab} (team0 - team1) -> team0 win rate'); print(r)
    bucket('gold earned r100', a.gold_100 - b.gold_100, [-9999, -200, -100, -30, 30, 100, 200, 9999], ['<-200', '-200..-100', '-100..-30', '~0', '30..100', '100..200', '>200'])
    bucket('gold earned r200', a.gold_200 - b.gold_200, [-9999, -300, -150, -50, 50, 150, 300, 9999], ['<-300', '-300..-150', '-150..-50', '~0', '50..150', '150..300', '>300'])
    bucket('captured gems r200', a.capGems_200 - b.capGems_200, [-9999, -60, -30, -10, 10, 30, 60, 9999], ['<-60', '-60..-30', '-30..-10', '~0', '10..30', '30..60', '>60'])
    bucket('mid-zone gems r300', a.midGems_300 - b.midGems_300, [-9999, -60, -30, -10, 10, 30, 60, 9999], ['<-60', '-60..-30', '-30..-10', '~0', '10..30', '30..60', '>60'])
    bucket('deaths r100', a.deaths_100 - b.deaths_100, [-9, -1.5, -0.5, 0.5, 1.5, 9], ['<=-2', '-1', '0', '+1', '>=+2'])
    bucket('bodies in mid band, mean r51-150', (a['w51-100_mid'] + a['w101-150_mid']) / 2 - (b['w51-100_mid'] + b['w101-150_mid']) / 2,
           [-9, -1, -0.5, -0.15, 0.15, 0.5, 1, 9], ['<-1', '-1..-0.5', '-0.5..-0.15', '~0', '0.15..0.5', '0.5..1', '>1'])
    for s_, g in a.groupby('size'):
        x = g[~g.fk_me.isna()]
        print(f'first kill r<=300, size {s_}: n {len(x)}, killer team wins {((x.fk_me == 1) & (x.won == 1) | (x.fk_me == 0) & (x.won == 0)).mean():.2f}; no kill by r300 in {int(g.fk_me.isna().sum())}')
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    def lr(feats, lab):
        X = pd.DataFrame({f: (a[f].fillna(a[f].median()) - b[f].fillna(b[f].median())) for f in feats}); X = (X - X.mean()) / X.std()
        m = LogisticRegression(max_iter=1000); acc = cross_val_score(m, X, a.won.values, cv=10).mean(); m.fit(X, a.won.values)
        co = pd.Series(m.coef_[0], index=feats).sort_values(key=abs, ascending=False)
        print(f'\n== logistic win model, {lab}: 10-fold CV accuracy {acc:.3f}; standardized coefficients'); print(co.round(2).to_string())
    lr(['first_hit_med', 'hit_d_med', 'hit_nearest_share', 'hit_zone_M', 'hit_cls_elk', 'squad_max_share', 'w1-50_lcf', 'w51-100_lcf', 'w1-50_mid',
        'w51-100_mid', 'first_cap_r', 'ff_me_first'], 'opening choices r<=100')
    lr(['gold_100', 'capGems_100', 'midGems_100', 'kills_100', 'deaths_100', 'banked_100', 'hpGain_100'], 'state at r100')
    lr(['gold_300', 'capGems_300', 'midGems_300', 'kills_300', 'deaths_300', 'banked_300', 'hpGain_300', 'carried_300'], 'state at r300')

if 'exploit' in SECS:
    rows = []
    for key in keys:
        g = tg[tg.key == key]
        a = g[g.study == 1].set_index('match'); b = g[g.study == 0].set_index('match').loc[a.index]
        def wr(mask):
            m = mask.fillna(False)
            return f"{a.won[m].mean():.2f} ({int(m.sum())})" if m.sum() else '-'
        rows.append(dict(key=key, all=f"{a.won.mean():.2f} ({len(a)})", opp_first_kill=wr(a.fk_me == 0), own_first_kill=wr(a.fk_me == 1),
                         opp_struck_first=wr(a.ff_me_first == 0), own_struck_first=wr(a.ff_me_first == 1),
                         own_more_deaths_r100=wr(a.deaths_100 > b.deaths_100), opp_more_deaths_r100=wr(b.deaths_100 > a.deaths_100),
                         opp_gold_r100_plus100=wr(b.gold_100 - a.gold_100 >= 100), own_gold_r100_plus100=wr(a.gold_100 - b.gold_100 >= 100),
                         opp_mid_presence_plus1=wr((b['w51-100_mid'] + b['w101-150_mid']) - (a['w51-100_mid'] + a['w101-150_mid']) >= 1),
                         opp_midgems_r300_plus30=wr(b.midGems_300 - a.midGems_300 >= 30), own_midgems_r300_plus30=wr(a.midGems_300 - b.midGems_300 >= 30),
                         opp_hp_bought_r200_plus300=wr(b.hpGain_200 - a.hpGain_200 >= 300)))
    print('\n== study-team win rate (n) conditional on opening events'); print(pd.DataFrame(rows).set_index('key').T)
    print('\n== study team metric in its wins / in its losses, and its opponent in those games')
    for key in keys:
        g = tg[tg.key == key]
        a = g[g.study == 1].set_index('match'); b = g[g.study == 0].set_index('match').loc[a.index]
        ms = ['capGems_300', 'midGems_300', 'ownGems_300', 'gold_100', 'gold_300', 'hpGain_200', 'kills_100', 'deaths_100', 'kills_300', 'deaths_300',
              'banked_300', 'carried_300', 'first_mid2_r', 'w51-100_mid', 'w51-100_lcf']
        out = [dict(metric=m, win_own=a[a.won == 1][m].mean(), win_opp=b[a.won == 1][m].mean(), loss_own=a[a.won == 0][m].mean(), loss_opp=b[a.won == 0][m].mean()) for m in ms]
        print(f'-- {key}: wins {int((a.won == 1).sum())}, losses {int((a.won == 0).sum())}')
        print(pd.DataFrame(out).set_index('metric').round(1).T.to_string())

if 'caps' in SECS:
    c = pd.read_csv(os.path.join(D, 'caps.csv'))
    cu = c.drop_duplicates(['match', 't', 'r', 'cls', 'gems'])
    for cls, mx in [('elk', 6), ('wolf', 5), ('gem', 3), ('golem', 6)]:
        x = cu[(cu.cls == cls) & (cu.contested == False)]
        print(f'\n== {cls}-group captures r<=300 (uncontested, unique games): first own hit -> capture rounds by own hitters')
        print(x.groupby(x.hitters.clip(upper=mx)).agg(n=('killRounds', 'size'), med=('killRounds', 'median'), q25=('killRounds', lambda s: s.quantile(.25)),
              q75=('killRounds', lambda s: s.quantile(.75)), gems=('gems', 'median')).round(1))
    c['grp'] = np.where(c.study == 1, c.key, 'opponents')
    rows = []
    for g, df in c.groupby('grp'):
        ng = tg[(tg.study == (0 if g == 'opponents' else 1)) & ((tg.key == g) if g != 'opponents' else True)].shape[0]
        for cls, d2 in df.groupby('cls'):
            rows.append(dict(grp=g, cls=cls, caps_per_game=len(d2) / ng, gems_per_cap=d2.gems.mean(), hitters=d2.hitters.mean(), split=d2.split.mean(),
                             killR=d2.killRounds.median(), contested=d2.contested.mean()))
    print('\n== captures r<=300 per team-game by camp class'); print(pd.DataFrame(rows).set_index(['cls', 'grp']).round(2).sort_index())
    u = unique_games(tg)
    rows = []
    for w, df in cu.merge(u[['match', 't']], on=['match', 't']).groupby('won'):
        ng = (u.won == w).sum()
        for z, d2 in df.groupby('zone'):
            rows.append(dict(won=w, zone=z, caps_per_game=len(d2) / ng, gems_per_cap=d2.gems.mean(), hitters=d2.hitters.mean(), contested=d2.contested.mean()))
    print('\n== captures r<=300 by zone, winners vs losers'); print(pd.DataFrame(rows).set_index(['zone', 'won']).round(2).sort_index())

if 'bank' in SECS:
    dd = pd.read_csv(os.path.join(D, 'decisions.csv'))
    dd['grp'] = np.where(dd.study == 1, dd.key, 'opponents')
    dd['bag_b'] = pd.cut(dd.bag, [0, 15, 30, 50, 80, 1000], labels=['1-15', '16-30', '31-50', '51-80', '81+'])
    dd['altar_b'] = pd.cut(dd.ad, [-2, 5, 10, 20, 1000], labels=['<=5', '6-10', '11-20', '>20'])
    print('\n== after a capture (r<=300): next action shares (home includes a recall that lands in the capture round)')
    print(dd.groupby('grp').next.value_counts(normalize=True).unstack().round(2))
    for g in ['all'] + keys + ['opponents']:
        x = dd if g == 'all' else dd[dd.grp == g]
        print(f'\n-- {g}: P(bank next) by carried bag x walking distance to the nearest altar (n)')
        print(x.pivot_table(index='bag_b', columns='altar_b', values='next', aggfunc=lambda s: f"{(s == 'bank').mean():.2f} ({len(s)})", observed=True))
    bt = pd.read_csv(os.path.join(D, 'banktrips.csv'))
    bt['viaHome'] = bt.viaHome.map({True: 1, False: 0, 'True': 1, 'False': 0})
    bt['grp'] = np.where(bt.study == 1, bt.key, 'opponents')
    print('\n== banks r<=300: count, gems per bank, rounds since the capture, capture tile -> altar walk, share via a home visit')
    print(bt.groupby('grp').agg(banks=('gems', 'size'), gems_med=('gems', 'median'), gems_mean=('gems', 'mean'), from_cap=('fromCapR', 'median'),
          cap_altar_walk=('capAd', 'median'), via_home=('viaHome', 'mean')).round(2))

if 'fight' in SECS:
    e = pd.read_csv(os.path.join(D, 'eng.csv'))
    fk = e.drop_duplicates('match')[['match', 'key']]
    u = e.merge(fk, on=['match', 'key'])
    u['kill'] = (u.dead_me + u.dead_opp) > 0
    s = u.copy()
    s['s_dn'] = np.where(s.me_first == 1, s.near_me - s.near_opp, s.near_opp - s.near_me)
    s['s_res'] = np.where(s.me_first == 1, np.sign(s.dead_opp - s.dead_me), np.sign(s.dead_me - s.dead_opp))
    s['s_hp'] = np.where(s.me_first == 1, s.nearHp_me - s.nearHp_opp, s.nearHp_opp - s.nearHp_me)
    k = s[s.kill].copy()
    print(f'\n== engagements r<=300 (unique games): {len(u)}, with a kill {int(u.kill.sum())}; striker wins {(k.s_res > 0).mean():.2f}, loses {(k.s_res < 0).mean():.2f}')
    k['dn_b'] = pd.cut(k.s_dn, [-10, -2, -1, 0, 1, 10], labels=['<=-2', '-1', '0', '+1', '>=+2'])
    print('-- by local numbers (striker bodies within 8 of the first victim - enemy bodies)')
    print(k.groupby('dn_b', observed=True).s_res.agg(win=lambda x: (x > 0).mean(), lose=lambda x: (x < 0).mean(), n='size').round(2))
    k['hp_b'] = pd.cut(k.s_hp, [-1e9, -1500, -500, 500, 1500, 1e9], labels=['<-1500', '-1500..-500', '+-500', '500..1500', '>1500'])
    print('-- by local current-HP difference')
    print(k.groupby('hp_b', observed=True).s_res.agg(win=lambda x: (x > 0).mean(), lose=lambda x: (x < 0).mean(), n='size').round(2))
    f = u[u.idx == 0].merge(tg[['match', 'area']].drop_duplicates('match'), on='match')
    f['size'] = np.where(f.area <= 1400, 'S', np.where(f.area <= 2600, 'M', 'L'))
    print('\n== first engagement per game by map size')
    print(f.groupby('size').agg(n=('r0', 'size'), q25=('r0', lambda x: x.quantile(.25)), med=('r0', 'median'), q75=('r0', lambda x: x.quantile(.75)),
          has_kill=('kill', 'mean'), in_mid=('zone_striker', lambda x: (x == 'M').mean())).round(2))
    print('striker types of first engagements:', f.striker_type.value_counts().head(8).to_dict())
    rows = []
    for key, g in e.groupby('key'):
        gk = g[(g.dead_me + g.dead_opp) > 0]
        rows.append(dict(key=key, eng_per_game=len(g) / g.match.nunique(), opened=g.me_first.mean(), kill_eng_per_game=len(gk) / g.match.nunique(),
                         won=(gk.dead_opp > gk.dead_me).mean(), lost=(gk.dead_opp < gk.dead_me).mean(),
                         numbers_when_opening=(g[g.me_first == 1].near_me - g[g.me_first == 1].near_opp).mean(),
                         numbers_when_hit=(g[g.me_first == 0].near_me - g[g.me_first == 0].near_opp).mean(),
                         won_opened=(gk.dead_opp > gk.dead_me)[gk.me_first == 1].mean(), won_received=(gk.dead_opp > gk.dead_me)[gk.me_first == 0].mean()))
    print('\n== per study team, engagements r<=300'); print(pd.DataFrame(rows).set_index('key').round(2))

if 'firsts' in SECS:
    bb = pd.read_csv(os.path.join(D, 'bodies.csv'))
    bb['grp'] = np.where(bb.study == 1, bb.key, 'opponents')
    print('\n== per body (medians): first move, first camp hit, walk distance, zone of the first group, first capture / bank / mid / home / shop')
    print(bb.groupby('grp').agg(moves_r1=('firstMove', lambda s: (s <= 1).mean()), hit_r=('hit_r', 'median'), hit_walk=('hit_d', 'median'),
          own=('hit_zone', lambda s: (s == 'O').mean()), mid=('hit_zone', lambda s: (s == 'M').mean()), cap_r=('cap_r', 'median'),
          no_cap300=('cap_r', lambda s: s.isna().mean()), bank_r=('bank_r', 'median'), mid_r=('mid_r', 'median'), home_r=('home_r', 'median'),
          shop_r=('shop_r', 'median'), died300=('death_r', lambda s: s.notna().mean())).round(2))
    t = tg[tg.study == 1].copy(); t['picks'] = tg.groupby('map').n.transform(lambda s: s.mode()[0])
    ms = ['won', 'first_hit_team', 'hit_d_med', 'squad_max_share', 'first_cap_r', 'first_mid2_r', 'first_bank_r', 'ff_r', 'midGems_300', 'gold_300',
          'w51-100_lcf', 'w51-100_mid']
    for col in ['size', 'picks']:
        x = t.groupby(['key', col])[ms].mean().round(2); x['n'] = t.groupby(['key', col]).size()
        print(f'\n== study teams by {col}'); print(x)
