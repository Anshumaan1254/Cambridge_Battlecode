"""verify_items: tribute / lock / stun / ability / Prism claims (C2-C7) from vd_all.jsonl.
   python tools/top2/verify_items/vagg_dump.py [section...]   sections: trib prism ab lock stun misc"""
import collections, statistics as stt, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from vlib import groups, vd, pct

G = groups(); D = vd()
ORDER = ['pbg', 'pbg14', 'nyx', 'ifish', 'pantheon', 'coo', 'cm']
secs = sys.argv[1:] or ['trib', 'prism', 'ab', 'lock', 'stun', 'misc']


def side_games(g):
    return [x for x in G[g] if x['base'] in D]


def tm_of(d):
    return {b[0]: b[1] for b in d['bodies']}, {b[0]: b[2] for b in d['bodies']}


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float('nan')


if 'trib' in secs:
    print('=== C2: tribute interruption by bag and enemy within 6 at the start (end of the start round); censored at game end excluded')
    for near_key in ('dmin', 'dmin_prev'):
        print(f'--- near = {near_key} <= 6')
        for g in ORDER:
            for side in ('S', 'O'):
                c = collections.defaultdict(lambda: [0, 0]); causes = collections.defaultdict(collections.Counter); n = 0
                for x in side_games(g):
                    d = D[x['base']]; tm, ty = tm_of(d)
                    t = x['S'] if side == 'S' else 1 - x['S']
                    for tr in d['tribs']:
                        if tm[tr['who']] != t or tr['out'] == 'end' or tr['bag'] <= 0:
                            continue
                        n += 1
                        bk = '1-49' if tr['bag'] < 50 else '50-149' if tr['bag'] < 150 else '150+'
                        nr = 'near' if tr[near_key] <= 6 else 'far'
                        c[(bk, nr)][0] += 1
                        if tr['out'] != 'done':
                            c[(bk, nr)][1] += 1
                            causes[(bk, nr)][tr['out'].split(':')[0]] += 1
                ng = len(side_games(g))
                cells = []
                for bk in ('1-49', '50-149', '150+'):
                    a, b = c[(bk, 'near')], c[(bk, 'far')]
                    cells.append(f"{bk}: {pct(a[1], a[0])}/{pct(b[1], b[0])} (n {a[0]}/{b[0]})")
                print(f"{g:9s} {side} trib/game {n/max(1,ng):5.1f} | " + ' | '.join(cells))
                if side == 'S' or g == 'nyx':
                    print('          causes 150+ near:', dict(causes[('150+', 'near')]), ' far:', dict(causes[('150+', 'far')]))
        if near_key == 'dmin':
            # per-bag fate of interrupted 150+ attempts: banked later in the same life, lost on death, or held at the end
            print('--- fate of the bag after an interrupted 150+ attempt (S and O pooled per group)')
            for g in ORDER:
                fate = collections.Counter(); repeats = []
                for x in side_games(g):
                    d = D[x['base']]; tm, ty = tm_of(d)
                    deaths = collections.defaultdict(list)
                    for de in d['deaths']: deaths[de[1]].append(de[0])
                    for side in ('S',):
                        t = x['S']
                        trs = sorted([tr for tr in d['tribs'] if tm[tr['who']] == t], key=lambda z: z['q0'])
                        for i, tr in enumerate(trs):
                            if tr['bag'] < 150 or tr['out'] in ('done', 'end'):
                                continue
                            nxt_death = min([r for r in deaths[tr['who']] if r >= tr['r0']], default=10 ** 9)
                            later = [z for z in trs[i + 1:] if z['who'] == tr['who'] and z['r0'] < nxt_death]
                            if any(z['out'] == 'done' for z in later):
                                fate['banked later'] += 1
                            elif nxt_death < 10 ** 9:
                                fate['died before banking'] += 1
                            else:
                                fate['held to the end'] += 1
                            repeats.append(len(later))
                print(f"{g:9s} S interrupted 150+: {dict(fate)}  mean later attempts same life {mean(repeats):.1f}")
    print('\n--- lock cancels of the study team tributes (bags) and stuns on tributing victims')
    for g in ORDER:
        for side in ('S', 'O'):
            lk = []; stv = []
            for x in side_games(g):
                d = D[x['base']]; tm, ty = tm_of(d)
                t = x['S'] if side == 'S' else 1 - x['S']
                for tr in d['tribs']:
                    if tm[tr['who']] == t and tr['out'] == 'lock':
                        lk.append((tr['bag'], ty[tr['who']], x['base'], tr['r1']))
                for s in d['stuns']:
                    r, a, v, state, bag = s
                    if a >= 0 and tm.get(a) == t and tm.get(v) != t and state == 'trib':
                        stv.append(bag)
            lk.sort(reverse=True); stv.sort(reverse=True)
            print(f"{g:9s} {side}: own tributes cancelled by enemy locks {len(lk)} top {[(b, ty_, f, r) for b, ty_, f, r in lk[:6]]}")
            print(f"           stuns landed on tributing enemies {len(stv)} top bags {stv[:8]}")

if 'prism' in secs:
    print('\n=== C3: Prism damage per champion-hitting cast by carried bag (bag at end of previous round)')
    BK = ['0', '1-24', '25-49', '50-99', '100-199', '200+']
    def bk(b):
        return '0' if b == 0 else '1-24' if b < 25 else '25-49' if b < 50 else '50-99' if b < 100 else '100-199' if b < 200 else '200+'
    for g in ORDER:
        for side in ('S', 'O'):
            ch = collections.defaultdict(list); cp = collections.defaultdict(list); chs = collections.defaultdict(list); big = []
            for x in side_games(g):
                d = D[x['base']]; tm, ty = tm_of(d)
                t = x['S'] if side == 'S' else 1 - x['S']
                for b, r, s, bag, cd, nv, campd in d['prism']:
                    if tm[b] != t: continue
                    if cd > 0:
                        ch[bk(bag)].append(cd); chs[(bk(bag), s)].append(cd / max(1, nv)); big.append((cd, bag, x['base'], r, s, nv))
                    elif campd > 0:
                        cp[bk(bag)].append(campd)
            if not any(ch.values()):
                continue
            big.sort(reverse=True)
            print(f"{g:9s} {side} champ: " + ' '.join(f"{k}:{mean(ch[k]):.0f}({len(ch[k])})" for k in BK) +
                  ' | camp: ' + ' '.join(f"{k}:{mean(cp[k]):.0f}" for k in BK))
            print('          per victim slot0/slot1 200+: %.0f / %.0f ; bag0: %.0f / %.0f' % (mean(chs[('200+', 0)]), mean(chs[('200+', 1)]), mean(chs[('0', 0)]), mean(chs[('0', 1)])),
                  '| top', big[:4])
    print('\n--- Prism drafted, bag, completed tributes, deaths with bags (study team Prism)')
    for g in ORDER:
        for side in ('S', 'O'):
            ng = 0; npr = 0; bags = {400: [], 600: [], 1000: []}; tribs = []; dbag = []; prism_games = 0
            for x in side_games(g):
                d = D[x['base']]; tm, ty = tm_of(d); ng += 1
                t = x['S'] if side == 'S' else 1 - x['S']
                pr = [b for b in tm if tm[b] == t and ty[b] == 'Prism']
                if not pr: continue
                prism_games += 1
                for b in pr:
                    for cpk in bags:
                        c = d['cp'].get(str(cpk), {}).get(str(b))
                        if c: bags[cpk].append(c[2])
                    tribs += [tr['bag'] for tr in d['tribs'] if tr['who'] == b and tr['out'] == 'done']
                    dbag += [de[2] for de in d['deaths'] if de[1] == b]
            print(f"{g:9s} {side} Prism in {prism_games}/{ng} games | mean bag r400 {mean(bags[400]):.0f} r600 {mean(bags[600]):.0f} r1000 {mean(bags[1000]):.0f} | "
                  f"completed tributes/Prism-game {len(tribs)/max(1,prism_games):.2f} mean {mean(tribs):.0f} ; >=100: {sum(1 for z in tribs if z>=100)/max(1,prism_games):.2f} mean {mean([z for z in tribs if z>=100]):.0f} | "
                  f"deaths {len(dbag)} mean bag lost {mean(dbag):.0f} with 100+: {sum(1 for z in dbag if z >= 100)}")

if 'ab' in secs:
    print('\n=== C4: cast share of ready turns by context (F fight, N enemy within 5, C camp in r-1/r-2, C0 camp only this round, O other)')
    KIT = {'Ryth': {0: 'aoestun', 1: 'reset'}, 'VesperVale': {0: 'reset', 1: 'dash'}, 'Marcella': {0: 'ereset', 1: 'dmg'},
           'HeartOfRuin': {0: 'shield', 1: 'hordash'}, 'Prism': {0: 'dmgstun', 1: 'aoe'}, 'Tavi': {0: 'reset', 1: 'dmgstun'},
           'Cassi': {0: 'dmg', 1: 'stun'}, 'Vendetta': {0: 'reset', 1: 'dash'}}
    WANT = [('HeartOfRuin', 1), ('Ryth', 0), ('Marcella', 1), ('VesperVale', 0), ('Prism', 0), ('Prism', 1), ('Tavi', 1), ('Cassi', 0)]
    for (T, s) in WANT:
        print(f'--- {T} slot {s} ({KIT[T][s]})')
        for g in ORDER:
            line = []
            for side in ('S', 'O'):
                c = collections.defaultdict(lambda: [0, 0]); nb = 0
                for x in side_games(g):
                    d = D[x['base']]; tm, ty = tm_of(d)
                    t = x['S'] if side == 'S' else 1 - x['S']
                    for b, slots in d['ab'].items():
                        b = int(b)
                        if tm[b] != t or ty[b] != T: continue
                        nb += 1
                        for ctx, (rd, cs) in slots.get(str(s), {}).items():
                            c[ctx][0] += rd; c[ctx][1] += cs
                cc = [c['C'][0] + c['C0'][0], c['C'][1] + c['C0'][1]]
                line.append(f"{side}({nb}) F {pct(c['F'][1], c['F'][0])} [{c['F'][0]}] N {pct(c['N'][1], c['N'][0])} C {pct(c['C'][1], c['C'][0])} C+C0 {pct(cc[1], cc[0])} O {pct(c['O'][1], c['O'][0])}")
            print(f"{g:9s} " + ' || '.join(line))
    print('\n--- champion-attack turns: reset used when ready at turn start; walk-reset-shot share')
    for T in ('Marcella', 'Ryth', 'VesperVale', 'Tavi', 'Vendetta'):
        for g in ORDER:
            line = []
            for side in ('S', 'O'):
                n = rd = us = mra = mra2 = 0; seqc = collections.Counter()
                for x in side_games(g):
                    d = D[x['base']]; tm, ty = tm_of(d)
                    t = x['S'] if side == 'S' else 1 - x['S']
                    for b, r, ready, used, seq in d['atkseq']:
                        if tm[b] != t or ty[b] != T: continue
                        n += 1; rd += ready; us += ready and used
                        s2 = seq.replace('a', '')
                        i = s2.find('M'); j = s2.find('R', i + 1) if i >= 0 else -1; k = s2.find('A', j + 1) if j >= 0 else -1
                        if k >= 0 and s2.find('A') > j: mra += 1  # walk, then reset, then the first champion hit
                        if s2.startswith('MRA'): mra2 += 1
                        seqc[s2] += 1
                if n:
                    line.append(f"{side} turns {n} ready {pct(rd, n)} used|ready {pct(us, rd)} M..R..A {pct(mra, n)} MRA-start {pct(mra2, n)} top {seqc.most_common(4)}")
            if line:
                print(f"{T:10s} {g:9s} " + ' || '.join(line))

if 'lock' in secs:
    print('\n=== C5: altar locks placed per game and outcomes')
    for g in ORDER:
        for side in ('S', 'O'):
            L = []; ng = 0
            for x in side_games(g):
                d = D[x['base']]; tm, ty = tm_of(d); ng += 1
                t = x['S'] if side == 'S' else 1 - x['S']
                L += [dict(lk, base=x['base']) for lk in d['locks'] if lk['team'] == t]
            if not L:
                print(f"{g:9s} {side} locks/game 0.00 ({ng} games)"); continue
            lives = [lk['life'] for lk in L if lk['life'] is not None]
            allv = [lk['life'] if lk['life'] is not None else lk['cens'] for lk in L]
            print(f"{g:9s} {side} locks/game {len(L)/ng:.2f} (n {len(L)}) | own tribute there within 3r {pct(sum(lk['own3'] for lk in L), len(L))} | "
                  f"no enemy within 8 {pct(sum(lk['dmin'] > 8 for lk in L), len(L))} | cleared {pct(len(lives), len(L))} | median life cleared {stt.median(lives) if lives else '-'} "
                  f"(incl. censored {stt.median(allv)}) | own banks while standing {mean(lk['banks'] for lk in L):.2f} | enemy attack turns {mean(lk['en_turns'] for lk in L):.2f} "
                  f"| placed on a standing enemy lock {sum(lk['on_enemy_lock'] for lk in L)} | cancelled enemy tributes {sum(len(lk['cancelled']) for lk in L)} {sorted([b for lk in L for b in lk['cancelled']], reverse=True)[:5]}")
    # locks on locks over all unique games
    seen = set(); n_on = 0; tg = set()
    for g in ('pbg', 'nyx', 'ifish', 'pantheon', 'coo', 'cm'):
        for x in side_games(g):
            if x['base'] in seen: continue
            seen.add(x['base'])
            for lk in D[x['base']]['locks']:
                if lk['on_enemy_lock']:
                    n_on += 1; tg.add((x['base'], lk['team']))
    print(f"locks placed on a standing enemy lock: {n_on} in {len(tg)} team-games ({len(seen)} unique games)")

if 'stun' in secs:
    print('\n=== C6: stuns on enemy champions per team-game, by stunner type, victim state')
    for g in ORDER:
        for side in ('S', 'O'):
            ng = 0; tot = 0; byt = collections.Counter(); drafted = collections.Counter(); state = collections.Counter()
            for x in side_games(g):
                d = D[x['base']]; tm, ty = tm_of(d); ng += 1
                t = x['S'] if side == 'S' else 1 - x['S']
                for T in set(ty[b] for b in tm if tm[b] == t): drafted[T] += 1
                for r, a, v, st_, bag in d['stuns']:
                    if a < 0 or tm.get(a) != t or tm.get(v) == t: continue
                    tot += 1; byt[ty[a]] += 1; state[st_] += 1
            print(f"{g:9s} {side} stuns/game {tot/ng:5.1f} | by type per team-game (per game drafted): " +
                  ', '.join(f"{T} {v/ng:.1f} ({v/drafted[T]:.1f})" for T, v in byt.most_common(5)) + f" | victim state {dict(state)}")
    print('--- recall starts per 100 alive rounds and spam share (recall cancelled at the next turn)')
    for g in ORDER:
        for side in ('S', 'O'):
            rc = sp = al = 0; spam_bodies = 0; nb = 0
            for x in side_games(g):
                d = D[x['base']]; tm, ty = tm_of(d)
                t = x['S'] if side == 'S' else 1 - x['S']
                for b in tm:
                    if tm[b] != t: continue
                    nb += 1
                    n = d['recalls_n'][str(b)]; s = d['recalls_spam'][str(b)]
                    rc += n; sp += s; al += d['alive'][str(b)]
                    if n and s / n > 0.5 and n > 50: spam_bodies += 1
            print(f"{g:9s} {side} recalls/100 alive r {100*rc/max(1,al):5.1f} spam share {pct(sp, rc)} spam bodies {spam_bodies}/{nb}")

if 'misc' in secs:
    print('\n=== C7 / C1: deaths per game by type, Cassi+Issac, Vesper champion damage')
    for g in ORDER:
        for side in ('S', 'O'):
            per = collections.defaultdict(lambda: [0, 0, 0]);
            for x in side_games(g):
                d = D[x['base']]; tm, ty = tm_of(d)
                t = x['S'] if side == 'S' else 1 - x['S']
                for b in tm:
                    if tm[b] != t: continue
                    T = ty[b]
                    per[T][0] += 1
                    per[T][1] += sum(1 for de in d['deaths'] if de[1] == b)
                    per[T][2] += d['cdmg_champ'][str(b)]
            print(f"{g:9s} {side} " + ', '.join(f"{T} n{v[0]} d/g {v[1]/v[0]:.2f} dmg/g {v[2]/v[0]:.0f}" for T, v in sorted(per.items()) if T in ('VesperVale', 'Cassi', 'Issac', 'Prism')))
