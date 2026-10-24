"""Twin of live.h."""


def load64(b):
	return int.from_bytes(bytes(b[:8]), "little")


def store64(v):
	return list(int(v).to_bytes(8, "little"))


def get_body(v, slot):
	f = (v >> (10 * slot)) & 0x3FF
	return {"claim": f & 63, "status": (f >> 6) & 3, "beat": (f >> 8) & 1, "flag": (f >> 9) & 1}


def set_body(v, slot, o):
	f = (o["claim"] & 63) | (o["status"] & 3) << 6 | (o["beat"] & 1) << 8 | (o["flag"] & 1) << 9
	mask = 0x3FF << (10 * slot)
	return ((v & ~mask) | (f << (10 * slot))) & 0xFFFFFFFFFFFFFFFF


def get_cursor(v):
	return (v >> 60) & 7


def get_tiebreak(v):
	return (v >> 63) & 1


def set_team(v, cursor, tiebreak):
	return (v & 0x0FFFFFFFFFFFFFFF) | ((cursor & 7) << 60) | ((tiebreak & 1) << 63)


class Beat:
	def __init__(self):
		self.last, self.since = -1, 0


def beat_stale(s, beat, rnd):
	if beat != s.last:
		s.last, s.since = beat, rnd
	return rnd - s.since >= 2


class FieldWatch:
	def __init__(self):
		self.since, self.obs, self.field, self.doubted = 0, -1, 0, False


def field_stale(s, field, rnd):
	if s.obs < 0 or field != s.field:
		s.since, s.doubted = rnd, False
	elif rnd - s.obs == 2 and not s.doubted:
		s.since, s.doubted = max(s.since, rnd - 1), True
	s.field, s.obs = field, rnd
	return rnd - s.since >= 2


def live_slot_of(types, my_type):
	return sum(1 for t in types if t < my_type)


class LiveState:
	def __init__(self, slot, n):
		self.slot, self.n = slot, min(6, n)
		self.beat = 0
		self.watch = [FieldWatch() for _ in range(6)]
		self.ever = 0
		self.live = 0
		self.seen = 0


def live_observe(L, seen, rnd):
	L.seen = seen
	L.live = 0
	for s in range(min(L.n, 6)):
		if s == L.slot:
			L.live |= 1 << s
			continue
		f = (seen >> (10 * s)) & 0x3FF
		if f != 0 or (L.watch[s].obs >= 0 and f != L.watch[s].field):
			L.ever |= 1 << s
		stale = field_stale(L.watch[s], f, rnd)
		if (L.ever >> s & 1) and not stale:
			L.live |= 1 << s


def live_compose(L, claim, status, flag, cursor, tiebreak):
	"""(bytes to write back as a 64-bit value, whether we wrote the team bits)."""
	L.beat ^= 1
	v = set_body(L.seen, L.slot, {"claim": claim, "status": status, "beat": L.beat, "flag": flag})
	w = (L.live & ((1 << L.slot) - 1)) == 0
	if w:
		v = set_team(v, cursor, tiebreak)
	return v, w
