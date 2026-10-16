#!/usr/bin/env python3
"""Summarise LEGEND_TRACE lines (T r=.. type task=..) from team stdout logs: task share per champion."""
import sys, re, collections
names = ['ryth','vesper','vendetta','cassi','issac','stellar','prism','marcella','willow','ren','varg','tavi']
tasks = ['none','farm','capture','wait','tribute','home','fight','flee']
for path in sys.argv[1:]:
    cnt = collections.defaultdict(collections.Counter)
    for line in open(path, errors='replace'):
        line = line.replace('\x00', '').strip()
        m = re.match(r'T r=(\d+) (\d+) task=(\d+) g=(-?\d+)', line)
        if m:
            cnt[names[int(m.group(2))]][tasks[int(m.group(3))]] += 1
    print(path)
    for ch, c in cnt.items():
        tot = sum(c.values())
        print(f'  {ch:9s} turns={tot:4d} ' + ' '.join(f'{t}={100*c[t]/tot:4.1f}%' for t in tasks if c[t]))
