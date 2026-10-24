"""Engine designs for the twins: experiments/results/teamplan/designs_<engine>.txt, written by the engine test bot
(tools/teamplan/test_teamplan.py --dump-designs). Doubles are stored as the 16 hex digits of their bits, so nothing is rounded."""
import os
import struct

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
DEFAULT = os.path.join(ROOT, "experiments", "results", "teamplan", "designs_3_0_5.txt")
AB_NAMES = ["none", "reset", "damage", "aoe", "cc", "heal", "dash", "shield"]


def hexf(h):
	return struct.unpack(">d", bytes.fromhex(h))[0]


class Ability:
	__slots__ = ("kind", "enhanced", "range", "mod", "radius", "dur", "cd")

	def __init__(self, kind=0, enhanced=0, range_=0.0, mod=0.0, radius=0.0, dur=0, cd=0):
		self.kind, self.enhanced, self.range, self.mod, self.radius, self.dur, self.cd = kind, enhanced, range_, mod, radius, dur, cd


class Design:
	__slots__ = ("hp", "hp_g", "str", "str_g", "foc", "foc_g", "campmul", "range", "move", "vision", "passive", "ab")


class Consts:
	__slots__ = ("bonus_gold_pct", "focus_per_gem", "health_strength_ratio", "retaliation_ratio", "missing_health_bonus",
				 "tribute_gold_per_gem", "shard_cost", "respawn_time", "capture_time", "max_rounds", "winning_gems", "kill_gold")


def parse_design(tok):
	"""tok: the fields after 'DES t' (as the test bot prints them)."""
	d = Design()
	d.hp, d.hp_g, d.str, d.str_g, d.foc, d.foc_g, d.campmul = (hexf(x) for x in tok[:7])
	d.range, d.move, d.vision, d.passive = (int(x) for x in tok[7:11])
	d.ab = []
	for s in range(2):
		a = tok[11 + 7 * s: 18 + 7 * s]
		d.ab.append(Ability(int(a[0]), int(a[1]), hexf(a[2]), hexf(a[3]), hexf(a[4]), int(a[5]), int(a[6])))
	return d


def parse_consts(tok):
	c = Consts()
	(c.bonus_gold_pct, c.focus_per_gem, c.health_strength_ratio, c.retaliation_ratio, c.missing_health_bonus, c.tribute_gold_per_gem,
	 c.shard_cost) = (hexf(x) for x in tok[:7])
	c.respawn_time, c.capture_time, c.max_rounds, c.winning_gems, c.kill_gold = (int(x) for x in tok[7:12])
	return c


def load(path=DEFAULT):
	"""(designs by body type 0-12, consts)."""
	des, con = {}, None
	for line in open(path):
		t = line.split()
		if not t or t[0].startswith("#"):
			continue
		if t[0] == "DES":
			des[int(t[1])] = parse_design(t[2:])
		elif t[0] == "CON":
			con = parse_consts(t[1:])
	return des, con
