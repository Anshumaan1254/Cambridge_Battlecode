# verify_items runner: python tools/top2/verify_items/run.py N OUT.jsonl LIST.txt SCRIPT.mjs [ARGS...]
# Runs `node SCRIPT ARGS FILE` for every file in LIST (one path per line) with N workers; resumes (skips files already in OUT).
import subprocess, sys, os, json, concurrent.futures as cf
n = int(sys.argv[1]); out = sys.argv[2]; lst = sys.argv[3]; cmd = sys.argv[4:]
files = [l.strip() for l in open(lst, encoding='utf-8') if l.strip()]
done = set()
if os.path.exists(out):
    for l in open(out, encoding='utf-8'):
        try:
            j = json.loads(l)
            if 'err' not in j: done.add(j['file'])
        except Exception: pass
files = [f for f in files if os.path.basename(f) not in done]
env = dict(os.environ, CAMBC_CACHE='C:/Users/Anjali Gupta/AppData/Local/cambc/assets')
def run(f):
    r = subprocess.run(['node'] + cmd + [f], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
    return r.stdout if r.stdout.strip() else json.dumps({'file': os.path.basename(f), 'err': r.stderr[-300:]}) + '\n'
with cf.ThreadPoolExecutor(n) as ex, open(out, 'a', encoding='utf-8') as fo:
    for s in ex.map(run, files):
        fo.write(s if s.endswith('\n') else s + '\n'); fo.flush()
print('done', len(files))
