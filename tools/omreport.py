#!/usr/bin/env python3
"""tools/omreport.py TRACES.jsonl [--model bots/god/src/om_model.h] [--lambda 0.8] [--on 0.6] [--off 0.4] [--min 3] [--start 100]

Replays the bot's opponent-model decision (OppModel::end_window with om_learned 1: smoothed features -> fitted logistic P(raider) ->
hysteresis + minimum duration + CUSUM bypass) over labelled traces, exactly as the leader would have decided, and reports:
- plan-level confusion matrix per window (true style: none / raider; decided plan: none / invader), rounds >= start;
- per true label: share of windows spent in the INVADER plan;
- for switching proxies (traces with 'switches'): rounds from each switch to the first window whose plan matches the new style.
The model weights are parsed from the C++ header, so the report checks the shipped numbers, not a refit.
"""
import json, math, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import omfit  # noqa: E402


def load_model(path):
	t = open(path).read()
	rows = re.findall(r'\{ ([^{}]*?) \},', t[t.index('OM_W'):])
	W = [[float(x.strip().rstrip('f')) for x in rows[0].split(',')]]
	b = [float(x.strip().rstrip('f')) for x in re.search(r'OM_B\[[^]]*\] = \{ ([^}]*) \}', t).group(1).split(',')]
	return W[0], b[0]


def contact(w):
	B = max(1, w.get('bodies', 6))
	return w['inv'] / B + (w['ad'] + w['ed']) / B


def decide(ws, W, b, lam, on, off, minw, start, k=0.15, h=0.6, alpha=0.2, warm=3):
	fema, arc, since, n = None, 0, 0, 0
	mu, cp, cn = 0.0, 0.0, 0.0
	out = []
	for w in ws:
		c = contact(w)
		fired = False
		if n >= warm:
			cp = max(0.0, cp + c - mu - k)
			cn = max(0.0, cn + mu - c - k)
			if cp > h or cn > h:
				fired, cp, cn, mu = True, 0.0, 0.0, c
		mu = c if n == 0 else mu + alpha * (c - mu)
		f = omfit.feat(w)
		fema = list(f) if fema is None else [(0.5 * e + 0.5 * x) if fired else (lam * e + (1 - lam) * x) for e, x in zip(fema, f)]
		z = b + sum(wi * fi for wi, fi in zip(W, fema))
		p = 1 / (1 + math.exp(-z))
		n += 1
		if w['round'] >= start:
			held = n - since >= minw
			nxt = arc
			if arc != 2 and p >= on and (held or fired or arc == 0):
				nxt = 2
			elif arc == 2 and p < off and (held or fired):
				nxt = 0
			if nxt != arc:
				arc, since = nxt, n
		out.append((w['round'], arc, p))
	return out


def main():
	a = sys.argv[1:]
	opt = lambda k, d: (a.pop(a.index(k) + 1), a.remove(k))[0] if k in a else d
	model = opt('--model', os.path.join(ROOT, 'bots/god/src/om_model.h'))
	lam, on, off = float(opt('--lambda', '0.8')), float(opt('--on', '0.6')), float(opt('--off', '0.4'))
	minw, start = int(opt('--min', '3')), int(opt('--start', '100'))
	W, b = load_model(model)
	raider = {'invader', 'deathball'}
	M = {(t, d): 0 for t in ('none', 'raider') for d in ('none', 'invader')}
	share = {}
	delays = []
	for path in a:
		games = omfit.games(path)
		meta = {}
		for l in open(path):
			r = json.loads(l)
			if r.get('game'):
				meta[(r['map'], r['side'], r['opp'], r['bot'])] = r
		for key, ws in games.items():
			dec = decide(ws, W, b, lam, on, off, minw, start)
			for w, (rnd, arc, p) in zip(ws, dec):
				if rnd < start:
					continue
				t = 'raider' if w['label'] in raider else 'none'
				M[(t, 'invader' if arc == 2 else 'none')] += 1
				s = share.setdefault(w['label'], [0, 0])
				s[0] += arc == 2
				s[1] += 1
			sw = meta.get(key, {}).get('switches') or []
			for rs, lab in sw:
				want = 2 if lab in raider else 0
				hit = next((rnd for rnd, arc, p in dec if rnd > rs and arc == want), None)
				delays.append((key[2], rs, lab, None if hit is None else hit - rs))
	print('plan confusion per window (rows true, columns plan):')
	print('            none   invader   share in INVADER plan')
	for t in ('none', 'raider'):
		n = M[(t, 'none')] + M[(t, 'invader')]
		print(f'{t:8s} {M[(t, "none")]:7d} {M[(t, "invader")]:9d}   {M[(t, "invader")] / max(1, n):.2f}')
	print('\nshare of windows in the INVADER plan by true style:')
	for lab, (x, n) in sorted(share.items()):
		print(f'  {lab:10s} {x / max(1, n):.2f}  ({n} windows)')
	if delays:
		print('\nrounds to detect a switch (to the matching plan); None = never in the game:')
		by = {}
		for opp, rs, lab, d in delays:
			by.setdefault((opp, rs, lab), []).append(d)
		for (opp, rs, lab), ds in sorted(by.items()):
			got = sorted(d for d in ds if d is not None)
			med = got[len(got) // 2] if got else None
			print(f'  {opp:7s} switch r{rs} -> {lab:9s} detected in {len(got)}/{len(ds)} games, median {med} rounds, all {got}')


if __name__ == '__main__':
	main()
