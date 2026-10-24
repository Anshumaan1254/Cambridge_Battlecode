import gzip, json, sys
from collections import Counter
d = json.load(gzip.open(sys.argv[1]))
m = d['meta']
print('bodies', m['bodies'])
print('ngroups', m['ngroups'], 'ncamps', len(m['camps']))
print('camps', m['camps'][:12])
print('camp g values', sorted(Counter(c[1] for c in m['camps']).items())[:40])
print('K', d['K'][:8], len(d['K']))
print('G', d['G'][:12], len(d['G']))
print('C', d['C'][:12], len(d['C']))
print('D kinds', Counter((x[6], x[7]) for x in d['D']))
print('D sample', [x for x in d['D'] if x[6] == 2][:6])
print('D death', [x for x in d['D'] if x[5] != 0][:6])
