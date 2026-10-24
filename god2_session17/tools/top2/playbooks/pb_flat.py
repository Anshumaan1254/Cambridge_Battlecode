# Flatten pb_extract.mjs games into one row per (study team, game, side X in S/O) with game-flow features -> pandas pickle.
#   python tools/top2/playbooks/pb_flat.py   -> C:/battlecode/cache/top2_playbooks/flat.pkl
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import pandas as pd
from pbcommon import load_all, BASE

WN = ['w1', 'w2', 'w3', 'w4', 'w5']


def feats(g, X, R):
    """X = team dict (S or O), R = its roles."""
    f = {}
    n = X['n']
    tot = {k: 0 for k in ['caps', 'capGems', 'capGold', 'deaths', 'kills', 'bagLost', 'bagStolen', 'banks', 'bankGems', 'recallsDone', 'recallEv',
                          'shops', 'wards', 'locks', 'dmgOut', 'dmgIn', 'campDmg', 'goldIn', 'goldSpent', 'holds', 'holdR', 'aliveBR', 'deadBR']}
    capZ = {'own': 0, 'mid': 0, 'their': 0}
    capC = {'cluster': 0, 'wolf': 0, 'elk': 0, 'golem': 0, 'mono': 0}
    zoneT = {'own': 0, 'mid': 0, 'their': 0}
    actT = {k: 0 for k in ['farm', 'fight', 'walk', 'idle', 'bank', 'home']}
    wardZ = {'own': 0, 'mid': 0, 'their': 0}
    for i, w in enumerate(X['win']):
        p = WN[i]
        br = w['aliveBR'] + w['deadBR']
        for k in tot:
            tot[k] += w[k]
        for z in capZ:
            capZ[z] += w['capZ'][z]
            zoneT[z] += w['zone'][z]
            wardZ[z] += w['wardZ'][z]
        for c in capC:
            capC[c] += w['capC'][c]
        for a in actT:
            actT[a] += w['act'][a]
        if br == 0:
            continue
        al = max(1, w['aliveBR'])
        rounds = br / n
        f[f'{p}_dead'] = w['deadBR'] / br
        for z in ['own', 'mid', 'their']:
            f[f'{p}_z_{z}'] = w['zone'][z] / al
        for a in ['farm', 'fight', 'walk', 'idle', 'bank', 'home']:
            f[f'{p}_a_{a}'] = w['act'][a] / al
        f[f'{p}_adv'] = w['adv']
        if w['cohR']:
            f[f'{p}_coh'] = w['coh'] / w['cohR']
            f[f'{p}_cohN'] = w['coh'] / w['cohR'] / n
            f[f'{p}_squads'] = w['squads'] / w['cohR']
            f[f'{p}_tog3'] = w['together3'] / w['cohR']
        per100 = 100 / rounds
        for k in ['caps', 'capGems', 'deaths', 'kills', 'banks', 'bankGems', 'wards', 'locks', 'dmgOut', 'dmgIn', 'goldIn', 'campDmg']:
            f[f'{p}_{k}100'] = w[k] * per100
        f[f'{p}_recall100b'] = w['recallsDone'] * per100 / n
        f[f'{p}_shops100b'] = w['shops'] * per100 / n
        f[f'{p}_capMid'] = w['capZ']['mid'] / w['capGems'] if w['capGems'] else None
        f[f'{p}_capTheir'] = w['capZ']['their'] / w['capGems'] if w['capGems'] else None
    final = g['final']
    f.update({f'tot_{k}': v for k, v in tot.items()})
    al = max(1, tot['aliveBR'])
    for z in zoneT:
        f[f'all_z_{z}'] = zoneT[z] / al
    for a in actT:
        f[f'all_a_{a}'] = actT[a] / al
    f['all_dead'] = tot['deadBR'] / max(1, tot['aliveBR'] + tot['deadBR'])
    cg = max(1, tot['capGems'])
    for z in capZ:
        f[f'capZ_{z}'] = capZ[z] / cg
    for c in capC:
        f[f'capC_{c}'] = capC[c] / cg
    f['wardsMidTheir'] = (wardZ['mid'] + wardZ['their']) / max(1, sum(wardZ.values()))
    f['gemsPerCap'] = tot['capGems'] / max(1, tot['caps'])
    f['gemsPerBank'] = tot['bankGems'] / max(1, tot['banks'])
    f['recallSpam'] = tot['recallEv'] / max(1, tot['recallsDone'])
    f['recalls1000b'] = tot['recallsDone'] * 1000 / final / n
    f['shops1000b'] = tot['shops'] * 1000 / final / n
    f['deaths1000'] = tot['deaths'] * 1000 / final
    f['kills1000'] = tot['kills'] * 1000 / final
    f['caps1000'] = tot['caps'] * 1000 / final
    f['capGems1000'] = tot['capGems'] * 1000 / final
    f['wards1000'] = tot['wards'] * 1000 / final
    f['locks'] = tot['locks']
    f['locksGuard'] = sum(1 for x in X['ev']['locks'] if x['kind'] == 'guard')
    f['locksOff'] = sum(1 for x in X['ev']['locks'] if x['kind'] == 'offense')
    f['bagLost'] = tot['bagLost']
    f['bagStolen'] = tot['bagStolen']
    f['bagLostShare'] = tot['bagLost'] / max(1, tot['capGems'])
    ev = X['ev']
    for k in ['firstCap', 'firstMidCap', 'firstTheirCap', 'firstKill', 'firstDeath', 'firstContact', 'r500', 'r1000', 'firstHitMed',
              'adv20', 'adv40', 'adv60', 'adv100', 'adv150', 'tribStarts', 'tribDone', 'firstGroupHitters']:
        f[k] = ev.get(k)
    f['firstGroupCls'] = ev.get('firstGroupCls')
    f['firstGroupZone'] = ev.get('firstGroupZone')
    f['tribRate'] = ev['tribDone'] / ev['tribStarts'] if ev['tribStarts'] else None
    bt = ev['bigTrib']
    f['bigTrib'] = len(bt)
    f['bigTribDone'] = sum(x['done'] for x in bt)
    f['bigTribGems'] = sum(x['bag'] for x in bt if x['done'])
    # caps list [r, gems, gold, z, cls, near, enear, who]
    caps = ev['caps']
    for cut in [100, 200, 300, 600]:
        f[f'caps_r{cut}'] = sum(1 for c in caps if c[0] <= cut)
        f[f'capGems_r{cut}'] = sum(c[1] for c in caps if c[0] <= cut)
    f['capNear'] = sum(c[5] for c in caps) / len(caps) if caps else None
    f['capContested'] = sum(1 for c in caps if c[6] > 0) / len(caps) if caps else None
    # banks list [r, gems, type2, z]
    bl = ev['banksList']
    f['bankOwnShare'] = sum(b[1] for b in bl if b[3] == 'o') / max(1, sum(b[1] for b in bl))
    f['bankMidShare'] = sum(b[1] for b in bl if b[3] == 'm') / max(1, sum(b[1] for b in bl))
    f['firstBank'] = bl[0][0] if bl else None
    lb = ev.get('lastBank')
    f['lastBankGems'] = lb['gems'] if lb else None
    f['lastBankType'] = lb['type'] if lb else None
    f['maxBankShare'] = max((b[1] for b in bl), default=0) / max(1, sum(b[1] for b in bl))
    # largest single bank and share of total banked in banks >= 150
    f['bigBankShare'] = sum(b[1] for b in bl if b[1] >= 150) / max(1, sum(b[1] for b in bl))
    # checkpoints
    for c in [100, 200, 300, 400, 500, 600, 800, 1000]:
        cp = X['cp'].get(str(c))
        if cp:
            f[f'sub{c}'] = cp['sub']
            f[f'maxHp{c}'] = cp['maxHp']
            f[f'carry{c}'] = cp['carry']
            f[f'maxBag{c}'] = cp['maxBag']
    # roles
    tc = max(R, key=lambda x: x['capGems']) if R else None
    totc = sum(x['capGems'] for x in R)
    f['topCapType'] = tc['type'] if tc else None
    f['topCapShare'] = tc['capGems'] / totc if tc and totc else None
    tb = max(R, key=lambda x: x['banked']) if R else None
    totb = sum(x['banked'] for x in R)
    f['topBankType'] = tb['type'] if tb else None
    f['topBankShare'] = tb['banked'] / totb if tb and totb else None
    mb = max(R, key=lambda x: x['maxBag']) if R else None
    f['maxBag'] = mb['maxBag'] if mb else 0
    f['maxBagType'] = mb['type'] if mb else None
    # objectives
    obj = ev['obj']
    f['objHit'] = sum(1 for o in obj if o['firstHit'] is not None)
    f['objCaps'] = sum(len(o['caps']) for o in obj)
    f['objECaps'] = sum(len(o['ecaps']) for o in obj)
    fo = [c for o in obj for c in o['caps']]
    f['objFirstCap'] = min(fo) if fo else None
    f['golemCaps'] = sum(len(o['caps']) for o in obj if o['cls'] == 'golem')
    f['monoCaps'] = sum(len(o['caps']) for o in obj if o['cls'] == 'mono')
    hit = [o for o in obj if o['firstHit'] is not None]
    f['objHitters'] = max((o['hitters'] for o in hit), default=None)
    f['objFirstHit'] = min((o['firstHit'] for o in hit), default=None)
    return f


def main():
    games = load_all()
    rows = []
    for key, gs in games.items():
        for g in gs:
            base = {'key': key, 'file': g['file'], 'map': g['map'], 'win': g['win'], 'opp': g['opp'], 'n': g['n'], 'size': g['size'], 'obj': g['obj'],
                    'final': g['final'], 'W': g['W'], 'H': g['H'], 's2s': (g.get('geo') or {}).get('s2s'), 'midShareMap': (g.get('geo') or {}).get('midShare'),
                    'draftS': ','.join(g['draftS']), 'draftO': ','.join(g['draftO']), 'scoreS': g['submitted'][g['s']], 'scoreO': g['submitted'][1 - g['s']],
                    'side': g['s'], 'endReason': g['endReason']}
            for X, R, lab in [(g['S'], g['rolesS'], 'S'), (g['O'], g['rolesO'], 'O')]:
                row = dict(base)
                row['X'] = lab
                row.update(feats(g, X, R))
                rows.append(row)
    df = pd.DataFrame(rows)
    df.to_pickle(f'{BASE}/flat.pkl')
    print(df.shape)


if __name__ == '__main__':
    main()
