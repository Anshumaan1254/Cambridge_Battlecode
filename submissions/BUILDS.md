# Submission builds

`submissions/legend.zip` is always the latest recommended build (`cambc bundle legend` output: the bot's
`src/` only). Upload it on the platform's Submissions page, or run `cambc submit legend`. Older builds are
kept in `submissions/history/` so any of them can be re-submitted. Win rates are from the local 45-map panel
(27 generated + 12 ladder + 6 official maps, both sides, 90 games per cell) unless stated.

| Build (zip in history/) | Code commit | What it contains | Measured |
|---|---|---|---|
| **legend_econ_20261017.zip** (= current legend.zip) | see `git log -- submissions/legend.zip` | everything below + the economy patch: Bruiser emblems instead of Power (7 stat points vs 6 for 150 gold), build lists that never run out, health first for Cassi & Issac, Treasure as the second emblem for Ren/Stellar, Monster's +10% in the kill-time estimate | economy patch on `_r2`: 60% head-to-head vs `_r2`, panel mean 79.1% vs 77.6%; promoted build vs `_v6` on the 12 ladder maps: 17/24, 0 faults, 1.8 lost turns per game (opponent 62) |
| legend_564785f_r2-learner-noexplore.zip | 564785f | fuel fix (566 -> 12 lost turns on the 98x99 map), review fixes, reworked stance learner without exploration, refreshed draft values | learner without exploration: panel mean 80.0% (vs `_v6` 77.8, `_hunt` 90.0, `_hunt2` 96.7, `_devci` 66.7, `_base` 86.7, `_r1` 62.2) |
| (not archived) 6bb913e / 58c2fe4 zips | 6bb913e, 58c2fe4 | v5 (on the ladder Oct 16) and the first rewrite | rebuild with `git show <commit>:submissions/legend.zip > old.zip` |

Before replacing `legend.zip`: run the panel (`tools/make_sparring.sh` once, then `tools/panel.sh legend
'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a' _v6 _hunt _hunt2 _devci _base`), check 0 faults and lost
turns with `decode(..., {rollovers: true})`, copy the new zip into `history/`, and add a row here.
