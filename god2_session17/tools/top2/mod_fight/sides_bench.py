# mod_fight: sides file for a local bench (tools/live/localbench.py A B): replay <map>_A has bot A as engine team 0, <map>_B as team 1.
# Writes {"<map>_<side>": {"set": TAG, "ours": 0|1, "names": [team0 bot, team1 bot], "res": [..], "map": map, "opp": B}} for the
# dump-based scripts (tools/live/fightan.mjs SIDES DUMP).   python tools/top2/mod_fight/sides_bench.py BENCHDIR OUT.json A B
import glob, json, os, sys
bench, out, A, B = sys.argv[1:5]
S = {}
for f in sorted(glob.glob(os.path.join(bench, '*.json'))):
    name = os.path.basename(f)[:-5]
    if name == 'manifest':
        continue
    mp, side = name.rsplit('_', 1)
    try:
        d = json.load(open(f, encoding='utf-8'))
    except Exception:
        continue
    ours = 0 if side == 'A' else 1
    names = [A, B] if side == 'A' else [B, A]
    win = d['match']['outcome']  # 'teamA' | 'teamB'
    res = ['win' if win == 'teamA' else 'loss', 'win' if win == 'teamB' else 'loss']
    S[name] = {'set': os.path.basename(bench.rstrip('/')), 'ours': ours, 'names': names, 'res': res, 'map': mp, 'opp': B}
json.dump(S, open(out, 'w', encoding='utf-8'))
print(len(S), 'games ->', out)
