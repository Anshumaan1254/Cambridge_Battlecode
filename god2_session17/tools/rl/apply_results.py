#!/usr/bin/env python3
"""Turn an RL results archive (rl_results_<run>.tar.gz from tools/rl/train_rl.py) into a bot directory.

    python tools/rl/apply_results.py ARCHIVE_OR_best_params.json NEW_BOT [--base bb4] [--or-bits N] [--keep NAME ...] [--dry-run]

- reads best_params.json (the archive is unpacked into a temp folder);
- copies bots/<base>/src to bots/<NEW_BOT>/src and patches every "params_h_overrides" entry into params.h;
- ab_base: the trained switch bits OR --or-bits (switches added to the bot after the training ran, e.g. the middle bundle);
- --keep NAME: leave that param at the current bot's value (repeatable);
- prints the changes against the current bot's params.h and the championship table of the run."""
import argparse, json, os, re, shutil, sys, tarfile, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train_rl import read_param_types, patch_params  # noqa: E402


def load_best(path):
    if path.endswith(".json"):
        return json.load(open(path, encoding="utf-8"))
    tmp = tempfile.mkdtemp()
    with tarfile.open(path) as tf:
        tf.extractall(tmp)
    for base, _, files in os.walk(tmp):
        if "best_params.json" in files:
            return json.load(open(os.path.join(base, "best_params.json"), encoding="utf-8"))
    raise SystemExit("no best_params.json in " + path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("bot")
    ap.add_argument("--base", default="bb4")
    ap.add_argument("--or-bits", type=int, default=0)
    ap.add_argument("--keep", action="append", default=[])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    best = load_best(a.results)
    src_h = open(os.path.join(ROOT, "bots", a.base, "src", "params.h"), encoding="utf-8").read()
    types = read_param_types(src_h)
    ov = {k: v for k, v in best["params_h_overrides"].items() if k not in a.keep}
    ov["ab_base"] = int(ov.get("ab_base", 0)) | a.or_bits
    missing = [k for k in ov if k not in types]
    for k in missing:
        print(f"skip {k}: not in the current params.h")
        ov.pop(k)
    print(f"run chose: {best.get('chosen')}  generations {best.get('generations')}  games {best.get('games')}")
    for t in best.get("championship", []):
        print(f"  {t['name']:14s} reward {t['reward']:+.3f}  win {100 * t['winrate']:.1f}% (n{t['n']})  paired vs start {t.get('paired_vs_start', '-')} t={t.get('paired_t', '-')}")
    print("changes against the current bot:")
    for k, v in sorted(ov.items()):
        cur = types[k][1]
        new = str(v)
        if cur.rstrip("f") != new and not (cur.endswith("f") and abs(float(cur.rstrip("f")) - float(v)) < 1e-6 if re.match(r"^-?[\d.]+f?$", cur) and isinstance(v, (int, float)) else False):
            print(f"  {k:24s} {cur:>14s} -> {new}")
    if a.dry_run:
        return
    d = os.path.join(ROOT, "bots", a.bot)
    if os.path.exists(d):
        shutil.rmtree(d)
    shutil.copytree(os.path.join(ROOT, "bots", a.base, "src"), os.path.join(d, "src"))
    open(os.path.join(d, "src", "params.h"), "w", encoding="utf-8").write(patch_params(src_h, ov, types))
    print(f"wrote bots/{a.bot} (build: cambc build {a.bot})")


if __name__ == "__main__":
    main()
