import json,glob,os,sys,collections
# usage: pool_cmp.py BOT1 BOT2 OPP POOLDIR...
b1,b2,opp=sys.argv[1:4]; pools=sys.argv[4:]
def latest(b,o):
    rows=[json.loads(l) for l in open(f'experiments/results/ledger/{b}_vs_{o}.jsonl')]
    h=rows[-1]['bot_hash']; oh=rows[-1]['opp_hash']
    d={}
    for r in rows:
        if r['bot_hash']==h and r['opp_hash']==oh: d[(r['map'],r['side'])]=r
    return d
A=latest(b1,opp); B=latest(b2,opp)
for p in pools:
    maps=[os.path.basename(x)[:-7] for x in glob.glob(p+'/*.map26a')]
    wa=wb=n=0; diff=[]
    for m in maps:
        for s in 'AB':
            ra=A.get((m,s)); rb=B.get((m,s))
            if not ra or not rb: continue
            n+=1; wa+=ra['win']; wb+=rb['win']
            if ra['win']!=rb['win']: diff.append(f"{m}{s}:{'+' if ra['win'] else '-'}")
    print(f"{p:12s} {b1} {wa}/{n}  {b2} {wb}/{n}   flips {' '.join(diff)}")
