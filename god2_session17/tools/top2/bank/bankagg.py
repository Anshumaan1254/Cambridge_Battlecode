"""god2 bank module (session 17): per-bot means of tools/top2/bank/bankstats.mjs lines from a localbench run.

  python tools/top2/bank/bankagg.py STATS.jsonl A B [--maps m1,m2]

Files are <map>_<side>.repl26a: on side A bot A is team 0, on side B bot A is team 1 (tools/live/localbench.py). A mirror (A == B)
pools both teams."""
import json, sys

KEYS = ["tribStarts", "done", "dead", "stunned", "locked", "cancel", "trib20", "trib20near7", "banks", "banked", "sub300", "sub600", "subEnd",
        "deaths", "lostBag", "lost100", "maxBag", "bag100Rounds", "recalls", "recNear5", "recDone", "recDead", "recInt", "heavyHitsBig",
        "enemyLocks", "captures", "capGems"]


def main():
    path, A, B = sys.argv[1], sys.argv[2], sys.argv[3]
    maps = None
    if "--maps" in sys.argv:
        maps = set(sys.argv[sys.argv.index("--maps") + 1].split(","))
    acc = {A: {k: 0.0 for k in KEYS + ["tribBag", "doneBag", "games"]}, B: {k: 0.0 for k in KEYS + ["tribBag", "doneBag", "games"]}}
    for line in open(path, encoding="utf-8"):
        d = json.loads(line)
        if "T" not in d:
            continue
        stem = d["file"][: -len(".repl26a")]
        mp, side = stem.rsplit("_", 1)
        if maps and mp not in maps:
            continue
        ta = 0 if side == "A" else 1
        for bot, t in ([(A, 0), (A, 1)] if A == B else [(A, ta), (B, 1 - ta)]):
            S = d["T"][str(t)]
            a = acc[bot]
            a["games"] += 1
            for k in KEYS + ["tribBag", "doneBag"]:
                a[k] += S.get(k, 0)
    for bot in ([A] if A == B else [A, B]):
        a = acc[bot]
        n = max(1.0, a["games"])
        st = max(1.0, a["tribStarts"])
        print(f"== {bot}: {int(a['games'])} team-games")
        print(f"  tributes started {a['tribStarts'] / n:.1f} / done {a['done'] / n:.1f} (dead {a['dead'] / n:.2f}, stunned {a['stunned'] / n:.2f}, "
              f"locked {a['locked'] / n:.2f}, own cancel {a['cancel'] / n:.2f}) | mean bag at start {a['tribBag'] / st:.1f}, at done "
              f"{a['doneBag'] / max(1.0, a['done']):.1f} | starts > 20 gems {a['trib20'] / n:.1f}, with an enemy within 7 {a['trib20near7'] / n:.2f}")
        print(f"  banks {a['banks'] / n:.1f} x {a['banked'] / max(1.0, a['banks']):.1f} gems | banked r300 {a['sub300'] / n:.0f}, r600 {a['sub600'] / n:.0f}, "
              f"end {a['subEnd'] / n:.0f} | captures {a['captures'] / n:.1f} ({a['capGems'] / n:.0f} gems)")
        print(f"  deaths {a['deaths'] / n:.1f}, bag lost {a['lostBag'] / n:.1f} (deaths with 100+: {a['lost100'] / n:.2f}) | max bag {a['maxBag'] / n:.0f} | "
              f"body-rounds with 100+ {a['bag100Rounds'] / n:.0f} | heavy-camp hits with 100+ {a['heavyHitsBig'] / n:.2f}")
        print(f"  recalls {a['recalls'] / n:.1f} (enemy within 5 at start {a['recNear5'] / n:.2f}; done {a['recDone'] / n:.1f}, interrupted "
              f"{a['recInt'] / n:.2f}, dead {a['recDead'] / n:.2f}) | enemy locks placed {a['enemyLocks'] / n:.2f}")


if __name__ == "__main__":
    main()
