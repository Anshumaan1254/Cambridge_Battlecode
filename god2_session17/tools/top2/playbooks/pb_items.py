# Build summary per study team from compact summaries (experiments/live/compact/<matchId>.json, only games in the team's t2 index):
# per champion: final item families / stats (counts), share of gold spent, health share; first purchases by round (buys).
#   python tools/top2/playbooks/pb_items.py
import sys, os, json, re
sys.path.insert(0, os.path.dirname(__file__))
from collections import Counter, defaultdict
from pbcommon import KEYS, ORDER

for k in ORDER:
    rows = [json.loads(l) for l in open(f'C:/battlecode/cache/t2/{k}/index.jsonl', encoding='utf-8')]
    n = 0
    fam = defaultdict(Counter)
    stat = defaultdict(Counter)
    firstbuy = defaultdict(Counter)
    spent = defaultdict(list)
    for r in rows:
        p = f"experiments/live/compact/{r['matchId']}.json"
        if not os.path.exists(p):
            continue
        d = json.load(open(p, encoding='utf-8'))
        me = [t for t in d['teams'] if t.get('teamId', '').startswith(KEYS[k])]
        if not me:
            continue
        team = me[0]['team']
        n += 1
        for c in d['champs']:
            if c['team'] != team:
                continue
            nm = c['name']
            spent[nm].append(c['m'].get('spentGold', 0))
            for it, cnt in c.get('items', []):
                m = re.match(r'(\w+) (Shard|Emblem) of (\w+)', it)
                if m:
                    fam[nm][m.group(1)] += cnt
                    stat[nm][m.group(3)] += cnt
        for b in d.get('buys', []):
            # buys rows: try to read owner / item / round
            if isinstance(b, dict):
                own = b.get('owner') or b.get('champ')
                it = b.get('item') or b.get('name')
                rr = b.get('round') or b.get('r')
            elif isinstance(b, list) and len(b) >= 3:
                rr, own, it = b[0], b[1], b[2]
            else:
                continue
            pass
    if not n:
        print(f'== {k}: no compact summaries')
        continue
    print(f'== {k}: {n} games')
    for nm in sorted(fam, key=lambda x: -sum(fam[x].values())):
        g = len(spent[nm])
        tot = sum(stat[nm].values())
        print(f"   {nm:14s} games {g:3d} gold spent {sum(spent[nm])/g:5.0f} | items/game {tot/g:4.1f} | families {', '.join(f'{f} {c/g:.1f}' for f, c in fam[nm].most_common(4))} | stats {', '.join(f'{s} {c/tot:.0%}' for s, c in stat[nm].most_common(4))}")
