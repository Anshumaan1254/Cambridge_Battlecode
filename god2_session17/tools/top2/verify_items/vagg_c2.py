"""verify_items C2: tribute interruptions split into voluntary (own Cancel channel) and forced (stun / enemy lock / death),
and bag episodes (all 150+ attempts of one body in one life) with their fate.   python tools/top2/verify_items/vagg_c2.py"""
import collections, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from vlib import groups, vd, pct

G = groups(); D = vd()
ORDER = ['pbg', 'pbg14', 'nyx', 'ifish', 'pantheon', 'coo', 'cm']
print('=== 150+ tribute attempts: any interruption / forced (stun, lock, death) / voluntary cancel; near = enemy within 6 at the end of the start round')
for g in ORDER:
    for side in ('S', 'O'):
        c = collections.defaultdict(collections.Counter)
        ep = collections.Counter(); ep_first_far = collections.Counter(); ng = 0
        for x in G[g]:
            d = D.get(x['base'])
            if not d: continue
            ng += 1
            tm = {b[0]: b[1] for b in d['bodies']}
            t = x['S'] if side == 'S' else 1 - x['S']
            deaths = collections.defaultdict(list)
            for de in d['deaths']: deaths[de[1]].append(de[0])
            trs = sorted([tr for tr in d['tribs'] if tm[tr['who']] == t], key=lambda z: z['q0'])
            for tr in trs:
                if tr['bag'] < 150 or tr['out'] == 'end': continue
                nr = 'near' if tr['dmin'] <= 6 else 'far'
                o = tr['out'].split(':')[0]
                c[nr]['n'] += 1
                if o != 'done': c[nr]['int'] += 1
                if o in ('stun', 'lock', 'death'): c[nr]['forced'] += 1
                if o == 'cancel': c[nr]['cancel'] += 1
            # episodes: per body and life, the 150+ attempts; fate = banked (a done 150+ attempt), died (death before), held (game end)
            seen = set()
            for i, tr in enumerate(trs):
                if tr['bag'] < 150: continue
                life_end = min([r for r in deaths[tr['who']] if r >= tr['r0']], default=10 ** 9)
                key = (tr['who'], life_end)
                if key in seen: continue
                seen.add(key)
                att = [z for z in trs if z['who'] == tr['who'] and z['bag'] >= 150 and tr['r0'] <= z['r0'] < life_end]
                if any(z['out'] == 'done' for z in att): f = 'banked'
                elif life_end < 10 ** 9: f = 'died'
                else: f = 'held to end'
                ep[f] += 1; ep['n'] += 1; ep['attempts'] += len(att)
                if att[0]['dmin'] > 6: ep_first_far[f] += 1; ep_first_far['n'] += 1
        cells = ' | '.join(f"{nr}: n {c[nr]['n']} any {pct(c[nr]['int'], c[nr]['n'])} forced {pct(c[nr]['forced'], c[nr]['n'])} own-cancel {pct(c[nr]['cancel'], c[nr]['n'])}" for nr in ('near', 'far'))
        print(f"{g:9s} {side} {cells}")
        if ep['n']:
            print(f"          bag episodes (150+) {ep['n']} in {ng} games, attempts/episode {ep['attempts']/ep['n']:.1f}: banked {pct(ep['banked'], ep['n'])}, died with it {pct(ep['died'], ep['n'])}, held to end {pct(ep['held to end'], ep['n'])}"
                  f" | first attempt with nobody within 6: n {ep_first_far['n']} died {pct(ep_first_far['died'], ep_first_far['n'])}")
