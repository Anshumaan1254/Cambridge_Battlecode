#!/usr/bin/env python3
"""Self-play parameter tuner (coordinate descent with paired head-to-head evaluation).

For each parameter in SPACE, build variants of the current best with one value changed and play each
against (a) the current best, both sides on every map, and (b) a fixed panel of frozen opponents.
A variant is accepted only if it wins the head-to-head by a margin AND does not regress against the
panel. Accepted values are written to tune_out/best_params.json and to bots/_best/src/params.h.

usage: tune.py [--rounds-limit N] [--margin 0.55] [--panel _v1aggro,_v3] [--passes 1] [--only a,b]
Run from the repository root with `cambc` on PATH. It is slow by design (~40 s per 128-game match on
4 cores); run it in the background and read tune_out/log.txt.
"""
import argparse, json, os, re, shutil, subprocess, sys, time

SPACE = {
    'fight_margin': ['1.1f', '1.3f', '1.6f'],
    'fight_back_margin': ['0.6f', '0.75f', '0.9f'],
    'cornered_margin': ['0.3f', '0.45f', '0.6f'],
    'retreat_hp': ['0.2f', '0.25f', '0.32f'],
    'tribute_min': ['24', '34', '48'],
    'tribute_near': ['3', '5', '8'],
    'gold_value': ['0.12f', '0.22f', '0.35f'],
    'deny_bonus': ['0.3f', '0.55f', '0.9f'],
    'enemy_half_penalty': ['4.f', '10.f', '18.f'],
    'max_trips': ['2', '3', '5'],
    'camp_hp_reserve': ['0.12f', '0.18f', '0.26f'],
    'hysteresis': ['1.05f', '1.15f', '1.3f'],
    'steal_hp_frac': ['0.4f', '0.55f', '0.7f'],
    'bag_caution': ['25', '40', '70'],
    'max_wait': ['10', '18', '28'],
}


def defaults():
    src = open('bots/legend/src/params.h').read()
    return {k: v.strip() for k, v in re.findall(r'^\s*\w+ (\w+) = ([^;]+);', src, re.M)}


def same(a, b):
    try:
        return abs(float(str(a).rstrip('f')) - float(str(b).rstrip('f'))) < 1e-9
    except ValueError:
        return a == b


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)


def make_variant(name, params):
    args = ' '.join(f'{k}={v}' for k, v in params.items())
    r = sh(f'tools/variant.sh {name} {args}')
    if r.returncode != 0:
        raise RuntimeError(r.stderr)


def match(a, b):
    r = sh(f'python3 tools/bench.py {a} {b} --jobs {os.cpu_count() or 4} --quiet')
    m = re.search(r'winrate=([0-9.]+)', r.stdout)
    if not m:
        raise RuntimeError(r.stdout + r.stderr)
    return float(m.group(1)), r.stdout.strip().splitlines()[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--margin', type=float, default=0.55)
    ap.add_argument('--panel', default='_v1aggro,_v3')
    ap.add_argument('--passes', type=int, default=1)
    ap.add_argument('--only', default='')
    args = ap.parse_args()
    os.makedirs('tune_out', exist_ok=True)
    log = open('tune_out/log.txt', 'a')

    def say(msg):
        line = f'[{time.strftime("%H:%M:%S")}] {msg}'
        print(line, flush=True)
        log.write(line + '\n'); log.flush()

    best = {}
    if os.path.exists('tune_out/best_params.json'):
        best = json.load(open('tune_out/best_params.json'))
    make_variant('_best', best)
    panel = [p for p in args.panel.split(',') if p]
    base_panel = {p: match('_best', p)[0] for p in panel}
    say(f'start best={best} panel={base_panel}')
    keys = [k for k in SPACE if not args.only or k in args.only.split(',')]
    dflt = defaults()
    for ps in range(args.passes):
        for key in keys:
            for val in SPACE[key]:
                cur = best.get(key, dflt.get(key))
                if cur is not None and same(cur, val):
                    continue
                cand = dict(best); cand[key] = val
                make_variant('_cand', cand)
                try:
                    h2h, line = match('_cand', '_best')
                except RuntimeError as e:
                    say(f'{key}={val} failed: {e}'); continue
                say(f'{key}={val}: h2h {h2h:.3f}  ({line})')
                if h2h < args.margin:
                    continue
                ok = True
                res = {}
                for p in panel:
                    w, _ = match('_cand', p)
                    res[p] = w
                    if w < base_panel[p] - 0.04:
                        ok = False
                say(f'   panel {res} vs base {base_panel} -> {"ACCEPT" if ok else "reject"}')
                if ok:
                    best = cand
                    base_panel = res
                    json.dump(best, open('tune_out/best_params.json', 'w'), indent=1)
                    make_variant('_best', best)
    say(f'done best={best}')


if __name__ == '__main__':
    main()
