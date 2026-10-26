"""Captured gems/gold by round R: v18 unopposed (vs idle, side b) vs IC (side b) in the ladder games vs v18, same maps."""
import glob, gzip, json, os, subprocess, collections, statistics as st
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CPS = [50, 100, 150, 200, 300]
def caps(d, side):
    out = {c: [0, 0] for c in CPS}
    for e in d['events']:
        if e['k'] == 'CaptureGems' and e.get('team') == side:
            for c in CPS:
                if e['r'] <= c: out[c][0] += e['gems']; out[c][1] += e['gold']
    return out
loc = {}
for f in glob.glob(os.path.join(ROOT, 'experiments/ab/idle_v18b/g/*.repl26a')):
    mp = os.path.basename(f).rsplit('_a_', 1)[0]
    out = os.path.join(ROOT, 'experiments/local_oct26/trdec', 'idle_' + os.path.basename(f) + '.json')
    if not os.path.exists(out): subprocess.run(['node', os.path.join(ROOT, 'tools/replay/decode.mjs'), f, '--out', out], check=True, capture_output=True)
    loc[mp] = caps(json.load(open(out)), 1)
S = json.load(open(os.path.join(ROOT, 'experiments/ladder_oct26_v74/sides_ic.json')))
ic = {}; us = {}
for k, v in S.items():
    d = json.load(gzip.open(os.path.join(ROOT, 'experiments/ladder_oct26_v74/dec', k + '.json.gz')))
    ic[v['map']] = caps(d, 1 - v['ours']); us[v['map']] = caps(d, v['ours'])
common = sorted(set(loc) & set(ic))
print(len(common), 'maps')
for c in CPS:
    print('by r%d: v18 unopposed %5.0f gems %5.0f gold | IC vs v18 %5.0f gems %5.0f gold | v18 vs IC %5.0f gems' % (c, st.mean(loc[m][c][0] for m in common), st.mean(loc[m][c][1] for m in common), st.mean(ic[m][c][0] for m in common), st.mean(ic[m][c][1] for m in common), st.mean(us[m][c][0] for m in common)))
worse = sorted(common, key=lambda m: loc[m][150][0] - ic[m][150][0])
print('maps where unopposed v18 trails IC most by r150:', [(m, loc[m][150][0], ic[m][150][0]) for m in worse[:12]])
