#!/usr/bin/env python3
"""tools/draftmodel/statpower.py PROBE_OUTPUT [PROBE_OUTPUT2]

Per-champion power features from the engine's own numbers (the output of tools/probe/champion_stats_main.cpp: champion_designs
base stats and ability payloads), the same arithmetic the bot's draft uses (draft.cpp stat_power): basic damage per round with an
attack reset, spell damage per round (modifier x focus / 8 cooldown), area spells x targets, dash landing, shields, stuns,
plus the engine's passive constants (Ren's retaliation, Varg's splash). With two files it prints the ratio (e.g. 3.0.4 / 3.0.2)."""
import re, sys

NAMES = ['Ryth', 'Vesper', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HoR']


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


def feats(c, i, targets=1):
	reset = any(k == 'reset' for k, _ in c['ab'])
	spell = aoe = stun = shield = heal = 0.0
	for k, v in c['ab']:
		mod = v.get('mod', 0.0)
		if k in ('damage', 'cc'):
			spell += mod * c['fo']
		elif k == 'aoe':
			aoe += mod * c['fo'] * targets
		elif k == 'dash':
			aoe += mod * c['fo'] * targets
		elif k == 'shield':
			shield += mod * c['fo']
		elif k == 'heal':
			heal += mod * c['fo']
		if (k == 'cc') or (k in ('aoe', 'dash') and v.get('dur', 0) > 0) or (k == 'reset' and v.get('enhanced', 0) > 0):
			stun += 1
	basic = c['st'] * (1 + (1 / 8 if reset else 0))
	if i == 10:  # Varg: splash equal to strength on the others within radius 1
		basic *= 1 + (targets - 1)
	ret = 0.2 * c['fo'] * min(targets, 3) if i == 9 else 0.0  # Ren: retaliation per hit taken (camps hit the nearest body)
	dps = basic + (spell + aoe) / 8 + ret
	ehp = c['hp'] + shield
	return dict(dps=dps, ehp=ehp, L=dps * ehp / 1000, stun=stun, heal=heal / 8, ranged=c['rng'] > 1)


def main():
	a = [parse(p) for p in sys.argv[1:]]
	for t in (1, 3):
		print(f'targets {t}')
		for i, n in enumerate(NAMES):
			f = [feats(x[i], i, t) for x in a]
			row = f'  {n:9s} ' + '  '.join(f"dps {g['dps']:6.1f} ehp {g['ehp']:6.0f} L {g['L']:6.1f} stun {g['stun']:.0f}" for g in f)
			if len(f) == 2:
				row += f"   L ratio {f[1]['L'] / f[0]['L']:.3f}"
			print(row)


if __name__ == '__main__':
	main()
