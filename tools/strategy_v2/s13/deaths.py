import sys, glob, os; sys.path.insert(0,'/home/user/Cambridge_Battlecode/tools'); import ledger
comp={os.path.basename(p)[:-7] for p in glob.glob('/home/user/Cambridge_Battlecode/maps/comp/*.map26a')}
for b in sys.argv[1:]:
    out=[]
    for o in ['_ch2','_mite','_ifish','_px9','_snk','_fA']:
        rs=[r for r in ledger.current_rows(b,o).values() if r['map'] in comp]
        if not rs: continue
        d0=sum(r['deaths'][0] for r in rs); d1=sum(r['deaths'][1] for r in rs); w=sum(r['win'] for r in rs)
        out.append(f"{o}:{w}/{len(rs)} d{d0}-{d1}")
    print(b.ljust(6),' '.join(out))
