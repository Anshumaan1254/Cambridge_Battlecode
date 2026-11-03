#!/usr/bin/env python3
"""Fuel: our bodies' per-turn fuel from the team-*.fuel stream of our replays (ladder_nov2/replays, only our own team's stream is in
the bundle), rollovers (turns at the limit: 200,000 on round 1, 100,000 after; draft turn 1 10,000,000, other draft turns 100,000),
by round band, by map, by champion; and the 'Turn rollover' events of out/rollovers.jsonl (both teams, ours and the top-30 games).
    nice -n 19 python3 -I execution/fuel.py > execution/out/fuel.txt
Layout of the stream (validated: n = 8 limits + draft picks + rounds x bodies, round-major, every body every round, dead ones too)."""
import json, os, sys, zipfile, struct, glob
from collections import Counter, defaultdict
from statistics import mean, median
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h30  # noqa: E402

TOP_IDS = {t['teamId'] for t in h30.LADDER['teams'][:30]}


def parse(path):
    z = zipfile.ZipFile(path)
    mem = [n for n in z.namelist() if n.endswith('.fuel')]
    if not mem:
        return None
    b = z.read(mem[0])
    off = 13
    n = (len(b) - off) // 8
    vals = struct.unpack('<%dQ' % n, b[off:off + n * 8])
    return vals[:8], vals[8:]


def band(r):
    return 'r1' if r == 1 else 'r2-10' if r <= 10 else 'r11-100' if r <= 100 else 'r101-300' if r <= 300 else 'r301-800' if r <= 800 else 'r801-1400' if r <= 1400 else 'r1400+'


def main():
    gs = h30.our_games('all')
    rows = []
    per_map = defaultdict(lambda: [0, 0, 0])   # map -> [games, rollovers, turns]
    per_champ = defaultdict(lambda: [0, 0])
    per_band = defaultdict(lambda: [0, 0])
    per_ver = defaultdict(lambda: [0, 0, 0])
    allv = []
    r1 = []
    draft1 = []
    worst = []
    roll_rounds = defaultdict(list)  # key -> [(r, body)]
    for g in gs:
        p = parse(g['replay'])
        if p is None:
            continue
        limits, rest = p
        d = json.load(open(g['dec']))
        m = d['meta']
        we = g['we']
        bodies = [b['index'] for b in m['bodies'] if b['team'] == we]
        nb = len(bodies)
        nd = len(m['drafts'][we])
        draft = rest[:nd]
        game = rest[nd:]
        draft1.append(draft[0])
        over = 0
        for i, v in enumerate(game):
            r = i // nb + 1
            b = bodies[i % nb]
            lim = 200000 if r == 1 else 100000
            allv.append(v)
            if r == 1:
                r1.append(v)
            if v >= lim:
                over += 1
                per_band[band(r)][0] += 1
                per_champ[m['bodies'][b]['type']][0] += 1
                roll_rounds[g['key']].append((r, b))
            per_band[band(r)][1] += 1
            per_champ[m['bodies'][b]['type']][1] += 1
        per_map[g['map']][0] += 1
        per_map[g['map']][1] += over
        per_map[g['map']][2] += len(game)
        per_ver[g['ver']][0] += 1
        per_ver[g['ver']][1] += over
        per_ver[g['ver']][2] += len(game)
        worst.append((over, g['key'][:8], g['map'], g['ver'], g['res']))
        rows.append({'key': g['key'], 'map': g['map'], 'ver': g['ver'], 'res': g['res'], 'over': over, 'turns': len(game), 'mean': mean(game),
                     'p99': sorted(game)[int(0.99 * len(game))], 'draft1': draft[0], 'roll': roll_rounds[g['key']]})
    json.dump(rows, open(f'{h30.EXE}/out/fuel_games.json', 'w'))
    allv.sort()
    print(f'OUR FUEL (team-*.fuel of {len(rows)} replays, v84-v88): draft turn 1 mean {mean(draft1):,.0f} max {max(draft1):,} (limit 10,000,000)')
    print(f'  game turns {len(allv):,}: mean {mean(allv):,.0f} median {median(allv):,.0f} p90 {allv[int(0.9 * len(allv))]:,} p99 {allv[int(0.99 * len(allv))]:,} max {allv[-1]:,}')
    print(f'  round-1 turns: mean {mean(r1):,.0f} max {max(r1):,} (limit 200,000); at the limit {sum(1 for v in r1 if v >= 200000)} of {len(r1)}')
    tot_over = sum(x[0] for x in per_band.values())
    tot = sum(x[1] for x in per_band.values())
    print(f'  rollovers (turn at the limit): {tot_over} = {tot_over / tot:.2%} of turns, {tot_over / len(rows):.1f} per game')
    print('  by round band (rollovers / turns, share):')
    for k in ('r1', 'r2-10', 'r11-100', 'r101-300', 'r301-800', 'r801-1400', 'r1400+'):
        a, n = per_band[k]
        print(f'    {k:10} {a:5} / {n:7} {a / max(1, n):.2%}')
    print('  by version:', {k: f'{v[1] / v[0]:.1f}/g ({v[1] / max(1, v[2]):.2%})' for k, v in sorted(per_ver.items())})
    print('  by champion (rollover share of turns):', {k: f'{v[0] / max(1, v[1]):.2%}' for k, v in sorted(per_champ.items(), key=lambda kv: -kv[1][0] / max(1, kv[1][1]))})
    print('  by map, worst 15 (rollovers per game, share of turns, games):')
    for k, v in sorted(per_map.items(), key=lambda kv: -kv[1][1] / kv[1][0])[:15]:
        print(f'    {k:24} {v[1] / v[0]:6.1f}/g {v[1] / max(1, v[2]):.2%} n={v[0]}')
    print('  worst games:', sorted(worst, reverse=True)[:10])
    # ---- rollover events (both teams), ours vs top-30 games
    rf = f'{h30.EXE}/out/rollovers.jsonl'
    if os.path.exists(rf):
        ev = {}
        for l in open(rf):
            x = json.loads(l)
            if 'roll' in x:
                ev[x['key']] = x
        ours = {g['key']: g for g in gs}
        top = {g['key']: g for g in h30.top_games()}
        print(f'\nTURN ROLLOVER EVENTS (replay step kind 26; {len(ev)} games decoded with --rollovers)')
        # validation on our games: stream count vs events for our team
        agree = []
        for row in rows:
            x = ev.get(row['key'])
            if not x:
                continue
            g = ours[row['key']]
            mine = sum(1 for r, who, t in x['roll'] if t == g['we'])
            agree.append((row['over'], mine))
        if agree:
            print(f'  validation on our games (n={len(agree)}): fuel-stream rollovers {sum(a for a, b in agree)} vs event rollovers for our team {sum(b for a, b in agree)};'
                  f' exact match in {sum(1 for a, b in agree if a == b)} games')
        # ours vs opponents in our games; top-30 teams in the top-30 games
        acc = defaultdict(lambda: [0, 0, 0])  # label -> [games, rollovers, body-rounds]
        by_band = defaultdict(Counter)
        by_team = defaultdict(lambda: [0, 0])
        for key, x in ev.items():
            if key in ours:
                g = ours[key]
                d = json.load(open(g['dec']))
                nb = {t: sum(1 for b in d['meta']['bodies'] if b['team'] == t) for t in (0, 1)}
                for t, lab in ((g['we'], f"we_{g['ver']}"), (1 - g['we'], 'opp_in_our_games')):
                    n = sum(1 for r, who, tt in x['roll'] if tt == t)
                    acc[lab][0] += 1
                    acc[lab][1] += n
                    acc[lab][2] += x['final'] * nb[t]
                    for r, who, tt in x['roll']:
                        if tt == t:
                            by_band[lab][band(r)] += 1
                    if lab != 'opp_in_our_games':
                        acc['we_all'][0] += 1
                        acc['we_all'][1] += n
                        acc['we_all'][2] += x['final'] * nb[t]
            elif key in top:
                g = top[key]
                d = json.load(open(g['dec']))
                nb = {t: sum(1 for b in d['meta']['bodies'] if b['team'] == t) for t in (0, 1)}
                for t in (0, 1):
                    n = sum(1 for r, who, tt in x['roll'] if tt == t)
                    acc['top30'][0] += 1
                    acc['top30'][1] += n
                    acc['top30'][2] += x['final'] * nb[t]
                    by_team[g['teams'][t]][0] += 1
                    by_team[g['teams'][t]][1] += n
                    for r, who, tt in x['roll']:
                        if tt == t:
                            by_band['top30'][band(r)] += 1
        print('  rollovers per team-game and per 1000 body-rounds:')
        for lab, v in sorted(acc.items()):
            print(f'    {lab:18} team-games {v[0]:4} rollovers {v[1] / max(1, v[0]):6.1f}/g  {1000 * v[1] / max(1, v[2]):6.2f} per 1000 body-rounds  bands {dict(by_band[lab])}')
        print('  top-30 teams by rollovers per game (team-games):')
        for tid, v in sorted(by_team.items(), key=lambda kv: -kv[1][1] / kv[1][0]):
            print(f"    {h30.NAME.get(tid, tid[:8]):28} rank {h30.RANK.get(tid, '?'):3} {v[1] / v[0]:6.1f}/g  n={v[0]}")


if __name__ == '__main__':
    main()
