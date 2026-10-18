# 11. Intercontinental Fish, Oct 18 upload (30 games), and what it means for our bot (session 12)

> Written as a handoff in session 12. `legend_m12` (= `legend_m11` play, wasm byte-identical, plus the inert switches below) is the build on branch `claude/laughing-curie-3rq6hu`; the zip `legend_final` described in section 0 below was the session-12 candidate before `legend_m11` shipped on the ccr branch (`legend_m11` = the same warding plus the stronger contest blob opening).

## Final check (session 12): which contest plan to ship

On the contest pool (contest + 33 geometry / perturbed copies, 68 games): `_fwc` (ward_bush 2 + GROUPED opening to r300, the `legend_final` zip of section 0) vs `_m11` (ward_bush 2 + blob opening `mono_follow_until` 200) **27.9%**; vs the sneaky-bush proxy `_fwc` 92.6%, `_m11` 97.1%. **`legend_m11` / `legend_m12` is the build to ship; `legend_final` is superseded.**

Why every switch stays off: each was measured switched on and lost (paired opening 35.3 / 38.2, all-map blob 44.1, `mi_chip` 47.1, `mi_deny_gems` 50.0 with `_px9` -5.9, Stellar first 45.5, IC builds 32.4, IC table + builds 29.4, IC farm builds and rows draft slower). Turning any of them on makes the bot worse in our tests.

## M12 screen on top of legend_m11 (official 34 games; `legend_m11`: vs Mite proxy 76.5, vs `_px9` 79.4)

| Variant (switch on `_m11`) | vs `_m11` | `_mite` | `_px9` | Verdict |
|---|---|---|---|---|
| `pair_open_until` 150 / 300 (any fighting group an ally claims is worth joining: IC pairs its melee bodies) | 35.3 / 38.2 | - | - | rejected |
| `follow_all_until` 60 / 120 (contest blob opening on every map) | 44.1 / 44.1 | - | - | rejected |
| `mi_chip` (idle spells chip camps while passing) | 47.1 | 73.5 | 73.5 | rejected |
| `mi_deny_gems` | 50.0 | 76.5 | 73.5 | rejected (`_px9` -5.9) |
| `mi_chip` + `mi_deny_gems` | 44.1 | 73.5 | 73.5 | rejected |

So `legend_m12` keeps `legend_m11`'s play; `follow_all_until` and `pair_open_until` stay in `params.h` at 0 (guarded so the wasm is identical).


For the Claude that builds the final bot. Everything below was measured in this session or by the parallel S7R session on the same branch
(`ccr-a858cd03-q87cpi`). **Nothing was pushed to GitHub** (the user's instruction). This folder holds everything you need:

| File | What |
|---|---|
| `legend_final.zip` | **the submission**: `cambc bundle` output, sha256 `65fb9af5370d40a61dd4e392dc6392d290452b5af5fb4e7540c414167d85f3df`; wasm byte-identical to the tested build `_fwc` |
| `final_vs_legend_m10.patch` | the same code as a patch against `bots/legend/src` (= `legend_m10`): `cd bots/legend && patch -p1 < .../final_vs_legend_m10.patch` |
| `patches/x_wb.patch`, `patches/x_ct.patch` | the two parts (S7R's ward-the-bush and contest-plan patches, cut against `_m10`, defaults off) |
| `patches/x_ic_switches_vs_m10.patch` | this session's Intercontinental-Fish switches (all off; every one measured worse, see section 4) |
| `analysis/` | decoded KPIs of the uploaded games: `ic_teamsum.md`, `ic_micro.md`, `builds_all_teams.txt`, `drafts_30_games.txt`, our ladder games vs the sneaky team for comparison |
| `replays/` | the 30 uploaded replays, named `<group>_<NN>_<map>.repl26a` |
| `tools/` | the small analysis scripts written here (`builds.py`, `opening.py`, `cofarm.py`, `pairs.py`) |

## 0. What to ship (no further tests needed)

**Ship `legend_final.zip`** = `legend_m10` + two switches:

1. `ward_bush = 2` (`x_wb.patch`): `place_ward` puts the ward on a bush tile within 2 when there is one (nearest to the closest
   recently seen enemy), and re-wards after 3 rounds when a bush is in reach and our ward is not in it. Reason: the sneaky-bush team
   (beat `legend_m8`/`m10` 12 of 17 on the ladder) wards bush tiles 100% of the time, we 19%; 48% of our champion-caused deaths had a
   hitter standing in a bush (doc `docs/strategy_v2/10_SNEAKY_BUSH.md`).
2. `mono_grouped_until = 300` (`x_ct.patch`, detector `mono_plan = 1`): on lone-monolith maps only (contest and its copies;
   `World::mono_mode`, inert elsewhere) the team plays the GROUPED stance until round 300 instead of arriving at the centre one by one.

Steps for the implementing Claude:
```bash
cd /path/to/Cambridge_Battlecode            # branch ccr-a858cd03-q87cpi
cp handoff_final/legend_final.zip submissions/legend.zip          # or: cambc submit with the zip
# optional, to keep the repo in sync with the zip:
(cd bots/legend && patch -p1 --no-backup-if-mismatch < ../../handoff_final/final_vs_legend_m10.patch)
rm -f /tmp/check.zip && cambc bundle legend --output /tmp/check.zip && sha256sum /tmp/check.zip   # bundle of the patched legend
```
Source hash of the shipped code (`tools/ledger.py src_hash` of the bot dir): `3729300fd292` (legend-based, with comments and the inert
`LEGEND_RUNTIME_PARAMS` block); the tested ledger name is `_fwc` (hash `50932dbb9b90`, built from `_m10` + both patches + the two values).
Rollback: `submissions/history/legend_m10_20261018.zip` (or `legend_m8`, same games).

## 1. The uploaded zip: who played whom

`intercontinental matches.zip` = 6 match groups x 5 games = 30 games, replays only (no team logs, so none of them is ours). Teams are
identified by their fixed per-map draft tables (same method as docs 09 and 10). One team is in all 30 games: **IC = Intercontinental
Fish**, now drafting **Stellar first** (Stellar, Ren, C&I, Ryth, Varg on 5-champion maps). Its builds match doc 09's ifish builds plus a
Home emblem.

| Group | Side A | Side B | Result for IC |
|---|---|---|---|
| 2c003f5b | **IC** | sneaky-bush (their draft table, doc 10) | 4-1 (lost expanse 942-1016) |
| 4fe94d92 | OIF (the old ifish draft table, Ren first, Treasure-first builds) | **IC** | 5-0 |
| d5df43d9 | **IC** | Mite (2nd on the ladder; doc 09 table) | **5-0** (stampede 1080-0, eight 1042-22) |
| dff89fd3 | **IC** | T5 (unknown; C&I-first drafts, Mite's stampede draft) | 4-1 (lost stampede 0-1080) |
| ea768792 | Mite | **IC** | 2-3 (lost rushbait 842-1010, stampede 0-1080, contest 0-0 on gold) |
| eb7ecbc4 | T6 (unknown; Varg, C&I, Ryth, Stellar) | **IC** | 5-0 |

**IC: 25 wins in 30.** Our `legend_m8`/`m10` lost 12 of 17 to the same sneaky-bush team; IC beat it 4-1 on five of those maps
(rushbait 1024-906, elkring 1008-612, eight 1026-182, pilgrimage 1004-936; we lost all five: 534, 396, 22, 592, 700 banked).

## 2. What IC does better (measured, contest excluded; per game unless said)

| # | Area | IC | Us (`legend_m8`/`m10` vs sneaky, ladder) | Source |
|---|---|---|---|---|
| 1 | Body deaths / kills | **3.9 / 6.2** | 5.4 / 3.4 | `analysis/ic_teamsum.md`, `us_vs_sneaky_teamsum.md` |
| 2 | Captures home / neutral / enemy half | 13.2 / **8.3** / 1.7 | 13.8 / 3.8 / 0.8 | same |
| 3 | Camp damage per body-round | **119** | 87 | same |
| 4 | Trade per distance band (dealt / taken next round, per body-round) | band 3: 42 / 30, band 4: **47 / 22**, band 5: 20 / 11 | band 3: 29 / 50, band 4: 36 / 38, band 5: 13 / 21 | `ic_micro.md`, `us_vs_sneaky_micro.md` |
| 5 | Fights opened (damage next 3 rounds mine / theirs) | 182 in 29 games (530 / 162); top openers Stellar spell from 5 (x34), Ryth spell from 5 (x23), Ren spell from 4 | 68 in 16 games (339 / 227) | same |
| 6 | Opening (to r200): melee bodies farming with an ally | Ren alone 16% of its camp damage, Ryth 12%, Varg 7% | Ren 42%, Ryth 48%, Varg 30% | `tools/pairs.py` |
| 7 | Stellar | first capture r37, first emblem **r66** (Power focus), gold by r150 **320**, 1,500 hp / 250 focus at r300, 1.36 captures per 100 alive rounds | r98, r170 (Monster focus), 35, 750 / 190, 0.72 | `analysis/builds_all_teams.txt` |
| 8 | Builds | Stellar / Issac / Varg: Power, **Home** health, Durability health, then Power forever; Ren / Ryth: Bruiser, Durability health, Power; Cassi: Power, Durability focus, Bruiser health; rows / expanse: Monster then Power | Monster, Treasure, Jungle, Bruiser cycles; never Home | same |
| 9 | Expanse (same draft C&I, Stellar, Varg, no contact) | 978 camp gems by r446; Cassi 430 focus at r300, Issac 130 strength | 700 by r446; Cassi 160 focus, Issac 88 strength | per-body tables |

**Draft compared with ours** (pick order; `legend_m8`/`m10` = `mapdraft 3`):

| Maps | IC | Ours |
|---|---|---|
| 5-champion maps | Stellar, Ren, C&I, Ryth, Varg | Ren, Stellar, C&I, Varg, Ryth (same set) |
| interlock, rushbait-v2 | Stellar, Ren, C&I, Ryth | Ren, Stellar, C&I, Ryth (same set) |
| swirl | Stellar, Ren, C&I, Ryth | Ren, Stellar, C&I, **Varg** |
| 3-champion maps | Stellar, Ren, C&I | Ren, Stellar, C&I |
| expanse | C&I, Stellar, Varg | same |
| rows | Stellar, **Prism**, C&I, Varg | **Ren**, Stellar, C&I, Varg |
| stampede | Stellar, Tavi, Prism, C&I, **Ren** | Prism, Stellar, C&I, **Ryth**, Tavi (Mite's ring draft) |
| contest | Stellar, Tavi, Prism, C&I, Ren | Ren, Stellar, C&I, Varg, Ryth |

So the champion sets are almost ours; the real differences are pick order (Stellar is body 0, so it collects shared rewards), builds,
and play (paired farming in the opening, fights opened with spells from 4-5, more neutral captures).

## 3. Why we cannot simply copy it: every IC element was tested inside our brain

All cells are in `experiments/results/ledger/` (local, not pushed). "88" = 44 distinct maps x 2 sides (`maps/*.map26a` + `maps/comp`),
"off" = the 17 official maps x 2 sides. `legend_m8`'s own cells for reference: `_mite` 76.1 / 82.4, `_ifish` 69.3 / 79.4, `_px9` 78.4 / 76.5,
`_snk` (`_m10`) 64.8 / 61.8. Control `_icc` (all new switches off) vs `_mite`: 33 of 34 games identical to `_m10` (lanes A flipped by fuel noise).

| Variant (switch on `_m10`) | vs `_m10` | `_mite` | `_ifish` | `_px9` | `_snk` | pace (17 official, `_m8` 503.8) | Verdict |
|---|---|---|---|---|---|---|---|
| `_ics` Stellar picked first (`stellar_first=1`, our builds) | 45.5 (88) | 67.0 | 63.6 | 56.8 | 71.6 | - | **rejected**: our brain is tuned around Ren as body 0 |
| `_icb` IC builds everywhere (`build_style=11`) | **32.4** (off) | 64.7 (off) | 55.9 (off) | 73.5 (off) | - | - | **rejected** (as sessions 6-10 found for every top-team build) |
| `_icp` IC table + IC builds (`mapdraft=5 build_style=11`, an IC proxy) | **29.4** (off) | 50.0 (off) | 55.9 (off) | - | - | - | our brain plays IC's set badly: weaker than the existing proxies, not a useful sparring partner |
| `_icf` Monster then Power on rows / expanse only (`farm_build=1`) | 1 / 4 on rows+expanse | 4 / 4 | 2 / 4 | 3 / 4 | 1 / 4 | **506.5** (expanse 499 -> 529, rows 373 -> 389) | **rejected**: slower in our brain |
| `_icr` IC's rows draft (`md_rows=1`) | - | - | - | - | - | **505.9** (rows 373 -> 409) | **rejected** |
| `_m10` itself on rows + expanse | - | 4 / 4 | 4 / 4 | 4 / 4 | 3 / 4 | 503.8 | keeps its table and builds |

Conclusion: IC's edge is **execution** (how its brain farms and fights), not its draft table or item list. In our brain each copied piece
loses, exactly as the earlier sessions found for Mite's, ifish's and the sneaky team's tables and builds. The only changes that pass the
user's rule ("never lose to `legend_m8`/`m10`, not worse against the third parties") target specific situations: bushes and contest.

## 4. The final bot's measurements

### 4.1 `ward_bush = 2` (S7R session, `_wb2` = `_m10` + `x_wb.patch` + `ward_bush=2`)
- Control `ward_bush=0`: 34 of 34 official games identical to `_m10`.
- 88 / off (`_m8`'s cell in brackets): vs `_m10` 52.3 / **64.7** (deaths 552-700); vs `_m8` 51.1 / 64.7; `_mite` 63.6 / 70.6 (76.1 / 82.4);
  `_ifish` 70.5 / 73.5 (69.3 / 79.4); `_px9` 72.7 / 82.4 (78.4 / 76.5); `_fA` 78.4 / 79.4 (73.9 / 82.4); `_ST` 85.2 / 91.2 (83.0 / 91.2);
  `_snk` 64.8 / 70.6 (64.8 / 61.8); pace 504.4.
- The Mite cell on the 88 looked worse; the **held-out maps** (gold, gold2, obj: 100 games, never used to select `_m8`'s choices) say it is
  selection bias: vs `_mite` **87.0** (`_m10` 79.0), vs `_px9` **74.0** (66.0), head-to-head vs `_m10` 51.0. Over 188 games vs `_mite`:
  76.1 vs 77.7; vs `_px9` 73.4 vs 71.8.

### 4.2 Contest GROUPED opening (`x_ct.patch`, `mono_grouped_until = 300`, S7R agent `ct`)
- Fires only where lone monoliths hold >= 90% of the gem rate (contest, its ladder copy, `gold_mono_*` test maps).
- Contest pool CT4 (contest + 3 geometry variants + 6 perturbed copies, 20 games): `_ct0` (= `_m10` play) vs `_snk` / `_mite` / `_ifish` /
  `_px9` / `_m8` / `_fA` = 30 / 60 / 50 / 50 / 50 / 75; **GROUPED to r300 (`_cw1`) 70 / 55 / 70 / 55 / 65 / 90**.
  CT34 (34 contest-like maps, 68 games) vs `_snk`: `_m10` 38.2, `_cw1` 69.1.
- Stronger, not yet committed by S7R when this was written: `mono_follow_until = 200` (`_fo200`, bodies follow the leader as a blob to
  r200): CT34 vs `_snk` / `_mite` / `_ifish` / `_px9` / `_m8` = **83.8 / 89.7 / 77.9 / 66.2 / 69.1**. Its code lived in S7R's local `bots/_x_ct2`;
  if `experiments/wip/x_ct.patch` on the branch now contains `mono_follow_until`, prefer `_fo200` for contest (same detector, still inert elsewhere).

### 4.3 The combination `_fwc` (= the zip), this session
`_fwc` = `_m10` + `x_wb.patch` + `x_ct.patch` with `ward_bush=2 mono_grouped_until=300` (both patches apply cleanly together; the zip's wasm
is byte-identical to `_fwc`'s). 0 faults in every cell.

| Opponent | `_fwc` all / official | deaths ours-theirs | `legend_m8` / `m10` same cell | held-out (gold, gold2, obj: 100 games) `_fwc` / `_m10` |
|---|---|---|---|---|
| `_m10` (= `legend_m8` play) | **52.3 / 64.7** (88 / 34) | 612-695 | - | - |
| `_mite` (Mite proxy) | 64.8 / 73.5 | 2037-3239 (188 games) | 76.1 / 82.4 | **87.0 / 79.0** (188 games: 76.6 vs 77.7, level) |
| `_px9` (ladder-calibrated proxy) | 73.9 / **85.3** | 2454-3209 (188 games) | 78.4 / 76.5 | **73.0 / 66.0** (188 games: 73.4 vs 71.8) |
| `_ifish` (ifish proxy) | 69.3 / 70.6 | 662-723 | 69.3 / 79.4 | - |
| `_snk` (sneaky-bush proxy) | 63.6 / **67.6** | 642-725 | 64.8 / 61.8 (`_m10`) | - |
| `_fA` (pressure archetype) | 78.4 / 79.4 | 545-949 | 73.9 / 82.4 | - |
| `_ST` (`legend_st`) | 85.2 / 91.2 | 467-987 | 83.0 / 91.2 | - |
| unopposed pace, 17 official maps | **503.4** rounds | | 503.8 | |

Per official map vs `_m10` (A / B): wins on ambush, contest (1000-0 and the 400-400 r2000 tiebreak), corners, eight, monolith, pilgrimage,
rushbait-v2 both sides; split on collision, elkring, expanse, interlock, lanes, packs, rows, stampede; loses fragment and swirl both sides.

Verdict against the user's rules: **head-to-head vs `legend_m10`/`m8` passes** (52.3 all, 64.7 official, fewer deaths). Against the third
parties it is **level**: the 88-game mean is 72.5 vs 74.3 (the Mite cell), the official mean 77.9 vs 79.0, but on the held-out maps it is
clearly better (+8 vs Mite, +7 vs `_px9`), and over 188 games per proxy it is level with Mite and +1.6 vs `_px9`. It is the best build
measured on this branch; ship it, and judge it on the ladder (KPIs to watch: deaths with a bush hitter, contest result, sneaky-bush games).
Turn rollovers on the fuel-stress map `gen16_98x99_V_c5` (vs `idle`): `_fwc` 8, `_m10` 8, all in rounds 1-3 (unchanged).

## 5. What the next session should work on (ranked by measured size; none of it is in the zip)

1. **Paired opening** (IC: Ren / Ryth / Varg farm with an ally 84-93% of the time before r200, ours 52-70%). In our brain a body joins an
   ally's group only when it is heavy (`group_score`, `join_min_rounds`, `max_join`). Test a switch "before round R, also join non-heavy
   groups next to a claiming ally", screened first against `_px9`, `_mite`, `_snk` on the official 34 (the lesson of sessions 10-11: changes
   that only beat our own build are non-transitive). S7R's contest blob (`mono_follow_until`) is the same idea on one map and wins big there.
2. **Fights opened from 4-5 with spells** (IC opened 182 fights with 530 dealt / 162 taken; band 4: 47 dealt / 22 taken vs our 36 / 38).
   Our `aoe_cast5` (area spells from 5) is in; Stellar's single-target spell and Ryth's stun from 5 as openers are not.
3. **Neutral camps** (IC 8.3 neutral captures per game, us 3.8; doc 10's C6).
4. Do **not** repeat: Stellar-first pick order, IC / Mite / ifish / sneaky builds or full draft tables, Power builds on farm maps, Prism on
   rows (all measured worse here or in sessions 6-11).

## 6. Method notes
- Decoding: `python3 tools/strategy_v2/run_all.py OUT "intercontinental matches/"`; team labels per group for `teamsum.py` / `micro.py`:
  `2c003f5b:IC:SNK,4fe94d92:OIF:IC,d5df43d9:IC:MITE,dff89fd3:IC:T5,ea768792:MITE:IC,eb7ecbc4:T6:IC` (outcome 1 = side A won).
- `report.md` in `analysis/` treats side A as "us", which is IC in only 3 of 6 groups: use `ic_teamsum.md` / `ic_micro.md` for IC numbers.
- New switches for experiments (all off, `patches/x_ic_switches_vs_m10.patch`): `mapdraft 5` (IC table), `stellar_first`, `build_style 11`
  (IC builds, buys Home), `farm_build`, `md_rows`; `has_home` is now set when a Home emblem is bought and every recall-time estimate uses
  `recall_turns()` (3 instead of 5 with Home), which matters only for builds that buy Home.
