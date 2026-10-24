#!/usr/bin/env python3
"""Regenerate tools/rl/knowledge.json (the trainer's priors) from this repo's ladder records.

    python tools/rl/make_knowledge.py [MAP_STATS.json]

MAP_STATS.json (optional): {"rows": [[map, ladder_games, top10_wins, top10_games, ranked_wins, ranked_games], ...]} computed from
experiments/live/lists/*.jsonl; without it the per-map numbers already in knowledge.json are kept.
Everything else (genes, priors, reward, league) is the session-16 evidence written out below."""
import json
import math
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "tools", "rl", "knowledge.json")


def F(name, lo, hi, init, block, sigma=0.15, note=""):
    return {"name": name, "type": "float", "lo": lo, "hi": hi, "init": init, "block": block, "sigma": sigma, "note": note}


def I(name, lo, hi, init, block, sigma=0.15, note=""):
    return {"name": name, "type": "int", "lo": lo, "hi": hi, "init": init, "block": block, "sigma": sigma, "note": note}


def C(name, values, init, block, probs=None, note=""):
    if probs is None:
        probs = [0.6 if v == init else 0.4 / (len(values) - 1) for v in values]
    return {"name": name, "type": "cat", "values": values, "init": init, "block": block, "probs": probs, "note": note}


def B(name, bit, init, p, block="switches", note=""):
    return {"name": name, "type": "bit", "bit": bit, "init": init, "p": p, "block": block, "note": note}


def genes():
    g = [
        # fights: when to engage, hit back, leave (Brain::combat)
        F("fight_margin", 1.1, 1.9, 1.4, "fight", note="engage proactively when our kill time beats theirs by this factor"),
        F("fight_back_margin", 0.55, 1.05, 0.873, "fight", note="in their reach: hit back unless this outmatched (59% of our flee turns)"),
        F("cornered_margin", 0.45, 0.95, 0.7409, "fight"),
        F("isolated_fight_adv", 1.0, 1.8, 1.35, "fight"),
        F("isolated_flee_adv", 0.9, 1.8, 1.5, "fight"),
        F("outmatch_flee_adv", 0.5, 1.0, 0.8, "fight", note="early exit before contact (30% of our flee turns)"),
        F("outmatch_solo_adv", 0.2, 0.7, 0.45, "fight"),
        F("ml2_leave", 0.1, 0.5, 0.2, "fight"),
        F("ml2_flee", 0.1, 0.5, 0.2, "fight"),
        I("flee_dist", 3, 7, 5, "fight"),
        F("fight_commit_margin", 0.5, 0.95, 0.7, "fight"),
        F("retreat_hp", 0.15, 0.4, 0.25, "fight"),
        # fight execution switches from the fights analysis (392 games vs the top 10 + 219 top-vs-top; the first 3 rounds' damage
        # decides 75% of fights; they struck first in 44.6% of fresh contacts, we in 22.8%)
        B("stepin_shot", 2097152, 0, 0.5, block="fight", note="ranged walk + attack reset + shot (top Vespers 13% of hitting rounds, ours 0%); local 44/80 vs base 45"),
        B("no_stepin", 4194304, 0, 0.35, block="fight", note="no step into their reach unless we can hit this turn (hold at the edge); local 36/80 vs 45"),
        B("convert", 8388608, 0, 0.35, block="fight", note="no chase of a retreating target; farm on after a nearby kill (top 15-18% vs our 4%); local 38/80 vs 45"),
        B("smart_flee", 16777216, 0, 0.1, block="fight", note="in reach with no step out of it: hit back; local 19/80 ungated, 27/80 gated at 0.6 (deaths x1.7): keep rare"),
        C("camp_in_fight", [3, 1], 3, "fight", probs=[0.5, 0.5], note="contested camp deaths +0.3-0.4 a game; the analysis suggests 1"),
        F("bb_sf_adv", 0.6, 1.3, 0.9, "fight", note="smart flee hits back only at this advantage or better"),
        # powers analysis (ability use vs the top 10)
        B("melee_combo", 33554432, 0, 0.5, block="fight", note="hit + reset + hit before stepping away (we use the ready reset 40-54% vs 70-92%); local 41/80 vs 45"),
        B("early_shield", 67108864, 0, 0.5, block="fight", note="shield with an enemy within 5 (HoR shield before contact 19% vs 47%); local 45/80 vs 45"),
        I("hold_spell_dist", 3, 8, 6, "fight", note="damage spells held for fights while an enemy is this close (top teams cast on camps nearer enemies)"),
        I("hold_cc_dist", 3, 9, 7, "fight"),
        I("strike_dash_hold", 4, 10, 9, "fight", note="HoR dash kept for strikes while an enemy is this close"),
        # farming targets and risk (Brain::group_score)
        F("target_threat_adv", 0.9, 2.0, 1.4942, "farm", note="threat veto on a farm target with enemies near"),
        F("enemy_half_penalty", 3.0, 20.0, 10.0, "farm"),
        F("deny_bonus", 0.0, 0.6, 0.043, "farm"),
        F("steal_hp_frac", 0.35, 0.8, 0.55, "farm"),
        F("unknown_discount", 0.5, 1.0, 0.75, "farm"),
        F("pain_w", 2.0, 16.0, 8.0, "farm"),
        F("deny_capture_mult", 0.8, 2.0, 1.3, "farm"),
        F("mid_risk", 0.0, 30.0, 0.0, "farm", note="opening cost on midline groups"),
        F("half_grade", 0.0, 0.6, 0.0, "farm"),
        F("join_share", 0.3, 0.9, 0.6, "farm"),
        # economy: gold, banking, shopping, build
        F("gold_value", 0.15, 0.5, 0.33, "economy"),
        I("tribute_min", 30, 80, 54, "economy"),
        I("early_tribute_min", 10, 40, 22, "economy"),
        I("bag_caution", 20, 80, 40, "economy"),
        F("home_hp", 0.3, 0.6, 0.45, "economy"),
        F("cap_recall_hp", 0.4, 0.85, 0.61, "economy"),
        I("cap_recall_gold", 30, 150, 60, "economy"),
        I("shop_shards", 2, 6, 4, "economy"),
        F("gold_early", 0.0, 2.5, 0.0, "economy", note="ladder v14f: x2.5 was flat"),
        C("build_style", [15, 16, 17], 15, "economy", note="15 Treasure-first (live), 16 health-heavy, 17 Durability-first"),
        C("mi_health_emblem", [0, 1], 0, "economy"),
        C("ic_home", [0, 1, 2], 0, "economy"),
        # resources analysis: banking is a time cost (we bank 12.9 times a game at 16 tiles 20 rounds after the capture, they 26.2 at 10-11)
        C("bank_first", [0, 1], 0, "economy", probs=[0.5, 0.5], note="bank at the nearest altar when that beats a recall"),
        I("tribute_near", 3, 10, 5, "economy", note="tribute anything when an altar is this close"),
        C("prism_bank", [0, 1], 0, "economy", probs=[0.7, 0.3], note="Prism holds bags (focus grows with its bag)"),
        B("route_gold", 32, 0, 0.35, block="economy", note="strat bit 5: rewards routed to the gold-bonus body within 4"),
        # team: rallies, stance bandit, grouping
        I("rally_r", 5, 14, 9, "team"),
        F("rally_hp", 0.4, 0.8, 0.6, "team"),
        F("q0_spread", -0.5, 0.8, 0.3, "team"),
        F("q0_grouped", -0.5, 0.8, 0.0, "team"),
        F("q0_push", -1.2, 0.3, -0.718, "team"),
        I("learn_window", 25, 80, 40, "team"),
        F("stance_hysteresis", 0.0, 0.4, 0.15, "team"),
        I("group_radius", 6, 16, 12, "team"),
        F("group_far_w", 0.2, 1.6, 0.8, "team"),
        # strategy switches: strat.cpp bits composed into ab_base, and the bb4 modules
        B("osc_fix", 64, 1, 0.85, note="stuck / oscillation fix; ladder +2.3, user priority"),
        B("spawn_threat_off", 2048, 0, 0.35, note="ladder ab3 -4.7 +- 10.4"),
        B("atk_first", 4, 0, 0.3),
        B("chase_max", 8, 0, 0.35, note="chase discipline"),
        B("open", 65536, 0, 0.4, note="near-first opening; local ~0"),
        B("mid_risk_bit", 131072, 0, 0.3),
        B("farm_thru", 262144, 0, 0.5, note="ladder -2 +- 6.5 over 2 rounds; local +2..+4 of 80"),
        B("stand", 524288, 0, 0.35, note="local -5 of 80"),
        B("farm_hold", 1048576, 0, 0.35),
        C("bb_formation", [0, 2], 0, "switches", probs=[0.75, 0.25], note="bb4 play modules lost in ranked (6-13 vs 15-6)"),
        C("bb_comms", [0, 1], 0, "switches", probs=[0.8, 0.2]),
        C("bb_terr", [0, 1], 0, "switches", probs=[0.75, 0.25]),
        C("bb_wards", [0, 1], 0, "switches", probs=[0.7, 0.3]),
        C("bb_prior", [0, 1], 0, "switches", probs=[0.75, 0.25]),
        C("bb_hop_walls", [0, 1], 0, "switches", probs=[0.5, 0.5], note="crystal shortcuts over walls (untested on the ladder)"),
        # objectives: the middle and the big groups (strategy analysis: the middle's gems decide games; top teams hold
        # positions next to respawning groups and take golems / monoliths with 3+ bodies)
        B("middle_control", 1, 0, 0.45, block="objectives",
          note="strat bit 1: middle groups worth more, threat check counts allies within 12, enemy-half cost graded; "
               "our share of middle gems < 0.2 -> 0% wins, >= 0.6 -> 81%"),
        B("bold", 2, 0, 0.3, block="objectives", note="strat bit 2: lower threat veto, later ml2 exits"),
        C("golem_team", [0, 1], 0, "objectives", probs=[0.5, 0.5], note="golem with the team plan; top 2.1 golems/game at r287, us 0.42 at r666"),
        C("mono_team", [0, 1], 1, "objectives", probs=[0.4, 0.6], note="lone monolith when the team can kill it"),
        C("big_reward", [0, 40, 70], 0, "objectives", probs=[0.5, 0.25, 0.25], note="groups worth this many gems are fought for with the team"),
        I("max_join", 1, 5, 3, "objectives", note="extra bodies allowed on one group"),
        I("max_wait", 8, 45, 18, "objectives", note="rounds we wait at a respawning group (top teams hold positions ~75 rounds a game)"),
        I("obj_max_wait", 8, 60, 18, "objectives"),
        # draft (draft.cpp parameter draft)
        C("bb_draft", [0, 1], 0, "draft", probs=[0.95, 0.05], note="archetype draft: ladder -8.0 +- 8.6"),
        F("pd_stat_k", 0.3, 2.0, 1.0, "draft", sigma=0.1),
        F("pd_counter", 0.0, 2.0, 1.0, "draft", sigma=0.1),
        F("pd_hor_prior", 0.0, 1.2, 0.4, "draft", sigma=0.1),
        F("pd_ci_prior", 0.3, 1.5, 0.9, "draft", sigma=0.1),
    ]
    for nm, v in (("ren", 1.0), ("stellar", 0.95), ("varg", 0.62), ("ryth", 0.6), ("prism", 0.36), ("tavi", 0.33), ("vendetta", 0.3),
                  ("marcella", 0.2), ("vesper", 0.12), ("willow", 0.1)):
        g.append(F(f"pd_pri_{nm}", max(0.0, round(v - 0.45, 3)), round(v + 0.45, 3), v, "draft", sigma=0.1))
    for nm, v in (("hp", 0.4321), ("basic", 0.5442), ("area", 0.4831), ("stun", 0.1242), ("dash", 0.1981), ("gold", 0.0565)):
        g.append(F(f"pd_w_{nm}", round(v - 0.4, 4), round(v + 0.4, 4), v, "draft", sigma=0.1))
    return g


def maps_from(rows):
    maps = {}
    for mp, f, w, n, rw, rn in rows:
        loss = 1 - w / n if n >= 5 else 0.85
        maps[mp] = {"ladder_games": f, "top10_wins": w, "top10_games": n, "ranked_wins": rw, "ranked_games": rn,
                    "weight": math.sqrt(max(f, 1)) * (0.5 + loss)}
    tot = sum(v["weight"] for v in maps.values()) or 1.0
    for v in maps.values():
        v["weight"] = round(v["weight"] / tot, 5)
    return maps


def main():
    old = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    if len(sys.argv) > 1:
        maps = maps_from(json.load(open(sys.argv[1], encoding="utf-8"))["rows"])
    else:
        maps = old.get("maps", {})
    k = {
        "version": 1,
        "created": "2026-10-23",
        "base_bot": "bb4",
        "notes": [
            "Built from session 16 (Oct 22-23): ~3,600 ladder games (ours vs top 10, ranked, top-10-vs-top-10).",
            "Local mirror games misled three times (bb4 play, farm-through, archetype draft won locally and were flat or lost on the",
            "ladder): train against a league of different styles, not one copy of ourselves, and validate on fresh cases before accepting.",
            "Early economy decides games vs the top 10: behind in max health at r200 -> 3% wins; first kill by them -> 2%, by us 16%;",
            "their captures by r200 7.1 vs ours 4.5 at equal deaths; near an enemy we hit camps 3% of rounds vs their 16%.",
        ],
        "base_overrides": {"ab_variants": 0, "ab_force": 0, "ab_nomask": 0},
        "maps": maps,
        "genes": genes(),
        "reward": {
            "win": 1.0, "gem_diff": 0.5, "gem_diff_scale": 1000,
            "econ300": 0.3, "econ300_scale": 150, "econ_gold_weight": 0.1,
            "first_kill": 0.1, "deaths": 0.03, "fast_win": 0.15, "fault": 0.5, "fuel_out": 0.01,
            "why": "win and banked-gem margin are the objective; round-300 economy (collected gems + 0.1 x gold), first kill and deaths "
                   "are the ladder's strongest early predictors of the result; faults and fuel-outs punish broken builds",
        },
        "league": [
            {"name": "live", "weight": 0.22, "genes": {}, "note": "the live v52 base (stuck fix, bb4 modules off, learned draft)"},
            {"name": "brave", "weight": 0.14, "genes": {"farm_thru": 1, "stand": 1, "farm_hold": 1},
             "note": "keeps farming near enemies and hits back (top-10-like near-enemy behaviour)"},
            {"name": "oldlive", "weight": 0.10, "genes": {"spawn_threat_off": 1}, "note": "the previous live config (bits 2112)"},
            {"name": "bb4full", "weight": 0.10,
             "genes": {"bb_formation": 2, "bb_comms": 1, "bb_terr": 1, "bb_wards": 1, "bb_prior": 1, "bb_draft": 1, "bb_hop_walls": 1},
             "note": "bb4 play modules + archetype draft (different compositions)"},
            {"name": "p_turtle", "weight": 0.06, "params": {"pxs_style": 1}, "note": "defensive persona"},
            {"name": "p_invader", "weight": 0.07, "params": {"pxs_style": 2}, "note": "raids our half"},
            {"name": "p_deathball", "weight": 0.07, "params": {"pxs_style": 3}, "note": "moves and fights as a ball"},
            {"name": "p_objective", "weight": 0.06, "params": {"pxs_style": 4}, "note": "rushes heavy groups / monoliths"},
            {"name": "p_ambush", "weight": 0.06, "params": {"pxs_style": 5}, "note": "bush ambusher"},
            {"name": "p_altar", "weight": 0.06, "params": {"pxs_style": 6}, "note": "camps our altars"},
        ],
        "hall_of_fame_weight": 0.06,
        "top10_targets": {
            "captures_r200": 7.1, "our_captures_r200": 4.5,
            "near_enemy_farm_share": 0.16, "our_near_enemy_farm_share": 0.03,
            "deaths_bodytime_r300": 0.066, "our_deaths_bodytime_r300": 0.096,
        },
    }
    json.dump(k, open(OUT, "w", encoding="utf-8"), indent=1)
    print(f"wrote {OUT}: {len(k['genes'])} genes, {len(k['maps'])} maps, {len(k['league'])} league bots")


if __name__ == "__main__":
    main()
