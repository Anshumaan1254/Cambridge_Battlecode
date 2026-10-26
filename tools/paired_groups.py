#!/usr/bin/env python3
"""Paired ladder A/B with unranked match groups (games are deterministic: same bot pair + map + side = same game).

1. plan:   python tools/paired_groups.py plan  MATCHES_ME.jsonl --since ISO [--until ISO] [--opp NAME ...] > plan.json
           the groups the OLD live version played (opponent, its source group, the five maps and our sides, our results)
2. run:    python tools/paired_groups.py run   plan.json [--max N]          (only after the user made the NEW version live)
           re-creates every planned group against the same opponent version (--source-group) on the same maps and sides
           and records the new group ids in plan.json
3. report: python tools/paired_groups.py report plan.json MATCHES_ME.jsonl  (after `fetch_me.py` has the new games)
           old vs new result per map and in total.

Read-only except `run`, which spends the team's unranked quota (allowed by the user; never submits or activates a version).
"""
import json
import subprocess
import sys
import collections

ME = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'


def load(p):
    return [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]


def plan(args):
    p = args[0]
    since = args[args.index('--since') + 1] if '--since' in args else ''
    until = args[args.index('--until') + 1] if '--until' in args else '9'
    opps = [args[i + 1].lower() for i, a in enumerate(args) if a == '--opp']
    G = collections.defaultdict(list)
    for m in load(p):
        if m['kind'] != 'unranked' or m['status'] != 'finished' or not (since <= m['createdAt'] <= until):
            continue
        G[m['groupId']].append(m)
    out = []
    seen = set()
    for gid, ms in G.items():
        ms.sort(key=lambda m: m.get('position', 0))
        me = [[t for t in m['teams'] if t['teamId'] == ME][0] for m in ms]
        op = [t for t in ms[0]['teams'] if t['teamId'] != ME][0]
        if opps and not any(o in op['name'].lower() for o in opps):
            continue
        key = (op['teamId'], tuple(m['map'] for m in ms), tuple(t['side'] for t in me))
        if key in seen or len(ms) != 5:
            continue
        seen.add(key)
        out.append({'opp': op['name'], 'oppId': op['teamId'], 'sourceGroup': gid, 'maps': [m['map'] for m in ms],
                    'sides': [t['side'] for t in me], 'old': [t['result'] for t in me], 'new_group': None})
    json.dump(out, sys.stdout, indent=1)


def run(args):
    p = args[0]
    mx = int(args[args.index('--max') + 1]) if '--max' in args else 999
    P = json.load(open(p, encoding='utf-8'))
    n = 0
    for g in P:
        if g['new_group'] or n >= mx:
            continue
        cmd = ['cambc', 'match-groups', 'create', g['oppId'], '--source-group', g['sourceGroup'], '--maps', ','.join(g['maps']),
               '--sides', ','.join(g['sides']), '--json']
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if r.returncode != 0:
            print('failed', g['opp'], r.stderr[:300])
            continue
        try:
            d = json.loads(r.stdout)
            g['new_group'] = d.get('groupId') or d.get('id') or d.get('group', {}).get('id')
        except json.JSONDecodeError:
            g['new_group'] = r.stdout.strip()[:80]
        n += 1
        print('queued', g['opp'], g['maps'], '->', g['new_group'])
        json.dump(P, open(p, 'w', encoding='utf-8'), indent=1)


def report(args):
    P = json.load(open(args[0], encoding='utf-8'))
    M = collections.defaultdict(list)
    for m in load(args[1]):
        M[m['groupId']].append(m)
    tot = collections.Counter()
    for g in P:
        if not g['new_group'] or g['new_group'] not in M:
            continue
        ms = sorted(M[g['new_group']], key=lambda m: m.get('position', 0))
        new = [[t for t in m['teams'] if t['teamId'] == ME][0]['result'] for m in ms]
        for mp, o, nw in zip(g['maps'], g['old'], new):
            tot['old_' + o] += 1
            tot['new_' + nw] += 1
            tot['flip_' + o + '_' + nw] += 1
        print('%-24s %s old %s new %s' % (g['opp'][:24], ','.join(g['maps']), ''.join('W' if r == 'win' else 'L' for r in g['old']), ''.join('W' if r == 'win' else 'L' for r in new)))
    print(dict(tot))


if __name__ == '__main__':
    {'plan': plan, 'run': run, 'report': report}[sys.argv[1]](sys.argv[2:])
