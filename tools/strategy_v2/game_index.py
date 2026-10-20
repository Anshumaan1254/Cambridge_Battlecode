#!/usr/bin/env python3
"""Per-game index of a run_all.py analysis directory (the format death_ctx.py / burst_ctx.py / ladder_pergame.py read):
group, nn, side, file, map, w, h, sym, champs, drafts, outcome, win, rounds, banked gems, deaths.

usage: python3 -I tools/strategy_v2/game_index.py AN_DIR MAPPING_TXT OUT_JSON [MAP_DIR ...]
AN_DIR: run_all.py's output (dmg/*.json). MAPPING_TXT: the stdout of `node tools/replay/extract_map.mjs --dir AN_DIR/replays DIR PREFIX`
(one line per replay: "<replay> -> <stem> {...}" or "<replay> -> same map as <stem>"). The extracted file is matched by content hash to a map
already in MAP_DIR (default maps/nyx_new maps/comp30 maps/comp maps/loss_oct20); otherwise the index names the extracted stem (copy it into a map folder).
"""
import glob
import hashlib
import json
import os
import re
import sys

an, mapping, out = sys.argv[1:4]
map_dirs = sys.argv[4:] or ['maps/nyx_new', 'maps/comp30', 'maps/comp', 'maps/loss_oct20']
known = {}
for d in map_dirs:
    for f in glob.glob(os.path.join(d, '*.map26a')):
        known[hashlib.sha1(open(f, 'rb').read()).hexdigest()] = os.path.basename(f)[:-len('.map26a')]
ext_dir = None
stem_of = {}
for line in open(mapping):
    m = re.match(r'(\S+\.repl26a) -> (?:same map as )?(\S+)', line.strip())
    if m:
        stem_of[os.path.basename(m.group(1))[:-len('.repl26a')]] = m.group(2)
rows = []
for f in sorted(glob.glob(os.path.join(an, 'dmg', '*.json'))):
    d = json.load(open(f))
    m = d['meta']
    stem = os.path.basename(f)[:-5]
    ext = stem_of.get(stem)
    mapname = ext
    if ext:
        for cand in glob.glob(os.path.join(os.path.dirname(mapping), '*', ext + '.map26a')) + glob.glob(os.path.join(os.path.dirname(mapping), ext + '.map26a')):
            h = hashlib.sha1(open(cand, 'rb').read()).hexdigest()
            if h in known:
                mapname = known[h]
                break
    last = d['rounds'][-1]
    deaths = [0, 0]
    for e in d['events']:
        if e.get('k') == 'Death':
            deaths[e['team']] += 1
    gems = last['sub']
    win = m['outcome'] == 1
    rows.append({'group': stem.split('_')[0], 'nn': stem.split('_')[1], 'side': 'A', 'file': os.path.relpath(f.replace('/dmg/', '/replays/')[:-5] + '.repl26a'),
                 'map': mapname, 'w': m['width'], 'h': m['height'], 'champs': m['champsPerTeam'], 'us_draft': m['drafts'][0], 'them_draft': m['drafts'][1],
                 'outcome': m['outcome'], 'win': win, 'rounds': m['finalRound'], 'us_gems': gems[0], 'them_gems': gems[1], 'deaths': deaths})
json.dump(rows, open(out, 'w'), indent=1)
for r in rows:
    print(f"{r['group']}_{r['nn']} {str(r['map'])[:26]:27s} {r['champs']} us={','.join(x[:4] for x in r['us_draft']):27s} them={','.join(x[:4] for x in r['them_draft']):27s} "
          f"r{r['rounds']:5d} {r['us_gems']:4d}-{r['them_gems']:4d} d={r['deaths'][0]:2d}-{r['deaths'][1]:2d} {'WIN' if r['win'] else ''}")
