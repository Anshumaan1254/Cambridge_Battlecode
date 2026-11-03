#!/usr/bin/env python3
"""Draft fingerprints of the top-30 (lists/<id8>.jsonl, last 400 ranked games each) and of us (ladder_nov2/matches_me.jsonl,
last 400 ranked). Map classes from draft_bank/out/map_features.csv (+ islands / bush from objectives mapcls).
Adaptation test: information gain of pick k (k>=2) about the opponent's revealed picks 1..k-1, given map + own earlier picks,
minus the same gain with opponent drafts shuffled among the team's games on that map (20 shuffles). >0 = reacts to opponent.
   nice -n 19 python3 -I draft.py -> draft_out.txt, draft_team.json"""
import json, os, csv, math, random
from collections import Counter, defaultdict
T = '/home/claude/cambridge_battlecode/experiments/top30_nov3'
L2 = '/home/claude/cambridge_battlecode/experiments/ladder_nov2'
OUT = '/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro'
ME = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'
CH = ['Ry', 'VV', 'Vd', 'CI', 'St', 'Pr', 'Ma', 'Wi', 'Re', 'Vg', 'Ta', 'HR']
lad = json.load(open(f'{T}/ladder.json'))['teams']
top = [t for t in lad if t['rank'] <= 30]
MF = {r['map']: r for r in csv.DictReader(open(f'{T}/draft_bank/out/map_features.csv'))}
extra = {}
for fn in (f'{T}/objectives/out/games_top.jsonl', f'{T}/objectives/out/games_me.jsonl'):
    for l in open(fn):
        o = json.loads(l)
        extra.setdefault(o['map'], o['mapcls'])


def mclass(m):
    f = MF[m]
    gpc = float(f['gems']) / float(f['champs'])
    e = extra.get(m, {})
    return {'scarce': gpc <= 92, 'gpc': round(gpc, 1), 'size': f['size_class'], 'mono': int(f['mono']) > 0, 'altars': int(f['altars']),
            'champs': int(f['champs']), 'islands': (e.get('islands') or 0) > 0 if e else None,
            'bushy': (e.get('bush_frac') or 0) >= 0.15 if e else None}


def load(teamid, path, n=400):
    rows = []
    for l in open(path):
        m = json.loads(l)
        if m.get('kind') != 'ranked' or m.get('status') != 'finished' or m['map'] not in MF:
            continue
        me = [t for t in m['teams'] if t['teamId'] == teamid]
        op = [t for t in m['teams'] if t['teamId'] != teamid]
        if not me or not op:
            continue
        rows.append({'map': m['map'], 'pk': me[0]['draftPicks'], 'op': op[0]['draftPicks'], 'win': me[0]['result'] == 'win',
                     'end': m['endReason'], 'at': m['createdAt'], 'opid': op[0]['teamId']})
    rows.sort(key=lambda r: r['at'])
    return rows[-n:]


def H(counter):
    n = sum(counter.values())
    return -sum(c / n * math.log2(c / n) for c in counter.values() if c)


def cond_H(pairs):
    """pairs: list of (context, value) -> H(value | context) weighted"""
    by = defaultdict(Counter)
    for c, v in pairs:
        by[c][v] += 1
    n = len(pairs)
    return sum(sum(cn.values()) / n * H(cn) for cn in by.values())


def adapt(rows, rng):
    ig_real, ig_null, npk = 0.0, 0.0, 0
    bymap = defaultdict(list)
    for r in rows:
        bymap[r['map']].append(r)
    for k in range(1, 5):
        base, real = [], []
        for m, rs in bymap.items():
            for r in rs:
                if len(r['pk']) > k and len(r['op']) >= k:
                    ctx = (m, tuple(r['pk'][:k]))
                    base.append((ctx, r['pk'][k]))
                    real.append((ctx + (tuple(sorted(r['op'][:k])),), r['pk'][k]))
        if not base:
            continue
        hb = cond_H(base)
        ig_real += hb - cond_H(real)
        nul = []
        for s in range(20):
            sh = []
            for m, rs in bymap.items():
                ops = [r['op'] for r in rs]
                rng.shuffle(ops)
                for r, o in zip(rs, ops):
                    if len(r['pk']) > k and len(o) >= k:
                        sh.append(((m, tuple(r['pk'][:k]), tuple(sorted(o[:k]))), r['pk'][k]))
            nul.append(hb - cond_H(sh))
        ig_null += sum(nul) / len(nul)
        npk += 1
    return round(ig_real, 3), round(ig_null, 3)


def team_draft(name, rows, rng):
    out = {'name': name, 'n': len(rows)}
    pres = Counter()
    for r in rows:
        for c in r['pk']:
            pres[c] += 1
    out['pickrate'] = {CH[c]: round(v / len(rows), 2) for c, v in pres.most_common()}
    out['first'] = Counter(CH[r['pk'][0]] for r in rows).most_common(3)
    out['avgpos'] = {}
    pos = defaultdict(list)
    for r in rows:
        for i, c in enumerate(r['pk']):
            pos[CH[c]].append(i + 1)
    out['avgpos'] = {c: round(sum(v) / len(v), 2) for c, v in sorted(pos.items(), key=lambda kv: sum(kv[1]) / len(kv[1])) if len(v) >= 0.2 * len(rows)}
    # rosters by class
    for key in ('scarce', 'size', 'mono', 'altars', 'islands', 'bushy', 'champs'):
        d = defaultdict(Counter)
        for r in rows:
            d[str(mclass(r['map'])[key])]['-'.join(CH[c] for c in sorted(r['pk']))] += 1
        out['by_' + key] = {k: (sum(v.values()), v.most_common(2)) for k, v in sorted(d.items())}
    # determinism per map
    bym = defaultdict(list)
    for r in rows:
        bym[r['map']].append(r)
    same_full = same_first = same_set = tot = 0
    for m, rs in bym.items():
        if len(rs) < 2:
            continue
        mf = Counter(tuple(r['pk']) for r in rs).most_common(1)[0][1]
        m1 = Counter(r['pk'][0] for r in rs).most_common(1)[0][1]
        ms = Counter(tuple(sorted(r['pk'])) for r in rs).most_common(1)[0][1]
        same_full += mf; same_first += m1; same_set += ms; tot += len(rs)
    out['det_full'] = round(same_full / tot, 2) if tot else None
    out['det_first'] = round(same_first / tot, 2) if tot else None
    out['det_set'] = round(same_set / tot, 2) if tot else None
    out['ig_real'], out['ig_null'] = adapt(rows, rng)
    out['distinct_sets'] = len({tuple(sorted(r['pk'])) for r in rows})
    out['win'] = round(sum(r['win'] for r in rows) / len(rows), 3)
    ends = Counter((r['win'], r['end']) for r in rows)
    out['ends'] = {f"{'W' if k[0] else 'L'}:{k[1]}": v for k, v in ends.items()}
    out['span'] = (rows[0]['at'][:16], rows[-1]['at'][:16])
    # 'mirror' share: shares champion with opponent at the same pick index
    out['share_opp'] = round(sum(len(set(r['pk']) & set(r['op'])) for r in rows) / len(rows), 2)
    return out


def main():
    rng = random.Random(7)
    res = []
    for t in top:
        rows = load(t['teamId'], f"{T}/lists/{t['teamId'][:8]}.jsonl")
        d = team_draft(t['name'], rows, rng)
        d['rank'], d['rating'], d['id8'] = t['rank'], round(t['rating']), t['teamId'][:8]
        res.append(d)
    rows = load(ME, f'{L2}/matches_me.jsonl')
    d = team_draft('HouseOfCoders', rows, rng)
    d['rank'], d['rating'], d['id8'] = 70, 1979, ME[:8]
    res.append(d)
    json.dump(res, open(f'{OUT}/draft_team.json', 'w'), indent=0)
    with open(f'{OUT}/draft_out.txt', 'w') as f:
        for d in res:
            print(f"#{d['rank']} {d['name']} ({d['rating']}) n={d['n']} span {d['span'][0]}..{d['span'][1]} win {d['win']}", file=f)
            print(f"  pickrate {d['pickrate']}", file=f)
            print(f"  first {d['first']}  avgpos {d['avgpos']}", file=f)
            print(f"  det_full {d['det_full']} det_set {d['det_set']} det_first {d['det_first']} distinct_sets {d['distinct_sets']} "
                  f"IG(opp) real {d['ig_real']} null {d['ig_null']} share_opp {d['share_opp']}", file=f)
            for key in ('scarce', 'size', 'mono', 'altars', 'islands', 'bushy', 'champs'):
                print(f"  {key}: " + ' | '.join(f"{k} n={v[0]}: " + ', '.join(f'{s} {c}' for s, c in v[1]) for k, v in d['by_' + key].items()), file=f)
            print(f"  ends {d['ends']}", file=f)
    print('ok')


main()
