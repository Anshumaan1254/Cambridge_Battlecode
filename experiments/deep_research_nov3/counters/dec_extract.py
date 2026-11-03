#!/usr/bin/env python3
"""Per-game extraction of the decoded top-30 vs top-30 replays (experiments/top30_nov3/dec, ~1,200 games).

One row per game: teams (side a = team 0), winner, gap timeline (banked and banked+carried), decisive round (the round from
which the loser stays >= 150 gems behind on banked+carried until the end), deaths (round, bag, killer), captures, banks,
tribute starts and cancellations, altar locks, item counts at checkpoints.
Usage: nice -n 19 python3 -I dec_extract.py   -> out/dec_games.jsonl
"""
import json, os, glob, sys
from multiprocessing import Pool

BASE = '/home/claude/cambridge_battlecode/experiments/top30_nov3'
OUT = '/home/claude/cambridge_battlecode/experiments/deep_research_nov3/counters/out'
CHECK = list(range(100, 2001, 100))

idx = {}
for fn in (f'{BASE}/matches_current.jsonl', f'{BASE}/selection.jsonl'):
    for l in open(fn):
        m = json.loads(l)
        idx[(m['map'], m['matchId'][:8])] = m


def one(path):
    fn = os.path.basename(path)[:-5]
    mp, m8 = fn.rsplit('_', 1)
    m = idx.get((mp, m8))
    if m is None:
        return None
    try:
        d = json.load(open(path))
    except Exception:
        return None
    meta = d['meta']
    ta = [t for t in m['teams'] if t['side'] == 'a'][0]
    tb = [t for t in m['teams'] if t['side'] == 'b'][0]
    tid = [ta['teamId'], tb['teamId']]
    if ta['result'] == tb['result']:
        return None
    win = 0 if ta['result'] == 'win' else 1
    team = {b['index']: b['team'] for b in meta['bodies']}
    typ = {b['index']: b['type'] for b in meta['bodies']}
    final = meta['finalRound']
    rounds = d['rounds'][1:]
    bank = {}
    tot = {}
    items = {}
    gold = {}
    alive = {}
    bagof = {}  # (r, body) -> carried gems
    for rr in rounds:
        r = rr['r']
        car = [0, 0]
        it = [0, 0]
        gd = [0, 0]
        al = [0, 0]
        for c in rr['ch']:
            t = c[1]
            if c[7]:
                car[t] += c[8]
                al[t] += 1
            gd[t] += c[9]
            it[t] += sum(x[1] for x in c[11]) if c[11] else 0
            bagof[(r, c[0])] = c[8]
        bank[r] = rr['sub']
        tot[r] = [rr['sub'][0] + car[0], rr['sub'][1] + car[1]]
        if r in CHECK or r == final:
            items[r] = it
            gold[r] = gd
        alive[r] = al
    rs = sorted(tot)
    lose = 1 - win
    # decisive round on banked+carried and on banked
    def decisive(series):
        dr = None
        for r in reversed(rs):
            g = series[r][win] - series[r][lose]
            if g >= 150:
                dr = r
            else:
                break
        return dr
    dec_tot = decisive(tot)
    dec_bank = decisive(bank)
    # biggest loser lead
    ml, mlr = -10 ** 9, None
    for r in rs:
        g = tot[r][lose] - tot[r][win]
        if g > ml:
            ml, mlr = g, r
    # lead changes on totals (sign of winner-loser crossing with hysteresis 30)
    sgn = 0
    lc = 0
    for r in rs:
        g = tot[r][win] - tot[r][lose]
        s = 1 if g >= 30 else (-1 if g <= -30 else 0)
        if s and sgn and s != sgn:
            lc += 1
        if s:
            sgn = s
    deaths, caps, banks, subs, locks, golds = [], [], [], [], [], []
    for e in d['events']:
        k = e['k']
        if k == 'Death':
            by = e.get('by')
            kt = 'camp' if by == 'camp' else (typ.get(by, '?') if isinstance(by, int) else str(by))
            deaths.append([e['r'], e['team'], e['champ'], e.get('bag', 0), kt])
        elif k == 'CaptureGems':
            caps.append([e['r'], e['team'], e['champ'], e['gems'], e['gold'], e['at']])
        elif k == 'CaptureGold':
            golds.append([e['r'], e['team'], e['champ'], e['gold'], e['at']])
        elif k == 'Banked':
            banks.append([e['r'], e['team'], e['champ'], e['gems'], e['who']])
        elif k == 'Submit gems':
            subs.append([e['r'], e['team'], e['champ'], bagof.get((e['r'], e['who']), 0), e['who']])
        elif k == 'Place altar lock':
            locks.append([e['r'], e['team'], e['champ'], e['to']])
    # tribute cancellations: a Submit start with no Banked of that body within ceil(bag/10)+3 rounds
    bk_by = {}
    for r, t, ch, g, who in banks:
        bk_by.setdefault(who, []).append(r)
    canc = []
    for r, t, ch, bag, who in subs:
        dur = max(1, -(-bag // 10))
        ok = any(r <= x <= r + dur + 3 for x in bk_by.get(who, []))
        if not ok and bag > 0:
            canc.append([r, t, ch, bag])
    tl = {r: [bank[r][0], bank[r][1], tot[r][0], tot[r][1]] for r in rs if r in CHECK or r == final}
    return {'mid': m['matchId'], 'm8': m8, 'map': mp, 'tid': tid, 'names': [ta['name'], tb['name']], 'win': win, 'final': final,
            'end': m.get('endReason'), 'n': meta['champsPerTeam'], 'drafts': meta['drafts'], 'dec_tot': dec_tot, 'dec_bank': dec_bank,
            'max_loser_lead': ml, 'max_loser_lead_r': mlr, 'lead_changes': lc, 'tl': tl, 'items': items, 'gold': gold,
            'deaths': deaths, 'caps': caps, 'golds': golds, 'banks': banks, 'subs': [s[:4] for s in subs], 'canc': canc, 'locks': locks,
            'fin': [bank[final][0] if final in bank else None, bank[final][1] if final in bank else None]}


if __name__ == '__main__':
    files = sorted(glob.glob(f'{BASE}/dec/*.json'))
    done = set()
    if os.path.exists(f'{OUT}/dec_games.jsonl'):
        for l in open(f'{OUT}/dec_games.jsonl'):
            try:
                done.add(json.loads(l)['m8'])
            except Exception:
                pass
    lad = json.load(open(f'{BASE}/ladder.json'))['teams']
    t10 = {t['teamId'] for t in lad if t['rank'] <= 10}
    def prio(f):
        fn = os.path.basename(f)[:-5]
        mp, m8 = fn.rsplit('_', 1)
        m = idx.get((mp, m8))
        k = sum(1 for t in m['teams'] if t['teamId'] in t10) if m else 0
        return (-k, hash(m8) % 1000)
    files = sorted([f for f in files if os.path.basename(f)[:-5].rsplit('_', 1)[1] not in done], key=prio)
    print('todo', len(files), 'done', len(done), flush=True)
    n = 0
    with Pool(2) as pool, open(f'{OUT}/dec_games.jsonl', 'a') as fo:
        for row in pool.imap_unordered(one, files, chunksize=4):
            if row:
                fo.write(json.dumps(row) + '\n')
                fo.flush()
                n += 1
    print('games', n, 'of', len(files))
