#!/usr/bin/env python3
"""Ladder A/B loop for CAMBC (team HouseOfCoders): snapshot -> deploy -> paired replays -> verdict -> keep or roll back.

  python3 experiments/ladder_nov2/ladder_loop.py snapshot [--since ISO] [--no-log]
  python3 experiments/ladder_nov2/ladder_loop.py adopt [--since ISO] [--previous N]
  python3 experiments/ladder_nov2/ladder_loop.py deploy BOT --note "..." [--execute]      (or: deploy --resume [--execute])
  python3 experiments/ladder_nov2/ladder_loop.py paired-run --plan PLAN.json --max N [--execute]
  python3 experiments/ladder_nov2/ladder_loop.py paired-report --plan PLAN.json
  python3 experiments/ladder_nov2/ladder_loop.py verdict [--plan PLAN.json]
  python3 experiments/ladder_nov2/ladder_loop.py rollback [--to N] [--execute]

Safety: the only commands that change anything on the platform -- `cambc submit`, `cambc submissions activate` and
`cambc match-groups create` -- run only with --execute; without it they are printed as "[dry-run] <command>".
Every external command goes through run_cmd(), which logs it (exit code, duration) to stderr.
Standard library only. Usage notes and the statistics: LADDER_LOOP.md next to this file.
"""
import argparse
import datetime as dt
import json
import math
import os
import re
import shlex
import subprocess
import sys
import time

ME = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'  # HouseOfCoders
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))  # repo root (cambc.toml, bots/): every command runs here
MATCHES = os.path.join(HERE, 'matches_me.jsonl')
FETCH_ME = os.path.join(HERE, 'fetch_me.py')
CAMBC = os.environ.get('CAMBC', 'cambc')
SELF = 'python3 experiments/ladder_nov2/ladder_loop.py'
UTC = dt.timezone.utc


class LoopError(Exception):
    """An expected failure with a clear message: printed as 'error: ...' (exit code 2), no traceback."""


def log(msg):
    print(msg, file=sys.stderr, flush=True)


# ------------------------------------------------------------------------------------------------ time

_TS = re.compile(r'^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:[.,](\d+))?)?)?\s*(Z|[+-]\d{2}:?\d{2})?$', re.I)


def parse_ts(s):
    """ISO-8601 -> aware UTC datetime. '2026-11-02T21:15:46.933Z', '2026-11-02T21:15', '...+05:30'; no zone = UTC."""
    if isinstance(s, dt.datetime):
        return s if s.tzinfo else s.replace(tzinfo=UTC)
    m = _TS.match(str(s or '').strip())
    if not m:
        raise LoopError(f'cannot parse time {s!r}; use ISO such as 2026-11-02T21:15:46Z')
    y, mo, d, h, mi, se, frac, tz = m.groups()
    try:
        t = dt.datetime(int(y), int(mo), int(d), int(h or 0), int(mi or 0), int(se or 0),
                        int((frac or '0')[:6].ljust(6, '0')), tzinfo=UTC)
    except ValueError as e:
        raise LoopError(f'bad time {s!r}: {e}')
    if tz and tz.upper() != 'Z':
        off = dt.timedelta(hours=int(tz[1:3]), minutes=int(tz[-2:]))
        t = t - off if tz[0] == '+' else t + off
    return t


def iso(t):
    return t.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def now():
    return dt.datetime.now(UTC)


# ------------------------------------------------------------------------------------------------ external commands

def run_cmd(args, *, write=False, execute=False, timeout=180):
    """The single gate for every external command; logs each one to stderr.

    write=True marks a command that changes the platform (submit, submissions activate, match-groups create). It runs
    only when execute=True, exactly once (never retried), and is otherwise printed as '[dry-run] <command>' (returns None).
    Returns (returncode, stdout, stderr); a timeout gives returncode -1."""
    args = [str(x) for x in args]
    line = shlex.join(args)
    if write and not execute:
        print('[dry-run] ' + line, flush=True)
        return None
    if write:
        print('[execute] ' + line, flush=True)
    t0 = time.time()
    try:
        r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace',
                           timeout=timeout)
        rc, out, err = r.returncode, r.stdout or '', r.stderr or ''
    except FileNotFoundError:
        raise LoopError(f'{args[0]!r} not found: is it installed and on PATH?')
    except subprocess.TimeoutExpired:
        rc, out, err = -1, '', f'timed out after {timeout}s'
    log(f"{'WRITE ' if write else ''}$ {line}   [rc {rc}, {time.time() - t0:.1f}s]")
    return rc, out, err


def parse_json(text):
    """JSON from a command's stdout, tolerating a banner line before it."""
    text = (text or '').strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    dec = json.JSONDecoder()
    for i in [i for i, ch in enumerate(text) if ch in '{['][:50]:
        try:
            return dec.raw_decode(text, i)[0]
        except json.JSONDecodeError:
            continue
    raise ValueError('no JSON in the output')


def cambc_json(*args, retries=3):
    """A read-only `cambc ... --json` call, parsed; retried with back-off on failure or unparsable output."""
    cmd = [CAMBC, *args, '--json']
    err = ''
    for attempt in range(retries + 1):
        rc, out, err = run_cmd(cmd)
        if rc == 0:
            try:
                return parse_json(out)
            except ValueError:
                err = 'unparsable output: ' + out.strip()[:300]
        if attempt < retries:
            wait = 3 * (attempt + 1)
            log(f'  retry {attempt + 1}/{retries} in {wait}s: {err.strip()[:200]}')
            time.sleep(wait)
    raise LoopError(f'`{shlex.join(cmd)}` failed after {retries + 1} attempts: {err.strip()[:400]}')


# ------------------------------------------------------------------------------------------------ local files

def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise LoopError(f'cannot read {path}: {e}')


def save_json(path, data):
    """Atomic write (temp file + rename), so an interrupted run never leaves a half-written file."""
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1)
        f.write('\n')
    os.replace(tmp, path)


def load_state(path):
    st = load_json(path, {})
    if not isinstance(st, dict):
        raise LoopError(f'{path}: expected a JSON object')
    st.setdefault('history', [])
    return st


def save_state(path, st):
    st['updatedAt'] = iso(now())
    save_json(path, st)
    print(f'state saved: {path}')


def append_log(path, line):
    with open(path, 'a', encoding='utf-8') as f:
        f.write(line.rstrip('\n') + '\n')


def rel(path):
    p = os.path.abspath(path)
    return os.path.relpath(p, ROOT) if p.startswith(ROOT + os.sep) else p


def load_plan(path):
    if not os.path.exists(path):
        raise LoopError(f'plan file not found: {path}')
    plan = load_json(path, None)
    if not isinstance(plan, list):
        raise LoopError(f'{path}: expected a JSON list of groups (the `tools/paired_groups.py plan` format)')
    for i, g in enumerate(plan):
        miss = [k for k in ('oppId', 'sourceGroup', 'maps', 'sides', 'old') if not g.get(k)]
        if miss:
            raise LoopError(f'{path}: group #{i} lacks {", ".join(miss)}')
        if not len(g['maps']) == len(g['sides']) == len(g['old']) == 5:
            raise LoopError(f'{path}: group #{i} needs exactly 5 maps, 5 sides and 5 old results')
    return plan


def plan_old_version(path, plan):
    """The version that played the plan's original games: an `old_version` key, else `_v<N>` in the file name."""
    vs = {g.get('old_version') for g in plan if g.get('old_version') is not None}
    if len(vs) == 1:
        return int(vs.pop())
    m = re.search(r'_v(\d+)(?!\d)', os.path.basename(path))
    return int(m.group(1)) if m else None


# ------------------------------------------------------------------------------------------------ platform reads

def get_submissions(before=None):
    d = cambc_json('submissions', 'list', *(['--before', str(before)] if before else []))
    if not isinstance(d, dict) or not isinstance(d.get('submissions'), list):
        raise LoopError('unexpected `cambc submissions list --json` output (no "submissions" list)')
    return d


def live_sub(d):
    a = d.get('active')
    if not isinstance(a, dict) or a.get('version') is None:
        raise LoopError('no live submission: "active" is empty in `cambc submissions list --json`')
    return a


def find_sub(d, version, deep=True):
    """The submission with this version number: first page, then older pages (--before) when deep."""
    page = d
    for _ in range(12):
        for s in [page.get('active') or {}] + page['submissions']:
            if s.get('version') == version:
                return s
        if not deep or not page.get('more') or not page['submissions']:
            return None
        page = get_submissions(before=min(s.get('version') or 0 for s in page['submissions']))
    return None


def build_state(status):
    """'ready' (built: active / inactive), 'failed', or 'building' (anything else, e.g. queued / building)."""
    s = str(status or '').lower()
    if s in ('active', 'inactive', 'ready', 'built', 'success', 'succeeded', 'compiled'):
        return 'ready'
    if any(k in s for k in ('fail', 'error', 'reject', 'invalid', 'cancel')):
        return 'failed'
    return 'building'


def other_changes(d, live):
    """Other versions whose status changed after the live version was uploaded and before its statusAt.
    A status change of another version is a version switch; if one happened before the live version's statusAt,
    that statusAt may have been moved later by a re-activation (seen on Nov 2: v85 statusAt 23:15 while v84 went
    inactive at 21:15, when v85 went live)."""
    t_up, t_st = parse_ts(live['createdAt']), parse_ts(live['statusAt'])
    out = []
    for s in d['submissions']:
        if s.get('version') == live['version'] or not s.get('statusAt'):
            continue
        t = parse_ts(s['statusAt'])
        if t_up <= t <= t_st - dt.timedelta(seconds=5):
            out.append((t, s['version']))
    return sorted(out)


def guess_previous(d, live, since):
    """The version the live one replaced: the other version whose status changed closest to `since` (within 10 min),
    else the last one that changed before it."""
    others = [(parse_ts(s['statusAt']), s['version']) for s in d['submissions']
              if s.get('version') != live['version'] and s.get('statusAt')]
    near = [(abs((t - since).total_seconds()), v) for t, v in others if abs((t - since).total_seconds()) <= 600]
    if near:
        return min(near)[1]
    before = [(t, v) for t, v in others if t <= since]
    return max(before)[1] if before else None


def resolve_since(a, d, st, quiet=False):
    """When the live version went live: --since, else the state file (deploy / adopt), else its statusAt."""
    live = live_sub(d)
    if getattr(a, 'since', None):
        return parse_ts(a.since), '--since'
    cur = st.get('current') or {}
    if cur.get('version') == live['version'] and cur.get('activatedAt'):
        return parse_ts(cur['activatedAt']), 'state file'
    t = parse_ts(live['statusAt'])
    ch = other_changes(d, live)
    if ch and not quiet:
        log(f"warning: v{live['version']}'s statusAt {iso(t)} may be later than its real activation: other versions "
            f"changed status after it was uploaded ({', '.join(f'v{v} at {iso(x)}' for x, v in ch)}). A re-activation "
            f"moves statusAt. Using statusAt; if you know when v{live['version']} went live, pass --since ISO or record "
            f"it once with `{SELF} adopt --since ISO`.")
    return t, 'statusAt'


def get_ladder():
    """teamId -> {'rank', 'name', 'rating'} for every team on the ladder (pages of 100: 1..9 today)."""
    teams, page, total = {}, 1, None
    while page <= 20:
        d = cambc_json('ladder', '--page', str(page), '--limit', '100')
        rows = (d.get('teams') or []) if isinstance(d, dict) else []
        for t in rows:
            if t.get('teamId') and t.get('rating') is not None:
                teams[t['teamId']] = {'rank': t.get('rank'), 'name': t.get('name'), 'rating': float(t['rating'])}
        total = (d.get('total') if isinstance(d, dict) else None) or total
        if len(rows) < 100 or (total and page * 100 >= total):
            break
        page += 1
    if ME not in teams:
        raise LoopError(f'our team {ME} is not on the ladder ({len(teams)} teams scanned)')
    return teams


# ------------------------------------------------------------------------------------------------ matches

def load_local_matches():
    """matchId -> row from matches_me.jsonl (the fetch_me.py cache); a half-written line is skipped."""
    out = {}
    if os.path.exists(MATCHES):
        with open(MATCHES, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    m = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if m.get('matchId'):
                    out[m['matchId']] = m
    return out


def refresh_local(pages):
    """Run the existing fetcher (read-only API calls; merges new matches into matches_me.jsonl)."""
    rc, out, err = run_cmd([sys.executable, FETCH_ME, '--pages', str(pages)], timeout=900)
    if rc != 0:
        log(f'warning: fetch_me.py failed (rc {rc}): {err.strip()[:300]}; using the cached {rel(MATCHES)}')
    elif out.strip():
        log('  ' + out.strip().splitlines()[-1])


def game(m):
    """One match from our side, or None when we are not in it."""
    teams = m.get('teams') or []
    me = next((t for t in teams if t.get('teamId') == ME), None)
    op = next((t for t in teams if t.get('teamId') != ME), None)
    if not me or not op or not m.get('createdAt'):
        return None
    return {'matchId': m.get('matchId'), 'groupId': m.get('groupId'), 'kind': m.get('kind'), 'status': m.get('status'),
            'map': m.get('map'), 'pos': m.get('position') or 0, 'side': me.get('side'), 'result': me.get('result'),
            'opp': op.get('teamId'), 'oppName': op.get('name') or '?', 'created': parse_ts(m['createdAt']),
            'finished': parse_ts(m['finishedAt']) if m.get('finishedAt') else None}


def fetch_ranked(since, need_before=0, floor=None, max_pages=30):
    """Our ranked matches straight from the API (newest first), paging back until all games since `since` and
    `need_before` finished older games (not older than `floor`) are in; merged over the matches_me.jsonl cache."""
    rows = {k: v for k, v in load_local_matches().items() if v.get('kind') == 'ranked'}
    fresh_before, cur = 0, None
    for _ in range(max_pages):
        d = cambc_json('matches', 'list', '--team', 'me', '--kind', 'ranked', '--limit', '100',
                       *(['--cursor', cur] if cur else []))
        ms = [m for m in (d.get('matches') or []) if m.get('matchId') and m.get('createdAt')]
        for m in ms:
            rows[m['matchId']] = m
            if m.get('status') == 'finished' and parse_ts(m['createdAt']) < since:
                fresh_before += 1
        cur = d.get('nextCursor')
        if not ms or not cur:
            break
        oldest = min(parse_ts(m['createdAt']) for m in ms)
        if oldest < since and (fresh_before >= need_before or (floor is not None and oldest < floor)):
            break
    return rows


def ranked_windows(rows, since, prev_n, prev_floor=None):
    """(games created after `since`, the last prev_n games that were created and finished before it).
    A game created before `since` but finished after it could have been played by either version: dropped."""
    gs = [g for g in (game(m) for m in rows.values())
          if g and g['kind'] == 'ranked' and g['status'] == 'finished' and g['result'] in ('win', 'loss')]
    new = sorted((g for g in gs if g['created'] >= since), key=lambda g: g['created'])
    old = [g for g in gs if g['created'] < since and (g['finished'] or g['created']) < since
           and (prev_floor is None or g['created'] >= prev_floor)]
    old.sort(key=lambda g: g['created'], reverse=True)
    return new, old[:prev_n]


# ------------------------------------------------------------------------------------------------ statistics

def expect(r_me, r_opp):
    """Elo expected score of r_me against r_opp."""
    return 1.0 / (1.0 + 10.0 ** ((r_opp - r_me) / 400.0))


def perf_rating(opp_ratings, wins):
    """The rating whose Elo-expected score against these opponents equals the actual wins (bisection)."""
    n = len(opp_ratings)
    if n == 0:
        return None
    lo, hi = min(opp_ratings) - 800.0, max(opp_ratings) + 800.0
    if wins <= 0:
        return lo
    if wins >= n:
        return hi
    for _ in range(60):
        mid = (lo + hi) / 2
        if sum(expect(mid, r) for r in opp_ratings) < wins:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def sign_test_p(a, b):
    """Two-sided exact sign test on a vs b flips (each flip +/- with probability 1/2 under 'no difference')."""
    n = a + b
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(a, b) + 1)) / 2 ** n)


def two_prop_z(w1, n1, w0, n0):
    if not n1 or not n0:
        return None
    p = (w1 + w0) / (n1 + n0)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n0))
    return (w1 / n1 - w0 / n0) / se if se > 0 else 0.0


def rate(games, lad):
    """[(game, opponent's current ladder rating)] for the games whose opponent is on the ladder."""
    return [(g, lad[g['opp']]['rating']) for g in games if g['opp'] in lad]


def ranked_compare(new, old, lad, fallback_base=None, min_base=30):
    """The live version's ranked games scored against the previous version's Elo level.

    Baseline = the previous version's performance rating over `old` (vs the opponents' current ratings); its own
    uncertainty is folded into the SE: SE^2 = V1 * (1 + V1/V0), V = sum of E(1-E). With fewer than min_base old games
    the rating recorded at activation (state file) is the baseline (SE = sqrt(V1)). z < 0: below the old level."""
    r1, r0 = rate(new, lad), rate(old, lad)
    w1 = sum(g['result'] == 'win' for g, _ in r1)
    w0 = sum(g['result'] == 'win' for g, _ in r0)
    out = {'n1': len(r1), 'w1': w1, 'n0': len(r0), 'w0': w0, 'unrated': len(new) + len(old) - len(r1) - len(r0),
           'perf1': perf_rating([r for _, r in r1], w1), 'perf0': perf_rating([r for _, r in r0], w0),
           'z2': two_prop_z(w1, len(r1), w0, len(r0)), 'base': None, 'z': None}
    if len(r0) >= min_base:
        base = out['perf0']
        v0 = sum(expect(base, r) * (1 - expect(base, r)) for _, r in r0)
        out['base_src'] = f"the previous version's performance rating over its last {len(r0)} ranked games"
    elif fallback_base is not None:
        base, v0 = float(fallback_base), None
        out['base_src'] = 'our ladder rating recorded at activation (state file)'
    else:
        out['base_src'] = f'none: only {len(r0)} earlier ranked games (need {min_base}) and no rating recorded at activation'
        return out
    e1 = [expect(base, r) for _, r in r1]
    x1, v1 = sum(e1), sum(e * (1 - e) for e in e1)
    se = math.sqrt(v1 * (1 + v1 / v0)) if v0 else math.sqrt(v1)
    out.update(base=base, exp1=x1, se=se, z=(w1 - x1) / se if se > 0 else 0.0, baseline_noise=bool(v0))
    return out


# ------------------------------------------------------------------------------------------------ paired groups

UUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.I)
QUOTA_WORDS = ('quota', 'rate limit', 'rate-limit', 'too many', '429', 'limit reached', 'exceeded', 'try again later')


def parse_group_id(out, g):
    """The new group's id from `match-groups create --json` output (format unverified, so searched broadly);
    None when no id can be found."""
    try:
        d = parse_json(out)
    except ValueError:
        d = None

    def find(x, keys):
        if isinstance(x, dict):
            for k in keys:
                if isinstance(x.get(k), str) and UUID.fullmatch(x[k]):
                    return x[k]
            for v in x.values():
                hit = find(v, keys)
                if hit:
                    return hit
        elif isinstance(x, list):
            for v in x:
                hit = find(v, keys)
                if hit:
                    return hit
        return None

    known = {g['oppId'].lower(), g['sourceGroup'].lower(), ME}
    for keys in (('groupId', 'matchGroupId', 'group_id'), ('id',)):
        hit = find(d, keys)
        if hit and hit.lower() not in known:
            return hit
    ids = [u for u in UUID.findall(out or '') if u.lower() not in known]
    return ids[0] if ids else None


def group_games(gid, index, budget):
    """Our games in one group: from the local cache, else (if unfinished / missing) from `match-groups show`."""
    ms = index.get(gid) or []
    if sum(m.get('status') == 'finished' for m in ms) < 5 and budget[0] > 0:
        budget[0] -= 1
        try:
            d = cambc_json('match-groups', 'show', gid, retries=1)
            ms = (d.get('matches') if isinstance(d, dict) else None) or ms
        except LoopError as e:
            log(f'warning: {e}')
    return [g for g in (game(m) for m in ms) if g]


def resolve_unknown(g, index, used):
    """A group queued without a parsable id: the first unranked group vs the same opponent on the same maps and sides,
    created after it was queued."""
    t0 = parse_ts(g['new_queued_at']) - dt.timedelta(minutes=5) if g.get('new_queued_at') else None
    best = None
    for gid, ms in index.items():
        if gid in used or len(ms) != 5:
            continue
        gs = sorted((x for x in (game(m) for m in ms) if x), key=lambda x: x['pos'])
        if (len(gs) == 5 and gs[0]['kind'] == 'unranked' and all(x['opp'] == g['oppId'] for x in gs)
                and [x['map'] for x in gs] == g['maps'] and [x['side'] for x in gs] == g['sides']
                and (t0 is None or gs[0]['created'] >= t0) and (best is None or gs[0]['created'] < best[0])):
            best = (gs[0]['created'], gid)
    return best[1] if best else None


def pair_group(g, games):
    """Pair each planned game (map, our side, old result) with the replayed game on the same map and side."""
    used, pairs = set(), []
    pool = sorted(games, key=lambda x: x['pos'])
    for mp, sd, old in zip(g['maps'], g['sides'], g['old']):
        hit = next((x for x in pool if x['map'] == mp and x['side'] == sd and x['matchId'] not in used), None)
        if hit:
            used.add(hit['matchId'])
        new = hit['result'] if hit and hit['status'] == 'finished' and hit['result'] in ('win', 'loss') else None
        pairs.append((mp, sd, old, new))
    return pairs


def paired_analysis(plan, plan_path, live_v, live_since, refresh_pages, show_max, verbose):
    """Old vs new result of every replayed game, totals per version that played the replays."""
    if refresh_pages:
        refresh_local(refresh_pages)
    index = {}
    for m in load_local_matches().values():
        index.setdefault(m.get('groupId'), []).append(m)
    used = {g['new_group'] for g in plan if g.get('new_group') and not str(g['new_group']).startswith('?')}
    budget, by_ver, not_run = [show_max], {}, 0
    wl = {'win': 'W', 'loss': 'L', None: '.'}
    for g in plan:
        gid = g.get('new_group')
        if not gid:
            not_run += 1
            continue
        if str(gid).startswith('?'):
            gid = resolve_unknown(g, index, used)
            if not gid:
                print(f"  {g.get('opp', '?')[:24]:<24} queued at {g.get('new_queued_at')} but its group id is unknown "
                      f"and no matching group was found yet")
                continue
            used.add(gid)
            print(f"  (group id resolved by opponent / maps / sides: {gid}; put it in the plan as new_group)")
        games = group_games(gid, index, budget)
        if any(x['opp'] != g['oppId'] for x in games):
            print(f"  {g.get('opp', '?')[:24]:<24} group {gid[:8]}: opponent differs from the plan; skipped")
            continue
        ver, tag = g.get('new_version'), ''
        if ver is None and games and all(x['created'] >= live_since for x in games):
            ver, tag = live_v, '~'  # queued by another tool after the live version went live: inferred
        pairs = pair_group(g, games)
        c = by_ver.setdefault(ver, {'groups': 0, 'n': 0, 'old_w': 0, 'new_w': 0, 'wl': 0, 'lw': 0, 'pending': 0})
        c['groups'] += 1
        flips = []
        for mp, sd, o, n in pairs:
            if n is None:
                c['pending'] += 1
                continue
            c['n'] += 1
            c['old_w'] += o == 'win'
            c['new_w'] += n == 'win'
            if o == 'win' and n == 'loss':
                c['wl'] += 1
                flips.append(f'-{mp}/{sd}')
            elif o == 'loss' and n == 'win':
                c['lw'] += 1
                flips.append(f'+{mp}/{sd}')
        if verbose:
            vs = f'v{ver}{tag}' if ver is not None else 'v?'
            print(f"  {g.get('opp', '?')[:24]:<24} {gid[:8]} {vs:<5} "
                  f"{''.join(wl.get(o, '?') for o in g['old'])} -> {''.join(wl.get(n, '?') for _, _, _, n in pairs)}"
                  f"  {' '.join(flips)}")
    return {'by_ver': by_ver, 'not_run': not_run, 'old_v': plan_old_version(plan_path, plan), 'size': len(plan)}


def print_paired_totals(pa):
    print(f"plan: {pa['size']} groups (originals played by v{pa['old_v'] if pa['old_v'] is not None else '?'}), "
          f"{pa['size'] - pa['not_run']} replayed, {pa['not_run']} not run yet")
    for ver, c in sorted(pa['by_ver'].items(), key=lambda kv: (kv[0] is None, kv[0] or 0)):
        net = c['lw'] - c['wl']
        print(f"  replays by v{ver if ver is not None else '? (unknown version)'}: {c['groups']} groups, {c['n']} paired games"
              f" ({c['pending']} pending): old {c['old_w']}-{c['n'] - c['old_w']}, new {c['new_w']}-{c['n'] - c['new_w']};"
              f" flips L->W {c['lw']}, W->L {c['wl']}, net {net:+d}, sign test p = {sign_test_p(c['lw'], c['wl']):.3f}")


# ------------------------------------------------------------------------------------------------ shared analysis

def ranked_part(a, st, d, live, since):
    """Ranked games of the live version since `since` vs the previous version's last ranked games."""
    cur, prev = st.get('current') or {}, st.get('previous') or {}
    in_state = cur.get('version') == live['version']
    prev_v = prev.get('version') if in_state and prev.get('version') is not None else guess_previous(d, live, since)
    floor = parse_ts(a.prev_since) if a.prev_since else (
        parse_ts(prev['activatedAt']) if in_state and prev.get('activatedAt') else None)
    rows = fetch_ranked(since, need_before=a.prev_n + 10, floor=floor)
    new, old = ranked_windows(rows, since, a.prev_n, floor)
    lad = get_ladder()
    rc = ranked_compare(new, old, lad, cur.get('ratingAtActivation') if in_state else None)
    rc.update(prev_v=prev_v, live_v=live['version'], since=since, floor=floor, me=lad[ME])
    return rc


def print_ranked(rc):
    lv, pv = rc['live_v'], rc['prev_v'] if rc['prev_v'] is not None else '?'
    pct = lambda w, n: f'{100 * w / n:.1f}%' if n else '-'
    perf = lambda p: f'{p:.0f}' if p is not None else '-'
    print(f"ranked: v{lv} since {iso(rc['since'])}: {rc['w1']}/{rc['n1']} ({pct(rc['w1'], rc['n1'])}), perf {perf(rc['perf1'])}")
    print(f"        before it (v{pv}), last {rc['n0']} games" + (f" since {iso(rc['floor'])}" if rc['floor'] else '') +
          f": {rc['w0']}/{rc['n0']} ({pct(rc['w0'], rc['n0'])}), perf {perf(rc['perf0'])}"
          + (f"   [{rc['unrated']} games vs teams no longer on the ladder left out]" if rc['unrated'] else ''))
    if rc['base'] is None:
        print(f"        Elo baseline: {rc['base_src']}")
        return
    print(f"        expected at v{pv}'s level ({rc['base']:.0f}, {rc['base_src']}): {rc['exp1']:.1f} wins of {rc['n1']}"
          f" -> {rc['w1'] - rc['exp1']:+.1f}, SE {rc['se']:.1f}{' incl. baseline noise' if rc['baseline_noise'] else ''},"
          f" z {rc['z']:+.2f}" + (f"; raw win rates: two-proportion z {rc['z2']:+.2f}" if rc['z2'] is not None else ''))


def common_analysis(a, verbose):
    st = load_state(a.state)
    d = get_submissions()
    live = live_sub(d)
    since, how = resolve_since(a, d, st)
    print(f"live: v{live['version']} \"{live.get('note', '')}\", live since {iso(since)} ({how})")
    plan_path = a.plan or st.get('plan')
    if plan_path and not os.path.isabs(plan_path) and not os.path.exists(plan_path):
        plan_path = os.path.join(ROOT, plan_path)
    pa = None
    if plan_path:
        plan = load_plan(plan_path)
        print(f'paired replays ({rel(plan_path)}):')
        pa = paired_analysis(plan, plan_path, live['version'], since, 0 if a.no_refresh else a.pages, a.show_max, verbose)
        print_paired_totals(pa)
    else:
        print('paired replays: no plan (pass --plan PLAN.json)')
    rc = ranked_part(a, st, d, live, since)
    print_ranked(rc)
    return st, d, live, since, pa, rc


# ------------------------------------------------------------------------------------------------ commands

def cmd_snapshot(a):
    st = load_state(a.state)
    d = get_submissions()
    live = live_sub(d)
    since, how = resolve_since(a, d, st)
    lad = get_ladder()
    me = lad[ME]
    new, _ = ranked_windows(fetch_ranked(since), since, 0)
    r = rate(new, lad)
    n, w = len(r), sum(g['result'] == 'win' for g, _ in r)
    e = [expect(me['rating'], x) for _, x in r]
    exp, var = sum(e), sum(p * (1 - p) for p in e)
    z = (w - exp) / math.sqrt(var) if var > 0 else 0.0
    perf = perf_rating([x for _, x in r], w)
    bands = {}
    for g, x in r:
        b = bands.setdefault(int(x // 50 * 50), [0, 0])
        b[0] += g['result'] == 'win'
        b[1] += 1
    note = (live.get('note') or '').replace('"', "'")
    line = (f"{now():%Y-%m-%dT%H:%MZ} rank {me['rank']} rating {me['rating']:.0f} | live v{live['version']} \"{note}\" "
            f"since {iso(since)} ({how}) | ranked {w}/{n} ({100 * w / max(1, n):.0f}%), Elo-expected {exp:.1f} "
            f"({w - exp:+.1f}, z {z:+.1f})" + (f", perf {perf:.0f}" if perf is not None else '')
            + (f", +{len(new) - n} vs unrated" if len(new) > n else '')
            + ' | bands ' + ' '.join(f'{k}:{v[0]}/{v[1]}' for k, v in sorted(bands.items())) + ' | ladder_loop')
    print(line)
    if not a.no_log:
        append_log(a.log, line)
        log(f'appended to {rel(a.log)}')


def cmd_adopt(a):
    """Record a version that went live outside this tool (activation time + previous version) in the state file."""
    st = load_state(a.state)
    d = get_submissions()
    live = live_sub(d)
    if a.since:
        since = parse_ts(a.since)
    else:
        since, _ = resolve_since(argparse.Namespace(since=None), d, {})
    pv = a.previous if a.previous is not None else guess_previous(d, live, since)
    ps = find_sub(d, pv) if pv is not None else None
    if pv is not None and ps is None:
        raise LoopError(f'v{pv} is not among our submissions')
    st['current'] = {'version': live['version'], 'id': live.get('id'), 'note': live.get('note'),
                     'activatedAt': iso(since), 'statusAt': live.get('statusAt'), 'source': 'adopt'}
    st['previous'] = ({'version': pv, 'id': ps.get('id'), 'note': ps.get('note'), 'statusAt': ps.get('statusAt')}
                      if ps else None)
    st['history'].append({'at': iso(now()), 'event': 'adopt', 'version': live['version'], 'activatedAt': iso(since),
                          'previous': pv})
    print(f"current = v{live['version']} \"{live.get('note', '')}\", live since {iso(since)}; "
          f"previous = {'v' + str(pv) + ' ' + json.dumps(ps.get('note', '')) if ps else 'none'}")
    save_state(a.state, st)


def bot_name(arg):
    name = os.path.basename(os.path.normpath(arg))
    path = os.path.join(ROOT, 'bots', name)
    if not os.path.isdir(path):
        raise LoopError(f'bot directory not found: {path}')
    if not os.listdir(path):
        raise LoopError(f'bot directory is empty: {path}')
    return name


def previous_record(st, live):
    """What to store as `previous` for the version live now (carrying over what the state file knows about it)."""
    rec = {'version': live['version'], 'id': live.get('id'), 'note': live.get('note'), 'statusAt': live.get('statusAt')}
    cur = st.get('current') or {}
    if cur.get('version') == live['version']:
        for k in ('activatedAt', 'ratingAtActivation', 'rankAtActivation', 'bot'):
            if cur.get(k) is not None:
                rec[k] = cur[k]
    return rec


def parse_submit_version(out, after):
    """The new version number printed by `cambc submit` (its format is unverified), or None. A number that is not
    newer than every earlier version (e.g. the CLI's own 'v4.0.0') is ignored; the build poll then finds the upload."""
    for pat in (r'\bversion\s*[:#=]?\s*v?(\d+)(?![.\d])', r'\bv(\d+)(?![.\d])'):
        for m in re.finditer(pat, out or '', re.I):
            if int(m.group(1)) > after:
                return int(m.group(1))
    return None


def wait_built(pend, timeout, poll):
    """Poll `submissions list` until the pending upload is built (ready), failed, or the timeout passes."""
    deadline, last = time.time() + timeout, None
    t_sub = parse_ts(pend['submittedAt']) - dt.timedelta(minutes=2)
    while True:
        d = get_submissions()
        if pend.get('version') is not None:
            s = find_sub(d, pend['version'], deep=False)
        else:  # version not printed by `cambc submit`: our note, else the first upload after we submitted
            newer = [x for x in d['submissions'] if (x.get('version') or 0) > pend['afterVersion']]
            mine = [x for x in newer if (x.get('note') or '').strip() == pend['note'].strip()] or \
                   [x for x in newer if x.get('createdAt') and parse_ts(x['createdAt']) >= t_sub]
            s = min(mine, key=lambda x: x['version']) if mine else None
        if s is not None:
            pend['version'] = s['version']
            if s.get('status') != last:
                last = s.get('status')
                print(f"  v{s['version']} status: {last}   ({iso(now())})", flush=True)
            state = build_state(last)
            if state == 'ready':
                return s
            if state == 'failed':
                raise LoopError(f"v{s['version']} did not build (status {last!r}); see its build log on the website. "
                                f"The live version is unchanged.")
        if time.time() >= deadline:
            what = f"v{pend['version']}" if pend.get('version') is not None else 'the upload'
            raise LoopError(f'{what} is not built after {timeout:.0f}s (last status {last!r}). The live version is '
                            f'unchanged. When it is built: `{SELF} deploy --resume --execute`')
        time.sleep(poll)


def activate(version, execute, source):
    """Make a version live (a write command: printed unless execute), wait until the platform shows it live, and
    return the state record for it (activation time = its statusAt, our rank / rating just before the switch)."""
    cmd = [CAMBC, 'submissions', 'activate', str(version), '--json']
    if not execute:
        run_cmd(cmd, write=True)
        return None
    lad = get_ladder()
    rc, out, err = run_cmd(cmd, write=True, execute=True)
    if rc != 0:
        raise LoopError(f'`cambc submissions activate {version}` failed (rc {rc}): {(err or out).strip()[:400]}')
    for _ in range(12):
        live = get_submissions().get('active') or {}
        if live.get('version') == version:
            break
        time.sleep(5)
    else:
        raise LoopError(f'v{version} is still not live 60 s after `activate`; check `cambc submissions list`')
    return {'version': version, 'id': live.get('id'), 'note': live.get('note'),
            'activatedAt': iso(parse_ts(live['statusAt'])) if live.get('statusAt') else iso(now()),
            'statusAt': live.get('statusAt'), 'ratingAtActivation': round(lad[ME]['rating'], 1),
            'rankAtActivation': lad[ME]['rank'], 'source': source}


def cmd_deploy(a):
    st = load_state(a.state)
    d = get_submissions()
    live = live_sub(d)
    if d.get('frozen'):
        raise LoopError('submissions are frozen on the platform (frozen = true)')
    for k in ('submissionPause', 'submissionGrace'):
        if d.get(k):
            log(f'note: {k} = {json.dumps(d[k])}')
    if d.get('compilationPaused') or d.get('compilerAvailable') is False:
        log('warning: compilation is paused / the compiler is unavailable: the build may not finish in time')
    print(f"live now: v{live['version']} \"{live.get('note', '')}\"")
    if a.resume:
        pend = st.get('pending')
        if not pend:
            raise LoopError('nothing to resume: no pending deploy in the state file')
        print(f"resuming the deploy of {('v' + str(pend['version'])) if pend.get('version') is not None else 'the upload'}"
              f" ({pend['bot']}, submitted {pend['submittedAt']})")
    else:
        if not a.bot or not a.note:
            raise LoopError('deploy needs BOT and --note "..." (or --resume)')
        if len(a.note) > 80 or '\n' in a.note:
            raise LoopError(f'--note must be one line of at most 80 characters (it has {len(a.note)})')
        if st.get('pending') and not a.force:
            p = st['pending']
            raise LoopError(f"a deploy is pending ({p['bot']}, submitted {p['submittedAt']}): "
                            f"`{SELF} deploy --resume --execute`, or pass --force to upload a new one")
        bot = bot_name(a.bot)
        prev = previous_record(st, live)
        after = max([s.get('version') or 0 for s in d['submissions']] + [live['version']])
        submit = [CAMBC, 'submit', bot, '-n', a.note]
        if not a.execute:
            print(f"[dry-run] would record previous = v{prev['version']} in {rel(a.state)}")
            run_cmd(submit, write=True)
            print(f'[dry-run] would poll `cambc submissions list --json` every {a.poll:.0f}s (up to {a.timeout:.0f}s) '
                  f'until the new version (> v{after}) is built, read the ladder, then:')
            run_cmd([CAMBC, 'submissions', 'activate', '<NEW_VERSION>', '--json'], write=True)
            print(f'[dry-run] would record current = <NEW_VERSION> (activation time, rank / rating) in {rel(a.state)} '
                  f'and append a DEPLOY line to {rel(a.log)}')
            return
        st['previous'] = prev
        save_state(a.state, st)
        t0 = now()
        rc, out, err = run_cmd(submit, write=True, execute=True, timeout=900)
        if out.strip():
            print(out.strip())
        if rc != 0:
            raise LoopError(f'`cambc submit` failed (rc {rc}): {(err or out).strip()[:400]}')
        pend = {'version': parse_submit_version(out, after), 'bot': bot, 'note': a.note, 'submittedAt': iso(t0),
                'afterVersion': after}
        st['pending'] = pend
        st['history'].append({'at': iso(t0), 'event': 'submit', 'bot': bot, 'note': a.note, 'version': pend['version']})
        save_state(a.state, st)
    pend = st['pending']
    if not a.execute:  # dry-run of --resume
        print(f'[dry-run] would poll `cambc submissions list --json` until it is built, then:')
        run_cmd([CAMBC, 'submissions', 'activate', str(pend.get('version') or '<NEW_VERSION>'), '--json'], write=True)
        return
    s = wait_built(pend, a.timeout, a.poll)
    st['pending'] = pend
    save_state(a.state, st)
    rec = activate(s['version'], True, 'deploy')
    rec.update(bot=pend['bot'], submittedAt=pend['submittedAt'])
    prev_v = (st.get('previous') or {}).get('version')
    st['current'], st['pending'] = rec, None
    st['history'].append({'at': iso(now()), 'event': 'deploy', 'version': rec['version'],
                          'activatedAt': rec['activatedAt'], 'previous': prev_v})
    save_state(a.state, st)
    line = (f"{now():%Y-%m-%dT%H:%MZ} DEPLOY v{rec['version']} \"{pend['note']}\" (bots/{pend['bot']}) live since "
            f"{rec['activatedAt']}; previous v{prev_v}; at activation rank {rec['rankAtActivation']} rating "
            f"{rec['ratingAtActivation']:.0f} | ladder_loop")
    append_log(a.log, line)
    print(line)
    print(f'next: `{SELF} paired-run --plan <plan of v{prev_v} groups> --max 20 --execute`, then `{SELF} verdict`')


def cmd_paired_run(a):
    plan = load_plan(a.plan)
    st = load_state(a.state)
    d = get_submissions()
    lv = live_sub(d)['version']
    old_v = plan_old_version(a.plan, plan)
    if old_v is not None and old_v == lv and not a.force:
        raise LoopError(f'the plan replays games of v{old_v}, which is live: the replays would be identical '
                        f'(deterministic games). Deploy the candidate first (or pass --force).')
    q = cambc_json('match-groups', 'quota')
    if not isinstance(q, dict):
        raise LoopError('unexpected `cambc match-groups quota --json` output')
    quota = q.get('quota') or {}
    limit, used = quota.get('limit'), quota.get('used')
    remaining = limit - used if isinstance(limit, int) and isinstance(used, int) else None
    print(f"quota: used {used} of {limit} (rolling hour), resetsAt {quota.get('resetsAt')}, ready {q.get('ready')}, "
          f"our rank {q.get('requesterRank')}, maxRankGap {q.get('maxRankGap')}")
    if q.get('ready') is False:
        raise LoopError('`match-groups quota` reports ready = false: the platform takes no groups now; try later')
    todo = [g for g in plan if not g.get('new_group')]
    n = min(a.max, len(todo), remaining if remaining is not None else len(todo))
    print(f"plan {rel(a.plan)}: {len(plan)} groups (originals by v{old_v if old_v is not None else '?'}), "
          f"{len(plan) - len(todo)} already replayed, {len(todo)} to go; queuing {n} now with live v{lv}")
    if remaining is not None and remaining <= 0:
        print(f"quota used up: try again after {quota.get('resetsAt') or 'the rolling hour frees slots'}")
        return
    ranks, gap, my_rank = q.get('opponentRanks') or {}, q.get('maxRankGap'), q.get('requesterRank')
    done = fails = 0
    for g in todo:
        if done >= n:
            break
        orank = ranks.get(g['oppId'])
        if gap and my_rank and orank and abs(orank - my_rank) > gap:
            print(f"  skip {g.get('opp')}: rank {orank} is more than maxRankGap {gap} from ours ({my_rank})")
            continue
        cmd = [CAMBC, 'match-groups', 'create', g['oppId'], '--source-group', g['sourceGroup'],
               '--maps', ','.join(g['maps']), '--sides', ','.join(g['sides']), '--json']
        if not a.execute:
            run_cmd(cmd, write=True)
            done += 1
            continue
        rc, out, err = run_cmd(cmd, write=True, execute=True)
        if rc != 0:
            msg = (err or out).strip()
            if any(k in msg.lower() for k in QUOTA_WORDS):
                print(f'stopping: quota / rate limit reached ({msg[:200]})')
                try:
                    qq = (cambc_json('match-groups', 'quota', retries=1).get('quota') or {})
                    print(f"  quota now: used {qq.get('used')} of {qq.get('limit')}, resetsAt {qq.get('resetsAt')}; "
                          f"run the same command again later (it skips groups already queued)")
                except LoopError:
                    pass
                break
            g['last_error'] = msg[:300]
            save_json(a.plan, plan)
            fails += 1
            print(f"  failed {g.get('opp')}: {msg[:200]}")
            if fails >= 3:
                print('stopping: 3 failures in a row')
                break
            continue
        fails = 0
        gid = parse_group_id(out, g)
        if not gid:
            gid = '?'
            g['new_raw'] = out.strip()[:500]
            print(f'  warning: no group id in the output; paired-report will look the group up by opponent / maps / sides')
        g.update(new_group=gid, new_version=lv, new_queued_at=iso(now()))
        g.pop('last_error', None)
        save_json(a.plan, plan)  # after every group: an interruption never loses a queued id
        done += 1
        print(f"  queued {g.get('opp')} {','.join(g['maps'])} -> {gid}")
        time.sleep(a.sleep)
    if a.execute and done:
        st['plan'] = rel(a.plan)
        save_state(a.state, st)
    if not a.execute:
        print(f'[dry-run] {done} commands printed; with --execute each new group id is stored in {rel(a.plan)}')


def cmd_paired_report(a):
    common_analysis(a, verbose=True)


def cmd_verdict(a):
    st, d, live, since, pa, rc = common_analysis(a, verbose=a.verbose)
    lv = live['version']
    votes, why = [], []
    c = (pa or {}).get('by_ver', {}).get(lv) if pa else None
    if pa is None:
        why.append('paired: no plan given -> no signal')
    elif pa['old_v'] is not None and pa['old_v'] == lv:
        why.append(f'paired: the plan replays v{lv} itself -> not informative')
    elif not c or c['n'] < a.min_games:
        why.append(f"paired: {c['n'] if c else 0} paired games by v{lv} (need >= {a.min_games}) -> no signal yet")
    else:
        net, p = c['lw'] - c['wl'], sign_test_p(c['lw'], c['wl'])
        s = f"paired: {c['n']} games, L->W {c['lw']} vs W->L {c['wl']} (net {net:+d}), sign test p = {p:.3f}"
        if net < 0 and p < a.p:
            votes.append('ROLLBACK')
            why.append(f'{s} < {a.p} -> ROLLBACK signal')
        elif net > 0 and p < a.p:
            votes.append('KEEP')
            why.append(f'{s} < {a.p} -> KEEP signal')
        else:
            why.append(f'{s} -> not significant (need p < {a.p})')
    if rc['z'] is None:
        why.append(f"ranked: no Elo baseline ({rc['base_src']}) -> no signal")
    elif rc['n1'] < a.min_games:
        why.append(f"ranked: {rc['n1']} ranked games by v{lv} (need >= {a.min_games}) -> no signal yet "
                   f"(so far z {rc['z']:+.2f})")
    else:
        s = (f"ranked: {rc['w1']}/{rc['n1']} vs {rc['exp1']:.1f} expected at the previous level -> "
             f"{rc['w1'] - rc['exp1']:+.1f} wins, z {rc['z']:+.2f}")
        if rc['z'] < -a.z:
            votes.append('ROLLBACK')
            why.append(f'{s} < -{a.z} -> ROLLBACK signal')
        elif rc['z'] > a.z:
            votes.append('KEEP')
            why.append(f'{s} > +{a.z} -> KEEP signal')
        else:
            why.append(f'{s} -> within +-{a.z} SE')
    verdict = 'ROLLBACK' if 'ROLLBACK' in votes else 'KEEP' if 'KEEP' in votes else 'WAIT'
    print(f'\nverdict for v{lv}:')
    for x in why:
        print('  ' + x)
    if 'ROLLBACK' in votes and 'KEEP' in votes:
        print('  note: the two signals disagree; ROLLBACK takes precedence')
    print(f'VERDICT: {verdict}')
    prev_v = (st.get('previous') or {}).get('version') if (st.get('current') or {}).get('version') == lv else None
    if verdict == 'ROLLBACK':
        print(f'next: `{SELF} rollback --execute`' + (f' (activates v{prev_v})' if prev_v is not None else
                                                       f" -- no previous version recorded: add --to {rc['prev_v'] or 'N'}"))
    elif verdict == 'KEEP':
        print(f'next: keep v{lv}; it is the baseline for the next candidate')
    else:
        print('next: re-run after more games (ranked games come about 30 an hour; paired: `paired-run --max N --execute`)')


def cmd_rollback(a):
    st = load_state(a.state)
    d = get_submissions()
    live = live_sub(d)
    lv = live['version']
    cur, prev = st.get('current') or {}, st.get('previous') or {}
    target = a.to if a.to is not None else prev.get('version')
    if target is None:
        raise LoopError(f'no previous version in {rel(a.state)}; pass --to N (e.g. the version live before v{lv})')
    if a.to is None and prev.get('rolledBack'):
        raise LoopError(f"v{target} was rolled back from already; pass --to N to choose a version explicitly")
    if target == lv:
        print(f'v{target} is already live: nothing to do')
        return
    if a.to is None and cur.get('version') is not None and cur['version'] != lv and not a.force:
        raise LoopError(f"live is v{lv}, but the state file says v{cur['version']} (someone switched versions): "
                        f"refusing; pass --to N or --force")
    s = find_sub(d, target)
    if s is None:
        raise LoopError(f'v{target} is not among our submissions')
    if build_state(s.get('status')) != 'ready':
        raise LoopError(f"v{target} is not built (status {s.get('status')!r})")
    print(f"rollback: v{lv} \"{live.get('note', '')}\" -> v{target} \"{s.get('note', '')}\"")
    old = previous_record(st, live)
    rec = activate(target, a.execute, 'rollback')
    if rec is None:
        print(f'[dry-run] would record current = v{target}, previous = v{lv} (marked rolled back) in {rel(a.state)} '
              f'and append a ROLLBACK line to {rel(a.log)}')
        return
    old['rolledBack'] = True
    st['current'], st['previous'] = rec, old
    st['history'].append({'at': iso(now()), 'event': 'rollback', 'from': lv, 'version': target,
                          'activatedAt': rec['activatedAt']})
    save_state(a.state, st)
    line = (f"{now():%Y-%m-%dT%H:%MZ} ROLLBACK v{lv} -> v{target} \"{s.get('note', '')}\" live since "
            f"{rec['activatedAt']}; rank {rec['rankAtActivation']} rating {rec['ratingAtActivation']:.0f} | ladder_loop")
    append_log(a.log, line)
    print(line)


# ------------------------------------------------------------------------------------------------ CLI

def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--state', default=os.path.join(HERE, 'loop_state.json'), help='state file (default: %(default)s)')
    common.add_argument('--log', default=os.path.join(HERE, 'loop_log.md'), help='log file (default: %(default)s)')
    since = argparse.ArgumentParser(add_help=False)
    since.add_argument('--since', help='when the live version went live (ISO, UTC unless an offset is given); '
                                       'default: the state file, else its statusAt')
    analysis = argparse.ArgumentParser(add_help=False)
    analysis.add_argument('--no-refresh', action='store_true', help='do not run fetch_me.py first')
    analysis.add_argument('--pages', type=int, default=3, help='fetch_me.py --pages (default 3)')
    analysis.add_argument('--show-max', type=int, default=150,
                          help='at most this many `match-groups show` calls for groups missing from the cache')
    analysis.add_argument('--prev-n', type=int, default=100, help="the previous version's last N ranked games (100)")
    analysis.add_argument('--prev-since', help="ignore ranked games before this time in the previous version's window")

    p = argparse.ArgumentParser(prog='ladder_loop.py', description=__doc__.split('\n\n')[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog='Details: LADDER_LOOP.md')
    sub = p.add_subparsers(dest='cmd', required=True, metavar='COMMAND')

    s = sub.add_parser('snapshot', parents=[common, since], help='rank, rating, live version, ranked record since it went live')
    s.add_argument('--no-log', action='store_true', help='do not append the line to the log')
    s.set_defaults(func=cmd_snapshot)

    s = sub.add_parser('adopt', parents=[common], help='record a version made live outside this tool in the state file')
    s.add_argument('--since', help='when it went live (default: its statusAt)')
    s.add_argument('--previous', type=int, help='the version it replaced (default: guessed from status times)')
    s.set_defaults(func=cmd_adopt)

    s = sub.add_parser('deploy', parents=[common], help='record previous, submit BOT, wait for the build, activate')
    s.add_argument('bot', nargs='?', help='directory name under bots/ (e.g. god23)')
    s.add_argument('--note', '-n', help='submission note, at most 80 characters')
    s.add_argument('--resume', action='store_true', help='continue a pending deploy (wait for its build, activate)')
    s.add_argument('--execute', action='store_true', help='really submit and activate (default: print the commands)')
    s.add_argument('--force', action='store_true', help='upload even though a deploy is pending')
    s.add_argument('--timeout', type=float, default=900, help='build wait in seconds (default 900)')
    s.add_argument('--poll', type=float, default=15, help='poll interval in seconds (default 15)')
    s.set_defaults(func=cmd_deploy)

    s = sub.add_parser('paired-run', parents=[common], help='queue up to N not-yet-run groups of a plan')
    s.add_argument('--plan', required=True)
    s.add_argument('--max', type=int, required=True, help='queue at most N groups (each spends 1 of ~50 per hour)')
    s.add_argument('--execute', action='store_true', help='really queue (default: print the commands)')
    s.add_argument('--force', action='store_true', help='queue even when the live version played the originals')
    s.add_argument('--sleep', type=float, default=1.0, help='pause between groups in seconds (default 1)')
    s.set_defaults(func=cmd_paired_run)

    s = sub.add_parser('paired-report', parents=[common, since, analysis],
                       help='old vs new per group, flips, sign test; ranked vs the previous version')
    s.add_argument('--plan', required=True)
    s.set_defaults(func=cmd_paired_report)

    s = sub.add_parser('verdict', parents=[common, since, analysis], help='KEEP / ROLLBACK / WAIT with the reasoning')
    s.add_argument('--plan', help='paired plan (default: the last one paired-run used, from the state file)')
    s.add_argument('--min-games', type=int, default=60, help='games needed before a signal counts (60)')
    s.add_argument('--p', type=float, default=0.2, help='sign test threshold (0.2)')
    s.add_argument('--z', type=float, default=1.5, help='ranked threshold in SE (1.5)')
    s.add_argument('--verbose', action='store_true', help='also print every paired group')
    s.set_defaults(func=cmd_verdict)

    s = sub.add_parser('rollback', parents=[common], help='activate the previous version from the state file')
    s.add_argument('--to', type=int, help='activate this version instead')
    s.add_argument('--execute', action='store_true', help='really activate (default: print the command)')
    s.add_argument('--force', action='store_true', help='roll back even if the live version is not the recorded one')
    s.set_defaults(func=cmd_rollback)
    return p


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        a.func(a)
    except LoopError as e:
        print(f'error: {e}', file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('interrupted', file=sys.stderr)
        return 130
    return 0


if __name__ == '__main__':
    sys.exit(main())
