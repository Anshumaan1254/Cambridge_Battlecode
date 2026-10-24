"""W/L tables for the study teams from platform match lists (index.jsonl of the t2 replay sets and the ranked lists).
   python tools/top2/weak/wl_lists.py   -> prints per team: record, by map, by side, by opponent, by end reason; JSON to stdout file arg."""
import json, sys, collections, os
TEAMS = {'pbg': '38e6d8c4', 'ifish': '1890540d', 'cm': 'ad5474c2', 'pantheon': '547efb5b', 'coo': '1570a113', 'nyx': '6f7fd199'}
def rows(path):
    out = []
    if not os.path.exists(path): return out
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        if line: out.append(json.loads(line))
    return out
def me_other(row, tid8):
    t = row['teams']
    if t[0]['teamId'].startswith(tid8): return t[0], t[1]
    if t[1]['teamId'].startswith(tid8): return t[1], t[0]
    return None, None
res = {}
for key, tid in TEAMS.items():
    for src, path in [('t2', f'C:/battlecode/cache/t2/{key}/index.jsonl'), ('wr', f'experiments/live/lists/wr/{tid}.jsonl')]:
        rs = rows(path)
        recs = []
        for r in rs:
            if r.get('status') != 'finished': continue
            me, op = me_other(r, tid)
            if me is None: continue
            recs.append({'map': r['map'], 'res': me['result'], 'side': me['side'], 'opp': op['name'], 'end': r.get('endReason'), 'at': r['createdAt'], 'draft': me['draftPicks'], 'odraft': op['draftPicks'], 'mid': r['matchId']})
        if not recs: continue
        recs.sort(key=lambda x: x['at'])
        W = sum(1 for x in recs if x['res'] == 'win'); L = sum(1 for x in recs if x['res'] == 'loss')
        print(f'== {key} [{src}] n={len(recs)} W {W} L {L} ({100*W/max(1,W+L):.0f}%) span {recs[0]["at"][:16]} .. {recs[-1]["at"][:16]}')
        for lab, f in [('side', lambda x: x['side']), ('end', lambda x: x['end'])]:
            c = collections.defaultdict(lambda: [0, 0])
            for x in recs: c[f(x)][0 if x['res'] == 'win' else 1] += 1
            print('  ', lab, ' '.join(f'{k}:{v[0]}-{v[1]}' for k, v in sorted(c.items(), key=lambda kv: str(kv[0]))))
        c = collections.defaultdict(lambda: [0, 0])
        for x in recs: c[x['opp']][0 if x['res'] == 'win' else 1] += 1
        print('   losses by opp:', ', '.join(f'{k} {v[0]}-{v[1]}' for k, v in sorted(c.items(), key=lambda kv: -kv[1][1]) if v[1] > 0))
        c = collections.defaultdict(lambda: [0, 0])
        for x in recs: c[x['map']][0 if x['res'] == 'win' else 1] += 1
        print('   losses by map:', ', '.join(f'{k} {v[0]}-{v[1]}' for k, v in sorted(c.items(), key=lambda kv: (-kv[1][1], kv[1][0])) if v[1] > 0))
        res[f'{key}_{src}'] = recs
json.dump(res, open(sys.argv[1] if len(sys.argv) > 1 else 'NUL', 'w'), indent=0)
