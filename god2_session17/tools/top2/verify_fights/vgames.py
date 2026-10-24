# Verify-fights (independent re-measure of experiments/top2/an_fights.md): game table.
# One row per dump: key, dump path, map, study team index (0/1), names, S won, drafts; cross-checked with the dump outcome.
#   python tools/top2/verify_fights/vgames.py OUT.json
import json, sys, os, gzip

TEAMS = {
    'pbg': 'prism best girl', 'ifish': 'Intercontinental Fish', 'pantheon': 'Pantheon',
    'coo': 'conqueror_of_openai', 'cm': 'Claudus Maximus', 'nyx': 'Nyx',
}
TEAM_ID8 = {'pbg': '38e6d8c4', 'ifish': '1890540d', 'pantheon': '547efb5b', 'coo': '1570a113', 'cm': 'ad5474c2', 'nyx': '6f7fd199'}
ROOT = 'C:/battlecode/cache'

out = []
bad = 0
for key in TEAMS:
    rows = [json.loads(l) for l in open(f'{ROOT}/t2/{key}/index.jsonl', encoding='utf-8')]
    for row in rows:
        m8 = row['matchId'][:8]
        dump = f"{ROOT}/t2dump/{key}/{row['map']}_{m8}.json.gz"
        if not os.path.exists(dump):
            print('missing', dump); continue
        si = [i for i, t in enumerate(row['teams']) if t['teamId'].startswith(TEAM_ID8[key])]
        assert len(si) == 1, (key, row['matchId'])
        t = row['teams'][si[0]]
        sidx = 0 if t['side'] == 'a' else 1
        o = row['teams'][1 - si[0]]
        swon = t['result'] == 'win'
        with gzip.open(dump) as f:
            meta = json.loads(f.read())['meta']
        oc = meta.get('outcome')
        dwin = (oc == 1 and sidx == 0) or (oc == 2 and sidx == 1)
        if dwin != swon:
            bad += 1
        out.append({'key': key, 'dump': dump, 'map': row['map'], 'match': row['matchId'], 'sidx': sidx, 'sname': t['name'],
                    'oname': o['name'], 'oid': o['teamId'], 'swon': swon, 'dwon': dwin, 'outcome': oc, 'final': meta.get('finalRound'),
                    'submitted': meta.get('submitted'), 'sdraft': t['draftPicks'], 'odraft': o['draftPicks'],
                    'ssize': sum(1 for b in meta['bodies'] if b['team'] == sidx), 'osize': sum(1 for b in meta['bodies'] if b['team'] != sidx),
                    'created': row['createdAt']})
json.dump(out, open(sys.argv[1], 'w'), indent=0)
print('games', len(out), 'outcome mismatches', bad)
from collections import Counter
c = Counter((g['key'], g['swon']) for g in out)
for k in TEAMS:
    print(k, 'W', c[(k, True)], 'L', c[(k, False)])
