# verify_economy aggregation helpers over C:/battlecode/cache/vecon/games.jsonl
import json, statistics as stt
from collections import defaultdict

GAMES = 'C:/battlecode/cache/vecon/games.jsonl'
KEYS = ['pbg', 'ifish', 'pantheon', 'coo', 'cm', 'nyx']


def load():
    out = []
    for l in open(GAMES, encoding='utf-8'):
        j = json.loads(l)
        if 'err' in j or 'skip' in j:
            continue
        out.append(j)
    return out


def mean(x):
    x = [v for v in x if v is not None]
    return sum(x) / len(x) if x else float('nan')


def med(x):
    x = [v for v in x if v is not None]
    return stt.median(x) if x else float('nan')


def pct(x, p):
    x = sorted(v for v in x if v is not None)
    if not x:
        return float('nan')
    k = (len(x) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(x) - 1)
    return x[lo] + (x[hi] - x[lo]) * (k - lo)


def pwl(pairs):
    """pairs of (winner value, loser value) -> P(w > l) with ties as 0.5"""
    n = 0
    s = 0.0
    for w, l in pairs:
        if w is None or l is None:
            continue
        n += 1
        s += 1 if w > l else (0.5 if w == l else 0)
    return s / n if n else float('nan')


def wl_table(games, fn, label):
    """fn(game, team) -> value; prints winner / loser mean, median, P(w > l)"""
    pairs = []
    for g in games:
        w = g['win']
        if w is None:
            continue
        pairs.append((fn(g, w), fn(g, 1 - w)))
    W = [p[0] for p in pairs]
    L = [p[1] for p in pairs]
    print(f'{label:40s} W mean {mean(W):8.1f} L mean {mean(L):8.1f} | W med {med(W):8.1f} L med {med(L):8.1f} | P(w>l) {pwl(pairs):.2f}  n {len(pairs)}')
    return pairs


def so_games(games, key):
    """[(game, S team index)] for a study key"""
    return [(g, g['keys'][key]) for g in games if key in g['keys'] and g['keys'][key] is not None]


def fmt(x, d=1):
    return ('%.' + str(d) + 'f') % x if isinstance(x, (int, float)) else str(x)
