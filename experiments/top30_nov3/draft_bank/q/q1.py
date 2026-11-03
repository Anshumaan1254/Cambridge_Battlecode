# quick like-with-like queries on teams.jsonl: map gem class x group, loss-conditioned
import json,collections,sys
rows=[json.loads(l) for l in open('/home/claude/cambridge_battlecode/experiments/top30_nov3/draft_bank/out/teams.jsonl')]
print(collections.Counter((r['grp'],r['res']) for r in rows))
def cls(r):
    g=r.get('map_gems') or 0
    return 'lowgem<=260' if g<=260 else 'gem>260'
keys=['captured','sub','sub_en','kills','deaths','gems_lost','deaths_bag20','carried_end','n_sub','bag_mean','final','locks','gold']
def agg(sel,label):
    n=len(sel)
    if n==0: return
    out=[f'{label:34s} n={n:4d} win%={100*sum(r["res"]=="win" for r in sel)/n:5.1f}']
    for k in keys:
        v=[r.get(k) for r in sel if r.get(k) is not None]
        out.append(f'{k}={sum(v)/max(1,len(v)):.1f}')
    print(' '.join(out))
for c in ['lowgem<=260','gem>260']:
    print('==',c)
    for grp in ['top30','ours_v88','ours_v84','opp']:
        for res in ['loss','win']:
            agg([r for r in rows if r['grp']==grp and r['res']==res and cls(r)==c], f'{grp}/{res}')
# worst maps list
bad=set('00crater 01elk_arena 03ambush_field 00gemfight 00oasis 01islands 00rushbait_v2 00quarry 00elkring 00gem_fields'.split())
print('== the 10 worst maps')
for grp in ['top30','ours_v88','ours_v84','opp']:
    for res in ['loss','win']:
        agg([r for r in rows if r['grp']==grp and r['res']==res and r['map'] in bad], f'{grp}/{res}')
print('== other maps')
for grp in ['top30','ours_v88','ours_v84','opp']:
    for res in ['loss','win']:
        agg([r for r in rows if r['grp']==grp and r['res']==res and r['map'] not in bad], f'{grp}/{res}')
