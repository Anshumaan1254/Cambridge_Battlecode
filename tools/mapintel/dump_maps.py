#!/usr/bin/env python3
"""Runtime dump of maps as a bot sees them (the ground truth of tools/mapintel): fingerprint, team size, spawn regions, the wall /
hole / bush / altar bitboards and the runtime camp groups, printed by the probe bot tools/mapintel/cpp/probe on its first draft turn.

    python3 -I tools/mapintel/dump_maps.py [--maps 'maps/official/*.map26a'] [--out experiments/results/mapintel/dump] [--jobs 4]

Builds bots/_mi_probe (git-ignored) from tools/mapintel/cpp/probe/main.cpp + tools/mapintel/cpp/mapintel/, plays one round of the probe
against itself on each map (`cambc run-batch --rounds 1`), and writes OUT/<map>.txt (team A's view, team B's spawn lines appended as
'MI specB ...' for a check) and OUT/fingerprints.txt (map, fingerprint, team size). Exits non-zero when a map gives no dump."""
import argparse, glob, os, shutil, subprocess, sys, tempfile, zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def build_probe(name="_mi_probe"):
	d = os.path.join(ROOT, "bots", name)
	shutil.rmtree(os.path.join(d, "src"), ignore_errors=True)
	os.makedirs(os.path.join(d, "src"), exist_ok=True)
	shutil.copy(os.path.join(ROOT, "tools/mapintel/cpp/probe/main.cpp"), os.path.join(d, "src", "main.cpp"))
	shutil.copytree(os.path.join(ROOT, "tools/mapintel/cpp/mapintel"), os.path.join(d, "src", "mapintel"))
	r = subprocess.run(["cambc", "build", name], cwd=ROOT, capture_output=True, text=True)
	if r.returncode != 0:
		sys.exit("probe build failed:\n" + r.stdout[-3000:] + r.stderr[-3000:])
	return name


def member(path, name):
	with zipfile.ZipFile(path) as z:
		for n in z.namelist():
			if n.endswith(name):
				return z.read(n).decode("utf-8", "replace").replace("\x00", "")
	return ""


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--maps", default="maps/official/*.map26a")
	ap.add_argument("--out", default="experiments/results/mapintel/dump")
	ap.add_argument("--jobs", type=int, default=4)
	a = ap.parse_args()
	maps = sorted(m for p in a.maps.split(",") for m in glob.glob(os.path.join(ROOT, p)))
	if not maps:
		sys.exit("no maps")
	probe = build_probe()
	out = os.path.join(ROOT, a.out)
	os.makedirs(out, exist_ok=True)
	tmp = tempfile.mkdtemp(prefix="mi_dump_")
	man = os.path.join(tmp, "manifest.txt")
	with open(man, "w") as f:
		for m in maps:
			n = os.path.splitext(os.path.basename(m))[0]
			f.write(f"{ROOT}/bots/{probe} {ROOT}/bots/{probe} {m} {tmp}/{n}.repl26a\n")
	subprocess.run(["cambc", "run-batch", man, "--jobs", str(a.jobs), "--rounds", "1", "--color", "never"], capture_output=True, text=True)
	fps, bad = [], []
	for m in maps:
		n = os.path.splitext(os.path.basename(m))[0]
		rp = os.path.join(tmp, n + ".repl26a")
		ta = member(rp, "team-a.stdout") if os.path.exists(rp) else ""
		tb = member(rp, "team-b.stdout") if os.path.exists(rp) else ""
		lines = [l for l in ta.splitlines() if l.startswith("MI ")]
		if not lines or lines[-1] != "MI END" or any(l.startswith("MI ERR") for l in lines):
			bad.append(n)
			continue
		lines += ["MI specB " + l[3:] for l in tb.splitlines() if l.startswith("MI fp") or l.startswith("MI spawn")]
		open(os.path.join(out, n + ".txt"), "w").write("\n".join(lines) + "\n")
		t = lines[0].split()
		fps.append(f"{n} {t[2]} {t[4]}")
	open(os.path.join(out, "fingerprints.txt"), "w").write("\n".join(fps) + "\n")
	shutil.rmtree(tmp, ignore_errors=True)
	print(f"{len(fps)} maps dumped into {a.out}" + (f"; FAILED: {', '.join(bad)}" if bad else ""))
	if bad:
		sys.exit(1)


if __name__ == "__main__":
	main()
