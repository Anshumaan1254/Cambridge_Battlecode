import sys, time, json, os
T='/home/claude/cambridge_battlecode/experiments/top30_nov3'
sys.path.insert(0, T+'/draft_bank'); sys.path.insert(0, T+'/objectives'); sys.path.insert(0, T+'/economy')
import extract_all as DB
import extract_obj as OB, common as C
import econ
gs = DB.load_games('top30'); print('db games', len(gs))
tg = C.top_games(); print('obj games', len(tg))
key = gs[40]['mid']
t=time.time(); DB.analyse(gs[40]); print('db s', round(time.time()-t,2), gs[40]['map'])
g2 = [g for g in tg if g['mid']==key][0]
t=time.time(); OB.analyse(g2); print('obj s', round(time.time()-t,2))
j = [j for j in econ.jobs_top30() if key[:8] in j[0]][0]
t=time.time(); econ.analyse(j); print('econ s', round(time.time()-t,2))
