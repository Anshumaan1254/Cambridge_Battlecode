"""Pick features from the engine's numbers (the probe output of tools/probe/champion_stats_main.cpp) and the map's draft-time
features (draft.cpp analyse(), LEGEND_FEATURES 'FEAT' lines). The same arithmetic as draft.cpp's pick_features() / map interactions."""
import re

PICK_TYPES = {'Ryth': [0], 'Vesper Vale': [1], 'Vendetta': [2], 'C&I': [3, 4], 'Stellar': [5], 'Prism': [6], 'Marcella': [7],
	'Willow': [8], 'Ren': [9], 'Varg': [10], 'Tavi': [11], 'Heart of Ruin': [12]}
BASE = ['hp', 'basic', 'splash', 'spell', 'area', 'stun', 'dash', 'ranged', 'gold', 'ret', 'bodies']
INTER = ['area_x_pack', 'stun_x_elk', 'gold_x_gold', 'bodies_x_small', 'dash_x_dist', 'ranged_x_mono']
FEATS = BASE + INTER


def parse(path):
	ch, cur = {}, None
	for line in open(path):
		m = re.match(r'CH (\d+) hp ([\d.]+) \+([\d.]+) str ([\d.]+) \+([\d.]+) foc ([\d.]+) \+([\d.]+) range (\d+)', line)
		if m:
			i = int(m.group(1))
			cur = ch[i] = dict(hp=float(m.group(2)), hpg=float(m.group(3)), st=float(m.group(4)), stg=float(m.group(5)), fo=float(m.group(6)),
				fog=float(m.group(7)), rng=int(m.group(8)), ab=[])
			continue
		m = re.match(r'\s+AB slot (\d) (\w+)(.*)', line)
		if m and cur is not None:
			kv = dict(re.findall(r'(\w+) (-?[\d.]+)', m.group(3)))
			cur['ab'].append((m.group(2), {k: float(v) for k, v in kv.items()}))
	return ch


def body(c, t):
	reset = any(k == 'reset' for k, _ in c['ab'])
	spell = area = stun = shield = heal = 0.0
	dash = 0
	for k, v in c['ab']:
		mod = v.get('mod', 0.0)
		if k in ('damage', 'cc'):
			spell += mod * c['fo']
		if k == 'aoe':
			area += mod * c['fo']
		if k == 'dash':
			dash = 1
			area += mod * c['fo']
		if k == 'heal':
			heal += mod * c['fo']
		if k == 'shield':
			shield += mod * c['fo']
		if k == 'cc' or (k in ('aoe', 'dash') and v.get('dur', 0) > 0) or (k == 'reset' and v.get('enhanced', 0) > 0):
			stun += 1
	basic = c['st'] * (1 + (0.125 if reset else 0.0))
	splash = basic if t == 10 else 0.0  # Varg: strength again on each other target within radius 1
	ret = 0.2 * c['fo'] if t == 9 else 0.0  # Ren: retaliation per hit taken
	return dict(hp=(c['hp'] + shield) / 1000, basic=basic / 50, splash=splash / 50, spell=(spell + heal) / 8 / 50, area=area / 8 / 50,
		stun=stun, dash=float(dash), ranged=1.0 if c['rng'] > 1 else 0.0, gold=0.33 if t == 1 else 0.0, ret=ret / 50, bodies=1.0)


def pick(ch, name, mf=None):
	f = {k: 0.0 for k in FEATS}
	for t in PICK_TYPES[name]:
		for k, v in body(ch[t], t).items():
			f[k] += v
	if mf is not None:
		g = max(1.0, mf['groups'])
		f['area_x_pack'] = (f['area'] + f['splash']) * mf['multi'] / g
		f['stun_x_elk'] = f['stun'] * mf['elk'] / g
		f['gold_x_gold'] = f['gold'] * mf['gold'] / g
		f['bodies_x_small'] = f['bodies'] * (1.0 if mf['team'] <= 3 else 0.0)
		f['dash_x_dist'] = f['dash'] * mf['mean_dist'] / 30
		f['ranged_x_mono'] = f['ranged'] * (1.0 if mf['mono'] > 0 else 0.0)
	return f


def team(ch, names, mf=None):
	f = {k: 0.0 for k in FEATS}
	for n in names:
		for k, v in pick(ch, n, mf).items():
			f[k] += v
	return f
