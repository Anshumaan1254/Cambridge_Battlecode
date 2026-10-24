#!/usr/bin/env python3
"""Queue and collect unranked match groups.
  python tools/live/groups.py create OPP_TEAM_ID m1,m2,m3,m4,m5 a,b,a,b,a [--label TEXT]
  python tools/live/groups.py status            # show every recorded group's state and score
  python tools/live/groups.py pull              # fetch finished groups' summaries (compact) + record results
Groups are recorded in experiments/live/groups.jsonl (one line per group, with our bot label)."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cli
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GF = os.path.join(ROOT, "experiments", "live", "groups.jsonl")
US = "5a103c90-b00b-4d46-8ace-6a3bb058dc72"


def load():
    if not os.path.exists(GF):
        return []
    return [json.loads(l) for l in open(GF, encoding="utf-8") if l.strip()]


def save(rows):
    with open(GF, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def create(opp, maps, sides, label):
    rc, o, e = cli.run(["match-groups", "create", opp, "--maps", maps, "--sides", sides, "--json"])
    if rc != 0:
        print("create failed:", e.strip() or o.strip())
        return False
    d = json.loads(o)
    rows = load()
    rows.append({"created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "label": label, "opp": opp,
                 "maps": maps, "sides": sides, "resp": d})
    save(rows)
    print(json.dumps(d)[:600])
    return True


def gid(r):
    d = r["resp"]
    return d.get("id") or d.get("groupId") or (d.get("group") or {}).get("id")


def show(g):
    rc, o, e = cli.run(["match-groups", "show", g, "--json"])
    if rc != 0:
        return None
    return json.loads(o)


def status(pull=False, label=None):
    rows = load()
    tot = {}
    for r in rows:
        if label and r.get("label") != label:
            continue
        if r.get("done") and not pull:
            d = r["last"]
        else:
            d = show(gid(r))
        g = gid(r)
        if d is None:
            print(g, "show failed")
            continue
        r["last"] = d
        ms = d.get("matches") or (d.get("group") or {}).get("matches") or []
        w = l = pend = 0
        oppname = None
        for m in ms:
            st = m.get("status")
            if st != "finished":
                pend += 1
                continue
            for t in m.get("teams", []):
                if t.get("teamId") == US:
                    w += t.get("result") == "win"
                    l += t.get("result") == "loss"
                else:
                    oppname = t.get("name")
        lab = r.get("label", "?")
        tot.setdefault(lab, [0, 0])
        tot[lab][0] += w
        tot[lab][1] += l
        r["done"] = bool(ms) and pend == 0
        print(f"{r['created']} {lab:10s} vs {oppname or r['opp'][:8]:28s} W-L {w}-{l} pending {pend}  group {g}")
        if pull and ms and pend == 0:
            import subprocess
            lst = os.path.join(ROOT, "experiments", "live", "lists", "groups_matches.jsonl")
            have = set()
            if os.path.exists(lst):
                have = {json.loads(x)["matchId"] for x in open(lst, encoding="utf-8") if x.strip()}
            with open(lst, "a", encoding="utf-8") as f:
                for m in ms:
                    if m.get("matchId") not in have:
                        m.setdefault("kind", "unranked")
                        f.write(json.dumps(m) + "\n")
    save(rows)
    for lab, (w, l) in tot.items():
        print(f"TOTAL {lab}: {w}-{l}")


def rerun(src_label, new_label, only=None):
    """Queue the same groups (opponent, maps, sides) as every group recorded under src_label (paired comparison)."""
    rows = [r for r in load() if r.get("label") == src_label]
    for r in rows:
        if only and r["opp"] not in only:
            continue
        create(r["opp"], r["maps"], r["sides"], new_label)
        time.sleep(1)


def runset(path, label):
    """Queue every group of a saved set (experiments/live/setB.json: [opp_id, maps, sides, name])."""
    for opp, maps, sides, name in json.load(open(path, encoding="utf-8")):
        create(opp, maps, sides, label)
        time.sleep(1)


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "runset":
        runset(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 4 and sys.argv[1] == "rerun":
        rerun(sys.argv[2], sys.argv[3], sys.argv[4:] or None)
    elif len(sys.argv) >= 5 and sys.argv[1] == "create":
        label = sys.argv[sys.argv.index("--label") + 1] if "--label" in sys.argv else "?"
        create(sys.argv[2], sys.argv[3], sys.argv[4], label)
    elif len(sys.argv) >= 2 and sys.argv[1] in ("status", "pull"):
        status(pull=sys.argv[1] == "pull", label=sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        print(__doc__)
