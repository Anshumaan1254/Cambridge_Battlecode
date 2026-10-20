import csv, json, sys, collections
S = sys.argv[1]
idx = {r['group']+'_'+r['nn']: r for r in json.load(open('experiments/ladder_oct19b/index.json'))}
D = list(csv.DictReader(open(S+'/deaths.csv')))
skip = set(sys.argv[2].split(',')) if len(sys.argv)>2 else set()
cnt = collections.defaultdict(collections.Counter)
for d in D:
    mp = d['match'].split('_')[-1]
    if mp in skip: continue
    r = idx[d['match'][:11]]
    us = 0 if r['side']=='A' else 1
    who = 'us' if int(d['team'])==us else 'them'
    c = cnt[who]
    c['n']+=1
    c['champ:'+d['champ']]+=1
    c['by:'+d['by']]+=1
    c['side:'+d['side']]+=1
    a,e = int(d['allies6']), int(d['enemies6'])
    c['outnum' if e>a else ('even' if e==a else 'upnum')]+=1
    c['alone' if a==0 else 'withally']+=1
    hp=float(d['hp_prev_frac'])
    c['hp_prev>=0.6' if hp>=0.6 else 'hp_prev<0.6']+=1
    c['bag>0']+= int(d['bag'])>0
    c['baggems']+=int(d['bag'])
for w in ('us','them'):
    c=cnt[w]; n=c['n']
    print(w, n, ' '.join(f'{k}={v}' for k,v in sorted(c.items(), key=lambda x:-x[1]) if k!='n'))
