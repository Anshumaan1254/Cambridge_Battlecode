# Flatten tools/top2/opening/open_extract.mjs output + the t2 platform index rows into analysis tables (one row per team-game etc.).
#   python tools/top2/opening/open_flat.py OUTDIR EXTRACT.jsonl...
# Writes OUTDIR/teamgame.csv (one row per (study key, game, team)), bodies.csv (per body), caps.csv (captures r<=300),
# decisions.csv (post-capture decisions), banktrips.csv, eng.csv (engagements r<=300). Study keys / team names below.
import json, sys, os, glob, statistics as st
import pandas as pd

KEYS = {'pbg': 'prism best girl', 'ifish': 'Intercontinental Fish', 'pantheon': 'Pantheon', 'coo': 'conqueror_of_openai',
        'cm': 'Claudus Maximus', 'nyx': 'Nyx'}
T2 = 'C:/battlecode/cache/t2'
DRAFT = ['Ryth', 'VesperVale', 'Vendetta', 'CassiAndIssac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin']

def types_of(picks):
    out = []
    for p in picks:
        if p == 3: out += ['Cassi', 'Issac']
        else: out.append(DRAFT[p])
    return sorted(out)

def med(v):
    v = [x for x in v if x is not None]
    return st.median(v) if v else None

def main():
    outdir = sys.argv[1]; os.makedirs(outdir, exist_ok=True)
    ext = {}
    for f in sys.argv[2:]:
        for l in open(f, encoding='utf-8'):
            if not l.strip(): continue
            d = json.loads(l)
            if 'err' in d: continue
            ext[d['file']] = d
    rows, brows, crows, drows, trows, erows, tsrows = [], [], [], [], [], [], []
    miss = 0; bad = 0
    for key, name in KEYS.items():
        idx = os.path.join(T2, key, 'index.jsonl')
        if not os.path.exists(idx): continue
        for l in open(idx, encoding='utf-8'):
            m = json.loads(l)
            fname = f"{m['map']}_{m['matchId'][:8]}"
            d = ext.get(fname)
            if d is None: miss += 1; continue
            tm = [t for t in m['teams'] if t['name'] == name]
            if len(tm) != 1: bad += 1; continue
            me = tm[0]; op = [t for t in m['teams'] if t is not me][0]
            s = 0 if me['side'] == 'a' else 1
            # sanity: draft types match the dump's team s
            if types_of(me['draftPicks']) != sorted(d['teams'][s]['types']): bad += 1; continue
            won = 1 if me['result'] == 'win' else 0
            feat = d.get('feat') or {}
            area = d['W'] * d['H']
            for t in (0, 1):
                T = d['teams'][t]; O = d['teams'][1 - t]
                study = 1 if t == s else 0
                r = dict(key=key, map=d['map'], match=m['matchId'], mid8=d['mid8'], t=t, study=study,
                         team=me['name'] if study else op['name'], opp=op['name'] if study else me['name'],
                         won=won if study else 1 - won, n=T['n'], n_opp=O['n'], types='+'.join(sorted(T['types'])),
                         W=d['W'], H=d['H'], area=area, final=d['final'], s2s=feat.get('s2s'), midShare=feat.get('midShare'),
                         golem=feat.get('golem'), mono=feat.get('mono'), elk=feat.get('elk'), ngroups=feat.get('groups'),
                         altars=feat.get('altars'), allGems=feat.get('allGems'), gemRate=feat.get('gemRate'), mincut=feat.get('mincut'))
                r['hp0'] = T.get('hp0')
                bo = T['bodies']
                r['first_move_med'] = med([o['firstMove'] for o in bo])
                r['first_hit_team'] = T['firstHit']
                hits = [o['firstHit'] for o in bo if o['firstHit']]
                r['first_hit_med'] = med([h['r'] for h in hits])
                r['hit_d_med'] = med([h['d'] for h in hits])
                r['hit_cheb_med'] = med([h['cheb'] for h in hits])
                r['hit_rank_med'] = med([h['rank'] for h in hits])
                r['hit_vrank_med'] = med([h['vrank'] for h in hits])
                r['hit_nearest_share'] = sum(1 for h in hits if h['rank'] == 1) / len(hits) if hits else None
                for z in 'OMT': r[f'hit_zone_{z}'] = sum(1 for h in hits if h['zone'] == z) / len(hits) if hits else None
                for c in ['elk', 'gem', 'wolf', 'gold', 'golem', 'mono']: r[f'hit_cls_{c}'] = sum(1 for h in hits if h['cls'] == c) / len(hits) if hits else None
                r['hit_gems_med'] = med([h['gems'] for h in hits])
                sq = T['squads']
                r['squads'] = len(sq); r['squad_max'] = sq[0] if sq else 0; r['squad_max_share'] = sq[0] / T['n'] if sq else 0
                fc = T['firstCap']
                r['first_cap_r'] = fc['r'] if fc else None; r['first_cap_gems'] = fc['gems'] if fc else None
                r['first_cap_zone'] = fc['zone'] if fc else None; r['first_cap_cls'] = fc['cls'] if fc else None
                r['first_cap_hitters'] = fc['hitters'] if fc else None; r['first_cap_split'] = fc['split'] if fc else None
                r['first_cap_d'] = fc['d'] if fc else None
                r['first_mid_r'] = T['firstMid']; r['mid_bodies'] = T['midBodies']; r['first_mid_cap_r'] = T['firstMidCap']
                r['first_mid2_r'] = T.get('firstMid2'); r['first_mid3_r'] = T.get('firstMid3')
                for x in T.get('ts', []):
                    tsrows.append(dict(key=key, match=m['matchId'], map=d['map'], t=t, study=study, won=r['won'], n=T['n'], area=area, r=x[0],
                                       alive=x[1], mid=x[2], enemy=x[3], lcf=x[4], gold=x[5], capGems=x[6], midGems=x[7], banked=x[8],
                                       kills=x[9], deaths=x[10], hpGain=x[11]))
                fb = T['firstBank']
                r['first_bank_r'] = fb['r'] if fb else None; r['first_bank_gems'] = fb['gems'] if fb else None
                r['first_home_med'] = med([o['firstRecall'] for o in bo])
                r['first_shop_med'] = med([o['firstShop'] for o in bo])
                r['groups_hit100'] = sum(o['groupsHit100'] for o in bo) / T['n']
                r['groups_hit300'] = sum(o['groupsHit300'] for o in bo) / T['n']
                for cp, v in T['cp'].items():
                    for k2, x in v.items(): r[f'{k2}_{cp}'] = x
                for cp in ('100', '200', '300'):
                    if f'maxHp_{cp}' in r and r.get('hp0'): r[f'hpGain_{cp}'] = r[f'maxHp_{cp}'] - r['hp0']
                    if f'gold_{cp}' in r: r[f'spent_{cp}'] = r[f'gold_{cp}'] - r[f'held_{cp}']
                for w, v in T['win'].items():
                    if v is None: continue
                    for k2, x in v.items(): r[f'w{w}_{k2}'] = x
                # first fight (first engagement r<=300)
                eng = d['eng']
                if eng:
                    e = eng[0]
                    r['ff_r'] = e['r0']; r['ff_me_first'] = 1 if e['striker'] == t else 0
                    r['ff_zone_striker'] = e['zoneForStriker']; r['ff_dead_me'] = e['dead'][t]; r['ff_dead_opp'] = e['dead'][1 - t]
                    r['ff_dmg3_me'] = e['dmg3'][t]; r['ff_dmg3_opp'] = e['dmg3'][1 - t]; r['ff_dmg_me'] = e['dmg'][t]; r['ff_dmg_opp'] = e['dmg'][1 - t]
                    r['ff_near_me'] = e['near'][t]; r['ff_near_opp'] = e['near'][1 - t]; r['ff_part_me'] = e['part'][t]; r['ff_part_opp'] = e['part'][1 - t]
                    r['ff_result'] = 1 if e['dead'][1 - t] > e['dead'][t] else (0 if e['dead'][1 - t] < e['dead'][t] else 0.5)
                    r['ff_striker_type'] = e['strikerType']
                    # first engagement with a kill
                    ek = [x for x in eng if sum(x['dead']) > 0]
                    if ek:
                        x = ek[0]; r['fkf_r'] = x['r0']; r['fkf_me_first'] = 1 if x['striker'] == t else 0
                        r['fkf_result'] = 1 if x['dead'][1 - t] > x['dead'][t] else (0 if x['dead'][1 - t] < x['dead'][t] else 0.5)
                        r['fkf_near_me'] = x['near'][t]; r['fkf_near_opp'] = x['near'][1 - t]
                    r['n_eng'] = len(eng)
                    r['eng_me_first'] = sum(1 for x in eng if x['striker'] == t) / len(eng)
                    r['eng_won'] = sum(1 if x['dead'][1 - t] > x['dead'][t] else 0 for x in eng)
                    r['eng_lost'] = sum(1 if x['dead'][1 - t] < x['dead'][t] else 0 for x in eng)
                else:
                    r['n_eng'] = 0
                fk = d['firstKill']
                if fk and fk['r'] <= 300:
                    r['fk_r'] = fk['r']; r['fk_me'] = 1 if fk['killerTeam'] == t else 0; r['fk_zone_killer'] = fk['zoneForKiller']
                rows.append(r)
                base = dict(key=key, match=m['matchId'], map=d['map'], t=t, study=study, won=r['won'], n=T['n'], area=area)
                for o in bo:
                    h = o['firstHit'] or {}
                    brows.append(dict(base, type=o['type'], firstMove=o['firstMove'], hit_r=h.get('r'), hit_d=h.get('d'), hit_cheb=h.get('cheb'),
                                      hit_rank=h.get('rank'), hit_vrank=h.get('vrank'), hit_zone=h.get('zone'), hit_cls=h.get('cls'), hit_type=h.get('type'),
                                      hit_gems=h.get('gems'), hit_gold=h.get('gold'), hit_hp=h.get('hp'),
                                      cap_r=(o['firstCap'] or {}).get('r'), cap_gems=(o['firstCap'] or {}).get('gems'), cap_zone=(o['firstCap'] or {}).get('zone'),
                                      bank_r=(o['firstBank'] or {}).get('r'), bank_gems=(o['firstBank'] or {}).get('gems'), mid_r=o['firstMid'],
                                      home_r=o['firstRecall'], shop_r=o['firstShop'], death_r=(o['firstDeath'] or {}).get('r'),
                                      death_by=(o['firstDeath'] or {}).get('by'), g100=o['groupsHit100'], g300=o['groupsHit300']))
                for c in T['caps']:
                    crows.append(dict(base, r=c['r'], cls=c['cls'], zone=c['zone'], gems=c['gems'], gold=c['gold'], split=c['split'], hitters=c['hitters'],
                                      enemyHitters=c['enemyHitters'], killRounds=c['killRounds'], contested=c['contested'], d=c['d'], ad=c['ad']))
                for x in d['decisions']:
                    if x['t'] != t: continue
                    drows.append(dict(base, r=x['r'], type=x['type'], bag=x['bag'], gems=x['gems'], ad=x['ad'], next=x['next'], dr=x['dr'], zone=x['zone']))
                for x in d['bankTrips']:
                    if x['t'] != t: continue
                    trows.append(dict(base, r=x['r'], gems=x['gems'], fromCapR=x['fromCapR'], capAd=x['capAd'], viaHome=x['viaHome']))
                if t == s:
                    for i, x in enumerate(d['eng']):
                        erows.append(dict(key=key, match=m['matchId'], map=d['map'], won=won, idx=i, r0=x['r0'], rEnd=x['rEnd'],
                                          me_first=1 if x['striker'] == s else 0, zone_striker=x['zoneForStriker'], striker_type=x['strikerType'],
                                          victim_type=x['victimType'], dead_me=x['dead'][s], dead_opp=x['dead'][1 - s], dmg3_me=x['dmg3'][s],
                                          dmg3_opp=x['dmg3'][1 - s], dmg_me=x['dmg'][s], dmg_opp=x['dmg'][1 - s], near_me=x['near'][s], near_opp=x['near'][1 - s],
                                          nearHp_me=x['nearHp'][s], nearHp_opp=x['nearHp'][1 - s], part_me=x['part'][s], part_opp=x['part'][1 - s],
                                          first_death_team=('me' if x['firstDeathTeam'] == s else 'opp') if x['firstDeathTeam'] is not None else None))
    for nm, rr in [('teamgame', rows), ('bodies', brows), ('caps', crows), ('decisions', drows), ('banktrips', trows), ('eng', erows), ('ts', tsrows)]:
        pd.DataFrame(rr).to_csv(os.path.join(outdir, nm + '.csv'), index=False)
    print('rows', len(rows), 'bodies', len(brows), 'caps', len(crows), 'dec', len(drows), 'trips', len(trows), 'eng', len(erows), 'missing', miss, 'bad', bad)

main()
