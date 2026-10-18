# 08. The top 3 against each other (ladder, 18 Oct 2026, session 9)

Input: 3 match groups the user downloaded where the top teams play **each other** (15 games, `experiments/ladder_top3/`,
replays in `repl/`), plus our `legend_m5` games against them (`experiments/ladder_m5/`; the "our fight with top 3" zip of this
session holds the same 3 groups as `ladder_m5/top4`: identical report). Made with `tools/strategy_v2/run_all.py`,
`teamsum.py` (named teams, per champion) and `micro.py` (fight micro: distance bands, hit ranges, openers).

Teams are identified by their per-map drafts (they draft the same way every time; `ladder_m5/*/team.csv`):

| Group | Side A | Side B | Result |
|---|---|---|---|
| 23206e46 | 3rd | 1st | 3rd 3-2 (contest 1000-0 with 80 kills, swirl, pilgrimage; 1st: eight, fragment) |
| 7b2474db | 2nd | 1st | 2nd 3-2 (rushbait 1024-920, stampede 1080-0, contest 0-0 on gold 18.2k-2.3k; 1st: corners, eight) |
| c47bab28 | 3rd | 1st | 1st 4-1 (rushbait, lanes, monolith, corners; 3rd: expanse) |

1st and 3rd draft identically on most maps (Ren, Stellar, C&I, Ryth, Varg); they differ on contest, stampede, expanse and rows.

## 1. Top-level games are farming races with few deaths; contest is a massacre

- Outside contest, a top-vs-top game ends at round 390-860 with 0-22 deaths a side (expanse 0-0, lanes 3-0, monolith 3-0,
  stampede 4-1, pilgrimage 6-8). Close races: rushbait 1024-920 and 726-1154, fragment 714-1020, corners 596-1030.
- Their **opposed** finish beats our **unopposed** pace on expanse (483 vs 570 rounds), lanes (443 vs 476), monolith (390 vs 407),
  stampede (484 vs 732) and equals it on rushbait (616-638 vs 612). Even with no fights at all we would lose those races.
- Unopposed our farming is as good as theirs opposed (camp damage per camp round 136 vs 97-127; 1,075 camp gems in 487 rounds).
  Against them it collapses: camp gems 578 per game (theirs 940-1,040), gold 2,581 (4,250-5,375), neutral captures 2.6 (7-10),
  14% of body-rounds dead (7-9%). The economy gap is made under opposition: deaths, lost neutral groups, less gold, fewer items.
- Contest: 2nd and 3rd crush 1st (deaths 98-9 and 97-8; 1st drafts Stellar, Tavi, Prism, C&I, Ren there). The loser dies 1-6 times
  per 100 rounds from round 0 and is spawn-camped from ~r900. 3rd then kills the two monoliths 5 times (1000-0 at r1998);
  2nd never banks a gem and wins on gold earned. We are the victim of the same pattern (55-84 deaths).

## 2. Fights are won by spells, and by whoever opens

| | 3rd / 2nd (vs 1st) | 1st (vs 2nd/3rd) | top (vs us) | us (vs top) |
|---|---|---|---|---|
| Spell share of champion damage | **82%** | **72%** | 58% | 48% |
| Stellar spell damage (15 games) | 74.7k | 65.7k | 49.8k | 20.8k |
| Cassi spell damage | 28.9k | 11.4k | 12.7k | 4.7k |

- Champion damage is mostly **spells from range 4-5**: 39-42% of spell damage lands at distance 4, 20-28% at distance 5
  (area spells: radius 1 around a point at range 4, so Stellar's area and Ryth's area stun reach 5). Ours: 53% at 4, **8% at 5**.
- **Openers** (first champion hit with no other within 8 tiles in the previous 10 rounds), excluding contest:

| | fights opened | damage in the 3 rounds from the opener (opener / other side) | fights opened on them | damage (them / opener) |
|---|---|---|---|---|
| top vs us | 129 | **391 / 58** | 74 | 149 / 322 |
| us vs top | 74 | 322 / 149 | 129 | 58 / 391 |
| 1st vs 2nd/3rd | 123 | 411 / 143 | 63 | 161 / 579 |
| 3rd vs 1st | 39 | 622 / 164 | 93 | 125 / 421 |

  The opener wins the first 3 rounds 3-7 to 1. Top openers: Ryth's area stun from 5, Stellar's area or damage spell from 4-5,
  Ren's stun from 4, Cassi's spell from 4. They open 129 times to our 74.
- Distance to the nearest enemy at the end of a round, and what the next round brings (per body-round, us vs top):

| distance | top: dealt / taken next round | us: dealt / taken |
|---|---|---|
| 1 | 81 / 63 | 48 / 74 |
| 2 | 55 / 34 | 32 / 57 |
| 3 | 34 / 14 | 16 / 28 |
| 4 | 29 / 14 | 19 / 20 |
| 5 | 13 / 3 | **3 / 12** |

  At distance 5 we stand inside their area-spell reach and cannot answer: our danger map (`build_danger`, `combat()`'s
  `reach_of`) counts every spell as reach 4. Between top teams, distance 5 is a trade (13-20 dealt, 10-14 taken).
- Death profile is the same at the top: 50-70% of deaths are bursts from above 60% health, 47-58% to ranged hits. Burst deaths
  are what fights between spell teams look like; what separates us is that we do not burst back.

## 3. Items: the damage stat, through the passives

Emblem orders (first 7 emblems, `body.csv` `emblems`; Xs/Xf/Xh = in strength / focus / health):

| Team | Pattern | Example |
|---|---|---|
| 3rd | **Treasure, Jungle, Durability in the damage stat, one Bruiser health, then Power in the damage stat** | Stellar 55:TfE 70:JfE 146:DfE 181:BhE 208:PfE ...; Cassi 48:TfE 127:DfE/JfE 319:PfE/BhE |
| 2nd | **Jungle in the damage stat first**, then Durability (damage stat), Bruiser health, Power forever | Varg 41:JsE 200:DsE 259:BhE 316:PsE; Ryth 65:JsE 150:DsE 212:BhE 252:PsE |
| 1st | Bruiser + Durability health on the frontline (Ren, Ryth), Power first on the damage dealers, then Power forever | Ren 41:BhE 102:DhE 236:PfE...; Issac 65:PsE 158:DhE 215:PsE; Stellar 38:PfE/DhE 122:PfE |
| us (`legend_m5`) | Monster / Treasure / Bruiser focus, Durability / Jungle health, Bruiser cycles; **Cassi & Issac health first** | |

Damage stat at round 300 (mean, non-contest games):

| Champion | 3rd/2nd (vs 1st) | 1st (vs 2nd/3rd) | top (vs us) | us vs top | us alone |
|---|---|---|---|---|---|
| Stellar focus | 240 | 198 | 191 | 166 | 210 |
| **Cassi focus** | **248** | 100 | 195 | **70** | **72** |
| Issac strength | 77 | 108 | 102 | 47 | 53 |
| Ren focus | 130 | 209 | 216 | 187 | 316 |

Our Cassi never buys focus before round 300 (`ci_health_first`): its damage spell does 140 where theirs does ~500.
Gold goes where the damage is: 3rd's Stellar and Cassi take 33% and 27% of the team's capture gold, 1st spreads it (Ren 24%,
Issac 22%), **our Ren takes 35-38%**.

## 4. What to build (session 9 plan)

1. **Fight: area reach 5 and openers** (agent `fight2`). Enemy area spells threaten 5, not 4 (danger map, `reach_of`, incoming);
   our area spells (Stellar, Prism; Ryth already) aim so the radius catches enemies at 5; with a spell ready and a fight chosen,
   cast from the longest reach instead of stepping in; out of a fight, do not end a turn at 4-5 from a ready enemy caster.
   KPIs (micro.py on local games): damage at distance 5 dealt/taken, openers, opener damage ratio.
2. **Economy: casters carry** (agent `econ2`). 3rd-team builds (Treasure, Jungle, Durability in the damage stat, one Bruiser
   health, Power forever), 2nd-team builds (Jungle in the damage stat first), Cassi focus builds; gold to Stellar and Cassi.
   Unopposed pace first, then head-to-head.
3. **A proxy with their tools**: `_px9` + area reach 5 + focus builds, so fight changes are judged against an opponent that opens
   from 5 and bursts with focus (built from the two agents' switches).
4. **Contest**: we are the spawn-camped side; later.
