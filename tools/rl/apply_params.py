#!/usr/bin/env python3
"""Bake learned parameters (tune_out/es/best_params.json or any {key: value} JSON) into bots/legend/src/params.h.

usage: apply_params.py [best_params.json] [--bot NAME] [--dry-run]
  --bot NAME   write into bots/NAME/src/params.h instead (validate on a copy before touching legend)
"""
import json, os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
args = sys.argv[1:]
bot = 'legend'
if '--bot' in args:
    i = args.index('--bot')
    bot = args[i + 1]
    del args[i:i + 2]
path = next((a for a in args if not a.startswith('--')), os.path.join(ROOT, 'tune_out/es/best_params.json'))
dry = '--dry-run' in args
vals = json.load(open(path))
hp = os.path.join(ROOT, 'bots', bot, 'src', 'params.h')
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
