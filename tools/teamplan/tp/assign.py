"""Twin of assign.h (list scheduling)."""
from .kit import front_order

NO_OWNER = 255


class AGroup:
	__slots__ = ("value", "hp", "walk", "gem_free")

	def __init__(self, value, hp, walk, gem_free):
		self.value, self.hp, self.walk, self.gem_free = value, hp, walk, gem_free


def front_norm(kits):
	n = len(kits)
	out = [0.0] * n
	for r, b in enumerate(front_order(kits)):
		out[b] = float(n - 1 - r) / (n - 1) if n > 1 else 0.5
	return out


def group_key(g, dps_mean, c):
	clear = g.hp / dps_mean if dps_mean > 0 else 1e9
	return g.value / (g.walk + clear + c.capture_time)


def assign_groups(gs, kits, alive, c, p, cap=64):
	"""(owner per group, time per body, value per body). cap: groups planned without buffers (the header's 64)."""
	n, G = len(kits), len(gs)
	fn = front_norm(kits)
	used, val = [0.0] * n, [0.0] * n
	owner = [NO_OWNER] * G
	dsum, na = 0.0, 0
	for b in range(n):
		if alive >> b & 1:
			dsum += kits[b].camp_dps
			na += 1
	if na > 0:
		dmean = dsum / na
		reach = [g for g in range(G) if gs[g].walk >= 0][:cap]
		keys = {g: group_key(gs[g], dmean, c) for g in reach}
		order = sorted(reach, key=lambda g: (-keys[g], g))
		for gi in order:
			g = gs[gi]
			bb, bc, bf = -1, 0.0, 0.0
			for b in range(n):
				if not (alive >> b & 1):
					continue
				k = kits[b]
				pref = 1.0 + p.gemfree_front * (fn[b] - 0.5) if g.gem_free else 1.0 - p.gemfree_front * (fn[b] - 0.5)
				clear = g.hp / k.camp_dps if k.camp_dps > 0 else 1e9
				fin = used[b] + g.walk + clear + c.capture_time
				cost = fin / pref
				if bb < 0 or cost < bc:
					bb, bc, bf = b, cost, fin
			owner[gi] = bb
			used[bb] = bf
			val[bb] += g.value
	return owner, used, val
