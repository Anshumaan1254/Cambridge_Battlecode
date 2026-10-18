# x_f2 (agent fight2, session 9): area reach 5, area casts from 5, openers

Baseline `bots/_xp4` (= shipped `legend_m6`). Copy `bots/_x_f2` = `_xp4` + `x_f2.patch`; every switch default 0 plays
identically to `_xp4` (checked: `_x_f2` vs `_px9` on the 34 official games, every stats JSON byte-identical to `_xp4` vs `_px9`).
Evidence: `docs/strategy_v2/08_TOP3_VS_TOP3.md` section 2 (spells 72-82% of champion damage between top teams, 20-28% of it
at distance 5; we deal 3 and take 12 per body-round at distance 5 against them; the opener wins the first 3 rounds 391 to 58).

## Switches (params.h, block "Fight micro v2")
- `aoe_reach5` (F1): enemy area spells (ready, or cooldown unknown while unseen) reach `aoe_range + aoe_radius` = 5 (Ryth's area
  stun, Stellar's and Prism's areas), not 4: `build_danger` (danger map, routes), `combat()`'s `reach_of` (in-reach weight,
  incoming, burst_exit, holds), `engage_angle`, the tribute stun check in `handle_channel`. 2: also walk-compatible spells
  (Cassi's stun) reach range + 1. Helper `enemy_spell_reach()` in brain.cpp.
- `aoe_cast5` (F2): our area spells (Stellar, Prism; Ryth already did) aim at a tile within cast range whose radius catches
  the target, most enemies first (`cast_area_stun_at` generalised: the Marcella filter only for stuns): engage() ranged branch
  casts the area at d = 5 instead of stepping in, the area fallback at d <= 4 aims the same way, `cast_on_nearer` looks to 5,
  px targeting counts the area at 5, `killable` counts the area at 5. Bit 2: at d <= 4 an area that catches 2+ enemies is
  cast before the single-target spell.
- `open_join` (F4): a body not fighting, with a fresh RALLY (an ally's fight target, this round or last; not if we fought
  last round ourselves), casts its spell on that target from where it stands when it reaches (damage spell, then area with
  the F2 aim, then stun), plus a basic attack if in range; no step, no commitment. Inside enemy reach only from
  `open_join_hp` (0.5) health.
- `open_first` (F3, bits): 1 = after a fight step, a walk-compatible spell that now reaches the target is cast (Cassi: walk
  5 -> 4 + stun); 2 = ranged body in a proactive fight with an opener ready that cannot hit this turn: when the next step
  enters an enemy's next-turn reach (with F1: 5 for area casters), hold at the edge for at most `open_hold` (2) rounds per fight.

## Recipes
- `_x_f2`: `SRC=bots/_xp4 tools/variant.sh _x_f2 && (cd bots/_x_f2 && patch -p1 < ../../experiments/wip/x_f2.patch)`
- variants: `SRC=bots/_x_f2 tools/variant.sh NAME key=val ...`
  `_f2a` aoe_reach5=1; `_f2b` aoe_cast5=1; `_f2c` aoe_cast5=3; `_f2d` open_first=1; `_f2e` open_first=2;
  `_f2f` aoe_reach5=1 aoe_cast5=1 open_first=1; `_f2g` aoe_reach5=3; `_f2h` aoe_cast5=3 open_first=1;
  `_f2i` aoe_cast5=3 aoe_reach5=3; `_f2j` aoe_cast5=3 open_first=1 aoe_reach5=3.
- proxy with reach-5 casts: `_f2p` = `_px9` + `x_f2.patch` (one hunk, the engage_angle loop, does not apply: `_px9` has no
  engage_angle; ignore it), then `SRC=bots/_f2p tools/variant.sh NAME aoe_cast5=...`.

## Results (88 distinct games / official 34 / deaths ours-theirs)

| Bot | recipe | vs `_xp4` | notes |
|---|---|---|---|
| `_f2a` | aoe_reach5=1 | 42.0 / 47.1 / 688-624 | rejected: in_reach at 5 makes bodies flee or fight-back from 5; more deaths, not fewer |
| `_f2b` | aoe_cast5=1 | 52.3 / 58.8 / 632-684 | |
| `_f2c` | aoe_cast5=3 | **54.5 / 58.8** / 639-699 | best of round 1 |
| `_f2d` | open_first=1 | 51.1 / 55.9 / 654-670 | neutral |
| `_f2e` | open_first=2 | 46.6 / 44.1 / 633-632 | rejected: holding at the edge (the old A6 / px_hold idea) loses again |
| `_f2f` | aoe_reach5=1 aoe_cast5=1 open_first=1 | 50.0 / 52.9 / 609-591 | F1 cancels F2 |
| `_f2g` | aoe_reach5=3 (routes only) | 53.4 / 61.8 / 616-664 | pace 525.3 (+3.4) |
| `_f2h` | aoe_cast5=3 open_first=1 | 51.1 / 52.9 / 651-695 | open_first adds nothing |
| `_f2i` | aoe_cast5=3 aoe_reach5=3 | 51.1 / 52.9 / 672-696 | pace 525.3 |
| `_f2j` | aoe_cast5=3 open_first=1 aoe_reach5=3 | 48.9 / 52.9 / 660-705 | |

### Reach-5 proxy `_f2q` (= `_px9` + x_f2.patch + aoe_cast5=3 open_first=1: the proxy casting its areas from 5 like the top teams)

| Bot | vs `_f2q` |
|---|---|
| `_xp4` | 44.3 / 41.2 / 679-650 |
| **`_f2c`** | **53.4 / 50.0** / 669-728 |
| `_f2g` | 51.1 / 50.0 / 614-685 |
| `_f2i` | 47.7 / 58.8 / 643-701 |
| `_px9` | 52.3 / 52.9 / 628-635 |

The 5-reach casts alone turn `_px9` (which `_xp4` beats 58.0 on the 88) into an opponent that beats `_xp4` 55.7. Our own
F2 recovers it (+9 over `_xp4`). Avoiding their reach (F1, routes only) does not help even against this proxy: the gain is
in casting from 5, not in staying out of 5.

### Best candidate `_f2c` (aoe_cast5=3) against the guards (88 / official 34 / deaths)

| Opponent | `_f2c` | `_xp4` |
|---|---|---|
| `_xp4` | 54.5 / 58.8 / 639-699 | - |
| held-out (gold, gold2, obj; 100) vs `_xp4` | **60.0** / deaths 2034-2235 | - |
| `_px9` | 56.8 / 61.8 / 594-688 | 58.0 / 64.7 / 621-663 |
| `_fA` | 69.3 / 82.4 / 590-1018 | 72.7 / 82.4 / 561-1015 |
| `_ST` | 75.0 / 76.5 / 528-947 | 73.9 / 82.4 / 465-909 |
| `_f2q` (reach-5 proxy) | 53.4 / 50.0 | 44.3 / 41.2 |
| `_eA` | 78.4 / 91.2 / 698-1278 | 71.6 / 79.4 / 738-1230 |
| `_m5a` | 52.3 / 50.0 / 559-708 | 52.3 / 61.8 / 580-710 |
| pace (official 17, vs idle) | 521.9 | 521.9 |

- 0 faults everywhere; fuel: gen16_98x99_V_c5 both sides, rollovers A=8 B=8, all in rounds 1-3 (= baseline).
- Pace identical (the area aim only runs in fights).

### KPIs, `_f2c` vs `_px9`, 17 official maps side A (`tools/strategy_v2/kpi_local.sh`; baseline `experiments/kpi_local/xp4_vs_px9`)

| KPI | `_xp4` | `_f2c` | top teams (doc 08) |
|---|---|---|---|
| Spell damage landing at distance 5 (share of spell damage) | 3% | **21%** | 20-28% |
| Distance-5 band: dealt / taken next round per body-round | 5 / 6 | **15 / 5** | 13 / 3 vs us |
| Fights opened / opened on | 130 / 104 | **143 / 98** | 129 / 74 vs us |
| Opener damage 3 rounds (ours / theirs) when we open | 518 / 100 | 516 / 123 | 391 / 58 |
| Fight damage ratio (ours / theirs) | 0.87 | **0.97** | |
| Body deaths per game | 10.3 | 10.2 | |
| Top opener | Ren spell d4 x23 | **Stellar spell d5 x33** | Ryth d5, Stellar d4-5 |
