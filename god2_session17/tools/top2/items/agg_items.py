# Items / consumables / wards / locks / crystals: study teams (S) vs their opponents in the same games (O), from ix.mjs output.
#   python tools/top2/items/agg_items.py C:/battlecode/cache/top2_items/ix_all.jsonl > report.txt
import sys, json, collections
sys.path.insert(0, 'tools/top2/items')
from common import *

IX = sys.argv[1]
idx = load_index()
games = []
for l in open(IX, encoding='utf-8'):
    try:
        g = json.loads(l)
    except Exception:
        continue
    stem = g['file'].replace('.repl26a', '')
    if stem not in idx:
        continue
    games.append((stem, g))

CPS = [100, 200, 300, 400, 600, 800, 1000]
rows = []  # per body
tg = []    # per team-game
for stem, g in games:
    for st in idx[stem]:
        key, ti = st['key'], st['ti']
        for b in g['B']:
            grp = 'S' if b['t'] == ti else 'O'
            win = st['win'] if grp == 'S' else (not st['win'])
            rows.append(dict(key=key, grp=grp, ty=b['ty'], win=win, b=b, final=g['final'], stem=stem, opp=st['opp']))
        for grp in 'SO':
            T = ti if grp == 'S' else 1 - ti
            win = st['win'] if grp == 'S' else (not st['win'])
            tg.append(dict(key=key, grp=grp, team=T, win=win, g=g, stem=stem, nb=sum(1 for b in g['B'] if b['t'] == T)))

def P(*a):
    print(*a)

P(f'# games with ix data: {len(games)} (study-team game rows {len(tg)//2})')
for key in KEYS:
    G = [t for t in tg if t['key'] == key and t['grp'] == 'S']
    P(f'{key}: {len(G)} games, W-L {sum(t["win"] for t in G)}-{sum(not t["win"] for t in G)}')

# ---------------------------------------------------------------- 1. gold / max hp / stats over time per team
P('\n## 1. Per body averages: gold earned / spent, max HP, damage stat (S = study team, O = its opponents in the same games)')
P('| team | grp | bodies | earned r300 | r600 | end | spent/earned end | held gold mean r300 / r600 | maxHp r100 | r200 | r300 | r400 | r600 | r800 | r1000 | emblems r300 / r600 | first emblem med |')
P('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
def cpv(b, r, i):
    c = b['cp'].get(str(r))
    return c[i] if c else None
for key in KEYS:
    for grp in 'SO':
        R = [x for x in rows if x['key'] == key and x['grp'] == grp]
        if not R:
            continue
        e3 = mean([cpv(x['b'], 300, 6) for x in R]); e6 = mean([cpv(x['b'], 600, 6) for x in R]); ee = mean([x['b']['earned'] for x in R])
        sp = sum(x['b']['spent'] for x in R) / max(1, sum(x['b']['earned'] for x in R))
        h3 = mean([cpv(x['b'], 300, 3) for x in R]); h6 = mean([cpv(x['b'], 600, 3) for x in R])
        mh = [mean([cpv(x['b'], r, 0) for x in R]) for r in CPS]
        em3 = mean([len([e for e in emblem_order(x['b']['buys']) if e[0] <= 300]) for x in R if x['final'] >= 300])
        em6 = mean([len([e for e in emblem_order(x['b']['buys']) if e[0] <= 600]) for x in R if x['final'] >= 600])
        fe = med([emblem_order(x['b']['buys'])[0][0] for x in R if emblem_order(x['b']['buys'])])
        P(f'| {key} | {grp} | {len(R)} | {fmt(e3)} | {fmt(e6)} | {fmt(ee)} | {sp:.2f} | {fmt(h3)} / {fmt(h6)} | ' + ' | '.join(fmt(v) for v in mh) + f' | {fmt(em3,2)} / {fmt(em6,2)} | {fmt(fe)} |')

# ---------------------------------------------------------------- 2. builds per team x champion
P('\n## 2. Builds per team and champion (first three emblems in completion order; share of bodies; then shard shares)')
for key in KEYS:
    P(f'\n### {key}')
    P('| champ | grp | n | top first-3 emblem orders | first buy (code) | first emblem med r | shard shares (top 6) | str/foc/hp pts r300 | r600 | maxHp r300 / r600 / r1000 | dmg stat r300 / r600 |')
    P('|---|---|---|---|---|---|---|---|---|---|---|')
    types = collections.Counter(x['ty'] for x in rows if x['key'] == key and x['grp'] == 'S')
    for ty, n in types.most_common():
        for grp in 'SO':
            R = [x for x in rows if x['key'] == key and x['grp'] == grp and x['ty'] == ty]
            if not R:
                continue
            orders = collections.Counter('>'.join(e[1] for e in emblem_order(x['b']['buys'])[:3]) or '(none)' for x in R)
            top = '; '.join(f'{o} {c}' for o, c in orders.most_common(3))
            fb = collections.Counter(code(min((bb for bb in x['b']['buys'] if bb[1] < 100), key=lambda q: q[0])[1]) for x in R if any(bb[1] < 100 for bb in x['b']['buys']))
            fbs = ', '.join(f'{o} {c}' for o, c in fb.most_common(2))
            fe = med([emblem_order(x['b']['buys'])[0][0] for x in R if emblem_order(x['b']['buys'])])
            sh = collections.Counter()
            for x in R:
                for bb in x['b']['buys']:
                    if bb[1] < 100:
                        sh[code(bb[1])] += bb[2]
            tot = sum(sh.values())
            shs = ', '.join(f'{c} {100*v/tot:.0f}%' for c, v in sh.most_common(6)) if tot else '-'
            def ptsat(r):
                vals = [points(se_at(x['b']['buys'], x['b']['sells'], r)) for x in R if x['final'] >= r]
                if not vals:
                    return '-'
                return '/'.join(f'{sum(v[i] for v in vals)/len(vals):.1f}' for i in range(3))
            def dmgat(r):
                vals = [stats(ty, se_at(x['b']['buys'], x['b']['sells'], r))[DMG_STAT.get(ty, 0)] for x in R if x['final'] >= r]
                return fmt(mean(vals))
            mh = ' / '.join(fmt(mean([cpv(x['b'], r, 0) for x in R])) for r in (300, 600, 1000))
            P(f'| {SHORT.get(ty, ty)} | {grp} | {len(R)} | {top} | {fbs} | {fmt(fe)} | {shs} | {ptsat(300)} | {ptsat(600)} | {mh} | {dmgat(300)} / {dmgat(600)} |')

# ---------------------------------------------------------------- 3. shopping
P('\n## 3. Shopping visits per body (a visit = purchases in one round)')
P('| team | grp | visits/body/game | per 100 alive rounds | gold before (median) | shards per visit | visits while dead | remote (Tavi) | first visit med r |')
P('|---|---|---|---|---|---|---|---|---|')
for key in KEYS:
    for grp in 'SO':
        R = [x for x in rows if x['key'] == key and x['grp'] == grp]
        if not R:
            continue
        nv, gb, spv, dead, rem, first, al = 0, [], [], 0, 0, [], 0
        for x in R:
            by = collections.defaultdict(list)
            for bb in x['b']['buys']:
                by[bb[0]].append(bb)
            al += x['b']['alive']
            rs = sorted(by)
            if rs:
                first.append(rs[0])
            for r in rs:
                L = by[r]
                nv += 1
                gb.append(max(q[3] for q in L))
                spv.append(sum(q[2] for q in L if q[1] < 100))
                if all(q[4] == 0 for q in L):
                    dead += 1
                if all(q[4] == 2 for q in L):
                    rem += 1
        P(f'| {key} | {grp} | {nv/len(R):.1f} | {100*nv/max(1,al):.2f} | {fmt(med(gb))} | {mean(spv):.1f} | {pct(dead,nv)} | {pct(rem,nv)} | {fmt(med(first))} |')

# ---------------------------------------------------------------- 4. consumables and wards per team-game
P('\n## 4. Consumables and wards per team-game')
P('| team | grp | games | crystals bought | crystals used | locks bought | locks placed | wards / body / 100 alive r | first ward med r | other consumables |')
P('|---|---|---|---|---|---|---|---|---|---|')
for key in KEYS:
    for grp in 'SO':
        G = [t for t in tg if t['key'] == key and t['grp'] == grp]
        if not G:
            continue
        cb = lb = cu = lp = oc = 0
        wn = al = 0
        fw = []
        for t in G:
            g = t['g']
            mine = {b['i'] for b in g['B'] if b['t'] == t['team']}
            for b in g['B']:
                if b['t'] != t['team']:
                    continue
                cb += sum(q[2] for q in b['buys'] if q[1] == 100)
                lb += sum(q[2] for q in b['buys'] if q[1] == 102)
                oc += sum(q[2] for q in b['buys'] if q[1] in (101, 103))
                al += b['alive']
            cu += sum(1 for x in g['tele'] if x['who'] in mine)
            lp += sum(1 for x in g['locks'] if x['who'] in mine)
            ws = [w for w in g['wards'] if w[1] in mine]
            wn += len(ws)
            if ws:
                fw.append(min(w[0] for w in ws))
        n = len(G)
        P(f'| {key} | {grp} | {n} | {cb/n:.2f} | {cu/n:.2f} | {lb/n:.2f} | {lp/n:.2f} | {100*wn/max(1,al):.2f} | {fmt(med(fw))} | {oc/n:.2f} |')

# ---------------------------------------------------------------- 5. altar locks in context
# Lock model (verified in replays, e.g. 00lost_world_5977a569 r302-320, 00corners_06869e89 r95-236): every team can hold its own lock
# on an altar; a lock blocks only the other team's tributes (their attempts become attacks on it), placing one cancels the other
# team's tribute channels at that altar, five attacks by the blocked team clear it. Lifetimes are recomputed here from the raw
# attacks on altar tiles (ix lockAtt), per (altar, team).
def lock_life(g):
    team = {b['i']: b['t'] for b in g['B']}
    out = []
    L = sorted(g['locks'], key=lambda x: x['r'])
    for i, x in enumerate(L):
        a, T, r0 = tuple(x['a']), x['t'], x['r']
        nxt = [y['r'] for y in L[i + 1:] if tuple(y['a']) == a and y['t'] == T]
        stop = nxt[0] if nxt else g['final'] + 1
        atk = [z for z in g['lockAtt'] if (z[2], z[3]) == a and team.get(z[1]) == 1 - T and r0 <= z[0] < stop]
        cleared = atk[4][0] if len(atk) >= 5 else -1
        end = cleared if cleared >= 0 else stop - 1 if nxt else g['final']
        own = [t for t in g['tribs'] if (t[2], t[3]) == a and team.get(t[1]) == T and r0 <= t[0] <= end]
        canc = [t for t in g['tribs'] if t[5] == 'lock' and t[6] == r0 and (t[2], t[3]) == a and team.get(t[1]) == 1 - T]
        out.append(dict(x=x, cleared=cleared, end=end, dur=end - r0, atk=len(atk[:5]), own=len([t for t in own if t[5] == 'ok']), ownG=sum(t[7] for t in own if t[5] == 'ok'),
                        canc=[(t[1], t[4]) for t in canc], refreshed=bool(nxt) and cleared < 0))
    return out

P()
P('## 5. Altar lock placements (S = study team placing, O = opponents placing)')
P('| team | grp | placed | per game | cancelled an enemy tribute (bags) | own tribute at that altar within 3 r | enemy carrier within 8 (mean max bag) | no enemy within 8 | altar nearer own spawn | cleared by enemy | median life (r) | own banks while it stood per lock (gems) | enemy attack turns spent per lock |')
P('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
lockex = collections.defaultdict(list)
for key in KEYS:
    for grp in 'SO':
        G = [t for t in tg if t['key'] == key and t['grp'] == grp]
        if not G:
            continue
        L = []
        for t in G:
            g = t['g']
            mine = {b['i'] for b in g['B'] if b['t'] == t['team']}
            for z in lock_life(g):
                x = z['x']
                if x['who'] in mine:
                    ownsoon = any(tr[1] in mine and tr[2] == x['a'][0] and tr[3] == x['a'][1] and x['r'] <= tr[0] <= x['r'] + 3 for tr in g['tribs'])
                    L.append((z, ownsoon, t['stem']))
        n = len(L)
        if not n:
            P(f'| {key} | {grp} | 0 | 0.00 | - | - | - | - | - | - | - | - | - |')
            continue
        canc = [z for z, o, s in L if z['canc']]
        cb = [c[1] for z in canc for c in z['canc']]
        own = sum(1 for z, o, s in L if o or z['x']['ownTrib'])
        car = [z for z, o, s in L if z['x']['enMaxBag8'] > 0]
        noen = sum(1 for z, o, s in L if z['x']['en8'] == 0)
        nearer = sum(1 for z, o, s in L if z['x']['aOwn'] < z['x']['aEnemy'])
        clr = sum(1 for z, o, s in L if z['cleared'] >= 0)
        P(f'| {key} | {grp} | {n} | {n/len(G):.2f} | {len(canc)} ({"/".join(str(c) for c in sorted(cb, reverse=True)[:6])}) | {pct(own,n)} | {len(car)} ({fmt(mean([z["x"]["enMaxBag8"] for z in car]))}) | {pct(noen,n)} | {pct(nearer,n)} | {pct(clr,n)} | {fmt(med([z["dur"] for z, o, s in L]))} | {sum(z["own"] for z, o, s in L)/n:.2f} ({sum(z["ownG"] for z, o, s in L)/n:.0f}) | {sum(z["atk"] for z, o, s in L)/n:.2f} |')
        for z, o, s in L:
            lockex[(key, grp)].append((s, z['x']['r'], z['x']['who'], z['x']['a'], z['canc'], o, z['x']['enMaxBag8'], z['x']['en8'], z['own'], z['dur']))
P()
P('Lock examples (file, round, body, altar, cancelled [(who, bag)], own tribute within 3 r, enemy max bag within 8, enemies within 8, own banks while standing, life):')
for key in KEYS:
    for e in lockex[(key, 'S')][:5]:
        P(f'  {key} S: {e}')
P('Cancelling placements (all):')
for k, v in lockex.items():
    for e in v:
        if e[4]:
            P(f'  {k}: {e}')

# ---------------------------------------------------------------- 6. wards
P('\n## 6. Ward placements (features at placement)')
P('| team | grp | wards | in bush | placer stood in bush | camp within 3 | altar within 3 | on the enemy side (nearer their spawn) | within 8 of their spawn | dist from placer mean | enemy within 8 of placer | r<100 share |')
P('|---|---|---|---|---|---|---|---|---|---|---|---|')
for key in KEYS:
    for grp in 'SO':
        G = [t for t in tg if t['key'] == key and t['grp'] == grp]
        W = []
        for t in G:
            mine = {b['i'] for b in t['g']['B'] if b['t'] == t['team']}
            W += [w for w in t['g']['wards'] if w[1] in mine]
        if not W:
            continue
        n = len(W)
        P(f'| {key} | {grp} | {n} | {pct(sum(w[4] for w in W),n)} | {pct(sum(w[11] for w in W),n)} | {pct(sum(w[5]<=3 for w in W),n)} | {pct(sum(w[6]<=3 for w in W),n)} | {pct(sum(w[8]<w[7] for w in W),n)} | {pct(sum(w[8]<=8 for w in W),n)} | {mean([w[9] for w in W]):.1f} | {pct(sum(w[10]<=8 for w in W),n)} | {pct(sum(w[0]<100 for w in W),n)} |')

# ---------------------------------------------------------------- 7. teleport crystals
P('\n## 7. Teleport crystal uses')
P('| team | grp | uses | per game | completed | walk distance of the 3-tile hop (median) | unreachable on foot | saved >= 6 steps | enemy within 6 at start | carrying gems (mean bag) | destination camp within 3 | altar within 3 | far from spawn (>20) |')
P('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
for key in KEYS:
    for grp in 'SO':
        G = [t for t in tg if t['key'] == key and t['grp'] == grp]
        X = []
        for t in G:
            mine = {b['i'] for b in t['g']['B'] if b['t'] == t['team']}
            X += [x for x in t['g']['tele'] if x['who'] in mine]
        if not X:
            continue
        n = len(X)
        walks = [x['walk'] for x in X if x['walk'] >= 0]
        P(f'| {key} | {grp} | {n} | {n/len(G):.2f} | {pct(sum(1 for x in X if x["done"]),n)} | {fmt(med(walks))} | {pct(sum(1 for x in X if x["walk"]<0),n)} | {pct(sum(1 for x in X if x["walk"]<0 or x["walk"]-x["cheb"]>=6),n)} | {pct(sum(1 for x in X if x["en6"]>0),n)} | {pct(sum(1 for x in X if x["bag"]>0),n)} ({fmt(mean([x["bag"] for x in X if x["bag"]>0]))}) | {pct(sum(1 for x in X if x["campD"]<=3),n)} | {pct(sum(1 for x in X if x["altarD"]<=3),n)} | {pct(sum(1 for x in X if x["dOwn"]>20),n)} |')

# ---------------------------------------------------------------- 8. stuns on channelling enemies (ix)
P('\n## 8. Stuns landed on enemy champions and the victim channel (ix: stunned flag rises during the stunner\'s step)')
P('| team | grp | stuns on champions / game | victim tributing (n, bags) | victim in a recall open >= 1 round | stunner = camp |')
P('|---|---|---|---|---|---|')
for key in KEYS:
    for grp in 'SO':
        G = [t for t in tg if t['key'] == key and t['grp'] == grp]
        if not G:
            continue
        n = trib = rec = camp = 0
        bags = []
        for t in G:
            g = t['g']
            team = {b['i']: b['t'] for b in g['B']}
            for s in g['stuns']:
                r, a, v = s[0], s[1], s[2]
                if team.get(v) == t['team']:
                    continue  # victim is this team: count on the attacker side
                if a < 0:
                    camp += 1
                    continue
                if team.get(a) != t['team']:
                    continue
                n += 1
                if s[4] >= 0:
                    trib += 1; bags.append(s[4])
                if s[6] >= 1:
                    rec += 1
        P(f'| {key} | {grp} | {n/len(G):.1f} | {trib} ({"/".join(str(b) for b in sorted(bags, reverse=True)[:8])}) | {rec} | {camp} |')

# ---------------------------------------------------------------- 9. item power vs outcome
P('\n## 9. Team max-HP sum (alive or dead bodies) S / O ratio at r300 and r600, and the study team win rate by that ratio')
P('| team | games | ratio r300 median | S wins when ratio r300 >= 1.1 | 0.9-1.1 | < 0.9 | ratio r600 median | S wins when ratio r600 >= 1.1 | 0.9-1.1 | < 0.9 |')
P('|---|---|---|---|---|---|---|---|---|---|')
for key in KEYS:
    G = [t for t in tg if t['key'] == key and t['grp'] == 'S']
    if not G:
        continue
    def ratio(t, r):
        g = t['g']
        s = sum(b['cp'][str(r)][0] for b in g['B'] if b['t'] == t['team'] and str(r) in b['cp'])
        o = sum(b['cp'][str(r)][0] for b in g['B'] if b['t'] != t['team'] and str(r) in b['cp'])
        # normalise by body count (C&I = 2 bodies)
        ns = sum(1 for b in g['B'] if b['t'] == t['team']); no = sum(1 for b in g['B'] if b['t'] != t['team'])
        return (s / ns) / (o / no) if o and s else None
    cells = []
    for r in (300, 600):
        rs = [(ratio(t, r), t['win']) for t in G if t['g']['final'] >= r]
        rs = [x for x in rs if x[0] is not None]
        b = [[w for v, w in rs if v >= 1.1], [w for v, w in rs if 0.9 <= v < 1.1], [w for v, w in rs if v < 0.9]]
        cells.append(f'{med([v for v, w in rs]):.2f} | ' + ' | '.join(f'{pct(sum(x), len(x))} ({len(x)})' for x in b))
    P(f'| {key} | {len(G)} | ' + ' | '.join(cells) + ' |')

# ---------------------------------------------------------------- 10. stat mix of purchases
P('\n## 10. Stat mix of all shard purchases (points by stat incl. emblem bonuses) and gold on consumables per team-game')
P('| team | grp | str | foc | hp | consumable gold / game |')
P('|---|---|---|---|---|---|')
for key in KEYS:
    for grp in 'SO':
        R = [x for x in rows if x['key'] == key and x['grp'] == grp]
        if not R:
            continue
        tot = [0.0, 0.0, 0.0]
        for x in R:
            p = points(se_at(x['b']['buys'], x['b']['sells'], 10 ** 6))
            for i in range(3):
                tot[i] += p[i]
        s = sum(tot)
        G = len({x['stem'] for x in R})
        cg = sum(10 * q[2] for x in R for q in x['b']['buys'] if q[1] >= 100) / max(1, G)
        P(f'| {key} | {grp} | {pct(tot[0], s)} | {pct(tot[1], s)} | {pct(tot[2], s)} | {cg:.0f} |')

# ---------------------------------------------------------------- 11. survivability per champion and HP per gold
P('\n## 11. Deaths per body-game (by champions only), bag lost per death, and max-HP gained per 100 gold spent by r600 (per champion)')
P('| team | champ | grp | bodies | deaths / game | killed by champion | mean bag lost | HP gained per 100 gold by r600 | dmg stat gained per 100 gold by r600 |')
P('|---|---|---|---|---|---|---|---|---|')
for key in KEYS:
    types = collections.Counter(x['ty'] for x in rows if x['key'] == key and x['grp'] == 'S')
    for ty, n in types.most_common():
        if n < 5:
            continue
        for grp in 'SO':
            R = [x for x in rows if x['key'] == key and x['grp'] == grp and x['ty'] == ty]
            if not R:
                continue
            dd = [d for x in R for d in x['b']['deaths']]
            ch = [d for d in dd if d[2] != 'camp']
            hpg, dmg = [], []
            for x in R:
                c = x['b']['cp'].get('600')
                if not c or c[7] < 60:
                    continue
                s, f, hp = stats(ty, se_at(x['b']['buys'], x['b']['sells'], 600))
                s0, f0, hp0 = stats(ty, {})
                hpg.append(100 * (hp - hp0) / c[7])
                dmg.append(100 * ((f - f0) if DMG_STAT.get(ty) else (s - s0)) / c[7])
            P(f'| {key} | {SHORT[ty]} | {grp} | {len(R)} | {len(dd)/len(R):.2f} | {pct(len(ch), len(dd))} | {fmt(mean([d[1] for d in dd]))} | {fmt(mean(hpg))} | {fmt(mean(dmg),1)} |')
