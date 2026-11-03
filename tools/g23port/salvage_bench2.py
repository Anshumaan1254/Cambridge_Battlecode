"""Salvage finished games of an interrupted bench2 run into rows.jsonl (bench2 then runs only the rest)."""
import sys, os, json, glob
sys.path.insert(0, '/home/claude/analysis')
import bench2
tag = sys.argv[1]
out = os.path.join(bench2.ROOT, 'experiments', 'ab2', tag)
rows_p = os.path.join(out, 'rows.jsonl')
have = set()
if os.path.exists(rows_p):
    for l in open(rows_p): r = json.loads(l); have.add((r['map'], r['side']))
n = bad = 0
with open(rows_p, 'a') as f:
    for sp in sorted(glob.glob(os.path.join(out, 'g', '*.json'))):
        base = os.path.basename(sp)[:-5]; mn, side = base.rsplit('_', 1)
        if (mn, side) in have: continue
        try:
            d = json.load(open(sp))
            me = bench2.team_stats(d, side); them = bench2.team_stats(d, 'b' if side == 'a' else 'a')
            outc = d['match']['outcome']; win = (outc == 'teamA' and side == 'a') or (outc == 'teamB' and side == 'b')
            r = {'map': mn, 'side': side, 'win': bool(win), 'rounds': int(d['match']['roundsCompleted']), 'me': me, 'them': them,
                 'faults': d.get('diagnostics', {}).get('botFaults', {})}
        except Exception as e:
            bad += 1; os.remove(sp); continue
        f.write(json.dumps(r) + '\n'); n += 1
        os.remove(sp)
        rp = sp[:-5] + '.repl26a'
        if os.path.exists(rp): os.remove(rp)
print(f'{tag}: salvaged {n} rows, dropped {bad} unreadable')
