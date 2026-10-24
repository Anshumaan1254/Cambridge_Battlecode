# Per-parameter drift of an A100/ES run: start (gen 0), end, best, move in % of range, consistency (share of steps toward the final value).
# Usage: python3 tools/rl/a100/analyze_run.py RUN_DIR   (run from the repo root; compares with bots/_rm and bots/_m4 params.h)
import json,re,sys
A=sys.argv[1]
h=json.load(open(A+'/history.json')); best=json.load(open(A+'/best_params.json'))
sp=json.load(open('tools/rl/a100/space.json')); params=sp['params'] if 'params' in sp else sp
rng={p['name']:(p.get('lo',p.get('min')),p.get('hi',p.get('max'))) for p in params} if isinstance(params,list) else {k:(v.get('lo',v.get('min')),v.get('hi',v.get('max'))) for k,v in params.items()}
def pdef(path):
    d={}
    for l in open(path):
        m=re.match(r'\s*(?:float|int|double|bool)\s+(\w+)\s*=\s*([-\d.eE+]+)f?\s*;',l)
        if m: d[m.group(1)]=float(m.group(2))
    return d
rm=pdef('bots/_rm/src/params.h'); m4=pdef('bots/_m4/src/params.h')
f=lambda s: float(str(s).rstrip('f'))
rows=[]
for n in h[0]['params']:
    seq=[f(g['params'][n]) for g in h]
    lo,hi=rng.get(n,(None,None)); b=f(best[n])
    steps=[seq[k+1]-seq[k] for k in range(len(seq)-1)]
    fin=b-seq[0]
    nz=[s for s in steps if abs(s)>1e-9]
    cons=sum(1 for s in nz if s*fin>0)/max(1,len(nz))
    mv=100*(b-seq[0])/(hi-lo) if lo is not None else 0
    flag='*' if rm.get(n)!=m4.get(n) else ' '
    rows.append((abs(mv)*cons,f"{flag}{n:20s} rm={rm.get(n,'?')!s:7s} m4={m4.get(n,'?')!s:7s} g0={seq[0]:7.3f} end={seq[-1]:7.3f} best={b:7.3f} [{lo},{hi}] move={mv:+6.1f}% cons={cons:.2f}"))
for _,r in sorted(rows,reverse=True): print(r)
