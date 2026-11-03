#!/usr/bin/env python3
"""Draft analysis: the top-30 teams' rosters (matches_current.jsonl, 6,795 ranked matches) vs ours (ladder_nov2/matches_me.jsonl).
Usage: python3 -I draft_analysis.py > out/draft_tables.txt
"""
import json, sys, math
from collections import Counter, defaultdict
BASE = '/home/claude/cambridge_battlecode/experiments'
sys.path.insert(0, f'{BASE}/top30_nov3/draft_bank')
import mapfeat  # noqa: E402

ME = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'
NAME = {0: 'Ryth', 1: 'Vesper', 2: 'Vendetta', 3: 'C&I', 4: 'Stellar', 5: 'Prism', 6: 'Marcella', 7: 'Willow', 8: 'Ren', 9: 'Varg', 10: 'Tavi', 11: 'HoR'}
ladder = json.load(open(f'{BASE}/top30_nov3/ladder.json'))['teams']
RANK = {t['teamId']: t['rank'] for t in ladder}
RATING = {t['teamId']: t['rating'] for t in ladder}
TNAME = {t['teamId']: t['name'] for t in ladder}
TOP = {t['teamId'] for t in ladder if t['rank'] <= 30}


def roster(picks):
    return '+'.join(NAME[p] for p in sorted(picks))


def order(picks):
    return '>'.join(NAME[p] for p in picks)


def wr(w, n):
    return f'{100 * w / n:5.1f}% ({w}/{n})' if n else '   -   (0)'


def elo_expect(ra, rb):
    return 1 / (1 + 10 ** ((rb - ra) / 400))


def main():
    rows = [json.loads(l) for l in open(f'{BASE}/top30_nov3/matches_current.jsonl')]
    rows = [r for r in rows if r['status'] == 'finished']
    print(f'{len(rows)} ranked matches, {len(TOP)} top-30 teams')
    mapclass = {}
    for r in rows:
        if r['map'] not in mapclass:
            try:
                f = mapfeat.features(r['map'])
                mapclass[r['map']] = f
            except Exception as ex:  # noqa: BLE001
                print('no features', r['map'], ex)
                mapclass[r['map']] = None
    # team-games of the top-30 teams
    tg = []
    for r in rows:
        for i, t in enumerate(r['teams']):
            o = r['teams'][1 - i]
            tg.append({'mid': r['matchId'], 'map': r['map'], 'tid': t['teamId'], 'name': t['name'], 'top': t['teamId'] in TOP, 'rank': RANK.get(t['teamId'], 999),
                       'picks': t['draftPicks'], 'n': len(t['draftPicks']), 'win': t['result'] == 'win', 'otid': o['teamId'], 'otop': o['teamId'] in TOP,
                       'opicks': o['draftPicks'], 'orank': RANK.get(o['teamId'], 999), 'end': r['endReason'], 'side': t['side'],
                       'exp': elo_expect(RATING.get(t['teamId'], 1500), RATING.get(o['teamId'], 1500))})
    top = [x for x in tg if x['top']]
    print(f'top-30 team-games: {len(top)}; vs top-30 opponents: {sum(1 for x in top if x["otop"])}')

    # ---------- 1. rosters by team size
    print('\n=== 1. Top-30 rosters by team size (share of top-30 team-games; win rate overall / vs top-30 opponents; mean Elo-expected) ===')
    for n in (3, 4, 5):
        sub = [x for x in top if x['n'] == n]
        c = Counter(roster(x['picks']) for x in sub)
        print(f'\n-- {n} champions: {len(sub)} team-games, {len(c)} distinct rosters')
        for ro, k in c.most_common(12):
            s = [x for x in sub if roster(x['picks']) == ro]
            w = sum(x['win'] for x in s)
            st = [x for x in s if x['otop']]
            wt = sum(x['win'] for x in st)
            teams = Counter(x['name'] for x in s)
            print(f'  {ro:45s} {100 * k / len(sub):5.1f}%  wr {wr(w, len(s))}  vsTop30 {wr(wt, len(st))}  exp {100 * sum(x["exp"] for x in s) / len(s):4.1f}%  teams: {", ".join(f"{a}({b})" for a, b in teams.most_common(4))}')
    # champion presence per size
    print('\n=== 1b. Champion presence in top-30 rosters by team size (share of team-games with the champion; win rate with / without, vs top-30 opponents only) ===')
    for n in (3, 4, 5):
        sub = [x for x in top if x['n'] == n and x['otop']]
        print(f'\n-- {n} champions, {len(sub)} top-30 vs top-30 team-games')
        for cid in range(12):
            w_in = [x for x in sub if cid in x['picks']]
            w_out = [x for x in sub if cid not in x['picks']]
            # mirror-controlled: games where exactly one team has it
            one = [x for x in sub if (cid in x['picks']) != (cid in x['opicks'])]
            has = [x for x in one if cid in x['picks']]
            print(f'  {NAME[cid]:9s} present {100 * len(w_in) / max(1, len(sub)):5.1f}%  wr with {wr(sum(x["win"] for x in w_in), len(w_in))}  without {wr(sum(x["win"] for x in w_out), len(w_out))}  one-side-only: with {wr(sum(x["win"] for x in has), len(has))}')

    # ---------- 2. rosters by map class (5-champ maps), and the per-map roster of the top-30
    print('\n=== 2. Top-30 rosters by map class (team size x map class) ===')
    def mclass(m):
        f = mapclass.get(m)
        if not f:
            return '?'
        return f"{f['champs']}c/{f['size_class']}/{'mono' if f['mono'] else 'nomono'}/alt{min(f['altars'], 4)}"
    byc = defaultdict(list)
    for x in top:
        byc[mclass(x['map'])].append(x)
    for k in sorted(byc):
        s = byc[k]
        c = Counter(roster(x['picks']) for x in s)
        print(f'\n-- {k}: {len(s)} team-games, maps: {len(set(x["map"] for x in s))}')
        for ro, kk in c.most_common(5):
            ss = [x for x in s if roster(x['picks']) == ro]
            print(f'  {ro:45s} {100 * kk / len(s):5.1f}%  wr {wr(sum(x["win"] for x in ss), len(ss))}')

    print('\n=== 2b. Per map: the top-30 majority roster, its share, win rate vs top-30; our roster on that map and our ranked win rate ===')
    me_rows = [json.loads(l) for l in open(f'{BASE}/ladder_nov2/matches_me.jsonl')]
    me = []
    for r in me_rows:
        if r['status'] != 'finished' or r['kind'] != 'ranked':
            continue
        us = [t for t in r['teams'] if t['teamId'] == ME][0]
        th = [t for t in r['teams'] if t['teamId'] != ME][0]
        me.append({'mid': r['matchId'], 'map': r['map'], 'picks': us['draftPicks'], 'opicks': th['draftPicks'], 'win': us['result'] == 'win',
                   'oname': th['name'], 'otid': th['teamId'], 'otop': th['teamId'] in TOP, 'created': r['createdAt'], 'end': r['endReason'],
                   'orank': RANK.get(th['teamId'], 999)})
    me_recent = [x for x in me if x['created'] >= '2026-11-02T13:00']
    print(f'our ranked games since Nov 2 13:00Z (v84+): {len(me_recent)}, win {wr(sum(x["win"] for x in me_recent), len(me_recent))}; vs top-30: {wr(sum(x["win"] for x in me_recent if x["otop"]), sum(1 for x in me_recent if x["otop"]))}')
    bymap_top = defaultdict(list)
    for x in top:
        bymap_top[x['map']].append(x)
    bymap_me = defaultdict(list)
    for x in me_recent:
        bymap_me[x['map']].append(x)
    print(f"{'map':24s} {'cl':14s} {'top-30 majority roster':40s} share  wr(vsTop)   | our roster (n)                          our wr")
    for m in sorted(bymap_top):
        s = bymap_top[m]
        c = Counter(roster(x['picks']) for x in s)
        ro, k = c.most_common(1)[0]
        ss = [x for x in s if roster(x['picks']) == ro and x['otop']]
        mm = bymap_me.get(m, [])
        cm = Counter(roster(x['picks']) for x in mm)
        ours = cm.most_common(1)[0][0] if cm else '-'
        print(f'{m:24s} {mclass(m):14s} {ro:40s} {100 * k / len(s):4.0f}%  {wr(sum(x["win"] for x in ss), len(ss)):14s} | {ours:40s} {wr(sum(x["win"] for x in mm), len(mm))}')

    # ---------- 3. pick order
    print('\n=== 3. Pick order of the top-30 (first pick, last pick) by team size ===')
    for n in (3, 4, 5):
        sub = [x for x in top if x['n'] == n]
        print(f'\n-- {n} champions: first pick', ', '.join(f'{NAME[a]} {100 * b / len(sub):.0f}%' for a, b in Counter(x['picks'][0] for x in sub).most_common(6)))
        print(f'   last pick ', ', '.join(f'{NAME[a]} {100 * b / len(sub):.0f}%' for a, b in Counter(x['picks'][-1] for x in sub).most_common(8)))
        c = Counter(order(x['picks']) for x in sub)
        print('   most common orders:', '; '.join(f'{a} {100 * b / len(sub):.0f}%' for a, b in c.most_common(4)))

    # ---------- 4. counter-picks: does the last pick depend on the enemy's visible picks?
    print('\n=== 4. Counter-picks: last pick conditional on the enemy roster (top-30 team-games; per team+map variation) ===')
    # per (team, map): distinct rosters and distinct last picks over >= 4 games
    var = []
    for (tid, m), s in defaultdict(list, {k: v for k, v in defaultdict(list).items()}).items():
        pass
    bytm = defaultdict(list)
    for x in top:
        bytm[(x['tid'], x['map'])].append(x)
    fixed = varied = 0
    per_team = defaultdict(lambda: [0, 0, 0])
    for (tid, m), s in bytm.items():
        if len(s) < 4:
            continue
        nro = len(set(roster(x['picks']) for x in s))
        nlast = len(set(x['picks'][-1] for x in s))
        per_team[tid][0] += 1
        per_team[tid][1] += nro > 1
        per_team[tid][2] += nlast > 1
        if nro > 1:
            varied += 1
        else:
            fixed += 1
    print(f'(team, map) cells with >= 4 games: {fixed + varied}; roster varies in {varied} ({100 * varied / max(1, fixed + varied):.0f}%)')
    print('per team: cells, cells with >1 roster, cells with >1 last pick')
    for tid, (a, b, c) in sorted(per_team.items(), key=lambda kv: RANK.get(kv[0], 999)):
        print(f'  #{RANK.get(tid, 999):2d} {TNAME.get(tid, tid[:8]):32s} {a:3d} {b:3d} {c:3d}')
    # conditional table: P(last pick = X | enemy's first n-1 picks contain Y) for 5-champ games, pooled over the top-30
    print('\nlast pick (5-champ) by enemy visible pick (enemy picks 1..4 contain Y): share of last pick = X; base = unconditional')
    sub = [x for x in top if x['n'] == 5]
    base = Counter(x['picks'][-1] for x in sub)
    tot = len(sub)
    print(f"{'enemy has':10s} " + ' '.join(f'{NAME[c]:>8s}' for c in range(12)))
    print(f"{'base':10s} " + ' '.join(f'{100 * base[c] / tot:7.1f}%' for c in range(12)))
    for y in range(12):
        s = [x for x in sub if y in x['opicks'][:4]]
        if len(s) < 50:
            continue
        c = Counter(x['picks'][-1] for x in s)
        print(f'{NAME[y]:10s} ' + ' '.join(f'{100 * c[k] / len(s):7.1f}%' for k in range(12)) + f'   n={len(s)}')
    # chi-square-like dependence strength per team: entropy of last pick given own first 4 vs given own first 4 + enemy first 4
    print('\nper team (5-champ, >= 60 games): H(last | own first 4) vs H(last | own first 4, enemy first 4) in bits; a big drop = counter-picking')
    def H(groups):
        tot = sum(sum(c.values()) for c in groups.values())
        h = 0
        for c in groups.values():
            n = sum(c.values())
            for v in c.values():
                h -= (n / tot) * (v / n) * math.log2(v / n)
        return h
    for tid in sorted(TOP, key=lambda t: RANK[t]):
        s = [x for x in top if x['tid'] == tid and x['n'] == 5]
        if len(s) < 60:
            continue
        g1 = defaultdict(Counter)
        g2 = defaultdict(Counter)
        for x in s:
            g1[(x['map'], tuple(x['picks'][:4]))][x['picks'][-1]] += 1
            g2[(x['map'], tuple(x['picks'][:4]), tuple(sorted(x['opicks'][:4])))][x['picks'][-1]] += 1
        print(f'  #{RANK[tid]:2d} {TNAME[tid]:32s} n={len(s):4d} H1={H(g1):.3f} H2={H(g2):.3f}  cells1={len(g1)} cells2={len(g2)}')

    # ---------- 5. matchups among top-30 games
    print('\n=== 5. Matchups (top-30 vs top-30 team-games): win rate when our side has A and the enemy does not (one-sided), by champion, 5-champ maps ===')
    sub = [x for x in top if x['otop']]
    for n in (3, 4, 5):
        s5 = [x for x in sub if x['n'] == n]
        print(f'-- {n} champions ({len(s5)} team-games)')
        for cid in range(12):
            one = [x for x in s5 if cid in x['picks'] and cid not in x['opicks']]
            w = sum(x['win'] for x in one)
            e = sum(x['exp'] for x in one)
            print(f'  {NAME[cid]:9s} one-sided n={len(one):4d} wr {wr(w, len(one))}  Elo-expected {100 * e / max(1, len(one)):4.1f}%  edge {100 * (w - e) / max(1, len(one)):+5.1f}')

    # ---------- 6. ours
    print('\n=== 6. Our rosters (ranked, since Nov 2 13:00Z) and win rate by their roster ===')
    for n in (3, 4, 5):
        s = [x for x in me_recent if len(x['picks']) == n]
        c = Counter(roster(x['picks']) for x in s)
        print(f'-- {n} champions: {len(s)} games; ours:', '; '.join(f'{a} {b} ({wr(sum(x["win"] for x in s if roster(x["picks"]) == a), b)})' for a, b in c.most_common(5)))
    print('\nour win rate by THEIR roster (>= 5 games), ranked since Nov 2:')
    c = Counter(roster(x['opicks']) for x in me_recent)
    for ro, k in c.most_common(25):
        s = [x for x in me_recent if roster(x['opicks']) == ro]
        print(f'  {ro:45s} n={k:3d} our wr {wr(sum(x["win"] for x in s), k)}  mean opp rank {sum(min(x["orank"], 200) for x in s) / k:5.0f}')
    print('\nour games vs top-30 teams (ranked, since Nov 2): map, their roster, ours, result')
    for x in sorted((x for x in me_recent if x['otop']), key=lambda x: x['map']):
        print(f"  {x['map']:22s} #{x['orank']:2d} {x['oname']:28s} they {roster(x['opicks']):40s} we {roster(x['picks']):40s} {'W' if x['win'] else 'L'} {x['end']}")
    print('\nour win rate by champion present on THEIR side (one-sided: they have it, we do not), ranked since Nov 2:')
    for cid in range(12):
        one = [x for x in me_recent if cid in x['opicks'] and cid not in x['picks']]
        both = [x for x in me_recent if cid in x['opicks'] and cid in x['picks']]
        print(f'  {NAME[cid]:9s} they-only n={len(one):3d} our wr {wr(sum(x["win"] for x in one), len(one))}   both n={len(both):3d} our wr {wr(sum(x["win"] for x in both), len(both))}')
    # 6b: all teams: who beats whom by roster (5-champ) across the whole dataset with Elo control
    print('\n=== 6b. Roster edge over Elo expectation, all 45 teams, >= 80 team-games (5-champ) ===')
    s5 = [x for x in tg if x['n'] == 5]
    c = Counter(roster(x['picks']) for x in s5)
    for ro, k in c.most_common(20):
        s = [x for x in s5 if roster(x['picks']) == ro]
        w = sum(x['win'] for x in s)
        e = sum(x['exp'] for x in s)
        print(f'  {ro:45s} n={k:4d} wr {100 * w / k:5.1f}% exp {100 * e / k:5.1f}% edge {100 * (w - e) / k:+5.1f}  teams {", ".join(a for a, b in Counter(x["name"] for x in s).most_common(3))}')


if __name__ == '__main__':
    main()
