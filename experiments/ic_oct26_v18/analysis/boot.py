"""Bootstrap 95% interval of the mean per-map margin (both sides averaged) for BOT vs OPP release rows; optional --pool glob list,
--base BASE for the paired difference (BOT vs OPP minus BASE vs OPP, same map and side).
    python3 -I boot.py BOT OPP [--base BASE] [--maps 'glob,glob']"""
import sys, os, random, glob
sys.path.insert(0, '/home/claude/cambridge_battlecode/tools')
import ledger
a = sys.argv[1:]
def opt(k, d=None):
    if k in a:
        i = a.index(k); v = a[i + 1]; del a[i:i + 2]; return v
    return d
base = opt('--base'); maps = opt('--maps')
bot, opp = a[0], a[1]
keep = None
if maps:
    keep = {os.path.splitext(os.path.basename(m))[0] for p in maps.split(',') for m in glob.glob(os.path.join('/home/claude/cambridge_battlecode', p))}
r = ledger.current_rows(bot, opp, True)
if keep is not None:
    r = {k: v for k, v in r.items() if k[0] in keep}
mg = lambda v: v['gems'][0] - v['gems'][1]
per = {}
if base:
    b = ledger.current_rows(base, opp, True)
    for k, v in r.items():
        if k in b:
            per.setdefault(k[0], []).append(mg(v) - mg(b[k]))
else:
    for (m, s), v in r.items():
        per.setdefault(m, []).append(mg(v))
vals = [sum(x) / len(x) for x in per.values()]
rnd = random.Random(7)
mu = sum(vals) / max(1, len(vals))
bs = sorted(sum(rnd.choice(vals) for _ in vals) / len(vals) for _ in range(4000))
w = sum(v['win'] for v in r.values())
print(f"{bot} vs {opp}{' (paired with ' + base + ')' if base else ''}: {len(vals)} maps, {len(r)} games, wins {w}/{len(r)} = {100 * w / max(1, len(r)):.1f}%, margin {mu:+.1f} [{bs[100]:+.1f}, {bs[3899]:+.1f}]")
