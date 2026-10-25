# gap_g8: aggregate tools/top2/gap/gapx.mjs output (one line per game) into us-vs-them tables, by opponent and overall.
#   python tools/top2/gap/gapx_agg.py C:/battlecode/cache/gap_g8/gapx.jsonl [SECTION ...]
# Sections: open cp tb walks zones kinds cyc eff mv rec bank deaths maps (default: all). Writes nothing; prints tables.
import json, sys, collections, statistics as st
SIDES = json.load(open('/tmp/claude-0/-home-claude/f3877353-3092-5ac8-aae3-9269d426c2cd/scratchpad/sides.json', encoding='utf-8'))
rows = [json.loads(l) for l in open(sys.argv[1], encoding='utf-8') if l.strip()]
rows = [r for r in rows if 'T' in r]
SECT = set(sys.argv[2:]) or {'open', 'cp', 'tb', 'walks', 'zones', 'kinds', 'cyc', 'eff', 'mv', 'rec', 'bank', 'deaths', 'maps'}
OPP = {'CM':'CM','UoS':'UoS','G3':'G3','IC':'IC'}
for r in rows:
    S = SIDES[r['file']]
    r['opp'] = OPP[S['opp']]; r['us'] = r['T'][str(S['ours'])]; r['them'] = r['T'][str(1 - S['ours'])]; r['ours'] = S['ours']
    r['win'] = int(S['res'][S['ours']] == 'win'); r['map'] = S['map']
    r['nbU'] = r['nb'][S['ours']]; r['nbT'] = r['nb'][1 - S['ours']]
GRP = [('ALL', rows)] + [(o, [r for r in rows if r['opp'] == o]) for o in ('CM','UoS','G3','IC')]
def mean(xs):
    xs = [x for x in xs if x is not None and x == x]
    return sum(xs) / len(xs) if xs else float('nan')
def med(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else float('nan')
def line(label, f, groups=GRP, fmt='%7.1f', agg=None):
    agg = agg or mean
    cells = []
    for g, G in groups:
        cells.append(('%s ' + fmt + ' /' + fmt) % (g[:5].ljust(5), agg([f(r, 'us') for r in G]), agg([f(r, 'them') for r in G])))
    print('  %-34s %s' % (label, ' | '.join(cells)))
print('games', len(rows), {g: len(G) for g, G in GRP})

if 'open' in SECT:
    print('\n== OPENING (us / them)')
    for k in ('firstHit', 'firstCap', 'firstBank', 'firstMidCap'):
        line('team %s (median, none=2000)' % k, lambda r, s, k=k: r[s]['open'][k] if r[s]['open'][k] is not None else 2000, agg=med)
        line('team %s (share <= r100)' % k, lambda r, s, k=k: 1.0 if (r[s]['open'][k] or 9999) <= 100 else 0.0, fmt='%5.2f')
        line('team %s (share <= r300)' % k, lambda r, s, k=k: 1.0 if (r[s]['open'][k] or 9999) <= 300 else 0.0, fmt='%5.2f')
    line('body first move', lambda r, s: mean([b['firstMove'] for b in r[s]['open']['bodies']]))
    line('body first camp hit', lambda r, s: mean([b['firstHit'] if b['firstHit'] is not None else 300 for b in r[s]['open']['bodies']]))
    line('body first camp hit (median body)', lambda r, s: med([b['firstHit'] if b['firstHit'] is not None else 300 for b in r[s]['open']['bodies']]))
    line('body first hit distance', lambda r, s: mean([b['hitDist'] for b in r[s]['open']['bodies']]))
    line('body first capture (None=600)', lambda r, s: mean([b['firstCap'] if b['firstCap'] is not None else 600 for b in r[s]['open']['bodies']]))
    line('body first death r<300 share', lambda r, s: mean([1.0 if (b['firstDeath'] or 9999) < 300 else 0.0 for b in r[s]['open']['bodies']]), fmt='%5.2f')
    kinds = collections.Counter(); kindsT = collections.Counter()
    for r in rows:
        for b in r['us']['open']['bodies']: kinds[b['hitKind']] += 1
        for b in r['them']['open']['bodies']: kindsT[b['hitKind']] += 1
    print('  first camp-hit kind us', dict(kinds), 'them', dict(kindsT))
    # first kill of the game
    fk = [r for r in rows if r.get('firstKill')]
    for g, G in GRP:
        G2 = [r for r in G if r.get('firstKill')]
        byUs = [r for r in G2 if r['firstKill']['killerTeam'] == r['ours']]
        byThem = [r for r in G2 if r['firstKill']['killerTeam'] != r['ours']]
        print('  first kill %-5s: games %d with a kill %d, by us %d (wins %d), by them %d (wins %d); round med us-kill %s them-kill %s' % (
            g, len(G), len(G2), len(byUs), sum(r['win'] for r in byUs), len(byThem), sum(r['win'] for r in byThem),
            med([r['firstKill']['r'] for r in byUs]), med([r['firstKill']['r'] for r in byThem])))
    byThem = [r for r in fk if r['firstKill']['killerTeam'] != r['ours']]
    print('  first kill by them: victim', collections.Counter(r['firstKill']['victim'] for r in byThem).most_common(8))
    print('     killer', collections.Counter(r['firstKill']['killer'] for r in byThem).most_common(8))
    print('     zone (victim-relative)', collections.Counter(r['firstKill']['zoneVictim'] for r in byThem), 'mode', collections.Counter(r['firstKill']['mode'] for r in byThem))
    print('     al6==0 share %.2f  en6>al6+1 share %.2f  myMax/enMax %.2f  bag mean %.1f' % (
        mean([1.0 if r['firstKill']['al6'] == 0 else 0.0 for r in byThem]), mean([1.0 if (r['firstKill']['en6'] or 0) > (r['firstKill']['al6'] or 0) + 1 else 0.0 for r in byThem]),
        mean([r['firstKill']['myMax'] / r['firstKill']['enMax'] for r in byThem if r['firstKill']['enMax']]), mean([r['firstKill']['bag'] for r in byThem])))
    byUs = [r for r in fk if r['firstKill']['killerTeam'] == r['ours']]
    print('  first kill by us: victim', collections.Counter(r['firstKill']['victim'] for r in byUs).most_common(8), 'killer', collections.Counter(r['firstKill']['killer'] for r in byUs).most_common(8))
    # early deaths by killer kind
    for g, G in GRP:
        c = collections.Counter(); ct = collections.Counter()
        for r in G:
            for x in r['us']['deaths']:
                if x[0] < 300: c['camp' if x[2] == 'camp' else 'champ'] += 1
            for x in r['them']['deaths']:
                if x[0] < 300: ct['camp' if x[2] == 'camp' else 'champ'] += 1
        n = len(G)
        print('  deaths r<300 %-5s us camp %.2f champ %.2f | them camp %.2f champ %.2f' % (g, c['camp'] / n, c['champ'] / n, ct['camp'] / n, ct['champ'] / n))

if 'cp' in SECT:
    print('\n== CHECKPOINTS (us / them)')
    for cp in ('100', '200', '300', '400', '600', '800', '1000'):
        print(' r%s' % cp)
        for k in ('caps', 'capGems', 'capGold', 'banked', 'maxHp', 'se', 'gold', 'bag', 'deaths', 'campDeaths', 'kills'):
            line(k, lambda r, s, k=k, cp=cp: r[s]['cp'][cp][k] if cp in r[s]['cp'] else None)
        line('maxHp per body', lambda r, s, cp=cp: r[s]['cp'][cp]['maxHp'] / (r['nbU'] if s == 'us' else r['nbT']) if cp in r[s]['cp'] else None)
    # conditional outcomes
    print('  max-HP lead at r200 -> win rate / gem margin')
    for lab, f in (('ahead', lambda r: r['us']['cp']['200']['maxHp'] / r['nbU'] >= r['them']['cp']['200']['maxHp'] / r['nbT']),
                   ('behind', lambda r: r['us']['cp']['200']['maxHp'] / r['nbU'] < r['them']['cp']['200']['maxHp'] / r['nbT'])):
        G = [r for r in rows if '200' in r['us']['cp'] and f(r)]
        print('    %-7s n=%d wins %d margin %.0f' % (lab, len(G), sum(r['win'] for r in G), mean([r['sub'][r['ours']] - r['sub'][1 - r['ours']] for r in G])))
    print('  captured gems lead at r300 -> wins')
    for lab, f in (('ahead', lambda r: r['us']['cp']['300']['capGems'] >= r['them']['cp']['300']['capGems']), ('behind', lambda r: r['us']['cp']['300']['capGems'] < r['them']['cp']['300']['capGems'])):
        G = [r for r in rows if '300' in r['us']['cp'] and f(r)]
        print('    %-7s n=%d wins %d margin %.0f' % (lab, len(G), sum(r['win'] for r in G), mean([r['sub'][r['ours']] - r['sub'][1 - r['ours']] for r in G])))

if 'tb' in SECT:
    print('\n== TIME BUDGET (share of body-rounds; us / them)')
    KS = ['dead', 'farm', 'fight', 'trib', 'recall', 'oncamp', 'walk', 'spawn', 'idle']
    for ph in range(4):
        print(' phase', ph)
        for k in KS + ['walkNearEnemy', 'nearE', 'mid', 'mid_farm']:
            line(k, lambda r, s, k=k, ph=ph: (r[s]['tb'][ph][k] / max(1, sum(r[s]['tb'][ph][x] for x in KS))) if sum(r[s]['tb'][ph][x] for x in KS) > 0 else None, fmt='%6.3f')
        for k in ('farm', 'fight', 'walk', 'oncamp', 'idle', 'spawn', 'trib', 'recall'):
            line('nearE share ' + k, lambda r, s, k=k, ph=ph: r[s]['tb'][ph]['nearE_' + k] / r[s]['tb'][ph]['nearE'] if r[s]['tb'][ph]['nearE'] else None, fmt='%6.3f')
        line('nearE hp adv share', lambda r, s, ph=ph: r[s]['tb'][ph]['nearE_hpAdv'] / r[s]['tb'][ph]['nearE'] if r[s]['tb'][ph]['nearE'] else None, fmt='%6.3f')
    print(' whole game, rounds per body')
    for k in KS:
        line(k, lambda r, s, k=k: sum(r[s]['tb'][ph][k] for ph in range(4)) / (r['nbU'] if s == 'us' else r['nbT']))

if 'walks' in SECT:
    print('\n== WALKS r<1000 (walk rounds per body by next action)')
    for k in ('farm', 'fight', 'capture', 'bank', 'recall', 'shop', 'died', 'none'):
        line(k, lambda r, s, k=k: r[s]['walks'].get(k, 0) / (r['nbU'] if s == 'us' else r['nbT']))
    line('runs per body', lambda r, s: r[s]['walks']['n'] / (r['nbU'] if s == 'us' else r['nbT']))

if 'zones' in SECT:
    print('\n== CAPTURES BY ZONE (per game: caps / gems)')
    for z in 'OMT':
        line('caps ' + z, lambda r, s, z=z: sum(r[s]['zones'][ph][z][0] for ph in range(4)))
        line('gems ' + z, lambda r, s, z=z: sum(r[s]['zones'][ph][z][1] for ph in range(4)))
        for ph in range(4):
            line('  gems %s ph%d' % (z, ph), lambda r, s, z=z, ph=ph: r[s]['zones'][ph][z][1])

if 'kinds' in SECT:
    print('\n== CAPTURES BY GROUP KIND (per game)')
    for k in ('cluster', 'wolf', 'elk', 'golem', 'monolith'):
        line('caps ' + k, lambda r, s, k=k: r[s]['kinds'].get(k, {}).get('caps', 0))
        line('gems ' + k, lambda r, s, k=k: r[s]['kinds'].get(k, {}).get('gems', 0))
        line('gold ' + k, lambda r, s, k=k: r[s]['kinds'].get(k, {}).get('gold', 0))
    for k in ('golem', 'monolith'):
        G = [r for r in rows if r['groups']['kinds'].get(k)]
        print('  maps with %s: %d games; caps us %.2f them %.2f; first cap us %s them %s; hits us %.0f them %.0f; hitter-50r-windows us %.1f them %.1f' % (
            k, len(G), mean([r['us']['kinds'].get(k, {}).get('caps', 0) for r in G]), mean([r['them']['kinds'].get(k, {}).get('caps', 0) for r in G]),
            med([r['us']['kinds'][k]['first'] for r in G if k in r['us']['kinds']]), med([r['them']['kinds'][k]['first'] for r in G if k in r['them']['kinds']]),
            mean([r['us']['obj']['golemHits' if k == 'golem' else 'monoHits'] for r in G]), mean([r['them']['obj']['golemHits' if k == 'golem' else 'monoHits'] for r in G]),
            mean([r['us']['obj']['golemHitters' if k == 'golem' else 'monoHitters'] for r in G]), mean([r['them']['obj']['golemHitters' if k == 'golem' else 'monoHitters'] for r in G])))
        print('     maps', sorted(set(r['map'] for r in G)))

if 'cyc' in SECT:
    print('\n== FARMING CYCLES (per completed cycle: wait / kill / capture / respawn; medians, means)')
    for z in 'OMT':
        for s in ('us', 'them'):
            C = [c for r in rows for c in r[s]['cyc'][z]]
            if not C: continue
            print('  %s %-4s n=%5d (%.1f/game) wait med %s mean %.0f | kill med %s mean %.0f | cap med %s | respawn med %s' % (
                z, s, len(C), len(C) / len(rows), med([c[1] for c in C]), mean([c[1] for c in C]), med([c[2] for c in C]), mean([c[2] for c in C]),
                med([c[3] for c in C]), med([c[4] for c in C if c[4] is not None])))
    for k in ('cluster', 'wolf', 'elk', 'golem', 'monolith'):
        for s in ('us', 'them'):
            C = [c for r in rows for z in 'OMT' for c in r[s]['cyc'][z] if c[0] == k]
            if not C: continue
            print('  kind %-8s %-4s n=%5d kill med %s mean %.0f | wait med %s' % (k, s, len(C), med([c[2] for c in C]), mean([c[2] for c in C]), med([c[1] for c in C])))

if 'eff' in SECT:
    print('\n== CAMP EFFORTS (per game)')
    for k in ('own', 'stolen', 'aband', 'hitsOwn', 'hitsAband', 'hitsStolen', 'abandEnemyNear', 'abandDied', 'abandCampOnly'):
        line(k, lambda r, s, k=k: sum(r[s]['eff'][ph][k] for ph in range(4)))
        line('  r<300 ' + k, lambda r, s, k=k: r[s]['eff'][0][k])
    line('captured share of efforts', lambda r, s: (sum(r[s]['eff'][ph]['own'] for ph in range(4)) / max(1, sum(r[s]['eff'][ph][k] for ph in range(4) for k in ('own', 'stolen', 'aband')))), fmt='%6.3f')

if 'mv' in SECT:
    print('\n== MOVEMENT (per body per game)')
    for k in ('aba', 'abaE', 'loops', 'loopsE', 'idleRuns', 'stand40', 'stand40r', 'stand40camp', 'spawnIdle'):
        line(k, lambda r, s, k=k: r[s]['mv'][k] / (r['nbU'] if s == 'us' else r['nbT']), fmt='%7.2f')
    line('stand40max (per game)', lambda r, s: r[s]['mv']['stand40max'])

if 'rec' in SECT:
    print('\n== RECALLS (per game)')
    for k in ('starts', 'done', 'killed', 'interrupted', 'nearE', 'nearE_done'):
        line(k, lambda r, s, k=k: r[s]['rec'][k])

if 'bank' in SECT:
    print('\n== BANKING (per game)')
    for k in ('tribStarts', 'tribDone', 'banks', 'banked', 'lostAtDeath', 'bag50', 'bag100', 'bag200', 'maxBag'):
        line(k, lambda r, s, k=k: r[s]['bank'][k])
    line('mean bank size', lambda r, s: mean(r[s]['bank']['bankSizes']) if r[s]['bank']['bankSizes'] else None)
    line('first bank (none=2000)', lambda r, s: r[s]['bank']['firstBank'] or 2000)
    line('tribute cancelled', lambda r, s: r[s]['bank']['tribStarts'] - r[s]['bank']['tribDone'])

if 'deaths' in SECT:
    print('\n== DEATHS (per game)')
    def dl(r, s): return r[s]['deaths']
    line('deaths', lambda r, s: len(dl(r, s)))
    for ph, (a, b) in enumerate(((0, 300), (300, 600), (600, 1000), (1000, 9999))):
        line('  deaths ph%d' % ph, lambda r, s, a=a, b=b: sum(1 for x in dl(r, s) if a <= x[0] < b))
    line('to camps', lambda r, s: sum(1 for x in dl(r, s) if x[2] == 'camp'))
    for z in ('O', 'M', 'T', 'TS'):
        line('zone ' + z, lambda r, s, z=z: sum(1 for x in dl(r, s) if x[3] == z))
    for m in ('fight', 'farm', 'move', 'channel', 'idle'):
        line('mode ' + m + ' (champion kills)', lambda r, s, m=m: sum(1 for x in dl(r, s) if x[5] == m and x[2] != 'camp'))
    line('isolated (no ally within 6)', lambda r, s: sum(1 for x in dl(r, s) if x[2] != 'camp' and x[7] == 0))
    line('outnumbered (en6 > al6+1)', lambda r, s: sum(1 for x in dl(r, s) if x[2] != 'camp' and x[8] > x[7] + 1))
    line('bag lost', lambda r, s: sum(x[4] for x in dl(r, s)))
    line('bag lost to champions', lambda r, s: sum(x[4] for x in dl(r, s) if x[2] != 'camp'))
    line('deaths with bag >= 50', lambda r, s: sum(1 for x in dl(r, s) if x[4] >= 50))
    line('victim max / killers mean max', lambda r, s: mean([x[11] / x[12] for x in dl(r, s) if x[12]]), fmt='%6.2f')
    line('local hp within 8 ours/theirs', lambda r, s: mean([x[13] / x[14] for x in dl(r, s) if x[14]]), fmt='%6.2f')
    line('hp3 share', lambda r, s: mean([x[6] for x in dl(r, s) if x[6] is not None and x[2] != 'camp']), fmt='%6.2f')
    c = collections.Counter(); ct = collections.Counter()
    for r in rows:
        for x in r['us']['deaths']: c[x[1]] += 1
        for x in r['them']['deaths']: ct[x[1]] += 1
    print('  our deaths by victim type', c.most_common()); print('  their deaths by victim type', ct.most_common())
    c = collections.Counter()
    for r in rows:
        for x in r['us']['deaths']: c[x[2]] += 1
    print('  our deaths by killer', c.most_common())

if 'maps' in SECT:
    print('\n== PER MAP (us/them): banked, capGems r300, maxHp/body r300, deaths, kills, mid gems, walk%, farm%, aba/body')
    bym = collections.defaultdict(list)
    for r in rows: bym[r['map']].append(r)
    L = []
    for m, G in bym.items():
        L.append((mean([r['sub'][r['ours']] - r['sub'][1 - r['ours']] for r in G]), m, G))
    KS = ['dead', 'farm', 'fight', 'trib', 'recall', 'oncamp', 'walk', 'spawn', 'idle']
    def share(r, s, k): tot = sum(r[s]['tb'][ph][x] for ph in range(4) for x in KS); return sum(r[s]['tb'][ph][k] for ph in range(4)) / tot
    for marg, m, G in sorted(L, reverse=True):
        f = lambda s, fn: mean([fn(r, s) for r in G])
        print('  %-22s w%d %4.0f/%4.0f cg300 %3.0f/%3.0f hp300 %4.0f/%4.0f d %4.1f/%4.1f mid %3.0f/%3.0f walk %.2f/%.2f farm %.2f/%.2f dead %.2f/%.2f aba %3.0f/%3.0f' % (
            m, sum(r['win'] for r in G), f('us', lambda r, s: r['sub'][r['ours']]), f('them', lambda r, s: r['sub'][1 - r['ours']]),
            f('us', lambda r, s: r[s]['cp'].get('300', {}).get('capGems', 0)), f('them', lambda r, s: r[s]['cp'].get('300', {}).get('capGems', 0)),
            f('us', lambda r, s: r[s]['cp'].get('300', {}).get('maxHp', 0) / r['nbU']), f('them', lambda r, s: r[s]['cp'].get('300', {}).get('maxHp', 0) / r['nbT']),
            f('us', lambda r, s: len(r[s]['deaths'])), f('them', lambda r, s: len(r[s]['deaths'])),
            f('us', lambda r, s: sum(r[s]['zones'][ph]['M'][1] for ph in range(4))), f('them', lambda r, s: sum(r[s]['zones'][ph]['M'][1] for ph in range(4))),
            f('us', lambda r, s: share(r, s, 'walk')), f('them', lambda r, s: share(r, s, 'walk')), f('us', lambda r, s: share(r, s, 'farm')), f('them', lambda r, s: share(r, s, 'farm')),
            f('us', lambda r, s: share(r, s, 'dead')), f('them', lambda r, s: share(r, s, 'dead')),
            f('us', lambda r, s: r[s]['mv']['aba'] / r['nbU']), f('them', lambda r, s: r[s]['mv']['aba'] / r['nbT'])))
