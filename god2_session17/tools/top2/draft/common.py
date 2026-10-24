"""Shared loaders for the draft / composition study (tools/top2/draft/*): ranked match lists, ratings, engine champion stats,
map features (terrain shares, team size, spawn walk distance, camp mix from fight-dump meta.camps).
  import common as C; C.matches('wr') / C.matches('all'); C.ratings(); C.mapfeat(); C.engine()"""
import glob, gzip, json, math, os, re, collections

ROOT = 'C:/battlecode/Cambridge_Battlecode'
NAMES = ['Ryth', 'Vesper', 'Vendetta', 'C&I', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HoR']
AB = ['Ry', 'Ve', 'Vd', 'CI', 'St', 'Pr', 'Ma', 'Wi', 'Re', 'Va', 'Ta', 'Ho']
STUDY = {'pbg': '38e6d8c4', 'ifish': '1890540d', 'pantheon': '547efb5b', 'coo': '1570a113', 'cm': 'ad5474c2', 'nyx': '6f7fd199'}
STUDY_NAME = {'pbg': 'prism best girl', 'ifish': 'Intercontinental Fish', 'pantheon': 'Pantheon', 'coo': 'conqueror_of_openai',
	'cm': 'Claudus Maximus', 'nyx': 'Nyx'}
US = '5a103c90'  # HouseOfCoders
# draft id -> engine champion type(s) (experiments/results/probe_v3_0_4/champions_engine_3_0_4.txt CH index)
ENGINE_TYPES = {0: [0], 1: [1], 2: [2], 3: [3, 4], 4: [5], 5: [6], 6: [7], 7: [8], 8: [9], 9: [10], 10: [11], 11: [12]}
CAMP_GEMS = {'wolf': 4, 'elk': 15, 'gem': 7, 'gold': 0, 'monolith': 200, 'golem': 36}
CAMP_GOLD = {'wolf': 40, 'elk': 90, 'gem': 0, 'gold': 20, 'monolith': 300, 'golem': 160}
CAMP_RESP = {'wolf': 40, 'elk': 60, 'gem': 50, 'gold': 50, 'monolith': 150, 'golem': 80}
CAMP_HP = {'wolf': 1350, 'elk': 2400, 'gem': 120, 'gold': 120, 'monolith': 20000, 'golem': 5000}


def mkey(m):
	return m.replace('-', '_')


def _rows(pattern):
	for f in glob.glob(os.path.join(ROOT, pattern), recursive=True):
		for line in open(f, encoding='utf-8'):
			line = line.strip()
			if not line:
				continue
			try:
				m = json.loads(line)
			except Exception:
				continue
			if isinstance(m, dict) and 'matchId' in m and 'teams' in m:
				yield m


def matches(which='wr', since='2026-10-22T07:00', ranked=True):
	"""Deduplicated finished matches with both drafts. which='wr' (top-50 lists, Oct 23) or 'all' (every list file)."""
	pats = ['experiments/live/lists/wr/*.jsonl'] if which == 'wr' else ['experiments/live/lists/**/*.jsonl']
	seen = {}
	for p in pats:
		for m in _rows(p):
			if m.get('status') != 'finished':
				continue
			if ranked and m.get('kind') != 'ranked':
				continue
			if m['createdAt'] < since:
				continue
			ta = next((t for t in m['teams'] if t.get('side') == 'a'), None)
			tb = next((t for t in m['teams'] if t.get('side') == 'b'), None)
			if not ta or not tb or not ta.get('draftPicks') or not tb.get('draftPicks'):
				continue
			if ta.get('result') not in ('win', 'loss'):
				continue
			seen[m['matchId']] = m
	out = []
	for m in seen.values():
		ta = next(t for t in m['teams'] if t['side'] == 'a')
		tb = next(t for t in m['teams'] if t['side'] == 'b')
		out.append(dict(id=m['matchId'], t=m['createdAt'], map=mkey(m['map']), end=m.get('endReason'),
			a=ta['teamId'], b=tb['teamId'], an=ta['name'], bn=tb['name'], da=list(ta['draftPicks']), db=list(tb['draftPicks']),
			awin=1 if ta['result'] == 'win' else 0, group=m.get('groupId')))
	out.sort(key=lambda r: r['t'])
	return out


def ratings():
	d = json.load(open('C:/battlecode/cache/ladder_now.json', encoding='utf-8'))
	return {t['teamId']: dict(rating=t['rating'], rank=t['rank'], name=t['name']) for t in d['teams']}


def engine():
	ch = {}
	cur = None
	for line in open(os.path.join(ROOT, 'experiments/results/probe_v3_0_4/champions_engine_3_0_4.txt')):
		m = re.match(r'CH (\d+) hp ([\d.]+) \+([\d.]+) str ([\d.]+) \+([\d.]+) foc ([\d.]+) \+([\d.]+) range (\d+)', line)
		if m:
			i = int(m.group(1))
			cur = ch[i] = dict(hp=float(m.group(2)), hpg=float(m.group(3)), st=float(m.group(4)), stg=float(m.group(5)),
				fo=float(m.group(6)), fog=float(m.group(7)), rng=int(m.group(8)), ab=[])
			continue
		m = re.match(r'\s+AB slot (\d) (\w+)(.*)', line)
		if m and cur is not None:
			kv = dict(re.findall(r'(\w+) (-?[\d.]+)', m.group(3)))
			cur['ab'].append((m.group(2), {k: float(v) for k, v in kv.items()}))
	return ch


def _groups(camps):
	at = {(c['x'], c['y']): k for k, c in enumerate(camps)}
	par = list(range(len(camps)))

	def find(k):
		while par[k] != k:
			par[k] = par[par[k]]
			k = par[k]
		return k
	for k, c in enumerate(camps):
		for dx, dy in ((1, 0), (0, 1)):
			j = at.get((c['x'] + dx, c['y'] + dy))
			if j is not None:
				par[find(k)] = find(j)
	comp = collections.defaultdict(list)
	for k in range(len(camps)):
		comp[find(k)].append(camps[k])
	return list(comp.values())


def mapfeat():
	"""Per-map features: W, H, area, wall, bush, hole (map_terrain.json), size (team size from the lists), s2s (spawn-to-spawn walk,
	an_strategy mapgeo2), camp mix from one fight dump's meta.camps (counts, gem / gold value per cycle by type, group counts),
	midShare (gem rate in groups at 0.4 < dA/(dA+dB) < 0.6, mapgeo2)."""
	cache = os.path.join(ROOT, 'experiments/top2/draft_mapfeat.json')
	if os.path.exists(cache):
		return json.load(open(cache, encoding='utf-8'))
	terr = {mkey(k): v for k, v in json.load(open(os.path.join(ROOT, 'experiments/live/map_terrain.json'), encoding='utf-8')).items()}
	geo = {}
	for line in open('C:/battlecode/cache/an_strategy/mapgeo2.jsonl', encoding='utf-8'):
		g = json.loads(line)
		geo[mkey(g['map'])] = g
	size = collections.defaultdict(collections.Counter)
	for m in _rows('experiments/live/lists/wr/*.jsonl'):
		for t in m['teams']:
			if t.get('draftPicks'):
				size[mkey(m['map'])][len(t['draftPicks'])] += 1
	dumps = {}
	for f in glob.glob('C:/battlecode/cache/t2dump/*/*.json.gz'):
		b = os.path.basename(f)
		mp = re.sub(r'_[0-9a-f]{8}\.json\.gz$', '', b)
		dumps.setdefault(mkey(mp), f)
	out = {}
	for mp in sorted(size):
		t = terr.get(mp, {})
		g = geo.get(mp, {})
		F = dict(W=t.get('W'), H=t.get('H'), area=(t.get('W') or 0) * (t.get('H') or 0), wall=t.get('wall'), bush=t.get('bush'),
			hole=t.get('hole'), size=size[mp].most_common(1)[0][0])
		gf = g.get('feat', {})
		F['s2s'] = gf.get('s2s')
		F['midShare'] = gf.get('midShare')
		F['altars'] = gf.get('altars')
		F['mincut'] = gf.get('mincut')
		if mp in dumps:
			d = json.loads(gzip.open(dumps[mp]).read())
			camps = [dict(c, type=('golem' if c['type'] == 5 else c['type'])) for c in d['meta']['camps']]
			cnt = collections.Counter(c['type'] for c in camps)
			for ty in CAMP_GEMS:
				F['n_' + ty] = cnt.get(ty, 0)
			gems = sum(CAMP_GEMS[c['type']] for c in camps)
			gold = sum(CAMP_GOLD[c['type']] for c in camps)
			# value per round of respawn (a group respawns on the longest member cooldown; approximate with per-camp rates)
			F['gems'] = gems
			F['gold'] = gold
			F['gemrate'] = round(sum(CAMP_GEMS[c['type']] / CAMP_RESP[c['type']] for c in camps), 2)
			F['goldrate'] = round(sum(CAMP_GOLD[c['type']] / CAMP_RESP[c['type']] for c in camps), 2)
			heavy = sum(CAMP_GEMS[c['type']] for c in camps if c['type'] in ('elk', 'golem', 'monolith'))
			F['heavyGemShare'] = round(heavy / gems, 3) if gems else 0
			F['monoGemShare'] = round(sum(CAMP_GEMS[c['type']] for c in camps if c['type'] == 'monolith') / gems, 3) if gems else 0
			F['golemGemShare'] = round(sum(CAMP_GEMS[c['type']] for c in camps if c['type'] == 'golem') / gems, 3) if gems else 0
			F['campHP'] = sum(CAMP_HP[c['type']] for c in camps)
			grs = _groups(camps)
			F['groups'] = len(grs)
			F['mon_groups'] = sum(1 for gr in grs if any(c['type'] in ('wolf', 'elk', 'golem', 'monolith') for c in gr))
			F['free_groups'] = F['groups'] - F['mon_groups']
			# gems from groups that hold no monster (free clusters)
			F['freeGemShare'] = round(sum(CAMP_GEMS[c['type']] for gr in grs if not any(c['type'] in ('wolf', 'elk', 'golem', 'monolith') for c in gr) for c in gr) / gems, 3) if gems else 0
			F['spawnEuclid'] = None
		out[mp] = F
	sp = json.load(open(os.path.join(ROOT, 'experiments/live/spawns.json'), encoding='utf-8'))
	for mp, v in sp.items():
		k = mkey(mp)
		if k in out and len(v) >= 2:
			(x0, y0), (x1, y1) = v[0], v[1]
			out[k]['spawnEuclid'] = round(math.hypot(x0 - x1, y0 - y1), 1)
	json.dump(out, open(cache, 'w', encoding='utf-8'), indent=1)
	return out


def comp_str(d):
	return '/'.join(AB[x] for x in d)


def comp_set(d):
	return '/'.join(AB[x] for x in sorted(d))
