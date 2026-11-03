#!/usr/bin/env python3
"""Per-team fight / micro fingerprints for the CAMBC 2026a top 30 (+ HouseOfCoders v84/v88 and their opponents).

Input : out/{top,our}_s{0,1}_{games,fights,deaths,retreats,chases,dives,hits,parts,casts,contacts}.jsonl  (extract3.py)
Output: tables_micro.txt (fingerprint table, correlations with rating, group contrasts, top-10 z-score notes)
        feats.json        (group -> feature -> [value, n])
Usage : nice -n 19 python3 -I analyze_micro.py
Groups: <team8> for each top-30 team (top-30 vs top-30 games), TOP, TOPw, TOPl, R01-10, R11-19, R20-30;
        US84, US88, OPP84, OPP88 (our ladder games on v84 / v88 and the opponents in the same games), US, OPP.
"""
import json, os, glob, random, math
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = f'{HERE}/out'
TOP = '/home/claude/cambridge_battlecode/experiments/top30_nov3'
LAD = {t['teamId']: t for t in json.load(open(f'{TOP}/ladder.json'))['teams']}
TOP30 = {tid: t for tid, t in LAD.items() if t['rank'] <= 30}


def rows(ds, name):
    for fn in sorted(glob.glob(f'{OUT}/{ds}_s*_{name}.jsonl')):
        for line in open(fn):
            if line.strip():
                try:
                    yield json.loads(line)
                except ValueError:
                    pass


# ---------------------------------------------------------------- side -> groups
SIDE = {}        # (mid, t) -> list of group labels
SIDE_DS = {}
GAMES = defaultdict(int)
DRAFT = defaultdict(Counter)
for ds in ('top', 'our'):
    seen = set()
    for g in rows(ds, 'games'):
        if g['mid'] in seen:
            continue
        seen.add(g['mid'])
        for t in (0, 1):
            tm = g['teams'][t]
            labs = []
            if ds == 'top':
                if tm['id'] not in TOP30 or g['teams'][1 - t]['id'] not in TOP30:
                    continue
                rk = TOP30[tm['id']]['rank']
                labs = [tm['id'][:8], 'TOP', 'TOPw' if tm['result'] == 'W' else 'TOPl',
                        'R01-10' if rk <= 10 else 'R11-19' if rk <= 19 else 'R20-30']
            else:
                if g['ver'] not in ('v84', 'v88'):
                    continue
                v = g['ver'][1:]
                labs = ['US' + v, 'US'] if t == g['we'] else ['OPP' + v, 'OPP']
            SIDE[(g['mid'], t)] = labs
            SIDE_DS[(g['mid'], t)] = ds
            for lab in labs:
                GAMES[lab] += 1
                for c in g['drafts'][t]:
                    DRAFT[lab][c] += 1


class Acc:
    def __init__(self):
        self.r = defaultdict(lambda: [0.0, 0])     # rate: [num, den]
        self.v = defaultdict(list)                 # values (mean / median)

    def rate(self, k, hit, n=1):
        self.r[k][0] += hit
        self.r[k][1] += n

    def val(self, k, x):
        if x is not None:
            self.v[k].append(x)


A = defaultdict(Acc)


def labs(mid, t):
    return SIDE.get((mid, int(t)), [])


def band(x):
    if x is None:
        return None
    return 'weak' if x < 0.67 else 'par' if x <= 1.5 else 'strong'


# ---------------------------------------------------------------- games: deaths, kills, steps
for ds in ('top', 'our'):
    seen = set()
    for g in rows(ds, 'games'):
        if g['mid'] in seen:
            continue
        seen.add(g['mid'])
        for t in (0, 1):
            for lab in labs(g['mid'], t):
                a = A[lab]
                a.rate('win', g['teams'][t]['result'] == 'W')
                a.val('exch_g', g['n_exch'])
                ss = g['step_stats']
                for bnd in ('weak', 'par', 'strong'):
                    tw = ss.get(f'{t}|{bnd}|toward|n', 0)
                    aw = ss.get(f'{t}|{bnd}|away|n', 0)
                    sd = ss.get(f'{t}|{bnd}|side|n', 0)
                    a.rate(f'step_tw_{bnd}', tw, tw + aw + sd)
                    a.rate(f'step_tw_{bnd}_die6', ss.get(f'{t}|{bnd}|toward|died6', 0), tw)
                a.val('weak_tw_g', ss.get(f'{t}|weak|toward|n', 0))
                a.val('weak_eqmore_tw_g', ss.get(f'{t}|weak+neq|toward|n', 0) + ss.get(f'{t}|weak+nmore|toward|n', 0))

# ---------------------------------------------------------------- deaths
for ds in ('top', 'our'):
    per = defaultdict(lambda: Counter())
    for d in rows(ds, 'deaths'):
        t = d['t']
        for lab in labs(d['mid'], t):
            per[(lab, d['mid'], t)]['n'] += 1
            a = A[lab]
            if d['cause'] == 'camp':
                ctx = 'camp'
            elif d.get('camp_waker') == 'enemy':
                ctx = 'enemy_camp'
            elif d.get('age') is not None and d['age'] <= 40:
                ctx = 'respawn'
            elif d.get('tw8', 0) >= 2:
                ctx = 'walkin'
            elif d.get('ret_r') is not None:
                ctx = 'caught'
            else:
                ctx = 'fight'
            per[(lab, d['mid'], t)][ctx] += 1
            per[(lab, d['mid'], t)]['carry'] += d['bag'] >= 10
            per[(lab, d['mid'], t)]['bag'] += d['bag']
            a.rate('d_stunned3', d.get('stunned3', False))
            a.rate('d_hitback', d.get('hit_back', False))
            a.rate('d_enemyhalf', d.get('enemy_half', False))
            a.rate('d_farming', d.get('farming', False))
            a.rate('d_marc', d.get('marcella_pattern', False))
            if d['champ'] == 'HeartOfRuin':
                per[(lab, d['mid'], t)]['hor'] += 1
        if d['killer'] != 'camp':
            for lab in labs(d['mid'], 1 - t):
                per[(lab, d['mid'], 1 - t)]['kill'] += 1
                per[(lab, d['mid'], 1 - t)]['kill_bag'] += d['bag']
    # every side gets a row even with no deaths
    for (mid, t), ls in SIDE.items():
        if SIDE_DS[(mid, t)] != ds:
            continue
        for lab in ls:
            c = per.get((lab, mid, t), Counter())
            a = A[lab]
            for k in ('n', 'camp', 'enemy_camp', 'respawn', 'walkin', 'caught', 'fight', 'carry', 'bag', 'kill', 'kill_bag', 'hor'):
                a.val('g_' + k, c[k])

# ---------------------------------------------------------------- fights / exchanges
FSTART = {}
for ds in ('top', 'our'):
    for f in rows(ds, 'fights'):
        FSTART[(ds, f['mid'], f['fid'])] = f['start']
        if not f['exchange']:
            for t in (0, 1):
                for lab in labs(f['mid'], t):
                    A[lab].rate('poke_open', f['first'] == t)
            continue
        for t in (0, 1):
            ls = labs(f['mid'], t)
            if not ls:
                continue
            o = 1 - t
            st, so = str(t), str(o)
            opened = f['first'] == t
            win = None if f['win'] is None else (1.0 if f['win'] == t else 0.0)
            pr = (f['pw'][st] / f['pw'][so]) if f['pw'][so] > 0 else None
            gap = None
            if f['parts'][st] and f['parts'][so]:
                gap = f['shards'][st] / f['parts'][st] - f['shards'][so] / f['parts'][so]
            for lab in ls:
                a = A[lab]
                a.rate('open', opened)
                w = 0.5 if win is None else win
                a.rate('xwin', w)
                a.rate('xwin_dec', win == 1.0, win is not None)
                a.val('x_gap', gap)
                a.val('x_parts_diff', f['parts'][st] - f['parts'][so])
                a.rate('x_more_bodies', f['parts'][st] > f['parts'][so])
                a.rate('x_fewer_bodies', f['parts'][st] < f['parts'][so])
                b = band(pr)
                if b:
                    a.rate(f'xwin_{b}', w)
                    a.rate(f'x_in_{b}', 1)
                if b == 'par' and gap is not None and abs(gap) <= 3:
                    a.rate('xwin_par_eqitem', w)
                if gap is not None:
                    gb = 'gneg' if gap < -3 else 'gpos' if gap > 3 else 'geq'
                    a.rate(f'xwin_{gb}', w)
                a.rate('x_near_obj', (f.get('d_alt') is not None and f['d_alt'] <= 4) or (f.get('d_camp') is not None and f['d_camp'] <= 3))
                a.val('x_deaths_own', f['dead'][st])
                a.val('x_deaths_en', f['dead'][so])
                if opened:
                    a.val('open_R', f['r_open'])
                    a.rate('open_weak', f['r_open'] is not None and f['r_open'] < 0.67)
                    a.rate('open_strong', f['r_open'] is not None and f['r_open'] > 1.5)
                    a.rate('open_walkin', f['approach'] == 'walkin')
                    a.rate('open_static', f['approach'] == 'static')
                    a.rate('open_spell', f['kind0'] in ('spell', 'area', 'dash'))
                    a.rate('open_on_carrier', (f.get('t_gems') or 0) >= 10)
                    a.rate('open_on_farmer', f.get('farm_def', False))
                    a.rate('open_alone', f.get('a_ally') is not None and f['a_ally'] > 6)
                    a.val('open_gap', gap)
                    a.rate('openwin', w)
                    if f['r_open'] is not None:
                        a.rate('openwin_' + band(f['r_open']), w)
                    a.rate(f'open_tgt_{f["target_champ"]}', 1)
                else:
                    a.rate('recv_answer1', f['answer'] is not None and f['answer'] <= 1)
                    a.rate('recvwin', w)
                    a.rate('recv_walkedinto', f['approach'] == 'received')

# ---------------------------------------------------------------- participations (stacking, late joins)
for ds in ('top', 'our'):
    for p in rows(ds, 'parts'):
        if not p['exchange']:
            continue
        for lab in labs(p['mid'], p['t']):
            a = A[lab]
            a.rate('part_alone', p['al6'] == 0)
            a.rate('part_outnum', p['en6'] > p['al6'] + 1)
            a.val('part_al6', p['al6'])
            st = FSTART.get((ds, p['mid'], p['fid']))
            if st is not None and not p['opener']:
                a.rate('part_late', p['r'] - st >= 2)
            a.rate('part_died', p['died'])

# ---------------------------------------------------------------- retreats
for ds in ('top', 'our'):
    for r in rows(ds, 'retreats'):
        for lab in labs(r['mid'], r['t']):
            a = A[lab]
            a.rate('ret_died8', r['died8'])
            if r['hp'] < 0.5:
                a.rate('ret_lowhp_died8', r['died8'])
            if r['own_dash']:
                a.rate('ret_dash_used', r['dash'])
                if r['champ'] == 'HeartOfRuin':
                    a.rate('ret_dash_used_HoR', r['dash'])
                if r['dash']:
                    a.rate('ret_dash_caught', r['died8'])
                else:
                    a.rate('ret_nodash_caught', r['died8'])
            a.rate('ret_to_ally', r['to_ally'])
            a.rate('ret_stun', r['stun'])
            if r.get('bush_near') and not r.get('bush0'):
                a.rate('ret_into_bush', r.get('bush3', False))
            a.val('ret_g', 1)

# ---------------------------------------------------------------- chases / dives
for ds in ('top', 'our'):
    for c in rows(ds, 'chases'):
        for lab in labs(c['mid'], c['t']):
            a = A[lab]
            a.rate('chase_died10', c['died10'])
            a.rate('chase_lured', c['died10'] and not c['killer_is_target'])
            a.rate('chase_into_more', (c['n_en1'] or 0) > c['n_en0'])
    for dv in rows(ds, 'dives'):
        for lab in labs(dv['mid'], dv['t']):
            A[lab].rate('dive_died8', dv['died8'])

# ---------------------------------------------------------------- hits: focus, target choice, kiting, burst
RANGED = {'VesperVale', 'Cassi', 'Stellar', 'Prism', 'Willow', 'Tavi'}
for ds in ('top', 'our'):
    stun_follow = defaultdict(list)
    for h in rows(ds, 'hits'):
        for lab in labs(h['mid'], h['t']):
            a = A[lab]
            a.rate('focus', h['helpers'] >= 1)
            a.rate('hit_outnum', h['en6'] > h['al6'] + 1)
            nc = h.get('nc') or 0
            if nc >= 2:
                a.rate('pick_low', bool(h.get('low')))
                a.rate('pick_low_base', 1.0 / nc)
                if (h.get('maxg') or 0) >= 5:
                    a.rate('pick_carrier', (h.get('tg') or 0) == h['maxg'])
                    a.rate('pick_carrier_base', 1.0 / nc)
                if h.get('mc'):
                    a.rate('pick_marc', h['tgt'] == 'Marcella')
                    a.rate('pick_marc_base', 1.0 / nc)
            a.val('hit_thp', h.get('thp'))
            if h['kind'] == 'atk' and h['champ'] in RANGED and h['tgt'] not in RANGED and h.get('dist') is not None:
                a.rate('kite_d3', h['dist'] >= 3)
                a.rate('kite_d1', h['dist'] <= 1)
            if h['kind'] in ('spell', 'area') and h.get('dist') is not None:
                a.rate('spell_d4', h['dist'] >= 4)
            if h['kind'] in ('spell', 'area', 'dash'):
                a.rate('spell_burst', (h.get('same_r') or 0) >= 1)
            if h.get('stun'):
                a.rate('stun_followed', h['helpers'] >= 1)

# ---------------------------------------------------------------- casts: dashes, Marcella, spells
for ds in ('top', 'our'):
    for c in rows(ds, 'casts'):
        for lab in labs(c['mid'], c['t']):
            a = A[lab]
            ch = c['champ']
            if c['ab'] == 6:
                if c.get('dn0') is None or c['dn0'] > 6:
                    a.rate(f'dash_travel_{ch}', 1)
                    continue
                a.rate(f'dash_travel_{ch}', 0)
                eng = c['dn1'] is not None and c['dn1'] < c['dn0']
                esc = c['dn1'] is not None and c['dn1'] > c['dn0']
                a.rate(f'dash_engage_{ch}', eng)
                a.rate(f'dash_escape_{ch}', esc)
                if ch == 'HeartOfRuin' and eng:
                    a.rate('hor_dash_hit', (c.get('nhit') or 0) >= 1)
                if esc:
                    a.val(f'dash_escape_hp_{ch}', c.get('hp'))
            elif c['ab'] == 'enh_atk':
                a.rate('marc_enh_champ', c['champ_hit'])
                if (c.get('dn') or 99) <= 4:
                    a.rate('marc_enh_champ_nearfoe', c['champ_hit'])
            elif c['ab'] in (2, 3, 4) and c.get('champ_hit') is not None:
                if (c.get('dn') or 99) <= 5:
                    a.rate(f'spell_on_champ_{ch}', c['champ_hit'] >= 1)
                    if c['champ_hit'] >= 1 and c.get('dist') is not None:
                        a.rate(f'spell_d4_{ch}', c['dist'] >= 4)
            elif c['ab'] == 1 and ch != 'Marcella':
                if (c.get('dn') or 99) <= 3:
                    a.rate('reset_in_fight', 1)

# ---------------------------------------------------------------- contacts: fight vs leave
for ds in ('top', 'our'):
    for c in rows(ds, 'contacts'):
        b = band(c['pr'])
        for lab in labs(c['mid'], c['t']):
            a = A[lab]
            left = (not c['dealt']) and (c['dn6'] is None or c['dn6'] > 6) and not c['died10']
            a.rate('ct_fight', c['dealt'])
            a.rate('ct_leave', left)
            a.rate('ct_died10', c['died10'])
            a.rate('ct_first', c['first'] == 'dealt', c['first'] is not None)
            if b:
                a.rate(f'ct_fight_{b}', c['dealt'])
                a.rate(f'ct_leave_{b}', left)
                a.rate(f'ct_died_{b}', c['died10'])
            if c['gems'] >= 10:
                a.rate('ct_carry_fight', c['dealt'])
            sh_en = c.get('sh_en') or []
            if sh_en:
                gap = c['sh'] - sum(sh_en) / len(sh_en)
                a.val('ct_gap', gap)
                if gap < -10:
                    a.rate('ct_fight_itemneg', c['dealt'])
                elif gap > 10:
                    a.rate('ct_fight_itempos', c['dealt'])

# ---------------------------------------------------------------- assemble features
def mean(v):
    return sum(v) / len(v) if v else None


def med(v):
    if not v:
        return None
    s = sorted(v)
    return s[len(s) // 2]


FEATS = {}
for lab, a in A.items():
    F = {}
    for k, (num, den) in a.r.items():
        if den:
            F[k] = (num / den, den)
    for k, v in a.v.items():
        if k == 'open_R':
            F['open_R_med'] = (med(v), len(v))
        else:
            F[k] = (mean(v), len(v))
    # lifts over random choice
    for k in ('pick_low', 'pick_carrier', 'pick_marc'):
        if k in F and k + '_base' in F:
            F[k + '_lift'] = (F[k][0] - F[k + '_base'][0], F[k][1])
    if 'g_n' in F:
        ng = F['g_n'][1]
        F['kd'] = ((F['g_kill'][0] or 0) / max(0.01, F['g_n'][0]), ng)
    if 'ct_fight_strong' in F and 'ct_fight_weak' in F:
        F['ct_select'] = (F['ct_fight_strong'][0] - F['ct_fight_weak'][0], min(F['ct_fight_strong'][1], F['ct_fight_weak'][1]))
    F['games'] = (GAMES[lab], GAMES[lab])
    FEATS[lab] = F
json.dump({k: v for k, v in FEATS.items()}, open(f'{HERE}/feats.json', 'w'))

# ---------------------------------------------------------------- report
ORDER = sorted(TOP30.values(), key=lambda t: t['rank'])
KEYS = [  # (feature, label, fmt, scale)
    ('games', 'games', '{:.0f}', 1), ('win', 'win%', '{:.0f}', 100),
    ('exch_g', 'exch/g', '{:.1f}', 1), ('open', 'open%', '{:.0f}', 100), ('open_R_med', 'openR', '{:.2f}', 1),
    ('open_weak', 'openWk%', '{:.0f}', 100), ('open_walkin', 'openWalk%', '{:.0f}', 100), ('open_spell', 'openSpl%', '{:.0f}', 100),
    ('open_gap', 'openGap', '{:+.0f}', 1), ('x_gap', 'xGap', '{:+.0f}', 1),
    ('ct_fight_weak', 'ctFtWk%', '{:.0f}', 100), ('ct_fight_par', 'ctFtPar%', '{:.0f}', 100), ('ct_fight_strong', 'ctFtSt%', '{:.0f}', 100),
    ('ct_leave_weak', 'ctLvWk%', '{:.0f}', 100), ('step_tw_weak', 'twWk%', '{:.0f}', 100),
    ('xwin', 'xWin%', '{:.0f}', 100), ('xwin_par', 'xWinPar%', '{:.0f}', 100), ('xwin_par_eqitem', 'xWinPar=it%', '{:.0f}', 100),
    ('x_more_bodies', 'xMoreB%', '{:.0f}', 100), ('x_near_obj', 'xObj%', '{:.0f}', 100),
    ('g_n', 'D/g', '{:.1f}', 1), ('g_kill', 'K/g', '{:.1f}', 1), ('g_bag', 'bagLost/g', '{:.0f}', 1),
    ('g_walkin', 'Dwalk/g', '{:.1f}', 1), ('g_caught', 'Dcaught/g', '{:.1f}', 1), ('g_respawn', 'Dresp/g', '{:.1f}', 1),
    ('g_camp', 'Dcamp/g', '{:.2f}', 1), ('g_enemy_camp', 'DenCamp/g', '{:.2f}', 1), ('g_carry', 'Dcarry/g', '{:.1f}', 1),
    ('ret_dash_used', 'retDash%', '{:.0f}', 100), ('ret_dash_used_HoR', 'HoRretDash%', '{:.0f}', 100),
    ('ret_died8', 'retCaught%', '{:.0f}', 100), ('ret_lowhp_died8', 'retLowCaught%', '{:.0f}', 100),
    ('ret_into_bush', 'retBush%', '{:.0f}', 100), ('ret_to_ally', 'retAlly%', '{:.0f}', 100),
    ('chase_died10', 'chaseDie%', '{:.0f}', 100), ('dive_died8', 'diveDie%', '{:.0f}', 100),
    ('focus', 'focus%', '{:.0f}', 100), ('pick_low_lift', 'lowLift', '{:+.2f}', 1), ('pick_carrier_lift', 'carLift', '{:+.2f}', 1),
    ('pick_marc_lift', 'marcLift', '{:+.2f}', 1), ('spell_d4', 'spellD4%', '{:.0f}', 100), ('spell_burst', 'burst%', '{:.0f}', 100),
    ('stun_followed', 'stunFol%', '{:.0f}', 100), ('kite_d3', 'kiteD3%', '{:.0f}', 100),
    ('part_alone', 'alone%', '{:.0f}', 100), ('part_late', 'late%', '{:.0f}', 100), ('recv_answer1', 'ans1%', '{:.0f}', 100),
    ('dash_engage_HeartOfRuin', 'HoRdEng%', '{:.0f}', 100), ('dash_escape_HeartOfRuin', 'HoRdEsc%', '{:.0f}', 100),
    ('hor_dash_hit', 'HoRdHit%', '{:.0f}', 100), ('dash_escape_VesperVale', 'VesDEsc%', '{:.0f}', 100),
    ('dash_engage_Vendetta', 'VenDEng%', '{:.0f}', 100), ('marc_enh_champ_nearfoe', 'MarcEnhCh%', '{:.0f}', 100),
    ('spell_d4_Marcella', 'MarcSpD4%', '{:.0f}', 100),
]


def fmt(F, k, f, sc, withn=True):
    if k not in F or F[k][0] is None:
        return '-'
    s = f.format(F[k][0] * sc)
    return s + (f'({F[k][1]})' if withn else '')


def ranks(xs):
    idx = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[idx[j + 1]] == xs[idx[i]]:
            j += 1
        for k in range(i, j + 1):
            r[idx[k]] = (i + j) / 2
        i = j + 1
    return r


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    if sx == 0 or sy == 0:
        return 0.0
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def spearman(x, y, perm=2000):
    rx, ry = ranks(x), ranks(y)
    rho = pearson(rx, ry)
    rnd = random.Random(7)
    c = 0
    ry2 = list(ry)
    for _ in range(perm):
        rnd.shuffle(ry2)
        if abs(pearson(rx, ry2)) >= abs(rho) - 1e-12:
            c += 1
    return rho, (c + 1) / (perm + 1)


L = []
L.append('TOP-30 MICRO FINGERPRINTS (extract3.py on experiments/top30_nov3 top-30 vs top-30 games; US/OPP = experiments/ladder_nov2 v84/v88 games)')
L.append('Each cell: value(n). n = games for per-game rates, otherwise the denominator (exchanges, contacts, retreats, hits, casts).')
L.append('')
# drafts
L.append('DRAFTS (champion picks per game, share)')
for t in ORDER:
    lab = t['teamId'][:8]
    g = GAMES[lab]
    top = ', '.join(f'{c} {100 * n / max(1, g):.0f}%' for c, n in DRAFT[lab].most_common(6))
    L.append(f"  #{t['rank']:2d} {t['name'][:24]:24s} {round(t['rating'])} n={g}: {top}")
for lab in ('US84', 'US88', 'OPP84', 'OPP88'):
    g = GAMES[lab]
    L.append(f"  {lab:28s} n={g}: " + ', '.join(f'{c} {100 * n / max(1, g):.0f}%' for c, n in DRAFT[lab].most_common(6)))
L.append('')

# table in chunks of columns
CH = 9
for c0 in range(0, len(KEYS), CH):
    keys = KEYS[c0:c0 + CH]
    L.append('rk team                     rating ' + ' '.join(f'{lbl:>14s}' for _, lbl, _, _ in keys))
    for t in ORDER:
        F = FEATS.get(t['teamId'][:8], {})
        L.append(f"{t['rank']:2d} {t['name'][:24]:24s} {round(t['rating']):6d} " + ' '.join(f'{fmt(F, k, f, sc):>14s}' for k, _, f, sc in keys))
    for lab in ('TOP', 'TOPw', 'TOPl', 'R01-10', 'R11-19', 'R20-30', 'US84', 'US88', 'OPP84', 'OPP88', 'US', 'OPP'):
        F = FEATS.get(lab, {})
        L.append(f"   {lab:24s} {'':6s} " + ' '.join(f'{fmt(F, k, f, sc):>14s}' for k, _, f, sc in keys))
    L.append('')

# correlations with rating across the 30 teams
L.append('SPEARMAN rho WITH RATING ACROSS THE 30 TEAMS (permutation p, 2000 perms; teams with n >= 10 for that feature)')
L.append('  feature                       rho     p    n_teams   R01-10   R20-30   US84   US88   OPP84  OPP88   TOPl')
allk = sorted({k for t in ORDER for k in FEATS.get(t['teamId'][:8], {})})
CORR = []
for k in allk:
    xs, ys = [], []
    for t in ORDER:
        F = FEATS.get(t['teamId'][:8], {})
        if k in F and F[k][0] is not None and F[k][1] >= 10:
            xs.append(F[k][0])
            ys.append(t['rating'])
    if len(xs) < 20:
        continue
    rho, p = spearman(xs, ys, 1000)
    CORR.append((k, rho, p, len(xs)))
CORR.sort(key=lambda z: -abs(z[1]))


def gv(lab, k):
    F = FEATS.get(lab, {})
    if k not in F or F[k][0] is None:
        return '-'
    v = F[k][0]
    return f'{v:.3f}' if abs(v) < 10 else f'{v:.1f}'


for k, rho, p, n in CORR:
    L.append(f'  {k:28s} {rho:+.2f} {p:6.3f} {n:5d}    ' + ' '.join(f'{gv(lab, k):>7s}' for lab in ('R01-10', 'R20-30', 'US84', 'US88', 'OPP84', 'OPP88', 'TOPl')))
L.append('')

# top-10 z-scores
L.append('TOP-10 DISTINCTIVE FEATURES (z vs the 30-team mean; only features with n >= 15)')
zkeys = [k for k, _, _, _ in KEYS if k not in ('games', 'win')]
stats = {}
for k in zkeys:
    vals = [FEATS.get(t['teamId'][:8], {}).get(k) for t in ORDER]
    vals = [v[0] for v in vals if v and v[0] is not None and v[1] >= 15]
    if len(vals) >= 15:
        m = sum(vals) / len(vals)
        sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) or 1
        stats[k] = (m, sd)
for t in ORDER[:10]:
    F = FEATS.get(t['teamId'][:8], {})
    zs = []
    for k, (m, sd) in stats.items():
        if k in F and F[k][0] is not None and F[k][1] >= 15:
            zs.append(((F[k][0] - m) / sd, k, F[k][0], F[k][1], m))
    zs.sort(key=lambda z: -abs(z[0]))
    L.append(f"  #{t['rank']} {t['name']}: " + '; '.join(f'{k} {v:.2f} (n {n}, mean {m:.2f}, z {z:+.1f})' for z, k, v, n, m in zs[:8]))
L.append('')
open(f'{HERE}/tables_micro.txt', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L[:5]))
print('written', len(L), 'lines')
