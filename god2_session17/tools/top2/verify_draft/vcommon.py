"""vcommon.py: independent loaders for the draft-claim verification (verify_draft).
Lists: experiments/live/lists/** (dedup by matchId); ratings: C:/battlecode/cache/ladder_now.json; dumps: C:/battlecode/cache/t2dump."""
import json, glob, os, gzip
from datetime import datetime, timezone

ROOT = 'C:/battlecode/Cambridge_Battlecode'
CACHE = 'C:/battlecode/cache'
NAMES = ['Ry', 'Ve', 'Vd', 'CI', 'St', 'Pr', 'Ma', 'Wi', 'Re', 'Va', 'Ta', 'Ho']
STUDY = {'pbg': '38e6d8c4', 'ifish': '1890540d', 'pantheon': '547efb5b', 'coo': '1570a113', 'cm': 'ad5474c2', 'nyx': '6f7fd199'}


def ts(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


def load_matches(since='2026-10-22T07:00:00Z', files=None, kinds=('ranked',)):
    """All distinct finished matches with two teams, engine 1.0.3, createdAt >= since."""
    if files is None:
        files = glob.glob(f'{ROOT}/experiments/live/lists/**/*.jsonl', recursive=True)
    t0 = ts(since)
    out = {}
    for f in files:
        with open(f, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    m = json.loads(line)
                except Exception:
                    continue
                if not isinstance(m, dict) or 'matchId' not in m or 'teams' not in m:
                    continue
                if m.get('status') != 'finished' or (kinds and m.get('kind') not in kinds):
                    continue
                if len(m['teams']) != 2:
                    continue
                if any(t.get('engineVersion') != '1.0.3' for t in m['teams']):
                    continue
                if ts(m['createdAt']) < t0:
                    continue
                res = [t.get('result') for t in m['teams']]
                if sorted(res) != ['loss', 'win']:
                    continue
                out[m['matchId']] = m
    return out


def ratings():
    d = json.load(open(f'{CACHE}/ladder_now.json', encoding='utf-8'))
    return {t['teamId']: t['rating'] for t in d['teams']}, {t['teamId']: t['name'] for t in d['teams']}, {t['teamId']: t['rank'] for t in d['teams']}


def side_teams(m):
    """returns (teamA, teamB) where A has side 'a'"""
    a = [t for t in m['teams'] if t.get('side') == 'a']
    b = [t for t in m['teams'] if t.get('side') == 'b']
    if len(a) == 1 and len(b) == 1:
        return a[0], b[0]
    return m['teams'][0], m['teams'][1]


def picks(t):
    return [int(x) for x in (t.get('draftPicks') or t.get('characters') or [])]


def load_dump(path):
    with gzip.open(path, 'rb') as fh:
        return json.loads(fh.read())


def index_rows(key):
    rows = {}
    with open(f'{CACHE}/t2/{key}/index.jsonl', encoding='utf-8') as fh:
        for line in fh:
            m = json.loads(line)
            rows[m['matchId'][:8]] = m
    return rows
