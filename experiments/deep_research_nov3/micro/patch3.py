"""Patch extract3.py (copy of top30_nov3/fights/extract2.py) with micro fields. Run once."""
import re
P = 'extract3.py'
s = open(P).read()

def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:80], s.count(old))
    s = s.replace(old, new)

# 1. map sets: bush, altars, camp tiles
rep("    camp_at = {(c['x'], c['y']): c['index'] for c in meta['camps']}\n",
    "    camp_at = {(c['x'], c['y']): c['index'] for c in meta['camps']}\n"
    "    rows_ = mp['rows']\n"
    "    bushset = {(x, y) for y in range(H) for x in range(W) if rows_[y][x] == '\"'}\n"
    "    altars = [(x, y) for y in range(H) for x in range(W) if rows_[y][x] == 'A']\n"
    "    camp_tiles = list(camp_at.keys())\n"
    "    casts = []\n"
    "    enh_open = {}\n")

# 2. candidate helper before the round loop
rep("    seq = 0\n    for r in range(1, final + 1):\n",
    "    def cand_info(who, apos, j, rng, r):\n"
    "        s0 = S.get(r - 1, {})\n"
    "        cs = [i for i, pi in pos.items() if pi is not None and team[i] != team[who] and apos is not None and cheb(pi, apos) <= rng]\n"
    "        if j not in cs:\n"
    "            cs.append(j)\n"
    "        def hpf(i):\n"
    "            c = s0.get(i)\n"
    "            return (c[5] / max(1, c[6])) if c and c[7] else 1.0\n"
    "        def gm(i):\n"
    "            c = s0.get(i)\n"
    "            return c[8] if c and c[7] else 0\n"
    "        hj = hpf(j)\n"
    "        return {'nc': len(cs), 'low': hj <= min(hpf(i) for i in cs) + 1e-9, 'thp': round(hj, 3), 'tg': gm(j),\n"
    "                'maxg': max(gm(i) for i in cs), 'mc': any(types[i] == 'Marcella' for i in cs),\n"
    "                'dist': cheb(apos, pos[j]) if apos and pos.get(j) else None,\n"
    "                'ahp': round(hpf(who), 3)}\n"
    "\n"
    "    def dnear(who):\n"
    "        p = pos.get(who)\n"
    "        if p is None:\n"
    "            return None\n"
    "        ds = [cheb(p, q) for i, q in pos.items() if q is not None and team[i] != team[who]]\n"
    "        return min(ds) if ds else None\n"
    "\n"
    "    seq = 0\n    for r in range(1, final + 1):\n")

# 3. dash cast rows (inside move handling)
rep("                if k == 'Cast ability':\n                    dash_cast[who].append((r, fr, to))\n",
    "                if k == 'Cast ability':\n                    dash_cast[who].append((r, fr, to))\n"
    "                    c0 = S.get(r - 1, {}).get(who)\n"
    "                    casts.append({'mid': mid, 't': team[who], 'body': who, 'champ': types[who], 'r': r, 'ab': 6,\n"
    "                                  'dn0': min((v[0] for v in rel.values()), default=None), 'dn1': min((v[1] for v in rel.values()), default=None),\n"
    "                                  'hp': (c0[5] / max(1, c0[6])) if c0 and c0[7] else None, 'gems': c0[8] if c0 else 0,\n"
    "                                  'nhit': sum(1 for j, pj in pos.items() if pj is not None and team[j] != team[who] and cheb(pj, to) <= 1) if types[who] == 'HeartOfRuin' else None})\n")

# 4. attack hits: candidate info + Marcella enhanced attack outcome
rep("                    hits.append({'r': r, 'seq': seq, 'a': who, 't': j, 'ap': pos.get(who) or tuple(e['from']), 'tp': P,\n"
    "                                 'kind': 'atk', 'w': STR[types[who]], 'stun': st})\n",
    "                    ap_ = pos.get(who) or tuple(e['from'])\n"
    "                    hits.append({'r': r, 'seq': seq, 'a': who, 't': j, 'ap': ap_, 'tp': P,\n"
    "                                 'kind': 'atk', 'w': STR[types[who]], 'stun': st, **cand_info(who, ap_, j, 3 if types[who] in RANGED else 1, r)})\n"
    "                    if enh.get(who):\n"
    "                        casts.append({'mid': mid, 't': team[who], 'body': who, 'champ': types[who], 'r': r, 'ab': 'enh_atk', 'champ_hit': 1, 'camp_hit': 0,\n"
    "                                      'tgt': types[j], 'thp': hits[-1]['thp'], 'dn': dnear(who)})\n")
rep("                elif P in camp_at:\n                    champ_camp[who].add(r)\n                    camp_hit_by[camp_at[P]].append((r, team[who]))\n                enh[who] = False\n",
    "                elif P in camp_at:\n                    champ_camp[who].add(r)\n                    camp_hit_by[camp_at[P]].append((r, team[who]))\n"
    "                    if enh.get(who):\n"
    "                        casts.append({'mid': mid, 't': team[who], 'body': who, 'champ': types[who], 'r': r, 'ab': 'enh_atk', 'champ_hit': 0, 'camp_hit': 1, 'dn': dnear(who)})\n"
    "                enh[who] = False\n")

# 5. spells: cast rows + candidate info
rep("                if ab == 1 and ct == 'Marcella':\n                    enh[who] = True\n",
    "                if ab in (1, 2, 3, 4, 5, 7):\n"
    "                    cp_ = pos.get(who)\n"
    "                    c0 = S.get(r - 1, {}).get(who)\n"
    "                    casts.append({'mid': mid, 't': team[who], 'body': who, 'champ': ct, 'r': r, 'ab': ab, 'dist': cheb(cp_, P) if cp_ else None,\n"
    "                                  'dn': dnear(who), 'champ_hit': sum(1 for j, pj in pos.items() if pj is not None and team[j] != team[who] and (pj == P if ab in (2, 4) else cheb(pj, P) <= 1)) if ab in (2, 3, 4) else None,\n"
    "                                  'camp_hit': int(any(cheb(P, q) <= (1 if ab == 3 else 0) for q in camp_at)) if ab in (2, 3, 4) else None,\n"
    "                                  'hp': (c0[5] / max(1, c0[6])) if c0 and c0[7] else None})\n"
    "                if ab == 1 and ct == 'Marcella':\n                    enh[who] = True\n")
rep("                        hits.append({'r': r, 'seq': seq, 'a': who, 't': j, 'ap': pos.get(who), 'tp': P, 'kind': 'spell',\n"
    "                                     'w': SPELL.get((ct, ab), 1.0) * FOC[ct], 'stun': st})\n",
    "                        hits.append({'r': r, 'seq': seq, 'a': who, 't': j, 'ap': pos.get(who), 'tp': P, 'kind': 'spell',\n"
    "                                     'w': SPELL.get((ct, ab), 1.0) * FOC[ct], 'stun': st, **cand_info(who, pos.get(who), j, 4, r)})\n")

# 6. retreat rows: bush
rep("                             'pursued': pursued, 'd_enemy': d0, 'enemy': types[j]})\n",
    "                             'pursued': pursued, 'd_enemy': d0, 'enemy': types[j],\n"
    "                             'bush0': p in bushset, 'bush3': any((lambda cc: cc is not None and cc[7] and (cc[3], cc[4]) in bushset)(S.get(r + k2, {}).get(b)) for k2 in (1, 2, 3)),\n"
    "                             'bush_near': bool(bushset) and min((cheb(p, q) for q in bushset), default=99) <= 3})\n")

# 7. fight rows: objective distance
rep("                      'approach': approach, 'r_open': r_open, 'answer': answer, 'leave': leave, 'deaths': dlist,\n",
    "                      'approach': approach, 'r_open': r_open, 'answer': answer, 'leave': leave, 'deaths': dlist,\n"
    "                      'd_alt': min((cheb(cp, q) for q in altars), default=None), 'd_camp': min((cheb(cp, q) for q in camp_tiles), default=None),\n"
    "                      'a_gems': ca[8] if ca else None, 't_gems': ct[8] if ct else None,\n")

# 8. hit rows: candidate fields
rep("        hrows.append({'mid': mid, 't': team[h['a']], 'a': h['a'], 'champ': types[h['a']], 'tgt': types[h['t']], 'r': h['r'], 'kind': h['kind'],\n"
    "                      'helpers': len(helpers), 'al6': al6, 'en6': en6, 'fid': hit_fight[i]})\n",
    "        hrows.append({'mid': mid, 't': team[h['a']], 'a': h['a'], 'champ': types[h['a']], 'tgt': types[h['t']], 'r': h['r'], 'kind': h['kind'],\n"
    "                      'helpers': len(helpers), 'al6': al6, 'en6': en6, 'fid': hit_fight[i], 'stun': h['stun'],\n"
    "                      'nc': h.get('nc'), 'low': h.get('low'), 'thp': h.get('thp'), 'tg': h.get('tg'), 'maxg': h.get('maxg'), 'mc': h.get('mc'),\n"
    "                      'dist': h.get('dist') if h.get('dist') is not None else (cheb(h['ap'], h['tp']) if h['ap'] and h['tp'] else None), 'ahp': h.get('ahp'),\n"
    "                      'same_r': sum(1 for (r2, a2) in by_target_r[h['t']] if a2 != h['a'] and r2 == h['r'])})\n")

# 9. contacts + cast post-pass, before the game row
rep("    g = {'mid': mid, 'map': gm['map'], 'kind': gm['kind'],",
    "    # ---- cast post-pass: recently hit / hitting\n"
    "    hit_by_r = defaultdict(set)\n"
    "    for h in hits:\n"
    "        hit_by_r[h['a']].add(h['r'])\n"
    "    for cr in casts:\n"
    "        b, r = cr['body'], cr['r']\n"
    "        cr['fight'] = any(x in hit_rounds[b] or x in hit_by_r[b] for x in range(r - 3, r + 1))\n"
    "    # ---- contact episodes: nearest enemy <= 5 after >= 5 rounds with none within 7\n"
    "    contacts = []\n"
    "    alive_pos = {}\n"
    "    for r in range(1, final + 1):\n"
    "        s = S.get(r)\n"
    "        if s:\n"
    "            alive_pos[r] = {i: (c[3], c[4]) for i, c in s.items() if c[7]}\n"
    "    def dn_at(b, r):\n"
    "        ap = alive_pos.get(r, {})\n"
    "        p = ap.get(b)\n"
    "        if p is None:\n"
    "            return None\n"
    "        return min((cheb(p, q) for i, q in ap.items() if team[i] != team[b]), default=99)\n"
    "    hits_inv = defaultdict(list)\n"
    "    for h in hits:\n"
    "        hits_inv[h['a']].append((h['r'], 'dealt', h['t']))\n"
    "        hits_inv[h['t']].append((h['r'], 'taken', h['a']))\n"
    "    for b in types:\n"
    "        if types[b] is None:\n"
    "            continue\n"
    "        tb = team[b]\n"
    "        hist = deque(maxlen=5)\n"
    "        last_c = -100\n"
    "        for r in range(1, final + 1):\n"
    "            dn = dn_at(b, r)\n"
    "            if dn is not None and dn <= 5 and len(hist) == 5 and all(x is not None and x > 7 for x in hist) and r - last_c >= 10:\n"
    "                last_c = r\n"
    "                p = alive_pos[r][b]\n"
    "                po, no = power(r, p, tb, 6, excl=b, incl_self=b)\n"
    "                pe, ne = power(r, p, 1 - tb, 6)\n"
    "                ev = sorted(x for x in hits_inv[b] if r <= x[0] <= r + 6)\n"
    "                dealt = any(x[1] == 'dealt' for x in ev)\n"
    "                taken = any(x[1] == 'taken' for x in ev)\n"
    "                first = ev[0][1] if ev else None\n"
    "                dn6 = dn_at(b, r + 6)\n"
    "                died = any(r <= x <= r + 10 for x in death_r[b])\n"
    "                c = S[r][b]\n"
    "                tw, aw, sd = move_class(b, r + 1, r + 4)\n"
    "                contacts.append({'mid': mid, 't': tb, 'body': b, 'champ': types[b], 'r': r, 'dn': dn, 'pr': (po / pe) if pe > 0 else None,\n"
    "                                 'n_own': no, 'n_en': ne, 'hp': c[5] / max(1, c[6]), 'gems': c[8], 'dealt': dealt, 'taken': taken,\n"
    "                                 'first': first, 'dn6': dn6, 'died10': died, 'tw4': tw, 'aw4': aw,\n"
    "                                 'farming': any(r - 3 <= x <= r for x in champ_camp[b]), 'sh': shards(c[11]),\n"
    "                                 'sh_en': [shards(S[r][i][11]) for i in nearby(r, p, 1 - tb)],\n"
    "                                 'd_alt': min((cheb(p, q) for q in altars), default=None), 'd_own': dist_home(tb, p), 'd_en': dist_home(1 - tb, p)})\n"
    "            hist.append(dn)\n"
    "    g = {'mid': mid, 'map': gm['map'], 'kind': gm['kind'],")
rep("    return {'games': [g], 'deaths': drows, 'fights': frows, 'retreats': retreats, 'dives': dives, 'chases': chases, 'hits': hrows, 'parts': parts_rows}",
    "    return {'games': [g], 'deaths': drows, 'fights': frows, 'retreats': retreats, 'dives': dives, 'chases': chases, 'hits': hrows, 'parts': parts_rows,\n"
    "            'casts': casts, 'contacts': contacts}")
rep("NAMES = ('games', 'deaths', 'fights', 'retreats', 'dives', 'chases', 'hits', 'parts')",
    "NAMES = ('games', 'deaths', 'fights', 'retreats', 'dives', 'chases', 'hits', 'parts', 'casts', 'contacts')")
# 10. sharding
rep("    if limit:\n        todo = todo[:limit]\n",
    "    if limit:\n        todo = todo[:limit]\n"
    "    shard = None\n"
    "    if '--shard' in sys.argv:\n"
    "        k, n = map(int, sys.argv[sys.argv.index('--shard') + 1].split('/'))\n"
    "        todo = [g for i, g in enumerate(todo) if i % n == k]\n"
    "        shard = k\n")
rep("    gpath = f'{out}/{ds}_games.jsonl'\n",
    "    sfx = ''\n"
    "    if '--shard' in sys.argv:\n"
    "        sfx = '_s' + sys.argv[sys.argv.index('--shard') + 1].split('/')[0]\n"
    "    gpath = f'{out}/{ds}{sfx}_games.jsonl'\n")
rep("    fh = {n: open(f'{out}/{ds}_{n}.jsonl', mode) for n in NAMES}\n",
    "    fh = {n: open(f'{out}/{ds}{sfx}_{n}.jsonl', mode) for n in NAMES}\n")
open(P, 'w').write(s)
print('patched')
