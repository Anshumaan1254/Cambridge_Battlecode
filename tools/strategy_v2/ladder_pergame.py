import csv, json, sys, collections
S = sys.argv[1]
idx = {r['group']+'_'+r['nn']: r for r in json.load(open('experiments/ladder_oct19b/index.json'))}
T = list(csv.DictReader(open(S+'/team.csv')))
by = collections.defaultdict(dict)
for t in T:
    k = t['match'][:11]
    r = idx[k]
    us = 0 if r['side']=='A' else 1
    by[t['match']]['us' if int(t['team'])==us else 'them'] = t
print('match                     win  us-them   rnd  deaths(us/them) kills camp_gems(us/them) gold caps casts dmg_champ(us/them)')
agg = collections.defaultdict(lambda: collections.defaultdict(float))
for m, d in sorted(by.items(), key=lambda x: x[0].split('_')[-1]):
    u, t = d['us'], d['them']
    print(f"{m:28s} {u['won']}  {u['banked']:>4}-{t['banked']:<4} {u['rounds']:>4}  {u['deaths']:>3}/{t['deaths']:<3}  {u['camp_gems']:>5}/{t['camp_gems']:<5} {u['gold']:>5}/{t['gold']:<5} {u['captures']:>3}/{t['captures']:<3} {u['casts']:>4}/{t['casts']:<4} {u['dmg_champ']:>6}/{t['dmg_champ']:<6}")
    for side,x in (('us',u),('them',t)):
        for c in ('deaths','camp_gems','gold','captures','casts','dmg_champ','dmg_camp','rounds','recalls','banks'):
            agg[side][c]+=float(x[c])
n=len(by)
print('per game:', {s:{c:round(v/n,1) for c,v in a.items()} for s,a in agg.items()})
