#!/usr/bin/env python3
"""Ranked-safe paired testing (the user's rule, Nov 3): ranked matches are created every 10 minutes (UTC minute % 10 == 0, at
about :00:05). The BEST version must be live then, so our rating only ever sees it. Between two ranked slots the TEST version is made
live just long enough to queue its paired groups (a match is bound to the submission that is live when it is created), then BEST is
made live again before the next slot.

    python3 experiments/ladder_nov2/ladder_cycle.py --test 91 --best 88 --plan experiments/ladder_nov2/paired_c6.json --max 50 [--execute]

One cycle: wait until 30 s after a ranked slot -> activate TEST -> wait until it is live (an activation recompiles: ~2 min) ->
paired-run --max N (only while TEST is live) -> activate BEST -> wait until it is live -> verify it is live >= 60 s before the next
slot (else it says so). Without --execute it only prints the schedule. Writes a CYCLE line to loop_log.md.
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LOG = os.path.join(HERE, 'loop_log.md')


def now():
    return dt.datetime.now(dt.timezone.utc)


def live_selected():
    out = subprocess.run(['cambc', 'submissions', 'list', '--json'], capture_output=True, text=True, cwd=ROOT).stdout
    d = json.loads(out)
    a = (d.get('active') or {}).get('version')
    s = (d.get('selected') or {}).get('version')
    return a, s


def submissions():
    out = subprocess.run(['cambc', 'submissions', 'list', '--json'], capture_output=True, text=True, cwd=ROOT).stdout
    d = json.loads(out)
    return d.get('submissions') or d.get('items') or []


def activate(v, tries=6, until=None):
    """Retry until it succeeds: `tries` attempts, or (with `until`, a UTC datetime) until that time. The platform answers 503 at
    times (12:50Z Nov 3: six 503s in a row left a test version live over a ranked slot)."""
    i = 0
    while True:
        r = subprocess.run(['cambc', 'submissions', 'activate', str(v), '--json'], capture_output=True, text=True, cwd=ROOT)
        if r.returncode == 0:
            return True
        i += 1
        print(f'  activate {v} failed (try {i}): {(r.stdout + r.stderr).strip()[:160]}', flush=True)
        if (until is None and i >= tries) or (until is not None and now() > until):
            return False
        time.sleep(5)


def wait_live(v, timeout=300):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            a, s = live_selected()
        except Exception as e:  # noqa: BLE001
            print('  list failed:', e, flush=True)
            a = None
        if a == v:
            return time.time() - t0
        time.sleep(5)
    return None


def next_slot(t):
    m = (t.minute // 10 + 1) * 10
    base = t.replace(minute=0, second=0, microsecond=0)
    return base + dt.timedelta(minutes=m)


def log(line):
    with open(LOG, 'a') as f:
        f.write(line + '\n')
    print(line, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--test', type=int, default=0)
    ap.add_argument('--submit', default='', help='bot dir under bots/ to upload at the window start (becomes the test version)')
    ap.add_argument('--note', default='')
    ap.add_argument('--min-free', type=int, default=20, help='wait until this many groups of quota are free (or the time runs out)')
    ap.add_argument('--best', type=int, required=True)
    ap.add_argument('--plan', required=True)
    ap.add_argument('--max', type=int, default=50)
    ap.add_argument('--execute', action='store_true')
    a = ap.parse_args()
    t = now()
    last_slot = t.replace(second=0, microsecond=0, minute=(t.minute // 10) * 10)
    start = last_slot + dt.timedelta(seconds=30)
    if t > last_slot + dt.timedelta(minutes=1 if a.submit else 3):
        # too late in this window for activate + queue + switch back with margin: use the next window
        start = next_slot(t) + dt.timedelta(seconds=30)
    print(f'now {t:%H:%M:%S}; cycle starts {start:%H:%M:%S}; ranked slot after it {next_slot(start):%H:%M:%S}', flush=True)
    if not a.execute:
        return
    while now() < start:
        time.sleep(2)
    if a.submit:
        before = {x.get('version') for x in submissions()}
        r = subprocess.run(['cambc', 'submit', a.submit, '-n', a.note[:80]], capture_output=True, text=True, cwd=ROOT)
        print('  submit:', (r.stdout + r.stderr).strip()[-200:], flush=True)
        t0 = time.time()
        while time.time() - t0 < 300:
            new = [x for x in submissions() if x.get('version') not in before]
            if new and new[0].get('status') in ('active', 'inactive'):
                a.test = new[0]['version']
                break
            if new and any(k in str(new[0].get('status')) for k in ('fail', 'error', 'reject')):
                log(f'{now():%Y-%m-%dT%H:%MZ} CYCLE submit of {a.submit} failed to build: {new[0].get("status")}; v{a.best} stays')
                activate(a.best)
                wait_live(a.best)
                return
            time.sleep(10)
        if not a.test:
            log(f'{now():%Y-%m-%dT%H:%MZ} CYCLE submit of {a.submit}: not built after 5 min; re-pinning v{a.best}')
            activate(a.best)
            wait_live(a.best)
            return
        print(f'  built: v{a.test} at {now():%H:%M:%S}', flush=True)
        if (next_slot(start) - now()).total_seconds() < 420:
            # too late to make it live, queue and switch back with margin: the upload is live by itself (follow-newest): revert now
            log(f'{now():%Y-%m-%dT%H:%MZ} CYCLE v{a.test} built too late for this window ({(next_slot(start) - now()).total_seconds():.0f} s to the slot): '
                f'back to v{a.best}; run again with --test {a.test}')
            activate(a.best, until=next_slot(start) + dt.timedelta(minutes=3))
            wait_live(a.best)
            return
    if not activate(a.test):
        log(f'{now():%Y-%m-%dT%H:%MZ} CYCLE abort: could not activate v{a.test}')
        return
    w = wait_live(a.test)
    slot = next_slot(start)
    if w is None:
        log(f'{now():%Y-%m-%dT%H:%MZ} CYCLE v{a.test} not live after 5 min: back to v{a.best}')
        activate(a.best)
        wait_live(a.best)
        return
    print(f'  v{a.test} live after {w:.0f} s at {now():%H:%M:%S}', flush=True)
    # wait for free quota (rolling hour) while there is time to queue and still switch back with margin
    while (slot - now()).total_seconds() > 300:
        try:
            q = json.loads(subprocess.run(['cambc', 'match-groups', 'quota', '--json'], capture_output=True, text=True, cwd=ROOT).stdout)['quota']
            if q['limit'] - q['used'] >= min(a.min_free, a.max):
                break
        except Exception:  # noqa: BLE001
            pass
        time.sleep(10)
    left = (slot - now()).total_seconds()
    queued = 0
    if left > 240:
        r = subprocess.run([sys.executable, os.path.join(HERE, 'ladder_loop.py'), 'paired-run', '--plan', a.plan, '--max', str(a.max),
                            '--execute'], capture_output=True, text=True, cwd=ROOT)
        queued = sum(1 for l in r.stdout.splitlines() if l.strip().startswith('queued '))
        tail = [l for l in r.stdout.splitlines() if 'quota' in l.lower() or 'error' in l.lower()][-2:]
        print(f'  queued {queued} groups at {now():%H:%M:%S}', *tail, sep='\n  ', flush=True)
    else:
        print(f'  only {left:.0f} s to the slot: nothing queued', flush=True)
    activate(a.best, until=slot + dt.timedelta(minutes=3))
    w2 = wait_live(a.best)
    margin = (slot - now()).total_seconds()
    log(f'{now():%Y-%m-%dT%H:%MZ} CYCLE test v{a.test} (live {w:.0f} s after activation) queued {queued} groups of {os.path.basename(a.plan)}; '
        f'best v{a.best} live again {"after %.0f s" % w2 if w2 is not None else "NOT CONFIRMED"}, {margin:.0f} s before the {slot:%H:%M} ranked slot')


if __name__ == '__main__':
    main()
