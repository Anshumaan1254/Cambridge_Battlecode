"""Twin of live.h (the 64-bit live protocol: places, the word, staleness, the per-turn layer)."""

PLACE_NONE, PLACE_GROUP, PLACE_ALTAR, PLACE_RALLY, NO_PLACE = 0, 1, 2, 3, 63
ALERT_ARMY, ALERT_ALTAR, ALERT_KILL, ALERT_HELP = 0, 1, 2, 3


class Places:
	def __init__(self, groups=0, altars=0, rallies=0):
		self.groups, self.altars, self.rallies = groups, altars, rallies


def place_code(P, kind, index):
	if kind == PLACE_GROUP:
		base, cnt = 0, P.groups
	elif kind == PLACE_ALTAR:
		base, cnt = P.groups, P.altars
	elif kind == PLACE_RALLY:
		base, cnt = P.groups + P.altars, P.rallies
	else:
		return NO_PLACE
	if index < 0 or index >= cnt or base + index >= NO_PLACE:
		return NO_PLACE
	return base + index


def place_kind(P, code):
	"""(kind, index)."""
	if 0 <= code < NO_PLACE:
		if code < P.groups:
			return PLACE_GROUP, code
		if code < P.groups + P.altars:
			return PLACE_ALTAR, code - P.groups
		if code < P.groups + P.altars + P.rallies:
			return PLACE_RALLY, code - P.groups - P.altars
	return PLACE_NONE, -1


def nearest_place(xs, ys, x, y):
	best, bd = NO_PLACE, 0
	for i in range(min(len(xs), NO_PLACE)):
		d = max(abs(xs[i] - x), abs(ys[i] - y))
		if best == NO_PLACE or d < bd:
			best, bd = i, d
	return best


def load64(b):
	return int.from_bytes(bytes(b[:8]), "little")


def store64(v):
	return list(int(v).to_bytes(8, "little"))


def get_body(v, slot):
	f = (v >> (8 * slot)) & 0xFF
	return {"claim": f & 63, "beat": (f >> 6) & 1, "flag": (f >> 7) & 1}


def set_body(v, slot, o):
	f = (o["claim"] & 63) | (o["beat"] & 1) << 6 | (o["flag"] & 1) << 7
	mask = 0xFF << (8 * slot)
	return ((v & ~mask) | (f << (8 * slot))) & 0xFFFFFFFFFFFFFFFF


def alert_bits(v):
	return (v >> 48) & 0xFFF


def get_alert(v):
	f = alert_bits(v)
	return {"place": ((f & 63) + 63) & 63, "kind": (f >> 6) & 3, "count": ((f >> 8) & 3) + 1, "seq": (f >> 10) & 3}


def set_alert(v, a):
	c = min(4, max(1, a["count"]))
	f = ((a["place"] + 1) & 63) | (a["kind"] & 3) << 6 | (c - 1) << 8 | (a["seq"] & 3) << 10
	return ((v & ~(0xFFF << 48)) | (f << 48)) & 0xFFFFFFFFFFFFFFFF


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
	def __init__(self, slot, n, ttl=5):
		self.slot, self.n, self.ttl = slot, min(6, n), ttl
		self.beat = 0
		self.watch = [FieldWatch() for _ in range(6)]
		self.ever = 0
		self.live = 0
		self.seen = 0
		self.round = 0
		self.alert = get_alert(0)
		self.alert_age = 99
		self.alert_field = 0
		self.alert_since, self.alert_obs = 0, -1


def live_observe(L, seen, rnd):
	L.seen, L.round, L.live = seen, rnd, 0
	for s in range(min(L.n, 6)):
		if s == L.slot:
			L.live |= 1 << s
			continue
		f = (seen >> (8 * s)) & 0xFF
		if f != 0 or (L.watch[s].obs >= 0 and f != L.watch[s].field):
			L.ever |= 1 << s
		stale = field_stale(L.watch[s], f, rnd)
		if (L.ever >> s & 1) and not stale:
			L.live |= 1 << s
	af = alert_bits(seen)
	if L.alert_obs < 0 or af != L.alert_field:
		L.alert_since = rnd
	L.alert_field, L.alert_obs = af, rnd
	L.alert = get_alert(seen)
	L.alert_age = 99 if L.alert["place"] == NO_PLACE else rnd - L.alert_since


def alert_accepts(L, post):
	c = L.alert
	return c["place"] == NO_PLACE or L.alert_age >= L.ttl or post["kind"] > c["kind"] or (post["kind"] == c["kind"] and post["place"] == c["place"])


def live_compose(L, claim, flag, cursor, tiebreak, post=None):
	"""(bytes to write back as a 64-bit value, whether we wrote the team bits, whether we posted the alert)."""
	L.beat ^= 1
	v = set_body(L.seen, L.slot, {"claim": claim, "beat": L.beat, "flag": flag})
	w = (L.live & ((1 << L.slot) - 1)) == 0
	if w:
		v = set_team(v, cursor, tiebreak)
	p = False
	if post is not None and 0 <= post["place"] < NO_PLACE and alert_accepts(L, post):
		a = dict(post)
		a["seq"] = (L.alert["seq"] + 1) & 3
		v = set_alert(v, a)
		L.alert, L.alert_field, L.alert_since, L.alert_age = get_alert(v), alert_bits(v), L.round, 0
		p = True
	return v, w, p
