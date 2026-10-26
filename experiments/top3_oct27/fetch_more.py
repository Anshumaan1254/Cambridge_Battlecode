"""Ranked matches (engine 2.0.0, since 2026-10-26 00:24 UTC) for our team and ladder ranks 4-12 -> experiments/top3_oct27/ranked_<slug>.jsonl.
    python3 -I fetch_more.py"""
import json, os, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__))
SINCE = '2026-10-26T00:24'
env = {k: v for k, v in os.environ.items() if k.lower() != 'no_proxy'}
lad = json.load(open('/tmp/claude-0/-home-claude/f3877353-3092-5ac8-aae3-9269d426c2cd/scratchpad/ladder_now.json'))['teams']
teams = {'us': '5a103c90-b00b-4d46-8ace-6a3bb058dc72'}
for t in lad:
    if 4 <= t['rank'] <= 12:
        teams[f"r{t['rank']:02d}"] = t['teamId']
for name, tid in teams.items():
    out, cur, seen = [], None, set()
    while True:
        cmd = ['cambc', 'matches', 'list', '--team', tid, '--kind', 'ranked', '--limit', '100', '--json'] + (['--cursor', cur] if cur else [])
        d = None
        for a in range(4):
            p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
            try:
                d = json.loads(p.stdout); break
            except Exception:
                time.sleep(5 * (a + 1))
        if d is None:
            print('fetch failed', name); break
        stop = False
        for m in d['matches']:
            if m['createdAt'] < SINCE:
                stop = True; break
            if m['matchId'] in seen or m.get('status') != 'finished' or any(t.get('engineVersion') != '2.0.0' for t in m['teams']):
                continue
            seen.add(m['matchId']); out.append(m)
        cur = d.get('nextCursor')
        if stop or not cur or not d['matches']:
            break
    with open(os.path.join(HERE, f'ranked_{name}.jsonl'), 'w') as f:
        for m in out:
            f.write(json.dumps(m) + '\n')
    print(name, tid[:8], len(out))
