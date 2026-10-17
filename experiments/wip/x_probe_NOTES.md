# x_probe: Session 5 engine-rule probes (cambc 2.2.5)

Agent `probe`, 2026-10-17. Verified five rules the endgame and fights depend on. Results table: `docs/ENGINE_FACTS.md`, section
"Session 5 probes (cambc 2.2.5)". Nothing in `bots/legend` was changed.

## Answers (short)
1. **A stun cancels an enemy tribute** (immediately, bag kept, must restart from tick 0). Damage does not. Altar lock also cancels it.
2. **Altar lock**: placed on an altar with an enemy mid-tribute, it cancels that tribute. The placing team can still bank there.
   3 hits destroy it, one basic attack each (attack used, move/cast still free; Vendetta reset gives 2 hits a turn); no decay.
   `submit_gems` at an enemy-locked altar is executed as an attack on the lock (3 calls), the 4th starts the tribute. Placement range 2
   (range 3 throws error 119), cost 10 gold, buy on spawn only.
3. Same-team and both-team tributes at one altar run in parallel (4 bodies tested). Capacity = the 8 neighbour tiles.
4. Duration = ceil(gems/10), min 1, lands at the start of the tributer's own turn in round R + ticks. Measured 22, 24, 46, 48, 72, 264 gems
   (exact 10/11/20/66 not buildable: rewards are 22/24). Gems count as banked on landing only. **The win registers on landing, mid-round; if
   both teams land a winning tribute in the same round, the team that acts first that round wins (A odd, B even).** Round-limit tiebreak
   (from engine strings, untested): gems, then gold earned, then kills, then team B.
5. Home emblem: recall 3 turn ends (normal 5).

## Legend code relying on the tribute/stun assumption
- `bots/legend/src/brain.cpp` `handle_channel()` (about lines 546-595):
  - the comment at 549-552 ("a tribute survives damage but not a stun or death"): **right**;
  - lines 556-569 compute `stunner_close` (enemy within 4 with cc ready, or aoe-stun ready);
  - line 581 `... || (stunner_close && gems >= 20 && threat_close)` cancels our own tribute pre-emptively: **consistent with the engine**
    (a stun would cancel it anyway; cancelling frees the turn to flee or fight, and the bag is kept either way). No bug.
- `brain.cpp` `use_locks()` (about 1060-1105): places a lock when a visible enemy tributes within 1 of the altar, at Chebyshev <= 2: **right**.
- `brain.cpp` 740 (`+6` for an enemy-locked altar) and `tribute()` (about 1952-2013) retrying `submit_gems`: **right** (3 hits, then the channel).
- `brain.cpp` 3013 `recall_time - (has_home ? 2 : 0)`: **right**. Lines 1692, 1969, 2173 use `recall_time` without `has_home`: harmless (we never buy Home).
- `brain.cpp` 2046 comment ("the only way to stop a winning tribute"): **wrong as a statement of fact**. A stun (range 4, any of Tavi, Ren,
  Prism, Cassi, Ryth area) or an altar lock also stops it, from farther away than a melee kill. The code under the comment only sends a
  fighter; stunners are not singled out. Possible follow-up (not done, not A/B tested): in `respond_to_alert` prefer an ally with a ready stun
  when the alerted enemy is tributing, and keep a lock bought (10 gold) for the endgame when the enemy approaches 1000.
- Old wording in the previous ENGINE_FACTS ("only death stops a tribute") was wrong; fixed in place.

## Files
- `experiments/wip/x_probe/main.cpp`: shared probe bot (farm/carrier/log helpers). `s1_stun.h`, `s2_lock.h`, `s3_concurrent.h`, `s5_home.h`,
  `s6_race.h`: one scenario each (`scenario()`), selected by copying into `bots/_x_probe/src/scen_body.h`.
- `tools/mapgen/probe5map.mjs` -> `maps/probe5/p5.map26a` (25x25 rot180, centre altar (12,12), 3 gem + 2 gold clusters + wolf per half);
  `tools/mapgen/probe5map_big.mjs` -> `maps/probe5/p6.map26a` (31x31, 4 champions per team, 16 gem clusters per half, altar (15,15)).
- `tools/probe5_run.sh NAME ROUNDS` builds `bots/_x_probe`, runs one game, unzips logs and decodes the replay into `/tmp/probe5/NAME/`.
- `tools/probe5_all.sh [s1 s1b s2 s2c s3 s5 s6 s6b]` runs every scenario (about 70 s total, one game at a time).

## Reproduce
```bash
tools/probe5_all.sh                      # all scenarios; logs in /tmp/probe5/<name>/team-{a,b}.stdout, decoded.json
grep -a -h "STUN\|B-vend" /tmp/probe5/s1/team-b.stdout | tr -d '\000' | sed 's/^ *//' | head      # 1: sub=0 stun=1 at r53, gems stay 46
grep -a -h "ATTACK\|B-vend" /tmp/probe5/s1b/team-a.stdout | tr -d '\000' | head                    # 1 control: damage does not cancel
grep -a -h "lock\|submit_gems\|START" /tmp/probe5/s2/team-{a,b}.stdout | tr -d '\000'             # 2a, 2d, 2e
grep -a -h "lock hits\|ATTACK\|atk\|reset" /tmp/probe5/s2c/team-b.stdout | tr -d '\000'           # 2b, 2c
grep -a -h "TRIBUTE START\|bag gems" /tmp/probe5/s3/team-{a,b}.stdout | tr -d '\000'            # 3, 4a
grep -a -h "RECALL\|ARRIVED" /tmp/probe5/s5/team-a.stdout | tr -d '\000'                         # 5
grep -h wins /tmp/probe5/s6/run.log /tmp/probe5/s6b/run.log                                      # 4c: A wins r249, B wins r250
```
Team stdout files contain NUL bytes and leading spaces (the runner pads per body): use `grep -a`, `tr -d '\000'`, `sed 's/^ *//'`.
Replay events: `node tools/replay/decode.mjs /tmp/probe5/s2/replay.repl26a --out x.json`, then events `Submit gems`, `Place altar lock`,
`Attack` (the implicit lock hits), `Gems submitted`, `Banked`.

## Caveats
- Everything ran with only gem/gold/wolf camps and no fighting, so no other champion's passive interferes. The stun test used Tavi's
  slot-1 stun; other stuns (Ren, Prism, Cassi, Ryth area) were not run, but the header says stuns "interrupt channels" generally.
- Engine tiebreaks at round 2000 are from strings in the binary, not from a played-out game.
- A game with 1000 gems needs about 250 rounds of scripted farming (4 bodies, 12-16 cluster harvests each); `s6` does it in 2 s of CPU.
