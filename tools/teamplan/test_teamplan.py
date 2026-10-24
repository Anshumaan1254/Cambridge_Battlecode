#!/usr/bin/env python3
"""Engine tests of the teamplan library (TEAMPLAN.md section 9) through the test bot tools/teamplan/cpp/test/main.cpp.

    python3 -I tools/teamplan/test_teamplan.py [--maps 'maps/official/*.map26a'] [--jobs 4] [--rounds 12] [--dump-designs]

Builds bots/_tp_test (git-ignored) = the test bot + tools/teamplan/cpp/teamplan/, plays the test bot against itself on every map (both
teams' prints are checked) and recomputes everything with the Python twins (tools/teamplan/tp/), bit for bit (FNV-1a hashes of the
values' bytes, as the bot prints them):
  * the engine designs and constants equal experiments/results/teamplan/designs_3_0_5.txt (--dump-designs writes that file);
  * params.h's defaults equal tp/params.py's (one hash);
  * kit.h on all 13 designs; assign.h on the map's groups for 3 test rosters (owners and runners-up), the plan and one variant per body left out;
    capture.h on 16 groups per roster (synthetic bags, items, walks and danger); timing.h, bag.h, focus.h, tiebreak.h, swap.h, live.h
    and nav.h on fixed sweeps;
  * nav_sdk.h's local detour returns a neighbouring tile or the body's own;
  * 0 exceptions; and the fuel of each part (the worst call over maps) is printed.
Exit status 1 on any failure."""
import argparse
import glob
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from tp import assign, bag, capture, designs, focus, kit, live, nav, params, swap, tiebreak, timing  # noqa: E402

ROSTER = [[1, 7, 12, 2, 0], [3, 4, 5, 9, 10], [6, 8, 11, 0, 12]]


class H:
	def __init__(self):
		self.h = 0xcbf29ce484222325

	def byte(self, b):
		self.h ^= b
		self.h = (self.h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF

	def d(self, v):
		for b in struct.pack("<d", float(v)):
			self.byte(b)

	def str(self):
		return f"{self.h:016x}"


def i32(v):
	"""The bot hashes int32(v) (two's complement of the low 32 bits)."""
	v &= 0xFFFFFFFF
	return v - (1 << 32) if v >= 1 << 31 else v


class HI(H):
	def i(self, v):
		for b in struct.pack("<i", i32(int(v))):
			self.byte(b)


def build(name="_tp_test"):
	d = os.path.join(ROOT, "bots", name)
	shutil.rmtree(os.path.join(d, "src"), ignore_errors=True)
	os.makedirs(os.path.join(d, "src"))
	shutil.copy(os.path.join(HERE, "cpp", "test", "main.cpp"), os.path.join(d, "src", "main.cpp"))
	shutil.copytree(os.path.join(HERE, "cpp", "teamplan"), os.path.join(d, "src", "teamplan"))
	r = subprocess.run(["cambc", "build", name, "--release"], cwd=ROOT, capture_output=True, text=True)
	if r.returncode != 0:
		sys.exit("test bot build failed:\n" + (r.stdout + r.stderr)[-4000:])
	return name


def member(path, name):
	with zipfile.ZipFile(path) as z:
		for n in z.namelist():
			if n.endswith(name):
				return z.read(n).decode("utf-8", "replace").replace("\x00", "")
	return ""


def lines_of(text):
	out = {}
	for l in text.splitlines():
		l = l.strip()
		if l.startswith("TP "):
			t = l.split()
			out.setdefault(t[1], []).append(t[2:])
	return out


# ---- the Python side of each check
def kit_hash(k):
	h = HI()
	for v in (k.melee, k.has_dash, k.stun_immune, k.splash, k.remote_shop, k.reset_on_kill):
		h.i(v)
	for f in ["hp", "resets", "basic", "spell", "spell_mod", "area", "area_mod", "stun", "shield", "heal", "dash_range", "reach", "gold_mult",
			  "tribute_gold", "focus_per_gem", "retaliation", "mhp_bonus", "str_per_hp", "dps", "camp_dps", "ehp", "dmg_str_shard",
			  "dmg_foc_shard", "dmg_hp_shard", "w_gold", "exposure", "front"]:
		h.d(getattr(k, f))
	return h.str()


def params_hash(P):
	h = HI()
	for f in ["enhanced_extra", "enhanced_stun", "missing_hp_avg", "hits_taken", "splash_targets", "area_targets", "fight_rounds", "ranged_front", "immune_ehp",
			  "dash_escape", "reach_escape", "gold_gems", "team_rate", "hazard", "danger_hazard", "items_half"]:
		h.d(getattr(P, f))
	h.i(P.capture_mode)
	h.i(P.bag_fight), h.d(P.bag_fight_scale), h.d(P.hunt_bag), h.d(P.hunt_bonus), h.d(P.kv_ref)
	for f in ["tb_period", "tb_enter", "tb_leave", "tb_min_round", "tb_defer_cap", "tb_safe_dist", "tb_final_margin", "tb_denial_rounds"]:
		h.i(getattr(P, f))
	h.d(P.own_bonus), h.d(P.gemfree_front), h.i(P.swap_period), h.i(P.swap_hold), h.d(P.swap_margin), h.d(P.lag_ratio)
	return h.str()


def parse_groups(tok):
	n, blob = int(tok[0]), tok[1] if len(tok) > 1 and not tok[1].startswith("fuel") else ""
	gs = []
	for i in range(n):
		s = blob[14 * i: 14 * i + 14]
		gems, gold, hp, walk = int(s[0:3], 16), int(s[3:6], 16), int(s[6:11], 16), int(s[11:14], 16)
		gs.append((gems, gold, hp, -1 if walk == 0xFFF else walk))
	return gs


def agroups(gs, P):
	return [assign.AGroup(g[0] + P.gold_gems * g[1], float(g[2]), g[3], 1 if g[0] == 0 else 0) for g in gs]


def assign_hash(gs, kits_all, r, team_n, C, P):
	kits = [kits_all[ROSTER[r][b]] for b in range(team_n)]
	ag = agroups(gs, P)
	h = HI()
	for v in range(-1, team_n):
		alive = ((1 << team_n) - 1) & ~((1 << v) if v >= 0 else 0)
		owner, tm, vl, run = assign.assign_groups(ag, kits, alive, C, P, runner=True)
		for o, u in zip(owner, run):
			h.i(o), h.i(u)
		for b in range(team_n):
			h.d(tm[b]), h.d(vl[b])
	return h.str()


def capture_hash(gs, kits_all, r, team_n, C, P):
	h = HI()
	ng = 0
	for g in range(len(gs)):
		if ng >= 16:
			break
		if gs[g][3] < 0:
			continue
		ng += 1
		cs = []
		for s in range(team_n):
			if (g + s) % 3 == 0:
				continue
			cs.append(capture.Cand(s, (g * 7 + s * 13) % 70, (g + 3 * s) % 15, (g + s) % 4, min(gs[g][3], 60), float((g * (s + 1)) % 3),
								   kits_all[ROSTER[r][s]]))
		for mode in (0, 1):
			q = params.Params(**{**P.__dict__, "capture_mode": mode, "items_half": 0.0 if mode else 12.0})
			w, gains = capture.choose_capturer(cs, gs[g][0], gs[g][1], team_n, C, q)
			h.i(w)
			for v in gains:
				h.d(v)
	return h.str()


def s1_hashes(kits_all, team_n, C, P):
	h = HI()
	for rnd in range(1, 5):
		for team in range(2):
			for no in range(1, 6):
				for nt in range(1, 6):
					for ur in range(no):
						for er in range(nt):
							h.i(timing.turn_pos(rnd, team, ur, no, nt))
							h.i(1 if timing.we_act_first(rnd, team, ur, no, er, nt) else 0)
	prio, ids = [3, 1, 3, 0, 2], [4, 2, 1, 0, 3]
	for me in range(5):
		h.i(timing.rank_of(prio, ids, me))
	ht = h.str()
	h = HI()
	for b_ in range(0, 91, 15):
		h.d(bag.fight_bar(1.2, b_, P))
		for ed in range(1, 10, 2):
			for wb in range(0, 13, 4):
				h.i(1 if bag.bank_before_fight(b_, ed, 4, wb, (ed + wb) % 2 == 0, P) else 0)
		for o in range(1, 4):
			for t in range(1, 4):
				h.d(bag.hunt_bonus(b_, o, t, P))
		h.i(1 if bag.bank_now_wins(900, b_, 15, C) else 0)
	hb = h.str()
	h = HI()
	for b_ in range(0, 81, 20):
		for bodies in (1, 2):
			for n in (3, 4, 5):
				kv = focus.kill_value(b_, bodies, n, C, P)
				h.d(kv)
				for rk in (0, 3, 6):
					h.d(focus.target_priority(kv, rk, P))
	return {"timing": ht, "bag": hb, "focus": h.str()}


def s2_hashes(C, P):
	h = HI()
	for sc in range(3):
		s = tiebreak.TbState()
		a, b = 0.25 + 0.15 * sc, 0.45 - 0.1 * sc
		for rnd in range(1, 2001, 10):
			ours, theirs, carried = int(rnd * a), int(rnd * b), (rnd // 7) % 40
			h.i(tiebreak.tb_update(s, rnd, ours, theirs, carried, sc % 2, C, P))
			h.i(s.proj_ours), h.i(s.proj_theirs)
			h.i(1 if tiebreak.tb_defer(s.mode, carried, (rnd // 3) % 15, P) else 0)
			h.i(1 if tiebreak.tb_final(rnd, (rnd // 11) % 40, carried, C, P) else 0)
			h.i(1 if tiebreak.tb_denial(rnd, C, P) else 0)
	return {"tiebreak": h.str()}


def s3_hashes(kits_all, team_n, P):
	h = HI()
	for r in range(3):
		kits = [kits_all[ROSTER[r][b]] for b in range(team_n)]
		s = swap.SwapState()
		for rnd in range(0, 1001, 50):
			plan = [0.1 + 0.05 * ((b * 3 + rnd // 50) % 7) for b in range(team_n)]
			code = [(b + rnd // 100) % 4 for b in range(team_n)]
			h.i(swap.swap_check(s, rnd, plan, code, kits, (1 << team_n) - 1, P))
			h.i(s.a), h.i(s.b), h.i(s.last)
		for b in range(team_n):
			for q in range(8):
				h.i(swap.progress_code(0.25 * q)), h.i(1 if kit.can_swap(kits[b], kits[q % team_n], 0.25) else 0)
	hs = h.str()
	h = HI()
	v = 0
	for k in range(40):
		o = {"claim": (k * 11) % 64, "status": k % 4, "beat": (k // 2) % 2, "flag": (k // 3) % 2}
		v = live.set_body(v, k % 6, o)
		v = live.set_team(v, k % 8, (k // 5) % 2)
		w = live.load64(live.store64(v))
		r_ = live.get_body(w, (k * 5) % 6)
		h.i(w & 0xFFFFFFFF), h.i(w >> 32)
		for f in ("claim", "status", "beat", "flag"):
			h.i(r_[f])
		h.i(live.get_cursor(w)), h.i(live.get_tiebreak(w))
	bt = live.Beat()
	for rnd in range(12):
		h.i(1 if live.beat_stale(bt, rnd % 2 if rnd < 6 else 1, rnd) else 0)
	hl = h.str()
	h = HI()
	pr, lg = nav.Progress(), nav.LoopGuard()
	for rnd in range(30):
		target, dist = (7 if rnd < 12 else 9), 20 - (rnd % 9)
		h.i(1 if nav.progress_stuck(pr, target, dist, rnd, 4) else 0)
		tile = (rnd * 7) % 11
		h.i(1 if nav.loop_seen(lg, tile) else 0)
		nav.loop_push(lg, tile)
		h.i(1 if nav.keep_target(dist, (rnd * 3) % 25) else 0)
	return {"swap": hs, "live": hl, "nav": h.str()}


def design_lines(out):
	return [" ".join(["DES"] + t) for t in out.get("DES", [])] + [" ".join(["CON"] + t) for t in out.get("CON", [])]


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--maps", default="maps/official/*.map26a")
	ap.add_argument("--jobs", type=int, default=4)
	ap.add_argument("--rounds", type=int, default=24)
	ap.add_argument("--dump-designs", action="store_true")
	a = ap.parse_args()
	fails = []
	bot = build()
	maps = sorted(glob.glob(os.path.join(ROOT, a.maps)))
	tmp = tempfile.mkdtemp(prefix="tp_test_")
	man = os.path.join(tmp, "man.txt")
	with open(man, "w") as f:
		for m in maps:
			f.write(f"{ROOT}/bots/{bot} {ROOT}/bots/{bot} {m} {tmp}/{os.path.basename(m)}.repl26a\n")
	subprocess.run(["cambc", "run-batch", man, "--jobs", str(a.jobs), "--rounds", str(a.rounds), "--release"], cwd=ROOT, capture_output=True, text=True)
	P = params.Params()
	stored = designs.DEFAULT
	ref_lines, kits_all, C = None, None, None
	if os.path.exists(stored) and not a.dump_designs:
		des, C = designs.load(stored)
		kits_all = {t: kit.compute_kit(des[t], C, P) for t in des}
		ref_lines = [l.strip() for l in open(stored) if l.strip() and not l.startswith("#")]
	fuel = {"kits": 0, "groups": 0, "assign": 0, "capture": 0, "timing": 0, "bag": 0, "focus": 0, "tiebreak": 0, "swap": 0, "live": 0, "nav": 0}
	navs = []
	n_cmp = 0
	for m in maps:
		n = os.path.splitext(os.path.basename(m))[0]
		rp = os.path.join(tmp, os.path.basename(m) + ".repl26a")
		for team, fn in ((0, "team-a.stdout"), (1, "team-b.stdout")):
			out = lines_of(member(rp, fn) if os.path.exists(rp) else "")
			if not out:
				fails.append(f"{n} team {team}: no test output")
				continue
			for e in out.get("E", []):
				fails.append(f"{n} team {team}: exception {' '.join(e)[:80]}")
			dl = design_lines(out)
			if a.dump_designs and ref_lines is None:
				os.makedirs(os.path.dirname(stored), exist_ok=True)
				ver = subprocess.run(["cambc", "--version"], capture_output=True, text=True).stdout.strip()
				with open(stored, "w") as f:
					f.write(f"# engine designs and constants for tools/teamplan/tp (doubles as bit hex); {ver}; tools/teamplan/test_teamplan.py --dump-designs\n")
					f.write("\n".join(dl) + "\n")
				des, C = designs.load(stored)
				kits_all = {t: kit.compute_kit(des[t], C, P) for t in des}
				ref_lines = dl
				print(f"wrote {os.path.relpath(stored, ROOT)}")
			if dl != ref_lines:
				fails.append(f"{n} team {team}: engine designs differ from {os.path.relpath(stored, ROOT)} (a patch? --dump-designs)")
				continue
			par = out.get("PAR", [[]])[0]
			if par[-1:] != [params_hash(P)] or par[:2] != ["version", str(params.VERSION)]:
				fails.append(f"{n} team {team}: params.h defaults differ from tp/params.py ({par})")
			for t in out.get("KIT", []):
				n_cmp += 1
				if t[1] != kit_hash(kits_all[int(t[0])]):
					fails.append(f"{n} team {team}: kit {t[0]} differs")
			for t in out.get("KF", []):
				fuel["kits"] = max(fuel["kits"], int(t[1]))
			g = out.get("G")
			if not g:
				fails.append(f"{n} team {team}: no TP G line")
				continue
			gs = parse_groups(g[0])
			fuel["groups"] = max(fuel["groups"], int(g[0][g[0].index("fuel_groups") + 1]))
			team_n = int(g[0][g[0].index("team_n") + 1])
			for t in out.get("A", []):
				n_cmp += 1
				r = int(t[0])
				if t[1] != assign_hash(gs, kits_all, r, team_n, C, P):
					fails.append(f"{n} team {team}: assign roster {r} differs (team size {team_n}, {len(gs)} groups)")
				fuel["assign"] = max(fuel["assign"], int(t[3]))
			for t in out.get("C", []):
				n_cmp += 1
				r = int(t[0])
				if t[1] != capture_hash(gs, kits_all, r, team_n, C, P):
					fails.append(f"{n} team {team}: capture roster {r} differs")
				fuel["capture"] = max(fuel["capture"], int(t[3]))
			want = {}
			want.update(s1_hashes(kits_all, team_n, C, P))
			want.update(s2_hashes(C, P))
			want.update(s3_hashes(kits_all, team_n, P))
			for key in ("S1", "S2", "S3"):
				t = out.get(key)
				if not t:
					fails.append(f"{n} team {team}: no TP {key} line")
					continue
				t = t[0]
				fi = t.index("fuel")
				names = t[:fi:2]
				for j, nm in enumerate(names):
					n_cmp += 1
					if t[2 * j + 1] != want[nm]:
						fails.append(f"{n} team {team}: {nm} differs")
					fuel[nm] = max(fuel[nm], int(t[fi + 1 + j]))
			for t in out.get("NAV", []):
				dx, dy, f = int(t[1]), int(t[2]), int(t[4])
				navs.append(f)
				if abs(dx) > 1 or abs(dy) > 1:
					fails.append(f"{n} team {team}: local detour stepped {dx},{dy}")
	print(f"maps: {len(maps)} x 2 teams, {n_cmp} hashed results compared with the Python twins")
	print("fuel, worst over maps: " + ", ".join(f"{k} {v}" for k, v in fuel.items())
		  + " (kits = all 13 designs in the draft; assign / capture = one call; the sweeps include hashing)")
	if navs:
		navs.sort()
		print(f"local detour (nav_sdk.h, radius 3): median {navs[len(navs) // 2]} fuel, max {navs[-1]} over {len(navs)} calls")
	print("FAILURES:\n  " + "\n  ".join(fails[:40]) if fails else "all checks passed")
	sys.exit(1 if fails else 0)


if __name__ == "__main__":
	main()
