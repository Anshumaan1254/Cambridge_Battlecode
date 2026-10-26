"""Draft tables of the top-3 teams from their engine-2.0.0 ranked games (fetch_ranked.py).
    python3 -I drafts.py"""
import collections, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
N = ['Ryth', 'Vesper', 'Vendetta', 'Cassi&I', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HoR']
TEAMS = {'ic': 'Intercontinental Fish', 'mite': 'Mite', 'tk': 'Trzy Kwaterki'}


def load(name):
    for l in open(os.path.join(HERE, f'{name}_ranked.jsonl')):
        m = json.loads(l)
        me = [t for t in m['teams'] if t['name'] == TEAMS[name]][0]
        op = [t for t in m['teams'] if t['name'] != TEAMS[name]][0]
        yield m, me, op


for name in TEAMS:
    G = list(load(name))
    w = sum(me['result'] == 'win' for _, me, _ in G)
    print(f"\n===== {TEAMS[name]}: {w}/{len(G)} = {100 * w / len(G):.1f}%")
    pick = collections.Counter(); pickw = collections.Counter(); first = collections.Counter()
    sets = collections.Counter(); setw = collections.Counter()
    for m, me, op in G:
        p = [int(x) for x in me['draftPicks']]
        first[N[p[0]]] += 1
        for c in p:
            pick[N[c]] += 1; pickw[N[c]] += me['result'] == 'win'
        k = tuple(sorted(N[c] for c in p)); sets[k] += 1; setw[k] += me['result'] == 'win'
    print('picks (games, win%):', ', '.join(f"{c} {n} {100 * pickw[c] / n:.0f}%" for c, n in pick.most_common()))
    print('first pick:', dict(first.most_common(6)))
    print('order examples:', [' '.join(N[int(x)] for x in me['draftPicks']) for _, me, _ in G[:4]])
    print('top sets:')
    for k, n in sets.most_common(6):
        print(f"   {n:4d} win {100 * setw[k] / n:5.1f}%  {' '.join(k)}")
    # losses: who beats them
    lo = collections.Counter(op['name'] for _, me, op in G if me['result'] != 'win')
    tot = collections.Counter(op['name'] for _, me, op in G)
    print('losses to:', ', '.join(f"{t} {n}/{tot[t]}" for t, n in lo.most_common(8)))
    mp = collections.defaultdict(lambda: [0, 0])
    for m, me, op in G:
        mp[m['map']][0] += me['result'] == 'win'; mp[m['map']][1] += 1
    worst = sorted(mp.items(), key=lambda kv: kv[1][0] / kv[1][1])[:10]
    print('worst maps:', ', '.join(f"{k} {a}/{b}" for k, (a, b) in worst))
