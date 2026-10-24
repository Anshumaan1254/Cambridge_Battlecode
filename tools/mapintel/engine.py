#!/usr/bin/env python3
"""Engine facts for tools/mapintel, read from the engine probe's output (never typed in): game settings, camp designs, champion
designs and abilities, kit classes, and the draft-pick -> body mapping.

    from engine import Engine;  E = Engine()            # experiments/results/probe_v3_0_5/engine_3_0_5.txt by default
    python3 -I tools/mapintel/engine.py                 # prints the parsed tables and the kit classes

Probe: tools/probe/engine_probe_main.cpp (`cambc run` of the probe, team stdout). Lines:
  SET k v k v ...; CAMP id name hp v +g str v +g foc v +g range r vision v move m;
  CH id hp v +g str v +g foc v +g range r vision v move m campmul x;   AB slot s <kind> key value ...
The draft-pick -> body mapping follows the SDK enums (champion_draft vs champion_type): picks 0-2 are bodies 0-2, pick 3 (Cassi & Issac)
is bodies 3 and 4, picks 4-11 are bodies 5-12. It is checked against the engine by the battery's roster check (stats 'roster')."""
import os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PROBE = os.path.join(ROOT, "experiments/results/probe_v3_0_5/engine_3_0_5.txt")
CAMP_NAMES = ["wolf", "elk", "gem_cluster", "gold_cluster", "monolith", "golem"]
BODY_NAMES = ["Ryth", "Vesper Vale", "Vendetta", "Cassi", "Issac", "Stellar", "Prism", "Marcella", "Willow", "Ren", "Varg", "Tavi", "Heart of Ruin"]
PICK_NAMES = ["Ryth", "Vesper Vale", "Vendetta", "Cassi & Issac", "Stellar", "Prism", "Marcella", "Willow", "Ren", "Varg", "Tavi", "Heart of Ruin"]


def pick_bodies(pick):
	"""Body type ids of a draft pick (SDK enum order)."""
	return [pick] if pick < 3 else [3, 4] if pick == 3 else [pick + 1]


def _kv(tokens):
	out = {}
	i = 0
	while i < len(tokens):
		k = tokens[i]
		if i + 1 < len(tokens):
			v = tokens[i + 1]
			try:
				out[k] = float(v) if any(c in v for c in ".e") else int(v)
			except ValueError:
				out[k] = v
			if i + 2 < len(tokens) and tokens[i + 2].startswith("+"):
				out[k + "_growth"] = float(tokens[i + 2])
				i += 1
		i += 2
	return out


class Engine:
	def __init__(self, path=PROBE):
		self.settings, self.camps, self.champs = {}, {}, {}
		cur = None
		for line in open(path):
			t = line.split()
			if not t:
				continue
			if t[0] == "SET":
				self.settings.update(_kv(t[1:]))
			elif t[0] == "CAMP":
				d = _kv(t[3:])
				d["name"] = t[2]
				self.camps[int(t[1])] = d
			elif t[0] == "CH":
				cur = int(t[1])
				d = _kv(t[2:])
				d["abilities"] = []
				d["name"] = BODY_NAMES[cur]
				self.champs[cur] = d
			elif t[0] == "AB" and cur is not None:
				ab = {"slot": int(t[2]), "kind": t[3]}
				ab.update(_kv(t[4:]))
				self.champs[cur]["abilities"].append(ab)
		if len(self.camps) != 6 or len(self.champs) != 13:
			raise SystemExit(f"engine probe {path}: expected 6 camps and 13 champions, got {len(self.camps)} / {len(self.champs)}")

	# --- per-body kit facts
	def has_dash(self, body):
		return any(a["kind"] == "dash" for a in self.champs[body]["abilities"])

	def dash(self, body):
		return next((a for a in self.champs[body]["abilities"] if a["kind"] == "dash"), None)

	def attack_range(self, body):
		return int(self.champs[body]["range"])

	def kit_class(self, body):
		"""One of four classes from attack range and dash (MAPAnalysis 1.7 / prompt): 'melee_dash', 'melee', 'ranged_dash', 'ranged'."""
		return ("melee" if self.attack_range(body) <= 1 else "ranged") + ("_dash" if self.has_dash(body) else "")

	def spells(self, body):
		"""Damaging or stun spells (damage / aoe / cc, and a damaging dash landing), with their reach: range, + radius for areas."""
		out = []
		for a in self.champs[body]["abilities"]:
			if a["kind"] in ("damage", "aoe", "cc") or (a["kind"] == "dash" and a.get("mod", 0) > 0):
				rad = a.get("radius", 0.0) if a["kind"] in ("aoe", "dash") else 0.0
				out.append(dict(a, reach=a.get("range", 0) + rad))
		return out

	def classes(self):
		return {b: self.kit_class(b) for b in self.champs}


if __name__ == "__main__":
	E = Engine(sys.argv[1] if len(sys.argv) > 1 else PROBE)
	print("settings:", E.settings)
	for i, c in E.camps.items():
		print("camp", i, c)
	for b, c in E.champs.items():
		sp = ", ".join(f"{s['kind']} reach {s['reach']:g} mod {s.get('mod', 0):g}" for s in E.spells(b))
		print(f"body {b:2d} {c['name']:14s} {E.kit_class(b):12s} range {E.attack_range(b)} spells: {sp}")
	for p, n in enumerate(PICK_NAMES):
		print("pick", p, n, "->", [BODY_NAMES[b] for b in pick_bodies(p)])
