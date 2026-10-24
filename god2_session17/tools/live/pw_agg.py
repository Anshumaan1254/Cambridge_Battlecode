# Aggregate tools/live/pw_casts.mjs output (ability usage per champion and slot) by group:
#   US  = HouseOfCoders in us-vs-top-10 replays, OPP = the top-10 team in those games, TT = both teams of top-vs-top games.
#   python tools/live/pw_agg.py C:/battlecode/cache/an_powers/casts.jsonl [--json OUT.json]
import json, sys, os, collections

ROOT = 'C:/battlecode/Cambridge_Battlecode/experiments/live/lists/'
KIT = {
    'Ryth': ['aoestun', 'reset'], 'VesperVale': ['reset', 'dash'], 'Vendetta': ['reset', 'dash'], 'Cassi': ['dmg', 'stun'],
    'Issac': ['reset', 'dash'], 'Stellar': ['dmg', 'aoe'], 'Prism': ['dmgstun', 'aoe'], 'Marcella': ['ereset', 'dmg'],
    'Willow': ['heal', 'reset'], 'Ren': ['dmgstun', 'dash'], 'Varg': ['reset', 'shield'], 'Tavi': ['reset', 'dmgstun'],
    'HeartOfRuin': ['shield', 'hordash'],
}
GROUPS = ['US', 'OPP', 'TT']
BK = ['fA', 'f4', 'fF', 'oA', 'e4', 'e6', 'e9', 'far']


def load_matches():
    m = {}
    for f in ['groups_matches.jsonl', 'top10_oct23/top_vs_top.jsonl']:
        for l in open(ROOT + f, encoding='utf-8'):
            j = json.loads(l)
            m.setdefault(j['matchId'][:8], j)
    return m


def team_groups(match):
    names = {('a' if t['side'] == 'a' else 'b'): t['name'] for t in match['teams']}
    if 'HouseOfCoders' in names.values():
        return [('US' if names['a'] == 'HouseOfCoders' else 'OPP'), ('US' if names['b'] == 'HouseOfCoders' else 'OPP')], names
    return ['TT', 'TT'], names


def pct(a, b):
    return f'{100 * a / b:.0f}%' if b else '-'


def main():
    path = sys.argv[1]
    out_json = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
    M = load_matches()
    games = []
    for l in open(path, encoding='utf-8'):
        try:
            games.append(json.loads(l))
        except Exception:
            pass
    # accumulators keyed (group, champ, slot)
    rate = collections.defaultdict(lambda: collections.Counter())
    ctx = collections.defaultdict(lambda: collections.Counter())  # (g, champ, slot, bucket) -> ready/cast/idle/blocked; and exposure
    expo = collections.defaultdict(lambda: collections.Counter())  # (g, champ) -> bucket turns
    tgt = collections.defaultdict(lambda: collections.Counter())
    stun = collections.defaultdict(lambda: collections.Counter())
    stun_on = collections.defaultdict(lambda: collections.Counter())
    dash = collections.defaultdict(lambda: collections.Counter())
    reset = collections.defaultdict(lambda: collections.Counter())
    shield = collections.defaultdict(lambda: collections.Counter())
    heal = collections.defaultdict(lambda: collections.Counter())
    epi = collections.defaultdict(lambda: collections.Counter())
    outc = collections.defaultdict(lambda: [0, 0, 0, 0, 0])  # n, kills, deaths, died, killedVictim
    ngames = collections.Counter()
    nbody = collections.Counter()
    for g in games:
        mid = g['file'].split('_')[-1].split('.')[0]
        match = M.get(mid)
        if not match:
            continue
        grp, names = team_groups(match)
        for t in (0, 1):
            ngames[grp[t]] += 1
        bteam = {b[0]: b[1] for b in g['bodies']}
        btype = {b[0]: b[2] for b in g['bodies']}
        G = lambda w: grp[bteam[w]]
        for b in g['bstats']:
            gr = grp[b['team']]
            ch = b['champ']
            nbody[(gr, ch)] += 1
            expo[(gr, ch)]['alive'] += b['alive']
            expo[(gr, ch)]['usable'] += b['usable']
            expo[(gr, ch)]['chan'] += b['chan']
            expo[(gr, ch)]['stun'] += b['stun']
            for k, v in b['ctx'].items():
                expo[(gr, ch)][k] += v
            for s in (0, 1):
                q = b['sl'][s]
                R = rate[(gr, ch, s)]
                R['alive'] += b['alive']; R['usable'] += b['usable']
                for k in ('ready', 'casts', 'idle', 'blocked', 'gapSum', 'gapN', 'idleAtk', 'campSafeIdle', 'idleFlee'):
                    R[k] += q[k]
                for bk, arr in q['c'].items():
                    C = ctx[(gr, ch, s, bk)]
                    C['ready'] += arr[0]; C['cast'] += arr[1]; C['idle'] += arr[2]; C['blocked'] += arr[3]
        for c in g['casts']:
            w = c['w']; gr = G(w); ch = btype[w]; s = c['slot']; kind = c['kind']
            key = (gr, ch, s)
            T = tgt[key]
            T['n'] += 1
            near = c.get('dE', 99)
            T['dE<=4'] += near <= 4
            T['dE<=6'] += near <= 6
            if c.get('ep') is not None:
                T['inFight'] += 1
            if kind in ('dmg', 'stun', 'dmgstun', 'aoestun', 'aoe', 'hordash'):
                cls = c.get('cls', '?')
                T['cls_' + cls] += 1
                if cls == 'camp':
                    T['camp_dE<=6'] += near <= 6
                    T['camp_dE<=9'] += near <= 9
                if cls == 'champ':
                    T['champHits'] += c.get('nCh', 0)
                    T['multi'] += c.get('nCh', 0) >= 2
                if kind in ('aoe', 'aoestun', 'hordash') and cls == 'camp':
                    T['campHits'] += c.get('nCamp', 0)
            if kind in ('stun', 'dmgstun', 'aoestun', 'hordash'):
                for st in c.get('stun', []):
                    S = stun[key]
                    S['n'] += 1; S['after'] += st['after']; S['chan'] += 1 if st['chan'] else 0
                    S['focus'] += st['focus'] > 0; S['kill3'] += st['kill3']
                    S['tgems>=10'] += st['tgems'] >= 10; S['thp<0.5'] += st['thp'] < 0.5
                    ep = c.get('ep')
                    S['ep_open'] += ep is not None and ep <= 1
                    stun_on[key][st['tt']] += 1
            if kind in ('dash', 'hordash') and c.get('dash'):
                d = c['dash']
                D = dash[key]
                D['n'] += 1
                db, da = d['dBefore'], d['dAfter']
                if db > 8:
                    cl = 'travel'
                    if d['campAfter'] < d['campBefore']:
                        D['travel_toCamp'] += 1
                elif da < db:
                    cl = 'engage'
                elif da > db:
                    cl = 'escape'
                else:
                    cl = 'lateral'
                D[cl] += 1
                D['dist2'] += d['dist'] == 2
                if c.get('cls') == 'champ':  # Heart of Ruin landing on a champion
                    D['strike'] += 1
                    D['strike_mvBefore'] += c.get('mvBefore', 0) > 0
                    D['strike_atkAfter'] += c.get('atkAfter', 0) > 0
                    D['strike_dE' + str(min(db, 5))] += 1
                if cl in ('engage', 'escape', 'lateral'):
                    D['near_mvBefore'] += c.get('mvBefore', 0) > 0
                    D['near_mvAfter'] += c.get('mvAfter', 0) > 0
                if cl == 'engage':
                    D['engage_atkAfter'] += c.get('atkAfter', 0) > 0
                    D['engage_land<=1'] += d['nearAfter'] <= 1
                    D['engage_land<=3'] += d['nearAfter'] <= 3
                if cl == 'escape':
                    D['escape_hp<0.5'] += (c.get('hp') or 1) < 0.5
                if db <= 8:
                    D['near_hp_sum'] += c.get('hp') or 0
                if c.get('ep') is not None:
                    D['inFight'] += 1
            if kind in ('reset', 'ereset'):
                Rz = reset[key]
                Rz['n'] += 1
                ab, aa = c.get('atkBefore', 0), c.get('atkAfter', 0)
                if ab and aa:
                    Rz['double'] += 1
                elif aa:
                    Rz['first'] += 1
                elif ab:
                    Rz['afterOnly'] += 1
                else:
                    Rz['none'] += 1
                Rz['champTurn'] += c.get('atkChamp', 0)
                if c.get('atkChamp'):
                    Rz['champ_double'] += 1 if (ab and aa) else 0
                    Rz['champ_first'] += 1 if (aa and not ab) else 0
            if kind == 'shield':
                Sh = shield[key]
                Sh['n'] += 1
                Sh['pre'] += c.get('hitPre', 0) > 0
                Sh['post'] += (c.get('hitPost', 0) + c.get('campPost', 0)) > 0
                Sh['postChamp'] += c.get('hitPost', 0) > 0
                Sh['e4'] += near <= 4
                Sh['hp<0.5'] += (c.get('hp') or 1) < 0.5
                Sh['hp_sum'] += c.get('hp') or 0
            if kind == 'heal':
                H = heal[key]
                H['n'] += 1
                if 'allyHp' in c:
                    H['tgt'] += 1
                    H['allyHp_sum'] += c['allyHp']
                    H['miss_sum'] += c['allyMiss']
                    H['miss>=300'] += c['allyMiss'] >= 300
                    H['allyE4'] += c.get('allyE4', 0) > 0
        for e in g['episodes']:
            gr = grp[e['team']]; ch = e['champ']
            sub = e['n'] >= 2 or e['hitsBy'] + e['hitsOn'] >= 3
            for s in (0, 1):
                sl = e['slots'][s]
                key = (gr, ch, s)
                E = epi[key]
                E['ep'] += 1
                if not sub:
                    continue
                E['sub'] += 1
                E['passive'] += e['hitsBy'] == 0
                if not sl['ready']:
                    E['notReady'] += 1
                    continue
                E['ready'] += 1
                off = sl['off']
                if off is None:
                    b = 'never'
                elif off < 0:
                    b = 'pre'
                elif off <= 1:
                    b = 'open'
                else:
                    b = 'late'
                E[b] += 1
                if e['hitsBy'] == 0:
                    E[b + '_passive'] += 1  # the body never hit an enemy champion in this engagement
                early = b in ('pre', 'open')
                ub = 'early' if early else ('late' if b == 'late' else 'never')
                strat = 'ahead' if e['hpA'] >= e['hpE'] else 'behind'  # max-health sum within 6 at the start, ours vs theirs
                for o in (outc[(gr, ch, s, ub)], outc[(gr, ch, s, ub, strat)]):
                    o[0] += 1; o[1] += e['kills']; o[2] += e['deaths']; o[3] += e['died']; o[4] += e['killedVictim']
            # whole-episode outcome by who hit first
            o = outc[(gr, ch, 'first', e['first'])]
            if sub:
                o[0] += 1; o[1] += e['kills']; o[2] += e['deaths']; o[3] += e['died']; o[4] += e['killedVictim']
    res = dict(ngames=ngames, nbody={f'{k[0]}|{k[1]}': v for k, v in nbody.items()})

    def dump(name, d):
        res[name] = {'|'.join(map(str, k)): dict(v) if isinstance(v, collections.Counter) else v for k, v in d.items()}
    for name, d in [('rate', rate), ('ctx', ctx), ('expo', expo), ('tgt', tgt), ('stun', stun), ('stun_on', stun_on), ('dash', dash),
                    ('reset', reset), ('shield', shield), ('heal', heal), ('epi', epi), ('outc', outc)]:
        dump(name, d)
    if out_json:
        json.dump(res, open(out_json, 'w'), indent=0)
    report(res)


def report(res):
    ng = res['ngames']
    print('team-games per group:', dict(ng))
    champs = ['HeartOfRuin', 'Vendetta', 'VesperVale', 'Ryth', 'Marcella', 'Prism', 'Tavi', 'Varg', 'Willow', 'Cassi', 'Issac']
    R = res['rate']; C = res['ctx']; X = res['expo']
    print('\n== 1. cast rate and cooldown use (per body; usable = alive, not channelling/stunned)')
    print('champ        slot kind     grp  bodies  casts/100alive  util(casts*8/usable)  ready-idle%usable  wait-after-ready(r)  blocked%ready')
    for ch in champs:
        for s in (0, 1):
            for gr in GROUPS:
                r = R.get(f'{gr}|{ch}|{s}')
                if not r or not r.get('alive'):
                    continue
                nb = res['nbody'].get(f'{gr}|{ch}', 0)
                print(f"{ch:12s} {s}    {KIT[ch][s]:8s} {gr:4s} {nb:6d}  {100 * r['casts'] / r['alive']:14.1f}  {100 * r['casts'] * 8 / max(1, r['usable']):19.0f}%  "
                      f"{100 * r['idle'] / max(1, r['usable']):16.0f}%  {r['gapSum'] / max(1, r['gapN']):18.1f}  {pct(r['blocked'], r['ready']):>12s}")
    print('\n== 1b. exposure: share of usable turns by context (f* = in a fight: exchanged with an enemy champion in the last 2 rounds or '
          'hit earlier this round; fA attacked a champion this turn, f4 enemy within 4 and no champion attack, fF enemy farther; '
          'oA = opening attack on a champion; eN = not fighting, nearest enemy within N)')
    for ch in champs:
        for gr in GROUPS:
            x = X.get(f'{gr}|{ch}')
            if not x:
                continue
            u = max(1, x['usable'])
            print(f"{ch:12s} {gr:4s} usable/body {u / max(1, res['nbody'].get(f'{gr}|{ch}', 1)):.0f}  " + ' '.join(f'{k} {pct(x.get(k, 0), u)}' for k in BK) +
                  f"  chan {pct(x['chan'], x['alive'])} stunned {x['stun'] / max(1, res['nbody'].get(f'{gr}|{ch}', 1)):.1f}/body")
    print('\n== 1c. ready -> cast in context: cast share of ready turns (n ready turns) by bucket')
    for ch in champs:
        for s in (0, 1):
            line = []
            for gr in GROUPS:
                parts = []
                for bk in BK:
                    c = C.get(f'{gr}|{ch}|{s}|{bk}')
                    if not c or not c.get('ready'):
                        parts.append(f'{bk} -')
                        continue
                    parts.append(f"{bk} {pct(c['cast'], c['ready'])} (n{c['ready']})")
                line.append(f'{gr}: ' + ' '.join(parts))
            if any('n' in p for p in line):
                print(f'{ch:12s} {s} {KIT[ch][s]:8s} | ' + ' | '.join(line))
    print('\n== 2. targets')
    T = res['tgt']
    for ch in champs:
        for s in (0, 1):
            k = KIT[ch][s]
            for gr in GROUPS:
                t = T.get(f'{gr}|{ch}|{s}')
                if not t:
                    continue
                n = t['n']
                if k in ('dmg', 'stun', 'dmgstun', 'aoestun', 'aoe', 'hordash'):
                    print(f"{ch:12s} {s} {k:8s} {gr:4s} n {n:5d}  champ {pct(t.get('cls_champ', 0), n)}  camp {pct(t.get('cls_camp', 0), n)}  empty {pct(t.get('cls_empty', 0), n)}"
                          f"  | camp casts with enemy<=6 {pct(t.get('camp_dE<=6', 0), t.get('cls_camp', 0))} <=9 {pct(t.get('camp_dE<=9', 0), t.get('cls_camp', 0))}"
                          f"  | multi-champ {pct(t.get('multi', 0), t.get('cls_champ', 0))} | in fight {pct(t.get('inFight', 0), n)}")
    print('\n== 2b. dashes (engage = closer to the nearest enemy within 8, escape = farther, travel = no enemy within 8)')
    D = res['dash']
    for ch in champs:
        for s in (0, 1):
            for gr in GROUPS:
                d = D.get(f'{gr}|{ch}|{s}')
                if not d:
                    continue
                n = d['n']
                near = n - d.get('travel', 0)
                print(f"{ch:12s} {s} {KIT[ch][s]:8s} {gr:4s} n {n:5d}  travel {pct(d.get('travel', 0), n)} (to camp {pct(d.get('travel_toCamp', 0), d.get('travel', 0))})  engage {pct(d.get('engage', 0), n)}  escape {pct(d.get('escape', 0), n)}  lateral {pct(d.get('lateral', 0), n)}"
                      f"  | engage+hit same turn {pct(d.get('engage_atkAfter', 0), d.get('engage', 0))} land adj {pct(d.get('engage_land<=1', 0), d.get('engage', 0))}  escape hp<0.5 {pct(d.get('escape_hp<0.5', 0), d.get('escape', 0))}"
                      f"  | near-enemy dashes: walk before {pct(d.get('near_mvBefore', 0), near)} walk after {pct(d.get('near_mvAfter', 0), near)}")
                if d.get('strike'):
                    st = d['strike']
                    print(f"{'':12s}   strikes on champions {st} ({pct(st, n)}): walked first {pct(d.get('strike_mvBefore', 0), st)}, attack after {pct(d.get('strike_atkAfter', 0), st)}, "
                          f"enemy dist at cast " + ' '.join(f"{k} {pct(d.get('strike_dE' + str(k), 0), st)}" for k in range(1, 6)))
    print('\n== 2c. resets (double = attack, reset, attack in one turn; first = reset then attack; none = no attack after)')
    Z = res['reset']
    for ch in champs:
        for s in (0, 1):
            for gr in GROUPS:
                z = Z.get(f'{gr}|{ch}|{s}')
                if not z:
                    continue
                n = z['n']
                print(f"{ch:12s} {s} {KIT[ch][s]:8s} {gr:4s} n {n:5d}  double {pct(z.get('double', 0), n)}  first {pct(z.get('first', 0), n)}  afterOnly {pct(z.get('afterOnly', 0), n)}  none {pct(z.get('none', 0), n)}  | on champion turns {pct(z.get('champTurn', 0), n)} (double {pct(z.get('champ_double', 0), z.get('champTurn', 0))})")
    print('\n== 2d. shields')
    for k, z in res['shield'].items():
        n = z['n']
        print(f"{k:28s} n {n:5d}  hit in r-1..r {pct(z['pre'], n)}  hit in next 5r {pct(z['post'], n)} (by champ {pct(z['postChamp'], n)})  enemy<=4 {pct(z['e4'], n)}  hp<0.5 {pct(z['hp<0.5'], n)} mean hp {z['hp_sum'] / n:.2f}")
    print('\n== 2e. heals')
    for k, z in res['heal'].items():
        n = z['n']
        t = max(1, z.get('tgt', 0))
        print(f"{k:28s} n {n:5d}  ally hp {z.get('allyHp_sum', 0) / t:.2f}  missing {z.get('miss_sum', 0) / t:.0f}  missing>=300 {pct(z.get('miss>=300', 0), t)}  enemy near ally {pct(z.get('allyE4', 0), t)}")
    print('\n== 3. stuns')
    for k, z in res['stun'].items():
        n = z['n']
        on = res['stun_on'][k]
        top = ', '.join(f'{a} {pct(b, n)}' for a, b in sorted(on.items(), key=lambda x: -x[1])[:5])
        print(f"{k:28s} n {n:5d}  after-target-acted {pct(z['after'], n)}  on channel {pct(z['chan'], n)}  followed up {pct(z['focus'], n)}  kill<=3r {pct(z['kill3'], n)}  target hp<0.5 {pct(z['thp<0.5'], n)}  fight-opening {pct(z['ep_open'], n)} | {top}")
    print('\n== 3b. engagements (substantive: >= 2 exchange rounds or >= 3 hits): slot ready at start -> used pre (-2..-1) / open (0..1) / late (2+) / never')
    E = res['epi']
    for ch in champs:
        for s in (0, 1):
            for gr in GROUPS:
                e = E.get(f'{gr}|{ch}|{s}')
                if not e or not e.get('sub'):
                    continue
                rd = max(1, e.get('ready', 0))
                print(f"{ch:12s} {s} {KIT[ch][s]:8s} {gr:4s} eps {e['sub']:5d} ready {pct(e.get('ready', 0), e['sub'])}  pre {pct(e.get('pre', 0), rd)} open {pct(e.get('open', 0), rd)} late {pct(e.get('late', 0), rd)} never {pct(e.get('never', 0), rd)}"
                      f"  | passive eps (never hit a champion) {pct(e.get('passive', 0), e['sub'])}, of 'never' {pct(e.get('never_passive', 0), e.get('never', 0))}")
    print('\n== 4. outcome within 15 rounds by slot use (ready at start): n, kills/ep, deaths/ep, self died, victim killed')
    O = res['outc']
    for ch in champs:
        for s in (0, 1):
            for gr in GROUPS:
                parts = []
                for b in ('early', 'late', 'never'):
                    o = O.get(f'{gr}|{ch}|{s}|{b}')
                    if not o or not o[0]:
                        continue
                    parts.append(f'{b} n{o[0]} k {o[1] / o[0]:.2f} d {o[2] / o[0]:.2f} died {pct(o[3], o[0])} vk {pct(o[4], o[0])}')
                if parts:
                    print(f"{ch:12s} {s} {KIT[ch][s]:8s} {gr:4s} " + ' | '.join(parts))
    print('\n== 4a. same, stratified by max-health sum within 6 at the start (ahead = ours >= theirs)')
    for ch in champs:
        for s in (0, 1):
            for gr in GROUPS:
                for st in ('ahead', 'behind'):
                    parts = []
                    for b in ('early', 'late', 'never'):
                        o = O.get(f'{gr}|{ch}|{s}|{b}|{st}')
                        if not o or not o[0]:
                            continue
                        parts.append(f'{b} n{o[0]} k {o[1] / o[0]:.2f} d {o[2] / o[0]:.2f} died {pct(o[3], o[0])} net {(o[1] - o[2]) / o[0]:+.2f}')
                    if parts:
                        print(f"{ch:12s} {s} {KIT[ch][s]:8s} {gr:4s} {st:6s} " + ' | '.join(parts))
    print('\n== 4b. outcome by who hit first in the engagement')
    for ch in champs:
        for gr in GROUPS:
            parts = []
            for b in ('me', 'them', 'both'):
                o = O.get(f'{gr}|{ch}|first|{b}')
                if not o or not o[0]:
                    continue
                parts.append(f'{b} n{o[0]} k {o[1] / o[0]:.2f} d {o[2] / o[0]:.2f} died {pct(o[3], o[0])}')
            if parts:
                print(f'{ch:12s} {gr:4s} ' + ' | '.join(parts))


if __name__ == '__main__':
    main()
