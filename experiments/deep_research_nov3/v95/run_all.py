#!/usr/bin/env python3
"""Run the top30_nov3 stream extractors (fights/extract2.process, execution/metrics.run, confusion/flips.run,
economy/econ.work) on v95's decoded games in experiments/deep_research_nov3/v95/{dec,mj}.
Per game output: out/g/<mid>.json = {'info':..., 'fights': {...}, 'met': {...}, 'fl': {...}, 'econ': [...]}.
Usage: nice -n 19 python3 -I run_all.py [--loop]   (resumable; --loop keeps going until the decoder logs DECDONE)"""
import json, os, sys, time, traceback
ROOT = '/home/claude/cambridge_battlecode'
V95 = f'{ROOT}/experiments/deep_research_nov3/v95'
T30 = f'{ROOT}/experiments/top30_nov3'
sys.path.insert(0, f'{T30}/execution')
sys.path.insert(0, f'{T30}/fights')
sys.path.insert(0, f'{T30}/confusion')
sys.path.insert(0, f'{T30}/economy')
import h30  # noqa: E402
import metrics  # noqa: E402
import flips  # noqa: E402
import extract2  # noqa: E402
import econ  # noqa: E402

ME = h30.ME
OUT = f'{V95}/out/g'
os.makedirs(OUT, exist_ok=True)
LAD = {t['teamId']: t for t in json.load(open(f'{T30}/ladder.json'))['teams']}


def era(t):
    if '2026-11-03T12:45:05' <= t < '2026-11-03T12:50:44' or t >= '2026-11-03T12:52:30':
        return 'v95'
    if '2026-11-03T12:50:44' <= t < '2026-11-03T12:52:30':
        return 'amb'
    return 'pre'


def games():
    out = []
    for l in open(f'{V95}/all_recent.jsonl'):
        m = json.loads(l)
        mid = m['matchId']
        e = era(m['createdAt'])
        if e == 'pre' or m['status'] != 'finished':
            continue
        dec, mj = f'{V95}/dec/{mid}.json', f'{V95}/mj/{mid}.json'
        if not (os.path.exists(dec) and os.path.getsize(dec) > 0 and os.path.exists(mj)):
            continue
        us = [t for t in m['teams'] if t['teamId'] == ME][0]
        th = [t for t in m['teams'] if t['teamId'] != ME][0]
        we = 0 if us['side'] == 'a' else 1
        teams = [None, None]
        for t in m['teams']:
            r = LAD.get(t['teamId'], {})
            teams[0 if t['side'] == 'a' else 1] = {'id': t['teamId'], 'name': t['name'], 'rank': r.get('rank'), 'rating': r.get('rating'),
                                                   'result': 'W' if t['result'] == 'win' else 'L'}
        g = {'key': mid, 'mid': mid, 'map': m['map'], 'dec': dec, 'mj': mj, 'replay': f'{V95}/replays/{mid}.repl26a', 'we': we,
             'res': 'W' if us['result'] == 'win' else 'L', 'ver': e, 'kind': m['kind'], 'tag': e, 'created': m['createdAt'],
             'teams': teams, 'names': [teams[0]['name'], teams[1]['name']], 'ratings': [teams[0]['rating'], teams[1]['rating']],
             'winner': we if us['result'] == 'win' else 1 - we, 'opp': th['name'], 'opp_id': th['teamId'], 'end': m.get('endReason'),
             'group': m['groupId']}
        out.append(g)
    return out


def one(g):
    res = {'info': {k: g[k] for k in ('mid', 'map', 'we', 'res', 'ver', 'kind', 'created', 'opp', 'opp_id', 'ratings', 'end', 'group')}}
    try:
        f = extract2.process(g)
        res['fights'] = f
    except Exception as ex:  # noqa: BLE001
        res['fights_err'] = repr(ex)[:300] + traceback.format_exc()[-600:]
    try:
        res['met'] = metrics.run(g)
    except Exception as ex:  # noqa: BLE001
        res['met_err'] = repr(ex)[:300] + traceback.format_exc()[-600:]
    try:
        res['fl'] = flips.run(g)
    except Exception as ex:  # noqa: BLE001
        res['fl_err'] = repr(ex)[:300] + traceback.format_exc()[-600:]
    try:
        ti = {}
        for t in (0, 1):
            tm = g['teams'][t]
            ti[t] = {'name': tm['name'], 'teamId': tm['id'], 'rating': tm['rating'], 'res': tm['result'], 'ver': g['ver'],
                     'kind': g['kind'], 'me': tm['id'] == ME}
        res['econ'] = econ.work((g['dec'], g['mj'], g['map'], ti))
    except Exception as ex:  # noqa: BLE001
        res['econ_err'] = repr(ex)[:300]
    return res


def main():
    loop = '--loop' in sys.argv
    while True:
        gs = games()
        need = {}
        for g in gs:
            if g['map'] not in h30.mapgroups.HALF and g['map'] not in need:
                need[g['map']] = g['replay']
        if need:
            print('maps missing half-group tables:', sorted(need), flush=True)
        todo = [g for g in gs if not os.path.exists(f"{OUT}/{g['mid']}.json") and g['map'] not in need]
        for g in todo:
            t0 = time.time()
            r = one(g)
            json.dump(r, open(f"{OUT}/{g['mid']}.json", 'w'))
            errs = [k for k in r if k.endswith('_err')]
            print(g['mid'][:8], g['map'], round(time.time() - t0, 1), 's', 'ERR ' + ','.join(errs) if errs else '', flush=True)
        if not loop:
            break
        done = os.path.exists(f'{V95}/dl_progress.log') and 'DECDONE' in open(f'{V95}/dl_progress.log').read()
        if done and not todo:
            break
        time.sleep(20)


if __name__ == '__main__':
    main()
