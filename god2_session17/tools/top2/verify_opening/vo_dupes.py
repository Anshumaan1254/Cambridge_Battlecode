# Content fingerprints of the study dumps: how many of the 584 "unique" match ids are identical game replays
# (deterministic engine: same two bot versions, same map, same sides -> same game).
# Usage: python tools/top2/verify_opening/vo_dupes.py OUT.json
import gzip, json, glob, os, hashlib, sys, collections
from multiprocessing import Pool
CACHE = 'C:/battlecode/cache'
KEYS = ('pbg', 'ifish', 'pantheon', 'coo', 'cm', 'nyx')


def fp(p):
    d = json.load(gzip.open(p))
    h = hashlib.sha1(json.dumps([d['meta']['bodies'], d['R'][:301]]).encode()).hexdigest()
    hfull = hashlib.sha1(json.dumps([d['R'], d['meta']['finalRound'], d['meta']['submitted']]).encode()).hexdigest()
    return os.path.basename(p), os.path.basename(os.path.dirname(p)), h, hfull


if __name__ == '__main__':
    files = sorted(glob.glob(f'{CACHE}/t2dump/*/*.json.gz'))
    files = [f for f in files if os.path.basename(os.path.dirname(f)) in KEYS]
    with Pool(3) as pool:
        res = pool.map(fp, files, chunksize=4)
    json.dump(res, open(sys.argv[1], 'w'))
    by_mid = {}
    for b, k, h, hf in res:
        by_mid.setdefault(b.rsplit('_', 1)[1][:8], (h, hf))
    print('dumps', len(res), 'unique match ids', len(by_mid), 'distinct r1-300 contents', len({v[0] for v in by_mid.values()}),
          'distinct full contents', len({v[1] for v in by_mid.values()}))
    c = collections.Counter(v[1] for v in by_mid.values())
    print('multiplicity of full contents', collections.Counter(c.values()))
