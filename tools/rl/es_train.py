#!/usr/bin/env python3
"""Offline reinforcement learning for the legend bot: evolution-strategies policy search with a shaped
reward ("reward good play, punish mistakes"), using the real engine as the simulator.

Why ES and not gradient RL: a submitted bot cannot be updated and cannot store anything between matches,
and 100k fuel per turn leaves no room for a neural network, so the policy is the bot's scoring rules and
the learnable part is its parameter vector (params.h). Matches are deterministic and take ~1.5 s, so we
optimise that vector directly with antithetic Evolution Strategies (Salimans et al. 2017) and rank-based
fitness shaping. The learned values are then baked into params.h before submission.

Reward per game (from our side, all terms from the engine's match statistics):
    + 1.0  win            - 1.0  loss
    + 0.6  * (our banked gems - their banked gems) / 1000
    - 0.03 * our deaths   + 0.015 * enemy deaths      (punish dying, reward kills)
    - 0.02 * (gems we carried into our deaths) / 22   (punish dying with a bag)
    + 0.15 * (2000 - win round) / 2000 on wins        (reward winning fast)
The opponent pool mixes frozen past versions, the starter bot and style archetypes (league training),
and every candidate of a generation plays the same maps and opponents (common random numbers).

usage:
  python3 tools/rl/es_train.py --space tools/rl/space.json --opponents _base,starter-cpp \
      --maps 'maps/ladder/*.map26a' --gens 12 --pop 6 --maps-per-gen 8 [--resume]
Outputs tune_out/es/: log.txt, history.json, best_params.json (apply with tools/rl/apply_params.py).
"""
import argparse, glob, json, math, os, random, re, shutil, subprocess, sys, time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'tune_out', 'es')


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT, **kw)


def read_defaults():
    src = open(os.path.join(ROOT, 'bots/legend/src/params.h')).read()
    return {k: v.strip() for k, v in re.findall(r'^\s*\w+ (\w+) = ([^;]+);', src, re.M)}


class Space:
    """Maps a real vector z (standard-normal scale) to parameter values within bounds."""

    def __init__(self, spec, defaults):
        self.keys = list(spec)
        self.spec = spec
        self.defaults = defaults

    def center(self):
        z = []
        for k in self.keys:
            s = self.spec[k]
            v = float(str(self.defaults[k]).rstrip('f'))
            z.append(self._to_z(s, v))
        return np.array(z, dtype=float)

    def _to_z(self, s, v):
        lo, hi = s['lo'], s['hi']
        if s.get('log'):
            lo, hi, v = math.log(lo), math.log(hi), math.log(max(v, 1e-9))
        v = min(max(v, lo), hi)
        return (v - lo) / (hi - lo) * 2 - 1  # [-1, 1]

    def values(self, z):
        out = {}
        for k, x in zip(self.keys, z):
            s = self.spec[k]
            lo, hi = s['lo'], s['hi']
            x = min(max(x, -1.0), 1.0)
            if s.get('log'):
                v = math.exp(math.log(lo) + (x + 1) / 2 * (math.log(hi) - math.log(lo)))
            else:
                v = lo + (x + 1) / 2 * (hi - lo)
            if s.get('int'):
                out[k] = str(int(round(v)))
            else:
                out[k] = f'{v:.4f}f'
        return out


def make_variant(name, params):
    """bots/NAME = bots/legend with these params.h defaults (same as tools/variant.sh, but portable: no GNU sed)."""
    dst = os.path.join(ROOT, 'bots', name)
    shutil.rmtree(os.path.join(dst, 'src'), ignore_errors=True)
    os.makedirs(dst, exist_ok=True)
    shutil.copytree(os.path.join(ROOT, 'bots/legend/src'), os.path.join(dst, 'src'))
    shutil.copy(os.path.join(ROOT, 'bots/legend/.gitignore'), dst)
    hp = os.path.join(dst, 'src', 'params.h')
    src = open(hp).read()
    for k, v in params.items():
        src, n = re.subn(rf'^(\s*\w+ {k} = )[^;]*;', lambda m: f'{m.group(1)}{v};', src, flags=re.M)
        if n != 1:
            raise RuntimeError(f'unknown param {k}')
    open(hp, 'w').write(src)
    r = sh(f'cambc build {name}')
    if r.returncode != 0:
        raise RuntimeError(r.stdout[-2000:] + r.stderr[-2000:])


def game_reward(stats_path, us):
    d = json.load(open(stats_path))
    them = 'teamB' if us == 'teamA' else 'teamA'
    gems = {t['team']: int(t['submittedGems']) for t in d['teams']}
    deaths = {us: 0, them: 0}
    for c in d['champions']:
        deaths[c['team']] += int(c['metrics']['deaths'])
    bag = 0
    for ev in d.get('events', []):
        if ev.get('kind') == 'gemLoss' and ev.get('owner', {}).get('team') == us:
            bag += sum(int(float(e['value'])) for e in ev['entries'])
    outcome = d['match']['outcome']
    rounds = int(d['match']['roundsCompleted'])
    win = outcome == us
    loss = outcome == them
    r = (1.0 if win else 0.0) - (1.0 if loss else 0.0)
    r += 0.6 * (gems[us] - gems[them]) / 1000.0
    r -= 0.03 * deaths[us]
    r += 0.015 * deaths[them]
    r -= 0.02 * bag / 22.0
    if win:
        r += 0.15 * (2000 - rounds) / 2000.0
    return r, win, loss


def evaluate(cands, opponents, maps, run_dir, jobs):
    """Every candidate plays every (map, opponent) on both sides. Returns mean reward per candidate."""
    os.makedirs(run_dir, exist_ok=True)
    manifest = os.path.join(run_dir, 'manifest.txt')
    rows = []
    with open(manifest, 'w') as f:
        for ci, c in enumerate(cands):
            for m in maps:
                mn = os.path.splitext(os.path.basename(m))[0]
                for o in opponents:
                    for side in ('A', 'B'):
                        a, b = (c, o) if side == 'A' else (o, c)
                        st = os.path.join(run_dir, f'{ci}_{mn}_{o}_{side}.json')
                        rp = os.path.join(run_dir, f'{ci}_{mn}_{o}_{side}.repl26a')
                        f.write(f'{ROOT}/bots/{a} {ROOT}/bots/{b} {os.path.abspath(m)} {rp} --statistics {st} --json\n')
                        rows.append((ci, st, 'teamA' if side == 'A' else 'teamB'))
    sh(f'cambc run-batch {manifest} --jobs {jobs} --color never --release')
    rewards = [[] for _ in cands]
    wins = [0] * len(cands)
    games = [0] * len(cands)
    for ci, st, us in rows:
        if not os.path.exists(st):
            rewards[ci].append(-1.5)  # crash / timeout counts as a heavy loss
            games[ci] += 1
            continue
        r, w, _ = game_reward(st, us)
        rewards[ci].append(r)
        wins[ci] += w
        games[ci] += 1
    shutil.rmtree(run_dir, ignore_errors=True)
    return [float(np.mean(r)) for r in rewards], [w / max(1, g) for w, g in zip(wins, games)]


def centered_ranks(x):
    x = np.asarray(x)
    ranks = np.empty(len(x))
    ranks[x.argsort()] = np.arange(len(x))
    return ranks / (len(x) - 1) - 0.5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--space', default=os.path.join(ROOT, 'tools/rl/space.json'))
    ap.add_argument('--opponents', default='_base,starter-cpp')
    ap.add_argument('--maps', default='maps/ladder/*.map26a')
    ap.add_argument('--maps-per-gen', type=int, default=8)
    ap.add_argument('--gens', type=int, default=10)
    ap.add_argument('--pop', type=int, default=6, help='antithetic pairs per generation')
    ap.add_argument('--sigma', type=float, default=0.25)
    ap.add_argument('--lr', type=float, default=0.35)
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 4)
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--resume', action='store_true')
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    log = open(os.path.join(OUT, 'log.txt'), 'a')

    def say(msg):
        line = f'[{time.strftime("%H:%M:%S")}] {msg}'
        print(line, flush=True)
        log.write(line + '\n')
        log.flush()

    spec = json.load(open(args.space))
    space = Space(spec, read_defaults())
    rng = random.Random(args.seed)
    nrng = np.random.default_rng(args.seed)
    maps_all = sorted({m for pat in args.maps.split(',') for m in glob.glob(os.path.join(ROOT, pat)) if not os.path.basename(m).startswith('zz_')})
    opponents = [o for o in args.opponents.split(',') if o]
    for o in opponents:
        sh(f'cambc build {o}')
    hist_path = os.path.join(OUT, 'history.json')
    theta = space.center()
    history = []
    if args.resume and os.path.exists(hist_path):
        history = json.load(open(hist_path))
        theta = np.array(history[-1]['theta'])
    # Adam-style moments for a stable step
    m_t = np.zeros_like(theta)
    v_t = np.zeros_like(theta)
    say(f'start: {len(space.keys)} params, {len(maps_all)} maps, opponents {opponents}, theta0={space.values(theta)}')
    for gen in range(len(history), len(history) + args.gens):
        maps = rng.sample(maps_all, min(args.maps_per_gen, len(maps_all)))
        eps = nrng.standard_normal((args.pop, len(theta)))
        cands = []
        names = []
        for i in range(args.pop):
            for sgn in (1, -1):
                z = theta + sgn * args.sigma * eps[i]
                name = f'_es{len(names)}'
                make_variant(name, space.values(z))
                cands.append(z)
                names.append(name)
        # The current mean is evaluated too (it is what we would ship).
        make_variant('_es_mean', space.values(theta))
        names.append('_es_mean')
        t0 = time.time()
        rewards, winrates = evaluate(names, opponents, maps, os.path.join(OUT, f'gen{gen}'), args.jobs)
        mean_reward, mean_wr = rewards[-1], winrates[-1]
        rs = np.array(rewards[:-1])
        shaped = centered_ranks(rs)
        grad = np.zeros_like(theta)
        for i in range(args.pop):
            grad += (shaped[2 * i] - shaped[2 * i + 1]) * eps[i]
        grad /= (2 * args.pop * args.sigma)
        b1, b2 = 0.9, 0.999
        m_t = b1 * m_t + (1 - b1) * grad
        v_t = b2 * v_t + (1 - b2) * grad * grad
        step = args.lr * (m_t / (1 - b1 ** (gen + 1))) / (np.sqrt(v_t / (1 - b2 ** (gen + 1))) + 1e-8) * args.sigma
        theta = np.clip(theta + step, -1, 1)
        best_i = int(np.argmax(rs))
        rec = {'gen': gen, 'maps': [os.path.basename(m) for m in maps], 'mean_reward': mean_reward, 'mean_winrate': mean_wr,
               'best_cand_reward': float(rs[best_i]), 'pop_rewards': [float(x) for x in rs], 'theta': theta.tolist(),
               'params': space.values(theta), 'secs': round(time.time() - t0)}
        history.append(rec)
        json.dump(history, open(hist_path, 'w'), indent=1)
        json.dump(space.values(theta), open(os.path.join(OUT, 'best_params.json'), 'w'), indent=1)
        say(f'gen {gen}: mean-policy reward {mean_reward:+.3f} winrate {mean_wr:.2f} | pop best {rs[best_i]:+.3f} worst {rs.min():+.3f} | {rec["secs"]}s')
        say(f'   theta -> {space.values(theta)}')
    for n in [f'_es{i}' for i in range(2 * args.pop)] + ['_es_mean']:
        shutil.rmtree(os.path.join(ROOT, 'bots', n), ignore_errors=True)
    say('done')


if __name__ == '__main__':
    main()
