#!/usr/bin/env python3
"""Item-value model for the legend bot: what each 30-gold shard is worth to each champion, and the build
order that maximises it.

usage: python3 tools/analysis/item_value.py BENCH_DIR... [--rounds 900] [--us A|auto]

Calibration (all per 1000 rounds, measured from the bench statistics JSONs of our bot):
  campDmg_c, champDmg_c, deaths_c, campDmgTaken_c, gold_c  per champion type
  gems_per_camp_dmg = team collected gems / team camp damage

Value rate of a champion with stats (S, F, H) and passives, in gems per 1000 rounds (log utility, so every
objective is valued by its relative change and has diminishing returns):

  V = A_farm ln(camp_dps) + A_kill ln(champ_dps) + A_surv ln(fight_ehp) + A_tank ln(camp_ehp)

  A_farm = e_farm * campDmg_c * gems_per_camp_dmg      faster kills -> more gems (e_farm of it, the rest is travel)
  A_kill = e_kill * champDmg_c / team champDmg * kills * gems_per_kill
  A_surv = e_death * deaths_c * cost_per_death_c         (Cassi and Issac die together: half the pair's cost each)
  A_tank = heal-trip rounds saved: campDmgTaken_c / (0.7 H) trips * trip_rounds * own gem rate

Every block of five shards costs 150 gold, so the greedy order picks the block with the largest gain in V;
Treasure (+20% gold) is valued by a rollout of the rest of the game with and without it.
"""
import argparse, collections, glob, json, math, os

# Engine designs (bots/_dump): base health, health growth, base strength, growth, base focus, growth
DESIGN = {
	'Ryth': (1200, 100, 50, 5, 100, 10), 'VesperVale': (900, 100, 45, 5, 100, 10), 'Vendetta': (800, 100, 70, 5, 100, 10),
	'Cassi': (700, 71, 30, 4, 70, 15), 'Issac': (900, 95, 40, 5, 100, 10), 'Stellar': (750, 75, 35, 4, 100, 10),
	'Prism': (700, 75, 35, 4, 80, 10), 'Marcella': (1200, 100, 45, 5, 50, 10), 'Willow': (700, 50, 45, 3, 105, 5),
	'Ren': (900, 100, 40, 5, 100, 10), 'Varg': (1000, 100, 50, 5, 100, 10), 'Tavi': (750, 75, 35, 5, 100, 10),
}
# Kit: attack reset, damage-spell modifier (single target, incl. damaging stuns), area modifier (radius 1), melee
KIT = {
	'Ryth': (1, 0.0, 1.0, 1), 'VesperVale': (1, 0.0, 0.0, 0), 'Vendetta': (1, 0.0, 0.0, 1), 'Cassi': (0, 2.0, 0.0, 0),
	'Issac': (1, 0.0, 0.0, 1), 'Stellar': (0, 2.0, 1.4, 0), 'Prism': (0, 1.5, 1.0, 0), 'Marcella': (1, 2.0, 0.0, 1),
	'Willow': (1, 0.0, 0.0, 0), 'Ren': (0, 1.25, 0.0, 1), 'Varg': (1, 0.0, 0.0, 1), 'Tavi': (1, 2.2, 0.0, 0),
}
# Reference camp groups (cluster factor, attacking camps, weight): single camps and packed trios
GROUPS = [(1.0, 1, 0.5), (2.2, 3, 0.5)]
FAMILIES = ['Monster', 'Durability', 'Treasure', 'Jungle', 'Power', 'Bruiser']
UNIQUE = {'Monster', 'Durability', 'Treasure', 'Jungle'}
STATS = ['str', 'foc', 'hp']


def calibrate(dirs, us_mode):
	per = collections.defaultdict(lambda: collections.defaultdict(float))
	team = collections.defaultdict(float)
	rounds_total = 0
	games = 0
	for d in dirs:
		for f in sorted(glob.glob(os.path.join(d, '*_[AB].json'))):
			s = json.load(open(f))
			us = 'teamA' if f.endswith('_A.json') else 'teamB'
			R = int(s['match']['roundsCompleted'])
			rounds_total += R
			games += 1
			for c in s['champions']:
				if c['team'] != us:
					continue
				m = c['metrics']
				p = per[c['name']]
				p['rounds'] += R
				p['campDmg'] += float(m['monsterDamageDone'])
				p['champDmg'] += float(m['championDamageDone'])
				p['deaths'] += int(m['deaths'])
				p['campTaken'] += float(m['monsterDamageTaken'])
				p['champTaken'] += float(m['championDamageTaken'])
				p['gold'] += int(m['earnedGold'])
				p['gems'] += int(m['collectedGems'])
				team['campDmg'] += float(m['monsterDamageDone'])
				team['champDmg'] += float(m['championDamageDone'])
				team['gems'] += int(m['collectedGems'])
				team['kills'] += int(m['kills'])
	cal = {}
	for name, p in per.items():
		k = 1000.0 / p['rounds']
		cal[name] = {key: p[key] * k for key in ('campDmg', 'champDmg', 'deaths', 'campTaken', 'champTaken', 'gold', 'gems')}
	g = {
		'gems_per_dmg': team['gems'] / max(1.0, team['campDmg']),
		'champDmg': team['champDmg'] * 1000.0 / rounds_total,
		'kills': team['kills'] * 1000.0 / rounds_total,
		'body_gems': team['gems'] * 1000.0 / rounds_total / max(1, len(per)),
		'games': games,
	}
	return cal, g


class Model:
	def __init__(self, name, cal, g, e_farm=0.5, e_kill=0.5, e_death=1.0, trip_rounds=20.0):
		self.name = name
		self.base = DESIGN[name]
		self.kit = KIT[name]
		c = cal[name]
		self.gold_rate = c['gold'] / 1000.0
		self.A_farm = e_farm * c['campDmg'] * g['gems_per_dmg']
		self.A_kill = e_kill * c['champDmg'] / max(1.0, g['champDmg']) * g['kills'] * 25.0
		bag = 6.0
		cost = 60.0 * g['body_gems'] / 1000.0 + bag + 5.0  # 60 rounds of farming, the bag, their 50 gold
		if name in ('Cassi', 'Issac'):
			cost = (2 * cost) / 2.0  # the pair dies together; each member's health guards half of it
		self.A_surv = e_death * c['deaths'] * cost
		# Deaths come from champions, but camp damage taken first leaves us weaker: survival is valued against the
		# measured mix of damage taken (Jungle reduces only the camp share, Durability both).
		self.f_camp = c['campTaken'] / max(1.0, c['campTaken'] + c['champTaken'])
		h_now = self.base[0] + 10 * self.base[1]
		self.A_tank = c['campTaken'] / (0.7 * h_now) * trip_rounds * (g['body_gems'] / 1000.0)
		if self.kit[3] == 0:
			self.A_tank *= 0.5  # ranged: behind a melee ally most of the time

	def stats(self, pts):
		H0, gh, S0, gs, F0, gf = self.base
		S = S0 + gs * pts['str']
		F = F0 + gf * pts['foc']
		H = H0 + gh * pts['hp']
		if self.name == 'Ryth':
			S += 0.01 * gh * pts['hp']
		return S, F, H

	def rate(self, pts, pas):
		S, F, H = self.stats(pts)
		reset, dmg, aoe, melee = self.kit
		base = S * (1 + 0.125 * reset)
		camp = 0.0
		for cl, att, w in GROUPS:
			d = base * (cl if self.name == 'Varg' else 1.0) + F * (dmg + aoe * cl) / 8.0
			if self.name == 'Ren':
				d += 0.2 * F * min(att, 3)
			camp += w * d
		if 'Monster' in pas:
			camp *= 1.1
		champ = base + F * (dmg + aoe) / 8.0 + (0.2 * F if self.name == 'Ren' else 0.0)
		dur = 0.9 if 'Durability' in pas else 1.0
		jun = 0.7 if 'Jungle' in pas else 1.0
		fight_h = H + (2.5 * F if self.name == 'Varg' else 0.0)  # Varg: one self-shield per fight
		camp_h = H * (1.0 + (2.5 * F / 8.0) / 60.0 if self.name == 'Varg' else 1.0)  # ... and a share of camp hits
		return (self.A_farm * math.log(max(1.0, camp)) + self.A_kill * math.log(max(1.0, champ)) +
			self.A_surv * math.log(fight_h / (dur * (1.0 - self.f_camp + self.f_camp * jun))) + self.A_tank * math.log(camp_h / (dur * jun)))

	@staticmethod
	def block_effect(fam, stat):
		"""Stat points (per shard, and the emblem's extra on completion) and passive of a block."""
		extra = {'str': 0, 'foc': 0, 'hp': 0}
		if fam == 'Power':
			extra[stat] += 1
		elif fam == 'Bruiser':
			for s in STATS:
				if s != stat:
					extra[s] += 1
		return extra, (fam if fam in UNIQUE else None)

	def candidates(self, pas):
		for fam in FAMILIES:
			if fam in UNIQUE and fam in pas:
				continue
			for st in STATS:
				yield fam, st

	def simulate(self, order, rounds, policy=None, state=None):
		"""Integrated value (gems per game) of buying `order` blocks (then `policy` greedily) as gold arrives."""
		if state:
			pts, pas, gold, t0 = dict(state[0]), set(state[1]), state[2], state[3]
		else:
			pts, pas, gold, t0 = {'str': 0, 'foc': 0, 'hp': 0}, set(), 0.0, 0
		total = 0.0
		seq = list(order)
		bought = []
		cur = None  # (fam, stat, shards bought)
		for t in range(t0, rounds):
			mult = 1.2 if 'Treasure' in pas else 1.0
			gold += self.gold_rate * mult
			while gold >= 30:
				if cur is None:
					if seq:
						fam, st = seq.pop(0)
					elif policy:
						fam, st = policy(self, pts, pas, t, rounds)
					else:
						break
					cur = [fam, st, 0]
				gold -= 30
				pts[cur[1]] += 1
				cur[2] += 1
				if cur[2] == 5:
					extra, pa = self.block_effect(cur[0], cur[1])
					for k, v in extra.items():
						pts[k] += v
					if pa:
						pas.add(pa)
					bought.append((cur[0], cur[1], t))
					cur = None
			total += self.rate(pts, pas) / 1000.0
		return total, bought, pts, pas


def greedy_policy(m, pts, pas, t, rounds):
	"""Largest immediate gain in V; Treasure by rollout of the rest of the game."""
	best, best_v = None, -1e9
	now = m.rate(pts, pas)
	for fam, st in m.candidates(pas):
		p2 = dict(pts)
		p2[st] += 5
		extra, pa = m.block_effect(fam, st)
		for k, v in extra.items():
			p2[k] += v
		pas2 = set(pas) | ({pa} if pa else set())
		v = m.rate(p2, pas2) - now
		if fam == 'Treasure':
			# Extra gold over the rest of the game buys more points: value it as that many more shards of the
			# current best block at its gain per shard, for the remaining time each lasts on average.
			left = max(0, rounds - t)
			extra_gold = 0.2 * m.gold_rate * left
			v_noT = 0.0
			for f2, s2 in m.candidates(pas):
				if f2 == 'Treasure':
					continue
				p3 = dict(pts)
				p3[s2] += 5
				e3, a3 = m.block_effect(f2, s2)
				for k, vv in e3.items():
					p3[k] += vv
				v_noT = max(v_noT, m.rate(p3, set(pas) | ({a3} if a3 else set())) - now)
			v += v_noT / 150.0 * extra_gold * 0.5  # gold arrives evenly: half the remaining time on average
			v -= 0  # Treasure's own five points are already in v
		if v > best_v:
			best, best_v = (fam, st), v
	return best


def rollout_policy(m, pts, pas, t, rounds):
	"""Exact one-step lookahead: each candidate block, then the immediate-gain greedy to the end of the game."""
	best, best_v = None, -1e9
	for cand in m.candidates(pas):
		v, _, _, _ = m.simulate([cand], rounds, greedy_policy, state=(pts, pas, 0.0, t))
		if v > best_v:
			best, best_v = cand, v
	return best


def fmt(bought):
	return ' > '.join(f"{f}-{s}@{t}" for f, s, t in bought)


R2_BUILDS = {
	'Issac': [('Monster', 'str'), ('Jungle', 'hp'), ('Treasure', 'str'), ('Durability', 'hp')] + [('Power', 'str')] * 10,
	'Varg': [('Monster', 'str'), ('Jungle', 'hp'), ('Treasure', 'str'), ('Durability', 'hp')] + [('Power', 'str')] * 10,
	'Ren': [('Jungle', 'hp'), ('Power', 'foc'), ('Durability', 'hp'), ('Treasure', 'foc')] + [('Power', 'foc')] * 10,
	'Ryth': [('Jungle', 'hp'), ('Monster', 'str'), ('Durability', 'hp')] + [('Power', 'str'), ('Power', 'str'), ('Power', 'hp')] * 4,
	'Stellar': [('Monster', 'foc'), ('Durability', 'hp'), ('Treasure', 'foc')] + [('Power', 'foc')] * 10,
	'Cassi': [('Monster', 'foc'), ('Durability', 'hp'), ('Treasure', 'foc')] + [('Power', 'foc')] * 10,
}
# The strongest ladder team (8694af79 replays, same draft as ours)
TOP_BUILDS = {
	'Ren': [('Bruiser', 'hp'), ('Durability', 'hp')] + [('Power', 'foc')] * 10,
	'Ryth': [('Bruiser', 'hp'), ('Durability', 'hp')] + [('Power', 'str')] * 10,
	'Stellar': [('Power', 'foc'), ('Durability', 'hp')] + [('Power', 'foc')] * 10,
	'Cassi': [('Durability', 'foc'), ('Bruiser', 'hp')] + [('Power', 'foc')] * 10,
	'Issac': [('Power', 'str'), ('Durability', 'hp')] + [('Power', 'str')] * 10,
	'Varg': [('Power', 'str'), ('Durability', 'hp')] + [('Power', 'str')] * 10,
}


# Prototype builds (bots/_x_econ build_style 2): rich farmers take Treasure first, the poor Cassi & Issac pair
# survival first, and Bruiser (5 + 1 + 1 points) replaces Power (6 points of one stat) everywhere.
# Final prototype (rich_treasure_first = 0): Ren and Stellar keep r2's first emblem, Treasure second.
X_BUILDS = {
	'Ren': [('Jungle', 'hp'), ('Treasure', 'foc'), ('Monster', 'foc'), ('Bruiser', 'foc'), ('Bruiser', 'foc'), ('Durability', 'hp')] + [('Bruiser', 'foc'), ('Bruiser', 'foc'), ('Bruiser', 'hp')] * 6,
	'Stellar': [('Monster', 'foc'), ('Treasure', 'foc'), ('Bruiser', 'foc'), ('Durability', 'hp')] + [('Bruiser', 'foc'), ('Bruiser', 'foc'), ('Bruiser', 'hp')] * 6,
	'Cassi': [('Durability', 'hp'), ('Jungle', 'hp'), ('Bruiser', 'hp'), ('Monster', 'foc')] + [('Bruiser', 'foc'), ('Bruiser', 'hp')] * 8,
	'Issac': [('Durability', 'hp'), ('Jungle', 'hp'), ('Bruiser', 'str'), ('Monster', 'str')] + [('Bruiser', 'str'), ('Bruiser', 'hp')] * 8,
	'Ryth': [('Jungle', 'hp'), ('Monster', 'str'), ('Durability', 'hp')] + [('Bruiser', 'str'), ('Bruiser', 'hp')] * 8,
	'Varg': [('Monster', 'str'), ('Treasure', 'str'), ('Jungle', 'str'), ('Durability', 'hp')] + [('Bruiser', 'str'), ('Bruiser', 'str'), ('Bruiser', 'hp')] * 6,
}
# First prototype (rich_treasure_first = 1): Treasure opens for Ren and Stellar
A_BUILDS = dict(X_BUILDS)
A_BUILDS['Ren'] = [('Treasure', 'foc'), ('Monster', 'foc'), ('Bruiser', 'foc'), ('Jungle', 'hp'), ('Bruiser', 'foc'), ('Durability', 'hp')] + [('Bruiser', 'foc'), ('Bruiser', 'foc'), ('Bruiser', 'hp')] * 6
A_BUILDS['Stellar'] = [('Treasure', 'foc'), ('Monster', 'foc'), ('Bruiser', 'foc'), ('Durability', 'hp')] + [('Bruiser', 'foc'), ('Bruiser', 'foc'), ('Bruiser', 'hp')] * 6
# Only Power -> Bruiser on top of the r2 builds (ablation)
B_BUILDS = {k: [('Bruiser' if f == 'Power' else f, s) for f, s in v] for k, v in R2_BUILDS.items()}


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('dirs', nargs='+')
	ap.add_argument('--rounds', type=int, default=900)
	ap.add_argument('--e_farm', type=float, default=0.5)
	ap.add_argument('--e_kill', type=float, default=0.5)
	ap.add_argument('--e_death', type=float, default=1.0)
	ap.add_argument('--rollout', action='store_true', help='exact one-step lookahead instead of the Treasure heuristic')
	ap.add_argument('--only', default='')
	args = ap.parse_args()
	cal, g = calibrate(args.dirs, 'auto')
	print(f"calibration: {g['games']} games, gems/camp dmg {g['gems_per_dmg']:.4f}, team champ dmg {g['champDmg']:.0f}/1000r, "
		f"kills {g['kills']:.1f}/1000r, gems per body {g['body_gems']:.0f}/1000r")
	for name in ('Ren', 'Stellar', 'Cassi', 'Issac', 'Ryth', 'Varg'):
		if name not in cal or (args.only and name not in args.only.split(',')):
			continue
		m = Model(name, cal, g, args.e_farm, args.e_kill, args.e_death)
		print(f"\n== {name}: camp share of damage taken {m.f_camp:.2f}, gold {m.gold_rate:.2f}/round  A_farm {m.A_farm:.0f} A_kill {m.A_kill:.0f} A_surv {m.A_surv:.0f} A_tank {m.A_tank:.0f} (gems/1000r per unit log)")
		# marginal value of one more point of each stat at 0, 10 and 25 points spent evenly in the r2 way
		p0 = {'str': 0, 'foc': 0, 'hp': 0}
		for st in STATS:
			p1 = dict(p0); p1[st] += 1
			print(f"   first point of {st:3s}: +{m.rate(p1, set()) - m.rate(p0, set()):.2f} gems/1000r")
		for label, fam in (('Monster', 'Monster'), ('Durability', 'Durability'), ('Jungle', 'Jungle')):
			print(f"   passive {label:10s} at 0 points: +{m.rate(p0, {fam}) - m.rate(p0, set()):.2f} gems/1000r")
		vg, bg, ptsg, _ = m.simulate([], args.rounds, rollout_policy if args.rollout else greedy_policy)
		v2, b2, pts2, _ = m.simulate(R2_BUILDS.get(name, []), args.rounds)
		vt, bt, ptst, _ = m.simulate(TOP_BUILDS.get(name, []), args.rounds)
		v0, _, _, _ = m.simulate([], args.rounds)
		vx, bx, _, _ = m.simulate(X_BUILDS.get(name, []), args.rounds)
		vb, _, _, _ = m.simulate(B_BUILDS.get(name, []), args.rounds)
		va, _, _, _ = m.simulate(A_BUILDS.get(name, []), args.rounds)
		print(f"   value over {args.rounds} rounds (gems, vs no items): greedy {vg - v0:.1f}  r2 {v2 - v0:.1f}  top-team {vt - v0:.1f}  "
			f"x_econ {vx - v0:.1f}  x_econ-treasure-first {va - v0:.1f}  r2+bruiser {vb - v0:.1f}")
		print(f"   greedy: {fmt(bg)}")
		print(f"   r2:     {fmt(b2)}")
		print(f"   x_econ: {fmt(bx)}")


if __name__ == '__main__':
	main()
