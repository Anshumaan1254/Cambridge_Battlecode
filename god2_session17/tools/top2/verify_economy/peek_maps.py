# Quick look: camp-type composition, size and bodies per map from the fight dumps (one dump per map).
import gzip, json, glob, os
from collections import Counter
seen = {}
for f in sorted(glob.glob('C:/battlecode/cache/t2dump/*/*.json.gz')):
    m = os.path.basename(f).rsplit('_', 1)[0]
    if m in seen: continue
    d = json.load(gzip.open(f))
    seen[m] = (d['meta']['width'], d['meta']['height'], dict(Counter(str(c['type']) for c in d['meta']['camps'])), len(d['meta']['bodies']))
for m, v in sorted(seen.items()): print(m, v)
print(len(seen))
