#!/usr/bin/env python3
"""Examples for REPORT.txt: cycles we opened and lost, respawns we waited at and lost, our raids that died, our recalls that
   never landed, wards. nice -n 19 python3 examples.py > out/examples.txt"""
import json, os, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
from report_stats import load, contested, side_of, mean  # noqa: E402


def main():
    me = load('me')
    top = load('top')
    print('# Q1 examples: contested big-group respawn cycles we HIT FIRST and the enemy captured (ME, v84-v88)')
    n = 0
    reasons = Counter()
    for r in sorted(me, key=lambda x: x['created'], reverse=True):
        we = 0 if r['sides']['0']['id'] == C.ME else 1
        for c in r['cycles']:
            if c['mono'] or not contested(c) or c['first_hit'] != we or c['by'] != 1 - we:
                continue
            rc = c['react'][str(we)]
            a = c['arr'][str(we)]
            reasons[(rc['beh'] if rc else 'no-contact')] += 1
            if n < 25:
                print(f"  {r['mid'][:8]} {r['map']:20s} {r.get('ver')} G{c['gid']} ({c['gems']}g) respawn r{c['start']} first hit r{c['first_hit_r']} by us; "
                      f"we: arrived r{a['at'] if a else '-'} n={a['n'] if a else 0} hp={a['hp'] if a else '-'}, hits {c['hits'][str(we)]} by {c['hitters'][str(we)]} bodies vs their {c['hits'][str(1 - we)]} by {c['hitters'][str(1 - we)]}; "
                      f"died r{c['died']} taken r{c['taken']} by them; deaths we/they {c['deaths'][str(we)]}/{c['deaths'][str(1 - we)]}; "
                      f"contact: {rc['beh'] if rc else '-'} (n {rc['n'] if rc else 0} vs {rc['n_en'] if rc else 0}, hp {rc['hp'] if rc else '-'}, back {rc['back'] if rc else '-'})")
            n += 1
    print('  total', n, 'reaction at contact:', dict(reasons))

    print('\n# Q1 examples: respawns we were WAITING at (present within 4 at the respawn round) and the enemy captured (ME)')
    n = 0
    for r in sorted(me, key=lambda x: x['created'], reverse=True):
        we = 0 if r['sides']['0']['id'] == C.ME else 1
        for c in r['cycles']:
            a = c['arr'][str(we)]
            b = c['arr'][str(1 - we)]
            if c['mono'] or not contested(c) or c['start'] == 1 or not a or a['wait'] < 0 or c['by'] != 1 - we:
                continue
            rc = c['react'][str(we)]
            if n < 20:
                print(f"  {r['mid'][:8]} {r['map']:20s} {r.get('ver')} G{c['gid']} ({c['gems']}g) respawn r{c['start']}: we waited {a['wait']} rounds with {a['n']} bodies hp {a['hp']}; "
                      f"they: {'present n=' + str(b['n']) + ' wait ' + str(b['wait']) + ' hp ' + str(b['hp']) if b else 'absent'}; first hit {'us' if c['first_hit'] == we else 'them'} r{c['first_hit_r']}; "
                      f"hits {c['hits'][str(we)]}/{c['hits'][str(1 - we)]}; taken r{c['taken']}; deaths {c['deaths'][str(we)]}/{c['deaths'][str(1 - we)]}; contact {rc['beh'] if rc else '-'}")
            n += 1
    print('  total', n)

    print('\n# Q1 waiting at respawns: distribution of waiting rounds (present at the respawn), TOP vs ME')
    for name, rows, pick in (('TOP', top, None), ('ME', me, 'me'), ('OPP', me, 'opp')):
        ws = []
        for r in rows:
            we = 0 if r['sides']['0']['id'] == C.ME else 1
            ts = (0, 1) if pick is None else ((we,) if pick == 'me' else (1 - we,))
            for t in ts:
                for c in r['cycles']:
                    if c['mono'] or not contested(c) or c['start'] == 1:
                        continue
                    a = c['arr'][str(t)]
                    if a and a['wait'] >= 0:
                        ws.append(a['wait'])
        if ws:
            h = Counter('0' if w == 0 else '1-5' if w <= 5 else '6-15' if w <= 15 else '16-30' if w <= 30 else '>30' for w in ws)
            print(f"  {name}: n={len(ws)} mean {mean(ws):.1f}: " + ', '.join(f'{k} {v / len(ws):.0%}' for k, v in sorted(h.items())))

    print('\n# Q1 per-map: contested cycles capture share, ME vs TOP on the same maps (maps with >= 3 of our games)')
    bym = defaultdict(lambda: {'me': [0, 0, 0], 'top': [0, 0, 0]})  # [won, taken, games]
    for r in me:
        we = 0 if r['sides']['0']['id'] == C.ME else 1
        d = bym[r['map']]['me']
        d[2] += 1
        for c in r['cycles']:
            if c['mono'] or not contested(c) or c['by'] not in (0, 1):
                continue
            d[1] += 1
            d[0] += c['by'] == we
    for r in top:
        d = bym[r['map']]['top']
        d[2] += 2
        for c in r['cycles']:
            if c['mono'] or not contested(c) or c['by'] not in (0, 1):
                continue
            d[1] += 2
            d[0] += 1
    rows = []
    for m, d in bym.items():
        if d['me'][2] >= 3 and d['me'][1] >= 4:
            rows.append((d['me'][0] / d['me'][1], m, d))
    for s, m, d in sorted(rows):
        print(f"  {m:22s} ME {d['me'][0]}/{d['me'][1]} = {s:.2f} (games {d['me'][2]})   TOP cycles/game {d['top'][1] / max(1, d['top'][2]):.1f} (sides {d['top'][2]})")

    print('\n# Q2 examples: our raids that died (ME, v88 first)')
    n = 0
    for r in sorted(me, key=lambda x: (x.get('ver') != 'v88', x['created']), reverse=False):
        we = 0 if r['sides']['0']['id'] == C.ME else 1
        for x in r['raids']:
            if x['t'] != we or not x['died']:
                continue
            if n < 15:
                print(f"  {r['mid'][:8]} {r['map']:20s} {r.get('ver')} body {x['b']} {x['champ']} r{x['r0']}-{x['r1']} ({x['len']} rounds) bodies {x['bodies']} camp hits {x['hits_camp']} champ hits {x['hits_champ']} caps {x['caps']}g kills {x['kills']}")
            n += 1
    print('  total raid deaths', n)
    print('\n# Q2 raids: TOP raids that captured something (share) and their size')
    for name, rows, pick in (('TOP', top, None), ('ME', me, 'me'), ('OPP', me, 'opp')):
        rd = []
        for r in rows:
            we = 0 if r['sides']['0']['id'] == C.ME else 1
            ts = (0, 1) if pick is None else ((we,) if pick == 'me' else (1 - we,))
            rd += [x for x in r['raids'] if x['t'] in ts]
        if rd:
            print(f"  {name}: raids {len(rd)}: with a capture {sum(1 for x in rd if x['caps'] or x['gold']) / len(rd):.0%}, with camp hits {sum(1 for x in rd if x['hits_camp']) / len(rd):.0%}, "
                  f"with champ hits {sum(1 for x in rd if x['hits_champ']) / len(rd):.0%}, died {sum(x['died'] for x in rd) / len(rd):.0%}, bodies>=2 {sum(1 for x in rd if x['bodies'] >= 2) / len(rd):.0%}, "
                  f"bodies>=3 {sum(1 for x in rd if x['bodies'] >= 3) / len(rd):.0%}; by champ: {dict(Counter(x['champ'] for x in rd).most_common(6))}")
            h = Counter('<200' if x['r0'] < 200 else '200-600' if x['r0'] < 600 else '600-1200' if x['r0'] < 1200 else '>1200' for x in rd)
            print('     start round: ' + ', '.join(f'{k} {v / len(rd):.0%}' for k, v in sorted(h.items())))

    print('\n# Q6 examples: our held recalls that never landed and were not hit (cancelled), v88')
    n = 0
    for r in sorted(me, key=lambda x: x['created'], reverse=True):
        we = 0 if r['sides']['0']['id'] == C.ME else 1
        if r.get('ver') != 'v88':
            continue
        for x in r['recalls']:
            if x['t'] != we or x['done'] is not None or x['hit'] or (x['d_spawn'] or 0) < 3:
                continue
            if n < 12:
                print(f"  {r['mid'][:8]} {r['map']:20s} body {x['b']} {x['champ']} r{x['r']} d_spawn {x['d_spawn']} band {x['band']} hp {x['hp']} bag {x['bag']} gold {x['gold']} why {x['why']} cap_recall {x['cap_recall']}")
            n += 1
    print('  total', n)
    print('\n# Q6 recall reasons by band and hp: TOP vs ME (held, >= 3 steps from spawn)')
    for name, rows, pick in (('TOP', top, None), ('ME', me, 'me'), ('ME88', [r for r in me if r.get('ver') == 'v88'], 'me'), ('OPP', me, 'opp')):
        rc = []
        for r in rows:
            we = 0 if r['sides']['0']['id'] == C.ME else 1
            ts = (0, 1) if pick is None else ((we,) if pick == 'me' else (1 - we,))
            rc += [x for x in r['recalls'] if x['t'] in ts and x['d_spawn'] is not None and x['d_spawn'] >= 3]
        if not rc:
            continue
        hp = Counter('<30%' if x['hp'] < 0.3 else '30-50%' if x['hp'] < 0.5 else '50-70%' if x['hp'] < 0.7 else '>=70%' for x in rc)
        dd = Counter('3-10' if x['d_spawn'] <= 10 else '11-25' if x['d_spawn'] <= 25 else '26-50' if x['d_spawn'] <= 50 else '>50' for x in rc)
        print(f"  {name}: n={len(rc)} ({len(rc) / max(1, len(rows) * (2 if pick is None else 1)):.1f}/game) hp: " + ', '.join(f'{k} {v / len(rc):.0%}' for k, v in sorted(hp.items())) +
              '; steps from spawn: ' + ', '.join(f'{k} {v / len(rc):.0%}' for k, v in sorted(dd.items())) +
              f"; landed {sum(1 for x in rc if x['done'] is not None) / len(rc):.0%}; hit {sum(1 for x in rc if x['hit']) / len(rc):.0%}; cap-recall {sum(1 for x in rc if x['cap_recall']) / len(rc):.0%}"
              f"; high-hp (>=70%) no-bag no-gold recalls {sum(1 for x in rc if x['hp'] >= 0.7 and x['bag'] < 20 and x['gold'] < 90) / len(rc):.0%}")

    print('\n# Q4 examples: ward placement by champion and the first ward (ME v88 vs TOP)')
    for name, rows, pick in (('TOP', top, None), ('ME88', [r for r in me if r.get('ver') == 'v88'], 'me'), ('OPP', me, 'opp')):
        ws = []
        for r in rows:
            we = 0 if r['sides']['0']['id'] == C.ME else 1
            ts = (0, 1) if pick is None else ((we,) if pick == 'me' else (1 - we,))
            ws += [w for w in r['wards'] if w['t'] in ts]
        if ws:
            print(f"  {name}: {len(ws)} wards; bush {sum(w['bush'] for w in ws) / len(ws):.0%}; near big group {sum(w['near_big'] for w in ws) / len(ws):.0%}; near camp {sum(w['near_camp'] for w in ws) / len(ws):.0%}; "
                  f"near altar {sum(w['near_altar'] for w in ws) / len(ws):.0%}; band {dict(Counter(w['band'] for w in ws))}; d_spawn mean {mean([w['d_spawn'] for w in ws]):.1f}")


if __name__ == '__main__':
    main()
