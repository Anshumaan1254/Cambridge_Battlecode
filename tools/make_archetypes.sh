#!/bin/bash
# Opponent archetypes from the ladder teams that beat legend_st 16-1 (experiments/ladder_oct18/,
# docs/HOUSEOFCODERS_ENEMY_STRATEGY_REPORT.md). Our code with their drafts, their builds (build_style 3 / 4) and their
# style; not faithful clones (their code is not available), but closer to them than our own past builds.
#   tools/make_archetypes.sh            # from bots/legend
#   SRC=bots/_rm tools/make_archetypes.sh
#   _eA  Ren-first pressure (13 of 17 games): Ren, Stellar, C&I, Ryth, Varg; Durability/Bruiser health early then Power
#        stacks; fights more readily, farms the enemy half, starts in the PUSH stance
#   _eB  CI-first farming (rows, expanse): C&I, Stellar, Varg, Ren; Monster then Power; solo camps (no joins), no denial
#   _eC  caster objective (contest, stampede): Stellar, Tavi, Prism, C&I, Ren; health then Power; plans lone monoliths
#   _eD  group hunter: the Ren-first draft playing a grouped opening (deathball until r250) with the pressure settings
# Draft ids (bc::champion_draft): Ryth 0, Vesper 1, Vendetta 2, C&I 3, Stellar 4, Prism 5, Marcella 6, Willow 7, Ren 8,
# Varg 9, Tavi 10.
set -e
cd "$(dirname "$0")/.."
export SRC=${SRC:-bots/legend}
PRESS="fight_margin=1.1f isolated_fight_adv=1.2f steal_hp_frac=0.4f enemy_half_penalty=4.f deny_bonus=0.4f"
tools/variant.sh _eA build_style=3 $PRESS gank_bag=15 q0_push=0.5f --define "LEGEND_DRAFT 8,4,3,0,9"
tools/variant.sh _eB build_style=4 max_join=0 deny_bonus=0.f --define "LEGEND_DRAFT 3,4,9,8,0"
tools/variant.sh _eC build_style=3 obj_min_attackers=1 $PRESS --define "LEGEND_DRAFT 4,10,5,3,8"
tools/variant.sh _eD build_style=3 $PRESS gank_bag=15 deathball_until=250 --define "LEGEND_DRAFT 8,4,3,0,9"
for b in _eA _eB _eC _eD; do cambc build $b >/dev/null && echo "built $b"; done
