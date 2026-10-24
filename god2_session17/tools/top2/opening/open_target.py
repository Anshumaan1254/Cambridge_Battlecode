# First-target choice of the main opening squad (the camp group most bodies hit first) vs the alternatives on the map, from
# tools/top2/opening/open_extract.mjs output; conditional-logit fit of the choice (utility over walk distance, gems, gold, zone,
# camp class) per study team and for all teams.   python tools/top2/opening/open_target.py FLATDIR EXTRACT.jsonl...
import sys, json, os
import numpy as np, pandas as pd
from scipy.optimize import minimize

flat = sys.argv[1]
tg = pd.read_csv(os.path.join(flat, 'teamgame.csv'))
tg['file'] = tg['map'] + '_' + tg['mid8']
lab = {}
# a team that is a study team keeps its own key even when the game also sits in its opponent's folder
for _, r in tg.sort_values('study', ascending=False).iterrows():
    lab.setdefault((r.file, r.t), (r.key if r.study == 1 else 'opp_' + r.key, r.won, r.n, r.area))

recs, cand = [], []
seen = set()
for f in sys.argv[2:]:
    for l in open(f, encoding='utf-8'):
        d = json.loads(l)
        if d['file'] in seen: continue  # the same game can sit in two study teams' folders
        seen.add(d['file'])
        G = {g['id']: g for g in d['groups']}
        for T in d['teams']:
            t = T['t']
            if (d['file'], t) not in lab: continue
            key, won, n, area = lab[(d['file'], t)]
            hits = [(o['firstHit']['r'], o['firstHit']['g'], o['type']) for o in T['bodies'] if o['firstHit']]
            if not hits: continue
            gs = [h[1] for h in hits]
            main = max(set(gs), key=lambda g: (gs.count(g), -min(h[0] for h in hits if h[1] == g)))
            k = gs.count(main)
            # candidates: every group reachable by this team with gems or gold
            cs = [g for g in d['groups'] if g['d'][t] >= 0 and (g['gems'] > 0 or g['gold'] > 0) and g['cls'] not in ('mono',)]
            if not cs: continue
            dn = min(g['d'][t] for g in cs)
            ch = G[main]
            rank_d = 1 + sum(1 for g in cs if g['d'][t] < ch['d'][t])
            rank_g = 1 + sum(1 for g in cs if g['gems'] > ch['gems'])
            # richest group (gems) within the chosen group's distance + 0
            better_closer = sum(1 for g in cs if g['d'][t] <= ch['d'][t] and g['gems'] > ch['gems'])
            recs.append(dict(file=d['file'], t=t, key=key, won=won, n=n, area=area, k=k, kshare=k / n, cls=ch['cls'], zone=ch['zone'][t],
                             f=ch['f'][t], d=ch['d'][t], dnear=dn, gems=ch['gems'], gold=ch['gold'], hp=ch['hp'], rank_d=rank_d, rank_g=rank_g,
                             better_closer=better_closer, ncand=len(cs), r0=min(h[0] for h in hits if h[1] == main)))
            for g in cs:
                cand.append(dict(file=d['file'], t=t, key=key, chosen=int(g['id'] == main), d=g['d'][t], gems=g['gems'], gold=g['gold'], hp=g['hp'],
                                 mid=int(g['zone'][t] == 'M'), enemy=int(g['zone'][t] == 'T'), elk=int(g['cls'] == 'elk'),
                                 golem=int(g['cls'] == 'golem'), gemc=int(g['cls'] == 'gem'), wolf=int(g['cls'] == 'wolf'), goldc=int(g['cls'] == 'gold')))
R = pd.DataFrame(recs); C = pd.DataFrame(cand)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
R['grp'] = np.where(R.key.str.startswith('opp_'), 'opponents', R.key)
print('== main opening squad first target (per team-game)')
agg = R.groupby('grp').agg(n=('k', 'size'), kshare=('kshare', 'mean'), d=('d', 'median'), dnear=('dnear', 'median'), gems=('gems', 'median'),
                           nearest=('rank_d', lambda s: (s == 1).mean()), top3d=('rank_d', lambda s: (s <= 3).mean()),
                           richest=('rank_g', lambda s: (s == 1).mean()), elk=('cls', lambda s: (s == 'elk').mean()),
                           gemcl=('cls', lambda s: (s == 'gem').mean()), wolf=('cls', lambda s: (s == 'wolf').mean()),
                           golem=('cls', lambda s: (s == 'golem').mean()), mid=('zone', lambda s: (s == 'M').mean()),
                           own=('zone', lambda s: (s == 'O').mean()), better_closer=('better_closer', 'mean'), r0=('r0', 'median'))
print(agg.round(2))
print('\n== same, by map size class (S <= 1400 tiles, M <= 2600, L) for all teams')
R['size'] = np.where(R.area <= 1400, 'S', np.where(R.area <= 2600, 'M', 'L'))
print(R.groupby(['size', R.grp == 'opponents']).agg(n=('k', 'size'), kshare=('kshare', 'mean'), d=('d', 'median'), gems=('gems', 'median'),
      nearest=('rank_d', lambda s: (s == 1).mean()), elk=('cls', lambda s: (s == 'elk').mean()), mid=('zone', lambda s: (s == 'M').mean())).round(2))
print('\n== winners vs losers (all teams in all games): main target features')
print(R.groupby('won').agg(n=('k', 'size'), kshare=('kshare', 'mean'), d=('d', 'mean'), gems=('gems', 'mean'), nearest=('rank_d', lambda s: (s == 1).mean()),
      elk=('cls', lambda s: (s == 'elk').mean()), mid=('zone', lambda s: (s == 'M').mean())).round(2))

# conditional logit
FE = ['logd', 'loggems', 'loggold', 'mid', 'enemy', 'elk', 'golem', 'wolf']
C['logd'] = np.log1p(C.d); C['loggems'] = np.log1p(C.gems); C['loggold'] = np.log1p(C.gold)
def fit(df):
    X = df[FE].to_numpy(float); y = df.chosen.to_numpy(); gid = df.groupby(['file', 't']).ngroup().to_numpy()
    ng = gid.max() + 1
    def nll(w):
        u = X @ w
        mx = np.zeros(ng); np.maximum.at(mx, gid, u)
        e = np.exp(u - mx[gid]); s = np.zeros(ng); np.add.at(s, gid, e)
        ll = (u - mx[gid])[y == 1].sum() - np.log(s).sum()
        return -ll + 0.5 * (w @ w)  # small ridge: some teams' choices are separable
    res = minimize(nll, np.zeros(len(FE)), method='BFGS')
    se = np.sqrt(np.diag(res.hess_inv)) if hasattr(res, 'hess_inv') else np.full(len(FE), np.nan)
    # hit rate: chosen = argmax utility
    u = X @ res.x
    df2 = df.assign(u=u)
    top = df2.loc[df2.groupby(['file', 't']).u.idxmax()]
    return res.x, se, top.chosen.mean(), ng
print('\n== conditional logit of the main squad first target (utility weights; hit = chosen group is the argmax)')
out = []
for grp, df in [('all', C)] + [(k, C[C.key == k]) for k in ['pbg', 'ifish', 'pantheon', 'coo', 'cm', 'nyx']] + [('opponents', C[C.key.str.startswith('opp_')])]:
    w, se, hit, ng = fit(df)
    row = {'grp': grp, 'n': ng, 'hit': round(hit, 2)}
    for f_, wi, si in zip(FE, w, se): row[f_] = f'{wi:+.2f}'
    out.append(row)
print(pd.DataFrame(out).set_index('grp'))
# simple rules: share of team-games where the rule picks the main squad's first target
def rule_hits(df):
    out = {}
    g = df.groupby(['file', 't'])
    def pick(score):
        sc = df.assign(s=score)
        top = sc.loc[sc.groupby(['file', 't']).s.idxmax()]
        return top.chosen.mean()
    out['nearest'] = pick(-df.d)
    for c in (5, 10, 20, 40):
        out[f'(gems+gold/10)/(d+{c})'] = pick((df.gems + df.gold / 10) / (df.d + c))
    for c in (5, 10, 20):
        out[f'gold/(d+{c})'] = pick((df.gold + 1) / (df.d + c))
    out['richest gems'] = pick(df.gems + 0.001 * -df.d)
    return out
print("\n== simple rules: share of team-games whose main first target is the rule's pick")
rows = []
for grp, df in [('all', C)] + [(k, C[C.key == k]) for k in ['pbg', 'ifish', 'pantheon', 'coo', 'cm', 'nyx']] + [('opponents', C[C.key.str.startswith('opp_')])]:
    rows.append(dict(grp=grp, **{k: round(v, 2) for k, v in rule_hits(df.reset_index(drop=True)).items()}))
print(pd.DataFrame(rows).set_index('grp'))
R.to_csv(os.path.join(flat, 'targets.csv'), index=False)
