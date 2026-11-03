#!/usr/bin/env python3
"""Aggregate out/games_top.jsonl + out/games_me.jsonl into the tables of REPORT.txt.
   nice -n 19 python3 report_stats.py > out/stats.txt
Columns: TOP = every top-30 side in top-30 vs top-30 games; ME = our side (v84-v88); OPP = our opponents in those games;
ME88 = our v88 games only."""
import json, os, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
OUT = f'{C.OBJ}/out'


def load(name):
    fn = f'{OUT}/games_{name}.jsonl'
    rows = {}
    if os.path.exists(fn):
        for l in open(fn):
            try:
                r = json.loads(l)
                rows[r['mid']] = r
            except Exception:
                pass
    return list(rows.values())


def mean(xs):
    xs = [x for x in xs if x is not None and x == x]
    return sum(xs) / len(xs) if xs else None


def fmt(x, nd=2):
    if x is None:
        return '-'
    if isinstance(x, float):
        return f'{x:.{nd}f}'
    return str(x)


class SideGames:
    """list of (row, t) pairs: the side t of game row"""
    def __init__(self, name, pairs):
        self.name = name
        self.pairs = pairs

    def __len__(self):
        return len(self.pairs)

    def side(self):
        for row, t in self.pairs:
            yield row, t, row['side'][str(t)] if str(t) in row['side'] else row['side'][t]


def side_of(row, t):
    return row['side'][str(t)]


def build_sets():
    top = load('top')
    me = load('me')
    TOP = SideGames('TOP', [(r, t) for r in top for t in (0, 1)])
    mepairs, opppairs, me88 = [], [], []
    for r in me:
        we = 0 if r['sides']['0']['id'] == C.ME else 1
        mepairs.append((r, we))
        opppairs.append((r, 1 - we))
        if r.get('ver') == 'v88':
            me88.append((r, we))
    return {'TOP': TOP, 'ME': SideGames('ME', mepairs), 'OPP': SideGames('OPP', opppairs), 'ME88': SideGames('ME88', me88)}


def table(title, sets, metrics):
    """metrics: list of (label, fn(row, t, side) -> value or None)"""
    print(f'\n## {title}')
    names = list(sets)
    print('metric'.ljust(58) + ''.join(n.rjust(12) for n in names))
    print(''.ljust(58) + ''.join(f'n={len(sets[n])}'.rjust(12) for n in names))
    for label, fn in metrics:
        vals = []
        for n in names:
            xs = []
            for row, t in sets[n].pairs:
                v = fn(row, t, side_of(row, t))
                if v is not None:
                    xs.append(v)
            vals.append(mean(xs))
        print(label.ljust(58) + ''.join(fmt(v).rjust(12) for v in vals))


def share(a, b):
    return a / b if b else None


def contested(cy):
    """a big group both teams reach about equally: within 20% of the spawn walk"""
    d0, d1 = cy['d']
    if d0 is None or d1 is None:
        return False
    return abs(d0 - d1) <= 0.2 * (d0 + d1)


def main():
    S = build_sets()
    print('games: top', len(S['TOP']) // 2, 'me', len(S['ME']), 'me88', len(S['ME88']))
    # ---------------- Q1 cycles
    def cyc_stats(row, t, s):
        cs = [c for c in row['cycles'] if not c['mono'] and contested(c)]
        return cs
    table('Q1 contested big groups (>=30 gems, |dA-dB| <= 20%): per side-game', S, [
        ('contested big-group cycles per game (respawn cycles, start>1)', lambda r, t, s: sum(1 for c in cyc_stats(r, t, s) if c['start'] > 1)),
        ('  of which captured by this side', lambda r, t, s: sum(1 for c in cyc_stats(r, t, s) if c['start'] > 1 and c['by'] == t)),
        ('  captured by the other side', lambda r, t, s: sum(1 for c in cyc_stats(r, t, s) if c['start'] > 1 and c['by'] == 1 - t)),
        ('  split', lambda r, t, s: sum(1 for c in cyc_stats(r, t, s) if c['start'] > 1 and c['by'] == 'split')),
        ('  never taken (cycle ran to game end)', lambda r, t, s: sum(1 for c in cyc_stats(r, t, s) if c['start'] > 1 and c['by'] is None)),
        ('share of contested respawn cycles captured (of taken)', lambda r, t, s: share(sum(1 for c in cyc_stats(r, t, s) if c['start'] > 1 and c['by'] == t), sum(1 for c in cyc_stats(r, t, s) if c['start'] > 1 and c['by'] in (0, 1)))),
        ('opening cycle (start=1) captured by this side (share)', lambda r, t, s: share(sum(1 for c in cyc_stats(r, t, s) if c['start'] == 1 and c['by'] == t), sum(1 for c in cyc_stats(r, t, s) if c['start'] == 1 and c['by'] in (0, 1)))),
        ('this side arrived first at the respawn (share of cycles with any arrival)', lambda r, t, s: share(sum(1 for c in cyc_stats(r, t, s) if c['start'] > 1 and c['first_arr'] == t), sum(1 for c in cyc_stats(r, t, s) if c['start'] > 1 and c['first_arr'] in (0, 1)))),
        ('  present within 4 AT the respawn round (share of cycles)', lambda r, t, s: share(sum(1 for c in cyc_stats(r, t, s) if c['start'] > 1 and c['arr'][str(t)] and c['arr'][str(t)]['wait'] >= 0), sum(1 for c in cyc_stats(r, t, s) if c['start'] > 1))),
        ('  waiting rounds before the respawn when present (mean)', lambda r, t, s: mean([c['arr'][str(t)]['wait'] for c in cyc_stats(r, t, s) if c['start'] > 1 and c['arr'][str(t)] and c['arr'][str(t)]['wait'] >= 0])),
        ('  bodies within 4 at the respawn when present (mean)', lambda r, t, s: mean([c['arr'][str(t)]['n'] for c in cyc_stats(r, t, s) if c['start'] > 1 and c['arr'][str(t)] and c['arr'][str(t)]['wait'] >= 0])),
        ('  mean hp of those bodies', lambda r, t, s: mean([c['arr'][str(t)]['hp'] for c in cyc_stats(r, t, s) if c['start'] > 1 and c['arr'][str(t)] and c['arr'][str(t)]['wait'] >= 0])),
        ('  arrived late: rounds after the respawn when not present (mean)', lambda r, t, s: mean([-c['arr'][str(t)]['wait'] for c in cyc_stats(r, t, s) if c['start'] > 1 and c['arr'][str(t)] and c['arr'][str(t)]['wait'] < 0])),
        ('  capture share when present at the respawn', lambda r, t, s: share(sum(1 for c in cyc_stats(r, t, s) if c['start'] > 1 and c['arr'][str(t)] and c['arr'][str(t)]['wait'] >= 0 and c['by'] == t), sum(1 for c in cyc_stats(r, t, s) if c['start'] > 1 and c['arr'][str(t)] and c['arr'][str(t)]['wait'] >= 0 and c['by'] in (0, 1)))),
        ('  capture share when the OTHER side was present at the respawn and we were not', lambda r, t, s: share(sum(1 for c in cyc_stats(r, t, s) if c['start'] > 1 and c['arr'][str(1 - t)] and c['arr'][str(1 - t)]['wait'] >= 0 and not (c['arr'][str(t)] and c['arr'][str(t)]['wait'] >= 0) and c['by'] == t), sum(1 for c in cyc_stats(r, t, s) if c['start'] > 1 and c['arr'][str(1 - t)] and c['arr'][str(1 - t)]['wait'] >= 0 and not (c['arr'][str(t)] and c['arr'][str(t)]['wait'] >= 0) and c['by'] in (0, 1)))),
        ('cycles this side hit first (per game)', lambda r, t, s: sum(1 for c in cyc_stats(r, t, s) if c['first_hit'] == t)),
        ('  ... and lost to the other side (per game)', lambda r, t, s: sum(1 for c in cyc_stats(r, t, s) if c['first_hit'] == t and c['by'] == 1 - t)),
        ('  share lost of those hit first (taken)', lambda r, t, s: share(sum(1 for c in cyc_stats(r, t, s) if c['first_hit'] == t and c['by'] == 1 - t), sum(1 for c in cyc_stats(r, t, s) if c['first_hit'] == t and c['by'] in (0, 1)))),
        ('  hitters (distinct bodies) on cycles hit first and won', lambda r, t, s: mean([c['hitters'][str(t)] for c in cyc_stats(r, t, s) if c['first_hit'] == t and c['by'] == t])),
        ('  hitters on cycles hit first and lost', lambda r, t, s: mean([c['hitters'][str(t)] for c in cyc_stats(r, t, s) if c['first_hit'] == t and c['by'] == 1 - t])),
        ('  deaths near the group on cycles hit first and lost (per cycle)', lambda r, t, s: mean([c['deaths'][str(t)] for c in cyc_stats(r, t, s) if c['first_hit'] == t and c['by'] == 1 - t])),
        ('deaths within 5 of contested groups per game', lambda r, t, s: sum(c['deaths'][str(t)] for c in cyc_stats(r, t, s))),
        ('gems captured on contested big groups per game', lambda r, t, s: sum(c.get('cap', {}).get(str(t), 0) for c in cyc_stats(r, t, s))),
    ])
    # reaction when the other side is there
    print('\n## Q1b reaction when the other side holds / is at a contested big group (first 12 rounds after both are there)')
    for n, sg in S.items():
        beh = Counter()
        nb = []
        nen = []
        back = 0
        hp = []
        won = Counter()
        for row, t in sg.pairs:
            for c in row['cycles']:
                if c['mono'] or not contested(c):
                    continue
                rc = c['react'][str(t)]
                if not rc:
                    continue
                beh[rc['beh']] += 1
                nb.append(rc['n'])
                nen.append(rc['n_en'])
                hp.append(rc['hp'])
                back += rc['back']
                won[(rc['beh'], c['by'] == t)] += 1
        tot = sum(beh.values())
        if not tot:
            continue
        print(f"{n}: contacts {tot} ({tot / max(1, len(sg)):.2f}/game): " + ', '.join(f'{k} {v / tot:.0%}' for k, v in beh.most_common()) +
              f"; our bodies {mean(nb):.2f} vs theirs {mean(nen):.2f}; hp {mean(hp):.2f}; came back after leaving {back} ({back / max(1, beh['left']):.0%} of left)")
        print('   capture share by reaction: ' + ', '.join(f"{b}: {won[(b, True)]}/{won[(b, True)] + won[(b, False)]}" for b in beh))

    # ---------------- Q2 territory
    table('Q2 territory: captures and presence by band (own / mid / their half)', S, [
        ('captures per game', lambda r, t, s: sum(s['caps'].values())),
        ('share of captures on own half', lambda r, t, s: share(s['caps']['own'], sum(s['caps'].values()))),
        ('share of captures in the middle band', lambda r, t, s: share(s['caps']['mid'], sum(s['caps'].values()))),
        ('share of captures on the enemy half', lambda r, t, s: share(s['caps']['their'], sum(s['caps'].values()))),
        ('gems captured on the enemy half per game', lambda r, t, s: s['cap_gems']['their']),
        ('gems captured in the middle per game', lambda r, t, s: s['cap_gems']['mid']),
        ('gems captured on own half per game', lambda r, t, s: s['cap_gems']['own']),
        ('body-round share on own half', lambda r, t, s: share(s['use_band'].get('own', 0), sum(s['use_band'].values()))),
        ('body-round share in the middle', lambda r, t, s: share(s['use_band'].get('mid', 0), sum(s['use_band'].values()))),
        ('body-round share on the enemy half', lambda r, t, s: share(s['use_band'].get('their', 0), sum(s['use_band'].values()))),
        ('raids (>=5 rounds on the enemy half) per game', lambda r, t, s: s['raids']),
        ('  first raid round', lambda r, t, s: s['raid_first_r']),
        ('  raids with >=2 bodies (share)', lambda r, t, s: share(s['raid_multi'], s['raids'])),
        ('  deaths per raid', lambda r, t, s: share(s['raid_deaths'], s['raids'])),
        ('  kills per raid', lambda r, t, s: share(s['raid_kills'], s['raids'])),
        ('  gems captured per raid', lambda r, t, s: share(s['raid_caps'], s['raids'])),
        ('  raid length (rounds)', lambda r, t, s: share(s['raid_rounds'], s['raids'])),
        ('camp hits on the enemy half per game', lambda r, t, s: s['their_half_hits']),
        ('DENIED: enemy captures on OUR half per game', lambda r, t, s: side_of(r, 1 - t)['caps']['their']),
        ('DENIED: enemy gems captured on OUR half per game', lambda r, t, s: side_of(r, 1 - t)['cap_gems']['their']),
        ('DENIED: enemy camp hits on OUR half per game', lambda r, t, s: side_of(r, 1 - t)['their_half_hits']),
        ('contested-reward cycles (both on the tiles while the reward was up) per game', lambda r, t, s: sum(1 for c in r['cycles'] if c['contested_reward'])),
        ('  of which the enemy stepped on OUR-half rewards', lambda r, t, s: sum(1 for c in r['cycles'] if c['contested_reward'] and c['band'][str(t)] == 'own')),
        ('  of which we stepped on THEIR-half rewards', lambda r, t, s: sum(1 for c in r['cycles'] if c['contested_reward'] and c['band'][str(t)] == 'their')),
    ])
    # ---------------- Q3 gold
    table('Q3 gold groups vs gem groups', S, [
        ('opening (r<=300) gems captured', lambda r, t, s: s['open_gems']),
        ('opening gold captured', lambda r, t, s: s['open_gold']),
        ('opening gold share of value (gold x 0.5 gem-equiv)', lambda r, t, s: share(0.5 * s['open_gold'], s['open_gems'] + 0.5 * s['open_gold'])),
        ('opening captures', lambda r, t, s: s['open_caps']),
        ('opening captures of gold-only groups', lambda r, t, s: s['open_gold_only_caps']),
        ('opening share of camp hits on gold camps', lambda r, t, s: share(s['open_gold_hits'], s['open_hits'])),
        ('opening camp hits', lambda r, t, s: s['open_hits']),
        ('whole game: gold captured', lambda r, t, s: s['cap_gold']),
        ('whole game: gems captured', lambda r, t, s: s['cap_gems_all']),
        ('whole game: gold-only group captures', lambda r, t, s: s['gold_only_caps']),
        ('shop visits per game', lambda r, t, s: s['shops']),
        ('camp hits per game', lambda r, t, s: s['camp_hits']),
    ])
    # ---------------- Q4 wards
    table('Q4 wards and vision', S, [
        ('wards placed per game', lambda r, t, s: s['wards']),
        ('  by r300', lambda r, t, s: s['wards_by300']),
        ('  by r600', lambda r, t, s: s['wards_by600']),
        ('  first ward round', lambda r, t, s: s['ward_first_r']),
        ('  bodies that ever ward (of champs)', lambda r, t, s: s['ward_bodies']),
        ('  share on a bush tile', lambda r, t, s: share(s['wards_bush'], s['wards'])),
        ('  share within 6 of a big group (>=30 gems)', lambda r, t, s: share(s['wards_near_big'], s['wards'])),
        ('  share within 3 of any camp', lambda r, t, s: share(s['wards_near_camp'], s['wards'])),
        ('  share within 4 of an altar', lambda r, t, s: share(s['wards_near_altar'], s['wards'])),
        ('  share within 8 steps of own spawn', lambda r, t, s: share(s['wards_near_spawn'], s['wards'])),
        ('  share on own half', lambda r, t, s: share(s['wards_band'].get('own', 0), s['wards'])),
        ('  share in the middle band', lambda r, t, s: share(s['wards_band'].get('mid', 0), s['wards'])),
        ('  share on the enemy half', lambda r, t, s: share(s['wards_band'].get('their', 0), s['wards'])),
        ('  re-wards (placements after a body\'s first) per game', lambda r, t, s: s['rewards']),
        ('live wards at r300 (engine table)', lambda r, t, s: s['live_wards300']),
        ('live wards at r600', lambda r, t, s: s['live_wards600']),
        ('map share seen by wards at r300 (passable tiles within 6 of a live ward)', lambda r, t, s: s['cov300']),
        ('map share seen by wards at r600', lambda r, t, s: s['cov600']),
    ])
    # ward placement timing distribution
    print('\n## Q4b ward placement rounds (share of wards in r<100 / 100-300 / 300-600 / >600) and bush share when a bush map (bush_frac>=0.03)')
    for n, sg in S.items():
        rs = Counter()
        tot = 0
        bushy = []
        for row, t in sg.pairs:
            for w in row['wards']:
                if w['t'] != t:
                    continue
                tot += 1
                rs['<100' if w['r'] < 100 else '100-300' if w['r'] < 300 else '300-600' if w['r'] < 600 else '>600'] += 1
            if row['mapcls']['bush_frac'] >= 0.03:
                sd = side_of(row, t)
                if sd['wards']:
                    bushy.append(sd['wards_bush'] / sd['wards'])
        if tot:
            print(f"{n}: {tot} wards: " + ', '.join(f'{k} {v / tot:.0%}' for k, v in rs.items()) + f'; bush share on bushy maps {fmt(mean(bushy))} (n={len(bushy)})')

    # ---------------- Q5 map classes
    print('\n## Q5 map classes: our win rate (ME, all v84-v88 games) and the top-30 numbers on the same classes')
    classes = {'lone monolith': lambda m: m['lone_mono'] > 0, 'any monolith group': lambda m: m['mono_groups'] > 0,
               'islands (unreachable groups)': lambda m: m['islands'] > 0, 'single altar': lambda m: m['altars'] == 1,
               'no altar': lambda m: m['altars'] == 0, '2+ altars': lambda m: m['altars'] >= 2, 'all maps': lambda m: True}
    for cn, cf in classes.items():
        me = [(r, t) for r, t in S['ME'].pairs if cf(r['mapcls'])]
        me88 = [(r, t) for r, t in S['ME88'].pairs if cf(r['mapcls'])]
        top = [(r, t) for r, t in S['TOP'].pairs if cf(r['mapcls'])]
        wr = mean([side_of(r, t)['win'] for r, t in me])
        wr88 = mean([side_of(r, t)['win'] for r, t in me88])
        maps = sorted({r['map'] for r, t in me})
        print(f"{cn}: ME n={len(me)} win {fmt(wr)}; ME88 n={len(me88)} win {fmt(wr88)}; TOP sides n={len(top)}; maps: {', '.join(maps)[:200]}")
    print('\nper-map win rate (ME, n>=3), worst first, with class flags')
    bym = defaultdict(list)
    for r, t in S['ME'].pairs:
        bym[r['map']].append((r, t))
    rows = []
    for m, prs in bym.items():
        if len(prs) >= 3:
            mc = prs[0][0]['mapcls']
            rows.append((mean([side_of(r, t)['win'] for r, t in prs]), len(prs), m, mc))
    for wr, n, m, mc in sorted(rows)[:25]:
        print(f"  {m:24s} win {wr:.2f} n={n}  lone_mono={mc['lone_mono']} mono={mc['mono_groups']} islands={mc['islands']} altars={mc['altars']} big={mc['big_groups']} mid_big={mc['mid_big']} champs={mc['champs']}")
    mono_sets = {n: SideGames(n, [(r, t) for r, t in sg.pairs if r['mapcls']['mono_groups'] > 0]) for n, sg in S.items()}
    table('Q5b monolith maps only', mono_sets, [
        ('win', lambda r, t, s: s['win']),
        ('monolith kills per game', lambda r, t, s: len(s['mono_kills'])),
        ('  first kill round', lambda r, t, s: min((k['r'] for k in s['mono_kills']), default=None)),
        ('  bodies within 5 at the kill', lambda r, t, s: mean([k['bodies'] for k in s['mono_kills']])),
        ('enemy monolith kills per game', lambda r, t, s: len(side_of(r, 1 - t)['mono_kills'])),
        ('deaths per game', lambda r, t, s: s['deaths']),
        ('banked', lambda r, t, s: s['bank']),
        ('captures on the enemy half', lambda r, t, s: s['caps']['their']),
        ('wards per game', lambda r, t, s: s['wards']),
    ])
    lone_sets = {n: SideGames(n, [(r, t) for r, t in sg.pairs if r['mapcls']['lone_mono'] > 0]) for n, sg in S.items()}
    table('Q5c lone-monolith maps only', lone_sets, [
        ('win', lambda r, t, s: s['win']),
        ('monolith kills per game', lambda r, t, s: len(s['mono_kills'])),
        ('  first kill round', lambda r, t, s: min((k['r'] for k in s['mono_kills']), default=None)),
        ('  bodies within 5 at the kill', lambda r, t, s: mean([k['bodies'] for k in s['mono_kills']])),
        ('deaths per game', lambda r, t, s: s['deaths']),
        ('banked', lambda r, t, s: s['bank']),
        ('final round', lambda r, t, s: r['final']),
    ])
    isl_sets = {n: SideGames(n, [(r, t) for r, t in sg.pairs if r['mapcls']['islands'] > 0]) for n, sg in S.items()}
    table('Q5d island maps only', isl_sets, [
        ('win', lambda r, t, s: s['win']),
        ('captures on islands (band ?) per game', lambda r, t, s: s['caps']['?']),
        ('gems from islands per game', lambda r, t, s: s['cap_gems']['?']),
        ('deaths per game', lambda r, t, s: s['deaths']),
        ('banked', lambda r, t, s: s['bank']),
    ])
    one_sets = {n: SideGames(n, [(r, t) for r, t in sg.pairs if r['mapcls']['altars'] == 1]) for n, sg in S.items()}
    table('Q5e single-altar maps only', one_sets, [
        ('win', lambda r, t, s: s['win']),
        ('deaths per game', lambda r, t, s: s['deaths']),
        ('banked', lambda r, t, s: s['bank']),
        ('captures per game', lambda r, t, s: sum(s['caps'].values())),
        ('share of captures in the middle', lambda r, t, s: share(s['caps']['mid'], sum(s['caps'].values()))),
        ('held recalls per game', lambda r, t, s: s['recalls']),
    ])
    # ---------------- Q6 recalls
    def recs(r, t):
        return [x for x in r['recalls'] if x['t'] == t and x['d_spawn'] is not None and x['d_spawn'] >= 3]
    table('Q6 held recalls (channel survived the next round; started >= 3 steps from spawn)', S, [
        ('held recalls per game', lambda r, t, s: len(recs(r, t))),
        ('  completed (on spawn within 7 rounds) share', lambda r, t, s: share(sum(1 for x in recs(r, t) if x['done'] is not None), len(recs(r, t)))),
        ('  interrupted by a hit (share)', lambda r, t, s: share(sum(1 for x in recs(r, t) if x['hit']), len(recs(r, t)))),
        ('  cancelled without a hit (share)', lambda r, t, s: share(sum(1 for x in recs(r, t) if x['done'] is None and not x['hit']), len(recs(r, t)))),
        ('  mean steps from spawn at the recall', lambda r, t, s: mean([x['d_spawn'] for x in recs(r, t)])),
        ('  share started on own half', lambda r, t, s: share(sum(1 for x in recs(r, t) if x['band'] == 'own'), len(recs(r, t)))),
        ('  share started in the middle', lambda r, t, s: share(sum(1 for x in recs(r, t) if x['band'] == 'mid'), len(recs(r, t)))),
        ('  share started on the enemy half', lambda r, t, s: share(sum(1 for x in recs(r, t) if x['band'] == 'their'), len(recs(r, t)))),
        ('  why: heal (hp<50%) share', lambda r, t, s: share(sum(1 for x in recs(r, t) if x['why'] == 'heal'), len(recs(r, t)))),
        ('  why: bank (bag>=20) share', lambda r, t, s: share(sum(1 for x in recs(r, t) if x['why'] == 'bank'), len(recs(r, t)))),
        ('  why: shop (gold>=90) share', lambda r, t, s: share(sum(1 for x in recs(r, t) if x['why'] == 'shop'), len(recs(r, t)))),
        ('  why: reposition (none of those) share', lambda r, t, s: share(sum(1 for x in recs(r, t) if x['why'] == 'reposition'), len(recs(r, t)))),
        ('  capture-recalls (a reward landed within 6 rounds) share', lambda r, t, s: share(sum(1 for x in recs(r, t) if x['cap_recall']), len(recs(r, t)))),
        ('  mean hp at the recall', lambda r, t, s: mean([x['hp'] for x in recs(r, t)])),
        ('  mean bag at the recall', lambda r, t, s: mean([x['bag'] for x in recs(r, t)])),
        ('  mean gold at the recall', lambda r, t, s: mean([x['gold'] for x in recs(r, t)])),
        ('bait recalls (started and cancelled next turn) per game', lambda r, t, s: s['fake_recalls']),
        ('deaths per game', lambda r, t, s: s['deaths']),
        ('banked', lambda r, t, s: s['bank']),
        ('win', lambda r, t, s: s['win']),
        ('final round', lambda r, t, s: r['final']),
    ])


if __name__ == '__main__':
    main()
