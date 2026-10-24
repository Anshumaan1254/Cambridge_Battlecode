# gap_g8: aggregate tools/top2/gap/killers.mjs output: our deaths by killer champion and killing blow, damage sources before deaths,
# stuns before deaths, champion damage dealt by champion / ability, camp damage per team. By opponent.
#   python tools/top2/gap/killers_agg.py C:/battlecode/cache/gap_g8/killers.jsonl
import json, sys, collections
SIDES = json.load(open('C:/battlecode/cache/gap_g8/sides.json', encoding='utf-8'))
OPP = {'prism best girl': 'PBG', 'Intercontinental Fish': 'IFish', 'Claudus Maximus': 'CM'}
rows = []
for l in open(sys.argv[1], encoding='utf-8'):
    if not l.strip(): continue
    r = json.loads(l)
    if 'err' in r: continue
    S = SIDES[r['file']]
    r['U'] = S['ours']; r['opp'] = OPP[S['opp']]
    rows.append(r)
GRP = [('ALL', rows)] + [(o, [r for r in rows if r['opp'] == o]) for o in ('PBG', 'IFish', 'CM')]
for g, G in GRP:
    n = len(G)
    du = [x for r in G for x in r['deaths'] if x['t'] == r['U'] and not x['linked']]
    dt = [x for r in G for x in r['deaths'] if x['t'] != r['U'] and not x['linked']]
    print('== %s (%d games): our deaths %.2f/game (non-linked), theirs %.2f' % (g, n, len(du) / n, len(dt) / n))
    print('   our deaths by killer:', ', '.join('%s %.2f' % (k, v / n) for k, v in collections.Counter(x['by'] for x in du).most_common(10)))
    print('   killing blow on us:', ', '.join('%s %.2f' % (k, v / n) for k, v in collections.Counter((x['by'] + ':' + str(x['kb'])) for x in du).most_common(12)))
    print('   their deaths by killer:', ', '.join('%s %.2f' % (k, v / n) for k, v in collections.Counter(x['by'] for x in dt).most_common(10)))
    print('   our victims (types):', ', '.join('%s %.2f' % (k, v / n) for k, v in collections.Counter(x['v'] for x in du).most_common(10)))
    src = collections.Counter()
    for x in du:
        for k, v in x['src'].items(): src[k] += v
    tot = sum(src.values())
    print('   damage on our dying bodies (10 rounds before) by source share:', ', '.join('%s %.0f%%' % (k, 100 * v / tot) for k, v in src.most_common(12)))
    print('   stunned in the 5 rounds before death: us %.0f%% (by %s) | them %.0f%%' % (
        100 * sum(1 for x in du if x['stuns']) / max(1, len(du)), collections.Counter(s for x in du for s in x['stuns']).most_common(6),
        100 * sum(1 for x in dt if x['stuns']) / max(1, len(dt))))
    print('   victim dealt champion damage in its last 10 rounds: us %.0f (0 in %.0f%%) | them %.0f (0 in %.0f%%); attackers us %.2f them %.2f' % (
        sum(x['own'] for x in du) / max(1, len(du)), 100 * sum(1 for x in du if x['own'] == 0 and x['by'] != 'camp') / max(1, sum(1 for x in du if x['by'] != 'camp')),
        sum(x['own'] for x in dt) / max(1, len(dt)), 100 * sum(1 for x in dt if x['own'] == 0 and x['by'] != 'camp') / max(1, sum(1 for x in dt if x['by'] != 'camp')),
        sum(x['natk'] for x in du if x['by'] != 'camp') / max(1, sum(1 for x in du if x['by'] != 'camp')), sum(x['natk'] for x in dt if x['by'] != 'camp') / max(1, sum(1 for x in dt if x['by'] != 'camp'))))
    dU = collections.Counter(); dT = collections.Counter()
    for r in G:
        for k, v in r['dealt'][str(r['U'])].items(): dU[k] += v
        for k, v in r['dealt'][str(1 - r['U'])].items(): dT[k] += v
    print('   champion damage dealt per game: us %.0f, them %.0f' % (sum(dU.values()) / n, sum(dT.values()) / n))
    print('     us  :', ', '.join('%s %.0f' % (k, v / n) for k, v in dU.most_common(12)))
    print('     them:', ', '.join('%s %.0f' % (k, v / n) for k, v in dT.most_common(12)))
    print('   camp damage per game: us %.0f them %.0f' % (sum(r['campDealt'][str(r['U'])] for r in G) / n, sum(r['campDealt'][str(1 - r['U'])] for r in G) / n))
