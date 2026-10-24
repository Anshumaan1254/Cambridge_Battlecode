# Local benches (session 17, Oct 23 2026)

All runs: `python tools/live/localbench.py A god2_load` = 40 maps x both sides, release builds, cambc 3.0.5 / engine 1.0.3.
Local mirror games do **not** predict the ladder (established in sessions 15-17); these numbers only show regressions and whether a
module changes what it was built to change. Contact metrics come from `timebudget.mjs` / `walks.mjs` (rounds 0-1000).

| bot (all other god2 modules off) | wins / 80 | gems (us-them) | deaths (us-them) | notes |
|---|---|---|---|---|
| god2_load vs god2 (g8h) | 54 | 833-567 | 10.0-17.3 | role-slot draft + health builds |
| god2b (all 4 modules) vs god2_load | 32 | | 17.1-9.8 | leave-one-out: no fight 34, no bank 30, no deny 31 |
| fight only (`_g2f`) | 36 | 654-749 | 15.6-10.2 | farm under contact 6.6% vs 5.3%, walk-to-fight 164 vs 166 /body |
| fight + calm, no rally gate (`_g2c` v1) | 27 | 639-791 | 14.3-8.6 | farm under contact 7.3% |
| fight + calm + rally gate, commit off (`_g2c`) | 39 | 726-745 | 11.8-7.5 | farm 18.8% vs 17.2%, under contact 9.3% vs 5.3%, walk-to-fight 132 vs 156 |
| ... calm_out 0.9 / 1.2 | 39 / 34 | 711-720 / 699-784 | 11.9-7.6 / 12.8-8.2 | |
| ... god2 group veto (`g2f_grp 0`) | 40 | 734-799 | 12.0-8.2 | |
| ... ml2 exit bar 0.2 | 39 | 719-743 | 12.2-7.5 | |
| **walk budget 0.5 (`_g2w`)** | **47** | **717-660** | **12.0-13.5** | unopposed pace 1085.0 vs 1089.5 (no cost) |
| walk budget 1.0 | 45 | 728-666 | 12.4-12.9 | |
| walk budget 2.0 | 37 | 675-668 | 13.9-13.5 | |
| walk 0.5 + calm | 32 | 651-785 | 13.3-7.2 | |
| mid full (`_g2mf`) | 31 | 636-692 | 15.6-13.9 | |
| mid without the 35-round wait and golem plan (`_g2ml`) | 29 | 592-738 | 14.8-13.3 | |
| golem maps only (god2b, 12 games) | 4 / 12 | 680-780 | 17.8-14.2 | smoke test of the golem team plan: 0 faults |

Debug trace of the fight module (`tools/top2/pathtrace.py` on `team-a.stdout` of a local bundle): its farm-through rule applied to
2.7% of contact turns; our steps toward enemies came from combat() fights 30%, **rally answers 27%**, flee steps 22%, farm 13%.
