#!/usr/bin/env python3
"""Portable tools/variant.sh: copy SRC's src/ to bots/NAME and override params.h fields / add #defines.

    python tools/mkvariant.py NAME --src bots/god18 [key=value ...] [--define MACRO[=VAL] ...]
"""
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    a = sys.argv[1:]
    name = a.pop(0)
    src = 'bots/god18'
    sets, defs = [], []
    while a:
        x = a.pop(0)
        if x == '--src':
            src = a.pop(0)
        elif x == '--define':
            defs.append(a.pop(0))
        else:
            sets.append(x)
    dst = os.path.join(ROOT, 'bots', name)
    if os.path.exists(os.path.join(dst, 'src')):
        shutil.rmtree(os.path.join(dst, 'src'))
    shutil.copytree(os.path.join(ROOT, src, 'src'), os.path.join(dst, 'src'))
    p = os.path.join(dst, 'src', 'params.h')
    s = open(p, encoding='utf-8').read()
    for kv in sets:
        k, v = kv.split('=', 1)
        s, n = re.subn(r'^(\s*[a-z]+ ' + re.escape(k) + r' = )[^;]*;', lambda m: m.group(1) + v + ';', s, flags=re.M)
        if n != 1:
            sys.exit('unknown param ' + k)
    if defs:
        s = ''.join('#define %s\n' % d.replace('=', ' ', 1) for d in defs) + s
    open(p, 'w', encoding='utf-8', newline='').write(s)
    print('bots/%s ready (%s)' % (name, ' '.join(sets + ['-D' + d for d in defs])))


if __name__ == '__main__':
    main()
