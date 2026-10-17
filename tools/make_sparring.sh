#!/bin/bash
# Recreate the git-ignored sparring panel (bots/_*) used by every A/B table in docs and AGENTS.md:
# frozen past versions of legend plus aggressive archetypes built on the 58c2fe4 code with ladder drafts.
#   tools/make_sparring.sh          # then: tools/panel.sh legend 'maps/*.map26a,maps/ladder/*.map26a,maps/comp/*.map26a' _v6 _hunt _hunt2 _devci _base
set -e
cd "$(dirname "$0")/.."
tools/snapshot.sh _base 6bb913e   # v5: what was on the ladder on Oct 16 (lost 17 of 20 scrims)
tools/snapshot.sh _v6 58c2fe4     # first rewrite (team farming, recall loop, meta draft)
tools/snapshot.sh _r2 4a3920d     # fuel + review fixes, reworked learner (UCB on): baseline of the prototype A/Bs
SRC=bots/_v6 tools/variant.sh _hunt learn_enabled=0 fight_margin=0.95f fight_back_margin=0.6f enemy_half_penalty=0.f \
	deny_bonus=1.5f steal_hp_frac=0.3f deathball_until=110 deficit_defend=99 deficit_escort=99 --define "LEGEND_DRAFT 8,4,3,0,9"
SRC=bots/_v6 tools/variant.sh _hunt2 learn_enabled=0 fight_margin=0.9f fight_back_margin=0.6f enemy_half_penalty=2.f \
	deny_bonus=1.2f steal_hp_frac=0.4f isolated_fight_adv=1.0f deficit_defend=99 deficit_escort=99 --define "LEGEND_DRAFT 3,2,9,0,4"
SRC=bots/_v6 tools/variant.sh _devci learn_enabled=0 --define "LEGEND_DRAFT 4,3,9,10,8"
for b in _base _v6 _r2 _hunt _hunt2 _devci; do cambc build $b >/dev/null && echo "built $b"; done
