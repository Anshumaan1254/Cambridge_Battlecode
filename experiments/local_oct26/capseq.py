"""Capture sequence on one map: IC (ladder game vs v18) vs v18 unopposed (local vs idle). python -I capseq.py MAP [MAXROUND]"""
import glob, gzip, json, os, sys, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
mp = sys.argv[1]; mr = int(sys.argv[2]) if len(sys.argv) > 2 else 400
S = json.load(open(os.path.join(ROOT, 'experiments/ladder_oct26_v74/sides_ic.json')))
def show(d, side, lab):
    typ = {b['index']: b['type'][:4] for b in d['meta']['bodies']}
    ev = [e for e in d['events'] if e['k'] == 'CaptureGems' and e.get('team') == side and e['r'] <= mr]
    bodies = [b['type'] for b in d['meta']['bodies'] if b['team'] == side]
    tot = 0; line = []
    for e in ev:
        tot += e['gems']; line.append('r%d %s %dg/%d$ @%s' % (e['r'], typ[e['who']], e['gems'], e['gold'], tuple(e['at'])))
    print('== %s %s bodies %s: %d captures, %d gems by r%d' % (lab, mp, bodies, len(ev), tot, mr))
    print('   ' + ' | '.join(line))
for k, v in S.items():
    if v['map'] == mp:
        d = json.load(gzip.open(os.path.join(ROOT, 'experiments/ladder_oct26_v74/dec', k + '.json.gz'))); show(d, 1 - v['ours'], 'IC'); show(d, v['ours'], 'v18-vs-IC'); break
f = glob.glob(os.path.join(ROOT, 'experiments/local_oct26/trdec', 'idle_%s_a_*.json' % mp.replace('_', '-')))
if f: show(json.load(open(f[0])), 1, 'v18-unopposed')
