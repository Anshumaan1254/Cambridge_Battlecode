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
