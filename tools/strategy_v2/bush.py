#!/usr/bin/env python3
"""Bush play from decoded replays: who stands in bushes, who strikes from them, who dies to them, and where wards go.

usage: python3 -I tools/strategy_v2/bush.py DMG_DIR MAP_DIR [--skip MAP,...] [--section occ,hits,deaths,wait,hidden,wards,all]

  DMG_DIR   decode_dmg.mjs output, one <map>.json per game (team 0 = us, team 1 = them)
  MAP_DIR   one <map>.txt per game, made with:  node tools/replay/mapinfo.mjs GAME.repl26a > MAP_DIR/<map>.txt
            (mapinfo marks bush tiles with a double quote; a wall, hole, altar, camp or spawn drawn on the same tile hides it)

Definitions (all from end-of-round snapshots and the action log; the tools do not know the champions' vision radius):
  - in bush: the body's end-of-round tile is a bush tile. Bushes hide a champion from everyone outside the bush, even while it
    attacks (docs/ENGINE_FACTS.md), and a ward only reveals a bush if the ward stands inside it.
  - hidden the round before: the attacker's end-of-previous-round tile is a bush tile (it was unseen when the victim decided).
  - stepped out: hidden the round before and its action tile this round is not a bush tile.
  - fight opener: tools/strategy_v2/micro.py's definition (first champion hit with no other hit within 8 tiles in the previous 10 rounds).
  - side: walking distance from the two spawns with a 3-tile neutral band (analyze.py's side_of), seen from the named team.
  - wait: the body stands still on one bush tile for 3+ rounds with no camp damage dealt and no recall, bank, shop or capture that round.
"""
import collections
import json
import os
import re
import sys
from collections import deque

BASIC = 4294967295


def cheb(a, b):
	return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def mirror(sym, w, h, x, y):
	if sym.startswith('H'):
		return w - 1 - x, y
	if sym.startswith('V'):
		return x, h - 1 - y
	return w - 1 - x, h - 1 - y


def bfs(grid, w, h, sources):
	INF = 10 ** 9
	dist = [[INF] * w for _ in range(h)]
	dq = deque()
	for (x, y) in sources:
		dist[y][x] = 0
		dq.append((x, y))
	while dq:
		x, y = dq.popleft()
		for dx in (-1, 0, 1):
			for dy in (-1, 0, 1):
				if not dx and not dy:
					continue
				nx, ny = x + dx, y + dy
				if 0 <= nx < w and 0 <= ny < h and dist[ny][nx] == INF and grid[ny][nx] not in '#oA':
					dist[ny][nx] = dist[y][x] + 1
					dq.append((nx, ny))
	return dist


class Game:
	def __init__(self, dmg_dir, map_dir, name):
		self.name = name
		self.d = json.load(open(os.path.join(dmg_dir, name + '.json')))
		lines = open(os.path.join(map_dir, name + '.txt')).read().splitlines()
		m = re.search(r'(\d+)x(\d+) sym (\S+).*spawnA (\d+),(\d+),(\d+),(\d+)', lines[0])
		w, h, sym, x0, y0, x1, y1 = m.groups()
		self.w, self.h, self.sym = int(w), int(h), sym
		self.grid = [list(l[4:].ljust(self.w, '.')) for l in lines[1:]]
		self.bush = set((x, y) for y in range(self.h) for x in range(self.w) if self.grid[y][x] == '"')
		self.passable = sum(1 for y in range(self.h) for x in range(self.w) if self.grid[y][x] not in '#oA')
		self.spawn = [set(), set()]
		for y in range(int(y0), int(y1)):
			for x in range(int(x0), int(x1)):
				self.spawn[0].add((x, y))
				self.spawn[1].add(mirror(sym, self.w, self.h, x, y))
		for t in (0, 1):
			for (x, y) in self.spawn[t]:
				if self.grid[y][x] in 'Ss':
					self.grid[y][x] = '.'
		self.dist = [bfs(self.grid, self.w, self.h, self.spawn[0]), bfs(self.grid, self.w, self.h, self.spawn[1])]
		self.meta = self.d['meta']
		self.bodies = {b['index']: b for b in self.meta['bodies']}
		self.btype = {i: b['type'] for i, b in self.bodies.items()}
		self.bteam = {i: b['team'] for i, b in self.bodies.items()}
		self.R = {rr['r']: rr for rr in self.d['rounds']}
		self.rounds = sorted(self.R)
		self.last = self.rounds[-1]
		self.st = {}
		for rr in self.d['rounds']:
			for c in rr['ch']:
				self.st[(rr['r'], c[0])] = c
		# Where each body stood at each attack ('a') or cast ('s'). An Attack event carries the attacker's tile in `from`; a Cast
		# event carries [0, 0] there unless it is a dash (then `from` is the tile before the dash), so a cast takes the tile
		# tracked through the round's Move / Attack / dash events, starting from the end-of-previous-round snapshot.
		self.act_pos = {}
		by_round = collections.defaultdict(list)
		for e in self.d['events']:
			by_round[e['r']].append(e)
		for r in sorted(by_round):
			pos = {}
			for c in (self.R[r - 1]['ch'] if (r - 1) in self.R else []):
				if c[7]:
					pos[c[0]] = (c[3], c[4])
			for e in by_round[r]:
				w_ = e.get('who')
				if w_ is None:
					continue
				if e['k'] == 'Move':
					pos[w_] = tuple(e['to'])
				elif e['k'] == 'Attack':
					pos[w_] = tuple(e['from'])
					self.act_pos[(r, w_, 'a')] = pos[w_]
				elif e['k'] == 'Cast ability':
					if tuple(e['from']) != (0, 0):
						pos[w_] = tuple(e['from'])
						self.act_pos[(r, w_, 's')] = pos[w_]
						pos[w_] = tuple(e['to']) if e.get('slot') is not None and e['to'] != e['from'] and cheb(e['from'], e['to']) <= 2 and self.btype.get(w_) in ('Ren', 'Issac', 'Vendetta', 'VesperVale') else pos[w_]
					elif w_ in pos:
						self.act_pos[(r, w_, 's')] = pos[w_]
				elif e['k'] == 'Respawn':
					pos.pop(w_, None)
		self.deaths = [e for e in self.d['events'] if e['k'] == 'Death' and 'who' in e]
		self.hits = []  # round, actor, target, amount, spell?, target tile (champion on champion, enemy teams)
		self.campdmg = collections.defaultdict(float)
		for x in self.d['dmg']:
			r, kind, ak, ai, slot, tk, ti, amt = x[:8]
			if ak == 'c' and tk == 'c' and amt < 0 and ai in self.bodies and ti in self.bodies and self.bteam[ai] != self.bteam[ti]:
				self.hits.append((r, ai, ti, -amt, slot != BASIC, (x[9], x[10])))
			if ak == 'c' and tk == 'm' and amt < 0 and ai in self.bodies:
				self.campdmg[(r, ai)] += -amt
		self.hits.sort()

	def side_of(self, team, pos):
		x, y = pos
		if not (0 <= x < self.w and 0 <= y < self.h):
			return 'own'
		do, de = self.dist[team][y][x], self.dist[1 - team][y][x]
		if do >= 10 ** 9 or de >= 10 ** 9:
			return 'neutral'
		if do < de - 3:
			return 'own'
		if de < do - 3:
			return 'enemy'
		return 'neutral'

	def apos(self, r, b, spell):
		return self.act_pos.get((r, b, 's' if spell else 'a'))

	def hidden_prev(self, r, b):
		c = self.st.get((r - 1, b))
		return bool(c and c[7] and (c[3], c[4]) in self.bush)


def pct(a, b):
	return f'{100 * a / b:.1f}%' if b else '-'


def sec_occ(games):
	print('## Share of alive body-rounds standing in a bush\n')
	print('| map | bush tiles | % of walkable | us | them | them / us |')
	print('|---|---|---|---|---|---|')
	tot = collections.defaultdict(lambda: [0, 0])
	grp = collections.defaultdict(lambda: [0, 0])
	side = collections.defaultdict(lambda: [0, 0])
	champ = collections.defaultdict(lambda: [0, 0])
	ctx = collections.defaultdict(lambda: [0, 0])
	hitr = {}
	for g in games:
		n = [0, 0]
		b = [0, 0]
		hr = collections.defaultdict(float)
		for (r, a, t, amt, sp, tp) in g.hits:
			hr[(r, a)] += amt
			hr[(r, t)] += amt
		for r in g.rounds:
			alive = [c for c in g.R[r]['ch'] if c[7]]
			for c in alive:
				t = c[1]
				pos = (c[3], c[4])
				inb = pos in g.bush
				n[t] += 1
				b[t] += inb
				tot[t][0] += 1
				tot[t][1] += inb
				s = side[(t, g.side_of(t, pos))]
				s[0] += 1
				s[1] += inb
				ch = champ[(t, g.btype[c[0]])]
				ch[0] += 1
				ch[1] += inb
				en = [e for e in alive if e[1] != t]
				if en:
					k = 'enemy within 6' if min(cheb(pos, (e[3], e[4])) for e in en) <= 6 else 'no enemy within 6'
					x = ctx[(t, k)]
					x[0] += 1
					x[1] += inb
				if hr.get((r, c[0]), 0) > 0:
					x = ctx[(t, 'hit or hitting a champion this round')]
					x[0] += 1
					x[1] += inb
		u, v = 100 * b[0] / max(1, n[0]), 100 * b[1] / max(1, n[1])
		print(f'| {g.name} | {len(g.bush)} | {100 * len(g.bush) / g.passable:.1f}% | {u:.1f}% | {v:.1f}% | {v / u if u else 0:.2f} |')
	for t in (0, 1):
		print(f"\nteam {t}: {tot[t][0]} alive body-rounds, {tot[t][1]} in a bush = {pct(tot[t][1], tot[t][0])}")
	print('\nBy side (seen from the body\'s own team):')
	for k, v in sorted(side.items()):
		print(f'  team {k[0]} {k[1]}: {v[0]} body-rounds, {pct(v[1], v[0])} in a bush')
	print('\nBy champion:')
	for k, v in sorted(champ.items()):
		print(f'  team {k[0]} {k[1]}: {v[0]} body-rounds, {pct(v[1], v[0])} in a bush')
	print('\nBy context:')
	for k, v in sorted(ctx.items()):
		print(f'  team {k[0]} {k[1]}: {v[0]} body-rounds, {pct(v[1], v[0])} in a bush')


def sec_hits(games):
	print('\n## Champion damage by where the attacker stood (at the action: spells never move, so a spell is cast from the end-of-previous-round tile)\n')
	for excl in (None, 'contest'):
		acc = collections.defaultdict(float)
		bych = collections.defaultdict(lambda: [0.0, 0.0])
		ret = collections.defaultdict(lambda: [0, 0.0])
		for g in games:
			if g.name == excl:
				continue
			ret_dmg = collections.defaultdict(float)  # (round, target) -> damage taken from the other team
			for (r, a, t, amt, sp, tp) in g.hits:
				ret_dmg[(r, t)] += amt
			done = set()
			for (r, a, t, amt, sp, tp) in g.hits:
				ta = g.bteam[a]
				ap = g.apos(r, a, sp)
				acc[(ta, 'dmg')] += amt
				acc[(ta, 'n')] += 1
				inb = ap in g.bush
				bych[(ta, g.btype[a])][0] += amt
				if inb:
					acc[(ta, 'dmg_in_bush')] += amt
					bych[(ta, g.btype[a])][1] += amt
				if g.hidden_prev(r, a):
					acc[(ta, 'dmg_hidden_prev')] += amt
				if (r, a) not in done:
					done.add((r, a))
					# damage the other team put on this attacker in the next 3 rounds (return fire)
					rf = sum(ret_dmg.get((rr, a), 0) for rr in range(r + 1, r + 4))
					x = ret[(ta, inb)]
					x[0] += 1
					x[1] += rf
		print(f"**{'all maps' if not excl else 'without ' + excl}**")
		for t in (0, 1):
			print(f"- team {t}: {int(acc[(t, 'n')])} hits, {int(acc[(t, 'dmg')])} damage; dealt by a body standing in a bush: {pct(acc[(t, 'dmg_in_bush')], acc[(t, 'dmg')])} ({int(acc[(t, 'dmg_in_bush')])});"
				  f" attacker was in a bush at the end of the previous round: {pct(acc[(t, 'dmg_hidden_prev')], acc[(t, 'dmg')])}")
		for t in (0, 1):
			print(f"- team {t} attackers, damage taken back from the other team in the 3 rounds after an attack turn: from a bush {ret[(t, True)][1] / max(1, ret[(t, True)][0]):.0f} ({ret[(t, True)][0]} attack turns),"
				  f" from the open {ret[(t, False)][1] / max(1, ret[(t, False)][0]):.0f} ({ret[(t, False)][0]} attack turns)")
		print('- share of each champion\'s damage dealt from a bush: ' + ', '.join(
			f"{'us' if k[0] == 0 else 'them'} {k[1]} {pct(v[1], v[0])} of {int(v[0])}" for k, v in sorted(bych.items()) if v[0] >= 2000))
	print('\n## Fight openers (micro.py definition) by bush status\n')
	rows = []
	for g in games:
		seen = set()
		for (r, a, t, amt, sp, tp) in g.hits:
			ta = g.bteam[a]
			if (r, a) in seen:
				continue
			if any(r - 10 <= h[0] < r and cheb(h[5], tp) <= 8 for h in g.hits):
				continue
			seen.add((r, a))
			ap = g.apos(r, a, sp)
			w3 = [h for h in g.hits if r <= h[0] < r + 3 and cheb(h[5], tp) <= 10]
			rows.append(dict(m=g.name, team=ta, champ=g.btype[a], at=bool(ap in g.bush), prev=g.hidden_prev(r, a),
							 side=g.side_of(ta, ap) if ap else '?', mine=sum(h[3] for h in w3 if g.bteam[h[1]] == ta),
							 theirs=sum(h[3] for h in w3 if g.bteam[h[1]] != ta)))
	for excl in (None, 'contest'):
		for t in (0, 1):
			xs = [x for x in rows if x['team'] == t and x['m'] != excl]
			if not xs:
				continue
			p = [x for x in xs if x['prev']]
			q = [x for x in xs if not x['prev']]
			av = lambda s, k: sum(x[k] for x in s) / max(1, len(s))
			print(f"team {t}{' (without ' + excl + ')' if excl else ''}: {len(xs)} openers; in a bush at the action {sum(x['at'] for x in xs)};"
				  f" hidden the round before {len(p)} ({pct(len(p), len(xs))}), damage in the next 3 rounds mine/theirs {av(p, 'mine'):.0f} / {av(p, 'theirs'):.0f}"
				  f" (others {av(q, 'mine'):.0f} / {av(q, 'theirs'):.0f}); side of all openers {dict(collections.Counter(x['side'] for x in xs))};"
				  f" side of the hidden ones {dict(collections.Counter(x['side'] for x in p))}")


def sec_deaths(games):
	print('\n## Death incidents (Cassi and Issac dying in the same round count once): the killer and the bush\n')
	inc = []
	for g in games:
		rows = []
		for e in g.deaths:
			v = e['who']
			vt = g.bteam[v]
			r = e['r']
			by = e.get('by')
			pos = tuple(e['at'])
			sp = g.st.get((r - 1, v))
			row = dict(m=g.name, r=r, team=vt, victim=g.btype[v], side=g.side_of(vt, pos), hpf=(sp[5] / sp[6]) if sp and sp[6] else 0,
					   camp=(by == 'camp' or by not in g.bodies), by=g.btype.get(by, by), hit=False, prev=False, any5=False)
			if not row['camp']:
				fh = [h for h in g.hits if h[0] == r and h[1] == by and h[2] == v]
				ap = g.apos(r, by, fh[0][4] if fh else False)
				row['hit'] = bool(ap in g.bush)
				row['prev'] = g.hidden_prev(r, by)
				for h in g.hits:
					if h[2] == v and r - 5 <= h[0] <= r and g.apos(h[0], h[1], h[4]) in g.bush:
						row['any5'] = True
			rows.append(row)
		used = set()
		for i, x in enumerate(rows):
			if i in used:
				continue
			grp = [x]
			if x['victim'] in ('Cassi', 'Issac'):
				for j, y in enumerate(rows):
					if j != i and j not in used and y['team'] == x['team'] and y['r'] == x['r'] and y['victim'] in ('Cassi', 'Issac') and y['victim'] != x['victim']:
						grp.append(y)
						used.add(j)
						break
			used.add(i)
			inc.append(dict(m=g.name, team=x['team'], side=x['side'], hpf=max(y['hpf'] for y in grp), camp=all(y['camp'] for y in grp),
							hit=any(y['hit'] for y in grp), prev=any(y['prev'] for y in grp), any5=any(y['any5'] for y in grp),
							killers=[y['by'] for y in grp]))
	for t in (0, 1):
		for excl in (None, 'contest'):
			xs = [d for d in inc if d['team'] == t and d['m'] != excl]
			ch = [d for d in xs if not d['camp']]
			print(f"**{'our' if t == 0 else 'their'} deaths, {'all maps' if not excl else 'without ' + excl}**: {len(xs)} incidents, {len(ch)} by a champion;"
				  f" killer standing in a bush at the final blow {sum(d['hit'] for d in ch)} ({pct(sum(d['hit'] for d in ch), len(ch))});"
				  f" killer in a bush at the end of the previous round {sum(d['prev'] for d in ch)}; a bush attacker among the hitters of the last 5 rounds {sum(d['any5'] for d in ch)} ({pct(sum(d['any5'] for d in ch), len(ch))})")
			for sd in ('own', 'neutral', 'enemy'):
				s_ = [d for d in ch if d['side'] == sd]
				print(f"  victim on its {sd} side: {len(s_)} by a champion, killer in a bush at the blow {sum(d['hit'] for d in s_)}, bush attacker in the last 5 rounds {sum(d['any5'] for d in s_)}")
			hi = [d for d in ch if d['hpf'] >= 0.75]
			print(f"  victim at 75%+ health the round before: {len(hi)}, killer in a bush at the blow {sum(d['hit'] for d in hi)}, bush attacker in the last 5 rounds {sum(d['any5'] for d in hi)}")
	print('\nPer map, our deaths (killer in a bush at the blow / bush attacker in the last 5 rounds / incidents by a champion):')
	by = collections.defaultdict(lambda: [0, 0, 0])
	for d in inc:
		if d['team'] == 0 and not d['camp']:
			by[d['m']][0] += d['hit']
			by[d['m']][1] += d['any5']
			by[d['m']][2] += 1
	print('  ' + ', '.join(f'{k} {v[0]}/{v[1]}/{v[2]}' for k, v in sorted(by.items())))
	json.dump(inc, open(os.path.join(os.environ.get('BUSH_OUT', '/tmp'), 'bush_incidents.json'), 'w'))


def sec_wait(games):
	print('\n## Waiting in a bush (3+ rounds on one bush tile, no camp damage, no recall / bank / shop / capture)\n')
	res = collections.defaultdict(list)
	for g in games:
		busy = set()
		for e in g.d['events']:
			if e['k'] in ('Recall', 'Submit gems', 'Gems submitted', 'Teleport channel', 'Teleport complete', 'Shop', 'Capture') and 'who' in e:
				busy.add((e['r'], e['who']))
		hit = collections.defaultdict(float)
		for (r, a, t, amt, sp, tp) in g.hits:
			hit[(r, a)] += amt
		for b in g.bodies:
			run = []
			prev = None

			def flush():
				if len(run) >= 3:
					res[(g.bteam[b], g.name)].append((len(run), any(hit.get((r, b), 0) > 0 for r in range(run[0], run[-1] + 4))))
			for r in g.rounds:
				c = g.st.get((r, b))
				if not c or not c[7]:
					flush()
					run = []
					prev = None
					continue
				pos = (c[3], c[4])
				ok = pos in g.bush and pos == prev and g.campdmg.get((r, b), 0) == 0 and (r, b) not in busy and pos not in g.spawn[0] and pos not in g.spawn[1]
				if ok:
					run.append(r)
				else:
					flush()
					run = []
				prev = pos
			flush()
	tot = {0: [0, 0, 0], 1: [0, 0, 0]}
	print('| map | us: waits / rounds | them: waits / rounds / longest / ended with a champion hit by that body within 3 rounds |')
	print('|---|---|---|')
	for g in games:
		a, b = res.get((0, g.name), []), res.get((1, g.name), [])
		for t, L in ((0, a), (1, b)):
			tot[t][0] += len(L)
			tot[t][1] += sum(x[0] for x in L)
			tot[t][2] += sum(1 for x in L if x[1])
		if a or b:
			print(f"| {g.name} | {len(a)} / {sum(x[0] for x in a)} | {len(b)} / {sum(x[0] for x in b)} / {max([x[0] for x in b] or [0])} / {sum(1 for x in b if x[1])} |")
	print(f"\nTotal: us {tot[0][0]} waits, {tot[0][1]} body-rounds, {tot[0][2]} ended with a hit; them {tot[1][0]} waits, {tot[1][1]} body-rounds, {tot[1][2]} ended with a hit")


def sec_hidden(games):
	print('\n## Bodies with a hidden enemy (in a bush) within 4 tiles\n')
	acc = collections.defaultdict(lambda: collections.defaultdict(float))
	for g in games:
		dealt = collections.defaultdict(float)
		taken = collections.defaultdict(float)
		for (r, a, t, amt, sp, tp) in g.hits:
			dealt[(r, a)] += amt
			taken[(r, t)] += amt
		dset = set((e['r'], e['who']) for e in g.deaths)
		for r in g.rounds:
			alive = [c for c in g.R[r]['ch'] if c[7]]
			for c in alive:
				t = c[1]
				pos = (c[3], c[4])
				if pos in g.spawn[0] or pos in g.spawn[1]:
					continue
				en = [e for e in alive if e[1] != t]
				hd = [e for e in en if (e[3], e[4]) in g.bush and cheb(pos, (e[3], e[4])) <= 4]
				vd = [e for e in en if (e[3], e[4]) not in g.bush and cheb(pos, (e[3], e[4])) <= 4]
				if hd and not vd:
					k = 'hidden only'
				elif hd:
					k = 'hidden + visible'
				elif vd:
					k = 'visible only'
				else:
					continue
				A = acc[(t, k)]
				A['n'] += 1
				A['taken'] += taken.get((r + 1, c[0]), 0)
				A['dealt'] += dealt.get((r + 1, c[0]), 0)
				A['died'] += any((r + kk, c[0]) in dset for kk in range(1, 5))
	print('| team | enemy within 4 | body-rounds | damage taken next round | damage dealt next round | deaths in 4 rounds per 100 |')
	print('|---|---|---|---|---|---|')
	for (t, k), A in sorted(acc.items()):
		n = A['n']
		print(f"| {'us' if t == 0 else 'them'} | {k} | {int(n)} | {A['taken'] / n:.0f} | {A['dealt'] / n:.0f} | {100 * A['died'] / n:.1f} |")


def sec_wards(games):
	print('\n## Wards: where they are placed\n')
	acc = collections.defaultdict(float)
	per = collections.defaultdict(lambda: [0, 0, 0, 0])
	for g in games:
		for e in g.d['events']:
			if e['k'] != 'Place ward':
				continue
			t = e['team']
			to = tuple(e['to'])
			sp = g.st.get((e['r'] - 1, e['who']))
			acc[(t, 'n')] += 1
			per[(g.name, t)][0] += 1
			if to in g.bush:
				acc[(t, 'on_bush')] += 1
				per[(g.name, t)][1] += 1
			if sp:
				bp = (sp[3], sp[4])
				avail = any((bp[0] + dx, bp[1] + dy) in g.bush for dx in range(-2, 3) for dy in range(-2, 3))
				if avail:
					acc[(t, 'bush_within_2')] += 1
					if to in g.bush:
						acc[(t, 'bush_chosen')] += 1
		for r in g.rounds:
			for c in g.R[r]['ch']:
				if c[7] and any((c[3] + dx, c[4] + dy) in g.bush for dx in range(-2, 3) for dy in range(-2, 3)):
					acc[(c[1], 'rounds_bush_within_2')] += 1
	for t in (0, 1):
		print(f"team {t}: {int(acc[(t, 'n')])} ward placements; on a bush tile {int(acc[(t, 'on_bush')])} ({pct(acc[(t, 'on_bush')], acc[(t, 'n')])});"
			  f" placements made with a bush tile within 2 of the body {int(acc[(t, 'bush_within_2')])}, of which on a bush tile {int(acc[(t, 'bush_chosen')])};"
			  f" alive body-rounds with a bush tile within 2: {int(acc[(t, 'rounds_bush_within_2')])}")
	print('\nPer map (placements us / them, on bush us / them): ' + ', '.join(
		f"{g.name} {per[(g.name, 0)][0]}/{per[(g.name, 1)][0]} ({per[(g.name, 0)][1]}/{per[(g.name, 1)][1]})" for g in games))


def sec_wardcover(games):
	print('\n## Attacks from a bush: is an enemy ward standing inside the same bush? (wards reconstructed from Place ward events: the latest one per body)\n')
	res = collections.defaultdict(lambda: [0, 0.0])
	for g in games:
		if not g.bush:
			continue
		comp = {}
		cid = 0
		for t in g.bush:
			if t in comp:
				continue
			stack = [t]
			comp[t] = cid
			while stack:
				x, y = stack.pop()
				for dx in (-1, 0, 1):
					for dy in (-1, 0, 1):
						n = (x + dx, y + dy)
						if n in g.bush and n not in comp:
							comp[n] = cid
							stack.append(n)
			cid += 1
		evs = sorted([e for e in g.d['events'] if e['k'] == 'Place ward'], key=lambda e: e['r'])
		wp = {}
		idx = 0
		wards = {}
		for r in g.rounds:
			while idx < len(evs) and evs[idx]['r'] <= r:
				wp[evs[idx]['who']] = (tuple(evs[idx]['to']), evs[idx]['team'])
				idx += 1
			wards[r] = list(wp.values())
		taken = collections.defaultdict(float)
		for (r, a, t, amt, sp, tp) in g.hits:
			taken[(r, t)] += amt
		done = set()
		for (r, a, t, amt, sp, tp) in g.hits:
			if (r, a) in done:
				continue
			done.add((r, a))
			ap = g.apos(r, a, sp)
			if ap not in g.bush:
				continue
			ta = g.bteam[a]
			cover = any(wt != ta and w in g.bush and comp[w] == comp[ap] for w, wt in wards.get(r - 1, []))
			x = res[(ta, cover)]
			x[0] += 1
			x[1] += sum(taken.get((rr, a), 0) for rr in range(r + 1, r + 4))
	for (t, cover), v in sorted(res.items()):
		print(f"- {'us' if t == 0 else 'them'} attacking from a bush, an enemy ward {'inside the same bush' if cover else 'not in that bush'}: {v[0]} attack turns, damage taken back in the next 3 rounds {v[1] / max(1, v[0]):.0f}")


def main():
	args = sys.argv[1:]
	if len(args) < 2:
		sys.exit(__doc__)
	dmg_dir, map_dir = args[0], args[1]
	skip = []
	secs = ['all']
	i = 2
	while i < len(args):
		if args[i] == '--skip':
			skip = args[i + 1].split(',')
			i += 2
		elif args[i] == '--section':
			secs = args[i + 1].split(',')
			i += 2
		else:
			i += 1
	names = sorted(f[:-5] for f in os.listdir(dmg_dir) if f.endswith('.json') and f[:-5] not in skip)
	games = [Game(dmg_dir, map_dir, n) for n in names]
	run = lambda s: 'all' in secs or s in secs
	if run('occ'):
		sec_occ(games)
	if run('hits'):
		sec_hits(games)
	if run('deaths'):
		sec_deaths(games)
	if run('wait'):
		sec_wait(games)
	if run('hidden'):
		sec_hidden(games)
	if run('wards'):
		sec_wards(games)
		sec_wardcover(games)


if __name__ == '__main__':
	main()
