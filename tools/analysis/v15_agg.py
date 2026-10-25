import json,sys,glob,collections,statistics as st
sys.path.insert(0,'tools/mapintel')
import mapdata
S=sys.argv[1]
T=collections.defaultdict(list)
rows=[]
for f in sorted(glob.glob(S+'/sum/*.json')):
    g=json.load(open(f))
    M=mapdata.load(g['map'])
    # spawn centres
    def cen(t):
        xs=[p[0] for p in t]; ys=[p[1] for p in t]; return (sum(xs)/len(xs), sum(ys)/len(ys))
    r={'g':f.split('/')[-1][:7],'map':g['map'],'rounds':g['final_round'],'sub':g['submitted']}
    for t in (0,1):
        caps=[c for c in g['captures'] if c[1]==t]
        r[f'capg{t}']=sum(c[4] for c in caps); r[f'capgold{t}']=sum(c[5] for c in caps); r[f'ncap{t}']=len(caps)
        ds=[d for d in g['deaths'] if d[1]==t]
        r[f'deaths{t}']=len(ds); r[f'lost{t}']=sum(d[4] for d in ds); r[f'campdeaths{t}']=sum(1 for d in ds if d[5]=='camp')
        bs=[b for b in g['banks'] if b[1]==t]
        r[f'banks{t}']=len(bs); r[f'bankg{t}']=sum(b[3] for b in bs)
        r[f'shops{t}']=sum(1 for s in g['shops'] if s[1]==t)
        fc=[c[0] for c in caps]; r[f'first{t}']=min(fc) if fc else 9999
        r[f'cap300_{t}']=sum(c[4] for c in caps if c[0]<=300)
        r[f'gold300_{t}']=sum(c[5] for c in caps if c[0]<=300)
    rows.append(r)
keys=[k for k in rows[0] if k[-1] in '01' and k not in ('g',)]
print('per game mean (us / them):')
for k in sorted(set(k[:-1] for k in keys)):
    a=st.mean(r[k+'0'] for r in rows); b=st.mean(r[k+'1'] for r in rows)
    print(f'  {k:10s} {a:8.1f} / {b:8.1f}')
print('submitted', st.mean(r['sub'][0] for r in rows), st.mean(r['sub'][1] for r in rows), 'rounds', st.mean(r['rounds'] for r in rows))
for r in rows:
    print(r['g'], r['map'][:14].ljust(14), 'sub %4d-%4d'%tuple(r['sub']), 'capg %3d-%4d'%(r['capg0'],r['capg1']), 'gold %4d-%4d'%(r['capgold0'],r['capgold1']), 'deaths %2d-%2d'%(r['deaths0'],r['deaths1']), 'lost %3d-%3d'%(r['lost0'],r['lost1']), 'banks %2d-%2d'%(r['banks0'],r['banks1']), 'first %d-%d'%(r['first0'],r['first1']))
