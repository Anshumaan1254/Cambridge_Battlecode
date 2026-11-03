#!/usr/bin/env python3
"""Extend the existing stream extractors (economy/econ.py, draft_bank/extract_all.py, objectives/extract_obj.py) to all decoded
top-30 games. Seeds each output with the stream's existing top-30 rows and only analyses games not yet done.
   nice -n 19 python3 -I run_extract.py econ_db   -> ext/econ_rows.jsonl, ext/db_{teams,tributes,locks,bodies}.jsonl
   nice -n 19 python3 -I run_extract.py obj       -> ext/obj_games.jsonl
"""
import sys, json, os
T = '/home/claude/cambridge_battlecode/experiments/top30_nov3'
OUT = '/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro/ext'
for p in ('economy', 'draft_bank', 'objectives'):
    sys.path.insert(0, f'{T}/{p}')


def seed(src, dst, keep=lambda o: True):
    done = set()
    with open(dst, 'w') as f:
        for l in open(src):
            o = json.loads(l)
            if 'error' in o or not keep(o):
                continue
            f.write(l if l.endswith('\n') else l + '\n')
            done.add(o['mid'])
    return done


mode = sys.argv[1]
if mode == 'econ_db':
    import econ
    done = seed(f'{T}/economy/rows_top30.jsonl', f'{OUT}/econ_rows.jsonl')
    jobs = [j for j in econ.jobs_top30() if os.path.basename(j[0])[:-5] not in done]
    print('econ todo', len(jobs), flush=True)
    with open(f'{OUT}/econ_rows.jsonl', 'a') as f:
        for i, j in enumerate(jobs):
            for r in econ.work(j):
                f.write(json.dumps(r) + '\n')
            if i % 50 == 0:
                print('econ', i, flush=True)
    import extract_all as DB
    names = ('teams', 'tributes', 'locks', 'bodies')
    done = set()
    for n in names:
        d = seed(f'{T}/draft_bank/out/{n}.jsonl', f'{OUT}/db_{n}.jsonl', keep=lambda o: o.get('set') == 'top30')
        if n == 'teams':
            done = d
    games = [g for g in DB.load_games('top30') if g['mid'] not in done]
    print('db todo', len(games), flush=True)
    fs = {n: open(f'{OUT}/db_{n}.jsonl', 'a') for n in names}
    for i, g in enumerate(games):
        try:
            res = DB.analyse(g)
        except Exception as ex:  # noqa
            print('db fail', g['mid'], repr(ex), flush=True)
            continue
        for n, rows in zip(names, res):
            for x in rows:
                fs[n].write(json.dumps(x) + '\n')
        if i % 50 == 0:
            print('db', i, flush=True)
    for f in fs.values():
        f.close()
    print('econ_db done', flush=True)
elif mode == 'obj':
    import extract_obj as OB, common as C
    done = seed(f'{T}/objectives/out/games_top.jsonl', f'{OUT}/obj_games.jsonl')
    todo = [g for g in C.top_games() if g['mid'] not in done]
    print('obj todo', len(todo), flush=True)
    with open(f'{OUT}/obj_games.jsonl', 'a') as f:
        for i, g in enumerate(todo):
            try:
                row = OB.analyse(g)
            except Exception as ex:  # noqa
                print('obj fail', g['mid'], repr(ex), flush=True)
                continue
            f.write(json.dumps(row) + '\n')
            if i % 50 == 0:
                print('obj', i, flush=True)
    print('obj done', flush=True)
