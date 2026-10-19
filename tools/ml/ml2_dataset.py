#!/usr/bin/env python3
"""Contact dataset for the fight / danger model (agent ml2, session 13).

usage: python3 -I tools/ml/ml2_dataset.py DEC_DIR OUT.npz [--sets a,b,...]

DEC_DIR holds one folder per replay set (tools/ml/ml2_decode.py output: <set>/<stem>.json + <set>/mapgeo.json).
One row per body-round in contact: the body is alive and an enemy champion (alive) stands within 7 (true positions).
Features use only what that body could see (an enemy in a bush is hidden unless we stand in a bush within 2 of it),
computed like the bot does (bots/_ch2/src/brain.cpp combat(): str, focus, burst of ready spells, reach).
Labels: die4 / die8 (this body dies within 4 / 8 rounds), kill8 (an enemy champion within 6 dies within 8 rounds),
net3 (champion damage this body deals minus takes over the next 3 rounds), taken3 (taken), act_hit1 (it hits a champion
next round), act_away1 (its distance to the nearest enemy grows next round).
Side of our bot ('us' = 1 on its bodies): ladder_oct19b from experiments/ladder_oct19b/index.json, ladder_oct18 and
sneaky_oct18 team 0; the other sets are other teams only (us = 0 everywhere).
"""
import collections
import hashlib
import json
import math
import os
import sys
from collections import deque

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'strategy_v2'))
from analyze import stats_of  # noqa: E402

CH = ['Ryth', 'VesperVale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin']
RANGED = {'Cassi', 'Stellar', 'Prism', 'Tavi', 'Willow', 'VesperVale'}
# slot -> (kind, modifier); kinds: dmg, cc (stun, damage = mod x focus), aoe (radius 1, mod x focus; Ryth's stuns), reset, dash, heal, shield
KIT = {
	'Ryth': {0: ('aoe', 1.0), 1: ('reset', 0)}, 'VesperVale': {0: ('reset', 0), 1: ('dash', 0)},
	'Vendetta': {0: ('reset', 0), 1: ('dash', 0)}, 'Cassi': {0: ('dmg', 2.0), 1: ('cc', 0.0)},
	'Issac': {0: ('reset', 0), 1: ('dash', 0)}, 'Stellar': {0: ('dmg', 2.0), 1: ('aoe', 1.4)},
	'Prism': {0: ('cc', 1.5), 1: ('aoe', 1.0)}, 'Marcella': {0: ('reset', 0), 1: ('dmg', 2.0)},
	'Willow': {0: ('heal', 3.0), 1: ('reset', 0)}, 'Ren': {0: ('cc', 1.25), 1: ('dash', 0)},
	'Varg': {0: ('reset', 0), 1: ('shield', 2.5)}, 'Tavi': {0: ('reset', 0), 1: ('cc', 2.2)},
}
STUNS = {'Ryth', 'Cassi', 'Prism', 'Ren', 'Tavi'}  # a ready stun spell (Ryth's area stuns)
AREA = {'Ryth', 'Stellar', 'Prism'}
TYPES_1H = ['Ren', 'Stellar', 'Cassi', 'Issac', 'Varg', 'Ryth']
COOLDOWN = 8

FEATURES = [
	# self
	'hp_frac', 'hp', 'max_hp', 'str', 'focus', 'dps_self', 'burst_self', 'ranged', 'pair', 'gems', 'spell_ready', 'dash_ready',
	'dhome', 'on_spawn', 'enemy_half', 'neutral', 'round', 'in_bush', 'bush4',
	'is_Ren', 'is_Stellar', 'is_Cassi', 'is_Issac', 'is_Varg', 'is_Ryth',
	# visible enemies
	'n_e3', 'n_e5', 'n_e7', 'hp_e5', 'hp_e7', 'dps_e5', 'dps_e7', 'burst_e5', 'stun_e5', 'area_e5', 'd_min', 'e_near_hpf',
	'e_min_hp5', 'killable', 'melee_e3', 'varg_e2', 'ren_e4', 'e_alive', 'e_spawn_near',
	# allies
	'n_a3', 'n_a5', 'n_a7', 'hp_a5', 'hp_a7', 'dps_a6', 'a_alive', 'a_low5',
	# camps
	'camp_awake3',
	# the bot's estimate (approximate reproduction of combat())
	'log_adv', 'in_reach', 'incoming', 'can_escape', 'isolated',
]
LABELS = ['die4', 'die8', 'kill8', 'net3', 'taken3', 'dealt3', 'act_hit1', 'act_away1', 'censored']


VISION_R2 = 10 ** 6  # champion vision radius 8 (champion_designs[*].base_stats().vision_radius, x_coord_NOTES.md)


def sees(p, q, p_in_bush, bush=None):
	"""Champion at p sees one at q: within vision radius 8, and q not in a bush unless we stand in a bush within 2."""
	dx, dy = p[0] - q[0], p[1] - q[1]
	if dx * dx + dy * dy > VISION_R2:
		return False
	if q in _BUSH[0] and not (p_in_bush and max(abs(dx), abs(dy)) <= 2):
		return False
	return True


_BUSH = [set()]


def cheb(a, b):
	return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def bfs(grid, w, h, sources):
	INF = 10 ** 6
	dist = [[INF] * w for _ in range(h)]
	dq = deque()
	for (x, y) in sources:
		dist[y][x] = 0
		dq.append((x, y))
	while dq:
		x, y = dq.popleft()
		for dx in (-1, 0, 1):
			for dy in (-1, 0, 1):
				nx, ny = x + dx, y + dy
				if (dx or dy) and 0 <= nx < w and 0 <= ny < h and dist[ny][nx] == INF and grid[ny][nx] not in '#oA':
					dist[ny][nx] = dist[y][x] + 1
					dq.append((nx, ny))
	return dist


def our_team(setname, stem, index):
	if setname == 'ladder_oct19b':
		r0 = index[stem[:11]]
		return 0 if r0['side'] == 'A' else 1
	if setname in ('ladder_oct18', 'sneaky_oct18'):
		return 0
	return -1


def game_rows(path, geo, us_team, setname, gid):
	d = json.load(open(path))
	w, h, grid = geo['w'], geo['h'], geo['grid']
	bodies = {b['index']: b for b in d['meta']['bodies']}
	team = {i: b['team'] for i, b in bodies.items()}
	btype = {i: b['type'] for i, b in bodies.items()}
	spawn = {0: [], 1: []}
	bush = set()
	for y in range(h):
		row = grid[y]
		for x in range(w):
			c = row[x]
			if c == 'S':
				spawn[0].append((x, y))
			elif c == 's':
				spawn[1].append((x, y))
			elif c == '"':
				bush.add((x, y))
	spawn_set = {t: set(v) for t, v in spawn.items()}
	_BUSH[0] = bush
	dist = {t: bfs(grid, w, h, spawn[t]) for t in (0, 1)}
	rounds = d['rounds']
	R = {rr['r']: rr for rr in rounds}
	last_r = rounds[-1]['r']
	# deaths per body
	deaths = collections.defaultdict(list)
	prev = None
	for rr in rounds:
		if prev is not None:
			pa = {c[0]: c[7] for c in prev['ch']}
			for c in rr['ch']:
				if pa.get(c[0]) and not c[7]:
					deaths[c[0]].append(rr['r'])
		prev = rr
	# casts per (body, slot)
	casts = collections.defaultdict(list)
	for e in d['events']:
		if e['k'] == 'Cast ability' and e.get('who') is not None:
			casts[(e['who'], e['slot'])].append(e['r'])
	# damage per round
	dealt = collections.defaultdict(float)  # (r, body) champion damage dealt
	taken = collections.defaultdict(float)
	camp_hp_max = {c['index']: c['hp'] for c in d['meta']['camps']}
	camp_pos = {c['index']: (c['x'], c['y']) for c in d['meta']['camps']}
	for row in d['dmg']:
		if row[5] == 'c' and row[7] < 0:
			if row[2] == 'c' and team.get(row[3]) is not None and team[row[3]] != team.get(row[6]):
				dealt[(row[0], row[3])] += -row[7]
			if row[2] == 'c' and team.get(row[3]) != team.get(row[6]):
				taken[(row[0], row[6])] += -row[7]

	def last_cast(b, slot, r):
		lst = casts.get((b, slot))
		if not lst:
			return -1000
		# latest cast at or before r (lists are in round order)
		lo, hi = 0, len(lst)
		while lo < hi:
			mid = (lo + hi) // 2
			if lst[mid] <= r:
				lo = mid + 1
			else:
				hi = mid
		return lst[lo - 1] if lo else -1000

	def ready(b, slot, r):
		return r + 1 - last_cast(b, slot, r) >= COOLDOWN

	X, Y, M = [], [], []
	stats_cache = {}
	for rr in rounds:
		r = rr['r']
		if r < 3:
			continue
		ch = {c[0]: c for c in rr['ch']}
		alive = {b: c for b, c in ch.items() if c[7] and c[3] >= 0}
		info = {}
		for b, c in alive.items():
			key = (b, json.dumps(c[11]))
			if key not in stats_cache:
				stats_cache[key] = stats_of(btype[b], c[11])
			mh, st, fo, passives, spent, pts = stats_cache[key]
			t = btype[b]
			kit = KIT.get(t, {})
			rd = {s: ready(b, s, r) for s in kit}
			burst = 0.0
			best = 0.0
			stun = False
			area = False
			spell = False
			dash = False
			for s, (k, m) in kit.items():
				if k in ('dmg', 'cc', 'aoe'):
					best = max(best, m)
					if rd[s]:
						spell = True
						burst = max(burst, fo * m)
						stun |= k == 'cc' or (k == 'aoe' and t == 'Ryth')
						area |= k == 'aoe'
				elif k == 'reset' and rd[s]:
					burst = max(burst, st)
				elif k == 'dash' and rd[s]:
					dash = True
			dps = st + fo * best / 8.0 + burst / 3.0
			# an ally's damage as the bot counts it in combat() (cooldowns of allies are not read): spells assumed up
			adps = st + fo * best / 8.0 + max(st, fo * best) / 3.0
			info[b] = dict(pos=(c[3], c[4]), hp=c[5], mh=c[6], st=st, fo=fo, burst=burst, dps=dps, adps=adps, stun=stun, area=area, spell=spell,
						   dash=dash, ranged=t in RANGED, gems=c[8], t=t)
		for b, me in info.items():
			tb = team[b]
			en = [o for o in info if team[o] != tb]
			if not en:
				continue
			p = me['pos']
			dtrue = min(cheb(p, info[o]['pos']) for o in en)
			if dtrue > 7:
				continue
			inb = p in bush
			vis = []
			hidden = 0
			for o in en:
				q = info[o]['pos']
				dd = cheb(p, q)
				if dd > 8:  # own vision: a Chebyshev square of radius 8 (probed in game, session 13)
					continue
				if not sees(p, q, inb):
					hidden += dd <= 7
					continue
				vis.append((o, dd))
			al = [(o, cheb(p, info[o]['pos'])) for o in info if o != b and team[o] == tb and sees(p, info[o]['pos'], inb)]
			f = {}
			f['hp_frac'] = me['hp'] / max(1, me['mh'])
			f['hp'] = me['hp'] / 1000
			f['max_hp'] = me['mh'] / 1000
			f['str'] = me['st'] / 100
			f['focus'] = me['fo'] / 100
			f['dps_self'] = me['dps'] / 100
			f['burst_self'] = me['burst'] / 100
			f['ranged'] = float(me['ranged'])
			f['pair'] = float(me['t'] in ('Cassi', 'Issac'))
			f['gems'] = me['gems'] / 100
			f['spell_ready'] = float(me['spell'])
			f['dash_ready'] = float(me['dash'])
			dh = dist[tb][p[1]][p[0]]
			da = dist[1 - tb][p[1]][p[0]]
			dh = min(dh, 200)
			da = min(da, 200)
			f['dhome'] = min(dh, 60) / 30
			f['on_spawn'] = float(p in spawn_set[tb])
			f['enemy_half'] = float(da < dh - 3)
			f['neutral'] = float(abs(da - dh) <= 3)
			f['round'] = r / 1000
			f['in_bush'] = float(inb)
			f['bush4'] = sum(1 for dx in range(-4, 5) for dy in range(-4, 5) if (p[0] + dx, p[1] + dy) in bush) / 20
			for t1 in TYPES_1H:
				f['is_' + t1] = float(me['t'] == t1)
			v3 = [o for o, dd in vis if dd <= 3]
			v5 = [o for o, dd in vis if dd <= 5]
			v7 = [o for o, dd in vis if dd <= 7]
			f['n_e3'] = len(v3)
			f['n_e5'] = len(v5)
			f['n_e7'] = len(v7)
			f['hp_e5'] = sum(info[o]['hp'] for o in v5) / 1000
			f['hp_e7'] = sum(info[o]['hp'] for o in v7) / 1000
			f['dps_e5'] = sum(info[o]['dps'] for o in v5) / 100
			f['dps_e7'] = sum(info[o]['dps'] for o in v7) / 100
			f['burst_e5'] = sum(info[o]['burst'] for o in v5 if info[o]['spell']) / 100
			f['stun_e5'] = sum(1 for o in v5 if info[o]['stun'])
			f['area_e5'] = sum(1 for o in v5 if info[o]['area'])
			dmin = min([dd for o, dd in vis], default=10)
			f['d_min'] = dmin / 10
			near = min(vis, key=lambda x: x[1])[0] if vis else None
			f['e_near_hpf'] = info[near]['hp'] / max(1, info[near]['mh']) if near is not None else 1.0
			f['e_min_hp5'] = min([info[o]['hp'] for o in v5], default=3000) / 1000
			# our burst this turn (basic attack + best ready spell), the target in reach of a spell (4) or attack
			my_reach = (3 if me['ranged'] else 2) + (2 if me['dash'] else 0)
			allies_burst = sum(info[o]['st'] for o, dd in al if dd <= 6)
			kill = 0.0
			for o, dd in vis:
				if dd <= max(my_reach, 4 if me['spell'] else 0) and info[o]['hp'] <= me['st'] + me['burst'] + allies_burst:
					kill = 1.0
			f['killable'] = kill
			f['melee_e3'] = sum(1 for o in v3 if not info[o]['ranged'] or info[o]['dash'])
			f['varg_e2'] = sum(1 for o, dd in vis if dd <= 2 and info[o]['t'] == 'Varg')
			f['ren_e4'] = sum(1 for o, dd in vis if dd <= 4 and info[o]['t'] == 'Ren')
			f['e_alive'] = sum(1 for o in en)
			f['e_spawn_near'] = float(any(info[o]['pos'] in spawn_set[1 - tb] for o in v7))
			a3 = [o for o, dd in al if dd <= 3]
			a5 = [o for o, dd in al if dd <= 5]
			a7 = [o for o, dd in al if dd <= 7]
			f['n_a3'] = len(a3)
			f['n_a5'] = len(a5)
			f['n_a7'] = len(a7)
			f['hp_a5'] = sum(info[o]['hp'] for o in a5) / 1000
			f['hp_a7'] = sum(info[o]['hp'] for o in a7) / 1000
			f['dps_a6'] = sum(info[o]['adps'] for o, dd in al if dd <= 6) / 100
			f['a_alive'] = 1 + len(al)
			f['a_low5'] = sum(1 for o in a5 if info[o]['hp'] < 0.3 * info[o]['mh'])
			ca = 0
			hp_now = rr['campHp']
			for ci, cp in camp_pos.items():
				if ci < len(hp_now) and 0 < hp_now[ci] < camp_hp_max[ci] and cheb(cp, p) <= 3:
					ca += 1
			f['camp_awake3'] = ca
			# the bot's estimate
			their_hp = their_dps = incoming = 0.0
			in_reach = False
			chaser = chaser_dash = False
			for o, dd in vis:
				e = info[o]
				if e['pos'] in spawn_set[1 - tb]:
					continue
				reach = (3 if e['ranged'] else 2) + (2 if e['dash'] else 0)
				if e['spell']:
					reach = max(reach, 4)
				dps = e['dps'] * (1.15 if e['stun'] else 1.0)
				their_hp += e['hp']
				their_dps += dps
				if dd <= reach:
					incoming += e['st'] + e['burst'] / 2
					in_reach = True
				if (not e['ranged'] or e['dash']) and dd <= 3 + (2 if e['dash'] else 0):
					chaser = True
					chaser_dash |= e['dash']
			our_hp = me['hp']
			our_dps = me['dps']
			nsup = 0
			for o, dd in al:
				a = info[o]
				if dd <= 6 and a['hp'] > 0.25 * a['mh'] and any(cheb(a['pos'], info[x]['pos']) <= 6 for x, _ in vis):
					our_hp += a['hp']
					our_dps += a['adps']
					nsup += 1
			if p in spawn_set[tb] and in_reach:
				our_hp += me['mh']
			if their_dps > 0 and their_hp > 0:
				adv = (our_hp / max(1, their_dps)) / max(0.1, their_hp / max(1, our_dps))
			else:
				adv = 10.0
			f['log_adv'] = math.log(max(0.01, min(100, adv)))
			f['in_reach'] = float(in_reach)
			f['incoming'] = incoming / 100
			t_die = me['hp'] / max(1, incoming)
			f['can_escape'] = float(p in spawn_set[tb] or not chaser or (me['dash'] and not chaser_dash) or dh + 1 < t_die)
			f['isolated'] = float(not any(dd <= 5 for o, dd in al))
			# labels
			db = deaths.get(b, [])
			die4 = any(r < t <= r + 4 for t in db)
			die8 = any(r < t <= r + 8 for t in db)
			kill8 = False
			for o, dd in vis + [(o, cheb(p, info[o]['pos'])) for o in en if all(o != x for x, _ in vis)]:
				if dd <= 6 and any(r < t <= r + 8 for t in deaths.get(o, [])):
					kill8 = True
			dl = sum(dealt.get((r + k, b), 0) for k in (1, 2, 3))
			tk = sum(taken.get((r + k, b), 0) for k in (1, 2, 3))
			hit1 = dealt.get((r + 1, b), 0) > 0
			nxt = R.get(r + 1)
			away = 0.0
			if nxt and near is not None:
				c1 = {c[0]: c for c in nxt['ch']}
				if c1.get(b) and c1[b][7] and c1.get(near) and c1[near][7]:
					away = float(cheb((c1[b][3], c1[b][4]), (c1[near][3], c1[near][4])) > dmin)
			X.append([f[k] for k in FEATURES])
			Y.append([float(die4), float(die8), float(kill8), (dl - tk) / 100, tk / 100, dl / 100, float(hit1), away, float(r + 8 > last_r)])
			M.append((gid, b, r, int(tb == us_team), hidden, tb))
	fp = hashlib.md5(json.dumps([d['meta']['drafts'], d['meta']['finalRound'], d['meta']['width'], d['rounds'][min(100, len(d['rounds']) - 1)]['ch']]).encode()).hexdigest()
	return X, Y, M, dict(d['meta'], fp=fp)


def main():
	a = sys.argv[1:]
	sets = None
	if '--sets' in a:
		i = a.index('--sets'); sets = a[i + 1].split(','); del a[i:i + 2]
	dec, out = a
	index = {r['group'] + '_' + r['nn']: r for r in json.load(open(os.path.join(ROOT, 'experiments', 'ladder_oct19b', 'index.json')))}
	X, Y, M, G = [], [], [], []
	for s in sorted(os.listdir(dec)):
		if sets and s not in sets:
			continue
		gp = os.path.join(dec, s, 'mapgeo.json')
		if not os.path.exists(gp):
			continue
		geo = json.load(open(gp))
		for stem in sorted(geo):
			path = os.path.join(dec, s, stem + '.json')
			if not os.path.exists(path):
				continue
			us = our_team(s, stem, index)
			gid = len(G)
			x, y, m, meta = game_rows(path, geo[stem], us, s, gid)
			mp = stem.split('_')[-1]
			G.append(dict(set=s, stem=stem, map=mp, us=us, drafts=meta['drafts'], outcome=meta.get('outcome'), final=meta.get('finalRound'), fp=meta['fp'],
						   dup=any(g['fp'] == meta['fp'] for g in G)))
			X += x; Y += y; M += m
			print(f'{s} {stem}: {len(x)} rows', flush=True)
	np.savez_compressed(out, X=np.array(X, dtype=np.float32), Y=np.array(Y, dtype=np.float32), M=np.array(M, dtype=np.int32),
						features=np.array(FEATURES), labels=np.array(LABELS), games=np.array(json.dumps(G)))
	print('rows', len(X), 'games', len(G))


if __name__ == '__main__':
	main()
