import json, collections, sys
ME='5a103c90-b00b-4d46-8ace-6a3bb058dc72'
rows=[json.loads(l) for l in open('matches_me.jsonl')]; info={m['matchId']:m for m in rows}
games=[json.loads(l) for l in open('all_games.jsonl')]
for g in games:
    m=info[g['file'][:-5]]; me=[t for t in m['teams'] if t['teamId']==ME][0]; g['win']= me['result']=='win'
def agg(G):
    n=len(G)
    if n==0: return {}
    r={'n':n}
    r['banked']=(sum(g['sub'][g['we']] for g in G)/n, sum(g['sub'][1-g['we']] for g in G)/n)
    r['deaths']=(sum(len(g['deaths']['we']) for g in G)/n, sum(len(g['deaths']['they']) for g in G)/n)
    r['kills_by_camp']=(sum(1 for g in G for x in g['deaths']['we'] if x['killer']=='camp')/n,)
    r['camp_hits']=(sum(g['hits']['we']['camp'] for g in G)/n, sum(g['hits']['they']['camp'] for g in G)/n)
    r['banks']=(sum(len(g['banks']['we']) for g in G)/n, sum(len(g['banks']['they']) for g in G)/n)
    r['gold']=(sum(g['gold']['we'] for g in G)/n, sum(g['gold']['they'] for g in G)/n)
    b=lambda side,k: sum(g['budget'][side].get(k,0) for g in G)/n
    r['walk_near']=(b('we','walk_near'), b('they','walk_near')); r['camp']=(b('we','camp'), b('they','camp')); r['dead']=(b('we','dead'),b('they','dead')); r['capture']=(b('we','capture'),b('they','capture')); r['idle']=(b('we','idle')+b('we','idle_near'), b('they','idle')+b('they','idle_near'))
    r['mid_caps']=(sum(G_['cap_we'] for g in G for G_ in g['groups'] if G_['zone_we']=='M')/n, sum(G_['cap_they'] for g in G for G_ in g['groups'] if G_['zone_we']=='M')/n)
    r['own_caps']=(sum(G_['cap_we'] for g in G for G_ in g['groups'] if G_['zone_we']=='O')/n, sum(G_['cap_they'] for g in G for G_ in g['groups'] if G_['zone_we']=='O')/n)
    r['their_half_caps']=(sum(G_['cap_we'] for g in G for G_ in g['groups'] if G_['zone_we']=='T')/n, sum(G_['cap_they'] for g in G for G_ in g['groups'] if G_['zone_we']=='T')/n)
    r['lost_on_death']=(sum(g['gems_lost']['we'] for g in G)/n, sum(g['gems_lost']['they'] for g in G)/n)
    r['lured_rounds']=(sum(g['lure']['they_lured_us']['rounds'] for g in G)/n, sum(g['lure']['we_lured_them']['rounds'] for g in G)/n)
    return r
maps = sys.argv[1:] if len(sys.argv)>1 else sorted(set(g['map'] for g in games))
for mp in maps:
    L=[g for g in games if g['map']==mp and not g['win']]; W=[g for g in games if g['map']==mp and g['win']]
    print('====', mp, 'losses', len(L), 'wins', len(W))
    for lab,G in (('LOSS',L),('WIN',W)):
        a=agg(G)
        if a: print('  ',lab, ' '.join(f"{k}={tuple(round(x) for x in v) if isinstance(v,tuple) else v}" for k,v in a.items()))
