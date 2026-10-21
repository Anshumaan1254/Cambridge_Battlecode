#!/usr/bin/env python3
"""tools/pdiff.py BASE BOT... : parameter values (params.h `int|float name = value;`) that differ from BASE, per bot."""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RX = re.compile(r'^\s*(?:int|float|double|bool|unsigned)\s+(\w+)\s*=\s*([^;]+);', re.M)


def params(bot):
	t = open(os.path.join(ROOT, 'bots', bot, 'src', 'params.h')).read()
	d = {k: v.strip() for k, v in RX.findall(t)}
	d.update({'#' + k: v.strip() for k, v in re.findall(r'^#define\s+(\w+)\s*(.*)$', t, re.M)})
	return d


def main():
	base, bots = sys.argv[1], sys.argv[2:]
	b = params(base)
	for x in bots:
		p = params(x)
		diff = [f'{k}={p[k]}' for k in sorted(p) if k in b and p[k] != b[k]] + [f'+{k}={p[k]}' for k in sorted(p) if k not in b]
		print(f'{x}: ' + ' '.join(diff))


if __name__ == '__main__':
	main()
