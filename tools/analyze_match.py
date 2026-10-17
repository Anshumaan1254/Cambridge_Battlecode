#!/usr/bin/env python3
"""Summarise one or more CAMBC match statistics files (JSON) into a compact, pasteable report.

Produce the JSON with either:
  cambc run legend other --map M --statistics out.json --json
  cambc matches summary <MATCH_ID> --json -o out.json      (ladder / scrim matches; needs `cambc login`)
Numeric-id summaries (downloaded without --json) are converted to the named layout first, see normalise().

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


# Ladder/scrim summaries downloaded without --json (and the platform's JSON download) use numeric ids instead of
# names. These tables mirror the schema embedded in the cambc CLI (formatVersion 1.0, metricSemanticsVersion 1)
# and the SDK enums (champion_draft, champion_type, item_type); heatmaps are row-major (index = y * width + x).
METRIC_NAMES = ['earnedGold', 'spentGold', 'gold', 'gems', 'collectedGems', 'submittedGems', 'saleRefunds', 'kills',
                'deaths', 'assists', 'monsterDamageDone', 'monsterDamageTaken', 'championDamageDone',
                'championDamageTaken', 'healingDone', 'healingReceived', 'shieldingDone']
EVENT_KINDS = {1: 'death', 2: 'kill', 3: 'assist', 4: 'wardPlacement', 5: 'buyItem', 6: 'buyConsumable', 7: 'sellItem',
               8: 'campClear', 9: 'gemSubmission', 10: 'gemCollection', 11: 'gemLoss', 12: 'itemCombination',
               13: 'botFault', 14: 'fuelExhausted', 15: 'resignation'}
DRAFT_NAMES = ['Ryth', 'Vesper Vale', 'Vendetta', 'Cassi & Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren',
               'Varg', 'Tavi']
CHAMP_NAMES = ['Ryth', 'Vesper Vale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren',
               'Varg', 'Tavi']
ITEM_FAMILIES = ['Monster', 'Power', 'Durability', 'Treasure', 'Jungle', 'Home', 'Bruiser']
CONSUMABLE_NAMES = {0: 'TP Crystal', 2: 'Altar Lock'}  # SDK raw_consumable_ids {tp_crystal: 0, altar_lock: 2}
TEAM_NAMES = ['teamA', 'teamB']
# Context codes: death/gemLoss 1 = killed by a champion, 2 = by a camp; gemCollection 1 = camp group, 2 = champion.
DEATH_CONTEXT = {'1': 'champion', '2': 'camp'}
GEM_SOURCE = {'1': 'campGroup', '2': 'champion'}


def _name(table, i):
    return table[i] if 0 <= i < len(table) else f'#{i}'


def item_name(i):
    fam, rest = divmod(int(i), 6)
    stat, emblem = divmod(rest, 2)
    return f"{_name(ITEM_FAMILIES, fam)} {'Emblem' if emblem else 'Shard'} of {('Strength', 'Focus', 'Health')[stat]}"


def normalise(d):
    """Convert a numeric-id summary into the named layout produced by `--json`; named files pass through unchanged."""
    if not isinstance(d['match'].get('outcome'), int):
        return d
    team = lambda t: _name(TEAM_NAMES, int(t))
    m = dict(d['match'])
    m['outcome'] = {1: 'teamA', 2: 'teamB'}.get(m['outcome'], 'draw')
    roster = d.get('roster', {})
    who = {}
    for c in roster.get('champions', []):
        who[c['id']] = {'id': c['id'], 'kind': 'champion', 'name': _name(CHAMP_NAMES, c['type']), 'team': team(c['team'])}
    out = dict(d)
    out['match'] = m
    out['roster'] = {
        'draft': [{'team': team(p['team']), 'champion': _name(DRAFT_NAMES, p['type'])} for p in roster.get('draft', [])],
        'champions': [dict(who[c['id']], draftPick=c['draftPick']) for c in roster.get('champions', [])],
    }
    out['teams'] = [{'team': team(t['id']), 'submittedGems': t['submittedGems']} for t in d['teams']]
    inv = lambda lst, key, fn: [{key: fn(x['id']), 'quantity': x['quantity']} for x in lst]
    cons = lambda i: CONSUMABLE_NAMES.get(int(i), f'#{i}')
    out['champions'] = [dict(name=who[c['id']]['name'], team=who[c['id']]['team'], id=c['id'],
                             metrics={_name(METRIC_NAMES, x['id']): x['value'] for x in c['metrics']},
                             items=inv(c.get('items', []), 'item', item_name),
                             itemsBought=inv(c.get('itemsBought', []), 'item', item_name),
                             consumables=inv(c.get('consumables', []), 'consumable', cons),
                             consumablesBought=inv(c.get('consumablesBought', []), 'consumable', cons))
                        for c in d['champions']]
    out['teamTimelines'] = [dict(t, owner=team(t['owner']), metric='submittedGems') for t in d.get('teamTimelines', [])]
    out['championTimelines'] = [dict(t, owner=who.get(t['owner'], t['owner']), metric=_name(METRIC_NAMES, t['metric']))
                                for t in d.get('championTimelines', [])]
    events = []
    for s in d.get('events', []):
        kind = EVENT_KINDS.get(s['kind'], str(s['kind']))
        entries = []
        for e in s['entries']:
            e = dict(e)
            ctx = str(e.get('context', ''))
            if kind in ('death', 'gemLoss'):
                e['context'] = DEATH_CONTEXT.get(ctx, ctx)
                e['target'] = who.get(e['target'], {'id': e['target'], 'kind': 'camp'}) if ctx == '1' else {'id': e['target'], 'kind': 'camp'}
            elif kind == 'gemCollection':
                e['context'] = GEM_SOURCE.get(ctx, ctx)
                e['target'] = who.get(e['target'], e['target']) if ctx == '2' else {'id': e['target'], 'kind': 'campGroup'}
            elif kind in ('kill', 'assist'):
                e['target'] = who.get(e['target'], e['target'])
            elif kind in ('buyItem', 'sellItem', 'itemCombination'):
                e['target'] = {'kind': 'item', 'name': item_name(e['target'])}
            elif kind == 'buyConsumable':
                e['target'] = {'kind': 'consumable', 'name': cons(e['target'])}
            entries.append(e)
        events.append({'owner': who.get(s['owner'], s['owner']), 'kind': kind, 'entries': entries})
    out['events'] = events
    return out


def analyse(path, us_hint, brief):
    d = normalise(json.load(open(path)))
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
