#!/usr/bin/env python3
"""Bake learned parameters (tune_out/es/best_params.json or any {key: value} JSON) into bots/legend/src/params.h.

usage: apply_params.py [best_params.json] [--dry-run]
"""
import json, os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
path = next((a for a in sys.argv[1:] if not a.startswith('--')), os.path.join(ROOT, 'tune_out/es/best_params.json'))
dry = '--dry-run' in sys.argv
vals = json.load(open(path))
hp = os.path.join(ROOT, 'bots/legend/src/params.h')
src = open(hp).read()
for k, v in vals.items():
    new, n = re.subn(rf'^(\s*\w+ {k} = )[^;]*;', rf'\g<1>{v};', src, flags=re.M)
    if n != 1:
        print(f'skip {k}: not found in params.h')
        continue
    src = new
    print(f'{k} = {v}')
if not dry:
    open(hp, 'w').write(src)
