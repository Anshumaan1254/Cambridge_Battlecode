"""Aggregate tools/top2/weak/wx3.mjs output (an_weak): camp deaths by camp type / activity / third party, Cassi & Issac killing blows,
   deaths per 100 alive body-rounds by max-health share, recalls started next to enemies and their outcome.
   python tools/top2/weak/wx3agg.py KEY..."""
import json, sys, collections
for key in sys.argv[1:]:
    G = [json.loads(l) for l in open(f'C:/battlecode/cache/an_weak/wx3_{key}.jsonl', encoding='utf-8') if l.strip()]
    print(f'### {key} ({len(G)} games, W {sum(g["win"] for g in G)})')
    for side in ['S', 'O']:
        for lab, GG in [('W', [g for g in G if g['win']]), ('L', [g for g in G if not g['win']])]:
            n = len(GG) or 1
            CD = [c for g in GG for c in g['T'][side]['campDeaths']]
            ct = collections.Counter(c['camp'] for c in CD)
            act = collections.Counter(c['hit10'] for c in CD)
            p3 = sum(1 for c in CD if c['en8'] > 0)
            hp = {k: [sum(g['T'][side]['hp'][k][0] for g in GG), sum(g['T'][side]['hp'][k][1] for g in GG)] for k in ['lo', 'ev', 'hi']}
            hps = ' '.join(f'{k} {100*v[1]/v[0]:.2f} (n {v[0]})' if v[0] else f'{k} -' for k, v in hp.items())
            print(f'  {side} {lab} n={len(GG)}: camp deaths {len(CD)/n:.2f}/game by {dict(ct.most_common(4))}; activity {dict(act.most_common(4))}; enemy within 8 {p3}/{len(CD)} | deaths per 100 alive body-rounds by max-hp share: {hps}')
        ci = collections.Counter()
        for g in G:
            for k, v in g['T'][side]['ciKills'].items(): ci[k] += v
        if sum(ci.values()): print(f'  {side} Cassi&Issac killing blows: {dict(ci)}')
        R = [r for g in G for r in g['T'][side]['recalls'] if not r['spam']]
        if R:
            res = collections.Counter(r['res'] for r in R)
            low = [r for r in R if r['hp'] < 0.4]
            print(f'  {side} recall starts with an enemy within 6 (non-spam): {len(R)} ({len(R)/len(G):.1f}/game) -> {dict(res)}; at hp<0.4: {len(low)} -> {dict(collections.Counter(r["res"] for r in low))}')
