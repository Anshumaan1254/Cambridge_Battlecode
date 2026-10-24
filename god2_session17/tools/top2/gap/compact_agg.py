# gap_g8: per-game platform-summary metrics for the S0 games (us = HouseOfCoders = g8 vs prism best girl / IFish / Claudus Maximus).
# Input: C:/battlecode/cache/gap_g8/sides.json (tools/top2/gap/sides.py) + experiments/live/compact/<matchId>.json (tools/live/summ.py).
# Output: C:/battlecode/cache/gap_g8/compact_games.jsonl (one row per game, 'us' / 'them' blocks) and printed tables by opponent.
#   python tools/top2/gap/compact_agg.py
import json, os, collections, statistics as st
SIDES = 'C:/battlecode/cache/gap_g8/sides.json'
CDIR = 'C:/battlecode/Cambridge_Battlecode/experiments/live/compact'
OUT = 'C:/battlecode/cache/gap_g8/compact_games.jsonl'
sides = json.load(open(SIDES, encoding='utf-8'))
PH = [(0, 300), (300, 600), (600, 1000), (1000, 99999)]
def ph(r):
    for i, (a, b) in enumerate(PH):
        if a <= r < b: return i
    return 3
FAM = ['Monster', 'Power', 'Durability', 'Treasure', 'Jungle', 'Home', 'Bruiser']
rows = []
for name, S in sides.items():
    p = os.path.join(CDIR, S['match'] + '.json')
    if not os.path.exists(p): print('missing compact', name); continue
    d = json.load(open(p, encoding='utf-8'))
    tk_us = 'teamA' if S['ours'] == 0 else 'teamB'
    out = {'game': name, 'map': S['map'], 'opp': S['opp'], 'side': 'a' if S['ours'] == 0 else 'b', 'win': int(S['res'][S['ours']] == 'win'),
           'rounds': d['rounds'], 'end': d['endReason']}
    for who, tk in (('us', tk_us), ('them', 'teamB' if tk_us == 'teamA' else 'teamA')):
        T = {}
        T['gems'] = next(t['gems'] for t in d['teams'] if t['team'] == tk)
        ch = [c for c in d['champs'] if c['team'] == tk]
        for k in ('earnedGold', 'spentGold', 'collectedGems', 'submittedGems', 'monsterDamageDone', 'monsterDamageTaken', 'championDamageDone',
                  'championDamageTaken', 'healingReceived', 'healingDone', 'shieldingDone', 'kills', 'deaths', 'assists'):
            T[k] = round(sum(c['m'].get(k, 0) for c in ch), 1)
        T['bodies'] = len(ch)
        de = [x for x in d['deaths'] if x[1] == tk]
        T['deaths_n'] = len(de)
        T['deaths_camp'] = sum(1 for x in de if x[4] == 'camp')
        T['deaths_ph'] = [sum(1 for x in de if ph(x[0]) == i) for i in range(4)]
        T['deaths_camp_ph'] = [sum(1 for x in de if ph(x[0]) == i and x[4] == 'camp') for i in range(4)]
        T['first_death'] = de[0][0] if de else None
        T['first_death_camp'] = (de[0][4] == 'camp') if de else None
        T['death_champ'] = collections.Counter(x[2] for x in de)
        ki = [x for x in d['kills'] if x[1] == tk]
        T['kills_n'] = len(ki)
        T['first_kill'] = ki[0][0] if ki else None
        cl = [x for x in d['clears'] if x[1] == tk]
        T['clears'] = len(cl)
        T['clears_ph'] = [sum(1 for x in cl if ph(x[0]) == i) for i in range(4)]
        T['first_clear'] = cl[0][0] if cl else None
        T['clears_r'] = [x[0] for x in cl]
        co = [x for x in d['colls'] if x[1] == tk]
        T['coll_camp'] = sum(int(x[6]) for x in co if x[4] == 'campGroup')
        T['coll_champ'] = sum(int(x[6]) for x in co if x[4] != 'campGroup')
        T['coll_ctx'] = collections.Counter(x[4] for x in co)
        T['coll_camp_ph'] = [sum(int(x[6]) for x in co if x[4] == 'campGroup' and ph(x[0]) == i) for i in range(4)]
        lo = [x for x in d['losses'] if x[1] == tk]
        T['lost_gems'] = sum(int(x[6]) for x in lo)
        T['lost_gems_champ'] = sum(int(x[6]) for x in lo if x[4] != 'camp')
        T['lost_gems_camp'] = sum(int(x[6]) for x in lo if x[4] == 'camp')
        T['lost_ph'] = [sum(int(x[6]) for x in lo if ph(x[0]) == i) for i in range(4)]
        su = [x for x in d['subs'] if x[1] == tk]
        T['banks'] = len(su)
        T['banked'] = sum(int(x[6]) for x in su)
        T['first_bank'] = su[0][0] if su else None
        T['bank_sizes'] = [int(x[6]) for x in su]
        T['bank_r'] = [x[0] for x in su]
        bu = [x for x in d['buys'] if x[1] == tk]
        T['spent_items'] = sum(float(x[7] or 0) for x in bu)
        T['spent_ph'] = [sum(float(x[7] or 0) for x in bu if ph(x[0]) == i) for i in range(4)]
        fam = collections.Counter()
        stat = collections.Counter()
        for x in bu:
            nm = x[5][2] if isinstance(x[5], list) else str(x[5])
            f = nm.split()[0]
            fam[f] += float(x[7] or 0)
            stat[nm.split()[-1]] += float(x[7] or 0)
        T['spend_fam'] = dict(fam)
        T['spend_stat'] = dict(stat)
        first = {}
        for x in bu:
            if x[3] not in first: first[x[3]] = (x[0], x[5][2] if isinstance(x[5], list) else x[5])
        T['first_buys'] = list(first.values())
        cs = [x for x in d['cons'] if x[1] == tk]
        T['cons'] = dict(collections.Counter(x[5][2] if isinstance(x[5], list) else str(x[5]) for x in cs))
        T['cons_gold'] = sum(float(x[7] or 0) for x in cs)
        T['wards'] = d['wards'].get(tk, 0)
        T['fuel'] = sum(1 for x in d['fuel'] if x[1] == tk)
        T['fuel_late'] = sum(1 for x in d['fuel'] if x[1] == tk and x[0] >= 10)
        T['faults'] = sum(1 for x in d['faults'] if x[1] == tk)
        tl = d['team_tl'].get(tk + ':submittedGems', [])
        def at(r):
            v = 0
            for rr, val in tl:
                if rr <= r: v = val
            return v
        T['sub_at'] = {r: at(r) for r in (100, 200, 300, 400, 600, 800, 1000)}
        T['draft'] = next(t['draft'] for t in d['teams'] if t['team'] == tk)
        T['items_final'] = {c['name']: c['items'] for c in ch}
        out[who] = T
    rows.append(out)
with open(OUT, 'w', encoding='utf-8') as f:
    for r in rows: f.write(json.dumps(r) + '\n')
print(len(rows), 'games ->', OUT)

def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float('nan')
def med(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else float('nan')
opps = ['prism best girl', 'Intercontinental Fish', 'Claudus Maximus', None]
print('%-22s %4s %5s | %-28s | %-28s' % ('opp', 'n', 'win', 'us', 'them'))
keys = ['gems', 'earnedGold', 'spentGold', 'spent_items', 'cons_gold', 'deaths_n', 'deaths_camp', 'kills_n', 'clears', 'coll_camp', 'coll_champ',
        'lost_gems', 'lost_gems_champ', 'banks', 'banked', 'first_bank', 'first_clear', 'first_death', 'wards', 'fuel', 'fuel_late',
        'monsterDamageDone', 'championDamageDone', 'healingReceived', 'shieldingDone']
for o in opps:
    G = [r for r in rows if o is None or r['opp'] == o]
    print('== %s n=%d wins=%d rounds %.0f' % (o or 'ALL', len(G), sum(r['win'] for r in G), mean([r['rounds'] for r in G])))
    for k in keys:
        print('   %-20s us %8.1f  them %8.1f   (med us %s them %s)' % (k, mean([r['us'][k] for r in G]), mean([r['them'][k] for r in G]),
              med([r['us'][k] for r in G]), med([r['them'][k] for r in G])))
    for i in range(4):
        print('   phase %d deaths us %.2f (camp %.2f) them %.2f (camp %.2f) | clears us %.1f them %.1f | camp gems us %.0f them %.0f | spent us %.0f them %.0f | lost us %.0f them %.0f' % (
            i, mean([r['us']['deaths_ph'][i] for r in G]), mean([r['us']['deaths_camp_ph'][i] for r in G]), mean([r['them']['deaths_ph'][i] for r in G]),
            mean([r['them']['deaths_camp_ph'][i] for r in G]), mean([r['us']['clears_ph'][i] for r in G]), mean([r['them']['clears_ph'][i] for r in G]),
            mean([r['us']['coll_camp_ph'][i] for r in G]), mean([r['them']['coll_camp_ph'][i] for r in G]), mean([r['us']['spent_ph'][i] for r in G]),
            mean([r['them']['spent_ph'][i] for r in G]), mean([r['us']['lost_ph'][i] for r in G]), mean([r['them']['lost_ph'][i] for r in G])))
    for r_ in (100, 200, 300, 400, 600, 800, 1000):
        print('   banked@%d us %.0f them %.0f' % (r_, mean([r['us']['sub_at'][r_] for r in G]), mean([r['them']['sub_at'][r_] for r in G])))
