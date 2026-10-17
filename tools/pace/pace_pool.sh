#!/bin/bash
# usage: full.sh BOT...  : pace vs idle on the 56-map pool, summary line per bot to /tmp/pace/full.log, per-map to /tmp/pace/res/BOT.txt
cd /home/user/Cambridge_Battlecode
mkdir -p /tmp/pace/res
for bot in "$@"; do
  rm -rf /tmp/pace/outf/$bot
  python3 tools/bench.py $bot idle --maps 'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a' --jobs 2 --out /tmp/pace/outf/$bot --quiet >/tmp/pace/outf_$bot.log 2>&1
  python3 tools/pace/pace_sum.py /tmp/pace/outf/$bot > /tmp/pace/res/$bot.txt
  echo "$bot $(tail -1 /tmp/pace/res/$bot.txt)" >> /tmp/pace/full.log
done
