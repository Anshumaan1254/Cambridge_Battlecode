# Flatten tools/top2/fights/sit.mjs output (sit_<key>.jsonl) into pandas tables (one pickle per record type) for agg.py.
# Every row carries key (study team), game, map, win (study team won the game), grp ('S' study team / 'O' its opponent), opp name.
# Symmetric records (eng, ctc, sum) are turned to the study team's perspective (S / O columns).
#   python tools/top2/fights/flat.py C:/battlecode/cache/top2_fights
import json, os, sys
import pandas as pd

D = sys.argv[1]
KEYS = ['pbg', 'ifish', 'cm', 'pantheon', 'coo', 'nyx']
SMP = ['t', 'ty', 'r', 'busy', 'bag', 'hpf', 'dn', 'nA', 'nE', 'hpA', 'hpE', 'mhA', 'mhE', 'z', 'a', 'died10', 'ek10', 'out5', 'in5', 'nA4', 'nE4', 'eTy',
       'eBag', 'eHp']
HELP = ['hTy', 'd0', 'hBusy', 'hHp', 'hit', 'hitAtk', 'appr', 'd5', 'minD', 'hBag']
rows = {k: [] for k in ['smp', 'arr', 'ast', 'cap', 'bnk', 'low', 'rcl', 'omt', 'pun', 'lck', 'eng', 'chs', 'dth', 'ctc', 'sum']}
for key in KEYS:
    p = os.path.join(D, f'sit_{key}.jsonl')
    if not os.path.exists(p):
        continue
    for l in open(p, encoding='utf-8'):
        g = json.loads(l)
        if 'err' in g or 'sum' not in g:
            continue
        st = g['st']
        base = {'key': key, 'game': g['game'], 'map': g['map'], 'win': g['win'], 'opp': g['opp'], 'FR': g['FR'], 'nb': g['nb'][st]}
        grp = lambda t: 'S' if t == st else 'O'
        for s in g['smp']:
            rows['smp'].append((key, g['game'], g['win'], grp(s[0]), *s[1:]))
        for typ in ['arr', 'cap', 'bnk', 'low', 'rcl', 'omt', 'lck', 'chs', 'dth']:
            for x in g[typ]:
                r = dict(base); r['grp'] = grp(x['t']); r.update({k: v for k, v in x.items() if k not in ('t',)})
                if typ == 'rcl':
                    r['hitters'] = len(x['hitters'])
                if typ == 'dth':
                    r['atkMh'] = sum(x['atkMh']) / len(x['atkMh']) if x['atkMh'] else 0
                rows[typ].append(r)
        for x in g['pun']:
            r = dict(base); r['grp'] = grp(x['t']); r.update({k: v for k, v in x.items() if k not in ('t', 'chT')}); rows['pun'].append(r)
        for x in g['ast']:
            for h in x['h']:
                r = dict(base); r['grp'] = grp(x['t'])
                r.update({k: v for k, v in x.items() if k not in ('t', 'h', 'v')})
                r.update(dict(zip(HELP, h)))
                rows['ast'].append(r)
        o = 1 - st
        for e in g['eng']:
            r = dict(base)
            r.update({'r0': e['r0'], 'r1': e['r1'], 'sSt': 1 if e['st'] == st else 0, 'aTy': e['aTy'], 'vTy': e['vTy'], 'cast': e['cast'], 'vFarm': e['vFarm'],
                      'vMove': e['vMove'], 'vChan': e['vChan'], 'aStill': e['aStill'], 'vIn': e['vIn'], 'aIn': e['aIn'], 'vHp': e['vHp'], 'vBag': e['vBag'],
                      'zS': (e['z0'] if st == 0 else 2 - e['z0']), 'nextSt': -1 if e['nextSt'] < 0 else (1 if e['nextSt'] == st else 0), 'nextDt': e['nextDt']})
            for side, t in (('S', st), ('O', o)):
                r['n' + side] = e['n'][t]; r['hp' + side] = e['hp'][t]; r['mh' + side] = e['mh'][t]; r['parts' + side] = e['parts'][t]
                r['dealt' + side] = e['dealt'][t]; r['dealt3' + side] = e['dealt3'][t]; r['hits' + side] = e['hits'][t]; r['casts' + side] = e['casts'][t]
                r['focus' + side] = e['focus'][t]; r['stun3' + side] = e['stun3'][t]; r['dE' + side] = e['dE'][t]; r['bag' + side] = e['bag'][t]
                r['d20' + side] = e['d20'][t]
                for i, w in enumerate(e['dW'][t]):
                    r[f'dW{i}' + side] = w
                for k2, v2 in e['after'][t].items():
                    r['a_' + k2 + side] = v2
            rows['eng'].append(r)
        for c in g['ctc']:
            r = dict(base)
            r.update({'r': c['r'], 'd': c['d'], 'first': -1 if c['first'] < 0 else (1 if c['first'] == st else 0), 'dt': c['dt'], 'fCast': c['fCast'], 'fTy': c['fTy'],
                      'zS': (c['z0'] if st == 0 else 2 - c['z0'])})
            for side, t in (('S', st), ('O', o)):
                r['n' + side] = c['n'][t]; r['hp' + side] = c['hp'][t]; r['mh' + side] = c['mh'][t]
            # inMove / farm are indexed by team (0 = team 0 body, 1 = team 1 body)
            r['inS'] = c['inMove'][st]; r['inO'] = c['inMove'][o]; r['farmS'] = c['farm'][st]; r['farmO'] = c['farm'][o]
            rows['ctc'].append(r)
        r = dict(base)
        r['typesS'] = ','.join(g['types'][st]); r['typesO'] = ','.join(g['types'][o])
        for side, t in (('S', st), ('O', o)):
            for k2, v2 in g['sum'][t].items():
                r[k2 + side] = v2
        rows['sum'].append(r)
os.makedirs(os.path.join(D, 'flat'), exist_ok=True)
for k, v in rows.items():
    if k == 'smp':
        df = pd.DataFrame(v, columns=['key', 'game', 'win', 'grp'] + SMP[1:])
    else:
        df = pd.DataFrame(v)
    df.to_pickle(os.path.join(D, 'flat', f'{k}.pkl'))
    print(k, len(df))
