#!/usr/bin/env python3
"""Contest cycles of the big camp groups (gems >= MIN): one row per alive period (spawn/respawn -> all camps dead -> reward taken).

    nice -n 19 python3 -I map_fail/cycles.py [map ...] > map_fail/out/cycles.txt   (also writes out/cycles.jsonl)

Per cycle: start round (respawn), bodies within 4 of the group at the start (we / they) and their mean hp%, the team that hit it first,
hits per team, round it died, who stood on its tiles while the reward was up (body-rounds per team), who took the reward (and gems),
our / their deaths within 5 of the group during the cycle, and how many of our bodies were within 4 at the start of the cycle
with hp < 60% (waited there damaged)."""
import json, os, sys
from collections import Counter, defaultdict
BASE = '/home/claude/cambridge_battlecode/experiments/ladder_nov2'
sys.path.insert(0, f'{BASE}/map_fail')
from mapgroups import full_groups  # noqa: E402
from analyze import select, MAPS  # noqa: E402

MIN = 30


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def run(g):
    mid, we = g['mid'], g['we']
    d = json.load(open(f'{BASE}/dec/{mid}.json'))
    mj = json.load(open(f'{BASE}/mj/{mid}.json'))
    meta = d['meta']
    team = {b['index']: b['team'] for b in meta['bodies']}
    G = full_groups(g['map'], meta, mj['sym'])
    R = {rr['r']: rr for rr in d['rounds'][1:]}
    final = meta['finalRound']
    camp_at = {(c['x'], c['y']): c['index'] for c in meta['camps']}
    hits = defaultdict(list)  # camp index -> [(r, team)]
    caps = []
    deaths = []
    for e in d['events']:
        if e['k'] == 'Attack' and e.get('who') is not None and tuple(e['to']) in camp_at:
            hits[camp_at[tuple(e['to'])]].append((e['r'], e['team']))
        elif e['k'] == 'Cast ability' and e.get('who') is not None and 'to' in e:
            P = tuple(e['to'])
            for q, ci in camp_at.items():
                if cheb(P, q) <= (1 if e.get('ability') == 3 else 0):
                    hits[ci].append((e['r'], e['team']))
        elif e['k'] in ('CaptureGems', 'CaptureGold'):
            caps.append((e['r'], e['team'], e['gems'], tuple(e['at'])))
        elif e['k'] == 'Death':
            deaths.append((e['r'], e['team'], tuple(e['at']), e['by']))
    rows = []
    for gg in G:
        if gg['gems'] < MIN:
            continue
        tiles = set(gg['tiles'])
        alive_prev = False
        cur = None
        for r in range(1, final + 1):
            rr = R.get(r)
            if rr is None:
                continue
            alive = any(rr['campHp'][i] > 0 for i in gg['idx'])
            gr = rr['gr'][gg['id']]
            if alive and not alive_prev:
                # new cycle
                if cur:
                    rows.append(cur)
                near = [(c[0], c[1], c[5] / max(1, c[6])) for c in rr['ch'] if c[7] and min(cheb((c[3], c[4]), t) for t in tiles) <= 4]
                cur = {'mid': mid, 'map': g['map'], 'res': g['res'], 'gid': gg['id'], 'gems': gg['gems'], 'start': r,
                       'n_we': sum(1 for x in near if x[1] == we), 'n_they': sum(1 for x in near if x[1] != we),
                       'hp_we': round(sum(x[2] for x in near if x[1] == we) / max(1, sum(1 for x in near if x[1] == we)), 2),
                       'hp_they': round(sum(x[2] for x in near if x[1] != we) / max(1, sum(1 for x in near if x[1] != we)), 2),
                       'weak_we': sum(1 for x in near if x[1] == we and x[2] < 0.6),
                       'died': None, 'taken': None, 'by': None, 'cap_gems': 0, 'on_we': 0, 'on_they': 0,
                       'first_hit': None, 'hits_we': 0, 'hits_they': 0, 'deaths_we': 0, 'deaths_they': 0,
                       'camp_kills_we': 0, 'camp_kills_they': 0}
            if cur is not None:
                if not alive and alive_prev:
                    cur['died'] = r
                if gr:
                    for c in rr['ch']:
                        if c[7] and (c[3], c[4]) in tiles:
                            cur['on_we' if c[1] == we else 'on_they'] += 1
            alive_prev = alive
        if cur:
            rows.append(cur)
    # fill hits / captures / deaths per cycle
    for row in rows:
        gg = G[row['gid']]
        tiles = set(gg['tiles'])
        nxt = [x['start'] for x in rows if x['gid'] == row['gid'] and x['start'] > row['start']]
        end = min(nxt) if nxt else final + 1
        hs = sorted((r, t) for i in gg['idx'] for (r, t) in hits[i] if row['start'] <= r < end)
        if hs:
            row['first_hit'] = 'we' if hs[0][1] == we else 'they'
        row['hits_we'] = sum(1 for r, t in hs if t == we)
        row['hits_they'] = sum(1 for r, t in hs if t != we)
        cs = [c for c in caps if row['start'] <= c[0] < end and c[3] in tiles]
        if cs:
            row['taken'] = cs[0][0]
            teams = Counter(c[1] for c in cs)
            row['by'] = 'we' if teams.get(we) and not teams.get(1 - we) else 'they' if teams.get(1 - we) and not teams.get(we) else 'split'
            row['cap_gems_we'] = sum(c[2] for c in cs if c[1] == we)
            row['cap_gems_they'] = sum(c[2] for c in cs if c[1] != we)
        for (r, t, p, by) in deaths:
            if row['start'] <= r < end and min(cheb(p, q) for q in tiles) <= 5:
                row['deaths_we' if t == we else 'deaths_they'] += 1
        row['end'] = end
    return rows


def main():
    maps = sys.argv[1:] or MAPS
    games = select(maps)
    out = []
    for g in games:
        out += run(g)
    with open(f'{BASE}/map_fail/out/cycles.jsonl', 'w') as f:
        for r in out:
            f.write(json.dumps(r) + '\n')
    for m in maps:
        rs = [r for r in out if r['map'] == m]
        if not rs:
            continue
        print(f'\n===== {m}')
        for res in ('L', 'W'):
            sel = [r for r in rs if r['res'] == res]
            if not sel:
                continue
            by = Counter(r['by'] for r in sel)
            fh = Counter(r['first_hit'] for r in sel)
            print(f'  {res}: cycles {len(sel)}  taken by {dict(by)}  first hit {dict(fh)}  gems we/they {sum(r.get("cap_gems_we", 0) for r in sel)}/{sum(r.get("cap_gems_they", 0) for r in sel)}')
            # cycles we started (first hit) and lost
            ws = [r for r in sel if r['first_hit'] == 'we']
            print(f'     we hit first {len(ws)}: taken by {dict(Counter(r["by"] for r in ws))}; deaths we/they in those {sum(r["deaths_we"] for r in ws)}/{sum(r["deaths_they"] for r in ws)}')
            ws = [r for r in sel if r['n_we'] >= 2]
            print(f'     2+ of ours within 4 at respawn: {len(ws)} -> taken by {dict(Counter(r["by"] for r in ws))}; mean hp we {sum(r["hp_we"] for r in ws) / max(1, len(ws)):.2f} vs they {sum(r["hp_they"] for r in ws if r["n_they"]) / max(1, sum(1 for r in ws if r["n_they"])):.2f}; weak(<60%) bodies {sum(r["weak_we"] for r in ws)}')
            for gid in sorted(set(r['gid'] for r in sel)):
                gs = [r for r in sel if r['gid'] == gid]
                print(f'     G{gid} ({gs[0]["gems"]}g): cycles {len(gs)} taken we {sum(1 for r in gs if r["by"] == "we")} they {sum(1 for r in gs if r["by"] == "they")} split {sum(1 for r in gs if r["by"] == "split")} none {sum(1 for r in gs if r["by"] is None)}'
                      f'; on-tile body-rounds we/they {sum(r["on_we"] for r in gs)}/{sum(r["on_they"] for r in gs)}; deaths we/they {sum(r["deaths_we"] for r in gs)}/{sum(r["deaths_they"] for r in gs)}')


if __name__ == '__main__':
    main()
