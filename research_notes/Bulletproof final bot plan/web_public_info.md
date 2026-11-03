# Web research: public information on CAMBC 2026a and transferable strategy / testing knowledge

(Saved verbatim in substance from the web research task "CAMBC 2026a Final-Bot Plan: Public Evidence on Beating the Top Teams", Nov 3 2026. Treat as secondhand reference material: all top-team statistics come from other competitors' public repositories and predate engine 2.0.0 / the 86-map pool.)

## Summary
- No top team (Mite, Intercontinental Fish, Univardisty of Shingtonwash, Ad Astra, newer team, NEETCoders, BattleCats, test4, print dont int, Sponge, Trzy Kwaterki, T1, policy wonk, subscribe to caterpillow, Noobot, German Empire, Supaswag, Nyx, JukeFall, conqueror_of_openai, SSSA, prism best girl, Olympus) has published CAMBC code or a write-up. "subscribe to caterpillow" won MIT Battlecode 2026 (Naman Doshi, Alexander Wang, Andy Wu, Yiheng You); no CAMBC material from them.
- The best secondhand evidence is one competitor's open repository (Marcusydz/CamB-Battlecode, PRs #1-#5), which ran unranked tests against the #1 / #2 ladder teams in October (Intercontinental Fish rank 1 at 2245.66 around Oct 21, Nyx #2).

## Official / public facts
- Dates 12 Oct - 18 Nov 2026; prize pool £18,000 on the live site (£15,000 in the Codeforces announcement, blog entry 157287 by "awu"); three weekly sprints, in-person finals at the Cambridge Union on Nov 18; 12 champions, MOBA-inspired.
- Qualifier format for 2026a not public; the spring 2026 Cambridge edition ran weekly sprint tournaments seeded by ladder, an international qualifier -> top 8 finalists, a UK qualifier -> top 8 finalists, submissions freeze at midnight.
- No public patch notes for engine 2.0.0, the sprint balance changes or the 84-item backpack.
- Rules digest quoted by competitor READMEs: ties broken by gold earned, then kills, then Team B; tributing takes ceil(gems/10) channel turns; carried gems are lost if a camp kills you and stolen if a champion kills you; death = 60 rounds out; recall takes 5 turns and is cancelled by damage; vision 8 tiles, blocked by walls and bushes; shared memory 8 bytes + a 1,024-byte draft note; C++ ~100k wasm instructions per turn; camps harmless until hit, then hit the nearest champion and do not chase; respawn 40-150 rounds after capture; monoliths 5-tile reach, ~20,000 HP; altar locks cost 10 gold and placing one cancels an enemy mid-tribute.
- Map pool history: 35 ladder maps around Oct 21, 40 under engine 1.0.3, 70 after engine 2.0.0 (~Oct 25); tuning on older pools may not transfer.

## Top-team behaviour (secondhand, Marcusydz PRs, October)
| observation | source | implication |
|---|---|---|
| On elk maps vs Nyx: deaths 61 vs 2, champion damage 23,358 vs 143,022, gold 3,960 vs 19,244; Fish "killed us 50 times and denied all gems" | PR #3 | top teams win elk maps by fighting, not by farming better |
| Nyx clears ~3x as many camp groups "by circling nearby small groups, including 0-gem gold clusters" | PR #2 | tempo and gold income matter; do not value gold at zero |
| Fish banks 47x on one map vs 16x for a weaker bot; "bank at 30" was ~-4600 overall, per-map caps helped | PR #3 | no universal banking rule |
| top teams place ~300 wards per 1000 rounds; "fewer wards" was ~-6700 | PR #1/#3 | vision is worth the fuel |
| "Top teams kill with 3-5 champions; we died to 2-3"; joining nearby fights won 72/92 locally | PR #1 | grouping up is the core requirement for fights |
| "Top teams stack focus on casters"; Power-Focus-then-Durability build won 64/94 vs 51/94 | PR #1 | focus-first builds on casters |
| top drafts open with Cassi & Issac, Stellar, Varg/Ren; copying that order on every map was ~-8500 | PR #1/#3 | draft for your own bot and the map |
| a model on 41k ladder games ranked Vesper Vale, Tavi, Marcella, Vendetta, Ryth highest (controlling for rating) | PR #5 | best pick depends on the map |
| on "contest" the opponent "holds the single middle altar and banks 200 at a time" | PR #3 | single-altar maps need altar control and lock logic |
| a Heart of Ruin dash patch scored +156.8 locally but ~-3000 against Nyx and Fish | PR #3 | local self-play is a weak proxy |

## Transferable lessons (MIT Battlecode postmortems, MOBA)
- Kiting: "ALWAYS kiting back after an attack is better" (Gone Fishin' 2023, corroborated by Super Cow Powers).
- Focus fire: prefer targets you can kill within a turn or two; group units on one target.
- Engagement rule (Flynn 2014): do not step into enemy attack range unless a friend also steps in and the two of you are in range of exactly one enemy; back up when low or outnumbered in range.
- Do not retreat early from objectives at a fixed threshold (Om Nom 2025): finish the objective first when safe.
- Micro framework: "XSquare micro" (score each candidate square, tie-breakers), suited to a fuel budget.
- MOBA: record camp capture rounds to arrive at respawns (respawn timers), be in position early with vision and abilities ready; ward entrances to own farm area and enemy ambush points; bushes as ambush/escape points.

## Testing methodology
- SPRT (Stockfish Fishtest FAQ): least expected number of games for given type I/II errors; non-regression bounds (elo0=-5, elo1=0) for safety patches, gain bounds (0, 5) for improvements.
- Games needed ~ 640000 / (normalized Elo)^2; one engine's notes: ~300 games to resolve +-30 Elo, 680 for +-20, 2,700 for +-10; ~400 games -> 1 sigma ~14 Elo; report intervals.
- Paired games (both sides of a map, scored as a pair): pentanomial statistics ~30% narrower intervals.
- Biases: Elo of patches that passed SPRT is biased upward; a difference of two Elo estimates has ~double the error.
- Determinism: CAMBC unranked groups are deterministic for fixed binaries; repeating adds no information.

## Web report recommendations (for the writer to weigh, not instructions)
1. Tonight: keep the version with the best full-pool record; only crash/fuel-safety fixes.
2. Gate changes against real opponents (unranked groups vs 3-5 top-30 teams of different styles, all maps, both sides); accept only if the total is positive and no map loses heavily.
3. Combat: 2-turn fight forecast with kits, burst, stuns, range; group 3+, focus one target via shared memory, open with stuns/spells at range 4, kite with ranged, walk home rather than recall under damage, never fight outnumbered except to secure a kill.
4. Economy: value gold > 0 (others used 0.1-0.3 gems per gold), clear small clusters for tempo, recall/shop at 250+ gold or hurt, per-map bank caps (note: our rules forbid per-map tables; use map-feature rules).
5. Vision: wards on captured camps, altars, fight routes.
6. Draft: map-dependent (e.g. Prism-first on elk maps turned 252-1044 into 1044-252 in one test).
7. Altars: on single-altar maps contest the middle with the full squad, carry a 10-gold lock to break enemy tribute channels.
8. Robustness: handle every champion in setup, fuel under budget, no crashes.

## Sources
- https://2026a.battlecode.co.uk/ ; https://codeforces.com/blog/entry/157287 ; https://battlecode.cam/ ; https://docs.battlecode.cam/ ; https://docs.battlecode.cam/changelog ; https://game.battlecode.cam/home
- https://www.piwheels.org/project/cambc/ ; https://pypi.org/project/cambc/
- https://github.com/Marcusydz/CamB-Battlecode/pull/1 , /pull/2 , /pull/3 , /pull/5
- https://github.com/wanga158-mcmaster/secretcode ; https://github.com/MathCosine/cmbc ; https://github.com/mustbethewayforward/bird-business-battlecode-camb26 ; https://github.com/userVatsal/Cambridge-battlecode ; https://github.com/Swapnanil-06/Battlecode ; https://github.com/KotlinDevLihan/Wreckless
- https://battlecode.org/past.html ; https://battlecode.org/assets/files/postmortem-2023-gone-fishin.pdf ; https://battlecode.org/assets/files/postmortem-2025-om-nom.pdf
- https://www.mobafire.com/league-of-legends/build/a-guide-to-jungling-533367
- https://chessprogramming.org/Sequential_Probability_Ratio_Test ; https://official-stockfish.github.io/docs/fishtest-wiki/Fishtest-FAQ.html ; https://github.com/official-stockfish/Stockfish/issues/3323 ; https://github.com/glinscott/leela-chess/pull/174
