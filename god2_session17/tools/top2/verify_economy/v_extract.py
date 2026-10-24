# One pass per distinct match (fight dump + own vdump + own BFS geometry) -> C:/battlecode/cache/vecon/games.jsonl
# Per game: teams, winner, per-team captures by zone/class, tributes with outcomes and channel context, bank decisions after
# captures, deaths with bags / killers / kill gold, bag chains, per-round bag exposure, golem/monolith/elk attempts, mid-group
# respawn cycles with holders, per-body gold by source. Independent of tools/top2/economy.
#   python tools/top2/verify_economy/v_extract.py [WORKERS]
import sys, os, json, math, traceback
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vlib import *

OUT = f'{CACHE}/vecon/games.jsonl'


def bucket(b):
    return 'empty' if b == 0 else ('1-49' if b < 50 else ('50-149' if b < 150 else ('150-399' if b < 400 else '400+')))


def extract(base, ent, geo_all):
    g = Game(base, ent, geo_all)
    if g.vd is None or g.geo is None:
        return None
    fd, vd = g.fd, g.vd
    T = g.team
    W = g.geo['W']
    teams = [None, None]
    for t in g.row['teams']:
        teams[0 if t['side'] == 'a' else 1] = {'name': t['name'], 'id': t['teamId'][:8], 'picks': t['draftPicks'], 'result': t['result']}
    keyteam = {k: team_of_key(g.row, k) for k in g.keys}
    tkeys = {k: team_of_key(g.row, k) for k in KEYS if team_of_key(g.row, k) is not None}
    rec = {'base': base, 'map': g.map, 'keys': keyteam, 'tkeys': tkeys, 'teams': teams, 'created': g.row.get('createdAt'), 'win': g.win, 'final': g.final,
           'sub': fd['meta']['submitted'], 'endReason': g.row.get('endReason'),
           'bodies': {str(b): [T[b], g.btype[b]] for b in g.bodies}}
    rounds = sorted(g.R)
    # ---------- captures ----------
    caps = g.captures()
    capl = []
    for c in caps:
        grp = g.groups[c['g']]
        gems = sum(v[1] for v in c['gains'].values())
        gold = sum(v[0] for v in c['gains'].values())
        team = c['team']
        capl.append({'r': c['r'], 'q': c['q'], 'g': c['g'], 'team': team, 'cls': grp['cls'], 'gems': gems, 'gold': gold,
                     'zone': g.zone(grp, team) if team is not None else None, 'gains': {str(b): v for b, v in c['gains'].items()},
                     'n': len(c['gains'])})
    rec['caps'] = capl
    rec['groups'] = [{'cls': gr['cls'], 'fA': gr.get('fA'), 'gems': gr['gems'], 'gold': gr['gold'], 'resp': gr['resp'], 'tiles': gr['tiles']} for gr in g.groups]
    # ---------- gold by source per body (vdump D) ----------
    deaths_q = {}
    for e in fd['ev']:
        if e['k'] == 'Death':
            deaths_q.setdefault(e['q'], []).append(e)
    goldsrc = defaultdict(lambda: defaultdict(int))
    for q, r, b, dg, dgem, dal, kind, ak, ai in vd['D']:
        if dg > 0:
            if kind == 2:
                src = 'capture'
            elif q in deaths_q and any(d.get('by') == b for d in deaths_q[q]):
                src = 'kill'
            elif kind == 18:
                src = 'tribute'
            else:
                src = 'other%d' % kind
            goldsrc[b][src] += dg
        elif dg < 0:
            goldsrc[b]['spent%d' % kind] += -dg
    rec['goldsrc'] = {str(b): dict(v) for b, v in goldsrc.items()}
    # ---------- deaths ----------
    dl = []
    for e in fd['ev']:
        if e['k'] != 'Death':
            continue
        by = e.get('by')
        dl.append({'r': e['r'], 'q': e['q'], 'who': e['who'], 'team': e['team'], 'bag': e['bag'], 'by': by if isinstance(by, int) and by in T else ('camp' if by == 'camp' else 'other'), 'at': e['at']})
    # kill gold / gems gained by the killer at the death step
    dq = defaultdict(list)
    for x in vd['D']:
        dq[x[0]].append(x)
    for d in dl:
        if isinstance(d['by'], int):
            gain = [x for x in dq.get(d['q'], []) if x[2] == d['by']]
            d['kgold'] = sum(x[3] for x in gain if x[3] > 0)
            d['kgems'] = sum(x[4] for x in gain if x[4] > 0)
    rec['deaths'] = dl
    # ---------- banked events, submits, cancels, stuns, locks ----------
    ev = fd['ev']
    banked = [e for e in ev if e['k'] == 'Banked']
    submits = [e for e in ev if e['k'] == 'Submit gems']
    cancels = [e for e in ev if e['k'] == 'Cancel channel']
    locks = [e for e in ev if e['k'] == 'Place altar lock']
    stuns = fd['stun']
    rec['locks'] = [{'r': e['r'], 'who': e['who'], 'team': T.get(e['who']), 'to': e.get('to')} for e in locks]
    byb = defaultdict(list)  # body -> list of (q, kind, payload)
    for e in banked:
        byb[e['who']].append((e['q'], 'done', e))
    for e in submits:
        byb[e['who']].append((e['q'], 'start', e))
    for e in cancels:
        byb[e['who']].append((e['q'], 'cancel', e))
    for s in stuns:
        byb[s[3]].append((s[0], 'stun', s))
    for d in dl:
        byb[d['who']].append((d['q'], 'death', d))
    for b in byb:
        byb[b].sort(key=lambda t: t[0])
    lockq = sorted((e['q'], e['r'], T.get(e['who']), tuple(e.get('to') or ())) for e in locks)
    tribs = []
    for b, lst in byb.items():
        for i, (q0, kind, e) in enumerate(lst):
            if kind != 'start':
                continue
            r0 = e['r']
            altar = tuple(e.get('to') or ())
            st = g.state(r0 - 1).get(b)
            bag = st[5] if st else 0
            team = T[b]
            out, rq, rr, got = 'open', None, None, None
            for q1, k1, e1 in lst[i + 1:]:
                if k1 == 'done':
                    out, rq, rr, got = 'done', q1, e1['r'], e1['gems']
                    break
                if k1 in ('cancel', 'stun', 'death', 'start'):
                    out, rq = ('restart' if k1 == 'start' else k1), q1
                    rr = e1['r'] if isinstance(e1, dict) else e1[1]
                    break
            # an enemy lock placed on that altar between start and the outcome
            for lq, lr, lt, lto in lockq:
                if lq > q0 and (rq is None or lq < rq) and lt is not None and lt != team and lto == altar:
                    out, rq, rr = 'lock', lq, lr
                    break
            end = rr if rr is not None else g.final
            # closest enemy during the channel and own allies
            mind, minally_all = 99, 99
            ally_all = True
            for r in range(r0, end + 1):
                s = g.R.get(r)
                if not s or b not in s or not s[b][4]:
                    continue
                me = s[b]
                de = [cheb((me[0], me[1]), (v[0], v[1])) for o, v in s.items() if T[o] != team and v[4]]
                da = [cheb((me[0], me[1]), (v[0], v[1])) for o, v in s.items() if T[o] == team and o != b and v[4]]
                if de:
                    mind = min(mind, min(de))
                if not da or min(da) > 4:
                    ally_all = False
            # enemy distance at the end round (for cancels)
            dend = None
            s = g.R.get(end - 1) or g.R.get(end)
            if s and b in s and s[b][4]:
                de = [cheb((s[b][0], s[b][1]), (v[0], v[1])) for o, v in s.items() if T[o] != team and v[4]]
                dend = min(de) if de else None
            s = g.R.get(end)
            dend2 = None
            if s and b in s and s[b][4]:
                de = [cheb((s[b][0], s[b][1]), (v[0], v[1])) for o, v in s.items() if T[o] != team and v[4]]
                dend2 = min(de) if de else None
            banked0 = g.sub.get(r0 - 1, (0, 0))[team] if (r0 - 1) in g.sub else 0
            tribs.append({'b': b, 'team': team, 'type': g.btype[b], 'r0': r0, 'q0': q0, 'bag': bag, 'altar': list(altar), 'out': out,
                          'rend': rr, 'got': got, 'mind': mind, 'dend': dend, 'dend2': dend2, 'ally_all': ally_all, 'banked0': banked0})
    tribs.sort(key=lambda t: t['q0'])
    rec['tribs'] = tribs
    rec['banked'] = [[e['q'], e['r'], e['who'], e['gems']] for e in banked]
    # after a big-bag tribute ends without banking: what happens next to the body and to the closest enemy
    for t in tribs:
        if t['bag'] < 100 or t['out'] == 'done' or t['rend'] is None:
            continue
        b, r1 = t['b'], t['rend']
        nb = [e for e in banked if e['who'] == b and e['r'] >= r1]
        t['next_bank'] = [nb[0]['r'], nb[0]['gems']] if nb else None
        dd = [d for d in dl if d['who'] == b and d['r'] >= r1]
        t['next_death'] = [dd[0]['r'], dd[0]['bag'], dd[0]['by']] if dd else None
        s = g.R.get(r1 - 1) or g.R.get(r1)
        if s and b in s and s[b][4]:
            en = sorted((cheb((s[b][0], s[b][1]), (v[0], v[1])), o) for o, v in s.items() if T[o] != t['team'] and v[4])
            if en:
                o = en[0][1]
                t['enemy'] = [o, g.btype[o], en[0][0]]
                od = [d for d in dl if d['who'] == o and r1 <= d['r'] <= r1 + 20]
                t['enemy_died20'] = [od[0]['r'], od[0]['by']] if od else None
                # did the enemy hold a position 5-7 tiles away for the next rounds (standing outside reach)
                ds = []
                for r in range(r1, r1 + 11):
                    ss = g.R.get(r)
                    if ss and b in ss and o in ss and ss[b][4] and ss[o][4]:
                        ds.append(cheb((ss[b][0], ss[b][1]), (ss[o][0], ss[o][1])))
                t['enemy_d10'] = ds
    # ---------- hits by the body on champions after its cancels (within 5 rounds) ----------
    dmg_by = defaultdict(list)
    for x in fd['dmg']:
        if x[2] >= 0 and x[2] != x[3] and x[3] in T and T.get(x[2]) is not None and T[x[2]] != T[x[3]]:
            dmg_by[x[2]].append(x[1])
    for t in tribs:
        if t['out'] == 'cancel' and t['rend'] is not None:
            t['hit5'] = any(t['rend'] <= r <= t['rend'] + 5 for r in dmg_by.get(t['b'], []))
    # ---------- bank decision after captures ----------
    adm = altar_dist_map(g.geo)
    caps_by_body = defaultdict(list)
    for c in capl:
        for bs, (gold, gems) in c['gains'].items():
            caps_by_body[int(bs)].append((c['q'], c['r'], c))
    starts_by_body = defaultdict(list)
    for t in tribs:
        starts_by_body[t['b']].append((t['q0'], t['r0']))
    deaths_by_body = defaultdict(list)
    for d in dl:
        deaths_by_body[d['who']].append(d['q'])
    bdec = []
    for b, lst in caps_by_body.items():
        lst.sort(key=lambda t: t[0])
        for i, (q, r, c) in enumerate(lst):
            st = g.state(r).get(b)
            if not st or not st[4]:
                continue
            bag = st[5]
            if bag <= 0:
                continue
            x, y = st[0], st[1]
            ad = [a[y * W + x] for a in adm if a[y * W + x] >= 0]
            dalt = min(ad) if ad else None
            nq = lst[i + 1][0] if i + 1 < len(lst) else 10 ** 12
            sq = [s for s in starts_by_body[b] if q < s[0] < nq]
            dq_ = [d for d in deaths_by_body[b] if q < d < nq]
            started = bool(sq) and (not dq_ or sq[0][0] < dq_[0])
            bdec.append([b, T[b], r, bag, dalt, 1 if started else 0, (sq[0][1] - r) if sq else None])
    rec['bdec'] = bdec
    # ---------- per-round exposure by bag (champion-kill deaths per body-round) ----------
    expo = defaultdict(lambda: [0, 0])  # (team, bucket) -> [body-rounds, champion-kill deaths]
    dr = defaultdict(list)
    for d in dl:
        dr[d['r']].append(d)
    prev = None
    for r in rounds:
        s = g.R[r]
        if prev is not None:
            for b, v in prev.items():
                if v[4]:
                    k = (T[b], bucket(v[5]))
                    expo[k][0] += 1
            for d in dr.get(r, []):
                pv = prev.get(d['who'])
                if pv and pv[4] and isinstance(d['by'], int):
                    expo[(T[d['who']], bucket(pv[5]))][1] += 1
        prev = s
    rec['expo'] = [[k[0], k[1], v[0], v[1]] for k, v in expo.items()]
    # ---------- attempts on golem / monolith / elk groups ----------
    hits = g.camp_hits()
    capsg = defaultdict(list)
    for c in capl:
        capsg[c['g']].append((c['r'], c['team']))
    att = []
    for gi, hl in hits.items():
        grp = g.groups[gi]
        if grp['cls'] not in ('golem', 'monolith', 'elk'):
            continue
        for team in (0, 1):
            th = [h for h in hl if h[1] in T and T[h[1]] == team]
            if not th:
                continue
            cur = [th[0]]
            chunks = []
            for h in th[1:]:
                if h[0] - cur[-1][0] > 30:
                    chunks.append(cur)
                    cur = [h]
                else:
                    cur.append(h)
            chunks.append(cur)
            for ch in chunks:
                r1, r2 = ch[0][0], ch[-1][0]
                hitters = sorted({h[1] for h in ch})
                h10 = len({h[1] for h in ch if h[0] <= r1 + 10})
                res = 'none'
                for cr, ct in capsg.get(gi, []):
                    if r1 <= cr <= r2 + 40:
                        res = 'won' if ct == team else 'stolen'
                        break
                s = g.state(r1 - 1)
                tiles = grp['tiles']
                en8 = any(T[o] != team and v[4] and min(cheb((v[0], v[1]), t) for t in tiles) <= 8 for o, v in s.items())
                hp_own = sum(v[3] for o, v in s.items() if T[o] == team and v[4])
                hp_en = sum(v[3] for o, v in s.items() if T[o] != team and v[4])
                al_own = sum(1 for o, v in s.items() if T[o] == team and v[4])
                al_en = sum(1 for o, v in s.items() if T[o] != team and v[4])
                carry = max([s[b][5] for b in hitters if b in s] + [0])
                att.append({'g': gi, 'cls': grp['cls'], 'team': team, 'r1': r1, 'r2': r2, 'hitters': len(hitters), 'h10': h10, 'res': res, 'en8': en8,
                            'hp': [hp_own, hp_en], 'al': [al_own, al_en], 'dmg': sum(h[2] for h in ch), 'carry': carry,
                            'zone': g.zone(grp, team)})
    rec['att'] = att
    # ---------- mid-group respawn cycles ----------
    resp = g.respawns()
    cyc = []
    for gi, grp in enumerate(g.groups):
        if 'fA' not in grp or not (0.4 <= grp['fA'] <= 0.6):
            continue
        cl = sorted([c for c in capl if c['g'] == gi], key=lambda c: c['q'])
        rl = resp.get(gi, [])
        hl = hits.get(gi, [])
        for i, c in enumerate(cl):
            rs = [x for x in rl if x > c['r']]
            if not rs:
                continue
            rsp = rs[0]
            nxt = cl[i + 1] if i + 1 < len(cl) else None
            if nxt is not None and nxt['r'] < rsp:
                continue
            s = g.state(rsp - 1)
            s2 = g.R.get(rsp, s)
            tiles = grp['tiles']
            hold = [0, 0]
            hold2 = [0, 0]
            for o, v in s.items():
                if v[4] and min(cheb((v[0], v[1]), t) for t in tiles) <= 4:
                    hold[T[o]] += 1
            for o, v in s2.items():
                if v[4] and min(cheb((v[0], v[1]), t) for t in tiles) <= 4:
                    hold2[T[o]] += 1
            prof = {}
            for off in (-60, -40, -30, -20, -10, -5, -2, -1, 0, 5, 10):
                ss = g.state(rsp + off)
                cnt = [0, 0]
                for o, v in ss.items():
                    if v[4] and min(cheb((v[0], v[1]), t) for t in tiles) <= 4:
                        cnt[T[o]] += 1
                prof[off] = cnt
            fh = [h for h in hl if h[0] >= rsp]
            first_hit = fh[0][0] if fh else None
            first_hit_team = T.get(fh[0][1]) if fh else None
            cyc.append({'g': gi, 'cls': grp['cls'], 'cap_r': c['r'], 'team': c['team'], 'resp': rsp, 'hold': hold, 'hold2': hold2,
                        'next_team': nxt['team'] if nxt else None, 'next_r': nxt['r'] if nxt else None,
                        'first_hit': first_hit, 'first_hit_team': first_hit_team, 'prof': prof})
    rec['cyc'] = cyc
    # ---------- per-team body-round time use: walked (position changed), hit a camp, dead ----------
    camp_hit_rounds = defaultdict(set)
    for q, r, a, ci, amt in fd['cdmg']:
        camp_hit_rounds[a].add(r)
    tu = defaultdict(lambda: [0, 0, 0, 0])  # team -> [body-rounds, dead, moved, hit camp]
    steps = defaultdict(int)
    prev = None
    for r in rounds:
        s = g.R[r]
        if prev is not None:
            for b, v in s.items():
                t = T[b]
                tu[t][0] += 1
                if not v[4]:
                    tu[t][1] += 1
                    continue
                pv = prev.get(b)
                if pv and pv[4] and (pv[0], pv[1]) != (v[0], v[1]):
                    tu[t][2] += 1
                    steps[t] += 1
                if r in camp_hit_rounds.get(b, ()):
                    tu[t][3] += 1
        prev = s
    rec['tu'] = {str(t): v for t, v in tu.items()}
    # banked at r300 / r600
    def subat(r):
        r = min(r, g.final)
        while r not in g.sub and r > 0:
            r -= 1
        return list(g.sub.get(r, (0, 0)))
    rec['sub300'] = subat(300)
    rec['sub600'] = subat(600)
    rec['maxhp300'] = [sum(v[3] for o, v in g.state(min(300, g.final)).items() if T[o] == t) for t in (0, 1)]
    # per body: max bag
    mb = defaultdict(int)
    for r in rounds:
        for b, v in g.R[r].items():
            if v[5] > mb[b]:
                mb[b] = v[5]
    rec['maxbag'] = {str(b): v for b, v in mb.items()}
    rec['endbag'] = {str(b): v[5] for b, v in g.R[rounds[-1]].items()}
    return rec


def work(args):
    base, ent = args
    try:
        r = extract(base, ent, load_geo())
        return json.dumps(r) if r else json.dumps({'base': base, 'skip': 1})
    except Exception as e:
        return json.dumps({'base': base, 'err': traceback.format_exc()[-800:]})


if __name__ == '__main__':
    import multiprocessing as mp
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    only = sys.argv[2] if len(sys.argv) > 2 else None
    idx = load_index()
    done = set()
    if os.path.exists(OUT) and not only:
        for l in open(OUT, encoding='utf-8'):
            j = json.loads(l)
            if 'err' not in j and 'skip' not in j:
                done.add(j['base'])
    items = [(b, e) for b, e in sorted(idx.items()) if b not in done and (not only or only in b)]
    items = [(b, e) for b, e in items if os.path.exists(f"{CACHE}/vecon/d/{b[:-8]}.json.gz")]
    print('to do', len(items), flush=True)
    outp = OUT if not only else f'{CACHE}/vecon/games_test.jsonl'
    with mp.Pool(n) as pool, open(outp, 'a' if not only else 'w', encoding='utf-8') as fo:
        for s in pool.imap_unordered(work, items, chunksize=2):
            j = json.loads(s)
            if 'base' in j and ('err' in j or 'skip' in j):
                print(s[:900], flush=True)
                if 'err' in j:
                    continue
            fo.write(s + '\n')
            fo.flush()
