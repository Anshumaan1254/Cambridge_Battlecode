# Run a node analysis script over replay files with N workers (resumes: skips files already in OUT):
#   python tools/live/par.py N OUT.jsonl SCRIPT [ARGS...] -- FILES...
# Run a node analysis script over replay files with N workers: python par.py N OUT.jsonl SCRIPT [ARGS...] -- FILES...
import subprocess, sys, os, concurrent.futures as cf
n = int(sys.argv[1]); out = sys.argv[2]; k = sys.argv.index('--')
cmd = sys.argv[3:k]; files = sys.argv[k + 1:]
done = set()
if os.path.exists(out):
    import json
    for l in open(out, encoding='utf-8'):
        try: done.add(json.loads(l)['file'])
        except Exception: pass
files = [f for f in files if os.path.basename(f) not in done]
env = dict(os.environ, CAMBC_CACHE='C:/Users/Anjali Gupta/AppData/Local/cambc/assets')
def run(f):
    r = subprocess.run(['node'] + cmd + [f], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
    return r.stdout
with cf.ThreadPoolExecutor(n) as ex, open(out, 'a', encoding='utf-8') as fo:
    for s in ex.map(run, files):
        if s.strip():
            fo.write(s if s.endswith('\n') else s + '\n'); fo.flush()
print('done', len(files))
