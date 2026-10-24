# Distinct replay list (one file per match basename), study-team order pbg, ifish, cm, pantheon, coo, nyx.
import glob, os
seen, out = set(), []
for k in ['pbg', 'ifish', 'cm', 'pantheon', 'coo', 'nyx']:
    for f in sorted(glob.glob(f'C:/battlecode/cache/t2/{k}/*.repl26a')):
        b = os.path.basename(f)
        if b in seen: continue
        seen.add(b); out.append(f)
open('C:/battlecode/cache/vecon/files.txt', 'w').write('\n'.join(out) + '\n')
print(len(out))
