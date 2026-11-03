#!/bin/bash
# sequential downloader (the platform allows one download at a time, HTTP 409 otherwise); retries
cd /home/claude/cambridge_battlecode/experiments/deep_research_nov3/v95
while read id map; do
  [ -s replays/$id.repl26a ] && continue
  for t in 1 2 3 4; do
    timeout 180 cambc matches download $id -o replays/$id.part >/dev/null 2>>dl.err && [ -s replays/$id.part ] && mv replays/$id.part replays/$id.repl26a && break
    sleep 3
  done
  echo "$(date -u +%H:%M:%S) $id" >> dl_progress.log
done < $1
echo DLDONE >> dl_progress.log
