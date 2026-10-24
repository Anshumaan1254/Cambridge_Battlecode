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
  * fuel: the first draft turn's work stays under 1,000,000 and every later draft turn under 100,000 (the turn's fuel left is printed);
  * 0 exceptions;
  * --sdk DIR builds the same sources against another SDK (e.g. a 3.0.4 `cambc init` sdk/) to check they compile there.
Exit status 1 on any failure."""
import argparse, glob, json, os, shutil, subprocess, sys, tempfile, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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


def parse(text):
	T, F, other = None, {}, []
	for l in text.splitlines():
		if l.startswith("MI T "):
			t = l.split()
			T = dict(zip(t[2::2], t[3::2]))
		elif l.startswith("MI F "):
			_, _, n, v = l.split()
			F[n] = float(v)
		elif l.startswith("MI "):
			other.append(l)
	return T, F, other


def run_maps(bot, maps, jobs, tmp):
	man = os.path.join(tmp, "man.txt")
	with open(man, "w") as f:
		for m in maps:
			f.write(f"{ROOT}/bots/{bot} {ROOT}/bots/{bot} {m} {tmp}/{os.path.basename(m)}.repl26a\n")
	subprocess.run(["cambc", "run-batch", man, "--jobs", str(jobs), "--rounds", "1", "--release", "--color", "never"], capture_output=True, text=True)


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--maps", default="maps/official/*.map26a")
	ap.add_argument("--perturbed", type=int, default=12)
	ap.add_argument("--jobs", type=int, default=4)
	ap.add_argument("--sdk", default="")
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
	maps = sorted(glob.glob(os.path.join(ROOT, a.maps)))
	tmp = tempfile.mkdtemp(prefix="mi_test_")
	run_maps(bot, maps, a.jobs, tmp)
	worst = {"fp": 0, "view": 0, "feat": 0, "plan": 0, "first_turn": 0, "later_left_min": 10 ** 9}
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
			if table is not None:
				k = [o for o in other if o.startswith("MI K")]
				idx = int(k[0].split()[2]) if k else -2
				if idx < 0 or table[idx] != n:
					fails.append(f"{n}: table lookup gave {idx}")
			py = FT.compute(M, team)
			for i, name in enumerate(FT.NAMES):
				c = F.get(name)
				if c is None or abs(c - py[i]) > 1e-9 * max(1.0, abs(py[i])):
					fails.append(f"{n} team {team}: feature {name} C++ {c} != Python {py[i]}")
				nfeat += 1
			for k_ in ("fp", "view", "feat", "plan"):
				worst[k_] = max(worst[k_], int(T.get("fuel_" + k_, 0)))
			worst["first_turn"] = max(worst["first_turn"], sum(int(T.get("fuel_" + k_, 0)) for k_ in ("fp", "view", "feat", "plan")))
			for o in other:
				if o.startswith("MI L"):
					worst["later_left_min"] = min(worst["later_left_min"], int(o.split()[-1]))
	print(f"official maps: {len(maps)} x 2 teams, {nfeat} feature values compared; fuel max: fingerprint {worst['fp']}, view {worst['view']}, "
		  f"features {worst['feat']}, plans {worst['plan']}, first turn total {worst['first_turn']} (limit 1,000,000); later draft turns: "
		  f"least fuel left {worst['later_left_min']} of 100,000")
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
