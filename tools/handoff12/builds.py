#!/usr/bin/env python3
"""Per-team, per-champion build summary from analyze.py body.csv.
usage: builds.py OUT_DIR=GROUP:L0:L1[,..] ... [--skip contest] [--team LABEL]"""
import csv, json, sys, collections, statistics as st
args = sys.argv[1:]
skip = []
if '--skip' in args:
    i = args.index('--skip'); skip = args[i+1].split(','); del args[i:i+2]
only = None
if '--team' in args:
    i = args.index('--team'); only = args[i+1].split(','); del args[i:i+2]
R = collections.defaultdict(list)
for a in args:
    d, spec = a.split('=', 1)
    labels = {}
    for s in spec.split(','):
        g, l0, l1 = s.split(':'); labels[g] = (l0, l1)
    for r in csv.DictReader(open(d + '/body.csv')):
        if any(s in r['match'] for s in skip): continue
        g = r['match'][:8]
        key = g if g in labels else ('*' if '*' in labels else None)
        if not key: continue
        lab = labels[key][int(r['team'])]
        if only and lab not in only: continue
        R[(lab, r['champ'])].append(r)
def med(v):
    v = [x for x in v if x is not None]
    return st.median(v) if v else None
for (lab, ch), rows in sorted(R.items()):
    em = collections.Counter(); first = collections.Counter(); second = collections.Counter()
    fe = []; fc = []; g150 = []; s300 = []; s150 = []
    for r in rows:
        e = json.loads(r['emblems'])
        if e: first[e[0].split(':')[1]] += 1
        if len(e) > 1: second[e[1].split(':')[1]] += 1
        for x in e: em[x.split(':')[1]] += 1
        fe.append(int(r['first_emblem']) if r['first_emblem'] not in ('', '999') else None)
        fc.append(int(r['first_cap']) if r['first_cap'] not in ('', '-1', '999') else None)
        g150.append(int(r['gold150']))
        s3 = json.loads(r['stat300']); s1 = json.loads(r['stat150'])
        s300.append(s3); s150.append(s1)
    n = len(rows)
    hp300 = med([s[0] for s in s300]); st300 = med([s[1] for s in s300]); fo300 = med([s[2] for s in s300])
    print(f"{lab:5s} {ch:8s} n={n:2d} firstEmb med r{med(fe)} firstCap med r{med(fc)} gold150 med {med(g150)} | r300 hp/str/foc {hp300}/{st300}/{fo300} | 1st {dict(first.most_common(3))} 2nd {dict(second.most_common(3))} | all {dict(em.most_common(6))}")
