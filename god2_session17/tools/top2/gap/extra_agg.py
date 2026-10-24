# gap_g8: the remaining tables of experiments/top2/gap_g8.md (python only; reads the outputs of compact_agg.py, gapx.mjs, campdps.mjs,
# strat_bank.mjs and the fight dumps):
#   A per-champion platform metrics (gold, gems, deaths, kills, camp / champion damage)      B item spend by family / stat, first buys
#   C gold income split (captures, kills, other)                                            D camp damage per farm round by champion and phase
#   E farm / walk share with and without an enemy within 8, by phase                       F banking profile (strat_bank)
#   G max health by champion type at r100/300/600/1000 (dumps)                              H low-contact games vs all
#   I per map table with map features + correlations                                        J our 13 wins
#   python tools/top2/gap/extra_agg.py
import json, collections, math, gzip, os
C_DIR = 'C:/battlecode/cache/gap_g8'
S = json.load(open(C_DIR + '/sides.json', encoding='utf-8'))
OPP = {'prism best girl': 'PBG', 'Intercontinental Fish': 'IFish', 'Claudus Maximus': 'CM'}
C = {json.loads(l)['game']: json.loads(l) for l in open(C_DIR + '/compact_games.jsonl', encoding='utf-8')}
X = {json.loads(l)['file']: json.loads(l) for l in open(C_DIR + '/gapx.jsonl', encoding='utf-8')}
D = {json.loads(l)['file']: json.loads(l) for l in open(C_DIR + '/campdps.jsonl', encoding='utf-8')}
BK = {json.loads(l)['file'].replace('.repl26a', ''): json.loads(l) for l in open(C_DIR + '/bank.jsonl', encoding='utf-8')}
F = json.load(open('C:/battlecode/Cambridge_Battlecode/experiments/top2/draft_mapfeat.json'))
def m(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float('nan')
def corr(a, b):
    ma, mb = m(a), m(b)
    sa = math.sqrt(sum((x - ma) ** 2 for x in a)); sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb) if sa and sb else 0

print('== A per champion (platform summary metrics, per body-game)')
agg = collections.defaultdict(collections.Counter); cnt = collections.Counter()
for g, v in S.items():
    d = json.load(open('C:/battlecode/Cambridge_Battlecode/experiments/live/compact/%s.json' % v['match'], encoding='utf-8'))
    tk = 'teamA' if v['ours'] == 0 else 'teamB'
    for c in d['champs']:
        k = ('us' if c['team'] == tk else 'them:' + OPP[v['opp']], c['name'])
        cnt[k] += 1
        for mm, x in c['m'].items(): agg[k][mm] += x
print('%-12s %-14s %4s %7s %7s %6s %6s %6s %7s %7s %7s' % ('team', 'champ', 'n', 'goldE', 'gemsC', 'subm', 'deaths', 'kills', 'monDmg', 'chDmg', 'chTaken'))
for k in sorted(cnt, key=lambda k: (k[0], -cnt[k])):
    n = cnt[k]; a = agg[k]
    print('%-12s %-14s %4d %7.0f %7.0f %6.0f %6.2f %6.2f %7.0f %7.0f %7.0f' % (k[0], k[1], n, a['earnedGold'] / n, a['collectedGems'] / n, a['submittedGems'] / n, a['deaths'] / n, a['kills'] / n, a['monsterDamageDone'] / n, a['championDamageDone'] / n, a['championDamageTaken'] / n))

print('\n== B item spend by family / stat and first buys')
for o in ('PBG', 'IFish', 'CM'):
    G = [r for g, r in C.items() if OPP[S[g]['opp']] == o]
    for who in ('us', 'them'):
        fam = collections.Counter(); stat = collections.Counter(); fb = collections.Counter()
        for r in G:
            for k, v in r[who]['spend_fam'].items(): fam[k] += v
            for k, v in r[who]['spend_stat'].items(): stat[k] += v
            for rr, nm in r[who]['first_buys']: fb[nm] += 1
        tot = sum(fam.values())
        print('  %-5s %-4s fam %s | stat %s | first buys %s' % (o, who, {k: round(v / tot, 2) for k, v in fam.most_common()}, {k: round(v / tot, 2) for k, v in stat.most_common()}, fb.most_common(4)))

print('\n== C gold income split per game')
for who in ('us', 'them'):
    capg = []; kill = []; earn = []
    for g, c in C.items():
        t = str(S[g]['ours'] if who == 'us' else 1 - S[g]['ours'])
        capg.append(sum(v['gold'] for v in X[g]['T'][t]['kinds'].values())); kill.append(c[who]['kills_n'] * 100); earn.append(c[who]['earnedGold'])
    print('  %-4s earned %.0f | captured gold %.0f | kill gold %.0f | other (tribute gold, refunds, ...) %.0f' % (who, m(earn), m(capg), m(kill), m(earn) - m(capg) - m(kill)))

print('\n== D camp damage per farm round (dpf) and farm share of alive rounds, phases r<300 / 300-600 / 600-1000 / 1000+')
agg = collections.defaultdict(lambda: [[0] * 4 for _ in range(4)])
for g, r in D.items():
    U = S[g]['ours']
    for b in r['bodies']:
        who = 'us' if b['team'] == U else 'them'
        for key in ((who, b['type']), (who, 'ALL')):
            A = agg[key]
            for ph in range(4):
                A[0][ph] += b['dmg'][ph]; A[1][ph] += b['farm'][ph]; A[2][ph] += b['alive'][ph]; A[3][ph] += b['taken'][ph]
for key in sorted(agg, key=lambda k: (k[1] != 'ALL', k[0], k[1])):
    A = agg[key]
    if sum(A[1]) < 500: continue
    print('  %-4s %-12s dpf %s | farm/alive %s | camp damage taken per farm round %s' % (key[0], key[1], ' '.join('%4.0f' % (A[0][p] / max(1, A[1][p])) for p in range(4)),
          ' '.join('%.2f' % (A[1][p] / max(1, A[2][p])) for p in range(4)), ' '.join('%3.0f' % (A[3][p] / max(1, A[1][p])) for p in range(4))))
for who in ('us', 'them'):
    print('  camp damage per game %-4s %.0f' % (who, sum(sum(b['dmg']) for g, r in D.items() for b in r['bodies'] if (b['team'] == S[g]['ours']) == (who == 'us')) / len(D)))

print('\n== E farm / walk with and without an enemy within 8 (share of alive body-rounds)')
KS = ['farm', 'fight', 'trib', 'recall', 'oncamp', 'walk', 'spawn', 'idle']
for ph in (0, 1, 2, 3, 'all'):
    for who in ('us', 'them'):
        A = collections.Counter()
        for g, r in X.items():
            t = str(S[g]['ours'] if who == 'us' else 1 - S[g]['ours'])
            for p in (range(4) if ph == 'all' else [ph]):
                T = r['T'][t]['tb'][p]
                for k in KS: A[k] += T[k]; A['n_' + k] += T['nearE_' + k]
                A['nearE'] += T['nearE']
        alive = sum(A[k] for k in KS); ne = A['nearE']; far = alive - ne
        print('  ph %-3s %-4s enemy within 8 in %.3f of alive rounds | no enemy: farm %.3f walk %.3f oncamp %.3f | enemy near: farm %.3f walk %.3f fight %.3f oncamp %.3f' % (
            ph, who, ne / alive, (A['farm'] - A['n_farm']) / far, (A['walk'] - A['n_walk']) / far, (A['oncamp'] - A['n_oncamp']) / far, A['n_farm'] / ne, A['n_walk'] / ne, A['n_fight'] / ne, A['n_oncamp'] / ne))

print('\n== F banking profile (tools/live/strat_bank.mjs on the dumps)')
for o in ('ALL', 'PBG', 'IFish', 'CM'):
    G = [g for g in BK if o == 'ALL' or OPP[S[g]['opp']] == o]
    for k in ('firstBank', 'banks', 'banked', 'maxBag', 'lostBag', 'carriedEnd', 'tribStarts', 'locks', 'bag300', 'bag600', 'bigBagRounds'):
        u = [BK[g]['T'][str(S[g]['ours'])][k] for g in G]; t = [BK[g]['T'][str(1 - S[g]['ours'])][k] for g in G]
        if k == 'firstBank': u = [x if x is not None else 2000 for x in u]; t = [x if x is not None else 2000 for x in t]
        print('  %-5s %-12s us %7.1f them %7.1f' % (o, k, m(u), m(t)))

print('\n== G max health by champion type (fight dumps)')
CP = [100, 300, 600, 1000]
mh = collections.defaultdict(lambda: collections.defaultdict(list))
for g, v in S.items():
    d = json.load(gzip.open('C:/battlecode/cache/t2dump/s0/%s.json.gz' % g))
    T = {b['index']: b for b in d['meta']['bodies']}
    R = {x[0]: x[3] for x in d['R']}
    for cp in CP:
        for c in R.get(cp, []):
            b = T[c[0]]; mh[('us' if b['team'] == v['ours'] else 'them') + ' ' + b['type']][cp].append(c[4])
for k in sorted(mh):
    print('  %-18s %s' % (k, '  '.join('r%d %5.0f (n%d)' % (cp, m(mh[k][cp]), len(mh[k][cp])) for cp in CP if mh[k][cp])))

print('\n== H low-contact games (both teams <= 4 deaths) vs all')
low = [g for g, c in C.items() if c['us']['deaths_n'] <= 4 and c['them']['deaths_n'] <= 4]
KS2 = ['dead'] + KS
for lab, G in (('low-contact', low), ('all', list(C))):
    print('  %s: %d games, wins %d, maps %s' % (lab, len(G), sum(C[g]['win'] for g in G), dict(collections.Counter(S[g]['map'] for g in G).most_common(6)) if lab != 'all' else ''))
    for who in ('us', 'them'):
        tb = collections.Counter(); dmg = farm = 0; caps = gems = 0; kinds = collections.Counter(); zones = collections.Counter()
        for g in G:
            t = str(S[g]['ours'] if who == 'us' else 1 - S[g]['ours'])
            for ph in range(4):
                for k in KS2: tb[k] += X[g]['T'][t]['tb'][ph][k]
                for z in 'OMT': caps += X[g]['T'][t]['zones'][ph][z][0]; gems += X[g]['T'][t]['zones'][ph][z][1]; zones[z] += X[g]['T'][t]['zones'][ph][z][1]
            for b in D[g]['bodies']:
                if (b['team'] == S[g]['ours']) == (who == 'us'): dmg += sum(b['dmg']); farm += sum(b['farm'])
            for k, v in X[g]['T'][t]['kinds'].items(): kinds[k] += v['gems']
        tot = sum(tb.values())
        print('    %-4s camp gems/round %.2f | shares %s | dpf %.0f | gems/capture %.1f | caps/game %.1f | gems by zone %s | by kind %s' % (
            who, m([C[g][who]['coll_camp'] / C[g]['rounds'] for g in G]), ' '.join('%s %.3f' % (k, tb[k] / tot) for k in KS2), dmg / farm, gems / caps, caps / len(G),
            {z: round(v / len(G)) for z, v in zones.items()}, {k: round(v / len(G)) for k, v in kinds.most_common()}))

print('\n== I per map (sorted by our gem share) + map features')
bym = collections.defaultdict(list)
for g in C: bym[S[g]['map']].append(g)
rows = []
for mp, G in bym.items():
    def mm(f): return m([f(g) for g in G])
    def ne(g):
        t = str(S[g]['ours']); A = sum(X[g]['T'][t]['tb'][p]['nearE'] for p in range(4)); al = sum(X[g]['T'][t]['tb'][p][k] for p in range(4) for k in KS); return A / al
    def midT(g):
        t = str(1 - S[g]['ours']); tot = sum(X[g]['T'][t]['zones'][p][z][1] for p in range(4) for z in 'OMT'); return sum(X[g]['T'][t]['zones'][p]['M'][1] for p in range(4)) / max(1, tot)
    rows.append(dict(map=mp, share=mm(lambda g: C[g]['us']['gems'] / (C[g]['us']['gems'] + C[g]['them']['gems'])), wins=sum(C[g]['win'] for g in G),
                     gu=mm(lambda g: C[g]['us']['gems']), gt=mm(lambda g: C[g]['them']['gems']), du=mm(lambda g: C[g]['us']['deaths_n']), dt=mm(lambda g: C[g]['them']['deaths_n']),
                     ne=mm(ne), midT=mm(midT), banks=mm(lambda g: C[g]['us']['banks']), lost=mm(lambda g: C[g]['us']['lost_gems']), fb=mm(lambda g: C[g]['us']['first_bank'] or 2000),
                     fuel=mm(lambda g: C[g]['us']['fuel']), **{k: F[mp][k] for k in ('gemrate', 'area', 'altars', 'monoGemShare', 'golemGemShare', 'size', 's2s')}))
rows.sort(key=lambda r: -r['share'])
print('  %-22s %5s %3s %9s %9s %5s %6s %6s %6s %5s %5s %5s %6s %5s %4s %5s' % ('map', 'share', 'win', 'gems', 'deaths', 'nearE', 'midT', 'gemrt', 'area', 'alt', 'mono', 'bnkU', 'lostU', '1stbU', 'size', 'fuel'))
for r in rows:
    print('  %-22s %5.2f %3d %4.0f/%4.0f %4.1f/%4.1f %5.2f %6.2f %6.1f %6d %5d %5.2f %5.1f %6.0f %5.0f %4d %5.1f' % (r['map'], r['share'], r['wins'], r['gu'], r['gt'], r['du'], r['dt'], r['ne'], r['midT'], r['gemrate'], r['area'], r['altars'], r['monoGemShare'], r['banks'], r['lost'], r['fb'], r['size'], r['fuel']))
for k in ('ne', 'du', 'dt', 'midT', 'gemrate', 'area', 'altars', 'monoGemShare', 'golemGemShare', 'size', 's2s', 'fuel'):
    print('  corr(share, %s) = %+.2f' % (k, corr([r['share'] for r in rows], [r[k] for r in rows])))
for lab, R in (('closest 8', rows[:8]), ('worst 12', rows[-12:])):
    print('  %s: share %.2f, deaths %.1f/%.1f, enemy within 8 %.2f of our alive time, their middle gem share %.2f, gemrate %.1f, area %.0f' % (
        lab, m([r['share'] for r in R]), m([r['du'] for r in R]), m([r['dt'] for r in R]), m([r['ne'] for r in R]), m([r['midT'] for r in R]), m([r['gemrate'] for r in R]), m([r['area'] for r in R])))

print('\n== J our wins')
for g, c in sorted(C.items()):
    if not c['win']: continue
    U = str(S[g]['ours']); T = str(1 - S[g]['ours'])
    print('  %-28s %-14s r%4d %4d-%4d | deaths %d/%d (camp %d/%d) | kills %d/%d | camp gems %d/%d | bags lost %d/%d | their max bag %d, carried at end %d' % (
        g, S[g]['opp'][:14], c['rounds'], c['us']['gems'], c['them']['gems'], c['us']['deaths_n'], c['them']['deaths_n'], c['us']['deaths_camp'], c['them']['deaths_camp'],
        c['us']['kills_n'], c['them']['kills_n'], c['us']['coll_camp'], c['them']['coll_camp'], c['us']['lost_gems'], c['them']['lost_gems'], BK[g]['T'][T]['maxBag'], BK[g]['T'][T]['carriedEnd']))
