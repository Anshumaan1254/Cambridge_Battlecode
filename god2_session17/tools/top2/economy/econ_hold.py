# an_economy: how teams hold respawning middle groups. For every middle-band group cycle (tools/top2/economy/econ_game.py cycles) whose
# capturer has a body within 4 at the respawn round, what those holder bodies did in the 20 rounds before the respawn (hit another camp,
# hit a champion, moved, stood still; standing on the group's own tiles), their distance to the group, and how fast the group was re-hit.
#   python tools/top2/economy/econ_hold.py KEY...   (reads C:/battlecode/cache/t2econ/games_<KEY>.jsonl and the dumps <KEY>/*.json.gz)
import gzip, json, sys, statistics
from collections import Counter, defaultdict

CACHE = 'C:/battlecode/cache'


def cheb(a, b, c, d):
    return max(abs(a - c), abs(b - d))


def main(keys):
    for key in keys:
        lab = Counter(); dist = []; rehit = []; ontile = 0; n = 0; nb = 0
        for l in open(f'{CACHE}/t2econ/games_{key}.jsonl', encoding='utf-8'):
            g = json.loads(l)
            S = g['S']
            cyc = [c for c in g['cycles'] if c['end'] == 'cap' and 0.4 <= c['f0'] <= 0.6 and c.get('tResp') and c['capT'] == S and c['hold'][S] > 0]
            if not cyc:
                continue
            d = json.load(gzip.open(f'{CACHE}/t2econ/{key}/' + g['file'].replace('.repl26a', '.json.gz')))
            team = {b['index']: b['team'] for b in d['meta']['bodies']}
            camps = {c['index']: c for c in d['meta']['camps']}
            # group tiles from the camps (rebuild as in econ_game: cardinal components)
            at = {(c['x'], c['y']): c['index'] for c in d['meta']['camps']}
            par = {i: i for i in camps}

            def find(a):
                while par[a] != a:
                    par[a] = par[par[a]]
                    a = par[a]
                return a
            for c in d['meta']['camps']:
                for dx, dy in ((1, 0), (0, 1)):
                    j = at.get((c['x'] + dx, c['y'] + dy))
                    if j is not None:
                        par[find(c['index'])] = find(j)
            comp = defaultdict(list)
            for c in d['meta']['camps']:
                comp[find(c['index'])].append((c['x'], c['y']))
            tiles = list(comp.values())  # same order as econ_game groups (dict insertion order of components)
            R = {rr[0]: {c[0]: (c[1], c[2]) if c[5] else None for c in rr[3]} for rr in d['R']}
            hitc = set((x[2], x[1]) for x in d['cd'])
            hitch = set((x[2], x[1]) for x in d['dm'] if x[2] >= 0 and team.get(x[2]) != team.get(x[3]))
            nxt = defaultdict(list)
            for c in g['cycles']:
                if c['end'] == 'cap':
                    nxt[c['g']].append(c)
            for c in cyc:
                T = tiles[c['g']]
                r = c['tResp']
                holders = [b for b, p in R.get(r, {}).items() if p and team[b] == S and min(cheb(p[0], p[1], x, y) for x, y in T) <= 4]
                n += 1
                for b in holders:
                    nb += 1
                    for rr in range(r - 20, r + 1):
                        p, pp = R.get(rr, {}).get(b), R.get(rr - 1, {}).get(b)
                        if not p:
                            lab['dead/away'] += 1
                            continue
                        dd = min(cheb(p[0], p[1], x, y) for x, y in T)
                        if dd > 6:
                            lab['away (> 6)'] += 1
                        elif (b, rr) in hitch:
                            lab['hit a champion'] += 1
                        elif (b, rr) in hitc:
                            lab['hit a camp'] += 1
                        elif pp and pp != p:
                            lab['moved'] += 1
                        else:
                            lab['still'] += 1
                        if p in T:
                            ontile += 1
                        dist.append(dd)
                later = [x for x in nxt[c['g']] if x['tFull'] == r]
                if later and later[0].get('tHit') is not None:
                    rehit.append(later[0]['tHit'] - r)
        tot = sum(lab.values())
        print(f'{key}: held mid cycles {n}, holder bodies {nb} ({nb / max(1, n):.2f} per cycle); holder rounds in the last 20 before respawn: ' +
              ', '.join(f'{k} {100 * v / tot:.0f}%' for k, v in lab.most_common()) +
              f'; distance to the group median {statistics.median(dist) if dist else "-"}; on a group tile {100 * ontile / max(1, len(dist)):.0f}%; '
              f're-hit after respawn median {statistics.median(rehit) if rehit else "-"} (n {len(rehit)}), within 2 rounds {100 * sum(1 for x in rehit if x <= 2) / max(1, len(rehit)):.0f}%')


if __name__ == '__main__':
    main(sys.argv[1:] or ['pbg', 'ifish', 'pantheon', 'coo', 'cm', 'nyx'])
