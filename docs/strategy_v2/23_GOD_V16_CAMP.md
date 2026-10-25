# GOD v16 "camp" (Oct 25): the spawn-camp bot

The user: "test a second bot after shipping the main bot: farm gold first, then go near their altar and kill all their members, then
get our most powerful champion near their spawn and kill them when they spawn again. Improvise it." Later: "first ship this camp bot".

`bots/god16` = GOD v15 + the `g16_*` switches (params.h, section "GOD v16"). Shipped as **`submissions/god16_camp.zip`** (history
`god16_camp_20261025.zip`, source hash 108e80470440 = the measured `_h10`). It is **not** `submissions/god.zip` (still GOD v15) and
nothing was submitted.

## 1. What it does

- Every body ranks the living allies by kit strength (Vendetta, Heart of Ruin, Vesper Vale, Marcella, Varg, Ryth, Tavi, Ren, Stellar,
  Prism, Willow) so the roles agree without talking. Rank 0 is the camper.
- `g16_camp` 1: from round `g16_hunt_from` the `g16_hunt_bodies` strongest bodies wait at the altar the enemy banks at (most tributes
  seen, else the one nearest their spawn) with bolder fight bars (x `g16_fight_k`); once `g16_camp_dead` enemies are dead at once, the
  camper waits `g16_camp_d` tiles from their spawn (out of reach of a body healing on it) for `g16_camp_hold` rounds while any is dead.
- `g16_gate`: hunt only while our deaths are at most theirs + `g16_gate_margin`. `g16_carry_camp`: Vesper Vale (the gold-funnel carry)
  is the camper. **`g16_only_camp`**: no altar hunt at all: every body farms like v15 and only the camper leaves, only after our fights
  have left `g16_camp_dead` of them dead (bold fights only while camping).
- Hurt bodies (below `g16_hunt_hp`), bodies carrying `g16_hunt_bag`+ gems and capturing bodies do what v15 does.

## 2. Results (40 official maps x 2 sides unless noted; cambc 3.0.5, release)

| Variant | vs GOD v15: wins, gem margin | deaths us-them | gold us-them |
|---|---|---|---|
| `_h1` camp 1 (3 hunters from r300) | 9/80, -620 | 18.6-9.9 | 3,450-9,638 |
| `_h4` + gate | 18/80, -338 | 15.4-10.7 | 5,148-8,662 |
| `_h5` + gate + Vesper camps | 15/80, -413 | 16.2-10.5 | 5,221-8,935 |
| `_h6` + gate + Vesper, 2 hunters from r400 | 21/80, -275 | 14.8-12.6 | 6,237-8,347 |
| `_h7` + gate margin -2 + Vesper | 30/80, -175 | 13.7-12.9 | 6,323-7,792 |
| `_h8` only_camp (2 dead, from r300) | 41/80, -1 | 12.2-12.5 | 7,011-7,378 |
| `_h9` only_camp + Vesper camps | 36/80, -25 | 11.6-12.1 | 6,983-7,264 |
| **`_h10` only_camp, 3 dead, from r200** | **45/80, +65**; all 167 maps **162/334 = 48.5% [43.2, 53.8], -14 [-83, +56]** | 13.7-13.1 | 7,217-7,482 |

Against the top-team draft proxies: `_h10` vs `_px_cm` 52/80 (+228), vs `_px_uos` 56/80 (+300); GOD v15 there 58/80 (+323) and 59/80
(+373).

**Why the hunting loses**: every body sent to an altar or a spawn stops farming; the first version earned 36% of v15's gold and died
twice as often. The less a variant hunts, the better it does; the camp pays only as a short opportunistic visit after our fights have
already won (three of theirs dead), and then it is level with v15, not better.

## 3. Decision

Shipped `_h10` as the camp bot (`g16_camp` 1, `g16_only_camp` 1, `g16_camp_dead` 3, `g16_hunt_from` 200) because the user asked for it:
it ties GOD v15 head-to-head over 334 games and is a little weaker against the proxies. `submissions/god.zip` stays GOD v15. The
spawn camp is kept as a switch in GOD v17 (`bots/god17` carries the `g16_*` code) and is not used unless it measures better there.
