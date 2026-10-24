"""Twin of swap.h."""
from .kit import can_swap


def progress_code(q):
	return 0 if q < 0.5 else 1 if q < 1.0 else 2 if q < 1.5 else 3


def progress_center(code):
	return 0.25 + 0.5 * code


class SwapState:
	def __init__(self):
		self.last, self.a, self.b = -1000000, -1, -1


def swap_check(s, rnd, plan_rate, code, kits, alive, p, w=None):
	n = len(kits)
	if rnd - s.last < p.swap_hold or rnd % p.swap_period != 0:
		return 0
	ba = bb = -1
	bg = 0.0
	for a in range(n):
		if not (alive >> a & 1):
			continue
		qa = progress_center(code[a])
		if qa >= p.lag_ratio:
			continue
		for b in range(n):
			if b == a or not (alive >> b & 1) or not can_swap(kits[a], kits[b], 0.25):
				continue
			qb = progress_center(code[b])
			cur = plan_rate[a] * qa + plan_rate[b] * qb
			gain = (plan_rate[a] - plan_rate[b]) * (qb - qa)
			if w is not None:
				gain += w[0] * qa + w[1] * qb + w[2] * plan_rate[a] + w[3] * plan_rate[b] + w[4]
			if cur > 0 and gain >= p.swap_margin * cur and (ba < 0 or gain > bg):
				ba, bb, bg = a, b, gain
	if ba < 0:
		return 0
	s.last, s.a, s.b = rnd, ba, bb
	return 1


def swap_owners(owner, a, b):
	return [b if o == a else a if o == b else o for o in owner]
