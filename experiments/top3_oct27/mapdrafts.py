"""Per-map drafts of the top 3 (engine 2.0.0 ranked) next to ours in the v20 games against them.
    python3 -I mapdrafts.py [--json OUT]"""
import collections, glob, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
N = ['Ryth', 'Vesper', 'Vendetta', 'Cassi', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HoR']
TEAMS = {'ic': 'Intercontinental Fish', 'mite': 'Mite', 'tk': 'Trzy Kwaterki'}
US = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'
M = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))   # map -> (team, set) -> [wins, games]
for t, nm in TEAMS.items():
    for l in open(os.path.join(HERE, f'{t}_ranked.jsonl')):
        m = json.loads(l)
        me = [x for x in m['teams'] if x['name'] == nm][0]
        k = (t, tuple(N[int(c)] for c in me['draftPicks']))
        M[m['map']][k][0] += me['result'] == 'win'; M[m['map']][k][1] += 1
ours = {}
for f in glob.glob('/tmp/claude-0/top3/*/show/*.json') + glob.glob('/tmp/claude-0/ic4/show/*.json'):
    for m in json.load(open(f))['matches']:
        me = [x for x in m['teams'] if x['teamId'] == US][0]
        ours[m['map']] = tuple(N[int(c)] for c in me['draftPicks'])
out = {}
for mp in sorted(M):
    by = M[mp]
    best = max(by.items(), key=lambda kv: ((kv[1][0] + 1) / (kv[1][1] + 2), kv[1][1]))
    print(f"{mp:22s} ours {' '.join(ours.get(mp, ())):38s}")
    for t in TEAMS:
        items = sorted([(k[1], v) for k, v in by.items() if k[0] == t], key=lambda kv: -kv[1][1])[:2]
        print('      ' + f"{t:5s} " + ' | '.join(f"{' '.join(s)} {v[0]}/{v[1]}" for s, v in items))
    out[mp] = {'ours': ours.get(mp), 'best': best[0][1], 'best_rec': best[1], 'best_team': best[0][0]}
if '--json' in sys.argv:
    json.dump(out, open(sys.argv[sys.argv.index('--json') + 1], 'w'), indent=1)
