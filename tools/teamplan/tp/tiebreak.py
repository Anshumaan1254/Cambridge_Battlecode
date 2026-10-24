"""Twin of tiebreak.h."""
from .capture import tribute_turns

RING = 9


class TbState:
	def __init__(self):
		self.mode, self.n, self.last_round = 0, 0, -1000000
		self.ours, self.theirs, self.rnd = [0] * RING, [0] * RING, [0] * RING
		self.proj_ours = self.proj_theirs = 0


def tb_project(rnd, banked, carried, rate, c):
	need = c.winning_gems - banked - carried
	if need <= 0:
		return rnd
	if rate <= 0:
		return 2 * c.max_rounds
	r = rnd + need / rate
	return 2 * c.max_rounds if r > 2.0 * c.max_rounds else int(r)


def tb_update(s, rnd, our_banked, their_banked, our_carried, prone, c, p):
	if rnd - s.last_round < p.tb_period:
		return s.mode
	s.last_round = rnd
	if s.n == RING:
		s.ours = s.ours[1:] + [0]
		s.theirs = s.theirs[1:] + [0]
		s.rnd = s.rnd[1:] + [0]
		s.n = RING - 1
	s.ours[s.n], s.theirs[s.n], s.rnd[s.n] = our_banked, their_banked, rnd
	s.n += 1
	if s.n < 3:
		return s.mode
	dt = s.rnd[s.n - 1] - s.rnd[0]
	ro = float(s.ours[s.n - 1] - s.ours[0]) / dt
	rt = float(s.theirs[s.n - 1] - s.theirs[0]) / dt
	s.proj_ours = tb_project(rnd, our_banked, our_carried, ro, c)
	s.proj_theirs = tb_project(rnd, their_banked, 0, rt, c)
	min_round = p.tb_min_round // 2 if prone else p.tb_min_round
	if not s.mode:
		if rnd >= min_round and s.proj_ours > c.max_rounds + p.tb_enter and s.proj_theirs > c.max_rounds + p.tb_enter:
			s.mode = 1
	elif s.proj_ours < c.max_rounds + p.tb_leave or s.proj_theirs < c.max_rounds + p.tb_leave:
		s.mode = 0
	return s.mode


def tb_defer(mode, bag, enemy_dist, p):
	return bool(mode) and bag <= p.tb_defer_cap and enemy_dist > p.tb_safe_dist


def tb_final(rnd, walk_bank, bag, c, p):
	return bag > 0 and rnd + walk_bank + tribute_turns(bag) + p.tb_final_margin >= c.max_rounds


def tb_denial(rnd, c, p):
	return rnd >= c.max_rounds - p.tb_denial_rounds
