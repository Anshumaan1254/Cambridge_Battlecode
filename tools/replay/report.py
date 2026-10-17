#!/usr/bin/env python3
"""Readable report from a decoded replay (tools/replay/decode.mjs output).

usage: report.py decoded.json [--us A|B] [--full]

Covers: result and gem timeline, per-champion activity (captures, banking, recalls, shopping, deaths,
kills, rounds dead / on spawn / idle, distance walked), every death with killer, place, bag and the
local headcount, captures, and how each side used set_priority.
"""
import argparse, collections, json

CH = ['Ryth', 'Vesper', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin']


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('--us', default='A')
    ap.add_argument('--full', action='store_true')
    a = ap.parse_args()
    d = json.load(open(a.file))
    m, rounds, events = d['meta'], d['rounds'], d['events']
    us = 0 if a.us == 'A' else 1
    them = 1 - us
    tag = {us: 'US', them: 'THEM'}
    names = {b['index']: f"{tag[b['team']]}:{b['type']}" for b in m['bodies']}
    team_of = {b['index']: b['team'] for b in m['bodies']}
    out = []
    w = out.append
    res = 'WIN' if m['outcome'] == us + 1 else 'LOSS' if m['outcome'] == them + 1 else f"outcome {m['outcome']}"
    w(f"# {a.file}\n{res} | round {m['finalRound']} | gems us {m['submitted'][us]} - them {m['submitted'][them]} | map {m['width']}x{m['height']} team size {m['champsPerTeam']}")
    w(f"draft us: {', '.join(m['drafts'][us])} | them: {', '.join(m['drafts'][them])}")
    camps = collections.Counter(c['type'] for c in m['camps'])
    w(f"camps on map: {dict(camps)}")
    tl = [f"r{r['r']}:{r['sub'][us]}-{r['sub'][them]}" for r in rounds if r['r'] % 50 == 0]
    w('gems (us-them): ' + ' '.join(tl))

    # Per-champion activity from round snapshots
    st = collections.defaultdict(lambda: collections.Counter())
    prev = {}
    spawn_tiles = {}
    for r in rounds:
        for c in r['ch']:
            idx, team, typ, x, y, hp, mx, alive, gems, gold, kills, items = c
            s = st[idx]
            if r['r'] <= 2 and alive:
                spawn_tiles.setdefault(team, set()).add((x, y))
            if not alive:
                s['dead_rounds'] += 1
            else:
                p = prev.get(idx)
                if p and p[7]:
                    dist = cheb((x, y), (p[3], p[4]))
                    s['walked'] += dist
                    if dist == 0:
                        s['still_rounds'] += 1
                s['bag_sum'] += gems
                s['alive_rounds'] += 1
            prev[idx] = c
    for idx, c in prev.items():
        st[idx]['final_gold_unspent'] = c[9]
        st[idx]['kills'] = c[10]
        st[idx]['max_hp'] = c[6]
        st[idx]['items'] = sum(q for _, q in c[11])
    kinds = ('Recall', 'Shop', 'Place ward', 'Submit gems', 'Cast ability', 'Attack', 'Move', 'Set priority', 'Movement blocked', 'Place altar lock', 'Teleport channel')
    for e in events:
        if 'who' in e and e['k'] in kinds:
            st[e['who']][e['k']] += 1
        if e['k'] == 'CaptureGems':
            st[e['who']]['captures'] += 1
            st[e['who']]['captured_gems'] += e['gems']
        if e['k'] == 'Banked':
            st[e['who']]['banked'] += e['gems']
            st[e['who']]['bank_trips'] += 1
        if e['k'] == 'Death':
            st[e['who']]['deaths'] += 1
    w('\nchampion activity (rounds counted from per-round snapshots):')
    w(f"{'champion':18s} {'capt':>4s} {'gems':>5s} {'bank':>5s} {'trips':>5s} {'rcl':>4s} {'shop':>4s} {'die':>3s} {'kill':>4s} {'dead':>4s} {'still':>5s} {'walk':>5s} {'avgbag':>6s} {'items':>5s} {'maxhp':>5s} {'prio':>4s} {'atk':>5s} {'cast':>4s}")
    for idx in sorted(st, key=lambda i: (team_of.get(i) != us, i)):
        s = st[idx]
        avgbag = s['bag_sum'] / max(1, s['alive_rounds'])
        w(f"{names.get(idx, idx):18s} {s['captures']:4d} {s['captured_gems']:5d} {s['banked']:5d} {s['bank_trips']:5d} {s['Recall']:4d} {s['Shop']:4d} {s['deaths']:3d} {s['kills']:4d} {s['dead_rounds']:4d} {s['still_rounds']:5d} {s['walked']:5d} {avgbag:6.1f} {s['items']:5d} {s['max_hp']:5d} {s['Set priority']:4d} {s['Attack']:5d} {s['Cast ability']:4d}")

    # Deaths with context
    by_round = {r['r']: r for r in rounds}
    w('\ndeaths:')
    for e in events:
        if e['k'] != 'Death':
            continue
        r = by_round.get(e['r']) or by_round.get(e['r'] - 1)
        at = tuple(e['at'])
        near_allies = near_enemies = 0
        if r:
            for c in r['ch']:
                if c[0] == e['who'] or not c[7]:
                    continue
                if cheb((c[3], c[4]), at) <= 5:
                    if c[1] == e['team']:
                        near_allies += 1
                    else:
                        near_enemies += 1
        killer = names.get(e['by'], e['by']) if isinstance(e['by'], int) else e['by']
        w(f"  r{e['r']:4d} {names.get(e['who'])} at {at} bag {e['bag']} killed by {killer} via {e.get('step')} | within 5: allies {near_allies} enemies {near_enemies}")

    w('\ncaptures:')
    caps = [e for e in events if e['k'] == 'CaptureGems']
    for e in caps if a.full else caps[:40]:
        w(f"  r{e['r']:4d} {names.get(e['who'])} +{e['gems']} gems +{e['gold']} gold at {tuple(e['at'])}")

    w('\nrecalls (round, champion, position):')
    rec = [e for e in events if e['k'] == 'Recall']
    def where(e):
        r = by_round.get(e['r'] - 1) or by_round.get(e['r'])
        for c in (r['ch'] if r else []):
            if c[0] == e['who']:
                return (c[3], c[4]), c[5], c[6], c[8]
        return ('?', '?'), 0, 0, 0
    parts = []
    for e in rec[:120]:
        p, hp, mx, bag = where(e)
        parts.append(f"r{e['r']} {names.get(e['who'])}@{p} hp{hp}/{mx} bag{bag}")
    w('  ' + '; '.join(parts))

    w('\nset_priority usage (first 40 per team):')
    for t in (us, them):
        pe = [e for e in events if e['k'] == 'Set priority' and e.get('team') == t]
        w(f"  {tag[t]}: " + ' '.join(f"r{e['r']}:{names.get(e['who'])}={e.get('priority')}" for e in pe[:40]))

    w('\naltar locks / teleports:')
    for e in events:
        if e['k'] in ('Place altar lock', 'Teleport channel', 'Teleport complete'):
            w(f"  r{e['r']} {names.get(e.get('who'))} {e['k']} to {e.get('to')}")
    print('\n'.join(out))


if __name__ == '__main__':
    main()
