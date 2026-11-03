#!/usr/bin/env python3
"""Aggregates of out/opening.jsonl (rounds 1-150 per body) by map, result and team.
    python3 -I map_fail/opening_summary.py > map_fail/out/opening_summary.txt"""
import json, sys
from collections import Counter, defaultdict
sys.path.insert(0, '/home/claude/cambridge_battlecode/experiments/ladder_nov2/agent_fights')
import extract as X  # noqa: E402
B = '/home/claude/cambridge_battlecode/experiments/ladder_nov2/map_fail/out'
rows = [json.loads(l) for l in open(f'{B}/opening.jsonl')]
games = {json.loads(l)['mid']: json.loads(l) for l in open(f'{B}/opening_games.jsonl')}
KS = ['walk-to', 'walk-home', 'walk-other', 'flee', 'hit', 'capture', 'fight', 'wait-ready', 'wait-alive', 'idle', 'recall', 'spawn', 'dead']
mean = lambda xs: (sum(xs) / len(xs)) if xs else float('nan')
maps = list(dict.fromkeys(r['map'] for r in rows))


def team_stats(sel, gsel, side):
    out = {}
    nb = len(sel)
    sp = Counter()
    for r in sel:
        sp.update(r['split'])
    tot = sum(sp.values()) or 1
    out['split'] = {k: 100 * sp[k] / tot for k in KS}
    fh = [r['first_hit'] for r in sel if r['first_hit'] is not None]
    out['first_hit_body'] = mean(fh)
    out['no_hit_bodies'] = sum(1 for r in sel if r['first_hit'] is None or r['first_hit'] > 150)
    out['team_first_hit'] = mean([min([r['first_hit'] for r in sel if r['mid'] == m and r['first_hit'] is not None] or [151]) for m in gsel])
    out['first_cap'] = mean([games[m]['first_cap'][side] or 151 for m in gsel])
    caps = [c for m in gsel for c in games[m]['caps150'][side]]
    out['caps150'] = len(caps) / len(gsel)
    out['gems150'] = sum(c[3] for c in caps) / len(gsel)
    out['gold150'] = sum(c[4] for c in caps) / len(gsel)
    out['first_d'] = mean([r['first_d'] for r in sel if r['first_d'] is not None])
    out['first_rank'] = mean([r['first_rank'] for r in sel if r['first_rank'] is not None])
    out['first_rank1'] = sum(1 for r in sel if r['first_rank'] == 1) / max(1, sum(1 for r in sel if r['first_rank'] is not None))
    # stacking: distinct first targets per game / bodies with a first target
    st = []
    for m in gsel:
        ft = [r['first_target'] for r in sel if r['mid'] == m and r['first_target'] is not None]
        if ft:
            st.append(len(set(ft)) / len(ft))
    out['distinct_first'] = mean(st)
    out['abandon'] = sum(len(r['abandon']) for r in sel) / nb
    out['recalls'] = sum(len(r['recalls']) for r in sel) / nb
    out['shops'] = sum(len(set(r['shops'])) for r in sel) / nb
    out['deaths'] = sum(len(r['deaths']) for r in sel) / len(gsel)
    out['shards150'] = sum(X.shards(r['items150'] or []) for r in sel) / len(gsel)
    # visits started in r1-150
    vs = [v for r in sel for v in r['visits'] if v['first'] <= 150]
    out['visits_body'] = len(vs) / nb
    out['visit_kill'] = sum(1 for v in vs if v['kill']) / max(1, len(vs))
    out['visit_cap_own'] = sum(1 for v in vs if v['cap_by'] and (('us' in v['cap_by']) == (side == 'we'))) / max(1, len(vs))
    out['visit_cap_lost'] = sum(1 for v in vs if v['cap_by'] and (('us' in v['cap_by']) != (side == 'we'))) / max(1, len(vs))
    out['visit_nokill'] = sum(1 for v in vs if not v['kill']) / max(1, len(vs))
    out['hits_per_visit'] = mean([v['n'] for v in vs])
    out['bodies_per_visit'] = mean([len(v['team_bodies']) for v in vs])
    out['contested_visits'] = sum(1 for v in vs if v['enemy_bodies']) / max(1, len(vs))
    out['arr_to_hit'] = mean([v['first'] - v['arrive'] for v in vs])
    return out


with open(f'{B}/opening_summary.txt', 'w') as fo:
    fo.write('Opening (rounds 1-150) per map / result / team. Time split = share of body-rounds (see opening.py).\n')
    for m in maps:
        for res in ('L', 'W'):
            gsel = [mid for mid, g in games.items() if g['map'] == m and g['res'] == res]
            if not gsel:
                continue
            fo.write(f'\n===== {m} {res} ({len(gsel)} games)\n')
            S = {}
            for side in ('we', 'they'):
                sel = [r for r in rows if r['mid'] in gsel and r['side'] == side]
                S[side] = team_stats(sel, gsel, side)
            keys = [('team_first_hit', 'team first camp hit r'), ('first_hit_body', 'body first camp hit r (mean)'), ('no_hit_bodies', 'bodies with no camp hit by r150 (total)'),
                    ('first_cap', 'first capture r'), ('caps150', 'captures by r150 /game'), ('gems150', 'gems captured by r150 /game'), ('gold150', 'camp gold by r150 /game'),
                    ('shards150', 'item shards at r150 /team'), ('first_d', 'first target: BFS steps from spawn'), ('first_rank', 'first target: rank by distance (1 = nearest valued)'),
                    ('first_rank1', 'share of bodies whose first target is the nearest valued group'), ('distinct_first', 'distinct first targets / bodies (1 = all split, low = stacked)'),
                    ('visits_body', 'group visits started per body'), ('bodies_per_visit', 'own bodies hitting the same group in a visit'), ('hits_per_visit', 'hits per visit'),
                    ('visit_kill', 'visits that killed the group'), ('visit_cap_own', 'visits whose group we (this team) captured'), ('visit_cap_lost', 'visits whose group the OTHER team captured'),
                    ('contested_visits', 'visits with an enemy hitting the same group'), ('arr_to_hit', 'rounds from arrival (within 2) to first hit'),
                    ('abandon', 'abandoned approaches per body'), ('recalls', 'held recalls per body'), ('shops', 'shop visits per body'), ('deaths', 'deaths by r150 /game')]
            for k, label in keys:
                a, b = S['we'][k], S['they'][k]
                fmt = (lambda x: f'{x:.2f}') if isinstance(a, float) and abs(a) < 5 else (lambda x: f'{x:.0f}' if isinstance(x, float) else str(x))
                fo.write(f'  {label:62} we {fmt(a):>7}   they {fmt(b):>7}\n')
            fo.write('  time split % (we | they):\n')
            for k in ['walk-to', 'walk-home', 'walk-other', 'flee', 'hit', 'capture', 'fight', 'wait-ready', 'wait-alive', 'idle', 'recall', 'spawn', 'dead']:
                fo.write(f"     {k:11} {S['we']['split'][k]:5.1f} | {S['they']['split'][k]:5.1f}\n")
            # first targets
            for side in ('we', 'they'):
                ft = Counter()
                for mid in gsel:
                    for r in rows:
                        if r['mid'] == mid and r['side'] == side and r['first_target'] is not None:
                            v = r['visits'][0]
                            ft[(f"G{v['g']}", v['types'], v['gems'], v['gold'], v['d_spawn'], v['rank'])] += 1
                fo.write(f'  first targets {side}: ' + '; '.join(f'{k[0]} {k[1]} {k[2]}g/{k[3]}$ d{k[4]} #{k[5]} x{n}' for k, n in ft.most_common(8)) + '\n')
print(open(f'{B}/opening_summary.txt').read())
