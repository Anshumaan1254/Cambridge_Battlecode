"""verify_items: independent per-game pass over tools/live/fightdump.mjs dumps (abilities, stuns, tributes, locks, deaths, Prism).
   python tools/top2/verify_items/vd.py LIST.txt OUT.jsonl [workers]      (resumes: skips files already in OUT)
One JSON line per dump with per-body facts; aggregation is done by vagg_*.py with the study-team index."""
import json, gzip, os, sys, collections, bisect
from concurrent.futures import ProcessPoolExecutor

CD = 8  # measured: minimum gap between two casts of the same slot by the same body is 8 rounds
# slot kinds (engine probe experiments/results/probe_v3_0_4/champions_engine_3_0_4.txt)
KIT = {
    'Ryth': {0: 'aoestun', 1: 'reset'}, 'VesperVale': {0: 'reset', 1: 'dash'}, 'Vendetta': {0: 'reset', 1: 'dash'},
    'Cassi': {0: 'dmg', 1: 'stun'}, 'Issac': {0: 'reset', 1: 'dash'}, 'Stellar': {0: 'dmg', 1: 'aoe'},
    'Prism': {0: 'dmgstun', 1: 'aoe'}, 'Marcella': {0: 'ereset', 1: 'dmg'}, 'Willow': {0: 'heal', 1: 'reset'},
    'Ren': {0: 'stun', 1: 'dash'}, 'Varg': {0: 'reset', 1: 'shield'}, 'Tavi': {0: 'reset', 1: 'dmgstun'},
    'HeartOfRuin': {0: 'shield', 1: 'hordash'},
}
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def bucket_bag(b):
    return '0' if b == 0 else '1-24' if b < 25 else '25-49' if b < 50 else '50-99' if b < 100 else '100-199' if b < 200 else '200+'


def proc(path):
    d = json.load(gzip.open(path))
    meta = d['meta']
    bodies = meta['bodies']
    team = {b['index']: b['team'] for b in bodies}
    typ = {b['index']: b['type'] for b in bodies}
    final = meta['finalRound']
    # rounds: later entries override the stray draft-phase entry at R[0]
    R = {}
    for row in d['R']:
        R[row[0]] = {c[0]: c for c in row[3]}
    rounds = sorted(R)
    def st(r, b):
        x = R.get(r)
        return x.get(b) if x else None
    ev = sorted(d['ev'], key=lambda e: e['q'])
    by = collections.defaultdict(list)
    for e in ev:
        if 'who' in e: by[e['who']].append(e)
    dmg = d['dmg']; cdmg = d['cdmg']; stun = d['stun']
    out = {'file': os.path.basename(path).replace('.json.gz', ''), 'final': final, 'outcome': meta.get('outcome'),
           'bodies': [[b['index'], b['team'], b['type']] for b in bodies]}

    # ---------- per body basics ----------
    alive_r = collections.Counter();
    for r in rounds:
        if r < 1: continue
        for b, c in R[r].items():
            if c[5]: alive_r[b] += 1
    deaths = []
    for e in ev:
        if e['k'] == 'Death':
            k = e.get('by')
            deaths.append([e['r'], e['who'], e.get('bag', 0), k if isinstance(k, int) else -1, e.get('step')])
    champ_dmg = collections.Counter(); champ_dmg_taken = collections.Counter()
    for q, r, a, v, amt, kind, slot in dmg:
        if a >= 0 and a != v and team.get(a) != team.get(v):
            champ_dmg[a] += amt; champ_dmg_taken[v] += amt
    cps = {}
    for cp in (300, 400, 600, 1000):
        if cp in R:
            cps[cp] = {b: [c[4], c[5], c[6], c[7]] for b, c in R[cp].items()}  # maxHp, alive, gems, gold
    out['alive'] = {b: alive_r[b] for b in team}
    out['deaths'] = deaths
    out['cdmg_champ'] = {b: champ_dmg[b] for b in team}
    out['cdmg_taken'] = {b: champ_dmg_taken[b] for b in team}
    out['cp'] = cps

    # ---------- channels: tributes and recalls ----------
    tribs = []
    recalls = []  # [who, r0, q0, outcome, r_end, q_end, spam]
    stun_by_victim = collections.defaultdict(list)
    for s in stun:
        stun_by_victim[s[3]].append(s)
    locks_ev = [e for e in ev if e['k'] == 'Place altar lock']
    for b in team:
        E = by.get(b, [])
        Sv = stun_by_victim.get(b, [])
        for i, e in enumerate(E):
            if e['k'] not in ('Submit gems', 'Recall'):
                continue
            q0, r0 = e['q'], e['r']
            # candidate terminators
            term = None
            for f in E[i + 1:]:
                if f['k'] in ('Gems submitted', 'Banked') and e['k'] == 'Submit gems':
                    term = ('done', f['q'], f['r'], None); break
                if f['k'] == 'Respawn' and e['k'] == 'Recall':
                    term = ('done', f['q'], f['r'], None); break
                if f['k'] == 'Cancel channel':
                    term = ('cancel', f['q'], f['r'], None); break
                if f['k'] == 'Death':
                    term = ('death', f['q'], f['r'], f.get('by')); break
                if f['k'] in ('CaptureGems',):
                    continue
                term = ('other:' + f['k'], f['q'], f['r'], None); break
            # stun before terminator
            for s in Sv:
                if s[0] > q0 and (term is None or s[0] < term[1] or (s[0] == term[1] and term[0] == 'death')):
                    if term is None or s[0] <= term[1]:
                        term = ('stun', s[0], s[1], s[2]); break
            if e['k'] == 'Submit gems':
                altar = tuple(e['to'])
                for L in locks_ev:
                    if L['q'] > q0 and team.get(L['who']) != team[b] and tuple(L['to']) == altar and (term is None or L['q'] < term[1]):
                        term = ('lock', L['q'], L['r'], L['who']); break
            if term is None:
                term = ('end', None, final, None)
            if e['k'] == 'Submit gems':
                me = st(r0, b)
                bag = me[6] if me else 0
                pos = (me[1], me[2]) if me else None
                near = []
                for rr in (r0 - 1, r0):
                    best = 99
                    x = R.get(rr, {})
                    mm = x.get(b)
                    for o, c in x.items():
                        if team.get(o) != team[b] and c[5] and mm:
                            best = min(best, cheb((mm[1], mm[2]), (c[1], c[2])))
                    near.append(best)
                banked = None
                tribs.append({'who': b, 'r0': r0, 'q0': q0, 'altar': list(e['to']), 'bag': bag, 'dmin_prev': near[0], 'dmin': near[1],
                              'out': term[0], 'r1': term[2], 'q1': term[1], 'by': term[3]})
            else:
                # spam: cancelled at the body's next turn (next round)
                spam = term[0] == 'cancel' and term[2] == r0 + 1
                recalls.append([b, r0, q0, term[0], term[2], term[1], 1 if spam else 0])
    out['tribs'] = tribs
    out['recalls_n'] = {b: sum(1 for x in recalls if x[0] == b) for b in team}
    out['recalls_spam'] = {b: sum(x[6] for x in recalls if x[0] == b) for b in team}

    # ---------- stuns with victim state ----------
    trib_iv = collections.defaultdict(list)
    for t in tribs:
        trib_iv[t['who']].append((t['q0'], t['q1'] if t['q1'] is not None else 1 << 60, t['bag'], t['out']))
    rec_iv = collections.defaultdict(list)
    for x in recalls:
        rec_iv[x[0]].append((x[2], x[5] if x[5] is not None else 1 << 60, x[6], x[1]))
    stuns = []
    for q, r, a, v in stun:
        if a < 0 or team.get(a) == team.get(v):
            stuns.append([r, a, v, 'camp' if a < 0 else 'ally', 0]); continue
        state, bag = 'none', 0
        for (qa, qb, bg, o) in trib_iv.get(v, []):
            if qa < q <= qb:
                state, bag = 'trib', bg; break
        if state == 'none':
            for (qa, qb, sp, rr0) in rec_iv.get(v, []):
                if qa < q <= qb:
                    state = 'recall_spam' if sp or (qb >= q and r <= rr0 + 1) else 'recall'
                    break
        stuns.append([r, a, v, state, bag])
    out['stuns'] = stuns

    # ---------- locks ----------
    atk_alt = collections.defaultdict(list)  # altar -> [(q, r, team, who)]
    altars = set(tuple(L['to']) for L in locks_ev) | set(tuple(t['altar']) for t in tribs)
    for e in ev:
        if e['k'] == 'Attack' and 'to' in e and tuple(e['to']) in altars:
            atk_alt[tuple(e['to'])].append((e['q'], e['r'], team[e['who']], e['who']))
    gs = collections.defaultdict(list)
    for e in ev:
        if e['k'] == 'Gems submitted' and 'to' in e:
            gs[tuple(e['to'])].append((e['q'], e['r'], team[e['who']]))
    locks = []
    for L in locks_ev:
        alt = tuple(L['to']); tm = team[L['who']]
        # cleared after 5 enemy attacks on the altar tile (rules: removed by five basic attacks)
        n = 0; clear = None; turns = set()
        for (q, r, t2, w) in atk_alt.get(alt, []):
            if q > L['q'] and t2 != tm:
                n += 1; turns.add((w, r))
                if n >= 5:
                    clear = (q, r); break
        own3 = any(t['q0'] > L['q'] and t['r0'] <= L['r'] + 3 and team[t['who']] == tm and tuple(t['altar']) == alt for t in tribs)
        qend = clear[0] if clear else 1 << 60
        banks = [g for g in gs.get(alt, []) if L['q'] < g[0] < qend and g[2] == tm]
        x = R.get(L['r'] - 1, {}); me = x.get(L['who'])
        en8 = 99
        if me:
            for o, c in x.items():
                if team.get(o) != tm and c[5]: en8 = min(en8, cheb((me[1], me[2]), (c[1], c[2])))
        canc = [t['bag'] for t in tribs if t['out'] == 'lock' and t['q1'] == L['q']]
        locks.append({'who': L['who'], 'team': tm, 'r': L['r'], 'q': L['q'], 'altar': list(alt), 'own3': own3,
                      'life': (clear[1] - L['r']) if clear else None, 'cens': final - L['r'], 'banks': len(banks),
                      'en_turns': len(turns), 'en_atk': n, 'dmin': en8, 'cancelled': canc, 'clear_q': clear[0] if clear else None})
    # lock placed while an enemy lock on that altar stands (placed earlier, not yet cleared)
    for Lk in locks:
        Lk['on_enemy_lock'] = any(o['team'] != Lk['team'] and o['altar'] == Lk['altar'] and o['q'] < Lk['q'] and
                                  (o['clear_q'] is None or o['clear_q'] > Lk['q']) for o in locks)
    out['locks'] = locks

    # ---------- abilities: readiness by context ----------
    casts = collections.defaultdict(list)  # (body) -> [(r, q, slot)]
    for e in ev:
        if e['k'] == 'Cast ability':
            casts[e['who']].append((e['r'], e['q'], e['slot']))
    # champion-vs-champion damage rounds per body (dealt or taken), with q
    fight_q = collections.defaultdict(list)
    for q, r, a, v, amt, kind, slot in dmg:
        if a >= 0 and v >= 0 and team.get(a) != team.get(v):
            fight_q[a].append((r, q)); fight_q[v].append((r, q))
    for b in fight_q: fight_q[b].sort()
    camp_r = collections.defaultdict(set)
    for q, r, a, ci, amt in cdmg:
        camp_r[a].add(r)
    # per (body, slot): counts[ctx] = [ready_turns, casts_when_ready]
    deaths_by = collections.defaultdict(list)
    for dd in deaths: deaths_by[dd[1]].append(dd[0])
    respawn_r = collections.defaultdict(list)
    first_ev_q = {}
    for b, E in by.items():
        for e in E:
            first_ev_q.setdefault((b, e['r']), e['q'])
    # channel rounds (inside a tribute or recall channel that continues through the turn)
    chan = collections.defaultdict(set)
    for t in tribs:
        r1 = t['r1'] if t['r1'] is not None else final
        for r in range(t['r0'] + 1, r1):
            chan[t['who']].add(r)
    for x in recalls:
        r1 = x[4] if x[4] is not None else final
        for r in range(x[1] + 1, r1):
            chan[x[0]].add(r)
    ab = {}
    seqs = []
    for b in team:
        T = typ[b]
        kit = KIT.get(T, {})
        cl = casts.get(b, [])
        cast_r = {}
        for (r, q, s) in cl:
            cast_r.setdefault((r, s), q)
        fq = fight_q.get(b, [])
        fr = [x[0] for x in fq]
        cnt = {s: collections.defaultdict(lambda: [0, 0]) for s in kit}
        last = {s: -999 for s in kit}
        alive_prev = False
        prev_dead = True
        for r in range(1, final + 1):
            c_prev = st(r - 1, b) if r > 1 else st(r, b)
            c_now = st(r, b)
            if c_prev is None or c_now is None:
                continue
            alive_start = bool(c_prev[5])
            if not alive_start:
                # died: cooldowns of the next life start fresh
                for s in last: last[s] = -999
                continue
            stunned = bool(c_prev[9])
            if stunned or r in chan[b]:
                for s in kit:
                    if (r, s) in cast_r: last[s] = r
                continue
            # context
            fqb = first_ev_q.get((b, r), 1 << 60)
            lo = bisect.bisect_left(fr, r - 2)
            F = False
            for k in range(lo, len(fq)):
                rr, qq = fq[k]
                if rr > r: break
                if rr < r or qq < fqb:
                    F = True; break
            if F: ctx = 'F'
            else:
                me = c_prev
                N = False
                for o, c in R[r - 1].items() if (r - 1) in R else []:
                    if team.get(o) != team[b] and c[5] and cheb((me[1], me[2]), (c[1], c[2])) <= 5:
                        N = True; break
                if N: ctx = 'N'
                elif (r - 1) in camp_r.get(b, ()) or (r - 2) in camp_r.get(b, ()): ctx = 'C'
                elif r in camp_r.get(b, ()): ctx = 'C0'  # camp hit only in this round (possibly by the cast itself)
                else: ctx = 'O'
            for s in kit:
                ready = r - last[s] >= CD
                did = (r, s) in cast_r
                if ready:
                    cnt[s][ctx][0] += 1
                    if did: cnt[s][ctx][1] += 1
                if did: last[s] = r
        ab[b] = {s: {k: v for k, v in cnt[s].items()} for s in kit}
        # champion-attack turns: rounds with a basic attack (kind 5) that hurt an enemy champion
        atk_rounds = {}
        for q, r, a, v, amt, kind, slot in dmg:
            if a == b and kind == 5 and v >= 0 and team.get(v) != team[b]:
                atk_rounds.setdefault(r, []).append(q)
        reset_slot = next((s for s, k in kit.items() if k in ('reset', 'ereset')), None)
        dash_slot = next((s for s, k in kit.items() if k in ('dash', 'hordash')), None)
        # readiness of the reset slot at turn start
        if reset_slot is not None and atk_rounds:
            lastc = -999
            rs_cast = sorted(set(r for (r, q, s) in cl if s == reset_slot))
            death_rs = sorted(deaths_by.get(b, []))
            ptr = 0
            Eb = by.get(b, [])
            ev_by_r = collections.defaultdict(list)
            for e in Eb: ev_by_r[e['r']].append(e)
            dmg_q = {}
            for q, r, a, v, amt, kind, slot in dmg:
                if a == b and v >= 0 and team.get(v) != team[b]:
                    dmg_q.setdefault(q, []).append(v)
            for r in sorted(atk_rounds):
                # last reset cast before round r in this life
                prevc = [x for x in rs_cast if x < r]
                lc = prevc[-1] if prevc else -999
                dprev = [x for x in death_rs if x < r]
                if dprev and dprev[-1] > lc: lc = -999
                ready = r - lc >= CD
                used = (r, reset_slot) in cast_r
                # letters
                L = []
                for e in sorted(ev_by_r[r], key=lambda e: e['q']):
                    k = e['k']
                    if k == 'Move': L.append('M')
                    elif k == 'Cast ability':
                        L.append('R' if e['slot'] == reset_slot else 'D' if e['slot'] == dash_slot else 'C')
                    elif k == 'Attack':
                        L.append('A' if e['q'] in dmg_q else 'a')
                    elif k == 'Recall': L.append('r')
                    elif k == 'Submit gems': L.append('s')
                seqs.append([b, r, 1 if ready else 0, 1 if used else 0, ''.join(L)])
    out['ab'] = ab
    out['atkseq'] = seqs

    # ---------- Prism casts: damage by bag ----------
    pr = []
    dq = collections.defaultdict(list)
    for q, r, a, v, amt, kind, slot in dmg:
        if kind == 6: dq[(a, q)].append((v, amt))
    cq = collections.defaultdict(int)
    for q, r, a, ci, amt in cdmg:
        cq[(a, q)] += amt
    for b in team:
        if typ[b] != 'Prism': continue
        for (r, q, s) in casts.get(b, []):
            me = st(r - 1, b) or st(r, b)
            bag = me[6] if me else 0
            ch = sum(amt for v, amt in dq.get((b, q), []) if v >= 0 and team.get(v) != team[b])
            nv = sum(1 for v, amt in dq.get((b, q), []) if v >= 0 and team.get(v) != team[b])
            pr.append([b, r, s, bag, ch, nv, cq.get((b, q), 0)])
    out['prism'] = pr
    return out


def main():
    lst, outp = sys.argv[1], sys.argv[2]
    w = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    files = [l.strip() for l in open(lst, encoding='utf-8') if l.strip()]
    done = set()
    if os.path.exists(outp):
        for l in open(outp, encoding='utf-8'):
            try: done.add(json.loads(l)['file'])
            except Exception: pass
    files = [f for f in files if os.path.basename(f).replace('.json.gz', '') not in done]
    with ProcessPoolExecutor(w) as ex, open(outp, 'a', encoding='utf-8') as fo:
        for f, res in zip(files, ex.map(safe, files)):
            fo.write(json.dumps(res) + '\n'); fo.flush()
    print('done', len(files))


def safe(f):
    try:
        return proc(f)
    except Exception as e:
        import traceback
        return {'file': os.path.basename(f).replace('.json.gz', ''), 'err': traceback.format_exc()[-500:]}


if __name__ == '__main__':
    main()
