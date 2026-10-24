"""Per-map / per-side / per-opponent W-L of a team from a ranked list (e.g. experiments/live/lists/t2_pbg_ranked.jsonl), with time windows.
   python tools/top2/weak/wl_big.py LIST TEAMID8 [SINCE_ISO]"""
import json, sys, collections
path, tid = sys.argv[1], sys.argv[2]
since = sys.argv[3] if len(sys.argv) > 3 else ''
recs = []
for line in open(path, encoding='utf-8'):
    if not line.strip(): continue
    r = json.loads(line)
    if r.get('status') != 'finished' or r['createdAt'] < since: continue
    t = r['teams']; i = 0 if t[0]['teamId'].startswith(tid) else 1 if t[1]['teamId'].startswith(tid) else -1
    if i < 0: continue
    recs.append((r['createdAt'], r['map'], t[i]['result'], t[i]['side'], t[1-i]['name'], tuple(t[i]['draftPicks']), tuple(t[1-i]['draftPicks']), r.get('endReason')))
recs.sort()
print('n', len(recs), 'span', recs[0][0][:16], recs[-1][0][:16])
# by hour
c = collections.defaultdict(lambda: [0, 0])
for x in recs: c[x[0][:13]][0 if x[2] == 'win' else 1] += 1
print('by hour', ' '.join(f'{k[5:]}:{v[0]}-{v[1]}' for k, v in sorted(c.items())))
# drafts distinct
c = collections.Counter(x[5] for x in recs)
print('drafts', c.most_common(8))
c = collections.defaultdict(lambda: [0, 0])
for x in recs: c[x[3]][0 if x[2] == 'win' else 1] += 1
print('side', dict(c))
c = collections.defaultdict(lambda: [0, 0])
for x in recs: c[x[1]][0 if x[2] == 'win' else 1] += 1
print('map (W-L, sorted by loss rate):')
for k, v in sorted(c.items(), key=lambda kv: -(kv[1][1] + 0.5) / (sum(kv[1]) + 1)):
    print(f'   {k:24s} {v[0]:3d}-{v[1]:<3d} {100*v[0]/sum(v):5.0f}%')
c = collections.defaultdict(lambda: [0, 0])
for x in recs: c[x[4]][0 if x[2] == 'win' else 1] += 1
print('opp:', ', '.join(f'{k} {v[0]}-{v[1]}' for k, v in sorted(c.items(), key=lambda kv: -kv[1][1])))
