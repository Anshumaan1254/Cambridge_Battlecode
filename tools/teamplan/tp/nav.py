"""Twin of nav.h."""


class Progress:
	def __init__(self):
		self.target, self.best, self.since = -1, 1 << 30, 0


def progress_stuck(s, target, dist, rnd, k):
	if target != s.target:
		s.target, s.best, s.since = target, dist, rnd
		return False
	if dist < s.best:
		s.best, s.since = dist, rnd
		return False
	return rnd - s.since >= k


class LoopGuard:
	def __init__(self):
		self.n, self.head, self.tile = 0, 0, [0] * 8


def loop_push(g, t):
	g.tile[g.head] = t
	g.head = (g.head + 1) & 7
	if g.n < 8:
		g.n += 1


def loop_seen(g, t):
	return any(g.tile[i] == t for i in range(g.n))


def keep_target(best_dist, new_dist):
	return new_dist >= best_dist
