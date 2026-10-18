#!/bin/bash
# usage: tools/pace17.sh BOT [JOBS] [MAPS]   unopposed pace (vs idle, both sides) on the 17 official maps (or MAPS glob).
# Rounds to 1000 gems per map (2000 = not reached) and the mean, in /tmp/ev/p_BOT.txt. The code-family-independent
# farming measure: every sparring bot is our own code, the real ladder is far stronger (session 6 report).
cd "$(dirname "$0")/.."
bot=$1; jobs=${2:-2}; maps=${3:-maps/comp/*.map26a}
mkdir -p /tmp/ev; rm -rf /tmp/ev/pace_$bot
python3 tools/bench.py $bot idle --maps "$maps" --jobs $jobs --out /tmp/ev/pace_$bot --quiet > /tmp/ev/pace_$bot.log 2>&1
python3 tools/pace/pace_sum.py /tmp/ev/pace_$bot > /tmp/ev/p_$bot.txt
echo "$bot $(tail -1 /tmp/ev/p_$bot.txt)"
