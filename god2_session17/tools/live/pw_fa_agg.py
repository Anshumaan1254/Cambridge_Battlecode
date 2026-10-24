# Aggregate tools/live/pw_fa.mjs: turns with a basic attack on an enemy champion and the attack reset ready at turn start, per group
# (US / OPP / TT, as in pw_agg.py) and champion: reset used, why not (other cast took the turn's one cast, the first hit killed, the
# body left after hitting), and the most common action sequences.
#   python tools/live/pw_fa_agg.py C:/battlecode/cache/an_powers/fa.jsonl
import json, sys, collections
sys.path.insert(0, 'C:/battlecode/Cambridge_Battlecode/tools/live')
from pw_agg import load_matches, team_groups, pct

M = load_matches()
S = collections.defaultdict(collections.Counter)
SEQ = collections.defaultdict(collections.Counter)
NU = collections.defaultdict(collections.Counter)  # sequences of reset-ready turns without the reset ('<' = left after)
for l in open(sys.argv[1], encoding='utf-8'):
    g = json.loads(l)
    mid = g['file'].split('_')[-1].split('.')[0]
    if mid not in M:
        continue
    grp, _ = team_groups(M[mid])
    bt = {b[0]: (b[1], b[2]) for b in g['bodies']}
    for w, r, rready, r0, r1, seq, left, hp in g['turns']:
        tm, ch = bt[w]
        if rready != 1:
            continue
        k = (grp[tm], ch)
        s = S[k]
        s['n'] += 1
        used = 'R' in seq
        s['used'] += used
        if not used:
            if 'C' in seq or 'D' in seq:
                s['blocked'] += 1
                if seq.index('C' if 'C' in seq else 'D') < seq.index('A' if 'A' in seq else 'K'):
                    s['blocked_castFirst'] += 1
            elif seq.count('A') + seq.count('K') == 1 and 'K' in seq:
                s['killed'] += 1
            elif left:
                s['left'] += 1
            else:
                s['other'] += 1
        SEQ[k][seq] += 1
        if not used:
            NU[k][seq + ('<' if left else '')] += 1
for k in sorted(S, key=lambda x: (x[1], x[0])):
    s = S[k]
    n = s['n']
    if n < 30:
        continue
    top = ', '.join(f'{q} {pct(c, n)}' for q, c in SEQ[k].most_common(6))
    print(f"{k[1]:12s} {k[0]:4s} turns {n:5d}  reset used {pct(s['used'], n)} | not used: other cast took the turn {pct(s['blocked'], n)} "
          f"(cast before the hit {pct(s['blocked_castFirst'], n)}), first hit killed {pct(s['killed'], n)}, left after the hit {pct(s['left'], n)}, "
          f"other {pct(s['other'], n)} | {top}")
    nu = sum(NU[k].values())
    print(f"{'':17s} not-used sequences: " + ', '.join(f'{q} {pct(c, nu)}' for q, c in NU[k].most_common(8)))

# All champions: champion-attack turns, per slot: ready at turn start -> cast this turn (any order), and the sequences.
print('\nall champions, turns with a basic attack on an enemy champion: slot ready -> cast in that turn')
A = collections.defaultdict(collections.Counter)
SQ = collections.defaultdict(collections.Counter)
KIT = {'Ryth': ['aoestun', 'reset'], 'VesperVale': ['reset', 'dash'], 'Vendetta': ['reset', 'dash'], 'Cassi': ['dmg', 'stun'],
       'Issac': ['reset', 'dash'], 'Stellar': ['dmg', 'aoe'], 'Prism': ['dmgstun', 'aoe'], 'Marcella': ['ereset', 'dmg'],
       'Willow': ['heal', 'reset'], 'Ren': ['dmgstun', 'dash'], 'Varg': ['reset', 'shield'], 'Tavi': ['reset', 'dmgstun'],
       'HeartOfRuin': ['shield', 'hordash']}
for l in open(sys.argv[1], encoding='utf-8'):
    g = json.loads(l)
    mid = g['file'].split('_')[-1].split('.')[0]
    if mid not in M:
        continue
    grp, _ = team_groups(M[mid])
    bt = {b[0]: (b[1], b[2]) for b in g['bodies']}
    for w, r, rready, r0, r1, seq, left, hp in g['turns']:
        tm, ch = bt[w]
        k = (grp[tm], ch)
        a = A[k]
        a['n'] += 1
        a['left'] += left
        SQ[k][seq] += 1
        for s, rd in ((0, r0), (1, r1)):
            if not rd:
                continue
            a[f'ready{s}'] += 1
            kind = KIT.get(ch, ['?', '?'])[s]
            letter = 'D' if kind in ('dash', 'hordash') else ('R' if kind in ('reset', 'ereset') else 'C')
            # 'C' is any non-reset non-dash cast: with two such slots (Prism, Cassi) this over-counts; fine for reset/dash/shield kits
            a[f'cast{s}'] += letter in seq
for k in sorted(A, key=lambda x: (x[1], x[0])):
    a = A[k]
    if a['n'] < 30:
        continue
    kit = KIT.get(k[1], ['?', '?'])
    top = ', '.join(f'{q} {pct(c, a["n"])}' for q, c in SQ[k].most_common(6))
    print(f"{k[1]:12s} {k[0]:4s} turns {a['n']:5d}  slot0 {kit[0]} ready {pct(a['ready0'], a['n'])} cast {pct(a['cast0'], a['ready0'])} | slot1 {kit[1]} ready {pct(a['ready1'], a['n'])} cast {pct(a['cast1'], a['ready1'])} | left {pct(a['left'], a['n'])} | {top}")
