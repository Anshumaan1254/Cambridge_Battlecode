#!/usr/bin/env python3
"""Per-team and per-champion farming / fight summary of one or more analyze.py output dirs, with named teams.

usage: python3 -I tools/strategy_v2/teamsum.py [--skip MAP,...] OUT_DIR=GROUP:LABEL0:LABEL1[,GROUP:LABEL0:LABEL1...] ...

OUT_DIR is an analyze.py output dir (run_all.py writes OUT/out/). Each GROUP is the 8-hex match-group prefix of the
replay names; LABEL0 / LABEL1 name team 0 (side A) and team 1 (side B) of that group ('*' as GROUP applies to every
match in the dir). Rates are per 100 alive body-rounds unless said otherwise, so short and long games weigh alike.
Example (session 9): the top-3 groups 23206e46 (3rd vs 1st), 7b2474db (2nd vs 1st), c47bab28 (3rd vs 1st).
"""
import collections
import csv
import json
import os
import sys


def load(out_dir, labels, skip):
	rows = {}
	for f in ('team', 'body', 'deaths', 'recalls', 'banks', 'captures'):
		p = os.path.join(out_dir, f + '.csv')
		rows[f] = list(csv.DictReader(open(p))) if os.path.exists(p) else []

	def lab(match, team):
		g = match[:8]
		if any(s in match for s in skip):
			return None
		key = g if g in labels else ('*' if '*' in labels else None)
		return labels[key][int(team)] if key else None
	return rows, lab


def main():
	args = sys.argv[1:]
	skip = []
	if args and args[0] == '--skip':
		skip = args[1].split(','); args = args[2:]
	if not args:
		sys.exit(__doc__)
	T = collections.defaultdict(lambda: collections.defaultdict(float))
	C = collections.defaultdict(lambda: collections.defaultdict(float))
	for a in args:
		d, spec = a.split('=', 1)
		labels = {}
		for s in spec.split(','):
			g, l0, l1 = s.split(':')
			labels[g] = (l0, l1)
		rows, lab = load(d, labels, skip)
		rounds = {}
		for r in rows['team']:
			L = lab(r['match'], r['team'])
			if not L:
				continue
			rounds[r['match']] = int(r['rounds'])
			t = T[L]
			t['games'] += 1; t['wins'] += int(r['won']); t['rounds'] += int(r['rounds'])
			for k in ('banked', 'camp_gems', 'captures', 'gold', 'deaths', 'kills', 'casts', 'recalls', 'banks', 'dmg_camp', 'dmg_champ'):
				t[k] += float(r[k])
			act = json.loads(r['act'])
			for k, v in act.items():
				t['act_' + k] += v
			terr = json.loads(r['terr'])
			for k, v in terr.items():
				t['terr_' + k] += v
		for r in rows['body']:
			L = lab(r['match'], r['team'])
			if not L:
				continue
			c = C[(L, r['champ'])]
			act = json.loads(r['act'])  # rounds per activity (team.csv holds shares)
			n = sum(act.values())
			alive = n - act.get('dead', 0)
			camp = act.get('camp', 0)
			c['games'] += 1; c['rounds'] += n; c['alive'] += alive; c['camp_rounds'] += camp
			for k in ('caps', 'cap_gems', 'gold_earned', 'deaths', 'casts', 'dmg_champ', 'dmg_camp', 'taken_champ', 'taken_camp'):
				c[k] += float(r[k])
			for k, v in act.items():
				c['act_' + k] += v
			fe = int(r['first_emblem']) if r['first_emblem'] not in ('', 'None') else 999
			c['first_emblem_sum'] += min(fe, 999)
		for r in rows['recalls']:
			L = lab(r['match'], r['team'])
			if L:
				T[L]['recall_hp_sum'] += float(r['hp_frac']); T[L]['recall_n'] += 1
				T[L]['recall_cap'] += r['cap_overlap'] == 'True'
		for r in rows['banks']:
			L = lab(r['match'], r['team'])
			if L:
				T[L]['bank_n'] += 1; T[L]['bank_gems'] += float(r['gems'])
				T[L]['bank_' + r['side']] += 1
		for r in rows['captures']:
			L = lab(r['match'], r['team'])
			if L:
				T[L]['cap_' + r['side']] += 1
		for r in rows['deaths']:
			L = lab(r['match'], r['team'])
			if L:
				T[L]['death_' + r['side']] += 1
				T[L]['death_burst'] += float(r['hp_prev_frac'] or 0) > 0.6
	print('## Teams (per game; act = share of body-rounds)\n')
	print('| Team | Games | Wins | Rounds | Banked | Camp gems | Gold | Deaths | Kills | Captures home/neutral/enemy | Recalls (hp) | Banks (gems) | Camp dmg per round | dead | walk | camp | capture | fight |')
	print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
	for L, t in sorted(T.items()):
		g = t['games']
		print(f"| {L} | {g:.0f} | {t['wins']:.0f} | {t['rounds']/g:.0f} | {t['banked']/g:.0f} | {t['camp_gems']/g:.0f} | {t['gold']/g:.0f} | {t['deaths']/g:.1f} | {t['kills']/g:.1f} "
			  f"| {t['cap_own']/g:.1f} / {t['cap_neutral']/g:.1f} / {t['cap_enemy']/g:.1f} | {t['recalls']/g:.0f} ({t['recall_hp_sum']/max(1,t['recall_n']):.2f}) "
			  f"| {t['bank_n']/g:.1f} ({t['bank_gems']/max(1,t['bank_n']):.0f}) | {t['dmg_camp']/max(1,t['rounds']):.0f} "
			  f"| {t['act_dead']/g:.2f} | {t['act_walk']/g:.2f} | {t['act_camp']/g:.2f} | {t['act_capture']/g:.2f} | {t['act_fight']/g:.2f} |")
	print('\n## Champions (per 100 alive rounds unless noted)\n')
	print('| Team | Champ | Games | Captures | Cap gems | Gold | Deaths /game | Casts | Camp dmg | Camp dmg per camp round | Camp dmg taken | Walk % | Camp % | First emblem (mean) |')
	print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
	for (L, ch), c in sorted(C.items()):
		a = max(1.0, c['alive']) / 100
		print(f"| {L} | {ch} | {c['games']:.0f} | {c['caps']/a:.2f} | {c['cap_gems']/a:.1f} | {c['gold_earned']/a:.0f} | {c['deaths']/c['games']:.1f} | {c['casts']/a:.1f} "
			  f"| {c['dmg_camp']/a:.0f} | {c['dmg_camp']/max(1,c['camp_rounds']):.0f} | {c['taken_camp']/a:.0f} | {100*c['act_walk']/max(1,c['rounds']):.0f} "
			  f"| {100*c['act_camp']/max(1,c['rounds']):.0f} | {c['first_emblem_sum']/c['games']:.0f} |")


if __name__ == '__main__':
	main()
