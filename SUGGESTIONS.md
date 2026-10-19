# SUGGESTIONS: strategies that should work in theory but did not measure better (yet)

Kept for the user's review (session 12 request): every strategy tested against the shipped bot that is comparable to the meta in
theory, with why it should help, what was measured, and what would have to change for it to help. Newest first. A strategy that
passed and shipped is not listed here (see `submissions/BUILDS.md`).

How each was measured unless stated: a switch on a copy of the shipped bot (`legend_m14` = `_pg3`), the 17 official maps x 2 sides
against the five sparring proxies (Mite `_mite`, ifish `_ifish`, ladder-calibrated `_px9`, sneaky-bush `_snk`, pressure `_fA`):
170 games pooled, `legend_m14` wins **135 (79.4%)**. A control build with every new switch off plays 133-134 of them (fuel noise of
about +-2 games). Head-to-head = 34 games against `legend_m14` itself. Ledger rows: `experiments/results/ledger/<variant>_vs_*.jsonl`;
code: `experiments/wip/x_ic.patch` (switches in `params.h`, all off).

## Session 12 (19 Oct): copying Intercontinental Fish (ladder #1; analysis `docs/strategy_v2/12_IC_OCT19.md`)

| Strategy | Why it should help (evidence) | Variant | Pooled vs proxies (of 170) | h2h vs m14 | Verdict |
|---|---|---|---|---|---|
| **Home emblem second** on bodies whose first emblem is a damage emblem (Stellar, C&I, Issac, Varg in our builds) | IC buys Home (recall in 3 turn ends, not 5) second on Stellar, Issac, Varg; IC recalls 23 times a game, 44% of them capture-recalls; our bodies recall 29 times: 2 rounds saved per recall, fewer recalls broken by damage | `_ich1` (`ic_home` 1) | 114 (67.1) | 15 | worse: the 150 gold delays Treasure and the damage emblems; our recall timing already overlaps the capture |
| Home emblem second on every body | same | `_ich2` (`ic_home` 2) | 120 (70.6) | 16 | worse |
| Home emblem once a body has recalled 6 times (decided in the match from its own recall count, not by champion) | only the bodies that actually recall a lot pay for it | `_ich3` (`ic_home` 3) | 132 (77.6) | 17 | level / slightly worse (sneaky +3, ifish +2, Mite -3, `_px9` -2, `_fA` -3) |
| **IC's whole build order** (Power in the damage stat first on carries, Bruiser + Durability health on Ren / Ryth, Home second, Power forever) | IC's captures accelerate over the game (3.9 -> 5.1 per 100 rounds) while everyone else's stay flat; damage stat points per gold | `_icb` (`build_style` 11) | 105 (61.8) | 16 | clearly worse inside our brain (same as every top-team build since session 6): Monster gives 5 points + 10% camp damage for the same 150 gold, which is worth more than Power's 6 points on camps; our planner is calibrated on our builds |
| Wait longer for respawns (`max_wait` 18 -> 24) | IC re-hits respawned camps after 13.8 rounds on average, ours 26.5 | `_mw24` | 120 / 168 (71.4) | 15 | worse: bodies park instead of farming the next group |
| Wait even longer (`max_wait` 30) | same | `_mw30` | 118 (69.4) | 17 | worse |
| **Recall at lower health** (`cap_recall_hp` 0.61 -> 0.45 / 0.50) | IC's recalls happen at 40% health (median), ours at 64%: fewer trips home, more time on camps | `_crh45`, `_crh50` | 133 (78.2), 135 (79.4) | 16, 16 | level: no gain; the extra camp time is paid back in deaths / heal trips |
| **Bigger banks** (`tribute_min` 54 -> 66) | IC banks 58 gems (median) per trip, ours 44 | `_tm66` | 131 (77.1) | 19 | level / slightly worse vs the proxies, better head-to-head: non-transitive |
| Later first bank (`early_tribute_min` 22 -> 40) | same (IC's first bank r76, bigger) | `_etm40` | 137 (80.6) | 13 | beats the proxies by 2 games but loses head-to-head (13/34): fails the rule (non-transitive) |
