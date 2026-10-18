#!/usr/bin/env python3
"""Fight micro from decoded replays (decode_dmg.mjs JSON): how close each team lets enemies come, what it trades there,
how fights open, and from what range champions hit champions.

usage: python3 -I tools/strategy_v2/micro.py [--skip MAP,...] DMG_DIR=GROUP:LABEL0:LABEL1[,...] ...

Per team label:
  - band table: every alive body-round (end-of-round positions) whose nearest visible-or-not enemy champion is within 7,
    by Chebyshev distance to the nearest enemy: share of those rounds, champion damage dealt and taken in the NEXT round
    per body-round, deaths in the next 4 rounds per 100 body-rounds;
  - hit ranges: distance from attacker to target for champion-on-champion damage, basic attacks and spells apart;
  - openers: the first champion-on-champion hit of each fight (no such hit within 8 tiles in the previous 10 rounds):
    who opened (champion, attack or spell, distance), and the damage both teams dealt in the 3 rounds from the opener;
  - exposure without return: body-rounds within the enemy's next-turn reach (nearest enemy <= its attack range + 1,
    or <= 4 for an enemy with a range-4 spell) in which the body dealt no champion damage that round.
"""
import collections
import glob
import json
import os
import sys

RANGE = {'Ryth': 1, 'VesperVale': 3, 'Vendetta': 1, 'Cassi': 3, 'Issac': 1, 'Stellar': 3, 'Prism': 3, 'Marcella': 1,
		 'Willow': 3, 'Ren': 1, 'Varg': 1, 'Tavi': 3, 'HeartOfRuin': 1}
SPELL4 = {'Ryth', 'Cassi', 'Stellar', 'Prism', 'Marcella', 'Ren', 'Tavi', 'Willow'}
DASH = {'VesperVale', 'Vendetta', 'Issac', 'Ren'}
CHAMP = ['Ryth', 'VesperVale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin']
BASIC = 4294967295


class Acc(dict):
	# nested tables for the band/hit-range/opener keys, plain counters for the rest
	def __missing__(self, k):
		v = collections.defaultdict(float) if k.startswith(('band_', 'hitrange_', 'open_by')) else 0.0
		self[k] = v
		return v


def cheb(a, b):
	return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def reach(t):
	r = RANGE[t] + 1
	if t in SPELL4:
		r = max(r, 4)
	if t in DASH:
		r = max(r, RANGE[t] + 2)
	return r


def analyze(path, lab0, lab1, acc):
	d = json.load(open(path))
	labels = (lab0, lab1)
	bodies = {b['index']: b for b in d['meta']['bodies']}
	R = {rr['r']: rr for rr in d['rounds']}
	rounds = sorted(R)
	# champion damage per (round, actor) and per (round, target); deaths per (round, body)
	dealt = collections.defaultdict(float)
	taken = collections.defaultdict(float)
	hits = []  # (round, actor, target, amount, spell?, target pos)
	for x in d['dmg']:
		r, kind, ak, ai, slot, tk, ti, amt = x[:8]
		if ak == 'c' and tk == 'c' and amt < 0 and ai in bodies and ti in bodies and bodies[ai]['team'] != bodies[ti]['team']:
			dealt[(r, ai)] += -amt
			taken[(r, ti)] += -amt
			hits.append((r, ai, ti, -amt, slot != BASIC, (x[9], x[10])))
	deaths = set()
	for e in d['events']:
		if e['k'] == 'Death' and 'who' in e:
			deaths.add((e['r'], e['who']))
	# actor position at each action: track positions through the events in order
	pos = {}
	act_pos = {}
	for e in d['events']:
		w = e.get('who')
		if w is None:
			continue
		if e['k'] == 'Move':
			pos[w] = tuple(e['to'])
		elif e['k'] == 'Attack':
			pos[w] = tuple(e['from'])
			act_pos[(e['r'], w, 'a')] = pos[w]
		elif e['k'] == 'Cast ability':
			if w in pos:
				act_pos[(e['r'], w, 's')] = pos[w]
		elif e['k'] == 'Respawn':
			pos.pop(w, None)
	# hit ranges
	for (r, a, t, amt, sp, tp) in hits:
		ap = act_pos.get((r, a, 's' if sp else 'a'))
		if ap is None:
			continue
		L = labels[bodies[a]['team']]
		acc[L]['hitrange_' + ('spell' if sp else 'basic')][min(cheb(ap, tp), 6)] += amt
	# bands from end-of-round snapshots
	for r in rounds:
		rr = R[r]
		alive = [c for c in rr['ch'] if c[7]]
		for c in alive:
			b, team = c[0], c[1]
			L = labels[team]
			en = [e for e in alive if e[1] != team]
			if not en:
				continue
			nd, ne = min((cheb((c[3], c[4]), (e[3], e[4])), e) for e in en)
			if nd > 7:
				continue
			A = acc[L]
			band = min(nd, 7)
			A['band_n'][band] += 1
			A['band_dealt'][band] += dealt.get((r + 1, b), 0)
			A['band_taken'][band] += taken.get((r + 1, b), 0)
			A['band_died'][band] += any((r + k, b) in deaths for k in range(1, 5))
			et = bodies[ne[0]]['type']
			if nd <= reach(et):
				A['exposed'] += 1
				A['exposed_nohit'] += dealt.get((r + 1, b), 0) == 0
				A['exposed_taken'] += taken.get((r + 1, b), 0)
			# bodies of ours within 4 of the nearest enemy (local numbers)
			mine = sum(1 for o in alive if o[1] == team and cheb((o[3], o[4]), (ne[3], ne[4])) <= 4)
			theirs = sum(1 for o in en if cheb((o[3], o[4]), (ne[3], ne[4])) <= 4)
			A['local_' + ('more' if mine > theirs else 'equal' if mine == theirs else 'fewer')] += 1
	# openers
	last = {}
	for (r, a, t, amt, sp, tp) in sorted(hits):
		ta = bodies[a]['team']
		key = None
		recent = [h for h in hits if r - 10 <= h[0] < r and cheb(h[5], tp) <= 8]
		if recent:
			continue
		if (r, a) in last:
			continue
		last[(r, a)] = 1
		ap = act_pos.get((r, a, 's' if sp else 'a'))
		L = labels[ta]
		O = labels[1 - ta]
		w3 = [h for h in hits if r <= h[0] < r + 3 and cheb(h[5], tp) <= 10]
		mine = sum(h[3] for h in w3 if bodies[h[1]]['team'] == ta)
		theirs = sum(h[3] for h in w3 if bodies[h[1]]['team'] != ta)
		acc[L]['open_n'] += 1
		acc[L]['open_by'][(bodies[a]['type'], 'spell' if sp else 'basic', cheb(ap, tp) if ap else -1)] += 1
		acc[L]['open_dmg_mine'] += mine
		acc[L]['open_dmg_theirs'] += theirs
		acc[O]['opened_on'] += 1
		acc[O]['opened_on_dmg_mine'] += theirs
		acc[O]['opened_on_dmg_theirs'] += mine


def main():
	args = sys.argv[1:]
	skip = []
	if args and args[0] == '--skip':
		skip = args[1].split(','); args = args[2:]
	acc = collections.defaultdict(Acc)
	for a in args:
		dd, spec = a.split('=', 1)
		labels = {}
		for s in spec.split(','):
			g, l0, l1 = s.split(':')
			labels[g] = (l0, l1)
		for f in sorted(glob.glob(os.path.join(dd, '*.json'))):
			name = os.path.basename(f)
			if any(s in name for s in skip):
				continue
			g = name[:8]
			lab = labels.get(g) or labels.get('*')
			if lab:
				analyze(f, lab[0], lab[1], acc)
	print('## Distance to the nearest enemy champion (end of round), and what the next round brings\n')
	print('| Team | band | share of rounds near enemies | dealt next round | taken next round | deaths in 4 rounds per 100 |')
	print('|---|---|---|---|---|---|')
	for L, A in sorted(acc.items()):
		tot = sum(A['band_n'].values())
		if not tot:
			continue
		for bd in range(0, 8):
			n = A['band_n'][bd]
			if n:
				print(f"| {L} | {bd} | {100*n/tot:.1f}% | {A['band_dealt'][bd]/n:.0f} | {A['band_taken'][bd]/n:.0f} | {100*A['band_died'][bd]/n:.1f} |")
	print('\n## Exposure: body-rounds within the nearest enemy\'s next-turn reach\n')
	print('| Team | exposed rounds | of them no champion damage dealt next round | damage taken per exposed round | local numbers more/equal/fewer |')
	print('|---|---|---|---|---|')
	for L, A in sorted(acc.items()):
		e = max(1, A['exposed'])
		ln = A['local_more'] + A['local_equal'] + A['local_fewer']
		print(f"| {L} | {A['exposed']:.0f} | {100*A['exposed_nohit']/e:.0f}% | {A['exposed_taken']/e:.0f} | "
			  f"{100*A['local_more']/max(1,ln):.0f}% / {100*A['local_equal']/max(1,ln):.0f}% / {100*A['local_fewer']/max(1,ln):.0f}% |")
	print('\n## Champion damage by attacker-target distance (share of the team\'s champion damage)\n')
	print('| Team | kind | 1 | 2 | 3 | 4 | 5 | 6+ |')
	print('|---|---|---|---|---|---|---|---|')
	for L, A in sorted(acc.items()):
		for k in ('basic', 'spell'):
			h = A['hitrange_' + k]
			t = max(1, sum(h.values()))
			print(f"| {L} | {k} | " + ' | '.join(f"{100*h[i]/t:.0f}%" for i in range(1, 7)) + ' |')
	print('\n## Fight openers (first champion hit with no other within 8 tiles in the previous 10 rounds)\n')
	print('| Team | opened | dmg 3 rounds mine/theirs | opened on | dmg 3 rounds mine/theirs | top openers |')
	print('|---|---|---|---|---|---|')
	for L, A in sorted(acc.items()):
		top = sorted(A['open_by'].items(), key=lambda kv: -kv[1])[:5]
		print(f"| {L} | {A['open_n']:.0f} | {A['open_dmg_mine']/max(1,A['open_n']):.0f} / {A['open_dmg_theirs']/max(1,A['open_n']):.0f} | "
			  f"{A['opened_on']:.0f} | {A['opened_on_dmg_mine']/max(1,A['opened_on']):.0f} / {A['opened_on_dmg_theirs']/max(1,A['opened_on']):.0f} | "
			  + ', '.join(f"{c} {k} d{dd} x{n:.0f}" for (c, k, dd), n in top) + ' |')


if __name__ == '__main__':
	main()
