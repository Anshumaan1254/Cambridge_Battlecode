import json,os,collections,statistics as st,sys
since=sys.argv[1] if len(sys.argv)>1 else '2026-10-25T10:37'
ms={json.loads(l)['matchId']:json.loads(l) for l in open('/home/claude/cambridge_battlecode/experiments/ladder_oct25_v15/matches_me.jsonl')}
rows=[]
for mid,m in ms.items():
    if m['createdAt']<since or m['status']!='finished': continue
    f=f'/tmp/claude-0/v15dl/sum/match-{mid}.json'
    if not os.path.exists(f): continue
    j=json.load(open(f))
    me=[t for t in m['teams'] if t['name']=='HouseOfCoders'][0]; o=[t for t in m['teams'] if t['name']!='HouseOfCoders'][0]
    us='team'+me['side'].upper()
    agg={'us':collections.Counter(),'them':collections.Counter()}
    for c in j['champions']:
        s='us' if c['team']==us else 'them'
        for k in ('deaths','kills','earnedGold','submittedGems','collectedGems','monsterDamageDone','championDamageDone'):
            agg[s][k]+=float(c['metrics'][k])
    rows.append((me['result'],o['name'],m['map'],agg,int(j['match']['roundsCompleted']),m['kind']))
print(len(rows),'games with summaries since',since)
for res in ('win','loss'):
    R=[r for r in rows if r[0]==res]
    if not R: continue
    f=lambda s,k: st.mean(r[3][s][k] for r in R)
    print(res, len(R), ' '.join(f"{k}: {f('us',k):.0f}/{f('them',k):.0f}" for k in ('deaths','earnedGold','collectedGems','submittedGems','monsterDamageDone','championDamageDone')), 'rounds', round(st.mean(r[4] for r in R)))
c=collections.Counter(r[2] for r in rows if r[0]=='loss'); w=collections.Counter(r[2] for r in rows if r[0]=='win')
print('maps (loss, win):', ', '.join(f'{k} {c[k]}-{w[k]}' for k in sorted(set(c)|set(w), key=lambda k:-c[k])))
