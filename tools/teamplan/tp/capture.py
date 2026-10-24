"""Twin of capture.h."""
from .kit import gold_weight


class Cand:
	__slots__ = ("slot", "bag", "items", "walk_reward", "walk_bank", "danger", "kit")

	def __init__(self, slot, bag, items, walk_reward, walk_bank, danger, kit):
		self.slot, self.bag, self.items, self.walk_reward, self.walk_bank, self.danger, self.kit = slot, bag, items, walk_reward, walk_bank, danger, kit


def tribute_turns(bag):
	return 0 if bag <= 0 else (bag + 9) // 10


def p_bank(h, t):
	return 1.0 / (1.0 + h * t)


def capture_gain(x, gems, gold, w_rel, rate, dps_rel, c, p):
	k = x.kit
	h = p.hazard * k.exposure + p.danger_hazard * x.danger
	t0 = x.walk_bank + tribute_turns(x.bag)
	t1 = x.walk_reward + c.capture_time + x.walk_bank + tribute_turns(x.bag + gems)
	p0, p1 = p_bank(h, t0), p_bank(h, t1)
	v = gems * p1 - x.bag * (p0 - p1)
	v += p.gold_gems * gold * k.gold_mult * w_rel
	v += p.gold_gems * k.tribute_gold * gems * p1
	v -= (x.walk_reward + c.capture_time) * rate * dps_rel
	return v


def choose_capturer(cands, gems, gold, team_n, c, p):
	"""(index into cands or -1, gains)."""
	n = len(cands)
	if n <= 0:
		return -1, []
	wsum = dsum = 0.0
	for x in cands:
		wsum += gold_weight(x.kit, x.items, p)
		dsum += x.kit.camp_dps
	wmean, dmean = wsum / n, dsum / n
	rate = p.team_rate / (team_n if team_n > 0 else 1)
	best, bv, gains = -1, 0.0, []
	for i, x in enumerate(cands):
		wr = gold_weight(x.kit, x.items, p) / wmean if wmean > 0 else 1.0
		dr = x.kit.camp_dps / dmean if dmean > 0 else 1.0
		v = capture_gain(x, gems, gold, wr, rate, dr, c, p)
		gains.append(v)
		if best < 0 or v > bv or (v == bv and x.slot < cands[best].slot):
			best, bv = i, v
	return best, gains
