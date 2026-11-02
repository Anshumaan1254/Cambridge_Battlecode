import json, os, sys
ME='5a103c90-b00b-4d46-8ace-6a3bb058dc72'
sides=json.load(open('sides.json'))
pref, r0, r1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
mid=[f[:-5] for f in os.listdir('dec') if f.startswith(pref)][0]
d=json.load(open('dec/'+mid+'.json')); we=sides[mid]
bodies={b['index']:b for b in d['meta']['bodies']}
R={r['r']:r for r in d['rounds']}
ev=[e for e in d['events'] if r0<=e['r']<=r1 and e['k'] in ('Attack','Cast ability','Death') and 'who' in e]
byr={}
for e in ev: byr.setdefault(e['r'],[]).append(e)
for r in range(r0,r1+1):
    s=R.get(r)
    if not s: continue
    line=[]
    for c in s['ch']:
        if c[7]!=1: continue
        tag=('U' if c[1]==we else 'T')+bodies[c[0]]['type'][:3]
        line.append(f"{tag}{c[0]}({c[3]},{c[4]}){int(c[5])}")
    acts=[]
    for e in byr.get(r,[]):
        who=e['who']; tm='U' if bodies[who]['team']==we else 'T'
        if e['k']=='Attack':
            tgt=[c for c in s['ch'] if c[7]==1 and [c[3],c[4]]==e['to']]
            t=(('U' if tgt[0][1]==we else 'T')+str(tgt[0][0])) if tgt else 'camp'
            acts.append(f"{tm}{who}>{t}")
        elif e['k']=='Cast ability': acts.append(f"{tm}{who}*cast")
        else: acts.append(f"{tm}{who} DIES")
    print(r, ' '.join(line)); print('    ', ' '.join(acts))
