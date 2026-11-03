"""Per game and side: captures (count, gems, gold) and banked gems by champion type; Marcella's share. -> out/marc.jsonl"""
import json, collections
B='/home/claude/cambridge_battlecode/experiments/ladder_nov2'
P='/home/claude/cambridge_battlecode/experiments/top30_nov3/nemesis/out/profiles.jsonl'
for l in open(P):
    g=json.loads(l); we=g['we']
    d=json.load(open(f"{B}/dec/{g['mid']}.json"))
    team={b['index']:b['team'] for b in d['meta']['bodies']}; typ={b['index']:b['type'] for b in d['meta']['bodies']}
    o={'mid':g['mid'],'opp':g['opp'],'res':g['res'],'map':g['map']}
    for s in ('we','they'):
        o[s]={'cap_n':collections.Counter(),'cap_gems':collections.Counter(),'cap_gold':collections.Counter(),'bank':collections.Counter(),'bank600':collections.Counter(),'bank_n':collections.Counter()}
    for e in d['events']:
        w=e.get('who')
        if w is None: continue
        s='we' if team[w]==we else 'they'; t=typ[w]
        if e['k']=='CaptureGems':
            o[s]['cap_n'][t]+=1; o[s]['cap_gems'][t]+=e['gems']; o[s]['cap_gold'][t]+=e['gold']
        elif e['k']=='Banked':
            o[s]['bank'][t]+=e['gems']; o[s]['bank_n'][t]+=1
            if e['r']<=600: o[s]['bank600'][t]+=e['gems']
    print(json.dumps(o))
