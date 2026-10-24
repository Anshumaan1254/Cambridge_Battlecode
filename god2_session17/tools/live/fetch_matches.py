#!/usr/bin/env python3
"""Fetch match lists from the platform (cambc matches list --json) with pagination.

Usage: python tools/live/fetch_matches.py --team me|<uuid>|<name> [--kind ranked|unranked] [--max 200] [--out FILE]
Writes one JSON object per match (JSONL), newest first. Re-running merges by matchId.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cli


def run_list(team, kind, limit, cursor):
    cmd = ["matches", "list", "--json", "--limit", str(limit)]
    if team:
        cmd += ["--team", team]
    if kind:
        cmd += ["--kind", kind]
    if cursor:
        cmd += ["--cursor", cursor]
    rc, so, se = cli.run(cmd)
    if rc != 0:
        sys.stderr.write(se)
        raise SystemExit(rc)
    return json.loads(so)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", default="me")
    ap.add_argument("--kind", default=None)
    ap.add_argument("--max", type=int, default=200)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    seen, rows, cursor = set(), [], None
    while len(rows) < a.max:
        d = run_list(a.team, a.kind, min(100, a.max - len(rows)), cursor)
        ms = d.get("matches", [])
        for m in ms:
            if m["matchId"] not in seen:
                seen.add(m["matchId"])
                rows.append(m)
        cursor = d.get("nextCursor") or d.get("cursor") or d.get("next")
        if not ms or not cursor:
            break
    if a.out:
        old = {}
        if os.path.exists(a.out):
            for line in open(a.out, encoding="utf-8"):
                line = line.strip()
                if line:
                    m = json.loads(line)
                    old[m["matchId"]] = m
        for m in rows:
            old[m["matchId"]] = m
        allm = sorted(old.values(), key=lambda m: m.get("createdAt", ""), reverse=True)
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            for m in allm:
                f.write(json.dumps(m) + "\n")
        print(f"{len(rows)} fetched, {len(allm)} total in {a.out}")
    else:
        for m in rows:
            print(json.dumps(m))


if __name__ == "__main__":
    main()
