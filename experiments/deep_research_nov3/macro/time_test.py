import sys, time, json, os
sys.path.insert(0,'/home/claude/cambridge_battlecode/experiments/top30_nov3/economy')
import econ
jobs = econ.jobs_top30()
print('econ jobs available', len(jobs))
H = econ.half_tables()
maps = {j[2] for j in jobs}
dec = os.listdir('/home/claude/cambridge_battlecode/experiments/top30_nov3/dec')
decmaps = {f.rsplit('_',1)[0] for f in dec}
print('maps in dec', len(decmaps), 'with half tables', len([m for m in decmaps if m in H]), 'missing', sorted(m for m in decmaps if m not in H)[:40])
t=time.time(); rows = econ.analyse(jobs[5]); print('econ one game s', round(time.time()-t,2), jobs[5][0][-30:])
