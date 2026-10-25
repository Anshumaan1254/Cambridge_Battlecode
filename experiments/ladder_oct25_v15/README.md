# GOD v15 (website v71) on the ladder, Oct 25 10:37-11:45 UTC

v15 went live at ~10:37 UTC (the ship commit is 10:36 UTC); the user ran one group against Intercontinental Fish (10:38) and one against
Mite (10:41): **0-10**. Over all 215 games since 10:37 (ranked + unranked groups other teams queued against us) v15 went 108-107.

Files:
- `matches_me.jsonl`: our match list (ranked + unranked, from Oct 24 16:00 UTC; `cambc matches list --team me`), `ladder_now.json` the top 40.
- `replays/` the 10 IC / Mite games (`ic_*`, `mite_*`); `sides.json` (team index of us, results); `gapx.jsonl` session 17's gap extractor
  on them, `gap_tables.txt` its tables (`gapx_agg_v15.py`).
- `cohes.py` (allies within 5 / outnumbered shares), `initiator.py` (who struck first before each death), `hitters.py` (bodies and
  rounds per camp kill), `v15sum.py` (wins vs losses from `cambc matches summary` JSON).

Headline (per game, us / them, 10 games): banked 269 / 1,017; deaths 11.7 / 2.5 (we are dead 16-32% of the body-rounds, they 0-8%);
farm share with an enemy within 8 3% / 20% (walk 80% / 47%); A-B-A walks 42 / 14 per body; captures before r600 7 / 21 a game; **IC farms
a group with 3 bodies (median) and stays together (2.2 allies within 5 before r300, us 1.0)**; item shard equivalents r400 31 / 81.
Of our 117 deaths 52 came after the enemy struck first, 30 after we did, 24 the same round.

**Mite's bait**: every Mite body starts a recall at the end of its turn and cancels it at the start of the next (Recall 1,100-1,200 and
Cancel 900-1,000 events a body a game; IC ~9 recalls a body). GOD v15 treats a visible enemy recalling with 20+ gems as a stuck carrier:
it posts a team OPPORTUNITY and bodies within 12 drop their farming to walk to it; the target value adds +60 for a channelling enemy.
The recall_started / recall_cancelled flags are not visible to the other team (probe `_pb17` vs `_pr17`), so GOD v17 detects the fake
by movement: a body seen recalling on consecutive rounds at different tiles.

Teams that beat IC (8 replays of IC's losses, `/tmp`): they kill first (median r187), die 0.6 times by r300 (IC 3.1) and farm 27% of
their enemy-near rounds (IC 20%).
