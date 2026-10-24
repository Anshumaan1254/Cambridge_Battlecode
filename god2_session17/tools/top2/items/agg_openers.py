# Which observable map / draft features go with a team's alternative first emblem (e.g. Jungle or Monster instead of Power / Treasure)?
#   python tools/top2/items/agg_openers.py C:/battlecode/cache/top2_items/ix_all.jsonl
import sys, json, collections
sys.path.insert(0, 'tools/top2/items')
from common import *

idx = load_index()
sig = {}
for l in open('experiments/live/map_sig.jsonl', encoding='utf-8'):
    m = json.loads(l)
    sig[m['file'].replace('.repl26a', '').replace('-', '_')] = m
terrain = json.load(open('experiments/live/map_terrain.json'))
spawns = json.load(open('experiments/live/spawns.json'))
DRAFT = ['Ryth', 'VesperVale', 'Vendetta', 'CassiIssac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin']
res = collections.defaultdict(list)
for l in open(sys.argv[1], encoding='utf-8'):
    g = json.loads(l)
    stem = g['file'].replace('.repl26a', '')
    for st in idx.get(stem, []):
        mp = st['map']
        s = sig.get(mp, {})
        t = terrain.get(mp, {})
        sp = spawns.get(mp)
        sd = max(abs(sp[0][0] - sp[1][0]), abs(sp[0][1] - sp[1][1])) if sp else None
        for b in g['B']:
            if b['t'] != st['ti']:
                continue
            eo = emblem_order(b['buys'])
            if not eo:
                continue
            res[(st['key'], b['ty'])].append(dict(first=eo[0][1], map=mp, area=g['W'] * g['H'], camps=s.get('camps'), dens=(s.get('camps') or 0) / (g['W'] * g['H']) * 1000,
                                                 wall=t.get('wall'), bush=t.get('bush'), hole=t.get('hole'), sd=sd, edraft=[DRAFT[x] for x in (st['odraft'] or [])]))
for key, v in sorted(res.items()):
    c = collections.Counter(x['first'] for x in v)
    if len(c) < 2 or len(v) < 10:
        continue
    print(f'\n{key[0]} {SHORT[key[1]]}: first emblem {dict(c.most_common())}')
    for first, n in c.most_common():
        sub = [x for x in v if x['first'] == first]
        mm = collections.Counter(x['map'] for x in sub)
        print(f'  {first} n={n}: area med {fmt(med([x["area"] for x in sub]))}, camps med {med([x["camps"] for x in sub if x["camps"]])}, camps per 1000 tiles med {fmt(med([x["dens"] for x in sub]), 1)}, '
              f'spawn dist med {med([x["sd"] for x in sub if x["sd"]])}, wall {fmt(mean([x["wall"] for x in sub if x["wall"] is not None]), 3)}, bush {fmt(mean([x["bush"] for x in sub if x["bush"] is not None]), 3)}; maps {dict(mm.most_common(12))}')
    # per map consistency: maps where the opener is always the same
    bym = collections.defaultdict(collections.Counter)
    for x in v:
        bym[x['map']][x['first']] += 1
    mixed = {m: dict(cc) for m, cc in bym.items() if len(cc) > 1}
    print(f'  maps with mixed openers: {mixed}')
