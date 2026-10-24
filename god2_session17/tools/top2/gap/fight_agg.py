# gap_g8: aggregate tools/live/fightan.mjs output over the S0 dumps (us = g8 vs the three top teams), by opponent.
#   python tools/top2/gap/fight_agg.py C:/battlecode/cache/gap_g8/fightan.jsonl
# Engagements (champion damage clustered <= 6 rounds, <= 10 tiles): starter, local max-health ratio at the start (within 8 of the first
# hit), deaths, first-3-round damage, focus; contacts (who strikes first); deaths (fightan modes, isolation, idle allies, bags).
import json, sys, collections, statistics as st
SIDES = json.load(open('C:/battlecode/cache/gap_g8/sides.json', encoding='utf-8'))
OPP = {'prism best girl': 'PBG', 'Intercontinental Fish': 'IFish', 'Claudus Maximus': 'CM'}
rows = []
for l in open(sys.argv[1], encoding='utf-8'):
    if not l.strip(): continue
    r = json.loads(l)
    if 'err' in r: continue
    S = SIDES[r['game']]
    r['U'] = S['ours']; r['opp'] = OPP[S['opp']]; r['win'] = int(S['res'][S['ours']] == 'win'); r['map'] = S['map']
    rows.append(r)
GRP = [('ALL', rows)] + [(o, [r for r in rows if r['opp'] == o]) for o in ('PBG', 'IFish', 'CM')]
def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float('nan')
print('games', len(rows))

print('\n== ENGAGEMENTS (>= 3 hits or a death)')
for g, G in GRP:
    n = len(G)
    E = [(r, e) for r in G for e in r['engs'] if sum(e['hits']) >= 3 or sum(e['dE']) > 0]
    us = [(r, e) for r, e in E if e['first']['team'] == r['U']]
    th = [(r, e) for r, e in E if e['first']['team'] != r['U']]
    def dd(L, who):  # deaths of us / them inside the engagements
        return sum(e['dE'][r['U'] if who == 'us' else 1 - r['U']] for r, e in L)
    print('  %-5s per game: started by us %.1f (our deaths %.2f, theirs %.2f) | by them %.1f (our deaths %.2f, theirs %.2f)' % (
        g, len(us) / n, dd(us, 'us') / n, dd(us, 'them') / n, len(th) / n, dd(th, 'us') / n, dd(th, 'them') / n))
    print('        per engagement: we start -> our d %.2f their d %.2f | they start -> our d %.2f their d %.2f' % (
        dd(us, 'us') / max(1, len(us)), dd(us, 'them') / max(1, len(us)), dd(th, 'us') / max(1, len(th)), dd(th, 'them') / max(1, len(th))))
# by local max-health ratio (ours / theirs within 8 at the start)
print('\n  by local max-health ratio ours/theirs within 8 of the first hit (all opponents):')
B = [(0, 0.67), (0.67, 0.87), (0.87, 1.15), (1.15, 1.5), (1.5, 99)]
for g, G in GRP:
    E = [(r, e) for r in G for e in r['engs'] if sum(e['hits']) >= 3 or sum(e['dE']) > 0]
    print('   ', g)
    for a, b in B:
        L = []
        for r, e in E:
            st_ = e['first']['team']
            mh = e['loc8']['mh']  # [starter side, other side]
            ours = mh[0] if st_ == r['U'] else mh[1]
            theirs = mh[1] if st_ == r['U'] else mh[0]
            if theirs <= 0: continue
            q = ours / theirs
            if a <= q < b: L.append((r, e))
        if not L: continue
        du = sum(e['dE'][r['U']] for r, e in L); dt = sum(e['dE'][1 - r['U']] for r, e in L)
        su = sum(1 for r, e in L if e['first']['team'] == r['U'])
        print('      ratio %.2f-%.2f: %5d engs (%.1f/game, we start %.0f%%) our deaths %.2f/eng their %.2f/eng (kill ratio %.2f)' % (
            a, b, len(L), len(L) / len(G), 100 * su / len(L), du / len(L), dt / len(L), dt / max(1, du)))
# numbers ratio
print('\n  by local body count (ours - theirs within 8):')
for g, G in GRP[:1]:
    E = [(r, e) for r in G for e in r['engs'] if sum(e['hits']) >= 3 or sum(e['dE']) > 0]
    cnt = collections.defaultdict(list)
    for r, e in E:
        st_ = e['first']['team']; n = e['loc8']['n']
        ours = n[0] if st_ == r['U'] else n[1]; theirs = n[1] if st_ == r['U'] else n[0]
        cnt[max(-3, min(3, ours - theirs))].append((r, e))
    for k in sorted(cnt):
        L = cnt[k]
        print('     diff %+d: %5d engs, our d/eng %.2f their %.2f' % (k, len(L), sum(e['dE'][r['U']] for r, e in L) / len(L), sum(e['dE'][1 - r['U']] for r, e in L) / len(L)))
# first-3-round damage share and focus
print('\n  first 3 rounds damage share (ours) and outcome; focus (share of damage on the most-damaged target)')
for g, G in GRP:
    E = [(r, e) for r in G for e in r['engs'] if sum(e['hits']) >= 3]
    sh = [e['dealt3'][r['U']] / max(1, sum(e['dealt3'])) for r, e in E]
    print('   %-5s engs %d: our share of first-3-round damage %.2f; focus us %.2f them %.2f; attackers us %.2f them %.2f; casts/hit us %.2f them %.2f; stuns3 us %.2f them %.2f' % (
        g, len(E), mean(sh), mean([e['focus'][r['U']] for r, e in E]), mean([e['focus'][1 - r['U']] for r, e in E]),
        mean([e['attackers'][r['U']] for r, e in E]), mean([e['attackers'][1 - r['U']] for r, e in E]),
        mean([e['castHits'][r['U']] / max(1, e['hits'][r['U']]) for r, e in E]), mean([e['castHits'][1 - r['U']] / max(1, e['hits'][1 - r['U']]) for r, e in E]),
        mean([e['stuns3'][r['U']] for r, e in E]), mean([e['stuns3'][1 - r['U']] for r, e in E])))
    won3 = [(r, e) for r, e in E if e['dealt3'][r['U']] > e['dealt3'][1 - r['U']]]
    lost3 = [(r, e) for r, e in E if e['dealt3'][r['U']] < e['dealt3'][1 - r['U']]]
    print('         we win first 3 rounds %d (our d %.2f their %.2f) | lose %d (our d %.2f their %.2f)' % (
        len(won3), mean([e['dE'][r['U']] for r, e in won3]), mean([e['dE'][1 - r['U']] for r, e in won3]),
        len(lost3), mean([e['dE'][r['U']] for r, e in lost3]), mean([e['dE'][1 - r['U']] for r, e in lost3])))
    # what our first victim was doing when they started
    th = [(r, e) for r, e in E if e['first']['team'] != r['U']]
    print('         they start: our first victim farming %.2f moving %.2f channel %.2f hp %.2f; victim types %s' % (
        mean([1.0 if e['first']['vFarm'] else 0.0 for r, e in th]), mean([1.0 if e['first']['vMove'] >= 2 else 0.0 for r, e in th]),
        mean([1.0 if e['first']['vChan'] else 0.0 for r, e in th]), mean([e['first']['vHp'] for r, e in th]),
        collections.Counter(e['first']['v'] for r, e in th).most_common(6)))
    print('         they start with: %s' % collections.Counter(e['first']['a'] + (':cast%d' % e['first']['slot'] if e['first']['cast'] else ':atk') for r, e in th).most_common(8))
    us_ = [(r, e) for r, e in E if e['first']['team'] == r['U']]
    print('         we start with: %s' % collections.Counter(e['first']['a'] + (':cast%d' % e['first']['slot'] if e['first']['cast'] else ':atk') for r, e in us_).most_common(8))
    # aftermath for the side that won
    for lab, L in (('we start', us_), ('they start', th)):
        aU = [e['after'][r['U']] for r, e in L]; aT = [e['after'][1 - r['U']] for r, e in L]
        print('         after (%s): us farm %.2f champ %.2f toward %.2f home %.2f caps %.2f | them farm %.2f champ %.2f toward %.2f home %.2f caps %.2f (per body-round / per eng caps)' % (
            lab, sum(a['farm'] for a in aU) / max(1, sum(a['br'] for a in aU)), sum(a['champ'] for a in aU) / max(1, sum(a['br'] for a in aU)),
            sum(a['toward'] for a in aU) / max(1, sum(a['mv'] for a in aU)), sum(a['home'] for a in aU) / max(1, sum(a['mv'] for a in aU)), mean([a['caps'] for a in aU]),
            sum(a['farm'] for a in aT) / max(1, sum(a['br'] for a in aT)), sum(a['champ'] for a in aT) / max(1, sum(a['br'] for a in aT)),
            sum(a['toward'] for a in aT) / max(1, sum(a['mv'] for a in aT)), sum(a['home'] for a in aT) / max(1, sum(a['mv'] for a in aT)), mean([a['caps'] for a in aT])))

print('\n== CONTACTS (opposing bodies within 4, area quiet 8 rounds): who strikes first within 5 rounds')
for g, G in GRP:
    C = [(r, c) for r in G for c in r['contacts']]
    us = sum(1 for r, c in C if c['first'] == r['U']); th = sum(1 for r, c in C if c['first'] == 1 - r['U']); no = sum(1 for r, c in C if c['first'] == -1)
    print('  %-5s contacts %.1f/game: we first %.0f%%, they first %.0f%%, nobody %.0f%%' % (g, len(C) / len(G), 100 * us / len(C), 100 * th / len(C), 100 * no / len(C)))
    # by local power at contact
    for lab, f in (('we stronger (mh > 1.15x)', lambda r, c: c['mh'][r['U']] > 1.15 * c['mh'][1 - r['U']]), ('even', lambda r, c: 0.87 * c['mh'][1 - r['U']] <= c['mh'][r['U']] <= 1.15 * c['mh'][1 - r['U']]),
                   ('they stronger', lambda r, c: c['mh'][r['U']] < 0.87 * c['mh'][1 - r['U']])):
        L = [(r, c) for r, c in C if f(r, c)]
        if not L: continue
        print('       %-26s %4.0f%% of contacts: we first %.0f%%, they first %.0f%%' % (lab, 100 * len(L) / len(C), 100 * sum(1 for r, c in L if c['first'] == r['U']) / len(L), 100 * sum(1 for r, c in L if c['first'] == 1 - r['U']) / len(L)))
    # our body farming at contact
    L = [(r, c) for r, c in C if c['farm'][r['U']] > 0]
    if L: print('       our body farming at contact: %d (they first %.0f%%)' % (len(L), 100 * sum(1 for r, c in L if c['first'] == 1 - r['U']) / len(L)))

print('\n== DEATHS (fightan modes; per game)')
MODES = ['linked', 'camp', 'banking', 'recalling', 'fighting', 'farming', 'capturing', 'fleeing', 'approaching', 'stunned', 'walking']
for g, G in GRP:
    n = len(G)
    D = [(r, x) for r in G for x in r['deaths']]
    du = [(r, x) for r, x in D if x['team'] == r['U']]; dt = [(r, x) for r, x in D if x['team'] != r['U']]
    print('  %-5s deaths/game us %.2f them %.2f' % (g, len(du) / n, len(dt) / n))
    print('        modes us  ', ' '.join('%s %.2f' % (m, sum(1 for r, x in du if x['mode'] == m) / n) for m in MODES))
    print('        modes them', ' '.join('%s %.2f' % (m, sum(1 for r, x in dt if x['mode'] == m) / n) for m in MODES))
    for lab, L in (('us', du), ('them', dt)):
        C = [(r, x) for r, x in L if x['mode'] not in ('camp', 'linked')]
        if not C: continue
        iso = sum(1 for r, x in C if x['l6']['n'][0] <= 1)
        outn = sum(1 for r, x in C if x['l6']['n'][1] > x['l6']['n'][0])
        idle_al = sum(sum(1 for a in x['allies'] if not a['hit']) for r, x in C)
        print('        %-4s champion kills %.2f/game: isolated (alone within 6) %.0f%%, outnumbered within 6 %.0f%%, zone own/mid/their %s, bag %.1f, hp before seq %.2f, seq %.1f rounds, exposure %.1f, attackers %.2f, allies within 8 not hitting %.2f/death, traded %.0f%%, in engagements they started %.0f%%' % (
            lab, len(C) / n, 100 * iso / len(C), 100 * outn / len(C), dict(collections.Counter(x['zone'] for r, x in C)), mean([x['bag'] for r, x in C]),
            mean([x['hpS'] for r, x in C]), mean([x['seq'] for r, x in C]), mean([x['expo'] for r, x in C]), mean([x['natk'] for r, x in C]),
            idle_al / len(C), 100 * sum(1 for r, x in C if x['trade']) / len(C),
            100 * sum(1 for r, x in C if x['eng'] and x['eng']['st'] != x['team']) / max(1, sum(1 for r, x in C if x['eng']))))
        mhr = [x['mh'] / mean(x['atkMh']) for r, x in C if x['atkMh'] and mean(x['atkMh'])]
        print('             victim max-health / mean attacker max-health %.2f (median %.2f); local max-health within 8 ours/theirs at r-1 %.2f' % (
            mean(mhr), st.median(mhr) if mhr else float('nan'), mean([x['l8']['mh'][0] / x['l8']['mh'][1] for r, x in C if x['l8']['mh'][1]])))
    # by phase
    for ph, (a, b) in enumerate(((0, 300), (300, 600), (600, 1000), (1000, 9999))):
        cu = collections.Counter(x['mode'] for r, x in du if a <= x['r'] < b)
        print('        ph%d us: %s' % (ph, ' '.join('%s %.2f' % (m, cu[m] / n) for m in MODES if cu[m])))
