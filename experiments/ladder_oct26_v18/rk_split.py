"""Split the ranked index by our result: OUT_loss.json / OUT_win.json (optionally only some sets).
    python3 -I rk_split.py /tmp/claude-0/rk_all.json /tmp/claude-0/rk [sets]"""
import json, sys
idx = json.load(open(sys.argv[1]))
sets = set(sys.argv[3].split(',')) if len(sys.argv) > 3 else None
for r in ('loss', 'win'):
    sub = {p: dict(v, set='rk') for p, v in idx.items() if v['res'][v['ours']] == r and (not sets or v['set'] in sets)}
    json.dump(sub, open(f'{sys.argv[2]}_{r}.json', 'w'))
    print(r, len(sub))
