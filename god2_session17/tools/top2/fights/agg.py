# Tables for experiments/top2/an_fights.md from the flattened situation records (tools/top2/fights/flat.py).
#   python tools/top2/fights/agg.py C:/battlecode/cache/top2_fights [section ...]  > tables.txt
# Groups: S = the study team (key), O = its opponents in the same games. ALL = the six study teams pooled.
import os, sys
import numpy as np
import pandas as pd

D = sys.argv[1]
SECS = set(sys.argv[2:])
KEYS = ['pbg', 'ifish', 'cm', 'pantheon', 'coo', 'nyx']
ACTS = ['fight', 'farm', 'away', 'toward', 'hold', 'recall', 'bank', 'dead']
F = {k: pd.read_pickle(os.path.join(D, 'flat', f'{k}.pkl')) for k in ['smp', 'arr', 'ast', 'cap', 'bnk', 'low', 'rcl', 'omt', 'pun', 'lck', 'eng', 'chs', 'dth', 'ctc', 'sum']}
NG = F['sum'].groupby('key').size().to_dict()
NG['ALL'] = len(F['sum'])


def md(df, floatfmt='{:.2f}'):
    cols = list(df.columns)
    out = ['| ' + ' | '.join(str(c) for c in cols) + ' |', '|' + '---|' * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                cells.append('' if np.isnan(v) else floatfmt.format(v))
            else:
                cells.append(str(v))
        out.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(out)


def show(title, df, **kw):
    print(f'\n### {title}\n')
    print(md(df, **kw))
    sys.stdout.flush()


def pools(df):
    """yield (label, sub-frame) for each study key's S and O and the pooled ALL S / ALL O"""
    for k in KEYS:
        for g in ('S', 'O'):
            yield f'{k}:{g}', k, g, df[(df.key == k) & (df.grp == g)]
    for g in ('S', 'O'):
        yield f'ALL:{g}', 'ALL', g, df[df.grp == g]


def bins(x, edges, labels):
    return pd.cut(x, edges, labels=labels, right=False)


def actshares(sub, col='a'):
    n = len(sub)
    c = sub[col].value_counts()
    return {ACTS[i]: (c.get(i, 0) / n * 100 if n else np.nan) for i in range(8)}


RB = [0, 0.6, 0.9, 1.2, 2.0, 1e9]
RL = ['<0.6', '0.6-0.9', '0.9-1.2', '1.2-2', '>=2']

# ------------------------------------------------------------------------------------------------ (0) data
if not SECS or '0' in SECS:
    s = F['sum']
    rows = []
    for k in KEYS:
        x = s[s.key == k]
        rows.append({'team': k, 'games': len(x), 'wins': int(x.win.sum()), 'win%': x.win.mean() * 100, 'deaths S': x.deathsS.mean(), 'deaths O': x.deathsO.mean(),
                     'kills S': x.killsS.mean(), 'camp deaths S': x.campDeathsS.mean(), 'camp deaths O': x.campDeathsO.mean(), 'bag lost S': x.bagLostS.mean(), 'bag lost O': x.bagLostO.mean(),
                     'maxBag S': x.maxBagS.median(), 'maxBag O': x.maxBagO.median(), 'banks S': x.banksS.mean(), 'banks O': x.banksO.mean(), 'dmgOut S': x.dmgOutS.mean(), 'dmgOut O': x.dmgOutO.mean(),
                     'campIn S': x.campInS.mean(), 'campIn O': x.campInO.mean(), 'mh300 S': x.mh300S.mean(), 'mh300 O': x.mh300O.mean(), 'locks S': x.locksS.mean(), 'locks O': x.locksO.mean(),
                     'spam S': x.spamS.mean(), 'spam O': x.spamO.mean()})
    show('0. Data and per-game summary (means per game; S = study team, O = its opponents)', pd.DataFrame(rows), floatfmt='{:.1f}')

# ------------------------------------------------------------------------------------------------ (a) an enemy comes within 8 while farming
if not SECS or 'a' in SECS:
    a = F['arr'].copy()
    a['ratio'] = a.hpA / a.hpE.clip(lower=1)
    a['rb'] = bins(a.ratio, RB, RL)
    rows = []
    for lab, k, g, sub in pools(a):
        if not len(sub):
            continue
        sh = actshares(sub)
        rows.append({'grp': lab, 'n': len(sub), 'n/game': len(sub) / NG[k], 'fight%': sh['fight'], 'farm%': sh['farm'], 'leave%': sh['away'] + sh['toward'] * 0, 'toward%': sh['toward'],
                     'hold%': sh['hold'], 'recall%': sh['recall'], 'bank%': sh['bank'], 'they hit first%': ((sub.eFirst >= 0) & ((sub.firstF < 0) | (sub.eFirst < sub.firstF))).mean() * 100,
                     'died20%': sub.died20.mean() * 100, 'own cap40%': (sub.capBy == 0).mean() * 100, 'enemy cap40%': (sub.capBy == 1).mean() * 100, 'kills20/100': sub.ek20.mean() * 100})
    show('a1. Enemy champion arrives within 8 of a farming / capturing body: action in the next 5 rounds and outcome', pd.DataFrame(rows), floatfmt='{:.1f}')
    rows = []
    for lab, k, g, sub in pools(a):
        if k not in ('ALL',) and k not in KEYS:
            continue
        for rb in RL:
            x = sub[sub.rb == rb]
            if len(x) < 15:
                continue
            sh = actshares(x)
            rows.append({'grp': lab, 'hp ratio within 8': rb, 'n': len(x), 'fight%': sh['fight'], 'farm%': sh['farm'], 'leave%': sh['away'], 'hold%': sh['hold'], 'recall%': sh['recall'],
                         'died20%': x.died20.mean() * 100, 'own cap%': (x.capBy == 0).mean() * 100, 'enemy cap%': (x.capBy == 1).mean() * 100, 'kills20/100': x.ek20.mean() * 100})
    show('a2. Same, by current-health ratio within 8 (allies incl. the farmer / enemies)', pd.DataFrame(rows), floatfmt='{:.1f}')
    # outcome by action at the same state, pooled S vs O
    rows = []
    for g in ('S', 'O'):
        for rb in RL:
            for ai in (0, 1, 2):
                x = a[(a.grp == g) & (a.rb == rb) & (a.a == ai)]
                if len(x) < 20:
                    continue
                rows.append({'grp': g, 'ratio': rb, 'action': ACTS[ai], 'n': len(x), 'died20%': x.died20.mean() * 100, 'own cap%': (x.capBy == 0).mean() * 100,
                             'enemy cap%': (x.capBy == 1).mean() * 100, 'kills20/100': x.ek20.mean() * 100, 'net (kills-deaths)/100': (x.ek20.mean() - x.died20.mean()) * 100})
    show('a3. Outcome by chosen action at the same health ratio (pooled over all six study teams S / their opponents O)', pd.DataFrame(rows), floatfmt='{:.1f}')
    # by bag carried and by numbers
    rows = []
    a['bagb'] = bins(a.bag, [0, 1, 50, 150, 1e9], ['0', '1-49', '50-149', '150+'])
    a['numd'] = np.sign(a.nA - a.nE)
    for lab, k, g, sub in pools(a):
        if k != 'ALL':
            continue
        for bb in ['0', '1-49', '50-149', '150+']:
            x = sub[sub.bagb == bb]
            if len(x) < 15:
                continue
            sh = actshares(x)
            rows.append({'grp': lab, 'bag': bb, 'n': len(x), 'fight%': sh['fight'], 'farm%': sh['farm'], 'leave%': sh['away'], 'recall%': sh['recall'], 'bank%': sh['bank'], 'died20%': x.died20.mean() * 100})
        for nd, nl in ((-1, 'fewer'), (0, 'equal'), (1, 'more')):
            x = sub[sub.numd == nd]
            if len(x) < 15:
                continue
            sh = actshares(x)
            rows.append({'grp': lab, 'bag': 'numbers ' + nl, 'n': len(x), 'fight%': sh['fight'], 'farm%': sh['farm'], 'leave%': sh['away'], 'recall%': sh['recall'], 'bank%': sh['bank'], 'died20%': x.died20.mean() * 100})
    show('a4. Same, by bag carried and by numbers within 8 (pooled)', pd.DataFrame(rows), floatfmt='{:.1f}')

# ------------------------------------------------------------------------------------------------ (b) an ally is hit
if not SECS or 'b' in SECS:
    h = F['ast'].copy()
    h['db'] = bins(h.d0, [0, 5, 9, 13, 17, 21], ['0-4', '5-8', '9-12', '13-16', '17-20'])
    h['helped'] = (h.hit >= 0).astype(int)
    h['came'] = (h.appr >= 0).astype(int)
    h['left'] = ((h.d5.notna()) & (h.d5 >= h.d0 + 2)).astype(int)
    rows = []
    for lab, k, g, sub in pools(h):
        r = {'grp': lab, 'events/game': sub.drop_duplicates(['game', 'r', 'vTy']).shape[0] / NG[k]}
        for db in ['0-4', '5-8', '9-12', '13-16']:
            x = sub[sub.db == db]
            r[f'hit% {db}'] = x.helped.mean() * 100 if len(x) else np.nan
            r[f'lat {db}'] = x[x.hit >= 0].hit.median() if (x.hit >= 0).any() else np.nan
        for db in ['5-8', '9-12', '13-16']:
            x = sub[sub.db == db]
            r[f'came<=4 % {db}'] = x.came.mean() * 100 if len(x) else np.nan
        x = sub[sub.db.isin(['0-4', '5-8'])]
        r['left% (<=8)'] = x.left.mean() * 100
        rows.append(r)
    show('b1. Ally hit (first champion hit after 6 quiet rounds): share of allies that hit an enemy near it within 10 rounds, median latency (rounds), share that came within 4, by distance', pd.DataFrame(rows), floatfmt='{:.1f}')
    # victim outcome vs number of allies that helped
    ev = h.groupby(['key', 'grp', 'game', 'r', 'vTy']).agg(nh=('helped', 'sum'), n8=('d0', lambda s: (s <= 8).sum()), vDied=('vDied', 'first'), aDied=('aDied', 'first'),
                                                         ratio=('mhA', 'first'), mhE=('mhE', 'first'), nA=('nA', 'first'), nE=('nE', 'first')).reset_index()
    rows = []
    for g in ('S', 'O'):
        for nh in (0, 1, 2):
            x = ev[(ev.grp == g) & ((ev.nh == nh) if nh < 2 else (ev.nh >= 2))]
            rows.append({'grp': g, 'allies that hit': f'{nh}' if nh < 2 else '2+', 'n': len(x), 'victim died15%': x.vDied.mean() * 100, 'attacker died15%': x.aDied.mean() * 100})
    show('b2. Outcome of the hit ally by number of allies that hit back (pooled)', pd.DataFrame(rows), floatfmt='{:.1f}')
    rows = []
    for lab, k, g, sub in pools(h):
        if k != 'ALL':
            continue
        for bz, bl in ((1, 'farming'), (2, 'on camp tile'), (0, 'free'), (3, 'recall chan'), (4, 'tribute chan')):
            x = sub[(sub.hBusy == bz) & (sub.d0 <= 8)]
            if len(x) < 20:
                continue
            rows.append({'grp': lab, 'helper state': bl, 'n (<=8)': len(x), 'hit%': x.helped.mean() * 100, 'came%': x.came.mean() * 100, 'left%': x.left.mean() * 100})
    show('b3. Allies within 8 by what they were doing when the ally was hit', pd.DataFrame(rows), floatfmt='{:.1f}')
    rows = []
    for lab, k, g, sub in pools(h):
        if k == 'ALL':
            continue
        x = sub[sub.d0 <= 8]
        for t in x.hTy.value_counts().index[:6]:
            y = x[x.hTy == t]
            if len(y) < 30:
                continue
            rows.append({'grp': lab, 'helper': t, 'n': len(y), 'hit%': y.helped.mean() * 100, 'lat': y[y.hit >= 0].hit.median(), 'came%': y.came.mean() * 100})
    show('b4. Help by champion (allies within 8)', pd.DataFrame(rows), floatfmt='{:.1f}')

# ------------------------------------------------------------------------------------------------ (c) bags
if not SECS or 'c' in SECS:
    c = F['cap'].copy()
    c['bagb'] = bins(c.bag, [0, 30, 60, 100, 200, 1e9], ['<30', '30-59', '60-99', '100-199', '200+'])
    c['adb'] = bins(c.ad, [0, 6, 13, 26, 1e9], ['<=5', '6-12', '13-25', '>25'])
    rows = []
    for lab, k, g, sub in pools(c):
        r = {'grp': lab, 'caps/game': len(sub) / NG[k], 'bank next%': (sub.nxt == 'bank').mean() * 100, 'cap again%': (sub.nxt == 'cap').mean() * 100,
             'died with it%': (sub.nxt == 'died').mean() * 100, 'rcNow%': sub.rcNow.mean() * 100}
        b = sub[sub.nxt == 'bank']
        r['rounds to bank (med)'] = b.when.median()
        r['via home%'] = b.viaHome.mean() * 100
        r['bag at bank med'] = b.bankBag.median()
        rows.append(r)
    show('c1. After a gem capture: next bag event (bank / another capture first / died) and how', pd.DataFrame(rows), floatfmt='{:.1f}')
    rows = []
    for lab, k, g, sub in pools(c):
        if k != 'ALL' and k not in KEYS:
            continue
        r = {'grp': lab}
        for bb in ['<30', '30-59', '60-99', '100-199', '200+']:
            x = sub[sub.bagb == bb]
            r[f'P(bank) {bb}'] = (x.nxt == 'bank').mean() * 100 if len(x) >= 10 else np.nan
            r[f'n {bb}'] = len(x)
        rows.append(r)
    show('c2. P(bank before the next capture) by bag after the capture', pd.DataFrame(rows), floatfmt='{:.0f}')
    rows = []
    for g in ('S', 'O'):
        for bb in ['<30', '30-59', '60-99', '100-199', '200+']:
            r = {'grp': g, 'bag': bb}
            for ab in ['<=5', '6-12', '13-25', '>25']:
                x = c[(c.grp == g) & (c.bagb == bb) & (c.adb == ab)]
                r[f'altar {ab}'] = f"{(x.nxt == 'bank').mean() * 100:.0f}% ({len(x)})" if len(x) >= 10 else f'({len(x)})'
            rows.append(r)
    show('c3. P(bank next) by bag x walking distance to the nearest altar at the capture (pooled S / O)', pd.DataFrame(rows))
    rows = []
    for g in ('S', 'O'):
        for nb, lab2 in ((0, 'no enemy within 8'), (1, 'enemy within 8')):
            x = c[(c.grp == g) & ((c.nE > 0) == bool(nb))]
            rows.append({'grp': g, 'threat': lab2, 'n': len(x), 'bank next%': (x.nxt == 'bank').mean() * 100, 'died with it%': (x.nxt == 'died').mean() * 100, 'bag med': x.bag.median()})
    show('c4. Threat at the capture vs next bag event (pooled)', pd.DataFrame(rows), floatfmt='{:.1f}')
    b = F['bnk']
    rows = []
    for lab, k, g, sub in pools(b):
        rows.append({'grp': lab, 'tributes/game': len(sub) / NG[k], 'bag med': sub.bag.median(), 'bag p75': sub.bag.quantile(.75), 'bag p90': sub.bag.quantile(.9), 'bag max': sub.bag.max(),
                     'enemy within 8 %': (sub.nE > 0).mean() * 100, 'hit during%': (sub.hitIn > 0).mean() * 100, 'done%': (sub.res == 'done').mean() * 100,
                     'killed%': (sub.res == 'killed').mean() * 100, 'stunned%': (sub.res == 'stunned').mean() * 100, 'locked%': (sub.res == 'locked').mean() * 100,
                     'since cap med': sub[sub.sinceCap >= 0].sinceCap.median(), 'altar dist at cap med': sub[sub.capAd >= 0].capAd.median()})
    show('c5. Tribute channels: bag size, threat, completion', pd.DataFrame(rows), floatfmt='{:.1f}')
    dd = F['dth']
    rows = []
    for lab, k, g, sub in pools(dd):
        x = sub[sub.bag > 0]
        rows.append({'grp': lab, 'deaths/game': len(sub) / NG[k], 'deaths with bag/game': len(x) / NG[k], 'gems lost/game': sub.bag.sum() / NG[k], 'bag at death med (if >0)': x.bag.median(),
                     'lost to camps/game': sub[sub.by == 'camp'].bag.sum() / NG[k]})
    show('c6. Bags lost on death', pd.DataFrame(rows), floatfmt='{:.1f}')

# ------------------------------------------------------------------------------------------------ (d) low health
if not SECS or 'd' in SECS:
    lo = F['low']
    lo = lo[lo['T'] == 0.35].copy()
    rows = []
    for lab, k, g, sub in pools(lo):
        for ctx, cond in (('enemy within 8', sub.dn <= 8), ('no enemy within 8', sub.dn > 8)):
            x = sub[cond]
            if len(x) < 15:
                continue
            sh = actshares(x)
            rows.append({'grp': lab, 'context': ctx, 'n/game': len(x) / NG[k], 'recall%': sh['recall'], 'away%': sh['away'], 'fight%': sh['fight'], 'farm%': sh['farm'], 'hold%': sh['hold'],
                         'bank%': sh['bank'], 'died15%': x.died15.mean() * 100, 'recall<=8 %': (x.rcAt >= 0).mean() * 100, 'home within 40%': (x.homeBy >= 0).mean() * 100,
                         'healed%': (x.heal10 > 0).mean() * 100})
    show('d1. Health falls below 35%: action in the next 5 rounds and outcome', pd.DataFrame(rows), floatfmt='{:.1f}')
    rows = []
    x0 = lo[lo.dn <= 8].copy()
    x0['ratio'] = x0.hpA / x0.hpE.clip(lower=1)
    x0['rb'] = bins(x0.ratio, RB, RL)
    for g in ('S', 'O'):
        for ai in (0, 2, 5, 4, 1):
            x = x0[(x0.grp == g) & (x0.a == ai)]
            if len(x) < 20:
                continue
            rows.append({'grp': g, 'action': ACTS[ai], 'n': len(x), 'died15%': x.died15.mean() * 100, 'median ratio': x.ratio.median(), 'enemy dist med': x.dn.median()})
    show('d2. Low health with an enemy within 8: outcome by action (pooled)', pd.DataFrame(rows), floatfmt='{:.1f}')
    rc = F['rcl']
    rows = []
    for lab, k, g, sub in pools(rc):
        x = sub[(sub.spam == 0)]
        sp = sub[sub.spam == 1]
        if len(x) < 10:
            rows.append({'grp': lab, 'non-spam attempts/game': len(x) / NG[k], 'spam team games': sp.game.nunique(), 'spam done/game': (sp.res == 'done').sum() / NG[k]})
            continue
        rows.append({'grp': lab, 'non-spam attempts/game': len(x) / NG[k], 'done%': (x.res == 'done').mean() * 100, 'interrupted%': (x.res == 'interrupted').mean() * 100, 'killed%': (x.res == 'killed').mean() * 100,
                     'cancel%': (x.res == 'cancel').mean() * 100, 'hp at start med': x.hpf.median(), 'hp p25': x.hpf.quantile(.25), 'hp p75': x.hpf.quantile(.75),
                     'enemy<=4 %': (x.dn <= 4).mean() * 100, 'enemy 5-8 %': ((x.dn > 4) & (x.dn <= 8)).mean() * 100, 'bag>0 %': (x.bag > 0).mean() * 100,
                     'spam team games': sp.game.nunique(), 'spam done/game': (sp.res == 'done').sum() / NG[k]})
    show('d3. Recall attempts (normal teams: every Recall away from spawn; recall-spam teams counted separately)', pd.DataFrame(rows), floatfmt='{:.2f}')
    rows = []
    x = rc[rc.spam == 0]
    for g in ('S', 'O'):
        for lab2, cond in (('enemy <=3', x.dn <= 3), ('enemy 4-5', (x.dn >= 4) & (x.dn <= 5)), ('enemy 6-8', (x.dn >= 6) & (x.dn <= 8)), ('enemy >8', x.dn > 8)):
            y = x[(x.grp == g) & cond]
            if len(y) < 10:
                continue
            rows.append({'grp': g, 'nearest enemy at start': lab2, 'n': len(y), 'done%': (y.res == 'done').mean() * 100, 'interrupted%': (y.res == 'interrupted').mean() * 100,
                         'killed%': (y.res == 'killed').mean() * 100, 'hit during%': (y.hitters > 0).mean() * 100})
    show('d4. Is the recall punished? Outcome by the nearest enemy distance at the start (normal teams, pooled)', pd.DataFrame(rows), floatfmt='{:.1f}')

# ------------------------------------------------------------------------------------------------ (e) outnumbered / outmatched
if not SECS or 'e' in SECS:
    o = F['omt']
    rows = []
    for lab, k, g, sub in pools(o):
        for kind in ('under', 'over'):
            x = sub[sub.kind == kind]
            if len(x) < 15:
                continue
            sh = actshares(x)
            rows.append({'grp': lab, 'state': kind, 'n/game': len(x) / NG[k], 'fight%': sh['fight'], 'away%': sh['away'], 'toward%': sh['toward'], 'hold%': sh['hold'], 'farm%': sh['farm'],
                         'recall%': sh['recall'], 'died15%': x.died15.mean() * 100, 'kills15/100': x.ek15.mean() * 100})
    show('e1. Enemy within 6 while outmatched (max health within 8 < 0.7x or 2+ fewer bodies) / outmatching (> 1.43x or 2+ more)', pd.DataFrame(rows), floatfmt='{:.1f}')
    rows = []
    for g in ('S', 'O'):
        for kind in ('under', 'over'):
            for ai in (0, 2, 3, 4, 1):
                x = o[(o.grp == g) & (o.kind == kind) & (o.a == ai)]
                if len(x) < 30:
                    continue
                rows.append({'grp': g, 'state': kind, 'action': ACTS[ai], 'n': len(x), 'died15%': x.died15.mean() * 100, 'kills15/100': x.ek15.mean() * 100, 'own hp med': x.hpf.median()})
    show('e2. Outcome by action (pooled)', pd.DataFrame(rows), floatfmt='{:.1f}')

# ------------------------------------------------------------------------------------------------ (f) punish channels
if not SECS or 'f' in SECS:
    p = F['pun']
    rows = []
    for lab, k, g, sub in pools(p):
        for kind in ('trib', 'rec'):
            x = sub[(sub.kind == kind) & (sub.nIn8 > 0)]
            if len(x) < 10:
                continue
            rows.append({'grp': lab, 'enemy channel': kind, 'n/game': len(x) / NG[k], 'bag med': x.bag.median(), 'dmin med': x.dmin.median(), 'hit%': (x.dmg > 0).mean() * 100, 'stun%': (x.stun > 0).mean() * 100,
                         'lock%': (x.lock > 0).mean() * 100, 'moved closer%': (x.closer > 0).mean() * 100, 'channel failed%': (x.res != 'done').mean() * 100, 'killed%': x.killed.mean() * 100})
    show('f1. Enemy tribute / recall channel with our body within 8: punish rates (from the punishing team)', pd.DataFrame(rows), floatfmt='{:.1f}')
    rows = []
    for g in ('S', 'O'):
        for kind in ('trib', 'rec'):
            for lab2, cond in (('<=4', p.dmin <= 4), ('5-6', (p.dmin >= 5) & (p.dmin <= 6)), ('7-8', (p.dmin >= 7) & (p.dmin <= 8))):
                x = p[(p.grp == g) & (p.kind == kind) & cond]
                if len(x) < 10:
                    continue
                rows.append({'grp': g, 'channel': kind, 'closest of us': lab2, 'n': len(x), 'hit%': (x.dmg > 0).mean() * 100, 'stun%': (x.stun > 0).mean() * 100, 'lock%': (x.lock > 0).mean() * 100,
                             'failed%': (x.res != 'done').mean() * 100, 'killed%': x.killed.mean() * 100, 'bag med': x.bag.median()})
    show('f2. Punish rate by distance (pooled)', pd.DataFrame(rows), floatfmt='{:.1f}')
    l = F['lck']
    rows = []
    for lab, k, g, sub in pools(l):
        r = {'grp': lab, 'locks/game': len(sub) / NG[k]}
        for cls in ('counter', 'guard', 'deny', 'other'):
            r[cls + '/game'] = (sub.cls == cls).sum() / NG[k]
        rows.append(r)
    show('f3. Altar locks placed per game by purpose (counter = cancels an enemy tribute in progress, guard = own tribute within 3 rounds at that altar, deny = enemy bag within 4)', pd.DataFrame(rows), floatfmt='{:.2f}')

# ------------------------------------------------------------------------------------------------ (g, h) engagements
if not SECS or 'g' in SECS or 'h' in SECS:
    e = F['eng'].copy()
    e['dec'] = np.sign(e.dEO - e.dES)  # +1 S won (fewer deaths), -1 O won, 0 even
    e['mhr'] = e.mhS / e.mhO.clip(lower=1)
    e['hpr'] = e.hpS / e.hpO.clip(lower=1)
    rows = []
    for k in KEYS + ['ALL']:
        x = e if k == 'ALL' else e[e.key == k]
        st = x[x.sSt == 1]; ot = x[x.sSt == 0]
        rows.append({'team': k, 'eng/game': len(x) / NG[k], 'S starts%': x.sSt.mean() * 100, 'S win% (decisive)': (x[x.dec != 0].dec > 0).mean() * 100,
                     'net/eng S started': (st.dEO - st.dES).mean(), 'net/eng O started': (ot.dEO - ot.dES).mean(), 'S deaths/eng': x.dES.mean(), 'O deaths/eng': x.dEO.mean(),
                     'S first3 dmg share': (x.dealt3S / (x.dealt3S + x.dealt3O).clip(lower=1)).mean(), 'S focus': x.focusS.mean(), 'O focus': x.focusO.mean(),
                     'S stun3': x.stun3S.mean(), 'O stun3': x.stun3O.mean()})
    show('h1. Engagements (champion damage clustered <= 6 rounds, <= 10 tiles; >= 3 hits or a death): who starts, who wins', pd.DataFrame(rows), floatfmt='{:.2f}')
    rows = []
    MB = [0, 0.67, 0.87, 1.15, 1.5, 1e9]
    ML = ['<0.67', '0.67-0.87', '0.87-1.15', '1.15-1.5', '>=1.5']
    e['mb'] = bins(e.mhr, MB, ML)
    for k in KEYS + ['ALL']:
        x = e if k == 'ALL' else e[e.key == k]
        r = {'team': k}
        for mb in ML:
            y = x[x.mb == mb]
            yd = y[y.dec != 0]
            r[f'{mb}'] = f"{(yd.dec > 0).mean() * 100:.0f}% {(y.dEO - y.dES).mean():+.2f} ({len(y)})" if len(y) >= 8 else f'({len(y)})'
        rows.append(r)
    show('h2. S win% of decisive engagements, net bodies per engagement (O deaths - S deaths), (n) by S/O local max-health ratio within 8 at the start', pd.DataFrame(rows))
    rows = []
    for k in KEYS + ['ALL']:
        x = e if k == 'ALL' else e[e.key == k]
        r = {'team': k}
        for mb in ML:
            for who, cond in (('S starts', x.sSt == 1), ('O starts', x.sSt == 0)):
                y = x[(x.mb == mb) & cond]
                r[f'{who} {mb}'] = f"{(y.dEO - y.dES).mean():+.2f} ({len(y)})" if len(y) >= 8 else f'({len(y)})'
        rows.append(r)
    show('h3. Net bodies per engagement by starter and S/O max-health ratio', pd.DataFrame(rows))
    # who starts at each power level (selectivity)
    rows = []
    for k in KEYS + ['ALL']:
        x = e if k == 'ALL' else e[e.key == k]
        r = {'team': k}
        for mb in ML:
            y = x[x.mb == mb]
            r[f'S starts% {mb}'] = y.sSt.mean() * 100 if len(y) >= 8 else np.nan
        rows.append(r)
    show('h4. Share of engagements started by S at each S/O max-health ratio (selectivity)', pd.DataFrame(rows), floatfmt='{:.0f}')
    # opener details
    rows = []
    for k in KEYS + ['ALL']:
        x = e if k == 'ALL' else e[e.key == k]
        for who, cond in (('S', x.sSt == 1), ('O', x.sSt == 0)):
            y = x[cond]
            rows.append({'team': k, 'starter': who, 'n': len(y), 'first hit is a spell%': y.cast.mean() * 100, 'opener stood still%': y.aStill.mean() * 100, 'victim walked in%': y.vIn.mean() * 100,
                         'opener walked in%': y.aIn.mean() * 100, 'victim farming%': (y.vFarm > 0).mean() * 100, 'victim channelling%': (y.vChan > 0).mean() * 100,
                         'victim hp med': y.vHp.median(), 'victim bag>0 %': (y.vBag > 0).mean() * 100})
    show('h5. How engagements open (by starter)', pd.DataFrame(rows), floatfmt='{:.1f}')
    # follow-through: damage share by window for the starter
    rows = []
    for k in KEYS + ['ALL']:
        x = e if k == 'ALL' else e[e.key == k]
        for who, cond in (('S', x.sSt == 1), ('O', x.sSt == 0)):
            y = x[cond]
            sh = []
            for i in range(3):
                a_ = np.where(y.sSt == 1, y[f'dW{i}S'], y[f'dW{i}O']); b_ = np.where(y.sSt == 1, y[f'dW{i}O'], y[f'dW{i}S'])
                tot = a_ + b_
                sh.append(np.nanmean(np.where(tot > 0, a_ / np.maximum(tot, 1), np.nan)))
            rows.append({'team': k, 'starter': who, 'n': len(y), 'starter dmg share r0..+2': sh[0], 'r+3..+6': sh[1], 'r+7..': sh[2],
                         'starter deaths/eng': np.where(y.sSt == 1, y.dES, y.dEO).mean(), 'other deaths/eng': np.where(y.sSt == 1, y.dEO, y.dES).mean()})
    show('h6. Follow-through: starter damage share by window', pd.DataFrame(rows), floatfmt='{:.2f}')

if not SECS or 'g' in SECS:
    e = F['eng'].copy()
    e['dec'] = np.sign(e.dEO - e.dES)
    rows = []
    for k in KEYS + ['ALL']:
        x = e if k == 'ALL' else e[e.key == k]
        for res, cond in (('S won', x.dec > 0), ('S lost', x.dec < 0), ('even, no deaths', (x.dES == 0) & (x.dEO == 0))):
            y = x[cond]
            for side in ('S', 'O'):
                br = y[f'a_br{side}'].sum()
                n = y[f'a_n{side}'].sum()
                rows.append({'team': k, 'result for S': res, 'side': side, 'n eng': len(y), 'farm%': y[f'a_farm{side}'].sum() / max(1, br) * 100, 'hit champ%': y[f'a_champ{side}'].sum() / max(1, br) * 100,
                             'recall chan%': y[f'a_rcl{side}'].sum() / max(1, br) * 100, 'caps30/eng': y[f'a_caps{side}'].mean(), 'gems30/eng': y[f'a_gemsCap{side}'].mean(),
                             'banks20/eng': y[f'a_bank{side}'].mean(), 'push% (4+ tiles toward their spawn)': y[f'a_toEnemy{side}'].sum() / max(1, n) * 100,
                             'reset% (4+ tiles home)': y[f'a_toHome{side}'].sum() / max(1, n) * 100, 'in their third%': y[f'a_theirHalf{side}'].sum() / max(1, br) * 100,
                             'next eng started by side%': ((y.nextSt == (1 if side == 'S' else 0))).mean() * 100, 'deaths 25 after/eng': y[f'd20{side}'].mean()})
    show('g1. After an engagement (participants alive at its end, next 20 rounds; captures within 30): what winners and losers do', pd.DataFrame(rows), floatfmt='{:.1f}')

if not SECS or 'h' in SECS:
    c = F['ctc'].copy()
    c['mhr'] = c.mhS / c.mhO.clip(lower=1)
    rows = []
    for k in KEYS + ['ALL']:
        x = c if k == 'ALL' else c[c.key == k]
        r = {'team': k, 'contacts/game': len(x) / NG[k], 'S first%': (x['first'] == 1).mean() * 100, 'O first%': (x['first'] == 0).mean() * 100, 'nobody%': (x['first'] == -1).mean() * 100}
        for lab2, cond in (('S weaker <0.87', x.mhr < 0.87), ('even', (x.mhr >= 0.87) & (x.mhr <= 1.15)), ('S stronger >1.15', x.mhr > 1.15)):
            y = x[cond]
            r[f'S first% {lab2}'] = (y['first'] == 1).mean() * 100
            r[f'O first% {lab2}'] = (y['first'] == 0).mean() * 100
        r['S body stepped in%'] = x.inS.mean() * 100; r['O body stepped in%'] = x.inO.mean() * 100
        rows.append(r)
    show('h7. Fresh contacts (opposing bodies within 5, quiet area for 8 rounds): who strikes first within 5 rounds', pd.DataFrame(rows), floatfmt='{:.1f}')
    ch = F['chs']
    rows = []
    for lab, k, g, sub in pools(ch):
        rows.append({'grp': lab, 'chases/game': len(sub) / NG[k], 'len med': sub.len.median(), 'len mean': sub.len.mean(), 'len p90': sub.len.quantile(.9), 'kill%': (sub.res == 'kill').mean() * 100,
                     'target died<=5 after%': sub.vDied5.mean() * 100, 'lost/home%': sub.res.isin(['lost', 'home']).mean() * 100, 'chaser died 10 after%': sub.aDied10.mean() * 100,
                     'deeper med (tiles from home)': sub.deeper.median(), 'kill% len<=4': (sub[sub.len <= 4].res == 'kill').mean() * 100, 'kill% len>=8': (sub[sub.len >= 8].res == 'kill').mean() * 100})
    show('h8. Chases (target steps away within 3 rounds of a hit, chaser follows)', pd.DataFrame(rows), floatfmt='{:.1f}')
    dd = F['dth']
    dd = dd[dd.by != 'camp']
    rows = []
    for lab, k, g, sub in pools(dd):
        n = len(sub)
        if not n:
            continue
        r = {'grp': lab, 'champ-kill deaths/game': n / NG[k]}
        for m in ('fighting', 'fleeAfterFight', 'flee', 'approach', 'walk', 'farming', 'recalling', 'banking', 'campContested'):
            r[m + '%'] = (sub['mode'] == m).mean() * 100
        r['isolated (no ally within 6)%'] = (sub.nA6 == 0).mean() * 100
        r['outnumbered within 6%'] = (sub.nE6 > sub.nA6 + 1).mean() * 100
        r['no hit in last 8%'] = (sub.own8 == 0).mean() * 100
        r['hp at seq start med'] = sub.hpS.median()
        r['victim mh / killer mh'] = (sub.mh / sub.atkMh.replace(0, np.nan)).median()
        r['their half%'] = (sub.z == 2).mean() * 100
        r['traded%'] = (sub.trade > 0).mean() * 100
        rows.append(r)
    show('h9. Champion-kill deaths: context (victim side)', pd.DataFrame(rows), floatfmt='{:.1f}')

# ------------------------------------------------------------------------------------------------ decision samples: state -> action
if not SECS or 's' in SECS:
    s = F['smp'].copy()
    s = s[s.busy < 3]
    s['ratio'] = s.hpA / s.hpE.clip(lower=1)
    s['rb'] = bins(s.ratio, RB, RL)
    rows = []
    for lab, k, g, sub in pools(s):
        r = {'grp': lab, 'n': len(sub)}
        for rb in RL:
            x = sub[(sub.rb == rb) & (sub.dn <= 4)]
            if len(x) < 30:
                r[rb] = ''
                continue
            sh = actshares(x)
            r[rb] = f"{sh['fight']:.0f}/{sh['away']:.0f}/{sh['farm']:.0f}"
        rows.append(r)
    show('s1. Enemy within 4 (decision samples every 3rd round): fight% / leave% / farm% in the next 3 rounds by current-health ratio within 8', pd.DataFrame(rows))
    rows = []
    for g in ('S', 'O'):
        for rb in RL:
            for ai in (0, 2, 1, 4):
                x = s[(s.grp == g) & (s.rb == rb) & (s.dn <= 4) & (s.a == ai)]
                if len(x) < 50:
                    continue
                rows.append({'grp': g, 'ratio': rb, 'action': ACTS[ai], 'n': len(x), 'died10%': x.died10.mean() * 100, 'kills10/100': x.ek10.mean() * 100,
                             'net/100': (x.ek10.mean() - x.died10.mean()) * 100, 'dmg out5': x.out5.mean(), 'dmg in5': x.in5.mean()})
    show('s2. Outcome by action, enemy within 4 (pooled S / O)', pd.DataFrame(rows), floatfmt='{:.1f}')
    # bag hunting: do they go toward an enemy that carries a bag?
    rows = []
    for g in ('S', 'O'):
        for lab2, cond in (('enemy bag 0', s.eBag == 0), ('enemy bag 1-49', (s.eBag > 0) & (s.eBag < 50)), ('enemy bag 50+', s.eBag >= 50)):
            x = s[(s.grp == g) & cond & (s.dn <= 6) & (s.dn >= 3)]
            if len(x) < 30:
                continue
            sh = actshares(x)
            rows.append({'grp': g, 'enemy bag within 8': lab2, 'n': len(x), 'fight%': sh['fight'], 'toward%': sh['toward'], 'away%': sh['away'], 'farm%': sh['farm']})
    show('s3. Enemy at 3-6 tiles: reaction to the enemy bag (pooled)', pd.DataFrame(rows), floatfmt='{:.1f}')
    # low hp target: do they go for a wounded enemy?
    rows = []
    for g in ('S', 'O'):
        for lab2, cond in (('nearest enemy hp <35%', s.eHp < 35), ('35-70%', (s.eHp >= 35) & (s.eHp < 70)), ('>=70%', s.eHp >= 70)):
            x = s[(s.grp == g) & cond & (s.dn <= 6)]
            if len(x) < 30:
                continue
            sh = actshares(x)
            rows.append({'grp': g, 'target': lab2, 'n': len(x), 'fight%': sh['fight'], 'toward%': sh['toward'], 'away%': sh['away'], 'kills10/100': x.ek10.mean() * 100, 'died10%': x.died10.mean() * 100})
    show('s4. Enemy within 6: reaction to the nearest enemy health (pooled)', pd.DataFrame(rows), floatfmt='{:.1f}')

# ------------------------------------------------------------------------------------------------ (p) who carries the bags (Prism carry)
if not SECS or 'p' in SECS:
    c = F['cap']
    rows = []
    for lab, k, g, sub in pools(c):
        if k == 'ALL':
            continue
        big = sub[sub.bag >= 100]
        if not len(big):
            rows.append({'grp': lab, 'caps with bag>=100 %': 0.0})
            continue
        top = big.ty.value_counts()
        rows.append({'grp': lab, 'caps with bag>=100 %': len(big) / len(sub) * 100, 'carrier 1': f'{top.index[0]} {top.iloc[0] / len(big) * 100:.0f}%',
                     'carrier 2': f'{top.index[1]} {top.iloc[1] / len(big) * 100:.0f}%' if len(top) > 1 else '', 'bag med when >=100': big.bag.median(),
                     'Prism drafted games': sub[sub.ty == 'Prism'].game.nunique()})
    show('p1. Who carries big bags (captures that leave the capturer with >= 100 gems)', pd.DataFrame(rows), floatfmt='{:.1f}')
    b = F['bnk']
    rows = []
    for lab, k, g, sub in pools(b):
        if k == 'ALL':
            continue
        x = sub[sub.ty == 'Prism']
        y = sub[sub.ty != 'Prism']
        if len(x) < 5:
            continue
        rows.append({'grp': lab, 'Prism tributes/game': len(x) / NG[k], 'Prism bag med': x.bag.median(), 'Prism bag p90': x.bag.quantile(.9), 'others bag med': y.bag.median(),
                     'Prism share of banked gems%': x.bag.sum() / max(1, sub.bag.sum()) * 100})
    show('p2. Prism tributes vs the rest', pd.DataFrame(rows), floatfmt='{:.1f}')
    s = F['smp']
    rows = []
    for g in ('S', 'O'):
        for lab2, cond in (('Prism bag 0-49', (s.ty == 'Prism') & (s.bag < 50)), ('Prism bag 50-149', (s.ty == 'Prism') & (s.bag >= 50) & (s.bag < 150)),
                           ('Prism bag 150+', (s.ty == 'Prism') & (s.bag >= 150))):
            x = s[(s.grp == g) & cond & (s.dn <= 6)]
            if len(x) < 30:
                continue
            sh = actshares(x)
            rows.append({'grp': g, 'state': lab2, 'n': len(x), 'fight%': sh['fight'], 'away%': sh['away'], 'farm%': sh['farm'], 'recall%': sh['recall'], 'bank%': sh['bank'],
                         'died10%': x.died10.mean() * 100, 'kills10/100': x.ek10.mean() * 100, 'dmg out5': x.out5.mean()})
    show('p3. Prism with an enemy within 6, by carried bag (pooled)', pd.DataFrame(rows), floatfmt='{:.1f}')

# ------------------------------------------------------------------------------------------------ (t) thresholds: fight vs leave by own health and local ratio
if not SECS or 't' in SECS:
    s = F['smp'].copy()
    s = s[(s.busy < 3) & (s.dn <= 4)]
    s['ratio'] = s.hpA / s.hpE.clip(lower=1)
    s['hb'] = bins(s.hpf, [0, 20, 35, 50, 70, 101], ['<20', '20-35', '35-50', '50-70', '70+'])
    RL2 = ['<0.45', '0.45-0.6', '0.6-0.75', '0.75-0.9', '0.9-1.1', '1.1-1.4', '>=1.4']
    s['rb2'] = bins(s.ratio, [0, 0.45, 0.6, 0.75, 0.9, 1.1, 1.4, 1e9], RL2)
    rows = []
    for lab, k, g, sub in pools(s):
        r = {'grp': lab}
        for hb in ['<20', '20-35', '35-50', '50-70', '70+']:
            x = sub[sub.hb == hb]
            sh = actshares(x)
            r[f'own hp {hb}'] = f"{sh['fight']:.0f}/{sh['away'] + sh['recall']:.0f}" if len(x) >= 40 else ''
        rows.append(r)
    show('t1. Enemy within 4: fight% / (leave+recall)% by OWN health fraction', pd.DataFrame(rows))
    rows = []
    for lab, k, g, sub in pools(s):
        r = {'grp': lab}
        for rb in RL2:
            x = sub[(sub.rb2 == rb) & (sub.hpf >= 35)]
            sh = actshares(x)
            r[rb] = f"{sh['fight']:.0f}/{sh['away'] + sh['recall']:.0f}" if len(x) >= 40 else ''
        rows.append(r)
    show('t2. Enemy within 4, own health >= 35%: fight% / (leave+recall)% by current-health ratio within 8', pd.DataFrame(rows))
    rows = []
    for lab, k, g, sub in pools(s):
        r = {'grp': lab}
        for nd in (-2, -1, 0, 1, 2):
            x = sub[(np.clip(sub.nA - sub.nE, -2, 2) == nd) & (sub.hpf >= 35)]
            sh = actshares(x)
            r[f'nA-nE {nd:+d}'] = f"{sh['fight']:.0f}/{sh['away'] + sh['recall']:.0f}" if len(x) >= 40 else ''
        rows.append(r)
    show('t3. Enemy within 4, own health >= 35%: fight% / (leave+recall)% by body count difference within 8 (clipped at +-2)', pd.DataFrame(rows))

# ------------------------------------------------------------------------------------------------ (w) game-level: decision features vs winning
if not SECS or 'w' in SECS:
    feats = {}

    def put(df, name, fn, need=1):
        for (key, game, grp), x in df.groupby(['key', 'game', 'grp']):
            if len(x) >= need:
                feats.setdefault((key, game), {})[name + grp] = fn(x)
    e = F['eng'].copy()
    e['mhr'] = e.mhS / e.mhO.clip(lower=1)
    for (key, game), x in e.groupby(['key', 'game']):
        f = feats.setdefault((key, game), {})
        f['startS'] = x.sSt.mean(); f['startO'] = 1 - x.sSt.mean()
        stS = x[x.sSt == 1]; stO = x[x.sSt == 0]
        f['badStartS'] = (stS.mhr < 0.67).mean() if len(stS) else np.nan
        f['badStartO'] = (stO.mhr > 1.0 / 0.67).mean() if len(stO) else np.nan
        f['netStartS'] = (stS.dEO - stS.dES).mean() if len(stS) else np.nan
        f['netStartO'] = (stO.dES - stO.dEO).mean() if len(stO) else np.nan
        f['first3S'] = (x.dealt3S / (x.dealt3S + x.dealt3O).clip(lower=1)).mean(); f['first3O'] = 1 - f['first3S']
    c = F['ctc']
    for (key, game), x in c.groupby(['key', 'game']):
        f = feats.setdefault((key, game), {})
        a_, b_ = (x['first'] == 1).sum(), (x['first'] == 0).sum()
        f['firstStrikeS'] = a_ / max(1, a_ + b_); f['firstStrikeO'] = b_ / max(1, a_ + b_)
    a = F['arr']
    put(a, 'keepFarm', lambda x: (x.a == 1).mean(), 3)
    put(a[(a.hpA / a.hpE.clip(lower=1)) < 0.9], 'weakFight', lambda x: (x.a == 0).mean(), 2)
    h = F['ast']
    put(h[h.d0 <= 8], 'help8', lambda x: (x.hit >= 0).mean(), 5)
    p = F['pun']
    put(p[(p.dmin <= 4)], 'punish4', lambda x: (x.dmg > 0).mean(), 2)
    rc = F['rcl']
    put(rc[rc.spam == 0], 'riskyRecall', lambda x: (x.dn <= 3).mean(), 5)
    lo = F['low']
    put(lo[(lo['T'] == 0.35) & (lo.dn <= 8)], 'lowRecall', lambda x: (x.a == 5).mean(), 2)
    put(lo[(lo['T'] == 0.35) & (lo.dn <= 8)], 'lowFight', lambda x: (x.a == 0).mean(), 2)
    ch = F['chs']
    put(ch, 'chaseLen', lambda x: x.len.mean(), 2)
    put(ch, 'chaseKill', lambda x: (x.res == 'kill').mean(), 2)
    b = F['bnk']
    put(b, 'bankBag', lambda x: x.bag.median(), 2)
    om = F['omt']
    put(om[om.kind == 'under'], 'underFight', lambda x: (x.a == 0).mean(), 3)
    put(om[om.kind == 'over'], 'overFight', lambda x: (x.a == 0).mean(), 3)
    d = F['dth']
    d2 = d[d.by != 'camp']
    put(d2, 'isoDeath', lambda x: (x.nA6 == 0).mean(), 2)
    put(d2, 'noHitDeath', lambda x: (x.own8 == 0).mean(), 2)
    sm = F['sum']
    for _, r in sm.iterrows():
        f = feats.setdefault((r.key, r.game), {})
        f['win'] = r.win
        for side in ('S', 'O'):
            for nm in ('deaths', 'kills', 'bagLost', 'mh300', 'locks', 'campDeaths'):
                f[nm + side] = r[nm + side]
    G = pd.DataFrame([{'key': k[0], 'game': k[1], **v} for k, v in feats.items()])
    names = ['deaths', 'kills', 'campDeaths', 'bagLost', 'mh300', 'start', 'badStart', 'netStart', 'first3', 'firstStrike', 'keepFarm', 'weakFight', 'help8', 'punish4',
             'riskyRecall', 'lowRecall', 'lowFight', 'chaseLen', 'chaseKill', 'bankBag', 'underFight', 'overFight', 'isoDeath', 'noHitDeath', 'locks']
    rows = []
    for nm in names:
        cS, cO = nm + 'S', nm + 'O'
        if cS not in G or cO not in G:
            continue
        x = G[['key', 'win', cS, cO]].dropna()
        diff = x[cS] - x[cO]
        r = {'feature': nm, 'n games': len(x), 'S mean': x[cS].mean(), 'O mean': x[cO].mean(), 'S in S wins': x[x.win == 1][cS].mean(), 'S in S losses': x[x.win == 0][cS].mean(),
             'corr(S-O, S win)': np.corrcoef(diff, x.win)[0, 1] if diff.std() > 0 else np.nan}
        for k in KEYS:
            y = x[x.key == k]
            dd = y[cS] - y[cO]
            r[k] = np.corrcoef(dd, y.win)[0, 1] if len(y) > 10 and dd.std() > 0 else np.nan
        rows.append(r)
    show('w1. Game-level decision features vs the game result (S mean / O mean; S value in S wins vs S losses; correlation of S-O with S winning, pooled and per study team)', pd.DataFrame(rows), floatfmt='{:.2f}')
    G.to_pickle(os.path.join(D, 'flat', 'gamefeat.pkl'))
