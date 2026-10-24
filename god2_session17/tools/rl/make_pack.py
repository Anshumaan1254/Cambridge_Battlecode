#!/usr/bin/env python3
"""Build the self-contained Linux package for the RL trainer: python tools/rl/make_pack.py [--base bb4] [--out FILE]
Writes rl_pack_<date>.zip (top folder cambc_rl/) with the cambc project files, the 40 ladder maps, the bot source, the
trainer, its knowledge file, the README and the run_rl.sh / stop_rl.sh launchers (executable). Text files get LF line
endings."""
import argparse
import glob
import os
import time
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TEXT = (".py", ".md", ".json", ".h", ".hpp", ".cpp", ".c", ".toml", ".txt", ".cmake", ".mjs", ".sh")


def add(zf, path, arc):
    data = open(path, "rb").read()
    if path.endswith(TEXT) or os.path.basename(path) == "CMakeLists.txt":
        data = data.replace(b"\r\n", b"\n")
    zi = zipfile.ZipInfo(arc, date_time=time.localtime()[:6])
    zi.create_system = 3  # unix: unzip keeps the permission bits below
    zi.external_attr = ((0o755 if arc.endswith((".py", ".sh")) else 0o644) | 0o100000) << 16
    zi.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(zi, data)


def add_tree(tf, d, arc, skip=(".cambc", "build", "__pycache__", "compile_commands.json")):
    for base, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if x not in skip]
        for f in files:
            if f in skip or f.endswith(".pyc"):
                continue
            p = os.path.join(base, f)
            add(tf, p, arc + "/" + os.path.relpath(p, d).replace(os.sep, "/"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="bb4")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = a.out or os.path.join(ROOT, f"rl_pack_{time.strftime('%Y%m%d')}.zip")
    top = "cambc_rl"
    with zipfile.ZipFile(out, "w") as tf:
        add(tf, os.path.join(ROOT, "cambc.toml"), f"{top}/cambc.toml")
        add_tree(tf, os.path.join(ROOT, "cmake"), f"{top}/cmake")
        add_tree(tf, os.path.join(ROOT, "sdk"), f"{top}/sdk")
        maps = sorted(glob.glob(os.path.join(ROOT, "maps", "0*.map26a")))
        for m in maps:
            add(tf, m, f"{top}/maps/{os.path.basename(m)}")
        add_tree(tf, os.path.join(ROOT, "bots", a.base, "src"), f"{top}/bots/{a.base}/src")
        for f in ("train_rl.py", "knowledge.json", "make_knowledge.py"):
            add(tf, os.path.join(ROOT, "tools", "rl", f), f"{top}/tools/rl/{f}")
        add(tf, os.path.join(ROOT, "tools", "rl", "RL_README.md"), f"{top}/README.md")
        for f in ("run_rl.sh", "stop_rl.sh"):
            add(tf, os.path.join(ROOT, "tools", "rl", f), f"{top}/{f}")
    print(f"wrote {out} ({os.path.getsize(out) / 1e6:.1f} MB): {len(maps)} maps, bots/{a.base}, trainer, knowledge, README, launchers")


if __name__ == "__main__":
    main()
