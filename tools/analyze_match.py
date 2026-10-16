#!/usr/bin/env python3
"""Summarise one or more CAMBC match statistics files (JSON) into a compact, pasteable report.

Produce the JSON with either:
  cambc run legend other --map M --statistics out.json --json
  cambc matches summary <MATCH_ID> --json -o out.json      (ladder / scrim matches; needs `cambc login`)

usage: analyze_match.py FILE.json [FILE.json ...] [--us teamA|teamB|BOTNAME] [--brief]

The report covers: result and pace, drafts, gem timeline, every death (where, when, killed by what,
gems lost), kills of carriers, gold and items, and a short list of automatic diagnoses that map to
tunables in bots/legend/src/params.h.
"""
import argparse, collections, json, sys

MARKS = (100, 200, 300, 400, 500, 750, 1000, 1500, 2000)


def runs_value_at(runs, t):
    """Timeline runs are (duration, value) segments; return the value at sample index t."""
    acc = 0
    last = 0
    for r in runs:
        acc += int(r['duration'])
        last = int(float(r['value']))
        if acc > t:
            return last
    return last


def analyse(path, us_hint, brief):
    d = json.load(open(path))
    m = d['match']
    rounds = m['roundsCompleted']
    teams = {t['team']: int(t['submittedGems']) for t in d['teams']}
    roster = d.get('roster', {})
    draft = collections.defaultdict(list)
    for p in roster.get('draft', []):
        draft[p['team']].append(p['champion'])
    names = {c['id']: (c['name'], c['team']) for c in d['champions']}

    us = 'teamA'
    if us_hint in ('teamA', 'teamB'):
        us = us_hint
    them = 'teamB' if us == 'teamA' else 'teamA'

    out = []
    w = out.append
    w(f'## {path}')
    outcome = m['outcome']
    res = 'WIN' if outcome == us else ('LOSS' if outcome == them else outcome)
    w(f'result: {res} for {us} | rounds {rounds} | gems {us} {teams.get(us, 0)} - {teams.get(them, 0)} {them} | map {m.get("width")}x{m.get("height")}')
    w(f'draft {us}: {", ".join(draft[us])}')
    w(f'draft {them}: {", ".join(draft[them])}')

    # Gem timeline
    tl = {t['owner']: t['runs'] for t in d.get('teamTimelines', []) if t['metric'] == 'submittedGems'}
    if tl:
        row = []
        for mk in MARKS:
            if mk > rounds + 1:
                break
            row.append(f'r{mk}:{runs_value_at(tl.get(us, []), mk)}-{runs_value_at(tl.get(them, []), mk)}')
        w('submitted gems over time (us-them): ' + '  '.join(row))

    # Per-champion metrics
    w('champions:')
    agg = {us: collections.Counter(), them: collections.Counter()}
    for c in d['champions']:
        mt = c['metrics']
        t = c['team']
        for k in ('kills', 'deaths', 'collectedGems', 'submittedGems', 'earnedGold', 'spentGold'):
            agg[t][k] += int(mt[k])
        for k in ('championDamageDone', 'championDamageTaken', 'monsterDamageDone', 'monsterDamageTaken', 'healingDone'):
            agg[t][k] += float(mt[k])
        if not brief:
            items = ', '.join(f"{i['item']}x{i['quantity']}" for i in c.get('items', []))
            w(f"  {t[-1]} {c['name']:12s} K{mt['kills']:>3} D{mt['deaths']:>3} collected {mt['collectedGems']:>4} submitted {mt['submittedGems']:>4} "
              f"gold {mt['earnedGold']:>5} dmg->champs {float(mt['championDamageDone']):7.0f} dmg->camps {float(mt['monsterDamageDone']):8.0f} "
              f"taken champs {float(mt['championDamageTaken']):6.0f} camps {float(mt['monsterDamageTaken']):6.0f} | {items}")
    for t in (us, them):
        a = agg[t]
        w(f"  total {t}: kills {a['kills']} deaths {a['deaths']} collected {a['collectedGems']} submitted {a['submittedGems']} "
          f"gold {a['earnedGold']} (spent {a['spentGold']}) champ-dmg {a['championDamageDone']:.0f} camp-dmg {a['monsterDamageDone']:.0f}")

    # Deaths and gem losses
    deaths = []
    losses = {}
    for ev in d['events']:
        owner = ev['owner']
        if ev['kind'] == 'gemLoss':
            for e in ev['entries']:
                losses[(owner.get('id'), e['timestamp']['round'])] = int(float(e['value']))
    for ev in d['events']:
        if ev['kind'] != 'death':
            continue
        owner = ev['owner']
        for e in ev['entries']:
            r = e['timestamp']['round']
            by = e.get('target', {})
            killer = by.get('name') or by.get('kind', '?')
            ctx = e.get('context', '')
            deaths.append((r, owner.get('team'), owner.get('name'), killer if ctx == 'champion' else f'camp', e.get('x'), e.get('y'),
                           losses.get((owner.get('id'), r), 0)))
    deaths.sort()
    by_cause = collections.Counter((t, k == 'camp') for _, t, _, k, _, _, _ in deaths)
    w(f"deaths: {us} {by_cause[(us, False)]} to champions + {by_cause[(us, True)]} to camps | "
      f"{them} {by_cause[(them, False)]} to champions + {by_cause[(them, True)]} to camps")
    bag_lost = collections.Counter()
    for r, t, n, k, x, y, g in deaths:
        bag_lost[t] += g
    w(f'gems carried into deaths: {us} {bag_lost[us]}  {them} {bag_lost[them]}')
    if not brief:
        for r, t, n, k, x, y, g in deaths[:60]:
            w(f'  r{r:4d} {t} {n:12s} killed by {k:12s} at ({x},{y}) carrying {g}')
        if len(deaths) > 60:
            w(f'  ... {len(deaths) - 60} more')

    # Diagnoses
    diag = []
    a, b = agg[us], agg[them]
    if by_cause[(us, True)] >= 3:
        diag.append(f'{by_cause[(us, True)]} camp deaths: raise camp_hp_reserve / retreat_hp (params.h)')
    if by_cause[(us, False)] > by_cause[(them, False)] + 3:
        diag.append('losing champion fights: raise fight_margin, lower threat_memory reach, retreat earlier')
    if bag_lost[us] > 60:
        diag.append(f'{bag_lost[us]} gems died with us: lower tribute_min / tribute_risky')
    if a['collectedGems'] and a['submittedGems'] < 0.85 * a['collectedGems']:
        diag.append('large share of collected gems never banked: tribute more often')
    if b['submittedGems'] > a['submittedGems'] and by_cause[(them, False)] <= 2 and by_cause[(us, False)] <= 2:
        diag.append('pure farming race lost: farming throughput is the gap (route/kill speed/items)')
    if a['earnedGold'] < 0.7 * b['earnedGold']:
        diag.append('earning much less gold: raise gold_value')
    if res != 'WIN' and rounds >= 1990:
        diag.append('went to the round limit: tiebreak is gold earned, then kills')
    w('diagnosis: ' + ('; '.join(diag) if diag else 'nothing obvious'))
    return '\n'.join(out), res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+')
    ap.add_argument('--us', default='teamA', help='teamA or teamB (the side your bot played)')
    ap.add_argument('--brief', action='store_true')
    args = ap.parse_args()
    tally = collections.Counter()
    for f in args.files:
        text, res = analyse(f, args.us, args.brief)
        tally[res] += 1
        print(text)
        print()
    if len(args.files) > 1:
        print('overall: ' + ', '.join(f'{k} {v}' for k, v in tally.items()))


if __name__ == '__main__':
    main()
