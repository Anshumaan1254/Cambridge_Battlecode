#!/usr/bin/env python3
"""Ladder snapshot: our rank / rating, the live version, the ranked record since a given ISO time (default: last 6 hours), by opponent rating band,
and the Elo-expected score. Appends one line to loop_log.md.   python3 ladder_check.py [--since ISO] [--pages 3]"""
import json, subprocess, sys, glob, collections, datetime, os
ME='5a103c90-b00b-4d46-8ace-6a3bb058dc72'
here=os.path.dirname(os.path.abspath(__file__))
since = sys.argv[sys.argv.index('--since')+1] if '--since' in sys.argv else (datetime.datetime.utcnow()-datetime.timedelta(hours=6)).strftime('%Y-%m-%dT%H:%M:%S')
pages = int(sys.argv[sys.argv.index('--pages')+1]) if '--pages' in sys.argv else 3
subprocess.run(['python3', os.path.join(here,'fetch_me.py'), '--pages', str(pages)], capture_output=True)
rating={}
for p in range(1,10):
    r=subprocess.run(['cambc','ladder','--page',str(p),'--limit','100','--json'],capture_output=True,text=True)
    try: d=json.loads(r.stdout)
    except Exception: continue
    for t in d['teams']: rating[t['teamId']]=(t['rank'],t['name'],t['rating'])
mine=rating.get(ME,(0,'?',0))
live=subprocess.run(['cambc','submissions','list'],capture_output=True,text=True).stdout.splitlines()[:2]
rows=[json.loads(l) for l in open(os.path.join(here,'matches_me.jsonl'))]
bands=collections.defaultdict(lambda:[0,0]); exp=0; got=0; n=0
for m in rows:
    if m['kind']!='ranked' or m['status']!='finished' or m['createdAt']<since: continue
    me=[t for t in m['teams'] if t['teamId']==ME][0]; op=[t for t in m['teams'] if t['teamId']!=ME][0]
    r=rating.get(op['teamId'])
    if not r: continue
    w=me['result']=='win'; b=int(r[2]//50*50); bands[b][0]+=w; bands[b][1]+=1
    exp+=1/(1+10**((r[2]-mine[2])/400)); got+=w; n+=1
line=f"{datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M')}Z rank {mine[0]} rating {mine[2]:.0f} | {live[1] if len(live)>1 else ''} | since {since}: {got}/{n} ({100*got/max(1,n):.0f}%), Elo-expected {exp:.1f} | bands " + ' '.join(f"{b}:{v[0]}/{v[1]}" for b,v in sorted(bands.items()))
print(line)
open(os.path.join(here,'loop_log.md'),'a').write(line+'\n')
