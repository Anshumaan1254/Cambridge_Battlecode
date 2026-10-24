# Powers: how champions use their abilities, ours vs the top 10 (replays, 2026-10-23)

## Data and method

- **Replays:** 611 in total.
  - 392 of ours against the top 10: `rp_bb4D` (200) and `rp_ft52D` (192). In these, **US** is our bodies and **OPP** is the top team in the same games.
  - 219 top-vs-top games, giving 438 team-games labelled **TT**.
  - OPP and TT agree closely on almost every rate, so the top teams use their powers the same way against us as against each other. TT is the clean reference.
- **Tools:** all are new and live in `tools/live/`.
  - `pw_casts.mjs`: run once per replay; uses the `spell_decode` variant that records end-turn events and stun flags.
  - `pw_agg.py`: aggregates the per-replay output.
  - `pw_fa.mjs` and `pw_fa_agg.py`: the action sequence of every turn that basic-attacks an enemy champion. Run on 200 games from bb4D plus 110 top-vs-top games.
  - `pw_kit.mjs`: the slot table shared by the scripts.
- **Outputs:** in `C:/battlecode/cache/an_powers/`.
  - `casts.jsonl`: per replay.
  - `agg.json`.
  - `report.txt`: all tables.
  - `fa.jsonl` and `fa_report.txt`.
  - To rerun: `python tools/live/pw_agg.py C:/battlecode/cache/an_powers/casts.jsonl` and `python tools/live/pw_fa_agg.py C:/battlecode/cache/an_powers/fa.jsonl`.
- **Definitions:**
  - **usable turn:** the body is alive and not channelling, stunned or rolled over.
  - **ready:** at least 8 rounds since the slot's last cast in this life. Respawn resets it, and so does a Vendetta kill of a champion.
  - **util:** casts × 8 / usable turns, i.e. the share of cooldown windows actually used.
  - **wait after ready:** the mean number of rounds a slot sat ready before each cast.
  - **Context of a turn**, decided before the body acts:
    - **in a fight:** the body hit or was hit by an enemy champion in the last 2 rounds, or was hit earlier this round. It splits into **fA** (attacked a champion this turn), **f4** (no champion attack, enemy within 4) and **fF** (enemy farther than 4).
    - **oA:** an opening attack on a champion.
    - **e4 / e6 / e9 / far:** not fighting, nearest enemy champion within 4 / 5-6 / 7-9 / farther.
  - **engagement (per body):** the rounds in which it hit or was hit by an enemy champion, with gaps of up to 3 rounds merged. "Substantive" means at least 2 exchange rounds or at least 3 hits.
    - Slot use relative to the first exchange round is classed as **pre** (rounds -2 to -1), **open** (0 to 1), **late** (2 or more) or **never**. Shares are of the engagements in which the slot was ready.
  - **outcome:** enemy and own champion deaths within 10 tiles and 15 rounds of the engagement start (kills, deaths, whether the body itself died). **net** = kills minus deaths.
- **Caveats:**
  - Targets are found by position: the tile of a unit spell, or radius 1 for area spells and the Heart of Ruin landing.
  - Vendetta's camp-kill resets are not seen.
  - Outcome links are correlations. The **never** bucket in particular mixes in engagements where the body never hit back.
  - Prism (25 bodies), Willow (37) and Tavi (53) are small samples on our side.

## 1. Cast rate and cooldown use

Casts per body per game, utilization, and mean rounds a ready slot waited.

| Champion | slot | kind | US bodies | casts/game US | OPP | TT | util US | OPP | TT | wait after ready US | OPP | TT |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HeartOfRuin | 0 | shield | 392 | **34** | 57 | 58 | **30%** | 48% | 51% | **11.2** | 6.9 | 6.6 |
| HeartOfRuin | 1 | dash (landing hit + stun) | 392 | 85 | 90 | 87 | 74% | 76% | 76% | 3.2 | 2.9 | 3.0 |
| Vendetta | 0 | reset | 361 | **37** | 60 | 53 | 33% | 51% | 47% | 12.8 | 9.1 | 9.5 |
| Vendetta | 1 | dash | 361 | **99** | 76 | 73 | 89% | 65% | 65% | 1.8 | 5.2 | 5.2 |
| VesperVale | 0 | reset | 355 | **35** | 55 | 51 | 30% | 45% | 44% | 14.6 | 9.6 | 10.3 |
| VesperVale | 1 | dash | 355 | **97** | 72 | 69 | 82% | 59% | 60% | 2.3 | 6.0 | 6.0 |
| Ryth | 0 | area stun | 333 | **35** | 49 | 51 | 30% | 40% | 43% | 14.2 | 10.8 | 9.6 |
| Ryth | 1 | reset | 333 | 26 | 37 | 33 | 23% | 30% | 28% | 16.2 | 15.1 | 16.1 |
| Marcella | 0 | enhanced reset | 134 | 27 | 36 | 30 | 22% | 29% | 26% | 16.4 | 16.4 | 17.8 |
| Marcella | 1 | damage | 134 | 41 | 45 | 44 | 34% | 37% | 38% | 12.2 | 12.6 | 12.2 |
| Prism | 0 | damage+stun | 25 | **30** | 48 | 44 | 23% | 40% | 39% | 18.1 | 10.5 | 10.8 |
| Prism | 1 | area | 25 | 41 | 50 | 48 | 32% | 42% | 43% | 14.7 | 9.9 | 9.5 |
| Tavi | 0 | reset | 53 | **29** | 51 | 46 | 23% | 40% | 41% | 17.2 | 10.1 | 10.3 |
| Tavi | 1 | damage+stun | 53 | **39** | 58 | 51 | 31% | 46% | 46% | 14.1 | 8.4 | 8.7 |
| Varg | 0 | reset | 77 | 30 | 41 | 36 | 26% | 35% | 27% | 14.5 | 14.3 | 18.2 |
| Varg | 1 | shield | 77 | **36** | 104 | 125 | **31%** | 89% | 94% | 10.7 | 1.3 | 0.8 |
| Willow | 0 | heal | 37 | 26 | 34 | 39 | 25% | 27% | 36% | 14.6 | 9.4 | 8.4 |
| Willow | 1 | reset | 37 | 29 | 31 | 32 | 29% | 24% | 29% | 13.2 | 16.6 | 15.2 |

(Alive rounds per body-game are about 840-1,130 in every group.)

- We **under-use every non-dash power**: resets, shields, Ryth's stun, and the Prism and Tavi damage spells. They are cast 30-65% less often and wait 1.5-2 times longer after coming off cooldown.
- We **over-use the plain dash**: VesperVale and Vendetta dash 97-99 times a game against 69-76.
- The plain-dash overuse is all outside fights. With an enemy 5-9 tiles away and no fight yet:

  | dash cast share of ready turns | e6 (5-6 tiles) | e9 (7-9 tiles) | far |
  |---|---|---|---|
  | VesperVale, ours | 50% | 45% | 29% |
  | VesperVale, TT | 9% | 11% | 15% |
  | Vendetta, ours | 59% | 48% | 36% |
  | Vendetta, TT | 16% | 15% | 16% |

  We dash into the approach: the "pre" share is 35-36% for us against 21-30% for the top teams (section 3b). Readiness when the fight starts ends up similar: 56% for us against 55-63% for them.

## 2. Targets

| spell | grp | n | on champion | on camp | empty | camp casts with an enemy within 6 / within 9 | 2+ champions hit |
|---|---|---|---|---|---|---|---|
| Ryth area stun | US | 11,708 | 43% | 53% | 4% | 3% / 10% | 16% |
| | TT | 13,095 | 40% | 55% | 5% | 7% / 22% | 22% |
| Heart of Ruin dash | US | 33,313 | 11% | 20% | 69% | 4% / 11% | 9% |
| | TT | 30,734 | 10% | 29% | 60% | 10% / 24% | 12% |
| Marcella damage | US | 5,530 | 32% | 63% | 4% | 2% / 7% | - |
| | TT | 15,381 | 34% | 61% | 5% | 9% / 25% | - |
| Prism damage+stun | US | 738 | 25% | 75% | 0% | 0% / 3% | - |
| | TT | 6,633 | 25% | 72% | 3% | 6% / 25% | - |
| Prism area | US | 1,031 | 20% | 72% | 8% | 1% / 4% | 6% |
| | TT | 7,275 | 26% | 68% | 6% | 8% / 26% | 18% |
| Tavi damage+stun | US | 2,061 | 23% | 67% | 9% | 1% / 7% | - |
| | TT | 3,715 | 25% | 66% | 8% | 6% / 26% | - |

- The champion-versus-camp split of damage and stun spells is about the same as the top teams'. The difference is **volume and context**.
  - The top teams put 22-29% of their camp casts in while an enemy stands within 9. We put in 3-11%, because of the hold rules.
  - So they get about 40-60% more camp casts per game from the same spells, without losing fight readiness. Their spells are ready at engagement start in 59-74% of engagements; ours in 70-89%, and the extra readiness does not show up in the outcomes (section 4).
- **Heals (Willow):** ours land on allies at 0.70 health missing 545 HP. TT's land at 0.63 missing 846; at least 300 HP missing in 61% of ours against 70% of theirs. This is about the same; 37 Willow bodies only.
- **Shields:**

  | shield | grp | hit in the cast round or the one before | hit within the next 5 rounds | mean health at cast |
  |---|---|---|---|---|
  | Heart of Ruin | US | 73% | 76% | 0.70 |
  | Heart of Ruin | TT | 52% | 67% | 0.81 |
  | Varg | US | 69% | 69% | 0.68 |
  | Varg | TT | 18% | 25% | 0.88 |

  Our Heart of Ruin shields react to damage already taken. Theirs are pre-emptive and still absorb as often. Top Varg shields on cooldown even when nothing hits them.

## 3. Fight usage

### 3a. Ready, then cast, in context

Cast share of ready turns.

| slot | grp | fA (in fight, attacked a champion) | f4 (in fight, enemy within 4, no attack) | oA (opening attack) | e4 (not fighting, enemy within 4) |
|---|---|---|---|---|---|
| Heart of Ruin shield | US | **51%** (n5,256) | 42% | **5%** | 17% |
| | TT | 84% | 61% | 35% | 36% |
| Heart of Ruin dash | US | **33%** | **2%** | 92% | **2%** |
| | TT | 72% | 32% | 96% | 21% |
| Vendetta reset | US | **41%** (n4,933) | 0% | 52% | 1% |
| | TT | 82% | 2% | 66% | 2% |
| VesperVale reset | US | 93% (n1,338) | 0% | 72% | 1% |
| | TT | 93% | 3% | 79% | 5% |
| Ryth area stun | US | **65%** | 27% | 26% | **18%** |
| | TT | 45% | 42% | 37% | 41% |
| Ryth reset | US | **33%** (n3,528) | 0% | 78% | 0% |
| | TT | 75% | 1% | 92% | 1% |
| Marcella enhanced reset | US | **45%** | 0% | 80% | 0% |
| | TT | 80% | 1% | 94% | 2% |
| Marcella damage | US | 28% | 17% | 16% | 26% |
| | TT | 48% | 38% | 23% | 40% |
| Varg reset | US | **29%** (n686) | 0% | 75% | 0% |
| | TT | 92% (n194) | 0% | 86% | 0% |
| Varg shield | US | 53% | 45% | 14% | 17% |
| | TT | 99% | 96% | 100% | 96% |
| Tavi damage+stun | US | 100% | 31% | 100% | 20% |
| | TT | 93% | 19% | 80% | 31% |

### 3b. Engagement timing

For each slot that was ready when the engagement started, when it was used. Shares are of ready engagements.

| slot | grp | eps | ready at start | pre | open | late | never | engagements in which the body never hit a champion |
|---|---|---|---|---|---|---|---|---|
| Heart of Ruin shield | US | 4,067 | 70% | **19%** | 27% | **38%** | **15%** | 13% |
| | TT | 3,428 | 56% | 47% | 38% | 12% | 3% | 12% |
| Heart of Ruin dash | US | 4,067 | 75% | 6% | 62% | 11% | **21%** | |
| | TT | 3,428 | 59% | 20% | 67% | 10% | 3% | |
| Vendetta reset | US | 3,986 | 86% | 1% | 42% | 20% | **37%** | 15% |
| | OPP / TT | 1,766 / 2,206 | 70 / 77% | 8 / 6% | 70 / 53% | 14 / 20% | 9 / 21% | 6 / 18% |
| Vendetta dash | US | 3,986 | 56% | 35% | 53% | 7% | 5% | |
| | TT | 2,206 | 59% | 29% | 43% | 15% | 13% | |
| VesperVale reset | US | 3,647 | 83% | 1% | 54% | 12% | **33%** | **30%** (87% of the "never" cases) |
| | TT | 4,755 | 68% | 7% | 73% | 12% | 7% | 7% |
| VesperVale dash | US | 3,647 | 56% | 36% | 32% | 15% | 17% | |
| | TT | 4,755 | 63% | 21% | 40% | 21% | 18% | |
| Ryth area stun | US | 2,767 | 70% | 1% | 74% | 15% | 11% | 7% |
| | TT | 2,625 | 59% | 2% | 85% | 8% | 5% | 5% |
| Ryth reset | US | 2,767 | 88% | 1% | 21% | 29% | 49% | |
| | OPP / TT | | 73 / 80% | 4 / 3% | 33 / 25% | 37 / 29% | 25 / 43% | |
| Marcella enhanced reset | US | 1,147 | 87% | 1% | 28% | 36% | 35% | |
| | OPP / TT | | 80 / 83% | | 48 / 29% | | 15 / 37% | |
| Marcella damage | US | 1,147 | 71% | 0% | 73% | 10% | 17% | |
| | TT | 2,913 | 65% | 3% | 82% | 7% | 8% | |
| Tavi damage+stun | US | 328 | 85% | 0% | 73% | 17% | 10% | |
| | TT | 736 | 74% | 3% | 79% | 10% | 8% | |
| Tavi reset | US | 328 | 86% | 0% | 29% | 24% | **47%** | |
| | TT | 736 | 70% | 8% | 56% | 22% | 14% | |
| Varg reset | US | 506 | 83% | 0% | 45% | 16% | **39%** | |
| | TT | 234 | 77% | 2% | 70% | 15% | 13% | |
| Varg shield | US | 506 | 69% | 22% | 34% | 31% | 12% | |
| | TT | 234 | 35% | 68% | 32% | 0% | 0% | |

**Who hits first:**

| grp | VesperVale | Tavi | Heart of Ruin |
|---|---|---|---|
| US | 44% | 55% | 40% |
| OPP | 68% | 82% | 46% |
| TT | 58% | 64% | 36% |

- When the enemy hits first our VesperVale dies in 35% of engagements, against 9% when it hits first. For TT the figures are 20% and 8%.

### 3c. Attack turns, in sequence

Turns with a basic attack on an enemy champion and the reset ready at turn start (`pw_fa`; 200 us-vs-top games plus 110 top-vs-top games).

Letters: A attack on a champion, R reset, M move, D dash, C other cast, r recall, `<` = ended farther from the enemy.

| champion | grp | turns | reset used | attack then move, no reset, per body-game | walk + reset + shot per body-game | most common sequences |
|---|---|---|---|---|---|---|
| Vendetta | US | 3,293 | **44%** | **6.2** | 0 | AM 32%, MARA 26%, ARA 16%, DMA 8% |
| | OPP / TT | 1,283 / 1,025 | 71 / 70% | 0.5 / 0.3 | 0 | MARA 24-32%, ARAM 10-11%, ARA 8-11% |
| Ryth | US | 2,201 | **40%** | **5.7** | 0 | AM 44%, MARA 27%, ARA 13%, AC 9% |
| | OPP / TT | 1,206 / 941 | 75 / 82% | 1.6 / 0.6 | 0 | MARA 27-34%, ARAM 15-17%, ARA 11-12% |
| Marcella | US | 756 | **54%** | **5.0** | 0 | AM 38%, MARA 35%, ARA 16% |
| | OPP / TT | 1,419 / 973 | 77 / 91% | 1.4 / 0.2 | 0 | MARA 27-42%, ARAM 12-14% |
| Varg | US | 321 | **41%** | **4.6** | 0 | AM 40%, MARA 25%, ARA 16% |
| | OPP / TT | 97 / 140 | 92 / 90% | 0 | 0 | MARA 44-59%, AMRA 16-19%, AMR 15-23% |
| VesperVale | US | 1,763 | 79% | 0 | **0** | ARA 77%, DA 19% |
| | OPP / TT | 2,692 / 2,901 | 88 / 87% | 0 | **4.6 / 6.0** | MRA 24-35%, ARA 29-31%, ARAr 11-20%, AD< 12-18% of the non-reset turns |
| Tavi | US | 275 | 67% | 0 | **0** | ARA 66%, CA 32% |
| | TT | 392 | 81% | 0 | 3.9 | ARA 38%, MRA 37%, CA 18% |
| Willow | US | 122 | 89% | 0 | **0** | ARA 89% |
| | TT | 193 | 98% | 0 | 3.4 | ARA 50%, MRA 47% |

- **Melee:** our missing resets are almost all **AM**: swing once, then step away. That is 57-81% of the reset-ready turns in which no reset was cast. The top teams double-hit before leaving (**ARAM**, AMRA).
- **Ranged:** the top teams walk into range, reset and shoot in the same turn (**MRA**). We never do. Our VesperVale instead dashes in (DA), which spends the turn's one cast. `SV.stepin_shot` (strat bit 2097152, `engage()` contact block) is being added for this already; these numbers support it.
- **Heart of Ruin** in attack turns:

  | grp | shield ready → cast | dash ready → cast | sequences |
  |---|---|---|---|
  | US | 32% → 44% | 36% → 45% | AM 28%, A 25%, MA 16%, DA 16% |
  | TT | 18% → 74% | 25% → 76% | |

### 3d. Dashes

Classes by the nearest enemy champion within 8 at the cast: travel (none within 8), engage (closer), escape (farther), lateral.

| dash | grp | n | travel | engage | escape | lateral | engage and attack in the same turn | walked before dashing (enemy near) |
|---|---|---|---|---|---|---|---|---|
| VesperVale | US | 34,553 | 68% | 14% | 16% | 2% | 22% | **0%** |
| | TT | 29,668 | 67% | 14% | 17% | 3% | 44% | 7% |
| Vendetta | US | 35,890 | 68% | 16% | 14% | 2% | 30% | **1%** |
| | TT | 19,482 | 70% | 12% | 15% | 2% | 30% | 17% |
| Heart of Ruin | US | 33,313 | **82%** | 12% | **3%** | 3% | 68% | **0%** |
| | TT | 30,734 | 69% | 14% | 11% | 6% | 50% | 12% |

- **Heart of Ruin strikes on champions** (the landing hits a champion):

  | grp | strikes | walked first | attacked after | enemy at distance 1 / 2 / 3 at the cast |
  |---|---|---|---|---|
  | US | 3,703 | **0%** | 87% | 21 / 29 / 50% |
  | TT | 3,087 | 19% | 70% | 28 / 28 / 44% |

  - We only strike from 3 tiles or closer; `strike_dash_at` needs the enemy within dash range + radius. The top teams also strike from 4: walk 1, then dash.
- **Heart of Ruin in fights with the dash ready and not cast:**

  | grp | fight-idle turns per body-game | moved away (walking) |
  |---|---|---|
  | US | 23 | 61% (about 14 turns per game) |
  | TT | 7 | 31% (about 2 turns per game) |

  In engagements where our Heart of Ruin never hit back, its dash was ready in 66% and used in 15%. TT used it in 57%; most of those are escape dashes.

### 3e. Stuns

| stunner | grp | n | target had already acted this round | target was channelling | followed up (an ally hit the target before it acted again) | target died within 3 rounds | cast in the engagement's opening rounds |
|---|---|---|---|---|---|---|---|
| Ryth area stun | US | 5,991 | 34% | 28% | 37% | 7% | 67% |
| | TT | 6,558 | 55% | 20% | 28% | 6% | 70% |
| Heart of Ruin dash | US | 4,050 | 60% | 31% | 87% | 17% | 55% |
| | TT | 3,497 | 50% | 22% | 78% | 16% | 42% |
| Tavi damage+stun | US | 484 | 40% | 33% | 50% | 9% | 77% |
| | TT | 944 | 59% | 35% | 57% | 12% | 69% |
| Prism damage+stun | US | 182 | 53% | 32% | 54% | 10% | 63% |
| | TT | 1,660 | 58% | 22% | 54% | 17% | 65% |

- Stun targets follow the enemy draft for both sides: Heart of Ruin about 25%, VesperVale about 22%, Ryth 14-18%, Vendetta 10-15%.
- Our stuns are about as early and as well followed up as theirs.
- Ryth's and Tavi's stuns land more often on targets that have not yet acted this round (34-40% after the target acted, against 55-59%). That denies the current turn instead of the next, which is about equal in value.
- No stun problem stands out except Ryth's ordering in melee contact (3a and 3c: the stun takes the contact turn, so the reset is lost).

## 4. Outcome links

Kills and deaths within 10 tiles and 15 rounds of the engagement start. **net** = (kills − deaths) per engagement.

TT, engagements where the slot was ready at start, with our max-health sum within 6 at least theirs ("ahead"). Early = pre or open.

| slot | early net (n) | late net (n) | never net (n) |
|---|---|---|---|
| VesperVale reset | **+0.30** (1,759) | +0.18 (240) | -0.19 (114) |
| Marcella damage | **+0.23** (1,064) | +0.04 (80) | -0.29 (52) |
| Heart of Ruin shield | **+0.19** (1,076) | +0.02 (149) | -0.10 (42) |
| Heart of Ruin dash | +0.20 (1,234) | +0.15 (117) | -0.16 (37) |
| Ryth area stun | **+0.14** (897) | +0.01 (91) | -0.32 (28) |
| Tavi damage+stun | **+0.15** (321) | 0.00 (23) | -0.30 (20) |
| Vendetta reset | +0.32 (698) | +0.26 (210) | +0.02 (179) |

- **For the top teams, early use goes with better local outcomes** for every slot, by +0.05 to +0.2 net per engagement.
- **Ours shows little early/late difference** ("ahead" stratum):

  | slot | early net | late net |
  |---|---|---|
  | VesperVale reset | +0.08 | +0.11 |
  | Heart of Ruin shield | -0.05 | -0.03 |
  | Vendetta reset | +0.17 | +0.14 |
  | Ryth area stun | -0.06 | 0.00 |

  Our early casts happen inside fights we lose for other reasons (item power, being hit first).
- **"Never" is the worst bucket for every champion and both groups.** For us:

  | slot | net when never used | self died |
  |---|---|---|
  | Heart of Ruin dash | -0.49 (ahead) / -0.70 (behind) | 29-49% |
  | VesperVale reset | -0.49 / -0.67 | 35-53% |
  | Vendetta reset | -0.40 / -0.66 | 31-48% |
  | Ryth reset | -0.26 / -0.62 | 22-43% |

  Part of this is selection: an engagement in which the body never hits back is one it is losing. Part is lost damage.
- **Who hits first** (all engagements):

  | grp | VesperVale died, we hit first | VesperVale died, they hit first | Vendetta died, we / they hit first | Heart of Ruin died, we / they hit first |
  |---|---|---|---|---|
  | US | 9% | 35% | 13% / 32% | 12% / 27% |
  | TT | 8% | 20% | | |

  The first hit matters most for ranged bodies. That is what the walk + reset + shot pattern buys.

## 5. Per-champion differences that cost us

- **Heart of Ruin (all 392 games):**
  - The shield waits until health is below 90%. It is cast before contact in 19% of engagements (top teams 47%), 34 times a game against 58, and is never used in 15% of ready engagements (top teams 3%).
  - The dash is held within 9 tiles of any enemy (`strike_dash_hold`). So it is spent on travel far away: 82% travel against 69%, and 48% cast share when far against 25%.
  - It is almost never used to escape: 3% of dashes against 11%. Our Heart of Ruin walks away with the dash ready about 14 turns a game; the top teams' do so about 2.
  - We strike only from 3 tiles or closer. The top teams walk 1 and then strike in 19% of their strikes.
  - When our strikes do happen they are good: 68% hit and attack in the same turn, against 50%.
- **Vendetta:**
  - Uses the reset in 44% of its reset-ready champion-attack turns, against 70%. That is 6.2 turns per game of swing-then-step without the second swing.
  - Its dash is spent in the approach: 59% / 48% of ready turns with an enemy at 5-6 / 7-9 tiles, against 16% / 15%. Dash-then-attack also takes the reset's cast (3.8 times per game, against 1.9).
- **VesperVale:**
  - Its reset use in attack turns is fine (93%).
  - It never hit an enemy champion in 30% of its engagements (top teams 7%); those are 87% of its "never used the reset" cases. It is hit first more often: we hit first in 44% of engagements, against 58-68%.
  - It never walks + resets + shoots; the top teams do so 4.6-6.0 times per game. It dashes in instead.
  - It never shoots and then dashes away (AD<); the top teams do so in 12-18% of their non-reset attack turns.
- **Ryth:**
  - Reset in 40% of reset-ready attack turns, against 75-82%. AM is 44% of its attack sequences: 5.7 per game.
  - In melee contact the area stun is cast first (65% of attack turns, against 45%), which takes the turn's cast from the reset.
  - It stuns before contact less often (e4: 18% of ready turns, against 41%).
  - The stun is held near enemies (`hold_cc_dist` 7; en-route casting is off for stuns): 35 casts a game against 51.
- **Marcella:** reset in 54% of reset-ready attack turns, against 77-91% (AM, 5.0 per game). Its damage spell in fights: 28% of fA ready turns, against 48%.
- **Varg:**
  - Reset in 41% of reset-ready attack turns, against 90-92% (AM, 4.6 per game).
  - The shield needs health below 90% plus an enemy or camp within reach: 36 casts a game against 104-125, and fA 53% against 99%.
- **Prism and Tavi (small samples):**
  - Their damage+stun counts as cc, so it is held when an enemy is within 7 and never cast en route: 30 and 39 casts a game, against 44-51 and 51-58.
  - Tavi never walks + resets + shoots: 0 against 3.9 per game.

## 6. Proposed casting changes

Ranked by expected value. All are in `bots/bb4/src/brain.cpp`. Line numbers are as of 15:36 today; the file is being edited, so search for the quoted code.

1. **Melee: hit twice before stepping away.**
   - **Where:** `combat()`, in-reach flee branch:
     - the `exec_flee_hit` swing (about line 3934: `if (P.exec_flee_hit && !kit.ranged && can_attack) if (Enemy* o = best_in_reach(nullptr)) attack_unit(*o->ch);`);
     - the step-then-swing after `toward_help() || go_home_step(true)` (about line 3987, "Melee champions can still swing after walking");
     - `engage()`'s `exec_hit_first` melee swing (about line 4105, "melee: then still walk toward the target below"). Nothing after it can use the reset, because `can_attack` is false by then.
   - **Change:** after the swing, if the target is alive, `!cast_done`, `ready(kit.reset)`, and no flee stun is about to be cast this turn, call `cast_self(kit.reset)` and attack again. That turns AM into ARAM, the top teams' pattern.
   - **Evidence:** our Vendetta, Ryth, Marcella and Varg use the reset in 40-54% of reset-ready champion-attack turns against 70-92%. That is 4.6-6.2 lost basic attacks per melee body per game, all against champions in contact.
   - **Risk:** small. The reset is a self-cast, and melee can attack and walk in one turn.
2. **Ranged: walk + reset + shoot** (VesperVale, Tavi, Willow).
   - **Status:** already being built as `SV.stepin_shot` (the `engage()` contact block and `edge_hold`).
   - **Evidence:** the top teams do it 4.6-6.0 times per game with VesperVale, 3.9 with Tavi and 3.4 with Willow; we do it 0 times. Our VesperVale hits first in 44% of engagements against 58-68%, and dies in 35% of the engagements where it is hit first.
   - **Suggestions:**
     - Turn it on for every kit with `kit.ranged && kit.reset >= 0`.
     - In the dash-in branch (about line 4250, `if (d <= kit.attack_range + 2 && ready(kit.dash))`), prefer walk + reset when the target is exactly `attack_range + 1` away. That keeps the dash; dash-in followed by a shot spends the cast that the reset would need (DA: 19% of VesperVale's reset-ready attack turns).
3. **Heart of Ruin, and Varg's shield: cast it pre-emptively in fights.**
   - **Where:** `support_spells()` (about line 2616): `if (kit.shield >= 0 && ready(kit.shield) && hp < 0.9f * max_hp && (in_awake_camp_range() || enemies_within(4) > 0))`.
   - **Change:** drop the `hp < 0.9f * max_hp` condition whenever an enemy champion is within 4-5, or when `combat()` decided to fight. Keep it for camps only. Keep the `hor_strike` deferral, but cast at turn end through `shield_deferred` whenever the strike did not happen.
   - **Evidence:**
     - Heart of Ruin: shield before contact in 19% of engagements against 47%, never used in 15% against 3%, 34 casts a game against 58, fA cast share 51% against 84%. Early shield is the better outcome for TT: +0.19 net against +0.02 for late.
     - Varg: fA 53% against 99%, e4 17% against 96%.
4. **Heart of Ruin: the dash to escape, and walk-then-strike.**
   - **Escape:** `mob_dash()` (about line 2195) returns -1 within `strike_dash_hold` (9) of any enemy unless `strike_dash` is set. So `go_home_step(true)` in the flee branches never dashes. Allow it when `task == T_FLEE`, at least when in reach or below about 50% health.
     - Evidence: escape dashes are 3% of ours against 11%. In passive engagements the dash was used in 15% against 57%. We walk away with the dash ready about 14 turns a game against 2.
   - **Strike reach:** in `engage()`'s melee branch, after `step(goal, false, true), dbg_eng = 5` (about line 4315), retry `strike_dash_at(e)` and then attack. This is the top teams' walk-1-then-strike, 19% of their strikes; we strike only from 3 tiles or closer today.
5. **Hold spells only when a fight can start next turn.**
   - **Where:** `params.h`: `hold_spell_dist = 6`, `hold_cc_dist = 7`, `strike_dash_hold = 9`. `cast_en_route()` refuses whenever `enemies_within(9) > 0` (about line 7835). The holds are read in `farm_group()` and `ring_farm()` (about lines 8037 and 5764). Stun-type damage spells (Prism and Tavi damage+stun, Ryth's area stun) are excluded from en-route casting (`cast_en_route < 2`).
   - **Evidence:**
     - The top teams put 22-29% of their camp casts in with an enemy within 9; we put in 3-11%.
     - Our utilization is far lower: Ryth stun 30% against 43%, Prism 23% against 39%, Tavi stun 31% against 46%, Heart of Ruin camp dashes 20% against 29% of dashes.
     - Our extra readiness at fight start (70-89% against 59-74%) did not buy better early-use outcomes.
   - **Proposal:** A/B test `hold_spell_dist` and `hold_cc_dist` at 4-5, and `strike_dash_hold` at 5-6 for camp casts.
6. **Ryth in melee contact: attack, reset, attack before the area stun.**
   - **Where:** `engage()` contact block, `if (!cast_done && kit.aoe >= 0 && kit.aoe_stuns) cast_ground(kit.aoe, e.pos);`, which comes before `attack_unit(ec)` (about line 4365).
   - **Change:** when the reset is ready, attack, reset and attack first, and stun only if the reset was not used. Keep `melee_aoe_stun` for the stun from 2-4 tiles before contact, where the top teams cast it (e4: 41% against our 18%).
   - **Evidence:** the stun takes 65% of our contact turns against 45%, and the reset is used in 33% against 75% of fA turns. This one is weaker: TT Ryth also leaves the reset unused in 43% of engagements.
7. **VesperVale kite: shoot, then dash away from a melee chaser** (AD<, 12-18% of the top teams' non-reset attack turns; never for us).
   - **Where:** today the dash is only taken by Nav before the walk.
   - **Change:** in the in-reach flee branch, a ranged body that can still attack could shoot first and then dash, instead of walking with no shot.
   - **Value:** lower, but it addresses VesperVale's 30% passive engagements.
8. **Minor: Marcella's damage spell** is cast before the attack in contact (`if (!cast_done && kit.dmg >= 0 && focus * kit.dmg_mod > str)`), which takes the cast from the enhanced reset. CA is 3-7% of her reset-ready attack turns. Not a priority.

### Not changes

- The dash budget for VesperVale and Vendetta is not a problem for fight readiness: 56% ready at engagement start against 55-63%. It is a problem for the reset only through dash-then-attack.
- Our stuns' targets and follow-up are in line with the top teams.
