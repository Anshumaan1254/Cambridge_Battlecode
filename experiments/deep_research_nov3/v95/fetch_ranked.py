import json, subprocess
# read-only: page our ranked list back to Nov 2 21:00Z -> ranked_recent.jsonl
out, cursor = [], None
for page in range(20):
    cmd = ['cambc', 'matches', 'list', '--team', 'me', '--kind', 'ranked', '--limit', '50', '--json'] + (['--cursor', cursor] if cursor else [])
    d = json.loads(subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout)
    out += d['matches']
    cursor = d.get('nextCursor')
    if not cursor or not d['matches'] or d['matches'][-1]['createdAt'] < '2026-11-02T21:00':
        break
with open('ranked_recent.jsonl', 'w') as f:
    for m in out:
        f.write(json.dumps(m) + '\n')
print(len(out), out[-1]['createdAt'])
