# gap_g8: aggregate tools/live/fightfirst.mjs (lead-up to first strikes and to kills) and tools/live/idleallies.mjs over the S0 dumps.
#   python tools/top2/gap/ff_agg.py C:/battlecode/cache/gap_g8/ff.jsonl C:/battlecode/cache/gap_g8/idleallies.jsonl
import json, sys, collections
SIDES = json.load(open('C:/battlecode/cache/gap_g8/sides.json', encoding='utf-8'))
OPP = {'prism best girl': 'PBG', 'Intercontinental Fish': 'IFish', 'Claudus Maximus': 'CM'}
def load(p):
    out = []
    for l in open(p, encoding='utf-8'):
        if not l.strip(): continue
        r = json.loads(l)
        if 'err' in r: continue
        S = SIDES[r['game']]
        r['U'] = S['ours']; r['opp'] = OPP[S['opp']]
        out.append(r)
    return out
ff = load(sys.argv[1])
def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float('nan')
GRP = [('ALL', ff)] + [(o, [r for r in ff if r['opp'] == o]) for o in ('PBG', 'IFish', 'CM')]
print('== FIRST STRIKES (engagement openers; victim = the side struck first)')
for g, G in GRP:
    for lab, cond in (('they strike us', lambda r, f: f['st'] != r['U']), ('we strike them', lambda r, f: f['st'] == r['U'])):
        F = [f for r in G for f in r['firsts'] if cond(r, f)]
        if not F: continue
        print('  %-5s %-15s n=%5d (%.1f/game): victim closed the gap in r0-3..r0-1 %.0f%%, attacker closed %.0f%%, victim could have struck first (in reach r0-1) %.0f%%, victim farming %.0f%%, victim spell ready %.0f%%, dist r0-1 %.1f, opener cast %.0f%%' % (
            g, lab, len(F), len(F) / len(G), 100 * mean([1.0 if f['vClose'] else 0.0 for f in F]), 100 * mean([1.0 if f['aClose'] else 0.0 for f in F]),
            100 * mean([f['vCould1'] for f in F]), 100 * mean([1.0 if f['vFarm'] else 0.0 for f in F]), 100 * mean([f['vReady'] for f in F]),
            mean([f['dist'][0] for f in F]), 100 * mean([f['cast'] for f in F])))
print('\n== KILLS: lead-up of the victim to its killer over the 8 rounds before')
for g, G in GRP:
    for lab, cond in (('our deaths', lambda r, k: k['team'] == r['U']), ('their deaths', lambda r, k: k['team'] != r['U'])):
        K = [k for r in G for k in r['kd'] if cond(r, k)]
        if not K: continue
        print('  %-5s %-12s n=%5d: victim closing moves %.2f, away moves %.2f, killer closing moves %.2f, hits taken while closing %.2f, victim own hitting rounds %.2f, victim never hit %.0f%%' % (
            g, lab, len(K), mean([k['vClose'] for k in K]), mean([k['vAway'] for k in K]), mean([k['kClose'] for k in K]), mean([k['hitWhileClosing'] for k in K]),
            mean([k['ownHits'] for k in K]), 100 * mean([1.0 if k['ownHits'] == 0 else 0.0 for k in K])))
if len(sys.argv) > 2:
    ia = load(sys.argv[2])
    print('\n== ALLIES within 8 of a champion kill that dealt no champion damage in r-5..r (rows per death)')
    for g, G in [('ALL', ia)] + [(o, [r for r in ia if r['opp'] == o]) for o in ('PBG', 'IFish', 'CM')]:
        for lab, cond in (('our deaths', lambda r, x: x[0] == r['U']), ('their deaths', lambda r, x: x[0] != r['U'])):
            X = [x for r in G for x in r['rows'] if cond(r, x)]
            if not X: continue
            print('  %-5s %-12s idle allies %.2f/game: moved closer to the victim %.0f%%, moved away %.0f%%, moved toward home %.0f%%, own hp %.2f, itself within 4 of an enemy %.0f%%, dist %.1f' % (
                g, lab, len(X) / len(G), 100 * mean([1.0 if x[1] < 0 else 0.0 for x in X]), 100 * mean([1.0 if x[1] > 0 else 0.0 for x in X]),
                100 * mean([1.0 if x[2] < 0 else 0.0 for x in X]), mean([x[3] for x in X]), 100 * mean([1.0 if x[4] else 0.0 for x in X]), mean([x[5] for x in X])))
