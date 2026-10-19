#!/usr/bin/env python3
"""Check that the bot's in-game ml2 features match the dataset features (agent ml2, session 13).

usage: python3 -I tools/ml/ml2_parity.py BUNDLE.repl26a MAP.map26a [--team 0]

BUNDLE: a local `cambc run` bundle of a bot built with --define "ML2_DEBUG 1" and the model switched on (it prints one
'ML2 r=R b=B p=P f=...' line per combat() evaluation with an enemy within 7). The replay inside is decoded and the
dataset rows of that team are rebuilt; the bot's round R is matched with the dataset's state round R - 1 (the state at
the end of the round before its turn). Prints per feature the mean absolute difference and the share of exact matches.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools', 'strategy_v2'))
import ml2_dataset as D  # noqa: E402
from run_all import map_dump, parse_dump  # noqa: E402


def main():
	a = sys.argv[1:]
	team = 0
	a = [x for x in a if x != '--show']
	if '--team' in a:
		i = a.index('--team'); team = int(a[i + 1]); del a[i:i + 2]
	bundle, mp = a
	z = zipfile.ZipFile(bundle)
	out = z.read(f'team-{"ab"[team]}.stdout').decode()
	tmp = tempfile.mkdtemp()
	rp = os.path.join(tmp, 'r.repl26a')
	open(rp, 'wb').write(z.read('replay.repl26a'))
	js = os.path.join(tmp, 'r.json')
	subprocess.run(['node', os.path.join(ROOT, 'tools', 'strategy_v2', 'decode_dmg.mjs'), rp, '--out', js], check=True)
	geo = parse_dump(map_dump(rp))
	X, Y, M, meta = D.game_rows(js, geo, team, 'local', 0)
	rows = {}
	for x, m in zip(X, M):
		if m[5] == team:
			rows[(m[2], m[1])] = x
	team_bodies = sorted(b['index'] for b in meta['bodies'] if b['team'] == team)
	bot = []
	for line in (l.strip().strip('\x00') for l in out.splitlines()):
		if not line.startswith('ML2 '):
			continue
		parts = dict(p.split('=', 1) for p in line.split()[1:])
		r, bi = int(parts['r']), int(parts['b'])
		f = [float(v) for v in parts['f'].rstrip(',').split(',')]
		bot.append((r, team_bodies[bi] if bi < len(team_bodies) else bi, f, float(parts['p'])))
	pairs = [(rows[(r - 1, b)], f) for r, b, f, p in bot if (r - 1, b) in rows]
	print(f'bot lines {len(bot)}, matched to dataset rows {len(pairs)}, dataset rows of the team {len(rows)}')
	if not pairs:
		return
	A = np.array([p[0] for p in pairs])
	B = np.array([p[1] for p in pairs])
	if '--show' in sys.argv:
		ia = D.FEATURES.index('log_adv')
		order = np.argsort(-np.abs(A[:, ia] - B[:, ia]))[:8]
		keys = [(r, b) for r, b, f, p in bot if (r - 1, b) in rows]
		for k in order:
			print('row', keys[k], 'py', ' '.join(f'{D.FEATURES[i]}={A[k, i]:.2f}' for i in range(len(D.FEATURES)) if abs(A[k, i] - B[k, i]) > 1e-3))
			print('      bot', ' '.join(f'{D.FEATURES[i]}={B[k, i]:.2f}' for i in range(len(D.FEATURES)) if abs(A[k, i] - B[k, i]) > 1e-3))
	for i, f in enumerate(D.FEATURES):
		d = np.abs(A[:, i] - B[:, i])
		print(f'  {f:14s} mean py {A[:, i].mean():8.3f} bot {B[:, i].mean():8.3f}  |diff| {d.mean():.4f}  exact {np.mean(d < 1e-3):.2f}')


if __name__ == '__main__':
	main()
