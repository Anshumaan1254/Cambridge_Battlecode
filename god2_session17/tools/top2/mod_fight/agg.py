# mod_fight: aggregate one bench measurement (tools/top2/mod_fight/measure.sh) per side: A = "ours" (the bot under test), B = the other.
#   NEAR  body-rounds with an enemy champion within 8 (alive, not on its own spawn; gap_g8 nearbehav.mjs): shares of farm / fight / chan /
#         toward / away / side / still, overall and when locally > 1.5x stronger (max health within 8); per game.
#   ARR   arrivals at farmers (an enemy comes within 8 of a body that hit a camp in its last 3 rounds): keep / fight / recall / leave /
#         toward / hold / dead in the next 5 rounds; died within 20; captured within 20.
#   DEATHS per game by fightan mode; ENG engagements (>= 3 hits or a death) per game, started by each side, our deaths / theirs per
#         engagement, and the share of each side's starts made below 0.67 of the other side's local max health (within 8 of the first hit).
#   python tools/top2/mod_fight/agg.py C:/battlecode/cache/modfight/TAG
import json, sys, collections, os
O = sys.argv[1]
S = json.load(open(os.path.join(O, 'sides.json'), encoding='utf-8'))
names = next(iter(S.values()))['names']
def side_name(k):
    return 'A' if k == 0 else 'B'
near = [collections.Counter(), collections.Counter()]
near_hi = [collections.Counter(), collections.Counter()]
arr = [collections.Counter(), collections.Counter()]
games = 0
for l in open(os.path.join(O, 'nearbehav.jsonl'), encoding='utf-8'):
    r = json.loads(l)
    if 'err' in r or r['file'] not in S:
        continue
    games += 1
    ours = S[r['file']]['ours']
    for k, n in r['near'].items():
        t, rb, hb, a = k.split('|')
        who = 0 if int(t) == ours else 1
        near[who][a] += n
        if rb == 'e>1.5':
            near_hi[who][a] += n
    for k, n in r['arr'].items():
        p = k.split('|')
        who = 0 if int(p[0]) == ours else 1
        key = p[2] + ('|' + p[3] if len(p) > 3 else '')
        arr[who][key] += n
print('games', games, '| A =', names[S[next(iter(S))]['ours']], 'B = the other bot')
acts = ['farm', 'fight', 'chan', 'toward', 'away', 'side', 'still']
for who in (0, 1):
    tot = sum(near[who].values()); hi = sum(near_hi[who].values())
    print('NEAR %s: %.0f body-rounds/game | ' % (side_name(who), tot / games) + ' '.join('%s %.1f%%' % (a, 100 * near[who][a] / max(1, tot)) for a in acts)
          + ' | walk %.1f%%' % (100 * (near[who]['toward'] + near[who]['away'] + near[who]['side']) / max(1, tot)))
    print('   >1.5x: %.0f/game | ' % (hi / games) + ' '.join('%s %.1f%%' % (a, 100 * near_hi[who][a] / max(1, hi)) for a in acts))
resp = ['keep', 'fight', 'recall', 'leave', 'toward', 'hold', 'dead']
for who in (0, 1):
    n = sum(arr[who][x] for x in resp)
    print('ARR %s: %.1f/game | ' % (side_name(who), n / games) + ' '.join('%s %.0f%%' % (x, 100 * arr[who][x] / max(1, n)) for x in resp)
          + ' | died<=20 %.0f%% cap<=20 %.0f%%' % (100 * sum(arr[who][x + '|died'] for x in resp) / max(1, n), 100 * sum(arr[who][x + '|cap'] for x in resp) / max(1, n)))
# fightan
modes = collections.Counter(), collections.Counter()
eng = [collections.Counter(), collections.Counter()]
fg = 0
for l in open(os.path.join(O, 'fightan.jsonl'), encoding='utf-8'):
    r = json.loads(l)
    if 'err' in r or r.get('ours') is None:
        continue
    fg += 1
    ours = r['ours']
    for d in r['deaths']:
        who = 0 if d['team'] == ours else 1
        modes[who][d['mode']] += 1
    for e in r['engs']:
        if sum(e['hits']) < 3 and sum(e['dE']) == 0:
            continue
        st = e['first']['team']
        who = 0 if st == ours else 1
        mh = e['loc8']['mh']
        q = mh[0] / mh[1] if mh[1] > 0 else 9
        eng[who]['n'] += 1
        eng[who]['low'] += q < 0.67
        eng[who]['mid'] += 0.67 <= q < 0.87
        eng[who]['d_st'] += e['dE'][st]
        eng[who]['d_ot'] += e['dE'][1 - st]
for who in (0, 1):
    tot = sum(modes[who].values())
    print('DEATHS %s: %.2f/game | ' % (side_name(who), tot / fg) + ' '.join('%s %.2f' % (m, modes[who][m] / fg) for m, _ in modes[who].most_common()))
for who in (0, 1):
    e = eng[who]
    print('ENG started by %s: %.2f/game | below 0.67: %.2f/game (%.0f%% of its starts), 0.67-0.87: %.0f%% | starter deaths %.2f / other %.2f per eng' % (
        side_name(who), e['n'] / fg, e['low'] / fg, 100 * e['low'] / max(1, e['n']), 100 * e['mid'] / max(1, e['n']), e['d_st'] / max(1, e['n']), e['d_ot'] / max(1, e['n'])))
