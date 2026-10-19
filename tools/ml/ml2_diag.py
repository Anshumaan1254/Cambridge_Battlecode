#!/usr/bin/env python3
"""Where the bot's fight estimate is wrong against real opponents (agent ml2, session 13).

usage: python3 -I tools/ml/ml2_diag.py DATA.npz [--skip contest]

Uses the held-out predictions ml2_train.py saved (DATA_p_die8.npy: logistic, boosted, label, us, game).
Tables: (1) our bodies by the bot's own estimate (log_adv bands) x the model's P(death within 8): rows, real death rate;
(2) high-risk states (model P >= 0.3): what the body did next round (hit a champion / moved away) and how often it died,
ours vs theirs; (3) per champion type, the share of our deaths the model flagged >= 0.3 / 0.2 one to eight rounds before.
"""
import json
import math
import sys

import numpy as np


def main():
	a = sys.argv[1:]
	skip = []
	if '--skip' in a:
		i = a.index('--skip'); skip = a[i + 1].split(','); del a[i:i + 2]
	path = a[0]
	d = np.load(path)
	X, Y, M = d['X'], d['Y'], d['M']
	F, L = list(d['features']), list(d['labels'])
	G = json.loads(str(d['games']))
	keep = np.array([G[g]['map'] not in skip and not G[g].get('dup') for g in M[:, 0]])
	X, Y, M = X[keep], Y[keep], M[keep]
	cens = Y[:, L.index('censored')] > 0
	X, Y, M = X[~cens], Y[~cens], M[~cens]
	P = np.load(path.replace('.npz', '_p_die8.npy'))
	assert P.shape[1] == len(X), (P.shape, X.shape)
	p_lr, p_gb, y, us = P[0], P[1], P[2], P[3] > 0
	la = X[:, F.index('log_adv')]
	inr = X[:, F.index('in_reach')] > 0
	hit = Y[:, L.index('act_hit1')] > 0
	away = Y[:, L.index('act_away1')] > 0
	kill = Y[:, L.index('kill8')] > 0
	print('(1) our bodies: bot estimate band x model P(die8) [rows / real death rate / kill8 rate]')
	bands = [(-9, math.log(0.5)), (math.log(0.5), math.log(0.873)), (math.log(0.873), math.log(1.3)), (math.log(1.3), 9)]
	names = ['adv<0.5', '0.5-0.87', '0.87-1.3', '>=1.3 (bot: fight)']
	pb = [(0, .1), (.1, .2), (.2, .3), (.3, .5), (.5, 1.01)]
	print('  %-20s' % '' + ''.join('%-24s' % f'P {lo:.1f}-{hi:.1f}' for lo, hi in pb))
	for (lo, hi), nm in zip(bands, names):
		row = '  %-20s' % nm
		for plo, phi in pb:
			s = us & (la >= lo) & (la < hi) & (p_lr >= plo) & (p_lr < phi)
			row += '%-24s' % (f'{s.sum():6d} {y[s].mean() if s.sum() else 0:.2f} {kill[s].mean() if s.sum() else 0:.2f}')
		print(row)
	print('  in reach only:')
	for (lo, hi), nm in zip(bands, names):
		row = '  %-20s' % nm
		for plo, phi in pb:
			s = us & inr & (la >= lo) & (la < hi) & (p_lr >= plo) & (p_lr < phi)
			row += '%-24s' % (f'{s.sum():6d} {y[s].mean() if s.sum() else 0:.2f} {kill[s].mean() if s.sum() else 0:.2f}')
		print(row)
	print('(2) high-risk states (logistic P >= 0.3): action next round -> death rate within 8')
	for side, sel in (('us', us), ('them', ~us)):
		hr = sel & (p_lr >= 0.3)
		for act, msk in (('hit a champion', hit), ('moved away', away), ('neither', ~hit & ~away)):
			s = hr & msk
			print(f'  {side:4s} {act:15s} rows {s.sum():6d} ({s.sum() / max(1, hr.sum()):.0%}) died {y[s].mean() if s.sum() else 0:.3f} kill8 {kill[s].mean() if s.sum() else 0:.3f} pred {p_lr[s].mean() if s.sum() else 0:.3f}')
	print('  same, P 0.15-0.3:')
	for side, sel in (('us', us), ('them', ~us)):
		hr = sel & (p_lr >= 0.15) & (p_lr < 0.3)
		for act, msk in (('hit a champion', hit), ('moved away', away), ('neither', ~hit & ~away)):
			s = hr & msk
			print(f'  {side:4s} {act:15s} rows {s.sum():6d} ({s.sum() / max(1, hr.sum()):.0%}) died {y[s].mean() if s.sum() else 0:.3f} kill8 {kill[s].mean() if s.sum() else 0:.3f} pred {p_lr[s].mean() if s.sum() else 0:.3f}')
	# (3) deaths flagged in advance: for each of our deaths (die4 rows in the last round before it), the max model P over the
	# preceding 8 rounds of that body
	print('(3) our deaths: max P over the 8 rounds before (body in contact)')
	gid, body, rnd = M[:, 0], M[:, 1], M[:, 2]
	die4 = Y[:, L.index('die4')] > 0
	key = {}
	for i in np.where(us & (Y[:, L.index('die8')] > 0))[0]:
		k = (gid[i], body[i])
		key.setdefault(k, []).append(i)
	# group rows into death events: consecutive rows of a body whose die8 window shares a death
	events = []
	for k, idx in key.items():
		idx = sorted(idx, key=lambda i: rnd[i])
		cur = [idx[0]]
		for i in idx[1:]:
			if rnd[i] - rnd[cur[-1]] > 8:
				events.append(cur)
				cur = [i]
			else:
				cur.append(i)
		events.append(cur)
	types = ['Ryth', 'VesperVale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi']
	tcol = {t: F.index('is_' + t) for t in ('Ren', 'Stellar', 'Cassi', 'Issac', 'Varg', 'Ryth') if 'is_' + t in F}
	n = len(events)
	f3 = sum(1 for e in events if max(p_lr[i] for i in e) >= 0.3)
	f2 = sum(1 for e in events if max(p_lr[i] for i in e) >= 0.2)
	hpf = F.index('hp_frac')
	early = sum(1 for e in events if X[e[0], hpf] >= 0.6)
	early_flag = sum(1 for e in events if X[e[0], hpf] >= 0.6 and max(p_lr[i] for i in e) >= 0.3)
	print(f'  death events {n}: flagged >= 0.3 {f3} ({f3 / max(1, n):.0%}), >= 0.2 {f2} ({f2 / max(1, n):.0%}); started >= 60% health {early}, of which flagged >= 0.3 {early_flag}')
	# first-flag lead time
	leads = []
	for e in events:
		fl = [rnd[i] for i in e if p_lr[i] >= 0.3]
		if fl:
			leads.append(max(rnd[i] for i in e) - min(fl))
	if leads:
		print(f'  rounds between the first flag (>= 0.3) and the last contact row before the death: median {np.median(leads):.0f}, mean {np.mean(leads):.1f}')
	# false alarms: share of our contact rows flagged >= 0.3 / 0.2 that did not die
	for t in (0.2, 0.3, 0.4, 0.5):
		s = us & (p_lr >= t)
		print(f'  threshold {t}: our rows flagged {s.sum()} ({s.sum() / max(1, us.sum()):.1%} of contact rows), died {y[s].mean():.2f}, kill8 {kill[s].mean():.2f}; deaths covered {y[s].sum() / max(1, y[us].sum()):.0%}')


if __name__ == '__main__':
	main()
