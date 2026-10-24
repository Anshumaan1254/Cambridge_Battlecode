#!/usr/bin/env python3
"""Draft memory version 2 (docs/DRAFT_MEMORY.md): the Python twin of tools/mapintel/cpp/mapintel/dmem2.h (its header comment has the
layout and every block's definition). Bit-equal, checked in the engine by tools/mapintel/test_dmem2.py. COMPUTED, with the LEARNED
values it names (teamplan Params::capture_mode and gold_gems, the economy's bank bag and retreat line).

Builders take the draft's state (compact.Compact for our side and the enemy's, the plans, the picks) and return the block's bytes;
image() packs blocks into the 1,024 bytes; Reader parses an image as dmem2.h's Reader does."""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "teamplan"))
import compact as CP  # noqa: E402
import economy as EC  # noqa: E402
import hazards as HZ  # noqa: E402
from tp import assign as TA  # noqa: E402
from tp import designs as TD  # noqa: E402
from tp import kit as TK  # noqa: E402
from tp import params as TP  # noqa: E402

DM2_MAGIC, DM2_LAYOUT, DM2_FINAL, DM2_MINIMAL = 0x54, 2, 1, 2
DM2_SIZE, DM2_TOC, DM2_NTOC, DM2_BUILDER, DM2_NBODY = 1024, 4, 12, 1, 13
OWN_MAX, NSLOT = 64, 6
BLOCKS = [("T", 100, 16, 1), ("O", 116, 64, 1), ("B", 180, 96, 1), ("C", 276, 32, 1), ("K", 308, 32, 1), ("E", 340, 16, 1),
		  ("N", 356, 64, 1), ("D", 420, 16, 1), ("M", 512, 352, 1), ("L", 864, 136, 1)]
BK = {b[0]: k for k, b in enumerate(BLOCKS)}
AB_DMG = (TK.AB_DAMAGE, TK.AB_AOE, TK.AB_CC, TK.AB_DASH)


def econ_body():
	e = EC.econ()
	return int(e["bank_bag"]), int(math.floor(e["retreat"] * 100.0 + 0.5))


class Kits13:
	"""Kits of every body type (the engine designs dumped by tools/teamplan/test_teamplan.py --dump-designs) and the danger features."""

	def __init__(self, params=None):
		des, self.c = TD.load()
		self.p = params or TP.Params()
		self.d = [des[t] for t in range(DM2_NBODY)]
		self.k = [TK.compute_kit(self.d[t], self.c, self.p) for t in range(DM2_NBODY)]
		self.alpha, self.carrier = [], []
		for t in range(DM2_NBODY):
			d = self.d[t]
			a = d.str
			for ab in d.ab:
				if ab.kind in AB_DMG and ab.mod > 0:
					a += ab.mod * d.foc
			self.alpha.append(a)
			k = self.k[t]
			self.carrier.append((4 if k.focus_per_gem > 0 else 0) + (2 if k.tribute_gold > 0 else 0) + (1 if k.gold_mult > 1 else 0))
		self.burst_thr = sorted(self.alpha, reverse=True)[DM2_NBODY // 3 - 1]


def pick_class(K, pick, ctx):
	b = CP.pick_bodies(pick)
	burst = any(K.alpha[t] >= K.burst_thr for t in b)
	stun = any(K.k[t].stun > 0 for t in b)
	carry = any(K.carrier[t] > 0 for t in b)
	cstun = any(K.k[t].stun > 0 for q in ctx if q != pick for t in CP.pick_bodies(q))
	return 1 if burst else 2 if (stun and cstun) else 3 if carry else 0


def roster_types(picks):
	return sorted(set(b for p in picks for b in CP.pick_bodies(p)))[:NSLOT]


# ---- OWN
class OwnResult:
	def __init__(self):
		self.b, self.n, self.G, self.mask, self.anchor = bytes([0xFF] * OWN_MAX), 0, 0, 0, [255] * NSLOT


def own_groups(C, M, p):
	G = min(len(M.groups), OWN_MAX)
	out = []
	for g in range(G):
		grp = M.groups[g]
		d = C.dU[g]
		out.append(TA.AGroup(grp["gems"] + p.gold_gems * grp["gold"], C.prep[g][1], d if 0 <= d <= 254 else -1, 1 if grp["gems"] == 0 else 0))
	return out


def build_own(gs, types, K):
	r = OwnResult()
	r.G, r.n = len(gs), len(types)
	kits = [K.k[t] for t in types]
	for t in types:
		r.mask |= 1 << t
	if r.n > 0 and r.G > 0:
		owner, _, _, run = TA.assign_groups(gs, kits, (1 << r.n) - 1, K.c, K.p, cap=10 ** 9, runner=True)
	else:
		owner, run = [TA.NO_OWNER] * r.G, [TA.NO_OWNER] * r.G
	b = bytearray([0xFF] * OWN_MAX)
	for g in range(r.G):
		o = 15 if owner[g] == TA.NO_OWNER else owner[g]
		u = 15 if run[g] == TA.NO_OWNER else run[g]
		b[g] = o | (u << 4)
	r.b = bytes(b)
	if r.n > 0:
		dsum = sum(k.camp_dps for k in kits)
		dmean = dsum / r.n
		reach = [g for g in range(r.G) if gs[g].walk >= 0]
		keys = {g: TA.group_key(gs[g], dmean, K.c) for g in reach}
		for g in sorted(reach, key=lambda g: (-keys[g], g)):
			s = owner[g]
			if s < r.n and r.anchor[s] == 255:
				r.anchor[s] = g
	return r


# ---- TEAM
def build_team(mode, types, own, capture_mode):
	b = bytearray(16)
	b[2] = (1 if mode != 0 else 0) | ((mode & 3) << 1)
	b[3] = capture_mode
	for s in range(NSLOT):
		b[4 + s] = types[s] if s < len(types) else 255
	if own is not None:
		b[10], b[11], b[12], b[13] = own.G, own.n, own.mask & 0xFF, (own.mask >> 8) & 0xFF
	return bytes(b)


# ---- BODY
def body_roles(types, K):
	n = len(types)
	role = [0] * NSLOT
	kits = [K.k[t] for t in types]
	bank = -1
	for s in range(n):
		if kits[s].gold_mult > 1 and (bank < 0 or kits[s].gold_mult > kits[bank].gold_mult):
			bank = s
	if bank < 0:
		for s in range(n):
			if kits[s].tribute_gold > 0 and (bank < 0 or kits[s].tribute_gold > kits[bank].tribute_gold):
				bank = s
	if bank >= 0:
		role[bank] = 3
	fronts = 0
	for s in TK.front_order(kits):
		if fronts >= (2 if n >= 5 else 1):
			break
		if s != bank:
			role[s] = 1
			fronts += 1
	carry = -1
	for s in range(n):
		if role[s] == 0 and s != bank and (carry < 0 or kits[s].dps > kits[carry].dps):
			carry = s
	if carry >= 0:
		role[carry] = 2
	return role


def build_body(types, K, plan_bodies, plan, bank_bag, retreat_pct, hook=None):
	"""plan_bodies / plan: compact.Compact.plan1's output (bodies in pick order, [[group, arrive, end], ...] per body)."""
	b = bytearray([0xFF] * 96)
	role = body_roles(types, K)
	for s, t in enumerate(types[:NSLOT]):
		o = 16 * s
		b[o] = role[s]
		if hook:
			b[o + 1:o + 9] = bytes(hook(s, t, types))
		ps = max((i for i, x in enumerate(plan_bodies) if x == t), default=-1)
		for k in range(3):
			b[o + 9 + k] = plan[ps][k][0] if ps >= 0 and k < len(plan[ps]) and plan[ps][k][0] is not None and plan[ps][k][0] >= 0 else 255
		b[o + 12] = min(255, max(0, bank_bag))
		b[o + 13] = min(100, max(0, retreat_pct))
		b[o + 14] = b[o + 15] = 0
	return bytes(b)


# ---- CONT
def build_cont(K, enemy_picks, types, hook=None):
	b = bytearray(32)
	for p in range(12):
		b[2 * p] = hook(p, types) if hook else 255
		b[2 * p + 1] = pick_class(K, p, enemy_picks)
	return bytes(b)


# ---- CODE
def bank_order(C, bank):
	"""dmem2.h bank_order: altars by the value of plan 2's groups banking there (descending, ties: lower altar), up to 8."""
	sums, cnt = {}, {}
	for g, a in enumerate(bank):
		if a != 255:
			sums[a] = sums.get(a, 0.0) + C.val[g]
			cnt[a] = cnt.get(a, 0) + 1
	return sorted(cnt, key=lambda a: (-sums[a], a))[:8]


def bank_order_py(C):
	return bank_order(C, C.bank_altars())


def rally_tiles(C, con, bank_ord):
	"""dmem2.h rally_tiles: the approaches of plan 3's contested groups (up to 5), then of the bank altars, then the other contested
	groups; up to 8 tile indices."""
	M, t = C.M, C.t
	f = C.fc[t]
	out = []

	def add(v):
		if v is not None and v >= 0 and len(out) < 8 and v not in out:
			out.append(v)

	def group_rally(g):
		t0 = C.near_tile(g)
		if g is None or g < 0 or g >= len(M.groups) or t0 < 0 or f[t0 // M.W, t0 % M.W] < 0:
			return -1
		camps = [(c[1], c[2], EC.camp_stats(c[0])) for c in M.groups[g]["camps"]]
		R = max([st[2] for _, _, st in camps if st[1] > 0], default=-1)
		x, y = t0 % M.W, t0 // M.W
		for _ in range(int(f[t0 // M.W, t0 % M.W]) + 1):
			ok = all(not (st[1] > 0 and max(abs(cx - x), abs(cy - y)) <= R) if R >= 0 else (cx, cy) != (x, y) for cx, cy, st in camps)
			v = int(f[y, x])
			if ok or v == 0:
				return y * M.W + x
			for k in range(8):
				nx, ny = x + HZ.DX[k], y + HZ.DY[k]
				if 0 <= nx < M.W and 0 <= ny < M.H and int(f[ny, nx]) == v - 1:
					break
			else:
				return -1
			x, y = nx, ny
		return -1

	def altar_rally(a):
		if a is None or a < 0 or a >= len(M.altar_tiles):
			return -1
		ax, ay = M.altar_tiles[a]
		best = [None, None]
		for dy in (-1, 0, 1):
			for dx in (-1, 0, 1):
				x, y = ax + dx, ay + dy
				if (dx, dy) == (0, 0) or not (0 <= x < M.W and 0 <= y < M.H) or not C.C[t][y, x]:
					continue
				v, c = int(f[y, x]), 1 if M.camps[y, x] else 0
				if v >= 0 and (best[c] is None or v < best[c][0]):
					best[c] = (v, y * M.W + x)
		return best[0][1] if best[0] else (best[1][1] if best[1] else -1)

	k = 0
	while k < len(con) and len(out) < 5:
		add(group_rally(con[k][0]))
		k += 1
	for a in list(bank_ord)[:8]:
		if len(out) < 8:
			add(altar_rally(a))
	for j in range(k, len(con)):
		if len(out) < 8:
			add(group_rally(con[j][0]))
	return out


def build_code(C, con, own, bank_ord):
	b = bytearray(32)
	rt = rally_tiles(C, con, bank_ord)
	for k in range(8):
		v = rt[k] if k < len(rt) else 0xFFFF
		b[2 * k], b[2 * k + 1] = v & 0xFF, v >> 8
	for k in range(8):
		b[16 + k] = own.anchor[k] if own is not None and k < NSLOT else 255
	for k in range(8):
		b[24 + k] = bank_ord[k] if k < len(bank_ord) else 255
	return bytes(b)


# ---- ENEMY (CE = compact.Compact(M, 1 - team))
def build_enemy(CE, K, enemy_picks):
	b = bytearray([255] * 16)
	bodies = [x for p in enemy_picks for x in CP.pick_bodies(p)][:NSLOT]
	want = min(NSLOT, max(4, len(bodies)))
	cand = sorted([g for g in range(len(CE.dU)) if CE.dU[g] >= 0], key=lambda g: (CE.dU[g], g))[:want]
	order = []
	if bodies and cand:
		for g in CE.first_assign(bodies, cand):
			if g is not None and g not in order:
				order.append(g)
	order += [g for g in cand if g not in order]
	for k, g in enumerate(order[:4]):
		b[k], b[4 + k] = g, CE.bank_box(g)
	car = sorted([i for i in range(len(bodies)) if K.carrier[bodies[i]] > 0], key=lambda i: (-K.carrier[bodies[i]], i))
	for k, i in enumerate(car[:4]):
		b[8 + k] = bodies[i]
	for k, p in enumerate(enemy_picks[:4]):
		b[12 + k] = pick_class(K, p, enemy_picks)
	return bytes(b)


# ---- NAV inputs
def nav_anchor_groups(C, rank):
	G = len(C.dU)
	if rank:
		out = [g for g in rank if 0 <= g < G and C.dU[g] >= 0][:4]
	else:
		out = sorted([g for g in range(G) if C.dU[g] >= 0], key=lambda g: (C.dU[g], g))[:4]
	return out + [-1] * (4 - len(out))


def nav_anchor_groups_py(M, team, C, ftw=None):
	"""The anchors the draft uses: the first_scores() ranking when model_weights.h has it (ftw), else the nearest groups."""
	if ftw is None:
		import json
		fp = os.path.join(HERE, "..", "..", "experiments", "results", "mapintel", "first_targets", "weights.json")
		ftw = json.load(open(fp)) if os.path.exists(fp) else None
	rank = None
	if ftw is not None:
		import export_headers as EH
		rank = EH.first_rank_py(M, team, ftw, 16)
	return nav_anchor_groups(C, rank)


def build_debug(used, turns, skips):
	b = bytearray(16)
	for k in range(5):
		v = min(65535, max(0, used[k] // 16))
		b[2 * k], b[2 * k + 1] = v & 0xFF, v >> 8
	b[10], b[11], b[12], b[13] = DM2_BUILDER & 0xFF, (DM2_BUILDER >> 8) & 0xFF, turns, skips
	return bytes(b)


# ---- the image and the reader
def image(blocks, flags, base=None):
	"""blocks: {block id letter: bytes}; returns the 1,024 bytes (unwritten blocks: zero entry, base's bytes)."""
	b = bytearray(base if base is not None else bytes(DM2_SIZE))
	for idc, data in blocks.items():
		k = BK[idc]
		_, off, ln, ver = BLOCKS[k]
		d = bytes(data[:ln]) + bytes(max(0, ln - len(data)))
		b[off:off + ln] = d
		s = sum(d) & 0xFF
		b[DM2_TOC + 8 * k:DM2_TOC + 8 * k + 8] = bytes([ord(idc), ver, off & 0xFF, off >> 8, ln & 0xFF, ln >> 8, s, 1])
	seal(b, flags)
	return bytes(b)


def seal(b, flags):
	b[0], b[1], b[2] = DM2_MAGIC, DM2_LAYOUT, flags
	b[3] = sum(b[DM2_TOC:DM2_TOC + 8 * DM2_NTOC]) & 0xFF


class Reader:
	def __init__(self, data):
		self.p = bytes(data)
		n = len(self.p)
		self.ok = n >= DM2_TOC + 8 * DM2_NTOC and self.p[0] == DM2_MAGIC and self.p[1] == DM2_LAYOUT and \
			(sum(self.p[DM2_TOC:DM2_TOC + 8 * DM2_NTOC]) & 0xFF) == self.p[3]

	def flags(self):
		return self.p[2] if self.ok else 0

	def block(self, idc, version):
		if not self.ok:
			return None
		for k in range(DM2_NTOC):
			e = self.p[DM2_TOC + 8 * k:DM2_TOC + 8 * k + 8]
			if e[0] != ord(idc):
				continue
			off, ln = e[2] | e[3] << 8, e[4] | e[5] << 8
			if e[1] != version or e[7] != 1 or off < DM2_TOC + 8 * DM2_NTOC or ln <= 0 or off + ln > len(self.p) or off + ln > DM2_SIZE:
				return None
			blk = self.p[off:off + ln]
			return blk if (sum(blk) & 0xFF) == e[6] else None
		return None


def team_slot(team, my_type):
	return next((s for s in range(NSLOT) if team[4 + s] == my_type), -1)
