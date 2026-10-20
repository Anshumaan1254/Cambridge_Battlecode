#!/bin/bash
# Session 13 checkpoint: commit and push the agents' and coordinator's result files (never bots/, never sources in progress).
# Usage: ckpt.sh [message]   (serialised with flock so the loop and manual calls never collide)
cd /home/user/Cambridge_Battlecode || exit 1
exec 9>/tmp/claude-0/-home-user-Cambridge-Battlecode/814bb573-3b54-57d0-a5c4-7b41cf5c5bd2/scratchpad/git.lock
flock 9
git add AGENTS.md SUGGESTIONS.md ISSUES.md README.md docs experiments/wip/x_zone* experiments/wip/x_s13* experiments/wip/x_ml2* experiments/wip/x_es13* experiments/wip/x_fin* experiments/wip/x_ml3* experiments/wip/x_dc* experiments/wip/x_tr* experiments/wip/x_es15* experiments/wip/x_mt2* experiments/wip/x_esx15* tools/ml experiments/wip/AGENT_RULES.md experiments/results/ledger experiments/results/ledger_v3 experiments/ladder_oct19b tools/strategy_v2 tools/*.py tools/*.sh docs/strategy_v2 2>/dev/null
if ! git diff --cached --quiet; then
	git commit -qm "${1:-Session 13 checkpoint: agent notes, patches and ledger rows}

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LrMqKD9UD4uJ2DqLYgsxzF"
	for i in 1 2 3 4; do git pull -q --no-rebase origin main && git push -q origin main && break; sleep $((2**i)); done
fi
