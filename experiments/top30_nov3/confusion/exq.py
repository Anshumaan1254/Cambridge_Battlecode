import json, glob, sys
from collections import Counter, defaultdict
OUT='/home/claude/cambridge_battlecode/experiments/top30_nov3/confusion/out'
rows=[json.load(open(f)) for f in glob.glob(f'{OUT}/fl/*.json')]
E=defaultdict(list)
for o in rows:
    for e in o['ex']:
        if o['tag']=='top':
            k='top_W' if e['t']==o['winner'] else 'top_L'
        elif o['tag']=='v88':
            k='we_v88'
        else: k='we_old'
        e['mid_']=o['mid']; e['map']=o['map']
        E[k].append(e)
def q(e): # quantile summary
    return e
for cl in sys.argv[1].split(','):
    for k in ('we_v88','top_W','top_L'):
        L=[e for e in E[k] if e['cl']==cl]
        if not L: continue
        n=len(L); lost=sum(e['n'] for e in L)
        f=lambda pred: f"{100*sum(e['n'] for e in L if pred(e))/max(1,lost):4.0f}%"
        print(f"{cl} {k:7s} eps={n} lost={lost} len_mean={lost/n:.1f} | en_d<=8 {f(lambda e:e['en_d']<=8)} en6>=2 {f(lambda e:e['en6']>=2)} al5>=1 {f(lambda e:e['al5']>=1)} hp<.6 {f(lambda e:e['hp']<.6)} bag>=20 {f(lambda e:e['bag']>=20)} grp_alive {f(lambda e:e['gs']=='alive')} grp_dead {f(lambda e:e['gs'] in ('dead','reward'))} nogrp {f(lambda e:e['gs'] is None)} dsp<=8 {f(lambda e:e['dsp']<=8)} resp<40 {f(lambda e:e['since_resp']<40)} len2 {f(lambda e:e['n']<=2)} len>=6 {f(lambda e:e['n']>=6)}")
        c=Counter(e['ty'] for e in L); 
        print('    by type (lost):', sorted(((t,sum(e['n'] for e in L if e['ty']==t)) for t in c), key=lambda x:-x[1])[:8])
        print('    pre:', Counter(e['pre'] for e in L).most_common(5), ' post:', Counter(e['post'] for e in L).most_common(5))
