#!/usr/bin/env python3
"""Large-machine RL trainer for bots/legend (Lightning AI A100 studio, or any many-core Linux box).

What it optimises: the bot's parameter vector (bots/legend/src/params.h), the only learnable part of a bot that
cannot be updated after submission and has no fuel for a network at play time. The simulator is the real engine.

Method (one generation):
  1. Test cases: every generation samples (map, opponent) cases from the groups of suite.json (the 17 official maps
     against the ladder-team archetypes _eA.._eD, against our frozen builds, farming pace against `idle`, held-out maps,
     fixed regression fixtures). Every case is played on both sides; all candidates of a generation play the same
     cases (common random numbers), so differences between candidates are not map-sample noise.
  2. Candidates: antithetic Gaussian perturbations of theta (evolution strategies, Salimans et al. 2017), the current
     mean, and two proposals from the surrogate model (below).
  3. Update: rank-shaped ES gradient with Adam; if a surrogate proposal beats the mean on the real games of this
     generation, theta also moves part of the way toward it.
  4. Surrogate (this is what the GPU is for): an ensemble of MLPs trained on every game played so far, predicting the
     shaped reward of (parameter vector, case). It averages over ALL cases, not only the sampled ones, so it
     (a) proposes candidates by gradient ascent inside a trust region around theta (mean and optimistic UCB), and
     (b) ranks every vector evaluated during training for the final tournament. Without torch it falls back to a
     ridge regression on the CPU. The game engine itself runs on the CPUs: more cores = more games per hour.
Final phase (time reserved from the budget): a tournament of the best vectors (surrogate ranking + defaults), each a
faithful submitted-style build (constexpr params), on a fixed large case set; the winner is best_params.json.

Training candidates are compiled with LEGEND_RUNTIME_PARAMS (params.h): the values live in a generated params_rt.cpp,
so a new candidate recompiles one file (~10 s) instead of the bot (~25 s). Slots persist between generations.

usage (normally through tools/rl/a100/run_a100.sh):
  python3 tools/rl/a100/es_a100.py --hours 2.5 [--jobs N] [--pop P] [--resume] [--selftest]
Outputs in tune_out/a100/: log.txt, history.json, dataset.npz, state.json, tournament.json, best_params.json,
best_meta.json, latest_params.json, surrogate_report.txt.
"""
import argparse, concurrent.futures as cf, glob, hashlib, json, math, os, random, re, shutil, subprocess, sys, threading, time

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'tune_out', 'a100')

try:
	import torch
except Exception:  # noqa: BLE001 (no torch: CPU ridge surrogate)
	torch = None


def sh(cmd, **kw):
	return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT, **kw)


LOG = None


def say(msg):
	line = f'[{time.strftime("%H:%M:%S")}] {msg}'
	print(line, flush=True)
	if LOG:
		LOG.write(line + '\n')
		LOG.flush()


# ------------------------------------------------------------------------------------------------ parameters

def read_params(path):
	"""Ordered (type, name, default string) of every Params field."""
	src = open(path).read()
	body = src[src.index('struct Params'):src.index('};', src.index('struct Params'))]
	return [(t, k, v.strip()) for t, k, v in re.findall(r'^\s*(int|float) (\w+) = ([^;]+);', body, re.M)]


class Space:
	"""Real vector z in [-1, 1]^D <-> parameter values within the bounds of the space file."""

	def __init__(self, spec, defaults):
		self.keys = [k for k in spec if k in defaults]
		self.skipped = [k for k in spec if k not in defaults]
		self.spec = spec
		self.defaults = defaults

	def _num(self, v):
		return float(str(v).rstrip('f'))

	def center(self):
		return np.array([self._to_z(self.spec[k], self._num(self.defaults[k])) for k in self.keys], dtype=float)

	def _to_z(self, s, v):
		lo, hi = s['lo'], s['hi']
		if s.get('log'):
			lo, hi, v = math.log(lo), math.log(hi), math.log(max(v, 1e-9))
		v = min(max(v, lo), hi)
		return (v - lo) / (hi - lo) * 2 - 1

	def values(self, z):
		out = {}
		for k, x in zip(self.keys, z):
			s = self.spec[k]
			lo, hi = s['lo'], s['hi']
			x = min(max(float(x), -1.0), 1.0)
			if s.get('log'):
				v = math.exp(math.log(lo) + (x + 1) / 2 * (math.log(hi) - math.log(lo)))
			else:
				v = lo + (x + 1) / 2 * (hi - lo)
			out[k] = str(int(round(v))) if s.get('int') else f'{v:.4f}f'
		return out


# ------------------------------------------------------------------------------------------------ bots

def src_hash():
	h = hashlib.sha1()
	for f in sorted(glob.glob(os.path.join(ROOT, 'bots/legend/src/*'))):
		h.update(os.path.basename(f).encode())
		h.update(open(f, 'rb').read())
	return h.hexdigest()[:12]


def ensure_slot(name, legend_hash):
	"""bots/NAME = bots/legend compiled with LEGEND_RUNTIME_PARAMS; recreated only when legend's sources change."""
	d = os.path.join(ROOT, 'bots', name)
	stamp = os.path.join(d, '.legend_hash')
	if os.path.exists(stamp) and open(stamp).read() == legend_hash:
		return
	shutil.rmtree(d, ignore_errors=True)
	shutil.copytree(os.path.join(ROOT, 'bots/legend/src'), os.path.join(d, 'src'))
	shutil.copy(os.path.join(ROOT, 'bots/legend/.gitignore'), d)
	hp = os.path.join(d, 'src', 'params.h')
	src = open(hp).read()
	open(hp, 'w').write('#define LEGEND_RUNTIME_PARAMS 1\n' + src)
	open(stamp, 'w').write(legend_hash)


def write_rt(name, values, fields):
	"""params_rt.cpp for a runtime-params slot (rewritten only when the values change, so ninja skips it)."""
	order = {k: i for i, (_, k, _) in enumerate(fields)}
	lines = [f'\tp.{k} = {v};' for k, v in sorted(values.items(), key=lambda kv: order[kv[0]])]
	src = ('// generated by tools/rl/a100/es_a100.py\n#include "params.h"\n#ifdef LEGEND_RUNTIME_PARAMS\n'
		   'constinit const Params P = [] {\n\tParams p{};\n' + '\n'.join(lines) + '\n\treturn p;\n}();\n#endif\n')
	path = os.path.join(ROOT, 'bots', name, 'src', 'params_rt.cpp')
	if not os.path.exists(path) or open(path).read() != src:
		open(path, 'w').write(src)


def make_static_variant(name, values):
	"""bots/NAME = bots/legend with these params.h defaults (a submitted-style build, as tools/variant.sh)."""
	d = os.path.join(ROOT, 'bots', name)
	shutil.rmtree(d, ignore_errors=True)
	shutil.copytree(os.path.join(ROOT, 'bots/legend/src'), os.path.join(d, 'src'))
	shutil.copy(os.path.join(ROOT, 'bots/legend/.gitignore'), d)
	hp = os.path.join(d, 'src', 'params.h')
	src = open(hp).read()
	for k, v in values.items():
		src, n = re.subn(rf'^(\s*\w+ {k} = )[^;]*;', lambda m: f'{m.group(1)}{v};', src, flags=re.M)
		if n != 1:
			raise RuntimeError(f'unknown param {k}')
	open(hp, 'w').write(src)


def build_all(names, workers):
	def one(n):
		r = sh(f'cambc build {n} --release')  # run-batch --release would otherwise build it itself
		if r.returncode != 0:
			raise RuntimeError(f'build {n} failed:\n{r.stdout[-3000:]}{r.stderr[-3000:]}')
	with cf.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
		list(ex.map(one, names))


# ------------------------------------------------------------------------------------------------ cases and rewards

class Suite:
	def __init__(self, path):
		spec = json.load(open(path))
		self.groups = []
		for g in spec['groups']:
			if 'fixed' in g:
				cases = [(os.path.join(ROOT, m), o) for m, o in g['fixed'] if os.path.exists(os.path.join(ROOT, m))]
			else:
				maps = sorted({m for p in g['maps'].split(',') for m in glob.glob(os.path.join(ROOT, p))
							   if not os.path.basename(m).startswith('zz_')})
				cases = [(m, o) for m in maps for o in g['opponents']]
			cases = [(m, o) for m, o in cases if os.path.isdir(os.path.join(ROOT, 'bots', o))]
			if not cases:
				continue
			self.groups.append({'name': g['name'], 'kind': g.get('kind', 'match'), 'weight': float(g.get('weight', 1)),
								'per_gen': int(g.get('per_gen', len(cases))), 'cases': cases, 'tournament': g.get('tournament', True)})
		self.pace_ref = spec.get('pace_ref', {})
		self.keys = []  # every (group, map, opponent, side): the surrogate's case universe
		for gi, g in enumerate(self.groups):
			for m, o in g['cases']:
				for side in 'AB':
					self.keys.append((gi, m, o, side))
		self.key_index = {k: i for i, k in enumerate(self.keys)}

	def opponents(self):
		return sorted({o for g in self.groups for _, o in g['cases']})

	def sample(self, rng, scale=1.0):
		out = []
		for gi, g in enumerate(self.groups):
			n = min(len(g['cases']), max(1, int(round(g['per_gen'] * scale))))
			out += [(gi, m, o) for m, o in rng.sample(g['cases'], n)]
		return out

	def tournament_cases(self):
		return [(gi, m, o) for gi, g in enumerate(self.groups) if g['tournament'] for m, o in g['cases']]


def load_stats(path, us):
	d = json.load(open(path))
	them = 'teamB' if us == 'teamA' else 'teamA'
	gems = {t['team']: int(t['submittedGems']) for t in d['teams']}
	deaths = {us: 0, them: 0}
	gold = {us: 0, them: 0}
	for c in d['champions']:
		deaths[c['team']] += int(c['metrics']['deaths'])
		gold[c['team']] += int(c['metrics'].get('earnedGold', 0))
	bag = 0
	for ev in d.get('events', []):
		if ev.get('kind') == 'gemLoss' and ev.get('owner', {}).get('team') == us:
			bag += sum(int(float(e['value'])) for e in ev['entries'])
	return {'outcome': d['match']['outcome'], 'rounds': int(d['match']['roundsCompleted']), 'us': us, 'them': them,
			'gems': gems, 'deaths': deaths, 'gold': gold, 'bag': bag, 'faults': d.get('diagnostics', {}).get('botFaults', {})}


def match_reward(s):
	"""+-1 win/loss, gem margin, gold margin (tiebreak 2 and the shop economy), deaths punished (and the bag carried
	into them), kills rewarded, fast wins rewarded."""
	us, them = s['us'], s['them']
	win, loss = s['outcome'] == us, s['outcome'] == them
	r = (1.0 if win else 0.0) - (1.0 if loss else 0.0)
	r += 0.6 * (s['gems'][us] - s['gems'][them]) / 1000.0
	r += 0.1 * max(-1.0, min(1.0, (s['gold'][us] - s['gold'][them]) / 5000.0))
	r -= 0.03 * s['deaths'][us]
	r += 0.015 * s['deaths'][them]
	r -= 0.02 * s['bag'] / 22.0
	if win:
		r += 0.15 * (2000 - s['rounds']) / 2000.0
	return r, win


def pace_reward(s, ref):
	"""Unopposed farming race vs `idle`: rounds to 1000 against a reference (the ladder winner's finish on this map,
	with us on the map: beating it unopposed is the minimum for a top team)."""
	us = s['us']
	rounds = s['rounds'] if s['outcome'] == us else 2000 + (1000 - s['gems'][us])
	return max(-1.5, min(1.0, (ref - rounds) / ref * 2.0)), s['outcome'] == us


def run_batch(cands, cases, suite, run_dir, jobs, release=True):
	"""Every candidate (bot name) plays every case on both sides. Returns per candidate: {key_index: reward}, wins,
	games, faults and the missing count."""
	os.makedirs(run_dir, exist_ok=True)
	manifest = os.path.join(run_dir, 'manifest.txt')
	rows = []
	with open(manifest, 'w') as f:
		for ci, c in enumerate(cands):
			for gi, m, o in cases:
				mn = os.path.splitext(os.path.basename(m))[0]
				for side in 'AB':
					a, b = (c, o) if side == 'A' else (o, c)
					st = os.path.join(run_dir, f'{ci}_{gi}_{mn}_{o}_{side}.json')
					rp = os.path.join(run_dir, f'{ci}_{gi}_{mn}_{o}_{side}.repl26a')
					f.write(f'{ROOT}/bots/{a} {ROOT}/bots/{b} {m} {rp} --statistics {st} --json\n')
					rows.append((ci, gi, m, o, side, st))
	t0 = time.time()
	res = sh(f'cambc run-batch {manifest} --jobs {jobs} --color never' + (' --release' if release else ''))
	secs = time.time() - t0
	out = [{} for _ in cands]
	wins = [0] * len(cands)
	games = [0] * len(cands)
	faults = [0] * len(cands)
	missing = 0
	for ci, gi, m, o, side, st in rows:
		key = suite.key_index[(gi, m, o, side)]
		us = 'teamA' if side == 'A' else 'teamB'
		try:
			s = load_stats(st, us)
		except (OSError, ValueError, KeyError, TypeError):
			out[ci][key] = -1.5
			games[ci] += 1
			missing += 1
			continue
		if suite.groups[gi]['kind'] == 'pace':
			mn = os.path.splitext(os.path.basename(m))[0]
			r, w = pace_reward(s, float(suite.pace_ref.get(mn, 600)))
		else:
			r, w = match_reward(s)
		out[ci][key] = r
		wins[ci] += w
		games[ci] += 1
		faults[ci] += sum(int(v) for v in s['faults'].values()) if isinstance(s['faults'], dict) else 0
	if missing or res.returncode != 0:
		kept = os.path.join(OUT, 'failed', os.path.basename(run_dir) + f'_{int(time.time())}')
		os.makedirs(os.path.dirname(kept), exist_ok=True)
		shutil.move(run_dir, kept)
		say(f'WARNING: {missing} of {len(rows)} games without statistics (run-batch rc {res.returncode}); kept in {kept}\n{res.stderr[-1500:]}')
	else:
		shutil.rmtree(run_dir, ignore_errors=True)
	return out, wins, games, faults, missing, secs, len(rows)


def aggregate(rew, suite):
	"""Weighted mean over groups of the mean reward of the group's played cases."""
	by = {}
	for key, r in rew.items():
		gi = suite.keys[key][0]
		by.setdefault(gi, []).append(r)
	tw = sum(suite.groups[gi]['weight'] for gi in by)
	return sum(suite.groups[gi]['weight'] * float(np.mean(v)) for gi, v in by.items()) / max(1e-9, tw)


# ------------------------------------------------------------------------------------------------ surrogate

class Surrogate:
	"""Predicts the shaped reward of (z, case key). Torch MLP ensemble (GPU if present) or numpy ridge regression."""

	def __init__(self, dim, nkeys, suite, members=5, hidden=256, seed=0):
		self.dim, self.nkeys, self.suite = dim, nkeys, suite
		self.members, self.hidden, self.seed = members, hidden, seed
		self.X, self.K, self.Y = [], [], []
		self.models = None
		self.ridge = None
		self.device = None
		# torch only on a GPU: on CPU cores the MLP ensemble would compete with the games (ridge instead)
		self.use_torch = torch is not None and torch.cuda.is_available() and not os.environ.get('A100_NO_TORCH')
		if self.use_torch:
			self.device = 'cuda'
		if torch is not None and os.environ.get('A100_FORCE_TORCH'):  # tests of the MLP path on a CPU
			self.use_torch, self.device = True, 'cpu'
		# pool weights: every key weighted by its group's weight / number of keys in the group
		w = np.zeros(nkeys)
		cnt = {}
		for gi, *_ in suite.keys:
			cnt[gi] = cnt.get(gi, 0) + 1
		for i, (gi, *_) in enumerate(suite.keys):
			w[i] = suite.groups[gi]['weight'] / cnt[gi]
		self.pool_w = w / w.sum()

	def add(self, z, rew):
		for key, r in rew.items():
			self.X.append(np.asarray(z, dtype=np.float32))
			self.K.append(key)
			self.Y.append(r)

	def size(self):
		return len(self.Y)

	def save(self, path):
		np.savez_compressed(path, X=np.array(self.X, dtype=np.float32), K=np.array(self.K, dtype=np.int32), Y=np.array(self.Y, dtype=np.float32))

	def load(self, path):
		d = np.load(path)
		if d['X'].shape[1] != self.dim:
			say(f'dataset dimension {d["X"].shape[1]} != space {self.dim}: not loaded')
			return
		self.X, self.K, self.Y = list(d['X']), list(d['K']), list(d['Y'])

	def ready(self):
		return self.models is not None or self.ridge is not None

	def fit(self, steps=2500, data=None):
		"""Fit on data (X, K, Y lists; default: everything so far). The new model replaces the old one only when done,
		so a fit can run in a thread while the games of the next generation are played."""
		Xl, Kl, Yl = data if data is not None else (self.X, self.K, self.Y)
		if len(Yl) < 50:
			return False
		X = np.array(Xl, dtype=np.float32)
		K = np.array(Kl, dtype=np.int64)
		Y = np.array(Yl, dtype=np.float32)
		if not self.use_torch:
			# ridge on [z, z^2, one-hot(key)]: per-case offsets plus a smooth parameter response
			F = np.concatenate([X, X * X, np.eye(self.nkeys, dtype=np.float32)[K]], axis=1)
			lam = 1.0
			A = F.T @ F + lam * np.eye(F.shape[1])
			self.ridge = np.linalg.solve(A, F.T @ Y)
			return True
		dev = self.device
		Xt = torch.tensor(X, device=dev)
		Kt = torch.tensor(K, device=dev)
		Yt = torch.tensor(Y, device=dev)
		models = []
		g = torch.Generator(device='cpu').manual_seed(self.seed)
		n = len(Y)
		for mi in range(self.members):
			net = Net(self.dim, self.nkeys, self.hidden).to(dev)
			opt = torch.optim.AdamW(net.parameters(), lr=2e-3, weight_decay=1e-4)
			idx = torch.randint(0, n, (n,), generator=g).to(dev)  # bootstrap per member
			bs = min(2048, n)
			for _ in range(steps):
				b = idx[torch.randint(0, n, (bs,), generator=g).to(dev)]
				loss = torch.nn.functional.smooth_l1_loss(net(Xt[b], Kt[b]), Yt[b])
				opt.zero_grad()
				loss.backward()
				opt.step()
			net.eval()
			models.append(net)
		self.models = models
		return True

	def pool(self, Z):
		"""Pool-wide predicted reward for each row of Z: (mean, std over ensemble members)."""
		Z = np.atleast_2d(np.asarray(Z, dtype=np.float32))
		if self.models is None and self.ridge is None:
			return np.zeros(len(Z)), np.ones(len(Z))
		if self.models is None:
			d = self.dim
			wz, wz2, wk = self.ridge[:d], self.ridge[d:2 * d], self.ridge[2 * d:]
			base = float(self.pool_w @ wk)
			return Z @ wz + (Z * Z) @ wz2 + base, np.zeros(len(Z))
		with torch.no_grad():
			zt = torch.tensor(Z, device=self.device)
			preds = torch.stack([m.pool(zt, torch.tensor(self.pool_w, dtype=torch.float32, device=self.device)) for m in self.models])
		return preds.mean(0).cpu().numpy(), preds.std(0).cpu().numpy()

	def propose(self, theta, radius, kappa, steps=300):
		"""Gradient ascent on mean + kappa * std of the pool prediction, inside an L-inf ball around theta."""
		if self.models is None:
			if self.ridge is None:
				return None
			d = self.dim
			wz, wz2 = self.ridge[:d], self.ridge[d:2 * d]
			z = np.array(theta, dtype=float)
			for _ in range(steps):
				z = z + 0.02 * (wz + 2 * wz2 * z)
				z = np.clip(np.clip(z, theta - radius, theta + radius), -1, 1)
			return z
		dev = self.device
		pw = torch.tensor(self.pool_w, dtype=torch.float32, device=dev)
		th = torch.tensor(np.asarray(theta, dtype=np.float32), device=dev)
		z = th.clone().requires_grad_(True)
		opt = torch.optim.Adam([z], lr=0.02)
		for _ in range(steps):
			preds = torch.stack([m.pool(z[None], pw)[0] for m in self.models])
			obj = preds.mean() + kappa * preds.std()
			opt.zero_grad()
			(-obj).backward()
			opt.step()
			with torch.no_grad():
				z.copy_(torch.clamp(torch.max(torch.min(z, th + radius), th - radius), -1, 1))
		return z.detach().cpu().numpy().astype(float)

	def report(self):
		"""Held-out check of the surrogate: fit on 80% of the games, R^2 and rank correlation on the rest."""
		n = len(self.Y)
		if n < 200:
			return 'too few games for a held-out check'
		rng = np.random.default_rng(1)
		perm = rng.permutation(n)
		cut = int(0.8 * n)
		full = (self.X, self.K, self.Y)
		tr, te = perm[:cut], perm[cut:]
		self.X, self.K, self.Y = [full[0][i] for i in tr], [full[1][i] for i in tr], [full[2][i] for i in tr]
		self.fit(steps=1500)
		Xte = np.array([full[0][i] for i in te], dtype=np.float32)
		Kte = np.array([full[1][i] for i in te])
		Yte = np.array([full[2][i] for i in te])
		pred = self.predict_cases(Xte, Kte)
		self.X, self.K, self.Y = list(full[0]), list(full[1]), list(full[2])
		ss = float(((Yte - Yte.mean()) ** 2).sum())
		r2 = 1 - float(((Yte - pred) ** 2).sum()) / max(1e-9, ss)
		rank = np.corrcoef(np.argsort(np.argsort(pred)), np.argsort(np.argsort(Yte)))[0, 1]
		return f'held-out games {len(te)}: R^2 {r2:.3f}, rank correlation {rank:.3f} (per-game rewards are noisy; the pool mean is what is used)'

	def predict_cases(self, X, K):
		if self.models is None:
			d = self.dim
			F = np.concatenate([X, X * X, np.eye(self.nkeys, dtype=np.float32)[K]], axis=1)
			return F @ self.ridge
		with torch.no_grad():
			xt = torch.tensor(X, device=self.device)
			kt = torch.tensor(np.asarray(K, dtype=np.int64), device=self.device)
			return torch.stack([m(xt, kt) for m in self.models]).mean(0).cpu().numpy()


if torch is not None:
	class Net(torch.nn.Module):
		def __init__(self, dim, nkeys, hidden):
			super().__init__()
			self.emb = torch.nn.Embedding(nkeys, 16)
			self.case_bias = torch.nn.Embedding(nkeys, 1)
			torch.nn.init.zeros_(self.case_bias.weight)
			self.body = torch.nn.Sequential(torch.nn.Linear(dim + 16, hidden), torch.nn.SiLU(), torch.nn.Linear(hidden, hidden),
											torch.nn.SiLU(), torch.nn.Linear(hidden, 1))

		def forward(self, z, k):
			return self.body(torch.cat([z, self.emb(k)], dim=1)).squeeze(1) + self.case_bias(k).squeeze(1)

		def pool(self, z, pw):
			"""z: (B, D) -> (B,) predicted reward averaged over every case key with weights pw."""
			nk = pw.shape[0]
			B = z.shape[0]
			keys = torch.arange(nk, device=z.device)
			zz = z[:, None, :].expand(B, nk, z.shape[1]).reshape(B * nk, -1)
			kk = keys[None, :].expand(B, nk).reshape(-1)
			return (self.forward(zz, kk).reshape(B, nk) * pw[None, :]).sum(1)


# ------------------------------------------------------------------------------------------------ main loop

def sur_gpu():
	return torch is not None and torch.cuda.is_available() and not os.environ.get('A100_NO_TORCH')


def centered_ranks(x):
	x = np.asarray(x)
	ranks = np.empty(len(x))
	ranks[x.argsort()] = np.arange(len(x))
	return ranks / max(1, len(x) - 1) - 0.5


def main():
	global LOG
	ap = argparse.ArgumentParser()
	ap.add_argument('--hours', type=float, default=2.5, help='total wall-clock budget, tournament included')
	ap.add_argument('--space', default=os.path.join(HERE, 'space.json'))
	ap.add_argument('--suite', default=os.path.join(HERE, 'suite.json'))
	ap.add_argument('--jobs', type=int, default=os.cpu_count() or 4)
	ap.add_argument('--pop', type=int, default=0, help='antithetic pairs per generation (0: from the core count)')
	ap.add_argument('--sigma', type=float, default=0.22)
	ap.add_argument('--lr', type=float, default=0.3)
	ap.add_argument('--case-scale', type=float, default=1.0, help='multiplies every group per_gen')
	ap.add_argument('--tournament-k', type=int, default=6, help='trained vectors in the final tournament (+ defaults)')
	ap.add_argument('--tournament-frac', type=float, default=0.2, help='share of the budget reserved for the tournament')
	ap.add_argument('--tournament-max-cases', type=int, default=0, help='cap on tournament cases (0: all; for tests)')
	ap.add_argument('--seed', type=int, default=11)
	ap.add_argument('--resume', action='store_true')
	ap.add_argument('--selftest', action='store_true', help='tiny run: 1 pair, 2 cases, no tournament')
	args = ap.parse_args()

	os.makedirs(OUT, exist_ok=True)
	LOG = open(os.path.join(OUT, 'log.txt'), 'a')
	t_start = time.time()
	budget = args.hours * 3600
	fields = read_params(os.path.join(ROOT, 'bots/legend/src/params.h'))
	defaults = {k: v for _, k, v in fields}
	space = Space(json.load(open(args.space)), defaults)
	if space.skipped:
		say(f'space params not in params.h (skipped): {space.skipped}')
	suite = Suite(args.suite)
	D = len(space.keys)
	rng = random.Random(args.seed)
	nrng = np.random.default_rng(args.seed)
	pop = args.pop or int(min(16, max(4, round(args.jobs / 2))))
	if args.selftest:
		pop = 1
	legend_hash = src_hash()
	commit = sh('git rev-parse --short HEAD').stdout.strip() or 'unknown'
	dev = f'MLP ensemble, torch {torch.__version__} on cuda: {torch.cuda.get_device_name(0)}' if sur_gpu() else 'ridge regression on CPU (no CUDA torch)'
	say(f'start: commit {commit}, legend {legend_hash}, {D} params, {len(suite.groups)} case groups ({len(suite.keys)} case keys), '
		f'opponents {suite.opponents()}, jobs {args.jobs}, pop {pop} pairs, surrogate {dev}, budget {args.hours} h')
	for g in suite.groups:
		say(f'   group {g["name"]}: {g["kind"]}, {len(g["cases"])} cases, {g["per_gen"]} per generation, weight {g["weight"]}')

	state_path = os.path.join(OUT, 'state.json')
	hist_path = os.path.join(OUT, 'history.json')
	data_path = os.path.join(OUT, 'dataset.npz')
	sur = Surrogate(D, len(suite.keys), suite, seed=args.seed)
	theta = space.center()
	m_t, v_t = np.zeros(D), np.zeros(D)
	history, evaluated = [], []  # evaluated: every z played as a mean / proposal, for the tournament
	gen0 = 0
	if args.resume and os.path.exists(state_path):
		st = json.load(open(state_path))
		if st.get('keys') == space.keys:
			theta, m_t, v_t = np.array(st['theta']), np.array(st['m']), np.array(st['v'])
			gen0, evaluated = st['gen'] + 1, st.get('evaluated', [])
			history = json.load(open(hist_path)) if os.path.exists(hist_path) else []
			if os.path.exists(data_path):
				sur.load(data_path)
			say(f'resumed at generation {gen0} with {sur.size()} games in the dataset')
		else:
			say('state.json has a different parameter list: starting fresh')
	slots = [f'_rt{i}' for i in range(2 * pop + 3)]
	for s in slots:
		ensure_slot(s, legend_hash)
	sec_game = None
	fit_thread = None
	gen = gen0
	while True:
		elapsed = time.time() - t_start
		reserve = 0 if args.selftest else args.tournament_frac * budget
		if gen > gen0 and sec_game:
			per_gen = (time.time() - t_start) / max(1, gen - gen0)
			if elapsed + per_gen + reserve > budget:
				break
		if args.selftest and gen > gen0:
			break
		cases = suite.sample(rng, args.case_scale) if not args.selftest else suite.sample(rng, 0.0)[:2]
		eps = nrng.standard_normal((pop, D))
		zs = []
		for i in range(pop):
			zs += [np.clip(theta + args.sigma * eps[i], -1, 1), np.clip(theta - args.sigma * eps[i], -1, 1)]
		zs.append(theta.copy())
		props = []
		if sur.ready():
			for kappa in (0.0, 1.0):
				z = sur.propose(theta, radius=2.0 * args.sigma, kappa=kappa)
				if z is not None:
					props.append(z)
		zs += props
		names = slots[:len(zs)]
		# the surrogate for the next generation trains on everything so far while this generation's games run
		# (a fit still running from the last generation keeps going; the proposals use the last finished model)
		if fit_thread is None or not fit_thread.is_alive():
			fit_thread = threading.Thread(target=sur.fit, kwargs={'data': (list(sur.X), list(sur.K), list(sur.Y))}, daemon=True)
			fit_thread.start()
		t0 = time.time()
		for n, z in zip(names, zs):
			write_rt(n, space.values(z), fields)
		build_all(names, max(1, args.jobs // 2))
		tb = time.time() - t0
		out, wins, games, faults, missing, secs, total = run_batch(names, cases, suite, os.path.join(OUT, f'gen{gen}'), args.jobs)
		sec_game = secs * args.jobs / max(1, total)
		for z, rew in zip(zs, out):
			sur.add(z, rew)
		agg = [aggregate(r, suite) for r in out]
		rs = np.array(agg[:2 * pop])
		mean_r = agg[2 * pop]
		prop_r = agg[2 * pop + 1:]
		shaped = centered_ranks(rs)
		grad = np.zeros(D)
		for i in range(pop):
			grad += (shaped[2 * i] - shaped[2 * i + 1]) * eps[i]
		grad /= (2 * pop * args.sigma)
		b1, b2 = 0.9, 0.999
		k = gen + 1
		m_t = b1 * m_t + (1 - b1) * grad
		v_t = b2 * v_t + (1 - b2) * grad * grad
		step = args.lr * (m_t / (1 - b1 ** k)) / (np.sqrt(v_t / (1 - b2 ** k)) + 1e-8) * args.sigma
		evaluated.append({'gen': gen, 'kind': 'mean', 'z': theta.tolist(), 'reward': mean_r})
		pulled = ''
		for j, (z, r) in enumerate(zip(props, prop_r)):
			evaluated.append({'gen': gen, 'kind': f'surrogate{j}', 'z': z.tolist(), 'reward': r})
		theta_new = np.clip(theta + step, -1, 1)
		if props:
			jb = int(np.argmax(prop_r))
			if prop_r[jb] > mean_r + 0.02:
				theta_new = np.clip(theta_new + 0.5 * (props[jb] - theta), -1, 1)
				pulled = f' | pulled toward surrogate{jb} ({prop_r[jb]:+.3f} > mean {mean_r:+.3f})'
		theta = theta_new
		rec = {'gen': gen, 'commit': commit, 'legend': legend_hash, 'cases': [[g, os.path.basename(m), o] for g, m, o in cases],
			   'mean_reward': mean_r, 'mean_winrate': wins[2 * pop] / max(1, games[2 * pop]), 'pop_rewards': rs.tolist(),
			   'surrogate_rewards': prop_r, 'theta': theta.tolist(), 'params': space.values(theta), 'faults': faults,
			   'missing': missing, 'build_secs': round(tb), 'game_secs': round(secs), 'dataset': sur.size()}
		history.append(rec)
		json.dump(history, open(hist_path, 'w'), indent=1)
		json.dump({'gen': gen, 'keys': space.keys, 'theta': theta.tolist(), 'm': m_t.tolist(), 'v': v_t.tolist(), 'evaluated': evaluated},
				  open(state_path, 'w'))
		json.dump(space.values(theta), open(os.path.join(OUT, 'latest_params.json'), 'w'), indent=1)
		sur.save(data_path)
		say(f'gen {gen}: mean {mean_r:+.3f} (win {rec["mean_winrate"]:.2f}) | pop best {rs.max():+.3f} worst {rs.min():+.3f}'
			f' | surrogate {", ".join(f"{x:+.3f}" for x in prop_r) or "-"}{pulled} | {len(cases)} cases, {total} games,'
			f' build {tb:.0f}s, games {secs:.0f}s ({sec_game:.2f} core-s/game), faults {sum(faults)}, missing {missing}')
		gen += 1

	if args.selftest:
		say('selftest done')
		return
	# ---------------------------------------------------------------------------------------- tournament
	if fit_thread is not None:
		fit_thread.join()
	say(f'training stopped after {gen - gen0} generations ({(time.time() - t_start) / 3600:.2f} h); fitting the surrogate on {sur.size()} games')
	sur.fit(steps=5000)
	open(os.path.join(OUT, 'surrogate_report.txt'), 'w').write(sur.report() + '\n')
	sur.fit(steps=5000)
	pool = [e for e in evaluated]
	if pool:
		pm, ps = sur.pool([e['z'] for e in pool])
		for e, a, b in zip(pool, pm, ps):
			e['pred'], e['pred_std'] = float(a), float(b)
		pool.sort(key=lambda e: e['pred'] - 0.5 * e['pred_std'], reverse=True)
	picks, seen = [], {json.dumps({k: defaults[k] for k in space.keys}, sort_keys=True), json.dumps(space.values(space.center()), sort_keys=True)}
	# entrants: the final theta (what ES converged to), the vector that beat its generation's population by the most
	# on real games, then the surrogate's ranking of everything evaluated
	rel = []
	for h in history:
		for e in evaluated:
			if e['gen'] == h['gen'] and e.get('reward') is not None:
				rel.append((e['reward'] - float(np.mean(h['pop_rewards'])), e))
	best_rel = [max(rel, key=lambda t: t[0])[1]] if rel else []
	for e in [{'gen': gen, 'kind': 'final_theta', 'z': theta.tolist(), 'reward': None}] + best_rel + pool:
		key = json.dumps(space.values(e['z']), sort_keys=True)
		if key in seen:
			continue
		seen.add(key)
		picks.append(e)
		if len(picks) >= args.tournament_k:
			break
	entrants = [('_tdef', {k: defaults[k] for k in space.keys}, {'kind': 'defaults'})]
	for i, e in enumerate(picks):
		entrants.append((f'_t{i}', space.values(e['z']), e))
	for n, vals, _ in entrants:
		make_static_variant(n, vals)
	build_all([n for n, _, _ in entrants], max(1, args.jobs // 2))
	tcases = suite.tournament_cases()
	if args.tournament_max_cases:
		tcases = rng.sample(tcases, min(len(tcases), args.tournament_max_cases))
	left = budget - (time.time() - t_start)
	est = len(entrants) * len(tcases) * 2 * (sec_game or 2.0) / args.jobs
	if est > left > 0:
		frac = max(0.25, left / est)
		tcases = rng.sample(tcases, max(1, int(len(tcases) * frac)))
		say(f'tournament trimmed to {len(tcases)} cases to fit the budget')
	say(f'tournament: {len(entrants)} entrants x {len(tcases)} cases x 2 sides ({len(entrants) * len(tcases) * 2} games)')
	out, wins, games, faults, missing, secs, total = run_batch([n for n, _, _ in entrants], tcases, suite, os.path.join(OUT, 'tournament'), args.jobs)
	table = []
	for (n, vals, e), rew, w, g, f in zip(entrants, out, wins, games, faults):
		by = {}
		for key, r in rew.items():
			by.setdefault(suite.groups[suite.keys[key][0]]['name'], []).append(r)
		table.append({'name': n, 'origin': {k: v for k, v in e.items() if k != 'z'}, 'reward': aggregate(rew, suite), 'winrate': w / max(1, g),
					  'faults': f, 'groups': {k: float(np.mean(v)) for k, v in by.items()}, 'params': vals})
	table.sort(key=lambda t: t['reward'], reverse=True)
	json.dump(table, open(os.path.join(OUT, 'tournament.json'), 'w'), indent=1)
	for t in table:
		say(f'   {t["name"]:6s} reward {t["reward"]:+.3f} win {t["winrate"]:.3f} faults {t["faults"]} origin {t["origin"]} '
			+ ' '.join(f'{k} {v:+.2f}' for k, v in t['groups'].items()))
	best = next((t for t in table if t['faults'] == 0), table[0])
	json.dump(best['params'], open(os.path.join(OUT, 'best_params.json'), 'w'), indent=1)
	json.dump({'name': best['name'], 'reward': best['reward'], 'winrate': best['winrate'], 'origin': best['origin'],
			   'beats_defaults_by': best['reward'] - next(t['reward'] for t in table if t['name'] == '_tdef'),
			   'commit': commit, 'legend': legend_hash, 'generations': gen - gen0, 'games': sur.size()},
			  open(os.path.join(OUT, 'best_meta.json'), 'w'), indent=1)
	say(f'best: {best["name"]} ({best["reward"]:+.3f}; defaults {next(t["reward"] for t in table if t["name"] == "_tdef"):+.3f}) -> best_params.json')
	for n, _, _ in entrants:
		if n != best['name']:
			shutil.rmtree(os.path.join(ROOT, 'bots', n), ignore_errors=True)
	say('done')


if __name__ == '__main__':
	main()
