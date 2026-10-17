import sys
def load(b):
    d={}
    for l in open(f'/tmp/pace/res/{b}.txt'):
        p=l.split()
        if len(p)>=2 and p[1].isdigit(): d[p[0]]=int(p[1])
    return d
a,b=load(sys.argv[1]),load(sys.argv[2])
rows=sorted(((b[k]-a[k],k) for k in a if k in b))
print(' '.join(f'{k}:{d:+d}' for d,k in rows if abs(d)>=15))
