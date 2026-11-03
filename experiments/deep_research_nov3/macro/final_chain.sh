cd /home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro
until grep -q 'econ_db done' ext/econ_db.log; do sleep 20; done
nice -n 19 python3 -I fp.py && nice -n 19 python3 -I mk_table.py >/dev/null && nice -n 19 python3 -I mclass.py
for f in fp_out.txt table.md fp_team.json fp_sides.jsonl fp_corr.json; do cp $f ${f%.*}_full.${f##*.}; done
date -u +%H:%M:%S
