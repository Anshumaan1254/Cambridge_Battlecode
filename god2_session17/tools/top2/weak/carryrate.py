"""Carry dependence (an_weak): team capture rate (gems captured per 100 rounds) and kill/death rate while a given champion is dead vs
   alive, rounds 100..min(final, 1200), from fightdump dumps. python tools/top2/weak/carryrate.py KEY CHAMP_TYPE"""
import json, gzip, sys, collections
key, champ = sys.argv[1], sys.argv[2]
TEAMS = {'pbg': '38e6d8c4', 'ifish': '1890540d', 'cm': 'ad5474c2', 'pantheon': '547efb5b', 'coo': '1570a113', 'nyx': '6f7fd199'}
idx = {}
for l in open(f'C:/battlecode/cache/t2/{key}/index.jsonl', encoding='utf-8'):
    r = json.loads(l); idx[r['matchId'][:8]] = r
import glob, os
agg = {'alive': [0, 0, 0, 0, 0], 'dead': [0, 0, 0, 0, 0]}  # rounds, team cap gems, opp cap gems, team deaths, opp deaths
for f in glob.glob(f'C:/battlecode/cache/t2dump/{key}/*.json.gz'):
    mid = os.path.basename(f).split('_')[-1][:8]; row = idx.get(mid)
    if not row: continue
    me = [t for t in row['teams'] if t['teamId'].startswith(TEAMS[key])][0]; S = 0 if me['side'] == 'a' else 1
    d = json.loads(gzip.open(f).read())
    team = {b['index']: b['team'] for b in d['meta']['bodies']}; ty = {b['index']: b['type'] for b in d['meta']['bodies']}
    cb = [i for i in ty if ty[i] == champ and team[i] == S]
    if not cb: continue
    c = cb[0]
    alive = {}
    for e in d['R']:
        for x in e[3]:
            if x[0] == c: alive[e[0]] = x[5]
    caps = collections.defaultdict(lambda: [0, 0]); dth = collections.defaultdict(lambda: [0, 0])
    for e in d['ev']:
        if e['k'] == 'CaptureGems': caps[e['r']][0 if team[e['who']] == S else 1] += e['gems']
        if e['k'] == 'Death': dth[e['r']][0 if team[e['who']] == S else 1] += 1
    for r in range(100, min(d['meta']['finalRound'], 1200)):
        k = 'alive' if alive.get(r, 1) else 'dead'
        A = agg[k]; A[0] += 1; A[1] += caps[r][0]; A[2] += caps[r][1]; A[3] += dth[r][0]; A[4] += dth[r][1]
for k, A in agg.items():
    print(f'{key} {champ} {k}: {A[0]} rounds; team cap gems/100r {100*A[1]/A[0]:.1f}, opp {100*A[2]/A[0]:.1f}; team deaths/100r {100*A[3]/A[0]:.2f}, opp {100*A[4]/A[0]:.2f}')
