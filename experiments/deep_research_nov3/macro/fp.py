#!/usr/bin/env python3
"""Macro fingerprints of the top-30 teams (Nov 3 2026) and of us.
Inputs (per side rows): ext/econ_rows.jsonl (economy/econ.py on top-30 vs top-30 games), ext/obj_games.jsonl (objectives/extract_obj.py),
ext/db_teams.jsonl + ext/db_bodies.jsonl (draft_bank/extract_all.py); ours: economy/rows_ours.jsonl, objectives/out/games_me.jsonl,
draft_bank/out/{teams,bodies}.jsonl (set 'ours').
Outputs: fp_sides.jsonl (one row per side with all features), fp_out.txt (team table, correlations, group comparisons, builds).
   nice -n 19 python3 -I fp.py
Groups: T5 = ranks 1-5, T20 = ranks 20-30 (team-level means), TOPl / TOPw = losing / winning top-30 sides (pooled),
ME = HouseOfCoders v84-v88 (econ/obj) or ours_v84+ours_v88 (draft_bank), OPP = our opponents in those same games.
Map-adjusted features ('_r' suffix) = side value minus the mean of all top-30 sides on that map."""
import json, math
from collections import Counter, defaultdict

T = '/home/claude/cambridge_battlecode/experiments/top30_nov3'
M = '/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro'
ME = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'
FAM = ['Monster', 'Power', 'Durability', 'Treasure', 'Jungle', 'Home', 'Bruiser', 'Tribute', 'Capture', 'Prospector', 'Hunter',
       'Skirmish', 'Greed', 'Collectors']
STAT = ['str', 'foc', 'hp']
lad = json.load(open(f'{T}/ladder.json'))['teams']
RANK = {t['teamId']: t['rank'] for t in lad}
RATING = {t['teamId']: t['rating'] for t in lad}
NAME2ID = {t['name']: t['teamId'] for t in lad}
TOP = [t for t in lad if t['rank'] <= 30]


def jl(fn):
    out = []
    for l in open(fn):
        try:
            o = json.loads(l)
        except Exception:
            continue
        if 'error' not in o:
            out.append(o)
    return out


def sdiv(a, b):
    return a / b if b else None


# ---------------------------------------------------------------- econ features
def econ_feat(r):
    ph = [p for p in r['phases'] if p]
    f = {}
    alive = sum(p['brounds'] - p['st'].get('dead', 0) for p in ph)
    for k in ('walk', 'hit', 'fight', 'recall', 'capture', 'wait', 'bank'):
        f['st_' + k] = sdiv(sum(p['st'].get(k, 0) for p in ph), alive)
    hits = sum(p['hits'] for p in ph)
    f['hits_c_share'] = sdiv(sum(p['hits_c'] for p in ph), hits)
    ctot = sum(sum(p['st_c'].values()) for p in ph)
    for k in ('hit', 'fight', 'walk', 'recall', 'capture'):
        f['c_' + k] = sdiv(sum(p['st_c'].get(k, 0) for p in ph), ctot)
    f['contact_share'] = sdiv(ctot, alive)
    for i, p in enumerate(r['phases']):
        if p and p['rounds'] > 0:
            f[f'pace{i + 1}'] = 100 * p['gems'] / p['rounds']
            f[f'gold{i + 1}'] = 100 * p['gold_earned'] / p['rounds']
    gems = sum(p['gems'] for p in ph)
    f['gems_cap'] = gems
    f['cap_big_share'] = sdiv(sum(p['cap_big'] for p in ph), gems)
    f['cap_enemy_share'] = sdiv(sum(p['cap_enemy_side'] for p in ph), gems)
    f['lost'] = sum(p['lost'] for p in ph)
    f['lost_share'] = sdiv(f['lost'], gems)
    f['deaths'] = r['deaths']
    f['first_cap'] = r.get('first_cap')
    f['g150'] = r.get('gems150')
    f['g300'] = r.get('gems300')
    ck = r.get('checks', {})
    for c in ('150', '300', '600'):
        if ck.get(c):
            f['shards' + c] = ck[c]['shards']
            f['emb' + c] = ck[c]['emblems']
            f['goldbank' + c] = ck[c]['gold']
    er = r.get('emblem_rounds') or []
    f['first_emblem_r'] = min(e[0] for e in er) if er else None
    sh = r.get('shops', {})
    f['shop_walk_share'] = sdiv(sh.get('walk', 0), sh.get('walk', 0) + sh.get('recall', 0))
    sl = r.get('shop_list') or []
    f['first_shop_r'] = min(s[0] for s in sl) if sl else None
    f['held_recalls'] = r.get('held_recalls')
    # opening: first visit per body
    op = r.get('opening', {})
    firsts = []
    allv = []
    for b, o in op.items():
        vs = sorted(o.get('visits') or [], key=lambda v: v['first'])
        if vs:
            firsts.append(vs[0]['g'])
            allv.append(vs[0])
    if firsts:
        c = Counter(firsts)
        f['open_stack'] = max(c.values())
        f['open_targets'] = len(c)
        f['open_stack_frac'] = max(c.values()) / len(firsts)
        v0 = min(allv, key=lambda v: v['first'])
        f['open_first_rank'] = v0.get('rank')
        f['open_first_gems'] = v0.get('gems')
        dd, de = v0.get('d'), v0.get('d_enemy')
        f['open_first_own'] = None if dd is None or de is None else 1 if dd < de else 0
        f['open_first_types'] = ''.join(sorted(set(v0.get('types', ''))))
        f['open_first_hit'] = v0.get('first')
    # endgame
    f['final'] = r['final']
    f['sub'] = r['sub']
    f['win'] = 1 if r['res'] == 'W' else 0
    f['win1000'] = 1 if (r['res'] == 'W' and r['sub'] >= 1000) else 0 if r['res'] == 'W' else None
    f['margin'] = r['sub'] - r['sub_opp']
    f['nbody'] = r['nbody']
    return f


def econ_builds(r):
    """first emblem family per champion type and first purchase"""
    out = {}
    for b, v in (r.get('builds') or {}).items():
        seq = v.get('seq') or []
        embs = [s for s in seq if s[3] == 1]
        if embs:
            out[v['champ']] = (FAM[embs[0][1]], STAT[embs[0][2]], embs[0][0])
    return out


# ---------------------------------------------------------------- objectives features
def obj_feat(o, t):
    s = o['side'][t]
    f = {}
    cg = s['cap_gems']
    tot = sum(cg.values())
    f['mid_share'] = sdiv(cg.get('mid', 0), tot)
    f['their_share'] = sdiv(cg.get('their', 0), tot)
    f['raids'] = s['raids']
    f['raid_caps'] = s['raid_caps']
    f['raid_kills'] = s['raid_kills']
    f['raid_deaths'] = s['raid_deaths']
    f['raid_first_r'] = s['raid_first_r']
    f['wards'] = s['wards']
    f['wards300'] = s['wards_by300']
    f['cov600'] = s['cov600']
    rw = s.get('recall_why', {})
    nr = sum(rw.values())
    for k in ('heal', 'shop', 'reposition', 'bank'):
        f['recall_' + k] = sdiv(rw.get(k, 0), nr)
    f['recalls'] = s.get('recalls')
    f['their_half_hits'] = sdiv(s.get('their_half_hits', 0), s.get('camp_hits', 0))
    u = s.get('use_band', {})
    ut = sum(u.values())
    f['use_mid'] = sdiv(u.get('mid', 0), ut)
    f['use_their'] = sdiv(u.get('their', 0), ut)
    o_ = '1' if t == '0' else '0'
    steals = steal_g = 0
    big_taken = big_any = 0
    first_arr = first_n = 0
    both_won = both_n = 0
    cont_won = cont_n = 0
    waits, ns = [], []
    for cy in o.get('cycles', []):
        if cy.get('by') is not None and str(cy['by']) == t and cy['hits'].get(t, 0) < cy['hits'].get(o_, 0):
            steals += 1
            steal_g += cy['gems']
        if cy['gems'] < 30:
            continue
        if cy.get('by') is not None:
            big_any += 1
            big_taken += str(cy['by']) == t
        fa = cy.get('first_arr')
        if fa is not None and fa != 'same':
            first_n += 1
            first_arr += str(fa) == t
        a = cy.get('arr', {})
        if a.get(t) and a.get(o_) and cy.get('by') is not None:
            both_n += 1
            both_won += str(cy['by']) == t
        if a.get(t):
            waits.append(a[t]['wait'])
            ns.append(a[t]['n'])
        if cy.get('contested_reward') and cy.get('by') is not None:
            cont_n += 1
            cont_won += str(cy['by']) == t
    f['steals'] = steals
    f['steal_gems'] = steal_g
    f['big_taken_share'] = sdiv(big_taken, big_any)
    f['big_first_arr'] = sdiv(first_arr, first_n)
    f['big_both_won'] = sdiv(both_won, both_n)
    f['big_cont_won'] = sdiv(cont_won, cont_n)
    f['big_wait'] = sum(waits) / len(waits) if waits else None
    f['big_arr_n'] = sum(ns) / len(ns) if ns else None
    f['big_cycles_present'] = len(waits)
    return f


# ---------------------------------------------------------------- draft_bank features
def db_feat(d, bodies):
    f = {}
    for k in ('bag_mean', 'n_sub', 'marc_share', 'gems_lost', 'deaths_bag20', 'locks', 'kills', 'carried_mean'):
        f['b_' + k] = d.get(k)
    ac = d.get('aclass') or {}
    na = sum(ac.values())
    f['b_spawnaltar_share'] = sdiv(ac.get('spawnaltar', 0), na)
    f['b_en6_share'] = sdiv(d.get('en6_banks', 0), d.get('n_banked') or 0)
    f['b_reach1000'] = d.get('reach1000')
    cap = defaultdict(int)
    tot = 0
    for b in bodies:
        cap[b['champ']] += b['captured']
        tot += b['captured']
    for c, k in (('Marcella', 'Ma'), ('VesperVale', 'VV'), ('HeartOfRuin', 'HR'), ('Vendetta', 'Vd'), ('Ryth', 'Ry')):
        f['capby_' + k] = sdiv(cap.get(c, 0), tot)
    f['capby_CI'] = sdiv(cap.get('Cassi', 0) + cap.get('Issac', 0), tot)
    f['capby_maxshare'] = sdiv(max(cap.values()) if cap else 0, tot)
    return f


def main():
    sides = []  # dict: team id, grp, res, map, feats
    # ---- top-30 econ
    E = jl(f'{M}/ext/econ_rows.jsonl')
    builds = defaultdict(lambda: defaultdict(Counter))
    for r in E:
        tid = r['teamId']
        if RANK.get(tid, 999) > 30:
            continue
        sides.append({'src': 'e', 'mid8': r['mid'].rsplit('_', 1)[1], 'map': r['map'], 'tid': tid, 'grp': 'top', 'res': r['res'],
                      'f': econ_feat(r)})
        for ch, b in econ_builds(r).items():
            builds[tid][ch][f'{b[0]}-{b[1]}'] += 1
    nE = len({s['mid8'] for s in sides})
    # ---- ours econ
    for r in jl(f'{T}/economy/rows_ours.jsonl'):
        if r['ver'] not in ('v84', 'v85', 'v86', 'v87', 'v88'):
            continue
        g = 'ME' if r['me'] else 'OPP'
        sides.append({'src': 'e', 'mid8': r['mid'][:8], 'map': r['map'], 'tid': r['teamId'], 'grp': g, 'ver': r['ver'], 'res': r['res'],
                      'f': econ_feat(r)})
        if r['me']:
            for ch, b in econ_builds(r).items():
                builds[ME][ch][f'{b[0]}-{b[1]}'] += 1
    # ---- objectives
    O = jl(f'{M}/ext/obj_games.jsonl')
    for o in O:
        for t in ('0', '1'):
            tid = o['sides'][t]['id']
            if RANK.get(tid, 999) > 30:
                continue
            sides.append({'src': 'o', 'mid8': o['mid'][:8], 'map': o['map'], 'tid': tid, 'grp': 'top',
                          'res': 'W' if o['side'][t]['win'] else 'L', 'f': obj_feat(o, t)})
    for o in jl(f'{T}/objectives/out/games_me.jsonl'):
        for t in ('0', '1'):
            tid = o['sides'][t]['id']
            sides.append({'src': 'o', 'mid8': o['mid'][:8], 'map': o['map'], 'tid': tid, 'grp': 'ME' if tid == ME else 'OPP', 'ver': o['ver'],
                          'res': 'W' if o['side'][t]['win'] else 'L', 'f': obj_feat(o, t)})
    # ---- draft_bank
    def add_db(teams_fn, bodies_fn, setname):
        B = defaultdict(list)
        for b in jl(bodies_fn):
            if b.get('set') == setname:
                B[(b['mid'], b['team'])].append(b)
        for d in jl(teams_fn):
            if d.get('set') != setname:
                continue
            if setname == 'top30':
                tid = NAME2ID.get(d['name'])
                if RANK.get(tid, 999) > 30:
                    continue
                g = 'top'
            else:
                if d['grp'] in ('ours_v88', 'ours_v84'):
                    g, tid = 'ME', ME
                elif d['grp'] == 'opp':
                    g, tid = 'OPP', NAME2ID.get(d['name'], d['name'])
                else:
                    continue
            sides.append({'src': 'd', 'mid8': d['mid'][:8], 'map': d['map'], 'tid': tid, 'grp': g, 'res': 'W' if d['res'] == 'win' else 'L',
                          'f': db_feat(d, B[(d['mid'], d['team'])])})
    import os
    if os.path.exists(f'{M}/ext/db_bodies.jsonl') and os.path.getsize(f'{M}/ext/db_bodies.jsonl') > 0 and 'econ_db done' in open(f'{M}/ext/econ_db.log').read():
        add_db(f'{M}/ext/db_teams.jsonl', f'{M}/ext/db_bodies.jsonl', 'top30')
    else:
        add_db(f'{T}/draft_bank/out/teams.jsonl', f'{T}/draft_bank/out/bodies.jsonl', 'top30')
    add_db(f'{T}/draft_bank/out/teams.jsonl', f'{T}/draft_bank/out/bodies.jsonl', 'ours')

    # ---- map adjustment (relative to the mean of top-30 sides on that map)
    ADJ = ['g150', 'g300', 'pace1', 'pace2', 'pace3', 'pace4', 'gold1', 'gold2', 'first_cap', 'gems_cap', 'deaths', 'shards300',
           'shards600', 'emb300', 'mid_share', 'their_share', 'wards', 'b_n_sub', 'b_bag_mean', 'st_walk', 'hits_c_share', 'contact_share']
    mm = defaultdict(list)
    for s in sides:
        if s['grp'] == 'top':
            for k in ADJ:
                v = s['f'].get(k)
                if v is not None:
                    mm[(s['map'], k)].append(v)
    mmean = {k: sum(v) / len(v) for k, v in mm.items()}
    for s in sides:
        for k in ADJ:
            v = s['f'].get(k)
            if v is not None and (s['map'], k) in mmean:
                s['f'][k + '_r'] = v - mmean[(s['map'], k)]
    with open(f'{M}/fp_sides.jsonl', 'w') as fo:
        for s in sides:
            fo.write(json.dumps(s) + '\n')

    # ---- aggregation
    def mean(vals):
        vals = [v for v in vals if v is not None]
        return (sum(vals) / len(vals), len(vals)) if vals else (None, 0)

    feats = sorted({k for s in sides for k, v in s['f'].items() if isinstance(v, (int, float)) and not isinstance(v, bool)})
    team = defaultdict(lambda: defaultdict(list))
    for s in sides:
        if s['grp'] == 'top':
            for k in feats:
                team[s['tid']][k].append(s['f'].get(k))
            team[s['tid']]['_n_' + s['src']].append(1)
    tm = {tid: {k: mean(v)[0] for k, v in d.items()} for tid, d in team.items()}
    tn = {tid: {k: mean(v)[1] for k, v in d.items()} for tid, d in team.items()}

    def spearman(xs, ys):
        pts = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
        if len(pts) < 8:
            return None, len(pts)

        def rk(v):
            o = sorted(range(len(v)), key=lambda i: v[i])
            r = [0] * len(v)
            i = 0
            while i < len(o):
                j = i
                while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
                    j += 1
                for q in range(i, j + 1):
                    r[o[q]] = (i + j) / 2
                i = j + 1
            return r
        a, b = rk([p[0] for p in pts]), rk([p[1] for p in pts])
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        va = math.sqrt(sum((x - ma) ** 2 for x in a))
        vb = math.sqrt(sum((y - mb) ** 2 for y in b))
        return (cov / (va * vb) if va and vb else None), len(pts)

    ids = [t['teamId'] for t in TOP]
    out = open(f'{M}/fp_out.txt', 'w')
    P = lambda *a: print(*a, file=out)
    P(f'sides: econ top-30 games {nE}; total side rows {len(sides)}; by src/grp {Counter((s["src"], s["grp"]) for s in sides)}')
    # pooled group means
    def grp_mean(k, cond):
        return mean([s['f'].get(k) for s in sides if cond(s)])

    rows = []
    for k in feats:
        rho, n = spearman([tm.get(i, {}).get(k) for i in ids], [RATING[i] for i in ids])
        t5 = mean([tm.get(i, {}).get(k) for i in ids if RANK[i] <= 5])
        t20 = mean([tm.get(i, {}).get(k) for i in ids if RANK[i] >= 20])
        topw = grp_mean(k, lambda s: s['grp'] == 'top' and s['res'] == 'W')
        topl = grp_mean(k, lambda s: s['grp'] == 'top' and s['res'] == 'L')
        t5l = grp_mean(k, lambda s: s['grp'] == 'top' and s['res'] == 'L' and RANK[s['tid']] <= 5)
        t20l = grp_mean(k, lambda s: s['grp'] == 'top' and s['res'] == 'L' and RANK[s['tid']] >= 20)
        me = grp_mean(k, lambda s: s['grp'] == 'ME')
        mel = grp_mean(k, lambda s: s['grp'] == 'ME' and s['res'] == 'L')
        me88 = grp_mean(k, lambda s: s['grp'] == 'ME' and s.get('ver') == 'v88')
        opp = grp_mean(k, lambda s: s['grp'] == 'OPP')
        oppw = grp_mean(k, lambda s: s['grp'] == 'OPP' and s['res'] == 'W')
        rows.append((k, rho, n, t5, t20, topw, topl, t5l, t20l, me, mel, me88, opp, oppw))
    rows.sort(key=lambda x: -abs(x[1]) if x[1] is not None else 0)

    def fm(v):
        if v is None:
            return '   -  '
        a = abs(v)
        return f'{v:6.3f}' if a < 1 else f'{v:6.2f}' if a < 10 else f'{v:6.1f}' if a < 1000 else f'{v:6.0f}'
    P('\n== FEATURE vs RATING across the 30 teams (Spearman rho on team means; n teams) and group means (value, n)')
    P('   T5/T20 = mean of team means (ranks 1-5 / 20-30); TOPw/TOPl = pooled top-30 winning/losing sides; T5l/T20l = losing sides of')
    P('   ranks 1-5 / 20-30; ME = us v84-v88 (all), MEl = our losses, ME88 = v88 only (losses), OPP = our opponents same games, OPPw their wins')
    P(f'{"feature":22} {"rho":>6} {"n":>3} | {"T5":>6} {"T20":>6} | {"TOPw":>6} {"TOPl":>6} {"T5l":>6} {"T20l":>6} | {"ME":>6} {"MEl":>6} {"ME88":>6} {"OPP":>6} {"OPPw":>6}  n(T5l,T20l,ME,MEl,OPP)')
    for (k, rho, n, t5, t20, topw, topl, t5l, t20l, me, mel, me88, opp, oppw) in rows:
        P(f'{k:22} {fm(rho)} {n:3d} | {fm(t5[0])} {fm(t20[0])} | {fm(topw[0])} {fm(topl[0])} {fm(t5l[0])} {fm(t20l[0])} | {fm(me[0])} {fm(mel[0])} {fm(me88[0])} {fm(opp[0])} {fm(oppw[0])}  ({t5l[1]},{t20l[1]},{me[1]},{mel[1]},{opp[1]})')
    json.dump({'rows': rows}, open(f'{M}/fp_corr.json', 'w'))
    json.dump({'tm': tm, 'tn': tn}, open(f'{M}/fp_team.json', 'w'))
    # ---- per-team table
    COLS = [('n_e', '_n_e'), ('n_o', '_n_o'), ('n_d', '_n_d'), ('win', 'win'), ('fcap', 'first_cap'), ('g150r', 'g150_r'), ('g300r', 'g300_r'),
            ('stack', 'open_stack'), ('ntarg', 'open_targets'), ('fown', 'open_first_own'), ('p2r', 'pace2_r'), ('p3r', 'pace3_r'),
            ('walk', 'st_walk'), ('hitC', 'hits_c_share'), ('cHit', 'c_hit'), ('cFig', 'c_fight'), ('bigF', 'big_first_arr'),
            ('bigW', 'big_both_won'), ('mid', 'mid_share'), ('thr', 'their_share'), ('raid', 'raids'), ('stl', 'steals'), ('ward', 'wards'),
            ('bag', 'b_bag_mean'), ('nsub', 'b_n_sub'), ('Ma%', 'capby_Ma'), ('VV%', 'capby_VV'), ('spA', 'b_spawnaltar_share'),
            ('lost', 'b_gems_lost'), ('lock', 'b_locks'), ('dth', 'deaths'), ('sh300', 'shards300'), ('emb1', 'first_emblem_r'),
            ('w1000', 'win1000')]
    P('\n== PER-TEAM FINGERPRINT (team means over sides in top-30 vs top-30 replays; n_e/n_o/n_d = sides in econ/objectives/banking rows)')
    P('rk team             ' + ' '.join(f'{c:>6}' for c, _ in COLS))
    for t in TOP:
        d = tm.get(t['teamId'], {})
        nn = tn.get(t['teamId'], {})
        vals = []
        for c, k in COLS:
            if k.startswith('_n_'):
                vals.append(f'{len(team[t["teamId"]].get(k, [])):6d}')
            else:
                vals.append(fm(d.get(k)))
        P(f'{t["rank"]:2d} {t["name"][:16]:16} ' + ' '.join(vals))
    for lab, cond in (('ME v84-88', lambda s: s['grp'] == 'ME'), ('OPP same gm', lambda s: s['grp'] == 'OPP'),
                      ('TOP losers', lambda s: s['grp'] == 'top' and s['res'] == 'L'), ('TOP winners', lambda s: s['grp'] == 'top' and s['res'] == 'W')):
        vals = []
        for c, k in COLS:
            if k.startswith('_n_'):
                vals.append(f'{sum(1 for s in sides if cond(s) and s["src"] == k[-1]):6d}')
            else:
                vals.append(fm(grp_mean(k, cond)[0]))
        P(f'{lab[:19]:19} ' + ' '.join(vals))
    # ---- builds
    P('\n== FIRST EMBLEM (family-stat) per champion, per team (count of games)')
    for t in TOP + [{'teamId': ME, 'rank': 70, 'name': 'HouseOfCoders'}]:
        bd = builds.get(t['teamId'], {})
        P(f'{t["rank"]:2d} {t["name"][:16]:16} ' + ' ; '.join(f'{ch[:4]}: ' + ','.join(f'{k} {v}' for k, v in cnt.most_common(2)) for ch, cnt in sorted(bd.items(), key=lambda kv: -sum(kv[1].values()))))
    # ---- opening first-target types
    P('\n== OPENING: first group touched (types), own-side share, stack size; per team')
    for t in TOP:
        ss = [s['f'] for s in sides if s['tid'] == t['teamId'] and s['src'] == 'e']
        c = Counter(f.get('open_first_types') for f in ss)
        P(f'{t["rank"]:2d} {t["name"][:16]:16} n={len(ss)} types {c.most_common(3)}')
    ss = [s['f'] for s in sides if s['grp'] == 'ME' and s['src'] == 'e']
    P(f'ME n={len(ss)} types {Counter(f.get("open_first_types") for f in ss).most_common(3)}')
    out.close()
    print('ok', len(sides))


main()
