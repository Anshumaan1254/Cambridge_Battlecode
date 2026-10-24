"""Aggregate tools/top2/weak/bagep.mjs output (an_weak): bag episodes per team (study team S vs its opponents O), by peak size.
   python tools/top2/weak/bagagg.py C:/battlecode/cache/an_weak/bagep.jsonl [MINPEAK=200]"""
import json, sys, collections
G = [json.loads(l) for l in open(sys.argv[1], encoding='utf-8') if l.strip()]
MINPEAK = int(sys.argv[2]) if len(sys.argv) > 2 else 200
def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float('nan')
for key in ['pbg', 'ifish', 'cm', 'pantheon', 'coo', 'nyx']:
    A = [g for g in G if g['key'] == key]
    if not A: continue
    print(f'### {key} ({len(A)} games; episodes with peak >= {MINPEAK})')
    for side, lab in [(0, 'S'), (1, 'O')]:
        E = [(g, e) for g in A for e in g['eps'] if (e['team'] == g['S']) == (side == 0) and e['peak'] >= MINPEAK]
        if not E: print(f'  {lab}: none'); continue
        end = collections.Counter(e['end'] for g, e in E)
        T = [t for g, e in E for t in e['tribs']]
        res = collections.Counter(t['res'] for t in T)
        selfc = [t for t in T if t['res'] in ('self', 'other')]
        print(f'  {lab}: {len(E)} episodes in {len(set(g["file"] for g, e in E))} games ({len(E)/len(A):.2f}/game); by type {dict(collections.Counter(e["ty"] for g, e in E).most_common(5))}')
        print(f'     peak mean {mean([e["peak"] for g, e in E]):.0f}, held mean {mean([e["held"] for g, e in E]):.0f} r (median {sorted(e["held"] for g, e in E)[len(E)//2]}), first tribute after {mean([e["firstTrib"] for g, e in E]):.0f} r (none in {sum(1 for g,e in E if e["firstTrib"] is None)})')
        print(f'     end: {dict(end)}; death -> killer team {dict(collections.Counter(("opp" if e.get("killerTeam") not in (None, "camp") else "camp") for g, e in E if e["end"] == "death"))}; bag lost on death {sum(e.get("deathBag", 0) for g, e in E if e["end"] == "death")}')
        print(f'     tribute starts {len(T)} ({len(T)/len(E):.1f}/episode): {dict(res)}; self/other-cancels with enemy within 6 {sum(1 for t in selfc if t.get("en6",0)>0)}/{len(selfc)}, within 8 {sum(1 for t in selfc if t.get("en8",0)>0)}, hit a champion within 3 r {sum(1 for t in selfc if t.get("hitAfter"))}')
        print(f'     enemy within 6 at the tribute start: {sum(1 for t in T if t["en6s"]>0)}/{len(T)}; first tribute -> end {mean([e["tribToEnd"] for g, e in E]):.0f} r')
        for w in [1, 0]:
            EE = [(g, e) for g, e in E if g['win'] == w]
            if EE: print(f'     in {"wins" if w else "losses"}: {len(EE)} eps, end {dict(collections.Counter(e["end"] for g, e in EE))}, peak {mean([e["peak"] for g, e in EE]):.0f}, held {mean([e["held"] for g, e in EE]):.0f}')
    # games where S had a big episode ending in death (bag stolen) -> outcome
    D = [(g, e) for g in A for e in g['eps'] if e['team'] == g['S'] and e['peak'] >= MINPEAK and e['end'] == 'death']
    print(f'  S big-bag deaths: {len(D)} in {len(set(g["file"] for g, e in D))} games, win {sum(g["win"] for g, e in D)}/{len(D)}')
    for g, e in D:
        print(f'     {g["file"]} {"W" if g["win"] else "L"} {g["sub"][0]}-{g["sub"][1]}: {e["ty"]} bag {e.get("deathBag")} (peak {e["peak"]}) died r{e["rEnd"]} to {e.get("killer")} after holding {e["held"]} r, {len(e["tribs"])} tribute starts')
