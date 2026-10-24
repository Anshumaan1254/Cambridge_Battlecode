# Ability use: study teams (S) vs their opponents in the same games (O), from ab.mjs output (one line per fight dump).
#   python tools/top2/items/agg_ab.py C:/battlecode/cache/top2_items/ab_all.jsonl > report.txt
import sys, json, collections
sys.path.insert(0, 'tools/top2/items')
from common import *

AB = sys.argv[1]
idx = load_index()
KIT = {
    'Ryth': ['aoestun', 'reset'], 'VesperVale': ['reset', 'dash'], 'Vendetta': ['reset', 'dash'], 'Cassi': ['dmg', 'stun'],
    'Issac': ['reset', 'dash'], 'Stellar': ['dmg', 'aoe'], 'Prism': ['dmgstun', 'aoe'], 'Marcella': ['ereset', 'dmg'],
    'Willow': ['heal', 'reset'], 'Ren': ['dmgstun', 'dash'], 'Varg': ['reset', 'shield'], 'Tavi': ['reset', 'dmgstun'],
    'HeartOfRuin': ['shield', 'hordash'],
}
games = {}
for l in open(AB, encoding='utf-8'):
    try:
        g = json.loads(l)
    except Exception:
        continue
    games[g['file']] = g
rows = []
for stem, g in games.items():
    for st in idx.get(stem, []):
        for b in g['B']:
            grp = 'S' if b['t'] == st['ti'] else 'O'
            rows.append(dict(key=st['key'], grp=grp, ty=b['ty'], b=b, stem=stem, win=st['win'] if grp == 'S' else not st['win']))
P = print
P(f'# dumps with ab data: {len(games)}; body rows {len(rows)}')

def agg(R, f):
    return sum(f(x['b']) for x in R)

# ------------------------------------------------------------ 1. casts per 100 alive rounds, per champion and slot
P('\n## 1. Casts per body per 100 alive rounds (slot 0 / slot 1), cast share of ready turns by context F fight / N enemy within 5 / C camp work / O other')
P('| team | champ | grp | bodies | s0 kind | casts/100r s0 | s1 kind | casts/100r s1 | s0 use F / N / C / O | s1 use F / N / C / O | turn ctx share F / N / C |')
P('|---|---|---|---|---|---|---|---|---|---|---|')
for key in KEYS:
    types = collections.Counter(x['ty'] for x in rows if x['key'] == key and x['grp'] == 'S')
    for ty, n in types.most_common():
        if n < 5:
            continue
        for grp in 'SO':
            R = [x for x in rows if x['key'] == key and x['grp'] == grp and x['ty'] == ty]
            if not R:
                continue
            al = agg(R, lambda b: b['alive'])
            us = agg(R, lambda b: b['usable'])
            c = [agg(R, lambda b, s=s: b['sl'][s]['casts']) for s in (0, 1)]
            def use(s):
                out = []
                for k in 'FNCO':
                    rd = agg(R, lambda b: b['sl'][s]['ready'][k]); rc = agg(R, lambda b: b['sl'][s]['rcast'][k])
                    out.append(pct(rc, rd))
                return ' / '.join(out)
            ctx = ' / '.join(pct(agg(R, lambda b, k=k: b['ctx'][k]), us) for k in 'FNC')
            P(f'| {key} | {SHORT[ty]} | {grp} | {len(R)} | {KIT[ty][0]} | {100*c[0]/max(1,al):.2f} | {KIT[ty][1]} | {100*c[1]/max(1,al):.2f} | {use(0)} | {use(1)} | {ctx} |')

# ------------------------------------------------------------ 2. effect classes
P('\n## 2. Cast effect classes per slot (shares of casts)')
P('| team | champ | grp | slot kind | casts | classes |')
P('|---|---|---|---|---|---|')
for key in KEYS:
    types = collections.Counter(x['ty'] for x in rows if x['key'] == key and x['grp'] == 'S')
    for ty, n in types.most_common():
        if n < 5:
            continue
        for s in (0, 1):
            if KIT[ty][s] == 'reset' or KIT[ty][s] == 'ereset':
                continue
            for grp in 'SO':
                R = [x for x in rows if x['key'] == key and x['grp'] == grp and x['ty'] == ty]
                if not R:
                    continue
                cl = collections.Counter()
                for x in R:
                    for k, v in x['b']['sl'][s]['cls'].items():
                        cl[k] += v
                tot = sum(cl.values())
                P(f'| {key} | {SHORT[ty]} | {grp} | {KIT[ty][s]} | {tot} | ' + ', '.join(f'{k} {100*v/tot:.0f}%' for k, v in cl.most_common()) + ' |')

# ------------------------------------------------------------ 3. attack turns on champions
P('\n## 3. Turns with a basic attack hitting an enemy champion: reset ready -> used, sequences (M move, D dash, A hit, K killing hit, R reset, C other cast, a camp hit)')
P('| team | champ | grp | attack turns / body-game | reset ready at start | used when ready | ended farther from nearest enemy | top sequences |')
P('|---|---|---|---|---|---|---|---|')
for key in KEYS:
    types = collections.Counter(x['ty'] for x in rows if x['key'] == key and x['grp'] == 'S')
    for ty, n in types.most_common():
        if n < 5 or not any(k in ('reset', 'ereset') for k in KIT[ty]):
            continue
        for grp in 'SO':
            R = [x for x in rows if x['key'] == key and x['grp'] == grp and x['ty'] == ty]
            if not R:
                continue
            t = agg(R, lambda b: b['atk']['turns']); rd = agg(R, lambda b: b['atk']['ready']); us = agg(R, lambda b: b['atk']['used'])
            lf = agg(R, lambda b: b['atk']['left'])
            sq = collections.Counter()
            for x in R:
                for k, v in x['b']['atk']['seq'].items():
                    sq[k] += v
            P(f'| {key} | {SHORT[ty]} | {grp} | {t/len(R):.1f} | {pct(rd,t)} | {pct(us,rd)} | {pct(lf,t)} | ' + ', '.join(f'{k} {100*v/max(1,t):.0f}%' for k, v in sq.most_common(6)) + ' |')

# ------------------------------------------------------------ 4. shields, heals
P('\n## 4. Shields (pre-emptive = no damage taken in the previous round or earlier this round) and heals')
P('| team | champ | grp | shields / body-game | pre-emptive | enemy within 4 | in a fight | hit within 5 r |')
P('|---|---|---|---|---|---|---|---|')
for key in KEYS:
    for ty in ('HeartOfRuin', 'Varg'):
        for grp in 'SO':
            R = [x for x in rows if x['key'] == key and x['grp'] == grp and x['ty'] == ty]
            if len(R) < 3:
                continue
            n = agg(R, lambda b: b['shield']['n'])
            P(f'| {key} | {SHORT[ty]} | {grp} | {n/len(R):.1f} | {pct(agg(R, lambda b: b["shield"]["pre"]), n)} | {pct(agg(R, lambda b: b["shield"]["en4"]), n)} | {pct(agg(R, lambda b: b["shield"]["fight"]), n)} | {pct(agg(R, lambda b: b["shield"]["hit5"]), n)} |')
P('| team | grp | Willow bodies | heals / body-game | mean missing HP of the target | mean target hp fraction | target in a fight |')
P('|---|---|---|---|---|---|---|')
for key in KEYS:
    for grp in 'SO':
        R = [x for x in rows if x['key'] == key and x['grp'] == grp and x['ty'] == 'Willow']
        if not R:
            continue
        n = agg(R, lambda b: b['heal']['n'])
        P(f'| {key} | {grp} | {len(R)} | {n/len(R):.1f} | {agg(R, lambda b: b["heal"]["miss"])/max(1,n):.0f} | {agg(R, lambda b: b["heal"]["frac"])/max(1,n):.2f} | {pct(agg(R, lambda b: b["heal"]["fight"]), n)} |')

# ------------------------------------------------------------ 5. stuns
P('\n## 5. Stuns on enemy champions (per team-game), victims channelling a tribute or a real recall (recall spammers excluded), kills within 3 rounds')
P('| team | grp | team-games | stuns / game | on tributes (bags) | on real recalls | on spam recalls | victim died within 3 r | by champion (stuns / game) |')
P('|---|---|---|---|---|---|---|---|---|')
stunex = collections.defaultdict(list)
for key in KEYS:
    for grp in 'SO':
        R = [x for x in rows if x['key'] == key and x['grp'] == grp]
        if not R:
            continue
        G = len({x['stem'] for x in R})
        n = agg(R, lambda b: b['stun']['n'])
        bags = []
        for x in R:
            for e in x['b']['stun']['ex']:
                if e[0] == 'trib':
                    bags.append(e[3]); stunex[(key, grp)].append((x['stem'], e[1], SHORT[x['ty']], e[3]))
        by = collections.Counter()
        for x in R:
            by[SHORT[x['ty']]] += x['b']['stun']['n']
        P(f'| {key} | {grp} | {G} | {n/G:.1f} | {agg(R, lambda b: b["stun"]["trib"])} ({"/".join(str(b) for b in sorted(bags, reverse=True)[:8])}) | {agg(R, lambda b: b["stun"]["recall"])} | {agg(R, lambda b: b["stun"].get("recallSpam", 0))} | {pct(agg(R, lambda b: b["stun"]["kill3"]), n)} | ' + ', '.join(f'{k} {v/G:.1f}' for k, v in by.most_common(5)) + ' |')
P('Stun-on-tribute examples (file, round, stunner, victim bag):')
for k, v in stunex.items():
    for e in sorted(v, key=lambda e: -e[3])[:5]:
        P(f'  {k}: {e}')

# ------------------------------------------------------------ 6. Prism and the bag
P('\n## 6. Prism: carried bag (share of alive rounds), casts by bag, damage per cast on champions / camps by bag')
for key in KEYS:
    for grp in 'SO':
        R = [x for x in rows if x['key'] == key and x['grp'] == grp and x['ty'] == 'Prism']
        if len(R) < 3:
            continue
        BB = ['0', '1-24', '25-49', '50-99', '100-199', '200+']
        al = collections.Counter(); ca = collections.Counter(); fi = collections.Counter(); dch = collections.defaultdict(lambda: [0, 0]); dcp = collections.defaultdict(lambda: [0, 0])
        for x in R:
            p = x['b']['prism']
            for k, v in p['bagRounds'].items(): al[k] += v
            for k, v in p['bag'].items(): ca[k] += v
            for k, v in p['bagFight'].items(): fi[k] += v
            for k, v in p['dmgCh'].items(): dch[k][0] += v[0]; dch[k][1] += v[1]
            for k, v in p['dmgCamp'].items(): dcp[k][0] += v[0]; dcp[k][1] += v[1]
        ta = sum(al.values()); tc = sum(ca.values()); tf = sum(fi.values())
        P(f'\n{key} {grp}: {len(R)} Prism bodies; casts / 100 alive r {100*tc/max(1,ta):.2f}; champion-exchange rounds {tf} ({100*tf/max(1,ta):.1f}% of alive rounds)')
        P('| bag | alive rounds | casts | casts per 100 rounds at this bag | exchange rounds | dmg per champion-hitting cast | dmg per camp-hitting cast |')
        P('|---|---|---|---|---|---|---|')
        for k in BB:
            P(f'| {k} | {pct(al[k],ta)} | {pct(ca[k],tc)} | {100*ca[k]/max(1,al[k]):.2f} | {fi[k]} | {fmt(dch[k][0]/dch[k][1]) if dch[k][1] else "-"} ({dch[k][1]}) | {fmt(dcp[k][0]/dcp[k][1]) if dcp[k][1] else "-"} ({dcp[k][1]}) |')

# ------------------------------------------------------------ 7. damage split
P('\n## 7. Damage on champions per body-game: basic attacks vs casts; camp damage')
P('| team | champ | grp | bodies | atk dmg on champs | cast dmg on champs | cast share | camp dmg (atk + cast) |')
P('|---|---|---|---|---|---|---|---|')
for key in KEYS:
    types = collections.Counter(x['ty'] for x in rows if x['key'] == key and x['grp'] == 'S')
    for ty, n in types.most_common():
        if n < 5:
            continue
        for grp in 'SO':
            R = [x for x in rows if x['key'] == key and x['grp'] == grp and x['ty'] == ty]
            if not R:
                continue
            a = agg(R, lambda b: b['dmg']['atkCh']) / len(R); c = agg(R, lambda b: b['dmg']['castCh']) / len(R)
            cp = (agg(R, lambda b: b['dmg']['atkCamp']) + agg(R, lambda b: b['dmg']['castCamp'])) / len(R)
            P(f'| {key} | {SHORT[ty]} | {grp} | {len(R)} | {fmt(a)} | {fmt(c)} | {pct(c, a + c)} | {fmt(cp)} |')
