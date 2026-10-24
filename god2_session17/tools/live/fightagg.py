# Aggregate tools/live/fightan.mjs output (an.jsonl): deaths (patterns), engagements (starts / outcomes), contacts (take / avoid),
# top-vs-top fight predictors and conversion. Prints the tables used in experiments/live/an_fights.md.
#   python tools/live/fightagg.py C:/battlecode/cache/an_fights/an.jsonl [section...]
import json, sys, math
from collections import Counter, defaultdict

src = sys.argv[1]
want = set(sys.argv[2:])
G = [json.loads(l) for l in open(src, encoding='utf-8') if l.strip()]
G = [g for g in G if 'deaths' in g]
OURS = [g for g in G if g['set'] in ('rp_bb4D', 'rp_ft52D') and g['ours'] is not None]
TOP = [g for g in G if g['set'] == 'rp_top']
print(f'games: ours vs top10 {len(OURS)} (bb4D {sum(g["set"]=="rp_bb4D" for g in OURS)}, ft52D {sum(g["set"]=="rp_ft52D" for g in OURS)}), top-vs-top {len(TOP)}')

MELEE = {'Ryth', 'Vendetta', 'Issac', 'Marcella', 'Ren', 'Varg', 'HeartOfRuin'}
DASH = {'VesperVale', 'Vendetta', 'Issac', 'Ren', 'HeartOfRuin'}


def pct(a, b):
    return f'{100.0 * a / b:.1f}%' if b else '-'


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float('nan')


def section(name):
    return not want or name in want


def mode2(x):
    # recomputed from the activity tokens: a Recall / Submit step counts as a channel only in a round without moves or hits
    # (several top bots issue a Recall step every turn while walking and fighting)
    if x['mode'] in ('linked', 'camp'):
        return x['mode']
    t = x['act'].split(' ')
    chan = lambda k, c: c in k and not any(z in k for z in 'FCawm')
    l3, l5 = t[-3:], t[-5:]
    if any(chan(k, 'B') for k in l3):
        return 'banking'
    if sum(chan(k, 'R') for k in l5) >= 2:
        return 'recalling'
    if any('F' in k for k in l3):
        return 'fighting'
    if any('C' in k for k in l3):
        return 'farming'
    if any('k' in k for k in l3) and not any(z in ''.join(l3) for z in 'awm'):
        return 'capturing'
    aw = sum(k.count('w') for k in l5)
    ap = sum(k.count('a') for k in l5)
    if aw > ap:
        return 'fleeing'
    if ap > aw:
        return 'approaching'
    return 'stunned' if any('s' in k for k in l3) else 'walking'


def fight_before(x):
    t = x['act'].split(' ')
    return any('F' in k for k in t[:7])


def pattern(x):
    m = mode2(x)
    if m in ('linked',):
        return None
    if m == 'camp':
        return 'camp kill'
    if m in ('banking', 'recalling'):
        return 'channel (bank/recall)'
    if m in ('farming', 'capturing'):
        return 'caught farming/capturing'
    l6 = x['l6']
    if m == 'fighting':
        mine, theirs = l6['n'][0], l6['n'][1]  # victim side includes the victim
        if theirs > mine:
            return 'fight: outnumbered'
        if l6['mh'][1] > 1.15 * l6['mh'][0]:
            return 'fight: even numbers, weaker'
        return 'fight: even/ahead'
    if m == 'fleeing':
        return 'fleeing after fighting' if fight_before(x) else 'fleeing, no fight'
    if m == 'approaching':
        return 'walking into them (approach)'
    return 'walking/stunned/other'


def death_rows(games, who):
    rows = []
    for g in games:
        for x in g['deaths']:
            if who == 'us' and x['team'] != g['ours']:
                continue
            if who == 'them' and x['team'] == g['ours']:
                continue
            x = dict(x)
            x['game'] = g['game']
            x['won'] = (g['res'][x['team']] == 'win') if g.get('res') else None
            rows.append(x)
    return rows


DR = {'us': death_rows(OURS, 'us'), 'them(vs us)': death_rows(OURS, 'them'), 'top-vs-top': death_rows(TOP, 'all')}
NG = {'us': len(OURS), 'them(vs us)': len(OURS), 'top-vs-top': 2 * len(TOP)}  # top: per team-game

if section('deaths'):
    print('\n=== DEATHS per team-game (all / r<=300 / r<=150), linked C&I partner deaths excluded')
    for k, rows in DR.items():
        rr = [x for x in rows if mode2(x) != 'linked']
        print(f'{k:14s} n={len(rr):5d} per game {len(rr)/NG[k]:.2f}  r<=300 {sum(x["r"]<=300 for x in rr)/NG[k]:.2f}  r<=150 {sum(x["r"]<=150 for x in rr)/NG[k]:.2f}  bag/game {sum(x["bag"] for x in rr)/NG[k]:.0f}')
    for lim in (300, 2001):
        print(f'\n--- death patterns, rounds <= {lim} (share of deaths; per team-game)')
        cnt = {k: Counter(pattern(x) for x in rows if x['r'] <= lim and pattern(x)) for k, rows in DR.items()}
        keys = sorted(set().union(*cnt.values()), key=lambda p: -cnt['us'][p])
        print(f'{"pattern":32s}' + ''.join(f'{k:>24s}' for k in DR))
        for p in keys:
            print(f'{p:32s}' + ''.join(f'{cnt[k][p]:6d} {pct(cnt[k][p], sum(cnt[k].values())):>7s} {cnt[k][p]/NG[k]:5.2f}/g ' for k in DR))
        print(f'{"total":32s}' + ''.join(f'{sum(cnt[k].values()):6d} {"":>7s} {sum(cnt[k].values())/NG[k]:5.2f}/g ' for k in DR))

    print('\n--- per pattern details (rounds <= 300): bag, hp at sequence start, seq rounds, own-side n / enemy n within 6, max-hp ratio within 8 (victim side / enemy), idle allies within 8, own dmg 10r, trade, zone own/mid/their, killer melee share')
    for k, rows in DR.items():
        print(f'[{k}]')
        by = defaultdict(list)
        for x in rows:
            if x['r'] <= 300 and pattern(x):
                by[pattern(x)].append(x)
        for p, xs in sorted(by.items(), key=lambda kv: -len(kv[1])):
            ratio = [(x['l8']['mh'][0] / x['l8']['mh'][1]) if x['l8']['mh'][1] else None for x in xs]
            idle = [sum(1 for a in x['allies'] if not a['hit']) for x in xs]
            z = Counter(x['zone'] for x in xs)
            km = sum(1 for x in xs if x['by'] in MELEE) / len(xs)
            print(f'  {p:30s} n={len(xs):4d} bag {mean([x["bag"] for x in xs]):5.1f} hpS {mean([x["hpS"] for x in xs]):.2f} seq {mean([x["seq"] for x in xs]):4.1f} '
                  f'n6 {mean([x["l6"]["n"][0] for x in xs]):.2f}v{mean([x["l6"]["n"][1] for x in xs]):.2f} mhR {mean(ratio):.2f} idle {mean(idle):.2f} own {mean([x["own"] for x in xs]):5.0f} '
                  f'trade {mean([1 if x["trade"] else 0 for x in xs]):.2f} zone {z["own"]}/{z["mid"]}/{z["their"]} kmelee {km:.2f} natk {mean([x["natk"] for x in xs]):.2f}')

    print('\n--- location of deaths (r<=300 / all): own / mid / their half, within 8 of their spawn')
    for k, rows in DR.items():
        for lim in (300, 2001):
            rr = [x for x in rows if x['r'] <= lim and mode2(x) != 'linked']
            z = Counter(x['zone'] for x in rr)
            print(f'  {k:14s} r<={lim:4d} own {pct(z["own"], len(rr))} mid {pct(z["mid"], len(rr))} their {pct(z["their"], len(rr))} nearSpawn(<=8) {pct(sum(x["dTheir"]<=8 for x in rr), len(rr))}')

    print('\n--- killers (champion type share of kills, r<=300) and victims')
    for k, rows in DR.items():
        rr = [x for x in rows if x['r'] <= 300 and mode2(x) not in ('linked',)]
        c = Counter(x['by'] for x in rr)
        v = Counter(x['v'] for x in rr)
        print(f'  {k:14s} killers: ' + ', '.join(f'{a} {pct(b, len(rr))}' for a, b in c.most_common(8)))
        print(f'  {"":14s} victims: ' + ', '.join(f'{a} {pct(b, len(rr))}' for a, b in v.most_common(8)))

    print('\n--- numbers at the death (within 6, 1 round before; victim side incl. victim vs enemies), r<=300')
    for k, rows in DR.items():
        rr = [x for x in rows if x['r'] <= 300 and mode2(x) not in ('linked', 'camp')]
        c = Counter()
        for x in rr:
            a, e = x['l6']['n'][0], x['l6']['n'][1]
            c['outnumbered' if e > a else 'even' if e == a else 'ahead'] += 1
        solo = sum(1 for x in rr if x['l6']['n'][0] <= 1)
        idle_any = sum(1 for x in rr if any((not a['hit']) and a['hpf'] >= 0.5 for a in x['allies']))
        none_help = sum(1 for x in rr if x['allies'] and not any(a['hit'] for a in x['allies']))
        print(f'  {k:14s} n={len(rr)} outnumbered {pct(c["outnumbered"], len(rr))} even {pct(c["even"], len(rr))} ahead {pct(c["ahead"], len(rr))} | alone within 6 {pct(solo, len(rr))} | '
              f'healthy ally within 8 not hitting {pct(idle_any, len(rr))} | allies within 8 but none hit {pct(none_help, len(rr))} | mean attackers {mean([x["natk"] for x in rr]):.2f} | own dmg 0 in 10r {pct(sum(x["own"]==0 for x in rr), len(rr))}')
        doing = Counter()
        for x in rr:
            for a in x['allies']:
                if not a['hit']:
                    doing['farm' if a['farm'] else 'channel' if a['chan'] else 'moving' if a['mv'] >= 3 else 'still'] += 1
        print(f'  {"":14s} idle allies doing: ' + ', '.join(f'{a} {b}' for a, b in doing.most_common()))

    print('\n--- hp at the start of the fatal damage sequence (r<=300), and max hp of victim vs attackers')
    for k, rows in DR.items():
        rr = [x for x in rows if x['r'] <= 300 and mode2(x) not in ('linked', 'camp')]
        hi = sum(1 for x in rr if (x['hpS'] or 0) >= 0.6)
        mr = [x['mh'] / mean(x['atkMh']) for x in rr if x['atkMh'] and x['mh']]
        print(f'  {k:14s} hpS>=0.6 {pct(hi, len(rr))} mean hpS {mean([x["hpS"] for x in rr]):.2f} seq {mean([x["seq"] for x in rr]):.1f} r | victim maxhp / attackers maxhp {mean(mr):.2f} | killer hp left {mean([x["killerHp"] for x in rr]):.2f} | exposure (rounds enemy within 8) {mean([x["expo"] for x in rr]):.1f}')
