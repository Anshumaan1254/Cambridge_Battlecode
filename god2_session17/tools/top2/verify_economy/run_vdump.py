# Run vdump.mjs over the distinct replay list with N workers (resumes by output log): python run_vdump.py N
import subprocess, sys, os, json, concurrent.futures as cf
n = int(sys.argv[1]); base = 'C:/battlecode/cache/vecon'
files = [l.strip().replace(chr(92), '/') for l in open(base + '/files.txt') if l.strip()]
log = base + '/vdump_log.jsonl'; done = set()
if os.path.exists(log):
    for l in open(log, encoding='utf-8'):
        try:
            j = json.loads(l)
            if j.get('ok'): done.add(j['file'])
        except Exception: pass
files = [f for f in files if os.path.basename(f) not in done]
env = dict(os.environ, CAMBC_CACHE='C:/Users/Anjali Gupta/AppData/Local/cambc/assets')
here = os.path.dirname(os.path.abspath(__file__))
def run(f):
    r = subprocess.run(['node', os.path.join(here, 'vdump.mjs'), base + '/d', f], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
    return r.stdout or json.dumps({'file': os.path.basename(f), 'ok': 0, 'err': r.stderr[-300:]})
with cf.ThreadPoolExecutor(n) as ex, open(log, 'a', encoding='utf-8') as fo:
    for s in ex.map(run, files):
        fo.write(s if s.endswith('\n') else s + '\n'); fo.flush()
print('done', len(files))
