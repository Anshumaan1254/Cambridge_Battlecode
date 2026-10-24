#!/usr/bin/env python3
"""Tests of the mapintel C++ library (MAPAnalysis.md 5.8 / step 8) through the test bot tools/mapintel/cpp/test/main.cpp.

    python3 -I tools/mapintel/test_library.py [--maps 'maps/official/*.map26a'] [--perturbed N] [--sdk SDK_DIR] [--jobs 4]

Builds bots/_mi_test (git-ignored) = the test bot + tools/mapintel/cpp/mapintel/, plays one round on every map with both teams as the test
bot (both teams' prints are checked), and checks:
  * the runtime features equal tools/mapintel/features.py (relative 1e-9) for both teams on every official map;
  * the fingerprint equals experiments/results/mapintel/dump/fingerprints.txt (the same C++ function in the engine), and the table lookup
    (known_maps.h, when generated) finds the right entry;
  * on N perturbed copies of official maps (tools/mapgen/perturb.mjs: a few bush / wall tiles moved) the fingerprint matches no table
    entry (the unknown-map path) and the features still equal the Python values;
  * the compact plans (plans.h) equal tools/mapintel/compact.py exactly (plan 1 for the test roster compact.TEST_PICKS cut to the team
    size, plans 2-4), and the draft-memory block (dmem.h) equals compact.pack byte for byte;
  * the block survives the engine: written in the draft, then a shorter 4-byte write from offset 0 (as GOD v10 makes), and every champion
    reads it back unchanged in its first game turn (the prefix byte is the 4-byte write's);
  * fuel: the first draft turn's work stays under 1,000,000 and every later draft turn under 100,000 (the turn's fuel left is printed,
    and the later turns re-plan with the roster: plan_fuel);
  * 0 exceptions;
  * with dl_weights.h (tools/mapintel/dl/dl_export.py): its three functions equal tools/mapintel/dl/dl_ref.py (rankings exactly,
    champion values relative 1e-9) and their fuel (measured in draft turn 2) fits a later draft turn; --dl-weights names the json the
    header was generated from (checked by its sha256);
  * --sdk DIR builds the same sources against another SDK (e.g. a 3.0.4 `cambc init` sdk/) to check they compile there.
Exit status 1 on any failure."""
import argparse, glob, hashlib, json, os, shutil, struct, subprocess, sys, tempfile, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compact as CP  # noqa: E402
import export_headers as EH  # noqa: E402
import features as FT  # noqa: E402
import mapdata  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def build(name="_mi_test"):
	d = os.path.join(ROOT, "bots", name)
	shutil.rmtree(os.path.join(d, "src"), ignore_errors=True)
	os.makedirs(os.path.join(d, "src"))
	shutil.copy(os.path.join(ROOT, "tools/mapintel/cpp/test/main.cpp"), os.path.join(d, "src", "main.cpp"))
	shutil.copytree(os.path.join(ROOT, "tools/mapintel/cpp/mapintel"), os.path.join(d, "src", "mapintel"))
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


def hexf(h):
	"""A double from the 16 hex digits of its bits (the test bot prints doubles exactly this way)."""
	return struct.unpack(">d", bytes.fromhex(h))[0]


def parse(text):
	"""MI T (turn 1), the features from the first MI FX line (a champion prints them from the draft memory), the other MI lines."""
	T, F, other = None, {}, []
	for l in text.splitlines():
		if l.startswith("MI T "):
			t = l.split()
			T = dict(zip(t[2::2], t[3::2]))
		elif l.startswith("MI FX ") and not F:
			t = l.split()
			F = {n: struct.unpack("<d", bytes.fromhex(t[2][16 * i:16 * i + 16]))[0] for i, n in enumerate(FT.NAMES)}  # memory order
			k = bytes.fromhex(t[4])
			other.append("MI K " + str(int.from_bytes(k, "little", signed=True)))
			other.append("MI KT " + str(int.from_bytes(bytes.fromhex(t[6]), "little", signed=True)))
		elif l.startswith("MI "):
			other.append(l)
	return T, F, other


def check_dl(n, team, M, other, dl, dlw, arche, fails, fuel):
	"""MI DL (offsets 864-999) and the fuel fields of MI R2 against tools/mapintel/dl/dl_ref.py."""
	d = [o for o in other if o.startswith("MI DL ")]
	if not d:
		fails.append(f"{n} team {team}: no MI DL line")
		return 0
	b = bytes.fromhex(d[0].split()[2])
	td = [o.split() for o in other if o.startswith("MI TD ")]
	if not td:
		fails.append(f"{n} team {team}: no MI TD line")
		return 0
	t = td[0]
	if t[3] == "1":
		fuel["skipped"].append(n)
		return 0
	for k in ("inputs", "open", "next", "val", "nextall"):
		fuel[k] = max(fuel[k], int(t[t.index(f"fuel_dl_{k}") + 1]))
	prev, ct = struct.unpack("<ii", b[128:136])
	got = {"opening": [x for x in b[:16] if x != 255], "next": [x for x in b[16:32] if x != 255]}
	if "opening" in dlw:
		want = dl.rank(dl.opening_scores(M, team, arche, dlw["opening"]), 16)
		if got["opening"] != want:
			fails.append(f"{n} team {team}: dl opening ranking C++ {got['opening'][:6]} != Python {want[:6]}")
	if "next" in dlw:
		C = CP.Compact(M, team)
		reach = [g for g in range(len(M.groups)) if C.dU[g] >= 0]
		want_prev = min(reach, key=lambda g: (C.dU[g], g))
		if prev != want_prev or ct != CP.pick_bodies(CP.TEST_PICKS[0])[0]:
			fails.append(f"{n} team {team}: dl next from group {prev} body {ct}, expected {want_prev}")
		else:
			bx = [CP.group_box(g) for g in M.groups]
			cand = sorted(reach, key=lambda g: (CP.box_dist(bx[prev], bx[g]), g))[:16]
			want = dl.rank(dl.next_scores(M, team, arche, dlw["next"], prev, ct, 100, [g in cand for g in range(len(M.groups))]), 16)
			if got["next"] != want:
				fails.append(f"{n} team {team}: dl next ranking C++ {got['next'][:6]} != Python {want[:6]}")
	if "values" in dlw:
		gv = struct.unpack("<12d", b[32:128])
		wv = dl.champion_values(M, team, arche, dlw["values"])
		if any(abs(x - y) > 1e-9 * max(1.0, abs(y)) for x, y in zip(gv, wv)):
			fails.append(f"{n} team {team}: dl champion values C++ {gv[:3]} != Python {wv[:3]}")
	return 1


def run_maps(bot, maps, jobs, tmp):
	man = os.path.join(tmp, "man.txt")
	with open(man, "w") as f:
		for m in maps:
			f.write(f"{ROOT}/bots/{bot} {ROOT}/bots/{bot} {m} {tmp}/{os.path.basename(m)}.repl26a\n")
	subprocess.run(["cambc", "run-batch", man, "--jobs", str(jobs), "--rounds", "2", "--release", "--color", "never"], capture_output=True, text=True)


def check_plans(n, team, M, T, other, fails, known, ftw=None):
	"""plans.h output (MI P1-P4, MI D) against compact.py for this map and team (plan 1 with the first_scores() ranking when the weights
	have it, as the test bot); returns the number of lines compared."""
	C = CP.Compact(M, team)
	picks = CP.TEST_PICKS[: max(0, min(5, M.team_size))]
	rank = EH.first_rank_py(M, team, ftw, 16) if ftw is not None else None
	bodies, plan = C.plan1(picks, rank)
	got = {}
	for o in other:
		t = o.split()
		if t[1].startswith("P") or t[1] == "D":
			got.setdefault(t[1], []).append(t[2:])
	cnt = 0
	p1 = got.get("P1", [])
	if p1 and len(p1) != len(bodies):
		fails.append(f"{n} team {team}: plan 1 has {len(p1)} bodies, Python {len(bodies)}")
	for t in p1:
		s, b = int(t[0]), int(t[1])
		want = [v for e in (plan[s] if s < len(plan) else []) for v in e]
		vals = []
		for k in range((len(t) - 2) // 3):
			vals += [int(t[2 + 3 * k]), hexf(t[3 + 3 * k]), hexf(t[4 + 3 * k])]
		if s >= len(bodies) or bodies[s] != b or [float(x) for x in vals] != [float(x) for x in want]:
			fails.append(f"{n} team {team}: plan 1 slot {s}: C++ {b} {vals[:6]} != Python {bodies[s] if s < len(bodies) else None} {want[:6]}")
		cnt += 1
	if "P2" in got:
		bank = [int(x) for x in got["P2"][0]]
		if bank != C.bank_altars():
			fails.append(f"{n} team {team}: plan 2 banks C++ {bank[:8]} != Python {C.bank_altars()[:8]}")
		band, con = C.contested()
		p3 = [int(x) for x in got.get("P3", [[]])[0]]
		if p3 != [band] + [v for c in con for v in c]:
			fails.append(f"{n} team {team}: plan 3 C++ {p3[:7]} != Python {[band] + [v for c in con for v in c][:6]}")
		p4 = got.get("P4", [[]])[0]
		if [int(x) for x in p4[:8]] != C.thresholds() or p4[8:] != ["mode", str(C.tiebreak_mode())]:
			fails.append(f"{n} team {team}: plan 4 C++ {p4} != Python {C.thresholds()} mode {C.tiebreak_mode()}")
		cnt += 3
	g = [o.split() for o in other if o.startswith("MI G ")]
	want = CP.pack(C, int(T["fp"], 16), picks, known, 255, rank).hex()
	if not g or g[0][2] != want:
		d = g[0][2] if g else ""
		diff = next((i // 2 for i in range(0, min(len(d), len(want)), 2) if d[i:i + 2] != want[i:i + 2]), -1)
		fails.append(f"{n} team {team}: draft-memory block read back {'none' if not g else d[:16] + '...'} differs from compact.pack (first byte {diff})")
	cnt += 1
	return cnt


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--maps", default="maps/official/*.map26a")
	ap.add_argument("--perturbed", type=int, default=12)
	ap.add_argument("--jobs", type=int, default=4)
	ap.add_argument("--sdk", default="")
	ap.add_argument("--dl-weights", default="experiments/results/mapintel/dl_model/dl_weights.json")
	a = ap.parse_args()
	fails = []
	if a.sdk:
		# compile check against another SDK: a scratch project with that sdk/ and the repository's cmake glue
		tmp = tempfile.mkdtemp(prefix="mi_sdk_")
		shutil.copytree(a.sdk, os.path.join(tmp, "sdk"))
		shutil.copytree(os.path.join(ROOT, "cmake"), os.path.join(tmp, "cmake"))
		os.makedirs(os.path.join(tmp, "bots", "t", "src"))
		shutil.copy(os.path.join(ROOT, "tools/mapintel/cpp/test/main.cpp"), os.path.join(tmp, "bots", "t", "src", "main.cpp"))
		shutil.copytree(os.path.join(ROOT, "tools/mapintel/cpp/mapintel"), os.path.join(tmp, "bots", "t", "src", "mapintel"))
		shutil.copy(os.path.join(ROOT, "cambc.toml"), tmp)
		r = subprocess.run(["cambc", "build", "t"], cwd=tmp, capture_output=True, text=True)
		print(f"build against {a.sdk}: {'ok' if r.returncode == 0 else 'FAILED'}")
		if r.returncode != 0:
			print((r.stdout + r.stderr)[-3000:])
			sys.exit(1)
		return
	bot = build()
	fps = {}
	for line in open(os.path.join(ROOT, "experiments/results/mapintel/dump/fingerprints.txt")):
		n, fp, ts = line.split()
		fps[n] = fp
	table = None
	kn = os.path.join(ROOT, "tools/mapintel/cpp/mapintel/known_maps.h")
	if os.path.exists(kn):
		table = [l.split('"')[1] for l in open(kn) if "/* map " in l and '"' in l]
	weights, arche, nmw, ftw = None, None, 0, None
	if os.path.exists(os.path.join(ROOT, "tools/mapintel/cpp/mapintel/model_weights.h")):
		arche = json.load(open(os.path.join(ROOT, "maps/catalog/archetypes.json")))
		wd = os.path.join(ROOT, "experiments/results/mapintel/draft_model")
		wp = next((os.path.join(wd, f) for f in ("weights_sim.json", "weights.json") if os.path.exists(os.path.join(wd, f))), None)  # export_headers.py's choice
		weights = json.load(open(wp)) if wp else {}
		fp_ = os.path.join(ROOT, "experiments/results/mapintel/first_targets/weights.json")
		ftw = json.load(open(fp_)) if os.path.exists(fp_) and "MAPINTEL_FIRST_SCORES" in open(os.path.join(ROOT, "tools/mapintel/cpp/mapintel/model_weights.h")).read() else None
	dl, dlw = None, None
	dlh = os.path.join(ROOT, "tools/mapintel/cpp/mapintel/dl_weights.h")
	if os.path.exists(dlh):
		sys.path.insert(0, os.path.join(ROOT, "tools/mapintel/dl"))
		import dl_ref as dl  # noqa: E402
		wp = os.path.join(ROOT, a.dl_weights)
		sha = next((l.split()[3] for l in open(dlh) if l.startswith("// json sha256 ")), "")
		if not os.path.exists(wp) or hashlib.sha256(open(wp, "rb").read()).hexdigest() != sha:
			sys.exit(f"dl_weights.h was generated from another json than {wp} (sha256 {sha[:12]}): pass --dl-weights")
		dlw = {k: m for k, m in json.load(open(wp))["models"].items() if m.get("export")}
	ndl, dlfuel = 0, {"inputs": 0, "open": 0, "next": 0, "val": 0, "nextall": 0, "skipped": []}
	maps = sorted(glob.glob(os.path.join(ROOT, a.maps)))
	tmp = tempfile.mkdtemp(prefix="mi_test_")
	run_maps(bot, maps, a.jobs, tmp)
	worst = {"view": 0, "fp": 0, "feat": 0, "base": 0, "row": 0, "first_turn": 0, "rows": 0, "plan1": 0, "turn3_left_min": 10 ** 9,
			 "later_left_min": 10 ** 9, "later_plan": 0}
	per_map = []
	nplan, ngame = 0, 0
	nfeat = 0
	for m in maps:
		n = os.path.splitext(os.path.basename(m))[0]
		rp = os.path.join(tmp, os.path.basename(m) + ".repl26a")
		M = mapdata.load(n)
		for team, f in ((0, "team-a.stdout"), (1, "team-b.stdout")):
			T, F, other = parse(member(rp, f) if os.path.exists(rp) else "")
			if T is None:
				fails.append(f"{n} team {team}: no test output")
				continue
			errs = [o for o in other if o.startswith("MI E")]
			if errs:
				fails.append(f"{n} team {team}: exceptions {errs[:3]}")
			if T["fp"] != fps.get(n):
				fails.append(f"{n}: fingerprint {T['fp']} != dump {fps.get(n)}")
			idx = -1
			if table is not None:
				k = [o for o in other if o.startswith("MI K")]
				idx = int(k[0].split()[2]) if k else -2
				if idx < 0 or table[idx] != n:
					fails.append(f"{n}: table lookup gave {idx}")
			if table is not None:
				kt = [o for o in other if o.startswith("MI KT")]
				if not kt or int(kt[0].split()[2]) != team:
					fails.append(f"{n} team {team}: known_team gave {kt[0].split()[2] if kt else None}")
			if weights is not None:
				mw = [o.split()[2] for o in other if o.startswith("MI MW")]
				z = EH.zfeat_py(FT.compute(M, team), arche)
				want_a, want_v = EH.archetype_py(z, arche), EH.champion_values_py(z, weights)
				if not mw:
					fails.append(f"{n} team {team}: no MI MW line")
				else:
					b = bytes.fromhex(mw[0])
					got_a = int.from_bytes(b[:4], "little", signed=True)
					got_v = struct.unpack("<12d", b[4:100])
					if got_a != want_a or (team == 0 and got_a != arche["labels"][n]):
						fails.append(f"{n} team {team}: archetype C++ {got_a} Python {want_a} label {arche['labels'][n]}")
					if any(abs(x - y) > 1e-9 * max(1.0, abs(y)) for x, y in zip(got_v, want_v)):
						fails.append(f"{n} team {team}: champion values C++ {got_v[:3]} != Python {want_v[:3]}")
					if ftw is not None:
						rk = [b_ for b_ in bytes.fromhex([o for o in other if o.startswith("MI MW")][0].split()[4]) if b_ != 255]
						want_r = EH.first_rank_py(M, team, ftw, 16)
						if rk != want_r:
							fails.append(f"{n} team {team}: first_scores ranking C++ {rk[:6]} != Python {want_r[:6]}")
					nmw += 1
			if dlw is not None:
				ndl += check_dl(n, team, M, other, dl, dlw, arche, fails, dlfuel)
			py = FT.compute(M, team)
			for i, name in enumerate(FT.NAMES):
				c = F.get(name)
				if c is None or abs(c - py[i]) > 1e-9 * max(1.0, abs(py[i])):
					fails.append(f"{n} team {team}: feature {name} C++ {c} != Python {py[i]}")
				nfeat += 1
			nplan += check_plans(n, team, M, T, other, fails, table is not None and idx >= 0, ftw)
			g = [o for o in other if o.startswith("MI G ")]
			if not g:
				fails.append(f"{n} team {team}: no champion read the block back")
			for o in g:
				t_ = o.split()
				if t_[2] != g[0].split()[2] or t_[4] != "183":
					fails.append(f"{n} team {team}: champions read different blocks or prefix {t_[4]} != 183 (the 4-byte write)")
					break
			ngame += len(g)
			parts = ("view", "fp", "feat", "base", "row")
			for k_ in parts:
				worst[k_] = max(worst[k_], int(T.get("fuel_" + k_, 0)))
			ft = sum(int(T.get("fuel_" + k_, 0)) for k_ in parts)
			worst["first_turn"] = max(worst["first_turn"], ft)
			for o in other:
				if o.startswith("MI R2 "):
					worst["row2"] = max(worst.get("row2", 0), int(o.split()[3]))
			r3 = [o.split() for o in other if o.startswith("MI R ")]
			if not r3:
				fails.append(f"{n} team {team}: no turn-3 line (plan 1)")
			for t_ in r3:
				worst["rows"] = max(worst["rows"], int(t_[3]))
				worst["plan1"] = max(worst["plan1"], int(t_[5]))
				worst["pack"] = max(worst.get("pack", 0), int(t_[9]))
				worst["turn3_left_min"] = min(worst["turn3_left_min"], int(t_[7]) - int(t_[9]))
			if team == 0:
				per_map.append((ft, n, {k_: int(T.get("fuel_" + k_, 0)) for k_ in parts}, r3[0][3:6:2] if r3 else None))
			for o in other:
				if o.startswith("MI L"):
					t_ = o.split()
					worst["later_left_min"] = min(worst["later_left_min"], int(t_[3]))
					worst["later_plan"] = max(worst["later_plan"], int(t_[5]))
	print(f"official maps: {len(maps)} x 2 teams, {nfeat} feature values and {nplan} plan lines compared, {ngame} champion read-backs"
		  + (f", table lookups {'checked' if table is not None else 'not generated'}, model_weights checked on {nmw}" if weights is not None else ""))
	print(f"fuel, first draft turn (limit 1,000,000): max view {worst['view']}, fingerprint {worst['fp']}, features {worst['feat']}, "
		  f"plans 2-4 {worst['base']}, first pick's rows {worst['row']}; worst total {worst['first_turn']}")
	print(f"fuel, turn 2 (limit 100,000): second pick's rows {worst.get('row2', 0)}")
	print(f"fuel, turn 3 (limit 100,000): rows of the remaining picks {worst['rows']}, plan 1 {worst['plan1']}, pack + write {worst.get('pack', 0)}, least left {worst['turn3_left_min']}; "
		  f"later turns: plan 1 from cached rows {worst['later_plan']}, least left {worst['later_left_min']}")
	if dlw is not None:
		print(f"dl_weights.h ({', '.join(dlw)}): checked on {ndl} map-teams; max fuel (measured in the first draft turn): inputs {dlfuel['inputs']}, "
			  f"opening {dlfuel['open']}, next target (one call on 16 candidates, cached inputs: a game turn has 100,000) {dlfuel['next']} "
			  f"(all groups {dlfuel['nextall']}), champion values {dlfuel['val']}"
			  + (f"; not measured on {sorted(set(dlfuel['skipped']))} (under 350,000 left in turn 1)" if dlfuel["skipped"] else ""))
		if dlfuel["next"] > 50_000:
			fails.append("dl_next_scores on 16 candidates needs more than 50,000 fuel a call (half a game turn)")
	per_map.sort(reverse=True)
	print("heaviest first turns: " + "; ".join(f"{n} {ft} ({', '.join(f'{k} {v}' for k, v in d.items())})" for ft, n, d, _ in per_map[:5]))
	if worst["first_turn"] > 1_000_000:
		fails.append("first draft turn over 1M fuel")
	# unknown maps: perturbed copies
	if a.perturbed:
		pdir = tempfile.mkdtemp(prefix="mi_pert_")
		pm = []
		for i, m in enumerate(maps[: a.perturbed]):
			out = os.path.join(pdir, f"zz_pert{i:02d}_{os.path.basename(m)}")
			r = subprocess.run(["node", os.path.join(ROOT, "tools/mapgen/perturb.mjs"), m, out, "--seed", str(17 + i)], capture_output=True, text=True)
			if r.returncode == 0 and os.path.exists(out):
				pm.append(out)
		dump = tempfile.mkdtemp(prefix="mi_pdump_")
		subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools/mapintel/dump_maps.py"), "--maps", ",".join(pm), "--out", dump],
					   capture_output=True, text=True)
		run_maps(bot, pm, a.jobs, tmp)
		unknown = 0
		for m in pm:
			n = os.path.splitext(os.path.basename(m))[0]
			T, F, other = parse(member(os.path.join(tmp, os.path.basename(m) + ".repl26a"), "team-a.stdout"))
			if T is None:
				fails.append(f"{n}: no output")
				continue
			if T["fp"] in fps.values():
				fails.append(f"{n}: a perturbed map matches an official fingerprint")
			if table is not None and int(T["table"]):
				fails.append(f"{n}: a perturbed map was found in the table")
			unknown += 1
			if os.path.exists(os.path.join(dump, n + ".txt")):
				py = FT.compute(mapdata.load(n, dump), 0)
				for i, name in enumerate(FT.NAMES):
					if abs(F.get(name, 1e99) - py[i]) > 1e-9 * max(1.0, abs(py[i])):
						fails.append(f"{n}: feature {name} C++ {F.get(name)} != Python {py[i]}")
		print(f"perturbed maps: {len(pm)} made, {unknown} took the unknown-map path")
	print("FAILURES:\n  " + "\n  ".join(fails[:40]) if fails else "all checks passed")
	sys.exit(1 if fails else 0)


if __name__ == "__main__":
	main()
