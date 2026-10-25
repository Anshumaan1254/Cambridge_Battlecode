import json,gzip,glob,collections,sys,statistics as st
S=json.load(open(sys.argv[1])); dec=sys.argv[2]
agg=collections.defaultdict(list)
for f in sorted(glob.glob(dec+'/*.json.gz')):
    k=f.split('/')[-1][:-8]
    if k not in S: continue
    ours=S[k]['ours']; d=json.load(gzip.open(f)); B=d['meta']['bodies']; camps=d['meta']['camps']
    ctile={(c['x'],c['y']):c for c in camps}
    # group camps by proximity? use capture events: CaptureGems by who at round r; hits on camp tiles within the 40 rounds before
    hits=collections.defaultdict(list)  # tile -> [(r, who)]
    for e in d['events']:
        if e['k'] in ('Attack','Cast ability') and e.get('to') and tuple(e['to']) in ctile and e.get('who') is not None:
            hits[tuple(e['to'])].append((e['r'],e['who']))
    for e in d['events']:
        if e['k']!='CaptureGems' or e['r']>600: continue
        w=e['who']; t=B[w]['team']; side='us' if t==ours else 'them'
        # find hits by this team in the 45 rounds before capture on camp tiles within 6 of capturer's position at capture
        # (approx: any camp tile hit by the team in window whose tile within 6 of capture position)
        cp=None
        for R in d['rounds']:
            if R['r']==e['r']:
                for c in R['ch']:
                    if c[0]==w: cp=(c[3],c[4])
                break
        if cp is None: continue
        hs=[(r,h) for tile,L in hits.items() if max(abs(tile[0]-cp[0]),abs(tile[1]-cp[1]))<=5 for (r,h) in L if e['r']-45<=r<=e['r'] and B[h]['team']==t]
        if not hs: continue
        bodies=len(set(h for _,h in hs)); span=max(r for r,_ in hs)-min(r for r,_ in hs)+1
        agg[(S[k]['opp'],side,'bodies')].append(bodies); agg[(S[k]['opp'],side,'span')].append(span); agg[(S[k]['opp'],side,'hits')].append(len(hs))
for k in sorted(agg): print(k, 'n',len(agg[k]),'mean %.2f median %.1f'%(st.mean(agg[k]),st.median(agg[k])))
