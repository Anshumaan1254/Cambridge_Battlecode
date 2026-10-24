"""v_tributes.py (verify_draft): tribute attempts per champion & team: starts, completion, bag at start, end reason.
Usage: python v_tributes.py ROLES.jsonl"""
import sys, collections
sys.path.insert(0, 'C:/battlecode/Cambridge_Battlecode/tools/top2/verify_draft')
from vagg import *
G = load(sys.argv[1]); D, _ = dedup(G)
def summarize(T, label):
    if not T: return
    n = len(T); done = sum(t['res'] == 'bank' for t in T)
    rs = collections.Counter(t['res'] for t in T if t['res'] != 'bank')
    failg = sum(t['bag'] for t in T if t['res'] != 'bank')
    print(f"  {label:28s} starts {n:4d} complete {done/n:5.0%} mean bag {mean(t['bag'] for t in T):5.0f} | fails: {dict(rs.most_common())} failed gems {failg}")
for key in ['pbg', 'pantheon', 'nyx', 'ifish', 'coo', 'cm']:
    gs = [g for g in D if g['key'] == key]
    print(f'== {key}')
    by = collections.defaultdict(list)
    for g in gs:
        for b in study_bodies(g):
            for t in b['tributes']: by[b['type']].append(dict(t, win=g['studyWin'], file=g['file']))
    for typ, T in sorted(by.items(), key=lambda x: -len(x[1])):
        summarize(T, typ)
        if typ == 'Prism':
            big = [t for t in T if t['bag'] >= 60]
            summarize(big, 'Prism bag>=60')
            summarize([t for t in T if t['priorLock'] == 0], 'Prism, no enemy lock <=60r before')
            summarize([t for t in T if t['win']], 'Prism in wins'); summarize([t for t in T if not t['win']], 'Prism in losses')
# opponents' Prisms
print('== opponents of study teams: Prism tributes')
T = []
for g in D:
    for b in opp_bodies(g, 'Prism'):
        T += b['tributes']
summarize(T, 'opp Prism (all study games)')
