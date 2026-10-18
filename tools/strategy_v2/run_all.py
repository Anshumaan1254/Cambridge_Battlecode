#!/usr/bin/env python3
"""One command from downloaded match groups to the strategy-v2 report.

usage: python3 tools/strategy_v2/run_all.py OUT_DIR INPUT [INPUT ...]

INPUT can be a match-group zip (the website download: a zip of five match zips), a single match zip, a folder of
those, or a .repl26a file. Run it from the repo root (it calls tools/replay/mapinfo.mjs and the engine wasm that
`cambc view` unpacks once; see README.md).

Writes:
  OUT_DIR/replays/<group>_<NN>_<map>.repl26a   the replays, named by group, order and official map
  OUT_DIR/dmg/<name>.json                      decoded with per-step damage (decode_dmg.mjs)
  OUT_DIR/mapgeo.json                          map grid, size, symmetry and spawn per replay (mapinfo.mjs)
  OUT_DIR/out/*.csv, analysis.json             analyze.py tables
  OUT_DIR/report.md                            report.py: the KPI tables, us (team 0 = side A) against them
Team 0 must be our bot: the archives we download contain only our side's logs (team-a.*) when we are side A.
"""
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
MAPINFO = os.path.join(ROOT, 'tools', 'replay', 'mapinfo.mjs')
DECODE = os.path.join(HERE, 'decode_dmg.mjs')


def safe_members(z):
    for i in z.infolist():
        n = i.filename
        if n.startswith('/') or '..' in n.split('/'):
            continue
        yield i


def collect(inputs, out):
    """Return a list of (name_stem, replay_bytes)."""
    found = []

    def from_zip(data, label):
        z = zipfile.ZipFile(io.BytesIO(data))
        names = [i for i in safe_members(z)]
        inner = [i for i in names if i.filename.endswith('.zip')]
        if inner:
            for k, i in enumerate(sorted(inner, key=lambda i: i.filename)):
                from_zip(z.read(i), f"{label}_{os.path.basename(i.filename)[:2]}")
            return
        for i in names:
            if i.filename.endswith('replay.repl26a') or i.filename.endswith('.repl26a'):
                found.append((label, z.read(i)))

    for inp in inputs:
        paths = sorted(glob.glob(os.path.join(inp, '**', '*'), recursive=True)) if os.path.isdir(inp) else [inp]
        for p in paths:
            if p.endswith('.zip'):
                base = os.path.basename(p)[:-4]
                m = re.search(r'match-group-([0-9a-f]{8})', base)
                label = m.group(1) if m else base[:12]
                from_zip(open(p, 'rb').read(), label)
            elif p.endswith('.repl26a'):
                found.append((os.path.basename(p)[:-8], open(p, 'rb').read()))
    return found


def map_dump(path):
    return subprocess.run(['node', MAPINFO, path], capture_output=True, text=True, check=True).stdout


def official_maps():
    res = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'maps', 'comp', '*.map26a'))):
        lines = map_dump(f).splitlines()
        res[hashlib.md5('\n'.join(lines[1:]).encode()).hexdigest()] = os.path.basename(f)[:-7]
    return res


def parse_dump(text):
    lines = text.splitlines()
    m = re.search(r'(\d+)x(\d+) sym (\S+).*spawnA (\d+),(\d+),(\d+),(\d+)', lines[0])
    w, h, sym, x0, y0, x1, y1 = m.groups()
    return dict(w=int(w), h=int(h), sym=sym, spawnA=[int(x0), int(y0), int(x1), int(y1)], grid=[l[4:] for l in lines[1:]])


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    out = os.path.abspath(sys.argv[1])
    for sub in ('replays', 'dmg', 'out'):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    reps = collect(sys.argv[2:], out)
    if not reps:
        sys.exit('no replays found')
    off = official_maps()
    geo = {}
    for label, data in reps:
        tmp = os.path.join(out, 'replays', label + '.repl26a')
        open(tmp, 'wb').write(data)
        dump = map_dump(tmp)
        h = hashlib.md5('\n'.join(dump.splitlines()[1:]).encode()).hexdigest()
        mp = off.get(h, 'unknown')
        stem = f'{label}_{mp}'
        final = os.path.join(out, 'replays', stem + '.repl26a')
        os.replace(tmp, final)
        geo[stem] = parse_dump(dump)
        subprocess.run(['node', DECODE, final, '--out', os.path.join(out, 'dmg', stem + '.json'), '--rollovers'], check=True)
        print('decoded', stem)
    json.dump(geo, open(os.path.join(out, 'mapgeo.json'), 'w'))
    subprocess.run([sys.executable, '-I', os.path.join(HERE, 'analyze.py'), os.path.join(out, 'dmg'), os.path.join(out, 'mapgeo.json'), os.path.join(out, 'out')], check=True)
    rep = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'report.py'), os.path.join(out, 'out', 'analysis.json'), os.path.join(out, 'dmg'), os.path.join(out, 'mapgeo.json')],
                         capture_output=True, text=True, check=True).stdout
    open(os.path.join(out, 'report.md'), 'w').write(rep)
    print(rep)


if __name__ == '__main__':
    main()
