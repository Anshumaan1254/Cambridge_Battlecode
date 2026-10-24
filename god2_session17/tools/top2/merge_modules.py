#!/usr/bin/env python3
"""3-way merge of module bot copies onto their common base (session 17 god2 modules).

    python tools/top2/merge_modules.py OUT_BOT BASE_BOT MOD_BOT [MOD_BOT ...]

Every module copy was made from bots/BASE_BOT/src and changed independently. For each file, start from the base and fold in each
module's version with `git merge-file` (base = the original); params.h uses --union, since every module appends its own block at the end of
struct Params (adjacent insertions). Files are compared and written with LF line endings. Conflicts in other files are left as conflict
markers and listed; the exit code is the number of files with conflicts."""
import os, shutil, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def read(path):
    with open(path, "rb") as f:
        return f.read().replace(b"\r\n", b"\n")


def main():
    out, base, mods = sys.argv[1], sys.argv[2], sys.argv[3:]
    bdir = os.path.join(ROOT, "bots", base, "src")
    odir = os.path.join(ROOT, "bots", out, "src")
    if os.path.exists(os.path.join(ROOT, "bots", out)):
        shutil.rmtree(os.path.join(ROOT, "bots", out))
    os.makedirs(odir)
    shutil.copy(os.path.join(ROOT, "bots", base, ".gitignore"), os.path.join(ROOT, "bots", out, ".gitignore"))
    names = set(os.listdir(bdir))
    for m in mods:
        names |= set(os.listdir(os.path.join(ROOT, "bots", m, "src")))
    tmp = tempfile.mkdtemp()
    bad = []
    for n in sorted(names):
        bpath = os.path.join(bdir, n)
        b = read(bpath) if os.path.exists(bpath) else b""
        cur = b
        touched = []
        for m in mods:
            mpath = os.path.join(ROOT, "bots", m, "src", n)
            if not os.path.exists(mpath):
                continue
            mv = read(mpath)
            if mv == b:
                continue
            touched.append(m)
            if cur == b:
                cur = mv
                continue
            paths = []
            for tag, data in (("cur", cur), ("base", b), ("mod", mv)):
                p = os.path.join(tmp, f"{tag}_{n}")
                with open(p, "wb") as f:
                    f.write(data)
                paths.append(p)
            args = ["git", "merge-file", "-p"] + (["--union"] if n == "params.h" else []) + ["-L", "merged", "-L", "base", "-L", m] + paths
            r = subprocess.run(args, capture_output=True)
            cur = r.stdout
            if r.returncode != 0:
                bad.append((n, m, r.returncode))
        with open(os.path.join(odir, n), "wb") as f:
            f.write(cur)
        if touched:
            print(f"{n}: {', '.join(touched)}")
    for n, m, c in bad:
        print(f"CONFLICT {n} merging {m}: {c} region(s)")
    shutil.rmtree(tmp)
    sys.exit(len({n for n, _, _ in bad}))


if __name__ == "__main__":
    main()
