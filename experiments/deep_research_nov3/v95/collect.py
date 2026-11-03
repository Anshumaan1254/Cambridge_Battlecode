import json, subprocess, sys
# page through unranked + ranked lists until createdAt < cutoff; write v95_matches.jsonl
CUT = '2026-11-03T12:40'
out = []
for kind in ['ranked', 'unranked']:
    cursor = None
    for page in range(8):
        cmd = ['cambc', 'matches', 'list', '--team', 'me', '--kind', kind, '--limit', '50', '--json']
        if cursor: cmd += ['--cursor', cursor]
        d = json.loads(subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout)
        ms = d['matches']
        stop = False
        for m in ms:
            if m['createdAt'] < CUT: stop = True; continue
            out.append(m)
        cursor = d.get('nextCursor')
        if stop or not cursor or not ms: break
seen=set(); 
with open('all_recent.jsonl', 'w') as f:
    for m in out:
        if m['matchId'] in seen: continue
        seen.add(m['matchId']); f.write(json.dumps(m) + '\n')
print(len(seen))
