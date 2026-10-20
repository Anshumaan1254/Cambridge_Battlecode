import json,sys,glob,os,collections
D=sys.argv[1]
for f in sorted(glob.glob(D+'/*.json')):
    d=json.load(open(f)); m=d['meta']; R=d['rounds']; E=d['events']
    us=0
    name=os.path.basename(f)[:-5]
    def banked(r):
        for x in R:
            if x['r']>=r: return x['sub']
        return R[-1]['sub']
    deaths=[0,0]; caps=[collections.Counter(),collections.Counter()]; capg=[0,0]; capgold=[0,0]; kills=[0,0]; firstcap=[None,None]
    camps=m['camps']
    def near(at):
        best=None;bd=1e9
        for c in camps:
            dd=max(abs(c['x']-at[0]),abs(c['y']-at[1]))
            if dd<bd: bd=dd;best=c['type']
        return best
    for e in E:
        if e['k']=='Death': deaths[e['team']]+=1
        if e['k']=='CaptureGems':
            t=e['team']; caps[t][near(e['at'])]+=1; capg[t]+=e['gems']; capgold[t]+=e['gold']
            if firstcap[t] is None: firstcap[t]=e['r']
    steps=collections.Counter((e.get('team'),e['k']) for e in E)
    print(f"{name} {m['width']}x{m['height']} c{m['champsPerTeam']} fin r{m['finalRound']} sub {m['submitted']} us {','.join(m['drafts'][0])} | them {','.join(m['drafts'][1])}")
    print(f"   banked r200 {banked(200)} r400 {banked(400)} r600 {banked(600)} r800 {banked(800)}; deaths {deaths}; capgems {capg}; firstcap {firstcap}")
    print(f"   caps us {dict(caps[0])} | them {dict(caps[1])}")
    print(f"   casts {steps[(0,'Cast ability')]}/{steps[(1,'Cast ability')]} attacks {steps[(0,'Attack')]}/{steps[(1,'Attack')]} recalls {steps[(0,'Recall')]}/{steps[(1,'Recall')]} shop {steps[(0,'Shop')]}/{steps[(1,'Shop')]} wards {steps[(0,'Place ward')]}/{steps[(1,'Place ward')]} cons {steps[(0,'Consumable')]}/{steps[(1,'Consumable')]} rollover {steps[(0,'Turn rollover')]}/{steps[(1,'Turn rollover')]}")
