# 12. Intercontinental Fish against the ladder, 19 Oct 2026 (session 12)

Input: the user's second `INTERWIN.zip` (49 match archives, **45 distinct games**), now `experiments/interwin_oct19/<id>_<map>.repl26a`;
tables in `experiments/interwin_oct19/analysis/` (`run_all.py`, then `teamsum.py` / `micro.py` with the labels of `tools/strategy_v2/ictab.py`,
and the new `tools/strategy_v2/regap.py`). Replays carry no names: **IC** is the side that drafts the Stellar-first table
(5 champions Stellar, Ren, C&I, Ryth, Varg; 4: Stellar, Ren, C&I, Ryth; 3: Stellar, Ren, C&I; stampede and contest Stellar, Tavi, Prism,
C&I, Ren; rows Stellar, Prism, C&I, Varg; expanse C&I, Stellar, Varg). It plays in 44 of the 45 games (the 45th, an expanse mirror,
is left out). Opponents by draft profile: **R** Ren-first (Ren, Stellar, C&I, Ryth, Varg: the old ifish table), **T** Tavi / Willow
(sneaky-bush-like), **C** C&I-first with Tavi, **M** Varg- / Prism-first (Mite-like).

Local comparison: `legend_m14` vs the ifish proxy on the 17 official maps (`tools/strategy_v2/kpi_local.sh _pg3 _ifish`), the same tables.
Contest and stampede are left out of every farming number below (objective plans).

## 1. Results

IC wins 32 of 44: vs R 11-3, vs T 10-0, vs C 4-4, vs M 6-5. Its losses: stampede 3 of 4 (the opponents ring the objective with
casters and score 1080 by r464-566), contest 2 of 4 (0-0 or 400-600 on gold), monolith 2 of 3 (pure farming races: the C team
finished at r406, the R team at r413), and one each on ambush, rows, packs, pilgrimage, expanse.

## 2. What IC does better than its opponents (36 farming games)

| | IC | opponents | `legend_m14` (local, vs ifish proxy) |
|---|---|---|---|
| deaths per game | 3.2 | 7.1 | 7.6 |
| banked at r200 / r300 | 234 / 406 | 183 / 318 | 174 / 339 |
| captures per 100 rounds, r0-100 / r100-200 / r200-300 / r300-400 | 3.9 / 4.1 / 4.4 / 5.1 | 4.0 / 4.3 / 4.1 / 3.8 | 2.7 / 3.5 / 3.5 / 3.5 |
| body time: walk / camp / dead / idle | 48.5 / 23.1 / 8.1 / 1.2% | 43.9 / 19.9 / 17.1 / 4.5% | 52.1 / 17.3 / 12.8 / 4.0% |
| bank size: mean / median, banks per game | 62.5 / 58, 15.8 | 51.4 / 44, 12.2 | 56.7 / 44, 17.4 |
| recalls (arrived), health at the recall | 22.8, 0.40 | 27.6, 0.53 | 28.6, 0.64 |
| median distance to the nearest ally | 3.9 | 5.0 | 4.6 |
| respawned camp left unattacked (mean / p75 rounds) | 13.8 / 17 own, 8.7 / 13 neutral | 17.4 / 20, 13.2 / 16 | 26.5 / 35, 29.7 / 46 |
| first emblem, Stellar / Ren (median round) | 83 / 74 | | 172 / 79 |
| Stellar captures / gold per 100 alive rounds | 1.44 / 262 | 0.9 / 150 | 0.73 / 150 |

1. **It dies least.** IC fights more often on the enemy's half than anywhere else (311 of 672 engagements) and wins there 132 kills to 32
   deaths; on its own half the trade is even (33 to 46). It spends 37% of its time near enemies at distance 4-5 (ours 32%) and 3.2% at
   distance 1 (ours 7.9%), deals 54 and takes 29 per round at distance 4 (ours 35 / 25): spells from 4-5 (Stellar d5, Ren d4, Cassi d4,
   Ryth d5) open its fights, 228 openers to 164 suffered.
2. **Its captures speed up over the game; everyone else's stay flat** (table): Power emblems in the damage stat from r33-100 make
   every kill faster. IC's builds (emblem order in 36 games): Stellar PfE > HhE > DhE, Ren BhE > DhE > PfE, Cassi PfE > DfE > BhE,
   Issac PsE > HhE > DhE, Ryth BhE > DhE > PsE, Varg PsE > HhE; no Treasure, no Monster, no Jungle. **HhE is the Home emblem** (recall in
   3 turn ends instead of 5): bought second by every damage carry. Our bot never buys Home.
3. **Its Stellar is the team's collector**: 1.44 captures and 262 gold per 100 alive rounds (ours 0.73 / 150), first emblem at r83.
4. **Respawned camps are hit again sooner**: on its own half the camp stands 13.8 rounds on average after its respawn (p75 17); ours 26.5
   (p75 35). The median is the same (4-5 rounds): our loss is the long tail of camps that nobody comes back to.
5. **Bigger banks, half of them at the neutral altars** (287 neutral, 271 own), and recalls at 40% health (ours 64%): fewer trips home.
6. **The opening**: groups 2-3 fall 20-60 rounds sooner than ours on fragment (r24 vs r84), eight (2-elk group at r25 vs our first
   pair kill at r133), interlock (r31 vs r58), lanes and ambush (2-elk group r88 vs r151). The other maps open alike.

## 3. What our own traces showed (unopposed `legend_m14`, 17 official maps, `LEGEND_TRACE` build)

- **Camps abandoned after we hit them: 198 in 17 games** (lanes 28, rushbait-v2 27, interlock and fragment 16): 92 for a target that scored a
  little higher, 67 on the join limits (a lower-index ally claims the same light camp). Example (interlock, r20-59): Ryth hit the wolf at (5,21)
  three times, left it for a reward 12 steps away that Ren had already captured (Ren's claim vanished; Ryth could not see the tile), then for a
  group 24 steps away; the wolf died at r59. IC kills the same three wolves at r10, r21, r31.
- Body time unopposed: farm 64%, **wait 16.5%** (no group scores above zero: fragment 33%, contest 30%, rows 23%), tribute 12%, capture 6%.
- Respawned camps unopposed are re-hit quickly on most maps (corners 5.9 rounds, fragment 4.7); slow on interlock 25.8, lanes 21.8,
  pilgrimage 29.0, rushbait-v2 34.4: our long tail under opposition is mostly contact.

## 4. Tested in session 12 (A/B against `legend_m14`)

Full table with reasons: `SUGGESTIONS.md`. In short (pooled wins of 170 against five proxies; `legend_m14` 135, control 134):
Home emblem 114 / 120 / 132, IC builds 105, IC draft + builds 112, IC draft 119, `max_wait` 24 / 30 120 / 118, recall at 45-50% health
133 / 135, bigger banks 131 / 137 (h2h 13/34), bulk shopping 126-131, graded enemy-half risk 130 / 125, vanished-claim rule 125 / 124.
**Finishing the camp we started** (`commit_hit`, `commit_prog`): 125-132, but 18-22 of 34 head-to-head, 51/88 and 44/80 on the wider pools, and
6-7 rounds faster unopposed: the only lead, non-transitive, offered as a ladder candidate (`submissions/candidates/legend_m14_commit_20261019.zip`).
Nothing passed the rule (>= the shipped bot head-to-head and not worse against the proxies), so `legend_m14` stays shipped.
