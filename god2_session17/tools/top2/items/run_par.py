# Run a node script over many files with N workers, reading the file list from a text file (one path per line; avoids the
# Windows command-line limit of tools/live/par.py). Resumes: skips files whose basename is already in OUT ('file' key).
#   python tools/top2/items/run_par.py N OUT.jsonl LIST.txt SCRIPT [ARGS...]
import subprocess, sys, os, json, concurrent.futures as cf
n = int(sys.argv[1]); out = sys.argv[2]; lst = sys.argv[3]; cmd = sys.argv[4:]
files = [l.strip() for l in open(lst, encoding='utf-8') if l.strip()]
done = set()
if os.path.exists(out):
    for l in open(out, encoding='utf-8'):
        try: done.add(json.loads(l)['file'])
        except Exception: pass
files = [f for f in files if os.path.basename(f) not in done]
env = dict(os.environ, CAMBC_CACHE='C:/Users/Anjali Gupta/AppData/Local/cambc/assets')
def run(f):
    r = subprocess.run(['node'] + cmd + [f], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
    if r.stderr.strip(): sys.stderr.write(r.stderr[-500:] + '\n')
    return r.stdout
with cf.ThreadPoolExecutor(n) as ex, open(out, 'a', encoding='utf-8') as fo:
    for s in ex.map(run, files):
        if s.strip():
            fo.write(s if s.endswith('\n') else s + '\n'); fo.flush()
print('done', len(files))
