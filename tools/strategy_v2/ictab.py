import csv, collections
IC = {5: "Stellar,Ren,CassiAndIssac,Ryth,Varg", 4: "Stellar,Ren,CassiAndIssac,Ryth", 3: "Stellar,Ren,CassiAndIssac"}
ICSP = {'stampede': "Stellar,Tavi,Prism,CassiAndIssac,Ren", 'contest': "Stellar,Tavi,Prism,CassiAndIssac,Ren",
        'rows': "Stellar,Prism,CassiAndIssac,Varg", 'expanse': "CassiAndIssac,Stellar,Varg"}
def prof(d):
    d = d.split(',')
    if d[0] == 'Ren': return 'R'
    if d[0].startswith('Varg') or (d[0] in ('Prism', 'Ryth') and 'Tavi' not in d[:2]): return 'M'
    if 'Tavi' in d[:3] or 'Willow' in d: return 'T'
    if d[0] == 'CassiAndIssac': return 'C'
    return 'X'
def games(team_csv):
    """IC = the side drafting the Stellar-first table of the Oct 18-19 ladder games (opponent profile R/T/C/M/X)."""
    by = collections.defaultdict(dict)
    for r in csv.DictReader(open(team_csv)): by[r['match']][int(r['team'])] = r
    out = []
    for m, t in sorted(by.items()):
        mp = m.split('_', 1)[1]; n = len(t[0]['draft'].split(','))
        ic = ICSP.get(mp, IC.get(n)); sides = [s for s in (0, 1) if t[s]['draft'] == ic]
        if len(sides) != 1: continue
        s = sides[0]
        out.append(dict(match=m, map=mp, ic=s, opp=prof(t[1 - s]['draft']), won=int(t[s]['won']), t=t))
    return out
if __name__ == '__main__':
    import sys
    labs = []
    for g in games(sys.argv[1]):
        l = ['', '']; l[g['ic']] = 'IC'; l[1 - g['ic']] = 'O' + g['opp']
        labs.append(f"{g['match'][:8]}:{l[0]}:{l[1]}")
    print(','.join(labs))
