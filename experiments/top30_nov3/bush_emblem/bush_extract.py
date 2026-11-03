#!/usr/bin/env python3
"""Bush use per game, joined to the fights stream's fight / death / retreat rows (same definitions as fights/extract2.py).

Usage: nice -n 19 python3 -I bush_extract.py top|our      -> out/<ds>_bush.jsonl (one row per game)
For each game of fights/out/<ds>_games.jsonl: load dec + map JSON, bush tiles ('"'), 8-connected bush clusters, then
  fights : opener / target in a bush at round start-1, opener in a bush in any of start-3..start-1 ('from bush'),
           hidden opener = opener in a bush cluster the target is not in (the target cannot see it, wards aside)
  deaths : killer (killer_body) in a bush in any of r-3..r-1; victim in a bush; bag carried
  retreats: body not in a bush at r, in one at some of r+1..r+3 ('into bush'); died8
  presence: per body alive rounds, bush rounds, bush rounds with an enemy within 6 ('contact'), open rounds with an enemy
           within 6, stationary bush rounds ('hold') within 5 of an altar / camp tile, and with an enemy within 8
"""
import json, os, sys
from collections import defaultdict

TOP = '/home/claude/cambridge_battlecode/experiments/top30_nov3'
OUR = '/home/claude/cambridge_battlecode/experiments/ladder_nov2'
POOL = '/home/claude/data/mapjson_pool'
FO = f'{TOP}/fights/out'
OUT = f'{TOP}/bush_emblem/out'


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def paths(ds, g):
    mid = g['mid']
    if ds == 'top':
        fn = f"{g['map']}_{mid[:8]}"
        mj = f'{TOP}/mj/{fn}.json'
        if not os.path.exists(mj):
            mj = f"{POOL}/{g['map']}.json"
        return f'{TOP}/dec/{fn}.json', mj
    return f'{OUR}/dec/{mid}.json', f'{OUR}/mj/{mid}.json'


def rows_by_mid(fn):
    out = defaultdict(list)
    for l in open(fn):
        r = json.loads(l)
        out[r['mid']].append(r)
    return out


def main():
    ds = sys.argv[1]
    os.makedirs(OUT, exist_ok=True)
    games = [json.loads(l) for l in open(f'{FO}/{ds}_games.jsonl')]
    F = rows_by_mid(f'{FO}/{ds}_fights.jsonl')
    D = rows_by_mid(f'{FO}/{ds}_deaths.jsonl')
    R = rows_by_mid(f'{FO}/{ds}_retreats.jsonl')
    done = set()
    ofn = f'{OUT}/{ds}_bush.jsonl'
    if os.path.exists(ofn):
        done = {json.loads(l)['mid'] for l in open(ofn)}
    fo = open(ofn, 'a')
    for gi, g in enumerate(games):
        if g['mid'] in done:
            continue
        dec, mj = paths(ds, g)
        if not (os.path.exists(dec) and os.path.exists(mj)):
            continue
        try:
            d = json.load(open(dec))
            mp = json.load(open(mj))
        except Exception as ex:  # noqa
            print('ERR', g['mid'], ex, file=sys.stderr)
            continue
        W, H, rows = mp['width'], mp['height'], mp['rows']
        bush = {(x, y) for y in range(H) for x in range(W) if rows[y][x] == '"'}
        obj = [(x, y) for y in range(H) for x in range(W) if rows[y][x] == 'A'] + [(c['x'], c['y']) for c in d['meta']['camps']]
        objset = set()
        for (ox, oy) in obj:
            for dx in range(-5, 6):
                for dy in range(-5, 6):
                    objset.add((ox + dx, oy + dy))
        # 8-connected bush clusters
        cl = {}
        k = 0
        for t in bush:
            if t in cl:
                continue
            st = [t]
            cl[t] = k
            while st:
                x, y = st.pop()
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        n = (x + dx, y + dy)
                        if n in bush and n not in cl:
                            cl[n] = k
                            st.append(n)
            k += 1
        team = {b['index']: b['team'] for b in d['meta']['bodies']}
        P = {}  # r -> body -> (x,y) alive only
        for rr in d['rounds'][1:]:
            P[rr['r']] = {c[0]: (c[3], c[4]) for c in rr['ch'] if c[7]}
        final = d['meta']['finalRound']

        def pos(r, b):
            return P.get(r, {}).get(b)

        def inb(r, b):
            p = pos(r, b)
            return p is not None and p in bush

        out = {'mid': g['mid'], 'map': g['map'], 'ver': g.get('ver'), 'we': g.get('we'), 'res': [t['result'] for t in g['teams']],
               'rating': [t.get('rating') for t in g['teams']], 'bush_frac': g['mf']['bush_frac'], 'area': g['mf']['area'],
               'nbush': len(bush), 'fights': [], 'deaths': [], 'retreats': [], 'pres': {}}
        for f in F.get(g['mid'], []):
            s, a, t = f['start'], f['opener'], f['target']
            pa, pt = pos(s - 1, a), pos(s - 1, t)
            a_in = pa is not None and pa in bush
            t_in = pt is not None and pt in bush
            a_from = any(inb(r, a) for r in range(s - 3, s))
            hidden = a_in and not (t_in and cl.get(pt) == cl.get(pa))
            # any participant of each side in a bush at s-1
            pb = f.get('part_bodies', {})
            side_in = {}
            for tt in ('0', '1'):
                side_in[tt] = sum(1 for x in pb.get(tt, []) if inb(s - 1, int(x.split(':')[0])))
            out['fights'].append({'fid': f['fid'], 's': s, 'first': f['first'], 'win': f['win'], 'exch': f['exchange'],
                                  'a_in': a_in, 't_in': t_in, 'a_from': a_from, 'hidden': hidden, 'side_in': side_in,
                                  'opener': a, 'target': t, 'oc': f['opener_champ'], 'tc': f['target_champ'],
                                  'sh': f.get('shards'), 'dead': f.get('dead'), 'num': f.get('num'), 'approach': f.get('approach')})
        for x in D.get(g['mid'], []):
            r, b, kb = x['r'], x['body'], x.get('killer_body')
            k_in = kb is not None and any(inb(rr, kb) for rr in range(r - 3, r))
            k_in1 = kb is not None and inb(r - 1, kb)
            v_in = inb(r - 1, b)
            out['deaths'].append({'r': r, 't': x['t'], 'body': b, 'champ': x['champ'], 'cause': x['cause'], 'kb': kb,
                                  'k_in': k_in, 'k_in1': k_in1, 'v_in': v_in, 'bag': x.get('bag', 0), 'killer': x.get('killer')})
        for x in R.get(g['mid'], []):
            r, b = x['r'], x['body']
            if inb(r, b):
                kind = 'was_in'
            elif any(inb(rr, b) for rr in range(r + 1, r + 4)):
                kind = 'into'
            else:
                kind = 'open'
            out['retreats'].append({'r': r, 't': x['t'], 'body': b, 'kind': kind, 'died8': x.get('died8'), 'pw': x.get('pw_ratio'),
                                    'hp': x.get('hp'), 'gems': x.get('gems')})
        pres = defaultdict(lambda: [0] * 8)  # alive, bush, bush_contact, open_contact, hold_obj, hold_contact, ward_bush, wards
        prev = {}
        for r in range(1, final + 1):
            cur = P.get(r)
            if not cur:
                continue
            for b, p in cur.items():
                v = pres[b]
                v[0] += 1
                ib = p in bush
                en = min((cheb(p, q) for j, q in cur.items() if team[j] != team[b]), default=99)
                if ib:
                    v[1] += 1
                    if en <= 6:
                        v[2] += 1
                    if prev.get(b) == p:
                        if p in objset:
                            v[4] += 1
                        if en <= 8:
                            v[5] += 1
                elif en <= 6:
                    v[3] += 1
            prev = cur
        for e in d['events']:
            if e['k'] == 'Place ward' and e.get('who') is not None:
                v = pres[e['who']]
                v[7] += 1
                v[6] += tuple(e['to']) in bush
        out['pres'] = {str(b): v for b, v in pres.items()}
        out['team'] = {str(b): t for b, t in team.items()}
        out['types'] = {str(b['index']): b['type'] for b in d['meta']['bodies']}
        fo.write(json.dumps(out) + '\n')
        fo.flush()
        if gi % 20 == 0:
            print(ds, gi, len(games), file=sys.stderr, flush=True)


if __name__ == '__main__':
    main()
