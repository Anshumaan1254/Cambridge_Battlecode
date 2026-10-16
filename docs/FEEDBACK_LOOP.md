# Feedback loop: play the top teams, report back, re-tune

The bot was built and tuned offline against our own sparring partners. This loop brings in the real
opponents. One round of it takes ~15 minutes of your time.

## 0. One-time setup (on your machine)

```bash
pip install cambc                 # CLI + engine + visualiser
git clone <this repo> && cd Cambridge_Battlecode
cambc init .                      # adds sdk/ and cmake/ (git-ignored); pick C++ when asked
cambc login                       # platform account, lasts 7 days
cambc maps pull                   # the official map pool into maps/
cambc build legend                # sanity check
```

If `cambc init` asks to overwrite files, keep this repo's `bots/` and `maps/`.

## 1. Check the bot on the official maps

```bash
python3 tools/bench.py legend starter-cpp --maps 'maps/*.map26a'      # should be ~100%
python3 tools/bench.py legend idle --maps 'maps/*.map26a'             # unopposed pace (avg_win_round)
```

## 2. Submit, then scrim the top teams

```bash
cambc submit legend
cambc ladder --limit 15                       # note the top teams' IDs
cambc match-groups create <TEAM_ID>           # 5 unranked matches against them (uses team quota)
cambc match-groups show <GROUP_ID>            # wait until finished
cambc match-groups download <GROUP_ID> -o matches/<team>
```

To learn what the top teams draft without spending quota:

```bash
cambc matches list --team <TEAM_ID> --limit 25          # map, teams and draft choices per match
```

## 3. Turn each match into a report

```bash
cambc matches summary <MATCH_ID> --json -o matches/<MATCH_ID>.json
python3 tools/analyze_match.py matches/<MATCH_ID>.json --us teamA     # or teamB: the side we played
python3 tools/analyze_match.py matches/*.json --brief                 # many matches at once
```

The report gives: result and pace, both drafts, the gem timeline at fixed rounds, per-champion
kills/deaths/gems/gold/damage/items, every death (round, place, killer, bag lost) and a diagnosis
line that maps to tunables in `bots/legend/src/params.h`.

To watch a replay: `cambc matches download <MATCH_ID>` then `cambc view <file>`.

## 4. What to paste back

Paste this block (one per opponent) into the chat:

```
OPPONENT: <team name>  (ladder rank #)
BOT VERSION: <git short hash of what you submitted>
RESULTS: W/L per map, e.g.  mapA W, mapB L, ...
THEIR DRAFTS: <from matches list>
<the analyze_match.py output, full for losses, --brief for wins>
WHAT I SAW IN THE REPLAY (optional): e.g. "they 3-man gank our Tavi at the mid altar around r150",
  "they never leave their half", "they lock our altar", "they rush the monolith at r600"
```

Losses are what matter most; one full loss report beats five win summaries.

## 5. What happens with your report

| Symptom in the report | Change |
|---|---|
| many deaths to champions, few kills | raise `fight_margin` / `fight_back_margin`, retreat earlier, tribute before contact |
| they win pure farming races (no deaths either side) | farming throughput: draft for the map, routing, item path; tune `gold_value`, `tribute_min`, `max_trips` |
| big bags lost on death | lower `tribute_min`, `tribute_risky`, `bag_caution` |
| deaths to camps | raise `camp_hp_reserve` / `retreat_hp` |
| their draft keeps beating ours | add their composition as a forced-draft sparring bot and re-run the composition tournament |
| a specific trick (locks, monolith, spawn-tile denial, invade timing) | code a counter, add the trick to a sparring archetype so it stays tested |

To reproduce an opponent's style locally, build an archetype from the closest parameters, e.g.:

```bash
tools/variant.sh _their_style fight_margin=0.9f deny_bonus=1.0f --define "LEGEND_DRAFT 9,8,10,4,0"
python3 tools/bench.py legend _their_style --maps 'maps/*.map26a'
```

## 6. Re-tuning on the real map pool

```bash
tools/snapshot.sh _v_ladder HEAD                  # freeze what is on the ladder now
python3 tools/tune.py --panel _v_ladder,_v1aggro  # hours; writes tune_out/best_params.json
cat tune_out/log.txt
```

Copy accepted values from `tune_out/best_params.json` into `bots/legend/src/params.h`, re-run
`tools/suite.sh legend`, then submit.
