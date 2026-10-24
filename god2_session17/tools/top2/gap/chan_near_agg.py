# gap_g8: aggregate tools/top2/gap/chanpunish.mjs (tributes / recalls and their punishment) and tools/top2/gap/nearbehav.mjs (what a
# body does with an enemy within 8; arrivals at farmers) over the S0 games, us vs them, by opponent.
#   python tools/top2/gap/chan_near_agg.py C:/battlecode/cache/gap_g8/chanpunish.jsonl C:/battlecode/cache/gap_g8/nearbehav.jsonl
import json, sys, collections
SIDES = json.load(open('C:/battlecode/cache/gap_g8/sides.json', encoding='utf-8'))
OPP = {'prism best girl': 'PBG', 'Intercontinental Fish': 'IFish', 'Claudus Maximus': 'CM'}
def load(p):
    out = []
    for l in open(p, encoding='utf-8'):
        if not l.strip(): continue
        r = json.loads(l)
        if 'err' in r: continue
        S = SIDES[r['file']]; r['U'] = S['ours']; r['opp'] = OPP[S['opp']]; out.append(r)
    return out
cp = load(sys.argv[1])
for g in ('ALL', 'PBG', 'IFish', 'CM'):
    G = [r for r in cp if g == 'ALL' or r['opp'] == g]
    n = len(G)
    C = {'us': collections.Counter(), 'them': collections.Counter()}
    for r in G:
        for k, v in r['c'].items():
            kind, t, b, key = k.split('|')
            C['us' if int(t) == r['U'] else 'them'][(kind, b, key)] += v
    print('== %s (%d games)' % (g, n))
    for who in ('us', 'them'):
        X = C[who]
        for b in ('a<50', 'b50-99', 'c100-199', 'd200+'):
            N = X[('trib', b, 'n')]
            if not N: continue
            nr = X[('trib', b, 'near8')]
            print('  %-4s tributes bag %-8s %.2f/game, mean bag %.0f, turns %.1f | done %.0f%% dead %.0f%% stunned %.0f%% locked %.0f%% cancel %.0f%% | opp within 8 %.0f%%: opp hit %.0f%% stun %.0f%% lock %.0f%% failed %.0f%%' % (
                who, b, N / n, X[('trib', b, 'gems')] / N, X[('trib', b, 'turns')] / N, 100 * X[('trib', b, 'done')] / N, 100 * X[('trib', b, 'dead')] / N,
                100 * X[('trib', b, 'stunned')] / N, 100 * X[('trib', b, 'locked')] / N, 100 * X[('trib', b, 'cancel')] / N, 100 * nr / N,
                100 * X[('trib', b, 'near8hit')] / max(1, nr), 100 * X[('trib', b, 'near8stun')] / max(1, nr), 100 * X[('trib', b, 'near8lock')] / max(1, nr), 100 * X[('trib', b, 'near8fail')] / max(1, nr)))
        for b in ('n<=3', 'n4-5', 'n6-8', 'n>8'):
            N = X[('rec', b, 'n')]
            if not N: continue
            print('  %-4s recalls nearest opp %-5s %.2f/game, hp %.2f | done %.0f%% dead %.0f%% interrupted %.0f%% | hit by the other side %.0f%%' % (
                who, b, N / n, X[('rec', b, 'hpf')] / N, 100 * X[('rec', b, 'done')] / N, 100 * X[('rec', b, 'dead')] / N, 100 * X[('rec', b, 'interrupted')] / N, 100 * X[('rec', b, 'hit')] / N))
if len(sys.argv) > 2:
    nb = load(sys.argv[2])
    ACTS = ['farm', 'fight', 'chan', 'toward', 'away', 'side', 'still']
    RB = ['a<.67', 'b.67-.87', 'c.87-1.15', 'd1.15-1.5', 'e>1.5']
    for g in ('ALL', 'PBG', 'IFish', 'CM'):
        G = [r for r in nb if g == 'ALL' or r['opp'] == g]
        n = len(G)
        N = {'us': collections.Counter(), 'them': collections.Counter()}
        A = {'us': collections.Counter(), 'them': collections.Counter()}
        for r in G:
            for k, v in r['near'].items():
                t, rb, hb, a = k.split('|')
                who = 'us' if int(t) == r['U'] else 'them'
                N[who][(rb, hb, a)] += v
            for k, v in r['arr'].items():
                p = k.split('|')
                who = 'us' if int(p[0]) == r['U'] else 'them'
                A[who][tuple(p[1:])] += v
        print('\n== NEAR ENEMY (%s, %d games): action shares with an enemy within 8, by local max-health ratio ours/theirs within 8' % (g, n))
        for who in ('us', 'them'):
            X = N[who]
            tot = sum(X.values())
            print('  %-4s all (%d body-rounds, %.0f/game): %s' % (who, tot, tot / n, ' '.join('%s %.2f' % (a, sum(v for k, v in X.items() if k[2] == a) / tot) for a in ACTS)))
            for rb in RB:
                T = sum(v for k, v in X.items() if k[0] == rb)
                if not T: continue
                print('       %-10s %5.1f%% of rounds: %s' % (rb, 100 * T / tot, ' '.join('%s %.2f' % (a, sum(v for k, v in X.items() if k[0] == rb and k[2] == a) / T) for a in ACTS)))
            for hb in ('hi', 'mid', 'lo'):
                T = sum(v for k, v in X.items() if k[1] == hb)
                if not T: continue
                print('       own hp %-4s %5.1f%%: %s' % (hb, 100 * T / tot, ' '.join('%s %.2f' % (a, sum(v for k, v in X.items() if k[1] == hb and k[2] == a) / T) for a in ACTS)))
        print('  ARRIVALS at farmers (enemy comes within 8 of a body that damaged a camp in the last 3 rounds): response in the next 5 rounds; died / captured within 20')
        for who in ('us', 'them'):
            X = A[who]
            tot = sum(v for k, v in X.items() if len(k) == 2)
            resp = ['keep', 'fight', 'recall', 'leave', 'toward', 'hold', 'dead']
            print('  %-4s %d arrivals (%.1f/game): %s' % (who, tot, tot / n, ' '.join('%s %.2f (died %.2f, cap %.2f)' % (
                a, sum(v for k, v in X.items() if len(k) == 2 and k[1] == a) / max(1, tot),
                sum(v for k, v in X.items() if len(k) == 3 and k[1] == a and k[2] == 'died') / max(1, sum(v for k, v in X.items() if len(k) == 2 and k[1] == a)),
                sum(v for k, v in X.items() if len(k) == 3 and k[1] == a and k[2] == 'cap') / max(1, sum(v for k, v in X.items() if len(k) == 2 and k[1] == a))) for a in resp)))
            for rb in RB:
                T = sum(v for k, v in X.items() if len(k) == 2 and k[0] == rb)
                if not T: continue
                print('       %-10s n=%4d: %s' % (rb, T, ' '.join('%s %.2f' % (a, X[(rb, a)] / T) for a in resp)))
