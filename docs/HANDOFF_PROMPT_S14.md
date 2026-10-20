You are taking over a Cambridge Battlecode 2026a (CAMBC) C++ bot in the repository Cambridge_Battlecode (single branch `main`).

Read `AGENTS.md` first: start with §S14 (the handoff written for you), then §S13-GOD and §S13. It holds everything measured so far,
what failed, the tools, and the plan.

Your task, in priority order:
1. We lose almost every game to the team Nyx after patch 3.0, on the new maps and on the changed official maps (Nyx won 17 of 20; replays in
   `experiments/nyx_oct20/`, maps extracted to `maps/nyx_new/` and `maps/comp30/`). Study those games, find out what Nyx does better
   (drafting, opening, farming, fights, shopping, recalls), reverse-engineer its good strategies, and build a new GOD that beats it.
   Loopholes, exploits and reverse engineering are allowed.
2. The bot's name and level is GOD. It must use every patch-3.0 change (`docs/patch_notes/week2_20261020.txt`) and be better than GOD v2
   (`submissions/god.zip`) and legend_m15.
3. Try `cambc maps pull` for the new official maps; if the network blocks it, tell me once and use the maps taken from the replays.

Rules:
- Set up a new container with `tools/setup_session.sh` (cambc 3.0.1).
- No hardcoded map strategy: every plan and draft choice comes from map features at runtime. Record anything hardcoded in ISSUES.md and
  ideas that did not measure better in SUGGESTIONS.md.
- Every change gets a switch in params.h and an A/B test through `tools/ledger.py` (map names must be unique). Ship a zip only when it is
  measured better (head-to-head vs GOD v2 and vs the proxies on `maps/nyx_new` + `maps/comp30`); push the zip first, then continue.
- Use few subagents and few parallel background tasks. When you delegate: Fable subagents for the main, heavy tasks; Opus for smaller ones;
  then Sonnet; Haiku only for the smallest (documentation, moving files). Do the core analysis yourself.
- Commit and push to `main` at every step (`git pull --no-rebase` first, never force, no pull request). Add a checkpoint to AGENTS.md §S14.8
  at every step so the next session can resume.
- Never use `pkill -f` or `killall`; kill by PID. Do not stop to ask me questions: decide, write the decision down, continue.
- Tell me when a better GOD zip is ready and what it beats.
