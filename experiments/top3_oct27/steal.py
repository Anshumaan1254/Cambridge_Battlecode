"""Who hit the camps of each captured group: for every capture, hits on that group's camp tiles since the group's previous capture
by each team. Captures 'stolen' = captured by a team that landed under 30% of the hits.
    python3 -I steal.py INDEX set"""
import collections, os, sys
sys.path.insert(0, '/home/claude/cambridge_battlecode/experiments/ic_oct26_v18/analysis')
import icx
S = collections.Counter()
for g in icx.games(sys.argv[1], {sys.argv[2]}):
    if not g.D:
        continue
    tg = g.D['tile_group']; gems = {x['id']: x['gems'] for x in g.D['groups']}
    hits = collections.defaultdict(lambda: [0, 0])
    for e in g.ev:
        if e['k'] in ('Attack', 'Cast ability') and e.get('who') is not None and e.get('to'):
            gid = tg.get(tuple(e['to']))
            if gid is not None:
                hits[gid][0 if g.team[e['who']] == g.ours else 1] += 1
        elif e['k'] == 'CaptureGems':
            gid = tg.get(tuple(e['at']))
            if gid is None:
                # reward tile may be off the camp tiles: nearest group center
                gid = min(g.D['groups'], key=lambda x: icx.cheb(x['center'], e['at']))['id']
            t = 0 if g.team[e['who']] == g.ours else 1
            h = hits[gid]; tot = h[0] + h[1]
            who = 'us' if t == 0 else 'them'
            S[(who, 'caps')] += 1; S[(who, 'gems')] += e['gems']
            if tot and h[t] / tot < 0.3:
                S[(who, 'stolen')] += 1; S[(who, 'stolen_gems')] += e['gems']
            if tot and h[1 - t] > 0:
                S[(who, 'contested')] += 1
            hits[gid] = [0, 0]
for w in ('us', 'them'):
    print(w, {k[1]: v for k, v in S.items() if k[0] == w})
