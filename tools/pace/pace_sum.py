import sys, glob, os
sys.path.insert(0,'/home/user/Cambridge_Battlecode/tools')
from bench import load_stats
comp = {os.path.splitext(os.path.basename(m))[0] for m in glob.glob('/home/user/Cambridge_Battlecode/maps/comp/*.map26a')}
d = glob.glob(sys.argv[1]+'/*/')[0]
m = {}
for st in sorted(glob.glob(d+'*_[AB].json')):
    n = os.path.basename(st)[:-7]; side = st[-6]
    s = load_stats(st); us = 'teamA' if side=='A' else 'teamB'
    m.setdefault(n,[]).append(s['rounds'] if s['outcome']==us else 2000)
for k,v in sorted(m.items()): print(k, sum(v)//len(v), 'C' if k in comp else '')
al=[sum(v)/len(v) for v in m.values()]; cp=[sum(v)/len(v) for k,v in m.items() if k in comp]
print('ALL %.1f (%d maps) COMP %.1f' % (sum(al)/len(al), len(al), sum(cp)/len(cp)))
