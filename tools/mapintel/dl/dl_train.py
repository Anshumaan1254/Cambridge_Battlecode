#!/usr/bin/env python3
"""Step 7 (MAPAnalysis.md 5.7): deep models on the step-7 dataset (make_dataset.py), leave-maps-out, against the step-6 bar. LEARNED.
Needs numpy and torch only (no repository imports), so it runs on the laptop's GPU; run_dl.sh installs both and calls it.

    python dl_train.py [--data experiments/results/mapintel/dl_data] [--out experiments/results/mapintel/dl_model]
                       [--tasks t1a,t1b,t2,t3] [--seeds 3] [--device auto] [--hidden 8] [--quick] [--archive NAME]

Tasks (bars from meta.json "baselines", the step-6 models on the same samples and the same 5 archetype-stratified map folds):
  t1a opening       which groups a top team captures first (n = its bodies); top-n share. Bar: boosted forest (first_scores()).
                    mlp: small MLP on group_features + zfeat (exportable: dl_weights.h); graph: attention over the map's groups with
                    a learned distance bias (a GNN over the group graph; research); distil: the mlp trained on the graph's soft scores.
  t1b next target   the group a body captures next, given its previous capture, champion, round and the groups not respawning;
                    top-1 / top-3. Bar: boosted forest on group features + distance + round. Same three models.
  t2  values        win ~ side + our roster . v(map) - their roster . v(map), v(map) = w + mlp(zfeat) (exportable: draft values
                    per map); deepset: f(zfeat, roster) (research). Out-of-fold log loss. Bar: constant values (M1).
  t3  heat          where the top teams hit camps, hit champions, capture, die: a small U-Net from the map tensors, dihedral
                    augmentation, a distribution per channel; Pearson on valid tiles. Bar: blurred camp map. Research only (too
                    heavy for a bot); out-of-fold predictions saved in heat_pred.npz.
Protocol per model, seed and outer fold k: inner fit on folds != k, k+1 with validation on k+1 picks the epoch count; a fresh fit
(same seed) on folds != k for that many epochs is scored on fold k. Reported: mean and sd over seeds. The exported model is seed 0
fitted on all maps for the median epoch count; it is marked "export" only when its mean held-out score clears the bar by MARGIN.
Writes: report.md, results.json, dl_weights.json (for dl_export.py), heat_pred.npz, log.txt."""
import argparse, json, math, os, platform, sys, tarfile, time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as Fn

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
MARGIN = {"share": 0.01, "logloss": 0.003, "pearson": 0.02}
NEG = -1e9
LOG = []


def log(*a):
	s = " ".join(str(x) for x in a)
	print(s, flush=True)
	LOG.append(s)


# ---------------------------------------------------------------------------------------------------------------- shared pieces
class Std(nn.Module):
	"""(x - mean) / std with the training rows' statistics (stored with the weights: the C++ does the same)."""

	def __init__(self, mean, std):
		super().__init__()
		self.register_buffer("mean", torch.as_tensor(mean, dtype=torch.float32))
		self.register_buffer("std", torch.as_tensor(std, dtype=torch.float32))

	def forward(self, x):
		return (x - self.mean) / self.std


def stats(rows):
	mu = rows.mean(0)
	sd = rows.std(0)
	sd[sd < 1e-6] = 1.0
	return mu, sd


class MLP(nn.Module):
	"""Exportable: Std, then Linear / ReLU layers (no ReLU after the last); dl_ref.mlp() and dl_weights.h compute the same."""

	def __init__(self, mean, std, sizes, zero_last=False):
		super().__init__()
		self.std = Std(mean, std)
		self.lin = nn.ModuleList(nn.Linear(a, b) for a, b in zip(sizes[:-1], sizes[1:]))
		if zero_last:
			nn.init.zeros_(self.lin[-1].weight)
			nn.init.zeros_(self.lin[-1].bias)

	def forward(self, x):
		h = self.std(x)
		for i, l in enumerate(self.lin):
			h = l(h)
			if i < len(self.lin) - 1:
				h = torch.relu(h)
		return h

	def export(self):
		return {"mean": [float(v) for v in self.std.mean.cpu()], "std": [float(v) for v in self.std.std.cpu()],
				"layers": [[l.weight.detach().cpu().double().tolist(), l.bias.detach().cpu().double().tolist()] for l in self.lin]}


class AttnLayer(nn.Module):
	"""Self-attention over the map's groups with a learned per-head penalty on the distance between group boxes, then a feed-forward."""

	def __init__(self, d, heads):
		super().__init__()
		self.h, self.dh = heads, d // heads
		self.qkv = nn.Linear(d, 3 * d)
		self.proj = nn.Linear(d, d)
		self.alpha = nn.Parameter(torch.zeros(heads))
		self.n1, self.n2 = nn.LayerNorm(d), nn.LayerNorm(d)
		self.ff = nn.Sequential(nn.Linear(d, 2 * d), nn.ReLU(), nn.Linear(2 * d, d))

	def forward(self, x, mask, dist):
		B, G, D = x.shape
		q, k, v = self.qkv(x).view(B, G, 3, self.h, self.dh).permute(2, 0, 3, 1, 4)
		a = q @ k.transpose(-1, -2) / math.sqrt(self.dh) - Fn.softplus(self.alpha)[None, :, None, None] * 10.0 * dist[:, None]
		a = a.masked_fill(mask[:, None, None, :] < 0.5, NEG).softmax(-1)
		o = (a @ v).transpose(1, 2).reshape(B, G, D)
		x = self.n1(x + self.proj(o))
		return self.n2(x + self.ff(x))


class GroupGraph(nn.Module):
	"""Research model: per-group embedding, attention layers over the group graph, a score per group."""

	def __init__(self, mean, std, nin, d=32, heads=4, layers=2):
		super().__init__()
		self.std = Std(mean, std)
		self.inp = nn.Sequential(nn.Linear(nin, d), nn.ReLU(), nn.Linear(d, d))
		self.layers = nn.ModuleList(AttnLayer(d, heads) for _ in range(layers))
		self.out = nn.Sequential(nn.Linear(d, d), nn.ReLU(), nn.Linear(d, 1))

	def forward(self, x, mask, dist):
		h = self.inp(self.std(x))
		for l in self.layers:
			h = l(h, mask, dist)
		return self.out(h).squeeze(-1)


def set_seed(s):
	torch.manual_seed(s)
	np.random.seed(s)


def fit(model, step, epochs, lr, wd, every=0, val=None):
	"""AdamW; step(model, epoch) yields losses (one per batch); val(model) -> score (higher better). Returns (best score, its epoch)."""
	opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=wd)
	best = (-math.inf, epochs)
	for ep in range(1, epochs + 1):
		model.train()
		for loss in step(model, ep):
			opt.zero_grad()
			loss.backward()
			opt.step()
			opt.zero_grad()
		if val is not None and (ep % every == 0 or ep == epochs):
			model.eval()
			with torch.no_grad():
				v = val(model)
			if v > best[0] + 1e-9:
				best = (v, ep)
	return best


def cv(name, fold_of, make, train_fn, score_fn, epochs, every, seeds, extra=None):
	"""The protocol of the docstring. fold_of: fold of every sample; make(seed, sel) -> model; train_fn(model, sel, epochs, val_sel)
	-> (best, epoch); score_fn(model, sel) -> dict of metrics (the first key is the selection metric). Returns per-seed metrics and
	the chosen epoch counts."""
	per_seed, epochs_used = [], []
	for s in seeds:
		agg = {}
		for k in range(5):
			te = fold_of == k
			va = fold_of == (k + 1) % 5
			tr_in = ~te & ~va
			tr = ~te
			if te.sum() == 0:
				continue
			set_seed(1000 * s + k)
			m = make(s, tr_in)
			_, e = train_fn(m, tr_in, epochs, va)
			epochs_used.append(e)
			set_seed(1000 * s + k)
			m = make(s, tr)
			train_fn(m, tr, e, None)
			m.eval()
			with torch.no_grad():
				r = score_fn(m, te)
			for key, (num, den) in r.items():
				a = agg.setdefault(key, [0.0, 0.0])
				a[0] += num
				a[1] += den
			if extra:
				with torch.no_grad():
					extra(m, te, s)
		per_seed.append({key: n / d for key, (n, d) in agg.items()})
		log(f"  {name} seed {s}: " + ", ".join(f"{k} {v:.4f}" for k, v in per_seed[-1].items()))
	keys = per_seed[0].keys()
	return {"mean": {k: float(np.mean([p[k] for p in per_seed])) for k in keys}, "sd": {k: float(np.std([p[k] for p in per_seed])) for k in keys},
			"per_seed": per_seed, "epochs": int(np.median(epochs_used))}


# ---------------------------------------------------------------------------------------------------------------- T1: group choice
class GroupTask:
	"""T1a and T1b share the per-group inputs: rows [B, 64, F], mask [B, 64], distances [B, 64, 64], target distribution [B, 64]."""

	def __init__(self, D, dev, kind):
		self.dev, self.kind = dev, kind
		self.gf = torch.tensor(D["gfeat"], device=dev)
		self.gm = torch.tensor(D["gmask"], device=dev)
		self.gd = torch.tensor(D["gdist"], device=dev)
		self.z = torch.tensor(D["z"], device=dev)
		fold = D["fold"]
		if kind == "t1a":
			self.mt = torch.tensor(D["t1a_mt"], device=dev)
			self.n = torch.tensor(D["t1a_n"], device=dev)
			self.y = torch.tensor(D["t1a_first"], device=dev, dtype=torch.float32)
			self.fold = fold[D["t1a_mt"] // 2]
		else:
			self.mt = torch.tensor(D["t1b_mt"], device=dev)
			self.prev = torch.tensor(D["t1b_prev"], device=dev)
			self.ch = torch.tensor(D["t1b_champ"], device=dev)
			self.rnd = torch.tensor(D["t1b_round"], device=dev)
			self.tgt = torch.tensor(D["t1b_target"], device=dev)
			self.av = torch.tensor(D["t1b_avail"], device=dev, dtype=torch.float32)
			self.fold = fold[D["t1b_mt"] // 2]
		self.N = len(self.fold)

	def batch(self, idx, research=False):
		"""(x, mask, dist, target) for the samples idx; x = the exportable layout of dl_ref.py (+ an is-previous flag for research)."""
		mt = self.mt[idx]
		gf, z = self.gf[mt], self.z[mt][:, None, :].expand(-1, 64, -1)
		if self.kind == "t1a":
			x = torch.cat([gf, z], -1)
			mask = self.gm[mt]
			y = self.y[idx] / self.n[idx][:, None]
		else:
			B = len(idx)
			dprev = self.gd[mt, self.prev[idx]]
			oh = Fn.one_hot(self.ch[idx], 13).float()[:, None, :].expand(-1, 64, -1)
			parts = [gf, dprev[..., None], self.rnd[idx][:, None, None].expand(-1, 64, 1), oh, z]
			if research:
				isp = Fn.one_hot(self.prev[idx], 64).float()[..., None]
				parts.append(isp)
			x = torch.cat(parts, -1)
			mask = self.av[idx]
			y = Fn.one_hot(self.tgt[idx], 64).float()
		return x, mask, self.gd[mt], y

	def rows(self, sel, research=False):
		idx = torch.tensor(np.nonzero(sel)[0], device=self.dev)
		xs = []
		for i in range(0, len(idx), 4096):
			x, m, _, _ = self.batch(idx[i:i + 4096], research)
			xs.append(x[m > 0.5])
		r = torch.cat(xs)
		return stats(r)

	def scores(self, model, x, mask, dist, research):
		s = model(x, mask, dist) if research else model(x).squeeze(-1)
		return s.masked_fill(mask < 0.5, NEG)

	def loss(self, model, idx, research, teacher=None, alpha=0.5):
		x, mask, dist, y = self.batch(idx, research)
		lp = self.scores(model, x, mask, dist, research).log_softmax(-1)
		l = -(y * lp).sum(-1).mean()
		if teacher is not None:
			with torch.no_grad():
				xt, _, _, _ = self.batch(idx, True)
				pt = self.scores(teacher, xt, mask, dist, True).softmax(-1)
			l = alpha * l + (1 - alpha) * -(pt * lp).sum(-1).mean()
		return l

	def metric(self, model, sel, research):
		idx = torch.tensor(np.nonzero(sel)[0], device=self.dev)
		out = {}
		for i in range(0, len(idx), 2048):
			b = idx[i:i + 2048]
			x, mask, dist, y = self.batch(b, research)
			s = self.scores(model, x, mask, dist, research)
			# ties by group index, as the baselines (np.lexsort((gs, -p)))
			order = torch.argsort(-s, dim=-1, stable=True)
			if self.kind == "t1a":
				n = self.n[b]
				hit = torch.gather(y * n[:, None], 1, order)
				keep = torch.arange(64, device=self.dev)[None] < n[:, None]
				v = ((hit * keep).sum(-1) / n).sum().item()
				out.setdefault("share", [0.0, 0.0])
				out["share"][0] += v
				out["share"][1] += len(b)
			else:
				t = self.tgt[b][:, None]
				out.setdefault("top1", [0.0, 0.0])
				out.setdefault("top3", [0.0, 0.0])
				out["top1"][0] += (order[:, :1] == t).any(-1).float().sum().item()
				out["top3"][0] += (order[:, :3] == t).any(-1).float().sum().item()
				out["top1"][1] += len(b)
				out["top3"][1] += len(b)
		return out


def run_group(D, dev, kind, args, base):
	T = GroupTask(D, dev, kind)
	q = args.quick
	if kind == "t1a":
		ep_mlp, ep_g, every, bs = (20, 10, 5, 0) if q else (400, 200, 10, 0)
	else:
		ep_mlp, ep_g, every, bs = (2, 1, 1, 1024) if q else (30, 20, 2, 512)
	seeds = list(range(args.seeds))
	nin = T.batch(torch.tensor([0], device=dev))[0].shape[-1]

	def batches(sel, ep):
		idx = np.nonzero(sel)[0]
		if bs == 0:
			yield torch.tensor(idx, device=dev)
			return
		rng = np.random.default_rng(ep)
		rng.shuffle(idx)
		for i in range(0, len(idx), bs):
			yield torch.tensor(idx[i:i + bs], device=dev)

	def make_mlp(s, sel):
		mu, sd = T.rows(sel)
		return MLP(mu, sd, [nin, args.hidden, 1]).to(dev)

	def make_graph(s, sel):
		mu, sd = T.rows(sel, True)
		return GroupGraph(mu, sd, len(mu)).to(dev)

	key = "share" if kind == "t1a" else "top1"

	def trainer(research, teacher_of=None):
		def tr(model, sel, epochs, val_sel):
			teacher = teacher_of(sel) if teacher_of else None
			step = lambda m, ep: (T.loss(m, b, research, teacher) for b in batches(sel, ep))
			val = (lambda m: T.metric(m, val_sel, research)[key][0] / max(1, val_sel.sum())) if val_sel is not None else None
			return fit(model, step, epochs, 3e-3 if research is False else 1e-3, 1e-4, every, val)
		return tr

	res = {}
	log(f"{kind}: {T.N} samples, inputs {nin}, bar {base}")
	res["mlp"] = cv(f"{kind} mlp", T.fold, make_mlp, trainer(False), lambda m, sel: T.metric(m, sel, False), ep_mlp, every, seeds)
	res["graph"] = cv(f"{kind} graph", T.fold, make_graph, trainer(True), lambda m, sel: T.metric(m, sel, True), ep_g, every, seeds)
	# distillation: the teacher is a graph model fitted on the same training maps for the graph's median epoch count
	cache = {}

	def teacher_of(sel):
		k = sel.tobytes()
		if k not in cache:
			set_seed(7)
			t = make_graph(0, sel)
			trainer(True)(t, sel, res["graph"]["epochs"], None)
			t.eval()
			cache[k] = t
		return cache[k]

	res["distil"] = cv(f"{kind} distil", T.fold, make_mlp, trainer(False, teacher_of), lambda m, sel: T.metric(m, sel, False), ep_mlp, every, seeds[:1] if q else seeds)
	# the exported model: the better of mlp / distil, seed 0, all maps
	pick = "distil" if res["distil"]["mean"][key] > res["mlp"]["mean"][key] else "mlp"
	allm = np.ones(T.N, bool)
	set_seed(0)
	m = make_mlp(0, allm)
	trainer(False, teacher_of if pick == "distil" else None)(m, allm, res[pick]["epochs"], None)
	ex = m.export()
	bar = base[0] if kind == "t1b" else base
	ok = res[pick]["mean"][key] > bar + MARGIN["share"]
	if kind == "t1b":
		ok = ok and res[pick]["mean"]["top3"] >= base[1]
	ex.update({"export": bool(ok), "from": pick, "cv": res[pick]["mean"], "bar": base,
			   "note": f"{pick} MLP {nin}-{args.hidden}-1, held-out {key} {res[pick]['mean'][key]:.4f} vs bar {bar:.4f} (LEARNED, current-patch ladder)"})
	return res, ex


# ---------------------------------------------------------------------------------------------------------------- T2: champion values
class Values(nn.Module):
	"""logit = b + a side + us . v(z_us) - them . v(z_them), v(z) = w + mlp(z): the exportable draft values per map."""

	def __init__(self, mean, std, hidden, use_mlp=True):
		super().__init__()
		self.use_mlp = use_mlp
		self.v = MLP(mean, std, [19, hidden, 12], zero_last=True)
		self.w = nn.Parameter(torch.zeros(12))
		self.a = nn.Parameter(torch.zeros(1))
		self.b = nn.Parameter(torch.zeros(1))

	def forward(self, side, zu, zt, us, them):
		if not self.use_mlp:
			return self.b + self.a * side + ((us - them) * self.w).sum(-1)
		return self.b + self.a * side + (us * (self.w + self.v(zu))).sum(-1) - (them * (self.w + self.v(zt))).sum(-1)


class DeepSet(nn.Module):
	"""Research: f(z, roster) by an MLP over [z, multi-hot roster]: champion interactions and map dependence together."""

	def __init__(self, mean, std, d=32):
		super().__init__()
		self.std = Std(mean, std)
		self.f = nn.Sequential(nn.Linear(19 + 12, d), nn.ReLU(), nn.Linear(d, d), nn.ReLU(), nn.Linear(d, 1))
		self.a = nn.Parameter(torch.zeros(1))
		self.b = nn.Parameter(torch.zeros(1))

	def forward(self, side, zu, zt, us, them):
		f = lambda z, r: self.f(torch.cat([self.std(z), r], -1)).squeeze(-1)
		return self.b + self.a * side + f(zu, us) - f(zt, them)


def run_values(D, dev, args, base):
	mp = D["t2_map"]
	side = torch.tensor(D["t2_side"], device=dev)
	team = (D["t2_side"] < 0).astype(np.int64)
	z = torch.tensor(D["z"], device=dev)
	zu = z[torch.tensor(2 * mp + team, device=dev)]
	zt = z[torch.tensor(2 * mp + 1 - team, device=dev)]
	us = torch.tensor(D["t2_us"], device=dev, dtype=torch.float32)
	them = torch.tensor(D["t2_them"], device=dev, dtype=torch.float32)
	win = torch.tensor(D["t2_win"], device=dev)
	fold = D["fold"][mp]
	q = args.quick
	ep, every = (30, 10) if q else (1500, 25)
	seeds = list(range(args.seeds))
	log(f"t2: {len(win)} games, bar {base}")

	def nll(m, sel):
		i = torch.tensor(np.nonzero(sel)[0], device=dev)
		return Fn.binary_cross_entropy_with_logits(m(side[i], zu[i], zt[i], us[i], them[i]), win[i], reduction="sum")

	def trainer(wd):
		def tr(model, sel, epochs, val_sel):
			n = max(1, sel.sum())
			step = lambda m, e: iter([nll(m, sel) / n])
			val = (lambda m: -nll(m, val_sel).item() / max(1, val_sel.sum())) if val_sel is not None else None
			return fit(model, step, epochs, 1e-2, wd, every, val)
		return tr

	def zstats(sel):
		return stats(torch.cat([zu[torch.tensor(np.nonzero(sel)[0], device=dev)], zt[torch.tensor(np.nonzero(sel)[0], device=dev)]]))

	score = lambda m, sel: {"logloss_neg": [-nll(m, sel).item(), float(sel.sum())]}
	res = {}
	for name, make, wd in (("const", lambda s, sel: Values(*zstats(sel), 1, use_mlp=False).to(dev), 0.0),
						   ("values", lambda s, sel: Values(*zstats(sel), args.hidden).to(dev), 1e-2),
						   ("deepset", lambda s, sel: DeepSet(*zstats(sel)).to(dev), 1e-2)):
		r = cv(f"t2 {name}", fold, make, trainer(wd), score, ep, every, seeds)
		r["mean"] = {"logloss": -r["mean"]["logloss_neg"]}
		res[name] = r
		log(f"  t2 {name}: held-out log loss {r['mean']['logloss']:.4f}")
	allm = np.ones(len(win), bool)
	set_seed(0)
	m = Values(*zstats(allm), args.hidden).to(dev)
	trainer(1e-2)(m, allm, res["values"]["epochs"], None)
	ex = m.v.export()
	ex["w"] = [float(v) for v in m.w.detach().cpu().double()]
	ex["side"] = float(m.a.item())
	ok = res["values"]["mean"]["logloss"] < base - MARGIN["logloss"]
	ex.update({"export": bool(ok), "from": "values", "cv": res["values"]["mean"], "bar": base,
			   "note": f"values w + MLP 19-{args.hidden}-12, held-out log loss {res['values']['mean']['logloss']:.4f} vs bar {base:.4f} (SIMULATED v10 roster battery)"})
	return res, ex


# ---------------------------------------------------------------------------------------------------------------- T3: heat maps
def conv(a, b):
	return nn.Sequential(nn.Conv2d(a, b, 3, padding=1), nn.ReLU(), nn.Conv2d(b, b, 3, padding=1), nn.ReLU())


class UNet(nn.Module):
	def __init__(self, cin, cout, w):
		super().__init__()
		self.e1, self.e2, self.e3 = conv(cin, w), conv(w, 2 * w), conv(2 * w, 4 * w)
		self.d2, self.d1 = conv(6 * w, 2 * w), conv(3 * w, w)
		self.out = nn.Conv2d(w, cout, 1)

	def forward(self, x):
		a = self.e1(x)
		b = self.e2(Fn.max_pool2d(a, 2))
		c = self.e3(Fn.max_pool2d(b, 2))
		b = self.d2(torch.cat([b, Fn.interpolate(c, size=b.shape[-2:])], 1))
		a = self.d1(torch.cat([a, Fn.interpolate(b, size=a.shape[-2:])], 1))
		return self.out(a)


def dihedral(x, k, inverse=False):
	if not inverse:
		if k >= 4:
			x = x.flip(-1)
		return torch.rot90(x, k % 4, (-2, -1))
	x = torch.rot90(x, -(k % 4), (-2, -1))
	return x.flip(-1) if k >= 4 else x


def run_heat(D, dev, args, base):
	keep = D["heat_games"] > 0
	idx_all = np.nonzero(keep)[0]
	grid = torch.tensor(D["grid"][idx_all], device=dev)
	heat = torch.tensor(D["heat"][idx_all], device=dev)
	valid = grid[:, :1] > 0.5
	tot = (heat * valid).sum((-2, -1), keepdim=True)
	has = (tot > 0).float()
	p = heat * valid / tot.clamp_min(1e-12)
	fold = D["fold"][idx_all // 2]
	q = args.quick
	ep, every, w, bs = (3, 1, 8, 8) if q else (150, 10, 16, 8)
	seeds = list(range(min(args.seeds, 2) if not q else 1))
	log(f"t3: {len(idx_all)} map-teams, bar {base}")

	def logq(m, x, v):
		return m(x).masked_fill(~v, NEG).flatten(-2).log_softmax(-1).view(x.shape[0], -1, x.shape[-2], x.shape[-1])

	def predict(m, i):
		"""Mean over the 8 dihedral transforms of the predicted distributions."""
		acc = 0
		for k in range(8):
			x, v = dihedral(grid[i], k), dihedral(valid[i], k)
			acc = acc + dihedral(logq(m, x, v).exp(), k, inverse=True)
		return acc / 8

	def step(m, sel, e):
		idx = np.nonzero(sel)[0]
		rng = np.random.default_rng(e)
		rng.shuffle(idx)
		for j in range(0, len(idx), bs):
			i = torch.tensor(idx[j:j + bs], device=dev)
			k = int(rng.integers(8))
			x, v, t = dihedral(grid[i], k), dihedral(valid[i], k), dihedral(p[i], k)
			lq = logq(m, x, v)
			yield -((t * lq.masked_fill(~v, 0)).sum((-2, -1)) * has[i, :, 0, 0]).sum() / has[i].sum().clamp_min(1)

	def pearson(m, sel):
		num, den = 0.0, 0
		for j in np.nonzero(sel)[0]:
			i = torch.tensor([j], device=dev)
			pr = predict(m, i)[0]
			vm = valid[j, 0]
			for ch in range(4):
				a, b = pr[ch][vm], heat[j, ch][vm]
				if a.std() > 0 and b.std() > 0:
					num += torch.corrcoef(torch.stack([a, b]))[0, 1].item()
					den += 1
		return {"pearson": [num, den]}

	def tr(model, sel, epochs, val_sel):
		def val(m):
			n, d = pearson(m, val_sel)["pearson"]
			return n / max(1, d)
		if val_sel is None:
			val = None
		return fit(model, lambda m, e: step(m, sel, e), epochs, 1e-3, 1e-4, every, val)

	oof = np.zeros(heat.shape, np.float32)

	def extra(m, te, s):
		if s == 0:
			for j in np.nonzero(te)[0]:
				oof[j] = predict(m, torch.tensor([j], device=dev))[0].cpu().numpy()

	r = cv("t3 unet", fold, lambda s, sel: UNet(grid.shape[1], 4, w).to(dev), tr, pearson, ep, every, seeds, extra)
	log(f"  t3 unet: held-out Pearson {r['mean']['pearson']:.4f} vs bar {base:.4f}")
	full = np.zeros((D["heat"].shape[0],) + oof.shape[1:], np.float16)
	full[idx_all] = oof
	return {"unet": r}, {"pred": full, "maps": D["maps"]}


# ---------------------------------------------------------------------------------------------------------------- main
def report(res, base, args, dev, secs):
	L = ["# Step 7: deep models vs the step-6 bar (leave-maps-out, 5 archetype-stratified folds)\n",
		 f"Device {dev}, torch {torch.__version__}, seeds {args.seeds}, hidden {args.hidden}{', QUICK (function test only)' if args.quick else ''}; "
		 f"{secs / 60:.1f} minutes. Held-out score: mean (sd) over seeds. Export needs the bar + {MARGIN['share']} (share / top-1), "
		 f"- {MARGIN['logloss']} (log loss).\n"]

	def row(task, name, r, keys):
		return f"| {task} | {name} | " + " | ".join(f"{r['mean'][k]:.4f} ({r['sd'].get(k, 0):.4f})" if k in r["sd"] else f"{r['mean'][k]:.4f}" for k in keys) + f" | {r['epochs']} |"

	if "t1a" in res:
		L += ["## T1a opening (top-n share)\n", "| task | model | share | epochs |", "|---|---|---|---|",
			  f"| t1a | bar: nearest | {base['t1a_topn_share']['nearest']:.4f} | |", f"| t1a | bar: boosted forest (first_scores) | {base['t1a_topn_share']['forest']:.4f} | |"]
		L += [row("t1a", k, v, ["share"]) for k, v in res["t1a"][0].items()] + [""]
	if "t1b" in res:
		b = base["t1b_top1_top3"]
		L += ["## T1b next target (top-1, top-3)\n", "| task | model | top-1 | top-3 | epochs |", "|---|---|---|---|---|",
			  f"| t1b | bar: nearest to previous | {b['nearest_prev'][0]:.4f} | {b['nearest_prev'][1]:.4f} | |",
			  f"| t1b | bar: boosted forest | {b['forest'][0]:.4f} | {b['forest'][1]:.4f} | |"]
		L += [row("t1b", k, v, ["top1", "top3"]) for k, v in res["t1b"][0].items()] + [""]
	if "t2" in res:
		b = base["t2_logloss"]
		L += ["## T2 champion values (out-of-fold log loss, lower is better)\n", "| task | model | log loss | epochs |", "|---|---|---|---|",
			  f"| t2 | bar: side only | {b['side_only']:.4f} | |", f"| t2 | bar: constant values (M1) | {b['M1_constant_values']:.4f} | |"]
		L += [f"| t2 | {k} | {v['mean']['logloss']:.4f} | {v['epochs']} |" for k, v in res["t2"][0].items()] + [""]
	if "t3" in res:
		L += ["## T3 heat (Pearson on valid tiles, per channel)\n", "| task | model | Pearson | epochs |", "|---|---|---|---|",
			  f"| t3 | bar: blurred camps | {base['t3_camp_blur_pearson']:.4f} | |"]
		L += [row("t3", k, v, ["pearson"]) for k, v in res["t3"][0].items()] + [""]
	L += ["## Exported (dl_weights.json -> dl_export.py -> dl_weights.h)\n"]
	for t, (_, ex) in res.items():
		if isinstance(ex, dict) and "export" in ex:
			L.append(f"- {t}: {'EXPORT' if ex['export'] else 'not exported'}: {ex['note']}")
	return "\n".join(L) + "\n"


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--data", default=os.path.join(ROOT, "experiments/results/mapintel/dl_data"))
	ap.add_argument("--out", default=os.path.join(ROOT, "experiments/results/mapintel/dl_model"))
	ap.add_argument("--tasks", default="t1a,t1b,t2,t3")
	ap.add_argument("--seeds", type=int, default=3)
	ap.add_argument("--device", default="auto")
	ap.add_argument("--hidden", type=int, default=8, help="hidden units of the exportable MLPs (fuel in the bot grows with it)")
	ap.add_argument("--quick", action="store_true", help="a few epochs, one seed: a function test, not a result")
	ap.add_argument("--archive", default="", help="write this .tar.gz (results only) and split it into 20 MB parts when larger")
	a = ap.parse_args()
	if a.quick:
		a.seeds = 1
	dev = torch.device("cuda" if a.device == "auto" and torch.cuda.is_available() else ("cpu" if a.device == "auto" else a.device))
	if dev.type == "cuda":
		if not torch.cuda.is_available():
			sys.exit(f"ERROR: --device cuda, but this torch ({torch.__version__}, CUDA {torch.version.cuda}) sees no CUDA GPU: run it through run_dl.sh")
		torch.backends.cudnn.benchmark = True
		torch.set_float32_matmul_precision("high")
	torch.set_num_threads(max(1, os.cpu_count() or 1))
	os.makedirs(a.out, exist_ok=True)
	t0 = time.time()
	D = dict(np.load(os.path.join(a.data, "dataset.npz")))
	meta = json.load(open(os.path.join(a.data, "meta.json")))
	base = meta["baselines"]
	gpu = f"{torch.cuda.get_device_name(0)}, {torch.cuda.get_device_properties(0).total_memory / 2 ** 30:.1f} GB" if dev.type == "cuda" else ""
	log(f"device {dev} ({gpu or platform.processor() or 'cpu'}), torch {torch.__version__}, "
		f"python {platform.python_version()}, {platform.system()}; sizes {meta['sizes']}")
	tasks = [t.strip() for t in a.tasks.split(",") if t.strip()]
	res, weights = {}, {"origin": "LEARNED / SIMULATED, tools/mapintel/dl/dl_train.py", "quick": a.quick, "models": {}}
	for t in tasks:
		ts = time.time()
		if t == "t1a":
			res[t] = run_group(D, dev, "t1a", a, base["t1a_topn_share"]["forest"])
			weights["models"]["opening"] = res[t][1]
		elif t == "t1b":
			res[t] = run_group(D, dev, "t1b", a, base["t1b_top1_top3"]["forest"])
			weights["models"]["next"] = res[t][1]
		elif t == "t2":
			res[t] = run_values(D, dev, a, base["t2_logloss"]["M1_constant_values"])
			weights["models"]["values"] = res[t][1]
		elif t == "t3":
			res[t] = run_heat(D, dev, a, base["t3_camp_blur_pearson"])
			np.savez_compressed(os.path.join(a.out, "heat_pred.npz"), **res[t][1])
		else:
			sys.exit(f"unknown task {t}")
		log(f"{t} done in {(time.time() - ts) / 60:.1f} min")
	secs = time.time() - t0
	if a.quick:
		for m in weights["models"].values():
			m["export"] = False
			m["note"] = "QUICK run (function test): " + m["note"]
	json.dump(weights, open(os.path.join(a.out, "dl_weights.json"), "w"), indent=0)
	json.dump({t: r[0] for t, r in res.items()}, open(os.path.join(a.out, "results.json"), "w"), indent=1)
	open(os.path.join(a.out, "report.md"), "w").write(report(res, base, a, dev, secs))
	open(os.path.join(a.out, "log.txt"), "w").write("\n".join(LOG) + "\n")
	print(open(os.path.join(a.out, "report.md")).read())
	if a.archive:
		with tarfile.open(a.archive, "w:gz") as tf:
			tf.add(a.out, arcname=os.path.basename(a.out.rstrip("/\\")))
		size = os.path.getsize(a.archive)
		if size > 20 * 2 ** 20:
			with open(a.archive, "rb") as f:
				k = 1
				while True:
					chunk = f.read(20 * 2 ** 20)
					if not chunk:
						break
					open(f"{a.archive}.part{k:02d}", "wb").write(chunk)
					k += 1
			os.remove(a.archive)
			print(f"wrote {a.archive}.part01..part{k - 1:02d} ({size / 2 ** 20:.1f} MiB): upload every part")
		else:
			print(f"wrote {a.archive} ({size / 2 ** 20:.1f} MiB): upload this file")


if __name__ == "__main__":
	main()
