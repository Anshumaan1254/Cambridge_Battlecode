"""vagg.py (verify_draft): load vroles.mjs output, dedup per team, helpers for the aggregations."""
import json, collections, math, sys

def load(path):
    G = [json.loads(l) for l in open(path, encoding='utf-8') if l.strip()]
    G = [g for g in G if 'err' not in g]
    return G

def dedup(G):
    out, seen, dups = [], set(), []
    for g in sorted(G, key=lambda g: (g['key'], g['createdAt'], g['file'])):
        sig = (g['key'], g['map'], g['opp'], g['side'], g['finalRound'], tuple(g['submitted']))
        if sig in seen:
            dups.append(g['key'] + '/' + g['file']); continue
        seen.add(sig); out.append(g)
    return out, dups

def study_bodies(g, typ=None):
    return [b for b in g['bodies'] if b['team'] == g['studyTeam'] and (typ is None or b['type'] == typ)]

def opp_bodies(g, typ=None):
    return [b for b in g['bodies'] if b['team'] != g['studyTeam'] and (typ is None or b['type'] == typ)]

def mean(x):
    x = list(x); return sum(x) / len(x) if x else float('nan')
