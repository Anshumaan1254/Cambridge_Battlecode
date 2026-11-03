#!/usr/bin/env python3
"""Per game (profiles.jsonl games): gold captured per side by r300/r600, shop events, teleports, altar locks and the tributes
they cancelled, our tributes cancelled (any cause), and bank sizes. Usage: nice python3 -I goldlocks.py > ../out/goldlocks.jsonl"""
import json, sys
B='/home/claude/cambridge_battlecode/experiments/ladder_nov2'
P='/home/claude/cambridge_battlecode/experiments/top30_nov3/nemesis/out/profiles.jsonl'
for l in open(P):
    g=json.loads(l); we=g['we']
    d=json.load(open(f"{B}/dec/{g['mid']}.json"))
    team={b['index']:b['team'] for b in d['meta']['bodies']}
    o={'mid':g['mid'],'opp':g['opp'],'res':g['res'],'map':g['map'],'we':we}
    side=lambda t:'we' if t==we else 'they'
    for s in ('we','they'):
        for k in ('gold300','gold600','gold','gems_from_gold_groups','shop','shop300','tp','tp_mid','locks','lock_cancel','lock_cancel_gems','sub','sub_fail','sub_fail_gems','banked_n'):
            o[f'{k}_{s}']=0
    ev=d['events']
    subs=[]  # (r, who, altar)
    banks={}  # who -> list of rounds banked
    locks=[]
    for e in ev:
        k=e['k']; w=e.get('who')
        if k=='CaptureGems':
            s=side(team[w]); o[f'gold_{s}']+=e['gold']
            if e['r']<=300: o[f'gold300_{s}']+=e['gold']
            if e['r']<=600: o[f'gold600_{s}']+=e['gold']
        elif k=='Shop' and w is not None:
            s=side(team[w]); o[f'shop_{s}']+=1
            if e['r']<=300: o[f'shop300_{s}']+=1
        elif k=='Teleport complete':
            o[f'tp_{side(team[w])}']+=1
        elif k=='Place altar lock':
            o[f'locks_{side(team[w])}']+=1; locks.append((e['r'],team[w],tuple(e['to']),w))
        elif k=='Submit gems':
            subs.append((e['r'],w,tuple(e['to'])))
        elif k=='Banked':
            banks.setdefault(w,[]).append((e['r'],e['gems']))
    # body bag per round for gem size of a failed tribute
    S={rr['r']:{c[0]:c for c in rr['ch']} for rr in d['rounds'][1:]}
    seen=set()
    for (r,w,alt) in subs:
        key=(w,alt)
        # collapse repeated submit calls (lock hits) within 8 rounds
        if any((w,alt,r2) in seen for r2 in range(r-8,r)):
            seen.add((w,alt,r)); continue
        seen.add((w,alt,r))
        s=side(team[w]); o[f'sub_{s}']+=1
        ok=any(r<=rb<=r+10 for rb,_ in banks.get(w,[]))
        if not ok:
            bag=S.get(r,{}).get(w,[0]*9)[8]
            o[f'sub_fail_{s}']+=1; o[f'sub_fail_gems_{s}']+=bag
            # cancelled by a lock of the other team on that altar placed within [r-1, r+6]?
            if any(lt!=team[w] and la==alt and r-1<=lr<=r+6 for lr,lt,la,lw in locks):
                o[f'lock_cancel_{side(1-team[w])}']+=1; o[f'lock_cancel_gems_{side(1-team[w])}']+=bag
    for w,bl in banks.items():
        o[f'banked_n_{side(team[w])}']+=len(bl)
    print(json.dumps(o), flush=True)
