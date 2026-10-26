"""Reward steals: for each capture, the share of the damage on that camp cluster (since its previous capture) dealt by each team.
A capture by X of a cluster where the other team dealt most of the damage is a steal. python -I steals.py SIDES.json DECDIR [MAXR]"""
import gzip, json, sys, os, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools', 'analysis'))
import choice_model as cm
S = json.load(open(sys.argv[1])); dec = sys.argv[2]; MR = int(sys.argv[3]) if len(sys.argv) > 3 else 9999; cheb = cm.cheb
T = collections.Counter(); n = 0
for k, v in S.items():
    d = json.load(gzip.open(os.path.join(dec, k + '.json.gz'))); o = v['ours']; n += 1
    camps = d['meta']['camps']; cl, ncl = cm.clusters_of(camps); cpos = {(c['x'], c['y']): i for i, c in enumerate(camps)}
    R = {s['r']: s for s in d['rounds']}; rs = sorted(R)
    hits = collections.defaultdict(list)
    for e in d['events']:
        if e['k'] in ('Attack', 'Cast ability') and 'team' in e and e.get('to') and tuple(e['to']) in cpos:
            hits[e['r']].append((e['team'], cpos[tuple(e['to'])]))
    dmg = collections.defaultdict(lambda: [0.0, 0.0])  # cluster -> damage by team since last capture
    caps = collections.defaultdict(list)
    for e in d['events']:
        if e['k'] == 'CaptureGems' and 'team' in e: caps[e['r']].append(e)
    for i in range(1, len(rs)):
        r0, r1 = rs[i - 1], rs[i]
        if r1 > MR: break
        h0, h1 = R[r0]['campHp'], R[r1]['campHp']
        for c in range(len(camps)):
            dl = h0[c] - h1[c]
            if dl <= 0: continue
            who = [t for t, ci in hits.get(r1, []) if ci == c]
            for t in who: dmg[cl[c]][t] += dl / len(who)
        seen = set()
        for e in caps.get(r1, []):
            ci = min(range(len(camps)), key=lambda j: cheb(tuple(e['at']), (camps[j]['x'], camps[j]['y'])))
            g = cl[ci]
            side = 'us' if e['team'] == o else 'them'
            dd = dmg[g]; tot = dd[0] + dd[1]
            if tot <= 0: continue
            mine = dd[e['team']] / tot
            T[side + '_gems'] += e['gems']
            if mine < 0.5: T[side + '_stolen_gems'] += e['gems']
            T[side + '_mine_share_x_gems'] += mine * e['gems']
            if (g, r1) not in seen: seen.add((g, r1))
        for e in caps.get(r1, []):
            ci = min(range(len(camps)), key=lambda j: cheb(tuple(e['at']), (camps[j]['x'], camps[j]['y'])))
            dmg[cl[ci]] = [0.0, 0.0]
    # damage dealt by each team overall on clusters that the OTHER team captured = lost work
print(n, 'games', 'up to round', MR)
for s in ('us', 'them'):
    g = T[s + '_gems']
    print('%-4s captured gems/game %.0f | of which on clusters the other team damaged most (steals) %.0f (%.0f%%) | own-damage share weighted %.2f' % (s, g / n, T[s + '_stolen_gems'] / n, 100 * T[s + '_stolen_gems'] / max(1, g), T[s + '_mine_share_x_gems'] / max(1, g)))
