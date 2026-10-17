# x_coord: team coordination (agent `coord`, 2026-10-17)

Bot copy: `bots/_x_coord` (local, git-ignored). Patch: `experiments/wip/x_coord.patch` (against `bots/legend/src` = `_L0`).
Tools (new):
- `tools/analysis/coord_audit.mjs DIR...` coordination failures from bench replays, both sides (`--split` adds won/lost games).
- `tools/analysis/coord_trace.mjs DIR...` joins the audit's death categories with the `COORD_TRACE` decision lines
  (build a copy with `#define COORD_TRACE 1` on top of `params.h`, run it with `cambc run-batch --log-limit 60000000`).

## 0. Engine facts checked first

- Champion vision radius is 8 for every champion (`champion_designs[*].base_stats().vision_radius`).
- Vision is **not** shared across the team: 56% of alive-ally turns had at least one ally hidden (probe, 400 rounds on
  a ladder map). A body still sees enemies up to ~39 tiles away and allies up to ~30 tiles away through the team's
  wards (vision 6, one per champion, re-placed every 10 rounds near it). So a "deterministic focus target from
  shared vision" cannot assume that every body sees the same enemies.
- Bushes hide allies from each other too: a traced Cassi standing in a bush 3 tiles from Ren counted 0 allies, next
  round (out of the bush) 3, and flipped fight/flee every other round until it died.

## 1. Measurements (baseline `_L0` = legend 25bed8d, engine 2.2.5)

360 games: `_L0` vs `_r2`, `_v6`, `_devci` and `_L0` itself, 45-map pool, both sides
(`node tools/analysis/coord_audit.mjs --split /tmp/coord/base/_L0_vs_*`). Per game, "us" = `_L0`:

| Metric | us | opponents |
|---|---|---|
| deaths (by champions / linked C&I / camps) | 13.5 (9.35 / 3.63 / 0.49) | 16.1 (11.1 / 4.3 / 0.65) |
| death cost, gem-equivalent (bag + 25 farming + 11 bounty) | 421 | 495 |
| champion deaths with no ally within 6 ("alone") | 29% (117 gem-eq/game) | 28% |
| ... with an ally within 10 that hit no enemy in the 3 rounds before ("help did not come") | **39% (155 gem-eq/game)** | 42% |
| ... with an ally that did hit ("joined") | 44% | 42% |
| ... locally outnumbered (within 6) while the team was not | 22% (82 gem-eq/game) | 17% |
| ... an engaged ally walked away and stopped hitting ("abandoned") | 6% (23 gem-eq/game) | 7% |
| ... carrying 20+ gems | 14% | 12% |
| kills, hitters per kill, solo kills | 11.1, 2.10, 30% | 9.35, 2.18, 26% |
| rounds with 2+ of our hitters in one fight that all hit one target ("focused") | 81% | 84% |
| fights (hit episodes) per game; share with fewer / equal / more of our bodies | 25.1; 21% / 59% / 20% | |
| net kills per fight when we are fewer / equal / more | **-0.17 / +0.05 / +0.48** | -0.48 / -0.05 / +0.17 |
| fights with one of our bodies idle within 10 | 45% | 47% |
| respawn walk-outs alone; died within 40 rounds alone vs with an ally | 30%; 10% vs 15% | 30%; 13% vs 19% |
| alive body-rounds with no ally within 8 | 28% | 28% |

- Lost games vs won games ("us"): deaths 18.7 vs 10.6; help-did-not-come cost 244 vs 108 gem-eq/game; alone 178 vs 84;
  net kills when we are fewer -0.77 vs +0.12.
- Idle allies at "help did not come" deaths (2,045): 57% were within 6 tiles, 21% at 7-8, 21% at 9-10; only 12% under
  half health, 18% carrying 20+, 12% hitting camps, 9% channelling; 53% were moving closer.
- Not problems: walking out of spawn alone (dies *less* often than walking out with an ally), focus fire (81%, same as
  the opponents), abandonment (6%).

Why help did not come (`coord_trace.mjs`, 32 traced games of `_L0` code vs `_r2`, 427 champion deaths, 261 idle allies):

| Idle ally's last decision | Count |
|---|---|
| saw the enemies and declined (combat() advantage < margin); 67 of 113 counted **no ally** (an=0) | 113 |
| ... of which fled (in reach 34, "isolated" walk-home 35) | 69 |
| walking to the rally alert, not there in time | 45 |
| farming (no enemy in its own view: hidden in a bush or beyond 9) | 44 |
| chose to fight, still walking in | 37 |
| no trace line (no enemy within 12, no alert within 12) | 35 |
| tribute / safety / home / shop | 31 |

- Victims: 54% were fighting when they died, 43% fleeing (adv < 0.5 for 43%). Of the 59 deaths with no ally within 10,
  54 were fleeing.
- Fight/flee flip-flops (fight, flee, fight in three rounds): 714 of 26,031 combat turns (2.7%); "allies counted" dropping
  from >0 to 0 while enemies stay in view: 926 of 28,409 (3.3%).

Conclusion: the costliest coordination failure is **help that does not come** (39% of champion deaths, 155 gem-eq per
game; 244 in lost games), then **lone deaths while fleeing**. Both come from each body judging a fight only with
allies within 6 of itself: a healthy ally 7-9 tiles away, or one hidden by a bush, is ignored, so a body next to a
teammate's fight computes it alone, declines and walks home, and a fleeing body walks home past its allies.

## 2. Mechanisms and A/B

(in progress)
