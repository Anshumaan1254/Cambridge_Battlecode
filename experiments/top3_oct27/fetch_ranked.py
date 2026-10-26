"""Ranked matches of the top-3 teams on engine 2.0.0 (since 2026-10-26 00:24 UTC) -> experiments/top3_oct27/<team>_ranked.jsonl.
    python3 -I fetch_ranked.py"""
import json, os, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__))
TEAMS = {'ic': '1890540d-1ffc-4847-adbf-d0d08772f268', 'mite': 'ee83f5e5-bcad-4923-86b4-b79ea6083d2e', 'tk': '36258abf-3fd0-4827-8fa5-2a217438cf6f'}
SINCE = '2026-10-26T00:24'
env = {k: v for k, v in os.environ.items() if k.lower() != 'no_proxy'}
for name, tid in TEAMS.items():
    out, cur, seen = [], None, set()
    while True:
        cmd = ['cambc', 'matches', 'list', '--team', tid, '--kind', 'ranked', '--limit', '100', '--json'] + (['--cursor', cur] if cur else [])
        for a in range(4):
            p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
            try:
                d = json.loads(p.stdout); break
            except Exception:
                time.sleep(5 * (a + 1))
        else:
            print('fetch failed', name); break
        ms = d['matches']
        stop = False
        for m in ms:
            if m['createdAt'] < SINCE:
                stop = True; break
            if m['matchId'] in seen or m.get('status') != 'finished':
                continue
            if any(t.get('engineVersion') != '2.0.0' for t in m['teams']):
                continue
            seen.add(m['matchId']); out.append(m)
        cur = d.get('nextCursor')
        if stop or not cur or not ms:
            break
    with open(os.path.join(HERE, f'{name}_ranked.jsonl'), 'w') as f:
        for m in out:
            f.write(json.dumps(m) + '\n')
    print(name, len(out), out[-1]['createdAt'] if out else '')
