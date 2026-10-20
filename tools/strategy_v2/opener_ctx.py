#!/usr/bin/env python3
"""What our body was doing when the enemy opened a fight on it, and how fast it died.

usage: python3 -I tools/strategy_v2/opener_ctx.py DMG_DIR INDEX_JSON [--side own|neutral|enemy|all] [--team us|them] [--list]
For every death of ours by a champion: the first enemy champion hit on that body in the 12 rounds before the death (the opener),
its kind (cast / attack) and distance, our activity in the 12 rounds before that opener (hits on camps, hits on champions, tiles
moved, captures), our health fraction when the opener landed, rounds from the opener to the death, whether we hit back or moved
away afterwards, allies and enemies within 6 at the opener.
"""
import collections
import glob
import json
import os
import statistics as st
import sys

a = sys.argv[1:]
dmg_dir, index = a[0], a[1]
side_f = a[a.index('--side') + 1] if '--side' in a else 'own'
team_f = a[a.index('--team') + 1] if '--team' in a else 'us'
listing = '--list' in a
idx = {r['group'] + '_' + r['nn']: r for r in json.load(open(index))}
rows = []
for f in sorted(glob.glob(os.path.join(dmg_dir, '*.json'))):
    name = os.path.basename(f)[:-5]
    g = idx.get(name[:11])
    if not g:
        continue
    us = 0 if g['side'] == 'A' else 1
    me = us if team_f == 'us' else 1 - us
    d = json.load(open(f))
    W, H = d['meta']['width'], d['meta']['height']
    bodies = {b['index']: b for b in d['meta']['bodies']}
    by_round = {r['r']: r for r in d['rounds']}
    # per round, per body: (x, y, hp, maxhp)
    def state(r, i):
        rr = by_round.get(r)
        if not rr or i >= len(rr['ch']):
            return None
        c = rr['ch'][i]
        return (c[3], c[4], c[5], c[6], c[7])
    dmg_by_r = collections.defaultdict(list)
    for row in d['dmg']:
        dmg_by_r[row[0]].append(row)
    moves = collections.defaultdict(list)  # (round, who) -> moves
    caps = collections.defaultdict(list)
    for e in d['events']:
        if e['k'] == 'Move':
            moves[(e['r'], e['who'])].append(e)
        elif e['k'] in ('Capture', 'CaptureGems'):
            caps[(e['r'], e.get('who'))].append(e)
    # which side of the map a tile is on, for team `me`: compare distance to the two spawns (spawnA = [x0,y0,x1,y1] rectangle)
    spawn = d['meta'].get('spawnA')
    for e in d['events']:
        if e['k'] != 'Death' or e['team'] != me or e['by'] == 'camp':
            continue
        who, rd = e['who'], e['r']
        # the opener: first champion hit on `who` in the 12 rounds before the death with no enemy champion hit in the 6 rounds before it
        hits = [(r, row) for r in range(max(0, rd - 40), rd + 1) for row in dmg_by_r.get(r, []) if row[2] == 'c' and row[5] == 'c' and row[6] == who and bodies[row[3]]['team'] != me]
        if not hits:
            continue
        # walk back from the death to the start of this fight: a gap of >= 6 rounds without a hit ends it
        start = len(hits) - 1
        while start > 0 and hits[start][0] - hits[start - 1][0] < 6:
            start -= 1
        r0, row0 = hits[start]
        if rd - r0 > 40:
            continue
        s0 = state(r0, who)
        if not s0:
            continue
        x, y, hp, mhp, alive = s0
        att = bodies[row0[3]]
        sa = state(r0, row0[3])
        dist = max(abs(sa[0] - x), abs(sa[1] - y)) if sa else -1
        # activity in the 12 rounds before the opener
        camp_hits = sum(1 for r in range(r0 - 12, r0) for row in dmg_by_r.get(r, []) if row[2] == 'c' and row[3] == who and row[5] == 'm')
        champ_hits = sum(1 for r in range(r0 - 12, r0) for row in dmg_by_r.get(r, []) if row[2] == 'c' and row[3] == who and row[5] == 'c')
        moved = sum(len(moves.get((r, who), [])) for r in range(r0 - 12, r0))
        captured = sum(len(caps.get((r, who), [])) for r in range(r0 - 12, r0 + 1))
        # after the opener: did we hit a champion back, move away from the attacker, before dying
        back = sum(1 for r in range(r0, rd + 1) for row in dmg_by_r.get(r, []) if row[2] == 'c' and row[3] == who and row[5] == 'c')
        away = 0
        for r in range(r0 + 1, min(rd, r0 + 4) + 1):
            s1 = state(r, who); sa1 = state(r, row0[3])
            if s1 and sa1 and sa and max(abs(sa1[0] - s1[0]), abs(sa1[1] - s1[1])) > dist:
                away += 1
        # bodies within 6 at the opener
        allies = enemies = 0
        for i, b in bodies.items():
            if i == who:
                continue
            s = state(r0, i)
            if not s or not s[4]:
                continue
            if max(abs(s[0] - x), abs(s[1] - y)) <= 6:
                if b['team'] == me:
                    allies += 1
                else:
                    enemies += 1
        # side: nearer to our spawn or theirs (spawn rectangles are mirrored: use the x/y mirror of spawnA)
        if spawn:
            sx, sy = (spawn[0] + spawn[2]) / 2, (spawn[1] + spawn[3]) / 2
            ex, ey = W - 1 - sx, H - 1 - sy
            da, de = abs(sx - x) + abs(sy - y), abs(ex - x) + abs(ey - y)
            if us != me:
                da, de = de, da
            side = 'own' if da < de - 4 else 'enemy' if de < da - 4 else 'neutral'
        else:
            side = '?'
        # damage in the fight to this body
        taken = sum(-row[7] for r in range(r0, rd + 1) for row in dmg_by_r.get(r, []) if row[5] == 'c' and row[6] == who and row[2] == 'c')
        enemy_dmg_r0 = sum(-row[7] for row in dmg_by_r.get(r0, []) if row[5] == 'c' and row[6] == who and row[2] == 'c')
        rows.append(dict(game=name[:11], r=r0, death=rd, who=bodies[who]['type'], att=att['type'], kind=row0[1], dist=dist, hpf=hp / max(1, mhp),
                         camp_hits=camp_hits, champ_hits=champ_hits, moved=moved, captured=captured, back=back, away=away, allies=allies, enemies=enemies,
                         side=side, rounds=rd - r0, taken=taken, first_r_dmg=enemy_dmg_r0, mhp=mhp))
sel = [r for r in rows if side_f == 'all' or r['side'] == side_f]
print(f"{team_f} deaths by champions with an opener found: {len(rows)}; on side '{side_f}': {len(sel)}")
if not sel:
    sys.exit()
def share(k, f):
    return sum(1 for r in sel if f(r)) / len(sel)
print(f"  opener kind: {collections.Counter(r['kind'] for r in sel).most_common()}")
print(f"  opener distance: {collections.Counter(r['dist'] for r in sel).most_common()}")
print(f"  opener champion: {collections.Counter(r['att'] for r in sel).most_common()}")
print(f"  victim: {collections.Counter(r['who'] for r in sel).most_common()}")
print(f"  our health at the opener: median {st.median(r['hpf'] for r in sel):.2f}; >= 0.8: {share('h', lambda r: r['hpf'] >= 0.8):.0%}; < 0.4: {share('h', lambda r: r['hpf'] < 0.4):.0%}")
print(f"  rounds from opener to death: median {st.median(r['rounds'] for r in sel)}, <= 2: {share('r', lambda r: r['rounds'] <= 2):.0%}, <= 5: {share('r', lambda r: r['rounds'] <= 5):.0%}")
print(f"  first-round damage / max health: median {st.median(r['first_r_dmg'] / r['mhp'] for r in sel):.2f}; >= 0.5: {share('f', lambda r: r['first_r_dmg'] >= 0.5 * r['mhp']):.0%}")
print(f"  activity in the 12 rounds before: farming (camp hits >= 3) {share('a', lambda r: r['camp_hits'] >= 3):.0%}, fighting champions {share('a', lambda r: r['champ_hits'] >= 2):.0%}, walking (moved >= 8, no hits) {share('a', lambda r: r['moved'] >= 8 and r['camp_hits'] + r['champ_hits'] == 0):.0%}, capturing {share('a', lambda r: r['captured'] > 0):.0%}")
print(f"  allies within 6 at the opener: {collections.Counter(r['allies'] for r in sel).most_common()}; enemies within 6: {collections.Counter(r['enemies'] for r in sel).most_common()}")
print(f"  after the opener: hit back {share('b', lambda r: r['back'] > 0):.0%}, moved away from the opener in the next 3 rounds {share('w', lambda r: r['away'] > 0):.0%}")
if listing:
    for r in sorted(sel, key=lambda r: (r['game'], r['r'])):
        print(f"   {r['game']} r{r['r']:4d}-{r['death']:4d} {r['who']:8s} by {r['att']:8s} {r['kind']:12s} d{r['dist']} hp{r['hpf']:.2f} camp{r['camp_hits']:2d} ch{r['champ_hits']:2d} mv{r['moved']:2d} cap{r['captured']} back{r['back']:2d} away{r['away']} al{r['allies']} en{r['enemies']} taken{r['taken']:5d}")
