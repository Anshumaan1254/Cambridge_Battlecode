# execution metrics split by map class (gems per champion on the map <= 92 = scarce) and side group
import json,os,collections,csv
D='/home/claude/cambridge_battlecode/experiments/top30_nov3/execution/'
mt={r['map']:r for r in csv.DictReader(open(D+'out/map_table.tsv'),delimiter='\t')}
agg=collections.defaultdict(lambda: collections.defaultdict(list))
for f in os.listdir(D+'out/met'):
    d=json.load(open(D+'out/met/'+f))
    m=mt.get(d['map'])
    if not m: continue
    gpc=float(m['gems'])/float(m['champs'])
    cls='scarce' if gpc<=92 else 'rich'
    for t,s in d['sides'].items():
        t=int(t)
        if d['tag']=='top': grp='top_W' if d['winner']==t else 'top_L'
        elif d['tag']=='v88': grp='we_v88' if t==d['we'] else 'opp_v88'
        else: grp=('we_old' if t==d['we'] else 'opp_old')
        A=agg[(cls,grp)]
        kl=s['kill_list']
        A['kills_g'].append(len(kl))
        A['att'].extend(k[6] for k in kl)
        A['big_att'].extend(k[6] for k in kl if k[2]>=30)
        A['solo_share'].extend(1.0 if k[6]<=1 else 0.0 for k in kl if k[2]>=12)
        for k in ['deaths','passive_dmg','aba_pure','wake_leave_solo','stall12','banked','collected','dash_wasted']:
            A[k].append(s.get(k,0))
        A['win'].append(1.0 if d['winner']==t else 0.0)
def m(v): return sum(v)/max(1,len(v))
for cls in ['scarce','rich']:
    print('==',cls,'(gems per champion on the map',('<= 92' if cls=='scarce' else '> 92'),')')
    for grp in ['top_W','top_L','we_v88','opp_v88','we_old','opp_old']:
        A=agg[(cls,grp)]
        if not A['win']: continue
        print(f"{grp:8s} n={len(A['win']):3d} win {m(A['win']):.2f} group kills/g {m(A['kills_g']):5.1f} attackers/kill {m(A['att']):.2f} big(>=30g) {m(A['big_att']):.2f} solo share(>=12g) {m(A['solo_share']):.2f} deaths {m(A['deaths']):5.1f} passive {m(A['passive_dmg']):6.0f} aba_pure {m(A['aba_pure']):5.1f} wakeleave_solo {m(A['wake_leave_solo']):.1f} collected {m(A['collected']):5.0f} banked {m(A['banked']):5.0f}")
