#include "brain.h"
#include "mi_game.h"
#include "opponent.h"
#include "dmplan.h"
#include "learn.h"
#include "draft.h"
#include "ml2_model.h"
#include "opp9.h"
#ifdef LEGEND_TRACE
#include <map>
#endif

#include <cmath>
#include <stdexcept>
#include <cstdio>

// Prediction audit hooks: compiled only into XM_TRACE builds and run inside debug_block (fuel paused).
#if defined(LEGEND_TRACE) || defined(Q_TRACE)
static int g_why = 0; // trace only: which rule made group_score return -1 (printed with target switches)
#define WHY(n) (g_why = (n), sc_why = (n))
#else
#define WHY(n) (sc_why = (n)) // v27_commit reads it: a safety rejection drops a committed target, a join / pair rule does not
#endif
#if defined(LEGEND_TRACE) || defined(Q_TRACE)
static int g_idle = 0, g_mfail = 0; // trace only: the last farming decision point of the turn (a line number) and the point whose move failed
#define IDL() (g_idle = __LINE__)
#else
#define IDL() (void)0
#endif
#ifdef XM_TRACE
#define XM(stmt) debug_block({ stmt; })
#else
#define XM(stmt) (void)0
#endif

namespace
{
using I = bc::item_type;
using CT = bc::champion_type;

void rep(std::vector<I>& v, I it, int n)
{
	for (int i = 0; i < n; ++i)
		v.push_back(it);
}

// Repeat a cycle of five-shard blocks n times (late-game raw stats; the list must never run out: a rich Ren
// earned 3,058 gold in one r2 game and stopped buying at 2,100 with 948 gold left).
void cycle(std::vector<I>& v, std::initializer_list<I> blocks, int n)
{
	for (int k = 0; k < n; ++k)
		for (const I it : blocks)
			rep(v, it, 5);
}

bool is_home_shard(I it)
{
	return it == I::home_shard_of_health || it == I::home_shard_of_strength || it == I::home_shard_of_focus;
}

bool is_health_shard(I it)
{
	return it == I::monster_shard_of_health || it == I::power_shard_of_health || it == I::durability_shard_of_health ||
		it == I::treasure_shard_of_health || it == I::jungle_shard_of_health || it == I::home_shard_of_health ||
		it == I::bruiser_shard_of_health;
}

// Shard plans: five shards of a family complete its emblem; only the emblem grants the passive.
// GOD v18 helpers: item enum = family x 6 + stat x 2 + (emblem ? 1 : 0) (SDK get_item_enum).
int item_fam(I it) { return static_cast<int>(static_cast<std::uint32_t>(it)) / 6; }
int item_stat_of(I it) { return (static_cast<int>(static_cast<std::uint32_t>(it)) % 6) / 2; }
I item_of(int fam, int stat) { return I{ static_cast<std::uint32_t>(fam * 6 + stat * 2) }; }
constexpr int FAM_MONSTER = 0, FAM_POWER = 1, FAM_TREASURE = 3, FAM_TRIBUTE = 7, FAM_CAPTURE = 8, FAM_GREED = 12;

// v24_build: the build orders that beat us with our own roster (PtitLK 8-2 on Oct 29, rated as we are) and match the top teams' items:
// a Treasure emblem (+20% gold) first on almost every body, more health on the front line (their Vendetta 2,129 max health at r600, ours
// 1,257), Bruiser stacks after. Order per champion read from their items at r300 / r600 (experiments/v81/ranked).
std::vector<I> v24_build_list(CT t)
{
	std::vector<I> v;
	switch (t)
	{
	case CT::vendetta:
		if (P.v24_build & 32)
		{
			// balanced: 10 health / 15 strength shards by the 25th, then two strength for each health (the user: not health only)
			rep(v, I::treasure_shard_of_health, 5), rep(v, I::jungle_shard_of_strength, 5), rep(v, I::bruiser_shard_of_strength, 5);
			rep(v, I::bruiser_shard_of_health, 5);
			cycle(v, { I::bruiser_shard_of_strength, I::bruiser_shard_of_strength, I::bruiser_shard_of_health }, 10);
			break;
		}
		rep(v, I::treasure_shard_of_health, 5), rep(v, I::jungle_shard_of_strength, 5), rep(v, I::bruiser_shard_of_health, 5);
		rep(v, I::bruiser_shard_of_strength, 5), rep(v, I::durability_shard_of_health, 5);
		cycle(v, { I::bruiser_shard_of_strength, I::bruiser_shard_of_health }, 12);
		break;
	case CT::vesper_vale:
		rep(v, I::treasure_shard_of_strength, 5), rep(v, I::jungle_shard_of_strength, 5), rep(v, I::durability_shard_of_health, 5);
		rep(v, I::bruiser_shard_of_health, 5), rep(v, I::bruiser_shard_of_strength, 5);
		cycle(v, { I::bruiser_shard_of_strength, I::power_shard_of_strength }, 12);
		break;
	case CT::marcella:
		rep(v, I::treasure_shard_of_focus, 5), rep(v, I::jungle_shard_of_focus, 5), rep(v, I::bruiser_shard_of_health, 5);
		cycle(v, { I::bruiser_shard_of_focus, I::bruiser_shard_of_health }, 12);
		break;
	case CT::ryth:
		rep(v, I::treasure_shard_of_health, 5), rep(v, I::bruiser_shard_of_health, 5), rep(v, I::bruiser_shard_of_strength, 5);
		rep(v, I::jungle_shard_of_strength, 5);
		cycle(v, { I::bruiser_shard_of_strength, I::bruiser_shard_of_health }, 12);
		break;
	case CT_HOR:
		rep(v, I::jungle_shard_of_focus, 5), rep(v, I::durability_shard_of_health, 5), rep(v, I::treasure_shard_of_health, 5);
		cycle(v, { I::bruiser_shard_of_focus, I::bruiser_shard_of_health }, 12);
		break;
	default:
		break; // other champions keep their lists
	}
	return v;
}

std::vector<I> build_for(CT t, int bs)
{
	std::vector<I> v;
	if (bs >= 3 && bs <= 4 || bs == 10)
	{
		// ifish (1st on the ladder; sparring proxy): one Durability health emblem and, on the frontline, a Bruiser health
		// emblem early (their Ren: 1,900 max health by r100), then Power in the damage stat for the rest of the game. On
		// its no-contact farming maps (rows, expanse: 0 deaths either side) Monster in the damage stat, then Power (style 4).
		const int om = official_map();
		const int style = bs == 10 ? (om == OM_ROWS || om == OM_EXPANSE ? 4 : 3) : bs;
		const bool focus = t == CT::ren || t == CT_HOR || t == CT::stellar || t == CT::cassi || t == CT::prism || (t == CT::tavi && !P.tavi_str) || t == CT::willow;
		const I power = focus ? I::power_shard_of_focus : I::power_shard_of_strength;
		if (style == 4)
			rep(v, focus ? I::monster_shard_of_focus : I::monster_shard_of_strength, 5);
		else
			switch (t)
			{
			case CT::ren:
			case CT_HOR: // patch 3.0: melee, focus-scaled dash stun and shield like Ren's spells (+15 focus, +100 health per shard)
			case CT::ryth:
			case CT::marcella:
				rep(v, I::bruiser_shard_of_health, 5);
				rep(v, I::durability_shard_of_health, 5);
				break;
			case CT::cassi:
			case CT::willow:
				rep(v, I::bruiser_shard_of_health, 5);
				rep(v, I::durability_shard_of_focus, 5);
				break;
			case CT::tavi:
				rep(v, I::treasure_shard_of_focus, 5);
				rep(v, I::durability_shard_of_focus, 5);
				break;
			default: // Stellar, Prism, Issac, Varg, Vendetta, Vesper: one Power emblem, then the health emblem
				rep(v, power, 5);
				rep(v, I::durability_shard_of_health, 5);
				break;
			}
		rep(v, power, 300);
		return v;
	}
	if (bs == 12)
	{
		// Nyx (patch 3.0, 20 games of Oct 20, experiments/nyx_oct20/analysis): Treasure first on every body (Stellar / Cassi TfE at r46-180, Ren
		// ThE, Issac TsE, Varg ThE), then Jungle in the damage stat (casters) or Bruiser health (melee), Durability, then Power in the damage
		// stat for the rest of the game (1,097 Power-dmg emblems in 20 games: their Stellar ends with 20-27 of them). The patch made gold
		// plentiful (gold clusters 120 HP for 20 gold, kills 100): damage snowballs into more gold.
		const bool focus = t == CT::ren || t == CT_HOR || t == CT::stellar || t == CT::cassi || t == CT::prism || (t == CT::tavi && !P.tavi_str) || t == CT::willow;
		const I pw = focus ? I::power_shard_of_focus : I::power_shard_of_strength;
		switch (t)
		{
		case CT::stellar:
		case CT::cassi:
		case CT::prism:
		case CT::tavi:
		case CT::willow:
			rep(v, I::treasure_shard_of_focus, 5);
			rep(v, I::jungle_shard_of_focus, 5);
			rep(v, I::durability_shard_of_focus, 5);
			rep(v, I::bruiser_shard_of_health, 5);
			break;
		case CT::ren:
		case CT_HOR:
			rep(v, I::treasure_shard_of_health, 5);
			rep(v, I::bruiser_shard_of_health, 5);
			rep(v, I::durability_shard_of_health, 5);
			break;
		case CT::issac:
			rep(v, I::treasure_shard_of_strength, 5);
			rep(v, I::power_shard_of_strength, 5);
			rep(v, I::durability_shard_of_health, 5);
			break;
		case CT::ryth:
		case CT::marcella:
			rep(v, I::treasure_shard_of_health, 5);
			rep(v, I::bruiser_shard_of_health, 5);
			rep(v, I::durability_shard_of_health, 5);
			break;
		default: // Varg, Vendetta, Vesper
			rep(v, I::treasure_shard_of_health, 5);
			rep(v, I::jungle_shard_of_health, 5);
			rep(v, I::durability_shard_of_health, 5);
			break;
		}
		rep(v, pw, 300);
		return v;
	}
	if (bs == 13 || bs == 14)
	{
		// Session 14 hybrids. 13: Treasure first (gold snowball), then our survival emblems (Jungle health on Ren / Ryth, Monster dmg then
		// Durability health on the carries, as build_style 2), then Power in the damage stat for ever (instead of Bruiser cycles: late
		// game our bodies reached 7,000 health and 500 damage while Nyx's Stellar one-shot them). 14: the same without Treasure first.
		const bool focus = t == CT::ren || t == CT_HOR || t == CT::stellar || t == CT::cassi || t == CT::prism || (t == CT::tavi && !P.tavi_str) || t == CT::willow;
		const I pw = focus ? I::power_shard_of_focus : I::power_shard_of_strength;
		const I tr = focus ? I::treasure_shard_of_focus : I::treasure_shard_of_strength;
		const I mo = focus ? I::monster_shard_of_focus : I::monster_shard_of_strength;
		switch (t)
		{
		case CT::ren:
		case CT_HOR:
			if (bs == 13) rep(v, I::treasure_shard_of_health, 5);
			rep(v, I::jungle_shard_of_health, 5);
			if (bs == 14) rep(v, I::treasure_shard_of_focus, 5);
			rep(v, mo, 5);
			rep(v, I::durability_shard_of_health, 5);
			break;
		case CT::ryth:
		case CT::marcella:
			if (bs == 13) rep(v, I::treasure_shard_of_health, 5);
			rep(v, I::jungle_shard_of_health, 5);
			rep(v, mo, 5);
			rep(v, I::durability_shard_of_health, 5);
			break;
		case CT::cassi:
		case CT::willow:
		case CT::issac:
			if (bs == 13) rep(v, tr, 5);
			rep(v, mo, 5);
			rep(v, I::durability_shard_of_health, 5);
			if (t == CT::issac) rep(v, I::jungle_shard_of_health, 5);
			break;
		default: // Stellar, Prism, Tavi, Varg, Vendetta, Vesper
			if (bs == 13) rep(v, tr, 5);
			rep(v, mo, 5);
			if (bs == 14) rep(v, tr, 5);
			if (t == CT::varg || t == CT::vendetta || t == CT::vesper_vale) rep(v, I::jungle_shard_of_strength, 5);
			rep(v, I::durability_shard_of_health, 5);
			break;
		}
		rep(v, pw, 300);
		return v;
	}
	if (bs == 11)
	{
		// Intercontinental Fish (ladder #1; emblem order of its bodies in 36 games of Oct 19, experiments/interwin_oct19):
		// Stellar PfE > HhE > DhE (17 of 36), Ren BhE > DhE > PfE, Cassi PfE > DfE > BhE, Issac PsE > HhE > DhE, Ryth BhE > DhE > PsE,
		// Varg PsE > HhE; first emblem near r83 (Stellar), r74 (Ren). Power in the damage stat for the rest of the game.
		const bool focus = t == CT::ren || t == CT_HOR || t == CT::stellar || t == CT::cassi || t == CT::prism || (t == CT::tavi && !P.tavi_str) || t == CT::willow;
		const I pw = focus ? I::power_shard_of_focus : I::power_shard_of_strength;
		switch (t)
		{
		case CT::ren:
		case CT_HOR: // patch 3.0: melee, focus-scaled dash stun and shield like Ren's spells (+15 focus, +100 health per shard)
		case CT::ryth:
		case CT::marcella:
			rep(v, I::bruiser_shard_of_health, 5);
			rep(v, I::durability_shard_of_health, 5);
			break;
		case CT::cassi:
		case CT::willow:
			rep(v, pw, 5);
			rep(v, I::durability_shard_of_focus, 5);
			rep(v, I::bruiser_shard_of_health, 5);
			break;
		default: // Stellar, Prism, Tavi, Issac, Varg, Vendetta, Vesper
			rep(v, pw, 5);
			rep(v, I::home_shard_of_health, 5);
			rep(v, I::durability_shard_of_health, 5);
			break;
		}
		rep(v, pw, 300);
		return v;
	}
	if (bs == 9)
	{
		// Mite (2nd on the ladder; sparring proxy), from its emblem timings in 33 ladder games: Jungle (-30% camp damage
		// taken) then Durability in the damage stat, one Bruiser health, then Power in the damage stat forever. Ren and
		// Ryth farm on strength on the small-team pack maps (packs Ren JsE r21, 10-12 captures; rows, rushbait-v2 Ryth),
		// on focus elsewhere. Contest (no gem income: the game is decided on gold earned): Treasure first.
		const int om = official_map();
		const bool str_maps = om == OM_PACKS || om == OM_ROWS || om == OM_RUSHBAIT || om == OM_SWIRL || om == OM_INTERLOCK
			|| om == OM_COLLISION || om == OM_FRAGMENT || om == OM_EXPANSE;
		bool focus = t == CT_HOR || t == CT::stellar || t == CT::cassi || t == CT::prism || (t == CT::tavi && !P.tavi_str) || t == CT::willow;
		if (t == CT::ren || t == CT::ryth)
			focus = !str_maps;
		const I ju = focus ? I::jungle_shard_of_focus : I::jungle_shard_of_strength;
		const I du = focus ? I::durability_shard_of_focus : I::durability_shard_of_strength;
		const I pw = focus ? I::power_shard_of_focus : I::power_shard_of_strength;
		rep(v, om == OM_CONTEST ? (focus ? I::treasure_shard_of_focus : I::treasure_shard_of_strength) : ju, 5);
		rep(v, du, 5);
		rep(v, I::bruiser_shard_of_health, 5);
		rep(v, pw, 300);
		return v;
	}
	if (bs == 2 && P.g15_build && t != CT::cassi && t != CT::issac && t != CT::willow)
	{
		// GOD v15 g15_build (the user's 20 ladder games: the four teams' carries end with Treasure, Jungle and Durability passives, and their
		// Vesper Vale with 103 shard equivalents against our 27): Treasure first in the damage stat (+20% gold, +53% with Vesper's passive),
		// Jungle and Durability in health, Monster, then Power in the damage stat for the rest of the game. Supports keep the v14 lists.
		const bool focus = t == CT::ren || t == CT_HOR || t == CT::stellar || t == CT::prism || (t == CT::tavi && !P.tavi_str);
		rep(v, focus ? I::treasure_shard_of_focus : I::treasure_shard_of_strength, 5);
		rep(v, I::jungle_shard_of_health, 5);
		rep(v, I::durability_shard_of_health, 5);
		rep(v, focus ? I::monster_shard_of_focus : I::monster_shard_of_strength, 5);
		rep(v, focus ? I::power_shard_of_focus : I::power_shard_of_strength, 300);
		return v;
	}
	if (bs == 2 && P.ic_build && t != CT::cassi && t != CT::issac && t != CT::ryth && t != CT::marcella && t != CT::willow)
	{
		// GOD v13 ic_build (Intercontinental Fish, 73 current-patch replays, experiments/ic_oct24): the gold goes to the carries early and
		// into their damage stat: a kit with a gold-bonus passive buys Treasure first (IC's Vesper Vale: TsE at rounds 29-84), then Monster,
		// Jungle on health, then Power in the damage stat for the rest of the game (Vendetta / Varg / Heart of Ruin: Monster, Jungle health,
		// Power). The supports (Cassi & Issac, Ryth, Marcella, Willow) keep the value-model lists (IC buys little for them).
		const bool focus = t == CT::ren || t == CT_HOR || t == CT::stellar || t == CT::prism || (t == CT::tavi && !P.tavi_str);
		const bool gold_kit = tpa::kit_of(static_cast<int>(t)).gold_mult > 1.0;
		if (gold_kit)
			rep(v, focus ? I::treasure_shard_of_focus : I::treasure_shard_of_strength, 5);
		rep(v, focus ? I::monster_shard_of_focus : I::monster_shard_of_strength, 5);
		rep(v, I::jungle_shard_of_health, 5);
		rep(v, focus ? I::power_shard_of_focus : I::power_shard_of_strength, 300);
		return v;
	}
	if (bs == 2)
	{
		// Value-model builds (tools/analysis/item_value.py, calibrated on 36 r2 games). Every shard adds one point
		// of its stat whatever the family, so the family only decides the emblem bonus:
		//  - Bruiser (5 points + 1 of each other stat) beats Power (6 of one): the sixth point of a stat is worth
		//    less than a first point of two others (log utility), at the same 150 gold.
		//  - Passives are unique per family (they do not stack), so each is bought once.
		//  - Ren and Stellar earn 1.3-1.6 gold per round (30% of team gold each): Treasure (+20% gold) pays for
		//    itself ~2x over a 700-round game. The model puts it first; measured vs _v6, keeping r2's first emblem
		//    and Treasure second won 21/24 (gems +9,385) against 19/24 (+8,623) for Treasure first.
		//  - Cassi and Issac earn 0.6 gold per round (first emblem near round 400) and die together 6 times a
		//    game: health with Durability / Jungle first (ci_health_first). It halves Cassi's own farming, but
		//    the pair survives fights: vs _v6 it measured 19/24 wins against 16/24 with Monster first.
		switch (t)
		{
		case CT::ren:
		case CT_HOR: // patch 3.0: melee, focus-scaled dash stun and shield like Ren's spells (3.0.2: +12 focus, +4 strength, +100 health per shard)
			if (t == CT_HOR && (P.hor_build == 1 || P.hor_build == 2))
			{
				rep(v, I::jungle_shard_of_health, 5);
				rep(v, I::durability_shard_of_health, 5);
				rep(v, I::bruiser_shard_of_health, 5);
				rep(v, I::treasure_shard_of_focus, 5);
				rep(v, I::monster_shard_of_focus, 5);
				cycle(v, { I::bruiser_shard_of_focus, I::bruiser_shard_of_health }, 8);
				break;
			}
			if (P.rich_treasure_first)
				rep(v, I::treasure_shard_of_focus, 5);
			else
			{
				// The first emblem lands near round 240 and sets the early pace: Ren tanks the packs, and the
				// kill-time planner (incoming_on) accepts more of them with Jungle health.
				rep(v, I::jungle_shard_of_health, 5);
				rep(v, I::treasure_shard_of_focus, 5);
			}
			rep(v, I::monster_shard_of_focus, 5);
			rep(v, I::bruiser_shard_of_focus, 5);
			if (P.rich_treasure_first)
				rep(v, I::jungle_shard_of_health, 5);
			rep(v, I::bruiser_shard_of_focus, 5);
			rep(v, I::durability_shard_of_health, 5);
			cycle(v, { I::bruiser_shard_of_focus, I::bruiser_shard_of_focus, I::bruiser_shard_of_health }, 8);
			break;
		case CT::stellar:
		case CT::prism:
		case CT::tavi:
		{
			// v9 tavi_str: Tavi takes the same list in strength (her attack resets make strength her best stat: guide, finding 7).
			const bool str = t == CT::tavi && P.tavi_str;
			const I monster = str ? I::monster_shard_of_strength : I::monster_shard_of_focus;
			const I treasure = str ? I::treasure_shard_of_strength : I::treasure_shard_of_focus;
			const I bruiser = str ? I::bruiser_shard_of_strength : I::bruiser_shard_of_focus;
			if (P.squishy_hp_first)
				rep(v, I::durability_shard_of_health, 5);
			if (P.rich_treasure_first)
			{
				rep(v, treasure, 5);
				rep(v, monster, 5);
			}
			else
			{
				rep(v, monster, 5);
				rep(v, treasure, 5);
			}
			rep(v, bruiser, 5);
			rep(v, I::durability_shard_of_health, 5);
			cycle(v, { bruiser, bruiser, I::bruiser_shard_of_health }, 8);
			break;
		}
		case CT::cassi:
		case CT::willow:
			if (P.ci_health_first)
			{
				rep(v, I::durability_shard_of_health, 5);
				rep(v, I::jungle_shard_of_health, 5);
				rep(v, I::bruiser_shard_of_health, 5);
				rep(v, I::monster_shard_of_focus, 5);
			}
			else
			{
				// The r2 order without Treasure: damage first, survival second (measured weaker, kept for A/B).
				rep(v, I::monster_shard_of_focus, 5);
				rep(v, I::durability_shard_of_health, 5);
			}
			cycle(v, { I::bruiser_shard_of_focus, I::bruiser_shard_of_health }, 12);
			break;
		case CT::issac:
			if (P.ci_health_first)
			{
				rep(v, I::durability_shard_of_health, 5);
				rep(v, I::jungle_shard_of_health, 5);
				rep(v, I::bruiser_shard_of_strength, 5);
				rep(v, I::monster_shard_of_strength, 5);
			}
			else
			{
				rep(v, I::monster_shard_of_strength, 5);
				rep(v, I::durability_shard_of_health, 5);
				rep(v, I::jungle_shard_of_health, 5);
			}
			cycle(v, { I::bruiser_shard_of_strength, I::bruiser_shard_of_health }, 12);
			break;
		case CT::ryth:
		case CT::marcella:
			// Model margin over the r2 order is ~0 here: keep it, Bruiser for the raw stats.
			rep(v, I::jungle_shard_of_health, 5);
			rep(v, I::monster_shard_of_strength, 5);
			rep(v, I::durability_shard_of_health, 5);
			cycle(v, { I::bruiser_shard_of_strength, I::bruiser_shard_of_health }, 12);
			break;
		case CT::varg:
		case CT::vendetta:
		case CT::vesper_vale:
			// Splash makes strength Varg's best stat (2.2x on packs): Jungle on strength, not health.
			if (P.squishy_hp_first)
				rep(v, I::durability_shard_of_health, 5);
			rep(v, I::monster_shard_of_strength, 5);
			rep(v, I::treasure_shard_of_strength, 5);
			rep(v, I::jungle_shard_of_strength, 5);
			rep(v, I::durability_shard_of_health, 5);
			cycle(v, { I::bruiser_shard_of_strength, I::bruiser_shard_of_strength, I::bruiser_shard_of_health }, 8);
			break;
		}
		if (P.build_tail)
		{
			// The list must never run out (session 14): Power in the damage stat (1) or the Bruiser mix (2) for the rest of the game.
			const bool focus = t == CT::ren || t == CT_HOR || t == CT::stellar || t == CT::cassi || t == CT::prism || (t == CT::tavi && !P.tavi_str) || t == CT::willow;
			if (t == CT_HOR && P.hor_build >= 2)
				cycle(v, { I::bruiser_shard_of_health, I::bruiser_shard_of_focus }, 30);
			else if (P.build_tail == 1)
				rep(v, focus ? I::power_shard_of_focus : I::power_shard_of_strength, 300);
			else
				cycle(v, { focus ? I::bruiser_shard_of_focus : I::bruiser_shard_of_strength, focus ? I::bruiser_shard_of_focus : I::bruiser_shard_of_strength, I::bruiser_shard_of_health }, 40);
		}
		return v;
	}
	if (bs == 1)
	{
		// Ladder-proven: survive first (Jungle health, Durability), farm faster (Monster), earn more (Treasure),
		// then raw stats through Power emblems (6 shards for the price of 5).
		switch (t)
		{
		case CT::varg:
		case CT::vendetta:
		case CT::issac:
			rep(v, I::monster_shard_of_strength, 5);
			rep(v, I::jungle_shard_of_health, 5);
			rep(v, I::treasure_shard_of_strength, 5);
			rep(v, I::durability_shard_of_health, 5);
			rep(v, I::power_shard_of_strength, 50);
			break;
		case CT::ren:
		case CT_HOR: // patch 3.0: melee, focus-scaled dash stun and shield like Ren's spells (+15 focus, +100 health per shard)
			// Retaliation scales with focus (0.2 x focus per hit taken): a health and focus tank.
			rep(v, I::jungle_shard_of_health, 5);
			rep(v, I::power_shard_of_focus, 5);
			rep(v, I::durability_shard_of_health, 5);
			rep(v, I::treasure_shard_of_focus, 5);
			rep(v, I::power_shard_of_focus, 50);
			break;
		case CT::ryth:
		case CT::marcella:
			rep(v, I::jungle_shard_of_health, 5);
			rep(v, I::monster_shard_of_strength, 5);
			rep(v, I::durability_shard_of_health, 5);
			for (int i = 0; i < 10; ++i)
			{
				rep(v, I::power_shard_of_strength, 3);
				rep(v, I::power_shard_of_health, 2);
			}
			break;
		case CT::tavi:
			rep(v, I::monster_shard_of_strength, 5);
			rep(v, I::treasure_shard_of_strength, 5);
			rep(v, I::durability_shard_of_health, 5);
			rep(v, I::power_shard_of_strength, 50);
			break;
		case CT::vesper_vale:
			rep(v, I::treasure_shard_of_strength, 5);
			rep(v, I::monster_shard_of_strength, 5);
			rep(v, I::durability_shard_of_health, 5);
			rep(v, I::power_shard_of_strength, 50);
			break;
		case CT::stellar:
		case CT::cassi:
		case CT::prism:
			rep(v, I::monster_shard_of_focus, 5);
			rep(v, I::durability_shard_of_health, 5);
			rep(v, I::treasure_shard_of_focus, 5);
			rep(v, I::power_shard_of_focus, 50);
			break;
		case CT::willow:
			rep(v, I::power_shard_of_focus, 5);
			rep(v, I::durability_shard_of_health, 5);
			rep(v, I::power_shard_of_focus, 50);
			break;
		}
		return v;
	}
	switch (t)
	{
	case CT::vendetta:
	case CT::varg:
	case CT::ren:
	case CT_HOR: // patch 3.0: melee, focus-scaled dash stun and shield like Ren's spells (+15 focus, +100 health per shard)
	case CT::issac:
		rep(v, I::jungle_shard_of_strength, 5);
		rep(v, I::monster_shard_of_strength, 5);
		rep(v, I::power_shard_of_strength, 60);
		break;
	case CT::ryth:
	case CT::marcella:
		rep(v, I::jungle_shard_of_health, 5);
		rep(v, I::monster_shard_of_strength, 5);
		for (int i = 0; i < 12; ++i)
		{
			rep(v, I::power_shard_of_strength, 3);
			rep(v, I::power_shard_of_health, 2);
		}
		break;
	case CT::tavi:
		rep(v, I::monster_shard_of_strength, 5);
		rep(v, I::power_shard_of_strength, 60);
		break;
	case CT::vesper_vale:
		rep(v, I::treasure_shard_of_strength, 5);
		rep(v, I::monster_shard_of_strength, 5);
		rep(v, I::power_shard_of_strength, 60);
		break;
	case CT::stellar:
	case CT::cassi:
		rep(v, I::monster_shard_of_focus, 5);
		rep(v, I::power_shard_of_focus, 60);
		break;
	case CT::prism:
		rep(v, I::monster_shard_of_strength, 5);
		rep(v, I::power_shard_of_focus, 60);
		break;
	case CT::willow:
		rep(v, I::power_shard_of_focus, 5);
		rep(v, I::durability_shard_of_health, 5);
		rep(v, I::power_shard_of_focus, 60);
		break;
	}
	return v;
}

// The same family's shard in the other damage stat (health shards and consumables unchanged): build_stat.
I in_stat(I it, bool focus)
{
	static const std::pair<I, I> fam[] = { { I::monster_shard_of_focus, I::monster_shard_of_strength }, { I::power_shard_of_focus, I::power_shard_of_strength },
		{ I::durability_shard_of_focus, I::durability_shard_of_strength }, { I::treasure_shard_of_focus, I::treasure_shard_of_strength },
		{ I::jungle_shard_of_focus, I::jungle_shard_of_strength }, { I::home_shard_of_focus, I::home_shard_of_strength },
		{ I::bruiser_shard_of_focus, I::bruiser_shard_of_strength } };
	for (const auto& f : fam)
		if (it == f.first || it == f.second)
			return focus ? f.first : f.second;
	return it;
}

float best_mod(const Kit& k)
{
	return std::max({ k.dmg >= 0 ? k.dmg_mod : 0.f, k.cc >= 0 ? k.cc_mod : 0.f, k.aoe >= 0 ? k.aoe_mod : 0.f, k.dash >= 0 ? k.dash_mod : 0.f });
}

// Next-turn reach of an enemy's spells (0 when none is up). Legend: every spell 4. P.aoe_reach5 (agent fight2): an area
// spell lands radius 1 around a tile up to range 4 away, so it hits bodies at 5 (top 3 vs each other: 20-28% of spell damage
// lands at 5; ours 8%; at distance 5 we dealt 3 and took 12 per body-round). 2: spells usable while walking (Cassi's stun)
// reach range + 1 (walk, then cast). `assume_ready`: cooldowns unknown (unseen this round).
int enemy_spell_reach(const Enemy& e, bool assume_ready)
{
	auto up = [&](int slot) { return slot >= 0 && (assume_ready || e.ready(slot)); };
	int r = (up(e.kit.dmg) || up(e.kit.cc) || up(e.kit.aoe)) ? 4 : 0;
	if (P.aoe_reach5 && up(e.kit.aoe))
		r = std::max(r, static_cast<int>(e.kit.aoe_range + e.kit.aoe_radius) + (e.kit.aoe_excl ? 0 : 1));
	if (P.aoe_reach5 >= 2)
	{
		if (up(e.kit.cc) && !e.kit.cc_excl)
			r = std::max(r, static_cast<int>(e.kit.cc_range) + 1);
		if (up(e.kit.dmg) && !e.kit.dmg_excl)
			r = std::max(r, static_cast<int>(e.kit.dmg_range) + 1);
	}
	return r;
}

vec2 sgn_step(vec2 from, vec2 to)
{
	return { (to.x > from.x) - (to.x < from.x), (to.y > from.y) - (to.y < from.y) };
}
} // namespace

Brain& brain()
{
	static Brain b;
	return b;
}

// ---------------------------------------------------------------------------------------------- lifecycle

// build_kit (patch 3.0.4): the build from the engine's numbers, no list per champion. The damage stat is the one a shard pays most for
// (focus_growth x the spell modifiers per 8-round cooldown, area spells and a damaging dash x 1.5 targets, heals, Ren's retaliation per
// hit; vs strength_growth per basic attack, +1/8 with a reset, Varg's splash x 1.5). A melee body (it takes the camps' hits) opens with
// Jungle health, a ranged one with the Monster emblem; then Treasure, Durability health and the Bruiser mix (two damage, one health)
// as in v8's lists; the linked pair (Cassi & Issac: gold-poor, they die together) skips Treasure. build_tail adds Power in the damage
// stat for the rest of the game.
std::vector<I> Brain::build_from_kit() const
{
	const float tg = 1.5f;
	float sp = 0;
	if (kit.dmg >= 0)
		sp += kit.dmg_mod;
	if (kit.cc >= 0)
		sp += kit.cc_mod;
	if (kit.aoe >= 0)
		sp += kit.aoe_mod * (kit.aoe_radius >= 1.f ? tg : 1.f);
	if (kit.dash >= 0)
		sp += kit.dash_mod * (kit.dash_radius >= 1.f ? tg : 1.f);
	if (kit.heal >= 0)
		sp += kit.heal_mod;
	float vf = focus_growth * sp / 8.f;
	if (type == CT::ren && !kit.ranged)
		vf += bc::constants::passive_abilities::ren_retaliation_focus_ratio * focus_growth * tg;
	const float vs = str_growth * (1.f + (kit.reset >= 0 ? 0.125f : 0.f)) * (type == CT::varg ? tg : 1.f);
	const bool f = vf >= vs;
	const I mon = f ? I::monster_shard_of_focus : I::monster_shard_of_strength, tre = f ? I::treasure_shard_of_focus : I::treasure_shard_of_strength,
			bru = f ? I::bruiser_shard_of_focus : I::bruiser_shard_of_strength, pw = f ? I::power_shard_of_focus : I::power_shard_of_strength;
	std::vector<I> v;
	const bool linked = type == CT::cassi || type == CT::issac;
	if (linked)
	{
		rep(v, mon, 5);
		rep(v, I::durability_shard_of_health, 5);
		cycle(v, { bru, I::bruiser_shard_of_health }, 12);
	}
	else if (!kit.ranged)
	{
		rep(v, I::jungle_shard_of_health, 5);
		rep(v, mon, 5);
		rep(v, tre, 5);
		rep(v, I::durability_shard_of_health, 5);
		cycle(v, { bru, bru, I::bruiser_shard_of_health }, 8);
	}
	else
	{
		rep(v, mon, 5);
		rep(v, tre, 5);
		rep(v, bru, 5);
		rep(v, I::durability_shard_of_health, 5);
		cycle(v, { bru, bru, I::bruiser_shard_of_health }, 8);
	}
	if (P.build_tail == 1)
		rep(v, pw, 300);
	else if (P.build_tail)
		cycle(v, { bru, bru, I::bruiser_shard_of_health }, 40);
	return v;
}

void Brain::debug_state(unsigned long long fuel_left) const
{
	std::printf("FS r=%d t=%d pos=(%d,%d) task=%d g=%d gems=%u left=%llu\n", round, static_cast<int>(type), pos.x, pos.y, task, task_group, gems, fuel_left);
}

void Brain::init()
{
	init_round = static_cast<int>(bc::round_number());
	auto& me = bc::self();
	self = handle_of(me);
	type = me.champion_name();
	kit = kit_of(me);
	{
		const auto bs = me.base_stats();
		base_hp = bs.base_health, hp_growth = bs.health_growth, base_str = bs.base_strength, str_growth = bs.strength_growth;
		base_focus = bs.base_focus, focus_growth = bs.focus_growth;
	}
	const auto abl = me.abilities();
	ab.assign(abl.begin(), abl.end());
	build = P.build_kit ? build_from_kit() : build_for(type, P.build_style);
	if (P.build_stat && !P.build_kit)
	{
		// build_stat (patch 3.0.4): every focus / strength shard of the list in the stat this kit pays most for, from the engine's numbers:
		// a focus shard adds focus_growth x the spell modifiers per cooldown (area spells and a damaging dash x build_stat_targets; Ren's
		// retaliation 0.2 x focus per hit taken, ~build_stat_targets hits a round), a strength shard strength_growth per basic attack
		// (+1/8 with an attack reset; Varg's splash x targets). The typed lists stay unless one stat pays build_stat_margin x the other:
		// Tavi (110 focus, one 1.4 x focus spell, a reset): 1.75 vs 5.6 a round per shard, so strength.
		const float tg = P.build_stat_targets;
		float sp = 0;
		if (kit.dmg >= 0)
			sp += kit.dmg_mod;
		if (kit.cc >= 0)
			sp += kit.cc_mod;
		if (kit.aoe >= 0)
			sp += kit.aoe_mod * (kit.aoe_radius >= 1.f ? tg : 1.f);
		if (kit.dash >= 0)
			sp += kit.dash_mod * (kit.dash_radius >= 1.f ? tg : 1.f);
		if (kit.heal >= 0)
			sp += kit.heal_mod; // Willow: health restored counts like damage dealt
		float vf = focus_growth * sp / 8.f;
		if (type == CT::ren && !kit.ranged)
			vf += bc::constants::passive_abilities::ren_retaliation_focus_ratio * focus_growth * tg;
		const float vs = str_growth * (1.f + (kit.reset >= 0 ? 0.125f : 0.f)) * (type == CT::varg ? tg : 1.f);
		const int want = vf >= P.build_stat_margin * vs ? 1 : vs >= P.build_stat_margin * vf ? 2 : 0;
		if (want)
			for (auto& it : build)
				it = in_stat(it, want == 1);
#ifdef GV_TRACE
		debug_block({ std::printf("BSTAT ch=%d vf=%.2f vs=%.2f want=%d\n", static_cast<int>(type), vf, vs, want); });
#endif
	}
	if (P.tail_stat && P.build_tail == 1 && !build.empty() && (build.back() == I::power_shard_of_focus || build.back() == I::power_shard_of_strength))
	{
		const float vf = focus_growth * (kit.dmg_mod + kit.cc_mod + kit.aoe_mod + kit.dash_mod) / 8.f;
		const float vs = str_growth * (1.f + (kit.reset >= 0 ? 1.f / 8.f : 0.f));
		const I want = vf > vs ? I::power_shard_of_focus : I::power_shard_of_strength;
#ifdef GV_TRACE
		debug_block({ std::printf("TAIL ch=%d vf=%.2f vs=%.2f tail=%s list=%s\n", static_cast<int>(type), vf, vs, want == I::power_shard_of_focus ? "focus" : "str",
			build.back() == I::power_shard_of_focus ? "focus" : "str"); });
#endif
		const I have = build.back();
		for (std::size_t i = build.size(); i-- > 0 && build[i] == have;)
			build[i] = want;
	}
	if (P.mi_health_emblem)
	{
		// mi_health_emblem (default branch): a Durability health emblem (-10% damage taken, +5 health points) right after the
		// first emblem. Builds that already have one further down move it up; the others insert one.
		const I dh = I::durability_shard_of_health;
		std::size_t at = build.size();
		for (std::size_t i = 0; i + 5 <= build.size(); i += 5)
			if (build[i] == dh)
			{
				at = i;
				break;
			}
		if (at != 0 && at != 5 && build.size() >= 5)
		{
			if (at < build.size())
				build.erase(build.begin() + static_cast<std::ptrdiff_t>(at), build.begin() + static_cast<std::ptrdiff_t>(at + 5));
			build.insert(build.begin() + 5, 5, dh);
		}
	}
	auto& W = world();
	W.dash_kit = kit.dash >= 0;
	W.init_static();
	{
		// g18_calm_mono: on a lone-monolith map (mono_mode: the contest plan, the fight at the objective is the game) keep v17's contact
		// reflexes; contact discipline lost there (ct2, 24 contest copies: 18/48, deaths 29.0-19.4) while it won on the ladder pool.
		// 2: also on objective maps (obj_mode: the whole team on one heavy group; var17's stampede copies -1,320 over 6 games).
		const bool v17_contact = (P.g18_calm_mono >= 1 && W.mono_mode) || (P.g18_calm_mono >= 2 && W.obj_mode);
		calm_bits = v17_contact ? 0 : P.g15_calm;
		ml2_flee_eff = v17_contact ? P.g18_mono_ml2_flee : P.ml2_flee;
		fz_engage_eff = v17_contact ? P.g18_mono_fz_engage : P.fz_engage;
	}
	if (W.mono_mode && P.mono_build)
		build = build_for(type, P.mono_build);
	if ((P.ic_home == 1 || P.ic_home == 2) && build.size() >= 5)
	{
		// ic_home: a Home emblem second, on the bodies whose first emblem is a damage emblem (1) or on all (2).
		const bool damage_first = !is_health_shard(build[0]);
		if (P.ic_home == 2 || damage_first)
			insert_home(5);
	}
	if (P.g18_treasure || P.g18_capture || P.g18_greed || P.g18_tribute)
		g18_adjust_build();
	if (P.v23_build)
		build = v23_build_list(); // GOD v23 4.7: builds by kit (replaces every list above)
	if (P.v24_build && (P.v24_build & (type == CT::vendetta ? 1 : type == CT::vesper_vale ? 2 : type == CT::marcella ? 4 : type == CT::ryth ? 8 : type == CT_HOR ? 16 : 0)))
	{
		auto b = v24_build_list(type);
		if (!b.empty())
			build = std::move(b); // v24: Treasure first, health on the front line (the roster-mirror team that beat us 8-2)
	}
	if (P.v26_prosp && !build.empty())
	{
		// v26_prosp: Prospector (+25% of our share of every capture's gems and gold) in place of Monster (+15% camp damage), the same
		// stat points. The top teams' capturers own it at r300 (newer team 9.6 shards, Ad Astra 3.1, prism 4.2; we buy none). 2: its
		// emblem first (a list without Monster gets one in its first damage stat).
		auto prosp = [](I it) {
			return it == I::monster_shard_of_strength ? I::prospector_shard_of_strength
				: it == I::monster_shard_of_focus	  ? I::prospector_shard_of_focus
				: it == I::monster_shard_of_health	  ? I::prospector_shard_of_health
													  : it;
		};
		for (auto& it : build)
			it = prosp(it);
		if (P.v26_prosp & 2)
		{
			I pick = I::prospector_shard_of_strength;
			bool found = false;
			for (const auto it : build)
				if (it == I::prospector_shard_of_strength || it == I::prospector_shard_of_focus || it == I::prospector_shard_of_health)
				{
					pick = it, found = true;
					break;
				}
			if (!found)
				for (const auto it : build)
					if (it == I::monster_shard_of_focus || it == I::power_shard_of_focus || it == I::bruiser_shard_of_focus || it == I::treasure_shard_of_focus ||
						it == I::jungle_shard_of_focus)
					{
						pick = I::prospector_shard_of_focus;
						break;
					}
					else if (it == I::power_shard_of_strength || it == I::bruiser_shard_of_strength || it == I::treasure_shard_of_strength || it == I::jungle_shard_of_strength)
						break;
			std::vector<I> b;
			b.reserve(build.size() + 5);
			for (int k = 0; k < 5; ++k)
				b.push_back(pick);
			int skip = found ? 5 : 0;
			for (const auto it : build)
			{
				if (skip > 0 && it == pick)
				{
					--skip;
					continue;
				}
				b.push_back(it);
			}
			build = std::move(b);
		}
	}
	// Islands are searched later (prebuild_fields): ~47k fuel on 100x100 maps, not needed in the opening rounds.
	W.island_of.assign(W.groups.size(), -1);
	W.islands_pending = true;
	if (!P.defer_islands)
		W.islands_pending = false, W.find_islands();
	W.init_units();
	blacklist.assign(W.groups.size(), -1);
	dmg_on.assign(W.groups.size(), 0.f);
	nav().init();
	learner().init(W.W, W.H);
	comms().bodies = static_cast<int>(W.allies.size());
	comms().bag_on = P.team_bank && W.groups.size() <= 62;
	if (P.tp_own)
		tp_own_ = tpa::read_own(static_cast<int>(type), static_cast<int>(W.groups.size()));
	if (P.mi_own > 0.f || P.mi_next > 0.f || P.mi_open > 0.f || P.mi_body || P.mi_live)
		try
		{
			mig::init(static_cast<int>(type), static_cast<int>(W.groups.size()));
		}
		catch (...)
		{
		}
	if (P.dm_plan)
	{
		// The draft's plan (dmplan.h): accepted only for this map (size and group count), else every user falls back.
		auto& dp = draft_plan();
		try
		{
			if (!bc::draft_memory.is_empty())
			{
				std::vector<std::uint8_t> b;
				b.reserve(bc::draft_memory.size());
				for (const auto x : bc::draft_memory)
					b.push_back(std::to_integer<std::uint8_t>(x));
				if (dm_decode(b, dp) && (dp.width != W.W || dp.height != W.H || dp.groups != static_cast<int>(W.groups.size())))
					dp.ok = false;
			}
		}
		catch (...)
		{
			dp.ok = false;
		}
		// Our pick slot (the draft's order): the slot whose champion is ours (Cassi and Issac share one).
		my_slot = -1;
		if (dp.ok)
			for (int k = 0; k < static_cast<int>(dp.ours.size()); ++k)
			{
				const auto d = static_cast<bc::champion_draft>(dp.ours[static_cast<std::size_t>(k)]);
				const bool pair = d == bc::champion_draft::cassi_and_issac && (type == CT::cassi || type == CT::issac);
				if (pair || (d != bc::champion_draft::cassi_and_issac && static_cast<int>(dm_type_of(d)) == static_cast<int>(type)))
					my_slot = k;
			}
#ifdef DM_TRACE
		debug_block({
			std::printf("DM body=%d ok=%d slot=%d groups=%d flags=%d obj=%d anchors=%d wards=%d\n", W.my_index, static_cast<int>(dp.ok), my_slot, dp.groups, dp.flags,
				static_cast<int>(dp.obj_groups.size()), static_cast<int>(dp.anchor_slots.size()), static_cast<int>(dp.wards.size()));
		});
#endif
	}
	inited = true;
#ifdef LEGEND_TRACE
	// Route analysis (tools/analysis): the static camp-group table, printed once per team (fuel-free in debug).
	debug_block({
		if (W.my_index == 0)
		{
			std::printf("M w=%d h=%d spawn=(%d,%d) team=%d\n", W.W, W.H, W.ally_spawn_c.x, W.ally_spawn_c.y, static_cast<int>(bc::detail::sdk_my_team()));
			std::printf("O mode=%d share=%.2f groups=%d first=%d mono=%d mshare=%.2f\n", static_cast<int>(W.obj_mode), W.obj_share, static_cast<int>(W.obj_groups.size()), W.obj_groups.empty() ? -1 : W.obj_groups[0], static_cast<int>(W.mono_mode), W.mono_share);
			for (const auto& g : W.groups)
			{
				std::printf("G id=%d gems=%d gold=%d respawn=%d ours=%d d_ally=%d hp=%.0f dps=%.0f tiles=", g.id, g.gems, g.gold, g.respawn, (int)g.ours, g.d_ally, g.max_hp, g.dps);
				for (auto t : g.tiles)
					std::printf("%d,%d;", t.x, t.y);
				std::printf("\n");
			}
		}
	});
#endif
}

void Brain::read_self()
{
	bc::detail::champion_info i{};
	bc::detail::check(bc::detail::sdk_champion(self, &i));
	alive = flag(i.state, bc::champion_state::alive);
	pos = { i.x, i.y };
	hp = i.health;
	max_hp = std::max(1.f, i.max_health);
	str = i.strength;
	focus = i.focus;
	state = i.state;
	can_move = flag(i.state, bc::champion_state::can_move);
	can_attack = flag(i.state, bc::champion_state::can_attack);
	can_cast = flag(i.state, bc::champion_state::can_cast);
	cast_done = false;
	for (std::uint32_t s = 0; s < 2; ++s)
	{
		std::int32_t c = 0;
		if (bc::detail::sdk_champion_cooldown(self, s, &c) != 0)
			c = 99;
		cd[s] = c;
	}
	if (P.fm_buffs & 1)
	{
		my_shield = 0.f;
		std::array<bc::detail::buff_data, static_cast<std::size_t>(bc::buff_types::count)> raw{};
		std::uint32_t n = 0;
		if (bc::detail::sdk_champion_buff_data(self, raw.data(), static_cast<std::uint32_t>(raw.size()), &n) == 0)
			for (std::uint32_t k = 0; k < n && k < raw.size(); ++k)
				if (raw[k].type == static_cast<std::uint32_t>(bc::buff_types::shield))
					my_shield = std::max(0.f, raw[k].data.shield.value);
	}
	const std::uint32_t before = gems;
	bc::detail::sdk_champion_gems(self, &gems);
	bc::detail::sdk_champion_gold(self, &gold);
	if (alive && before > 0 && gems == 0 && flag(i.state, bc::champion_state::alive))
		last_bank_round = round;
}

void Brain::turn()
{
	if (inited && P.no_split)
		remember_positions();
	round = static_cast<int>(bc::round_number());
	auto& W = world();
	W.round = round;
	if (!inited)
	{
		init();
		if (P.v23_init_resume)
		{
			// The first turn's init can outlast its fuel (heavy maps: ~200-270k against ~185k): the turn resumes in round 2 or 3 with fuel
			// left, and with the round read before init it then sat out (round < start_round): our first move came a round late on half the maps.
			round = static_cast<int>(bc::round_number());
			W.round = round;
		}
	}
	read_self();
#ifdef Q_TRACE
	q_p0 = pos;
	g_idle = 0, g_mfail = 0;
#endif
#ifdef FAULT_INJECT
	// GOD_Improvement_Plan FIX-2 test only: body 1 throws on every turn after round 300 (the watchdogs must keep it useful).
	if (alive && W.my_index == 1 && round > 300)
		throw std::runtime_error("FAULT_INJECT");
#endif
	if (alive && round < P.start_round)
	{
		prebuild_fields();
		return;
	}
	auto& C = comms();
	if (!alive)
	{
		XM(xm_dead());
		if (was_alive && P.death_learn)
			dl_on_death();
		if (was_alive && P.ml2_adapt > 0.f)
			ml2_learn(true); // the evaluations of the last 8 rounds ended in a death
		was_alive = false;
		W.update_alive(round);
		shop();
		C.read(round);
		C.write_bag(0);
		C.write_self(W.my_index, -1);
		if (P.opp_model)
			learner().frozen = C.plan >= PLAN_INVADER;
		learner().tick(round, W.my_index == 0, false);
		if (P.opp_model || P.om_sight)
			om_tick_traced();
		if (W.my_index == 0)
		{
			if (P.opp_model)
				C.write_plan(P.om_force > 0 && round >= P.om_start ? P.om_force : P.om_act ? opp_model().plan_id(learner().stance) : learner().stance);
			else
				C.write_stance(learner().stance);
		}
		if (P.opp_plan && !P.opp_model && W.my_index == 0)
		{
			// v9: the leader keeps the opponent model running while dead (global score and alive flags need no vision).
			opp9().tick(round, P.contact_bit && C.take_contact(), C.others_carried());
			C.write_plan9(opp9().plan);
		}
		task = T_NONE;
		return;
	}
	W.perceive(pos);
	C.read(round);
	if (P.mi_next > 0.f || P.mi_open > 0.f)
	{
		// GOD v12: a capture landed (our gems or gold rose within a few rounds after the capture time on the group we stood on)
		const int since = round - capture_since;
		if (capture_group_id >= 0 && capture_since != mi_cap_since && since >= static_cast<int>(bc::constants::capture_time) &&
			since <= static_cast<int>(bc::constants::capture_time) + 8 && (gems > mi_prev_gems || gold > mi_prev_gold))
		{
			mi_cap_since = capture_since;
			mig::on_capture(capture_group_id, round);
		}
		mi_prev_gems = gems, mi_prev_gold = gold;
	}
	if (P.farm_ema > 0.f && farm_pred > 0.f)
	{
		// T09d: last turn we farmed alone inside every live camp's reach; health lost since then vs the model's prediction.
		if (hp <= last_hp && enemies_within(6) == 0)
			farm_ema_v = std::clamp(farm_ema_v + P.farm_ema * (std::clamp((last_hp - hp) / farm_pred, 0.f, 3.f) - farm_ema_v), 0.7f, 1.5f);
		farm_pred = 0.f;
	}
	if (P.opp_plan && !P.opp_model)
	{
		// v9: shared evidence for the opponent model. Any body that sees an enemy on our half sets the contact bit; the leader
		// reads and clears it once per round, updates the model and broadcasts the plan (read by every body in Comms::read).
		const bool contact = P.contact_bit && enemy_on_our_half();
		if (W.my_index == 0)
		{
			const bool shared = P.contact_bit && C.take_contact(); // always clear it: one count per round
			opp9().tick(round, contact || shared, static_cast<int>(gems) + C.others_carried());
			C.write_plan9(opp9().plan);
		}
		else if (contact)
			C.set_contact();
	}
	if (P.reward_claim_gone)
	{
		// Shared memory says who works which group. A living ally whose claim leaves a reward we cannot see has taken it
		// (interlock, session 12: Ren captured a wolf reward r17-22, its claim left at r23, and Ryth, 12 steps away and
		// blind to the tile, walked off a wolf it had hit 3 times to capture a reward that was gone).
		for (int i = 0; i < 6 && i < static_cast<int>(W.allies.size()); ++i)
		{
			const auto k = static_cast<std::size_t>(i);
			const int was = prev_claim[k], now = C.claim[k];
			if (i != W.my_index && was >= 0 && was != now && was < static_cast<int>(W.groups.size()) && W.allies[k].alive)
			{
				auto& g = W.groups[static_cast<std::size_t>(was)];
				// Mode 2: only when the ally held the claim for a whole capture since the reward appeared (mode 1 also fired on
				// allies that left a reward uncaptured to heal or flee, and the reward then expired: 125 of 170 vs 135).
				const bool held = P.reward_claim_gone != 2 ||
					round - std::max(prev_claim_since[k], g.reward_round) >= static_cast<int>(bc::constants::capture_time);
				if (g.st == ST_REWARD && g.seen_round != round && held)
				{
					g.st = ST_RESPAWN;
					g.ready_round = round + g.respawn;
				}
			}
			if (was != now)
				prev_claim_since[k] = round;
			prev_claim[k] = now;
		}
	}
	C.write_bag(static_cast<int>(gems));
	{
		// Learning signals: champion damage marks a painful place; an enemy dying near us relieves it.
		auto& L = learner();
		if (P.opp_model)
			L.frozen = C.plan >= PLAN_INVADER;
		L.tick(round, W.my_index == 0, true);
		if (P.opp_model || P.om_sight)
			om_tick_traced();
		if (W.my_index == 0)
		{
			if (P.opp_model)
				C.write_plan(P.om_force > 0 && round >= P.om_start ? P.om_force : P.om_act ? opp_model().plan_id(L.stance) : L.stance);
			else
				C.write_stance(L.stance);
		}
		if (hp < last_hp - 0.5f)
		{
			last_hit_round = round;
			if (enemies_within(5) > 0)
				L.add_pain(pos, P.pain_hit * (last_hp - hp) / max_hp);
		}
		for (const auto& e : W.enemies)
			if (e.died_round == round && round - e.seen_round <= 2 && cheb(e.pos, pos) <= 8)
				L.on_enemy_killed_near(e.pos, round);
		// GOD v15 g15_lock & 2: since when (and with what bag) we see each enemy tributing: the ticks it has left.
		if (P.g15_lock & 2)
			for (std::size_t k = 0; k < W.enemies.size() && k < g15_trib_since.size(); ++k)
			{
				const auto& e = W.enemies[k];
				if (e.visible && e.alive && e.tributing)
				{
					if (g15_trib_since[k] < 0)
						g15_trib_since[k] = round, g15_trib_gems[k] = static_cast<int>(e.gems);
				}
				else if (e.visible || !e.alive)
					g15_trib_since[k] = -1;
			}
		// A visible enemy tributing a bag (or recalling with one) is an opportunity for the whole team.
		// v23 4.4: no OPPORTUNITY alert (Mite recalls every turn: the signal is noise, and it is the bait).
		for (std::size_t k = 0; k < W.enemies.size() && (!P.v23_contact || P.v23_alert_keep); ++k)
		{
			const auto& e = W.enemies[k];
			if (e.visible && e.alive && (e.tributing || (e.recalling && e.gems >= 20) || (race_state == 1 && static_cast<int>(e.gems) >= P.race_carrier)) && e.gems >= 10 &&
				!W.enemy_spawn.is_set(e.pos))
			{
				if ((P.g15_lock & 2) && Comms::t4_free() && e.tributing && static_cast<int>(e.gems) >= P.g15_lock_bag && k < g15_trib_since.size() && g15_trib_since[k] >= 0)
				{
					// v15: posted at its altar with the rounds it has left, so a lock carrier knows whether it can get there in time.
					vec2 altar{ -1, -1 };
					for (const auto& a : W.altars)
						if (cheb(a, e.pos) <= 1 && (altar.x < 0 || cheb(a, e.pos) < cheb(altar, e.pos)))
							altar = a;
					const int left = (g15_trib_gems[k] + 9) / 10 - (round - g15_trib_since[k]);
					if (altar.x >= 0 && left >= 2)
					{
						C.post(AL_OPPORTUNITY, altar, round);
						C.write_t4((left + 3) / 4);
						break;
					}
				}
				C.post(AL_OPPORTUNITY, e.pos, round);
				if ((P.g15_lock & 2) && Comms::t4_free() && C.t4 != 0)
					C.write_t4(0);
				break;
			}
		}
	}
	build_danger();
	nowake_prepare();
	if (P.v23_bank || P.v23_locks)
		v23_perceive();
	if (calm_bits)
		g15_threats();
	if (P.ward_enemy && round % 2 == 0)
		enemy_wards_update();
	if (P.death_learn)
		dl_record();
	if (P.kill_captures > 0.f)
		for (const auto& g : W.groups)
			if (g.st == ST_RESPAWN && g.id >= 0 && g.id < static_cast<int>(dmg_on.size()))
				dmg_on[static_cast<std::size_t>(g.id)] = 0.f;
	if (P.build_react > 0.f)
		for (const auto& e : W.enemies)
			if (e.alive && e.visible)
				enemy_burst_seen = std::max(enemy_burst_seen, e.str + e.focus * std::max({ e.kit.dmg_mod, e.kit.cc_mod, e.kit.aoe_mod, e.kit.dash_mod }));
	if (P.mi_learn_burst || P.mi_lethal)
		learn_burst();
	XM(xm_pre());
	if (g17_bait_on)
	{
		// v17 g17_bait: cancel the bait recall from the end of our last turn before anything reads the channel
		g17_bait_on = false;
		if (flag(state, bc::champion_state::recalling))
		{
			try
			{
				bc::self().cancel_recall();
			}
			catch (...)
			{
			}
			read_self();
		}
	}
	{
		const bool rec = flag(state, bc::champion_state::recalling);
		recalls_started += rec && !was_recalling;
		was_recalling = rec;
	}

	if (flag(state, bc::champion_state::recalling) || flag(state, bc::champion_state::submitting_gems) ||
		flag(state, bc::champion_state::teleporting))
	{
		handle_channel();
		read_self();
		if (flag(state, bc::champion_state::recalling) || flag(state, bc::champion_state::submitting_gems) ||
			flag(state, bc::champion_state::teleporting))
		{
			XM(xm_post());
#ifdef Q_TRACE
			q_line(90);
#endif
			pw_since = round; // a channel is progress (v27_watch)
			last_hp = hp;
			return;
		}
	}

	shop();
	nav().new_turn();
	update_mode();

	support_spells();
	use_locks();
	if (P.v23_locks)
		v23_lock_carrier();

	if (!was_alive)
		respawn_round = round;
	was_alive = true;
	if (escort_wait())
	{
		place_ward(false);
		update_priority();
		prebuild_fields();
		C.write_self(W.my_index, -1);
		XM(xm_post());
#ifdef Q_TRACE
		q_line(91);
#endif
		pw_since = round; // holding on spawn (healing, shopping) is progress (v27_watch)
		last_hp = hp;
		return;
	}

	dbg_path = 0, dbg_eng = 0, dbg_hit_other = false;
	if (P.v23_tol)
		v23_team_plan(); // v23 4.3: the prime clock, the roster, our role
#ifdef SPELL_TRACE
	const vec2 pos0 = pos;
	const bool dmg_up0 = kit.dmg >= 0 && cd[static_cast<std::size_t>(kit.dmg)] <= 0, aoe_up0 = kit.aoe >= 0 && cd[static_cast<std::size_t>(kit.aoe)] <= 0;
#endif
	bool acted = false;
#ifdef LEGEND_TRACE
	g_idle = 0, g_mfail = 0;
#endif
#ifdef FUEL_STATE
#define FSP(tag) debug_block({ std::printf("FP r=%d t=%d %s %llu\n", round, static_cast<int>(type), tag, static_cast<unsigned long long>(bc::fuel_remaining())); })
#else
#define FSP(tag) (void)0
#endif
	FSP("start");
	if (P.mono_rg && regroup_active() && (P.mono_rg_fight_r <= 0 || enemies_within(P.mono_rg_fight_r) == 0))
		acted = go_home(), dbg_path = 9;
	if (!acted)
		acted = P.v23_fe ? v23_fight() : combat(); // v23 4.5: the fight engine replaces combat()
	FSP("combat");
	// pocket_fix 2: in a pocket no walk leaves (dist_home unreachable) a dash kit dashes out as soon as its dash is up, whatever the task:
	// the fields route into such pockets over one-wide hole crossings, and staying cost a body hundreds of rounds (nx100x100).
	if (!acted && (P.pocket_fix & 2) && W.dist_home(pos) >= BIG && !reward_here() && pocket_dash())
		acted = true, dbg_path = 12;
	if (acted)
		dbg_path = task == T_FIGHT ? 1 : 2;
	if (!acted && (acted = safety()))
		dbg_path = 3;
	if (!acted && (acted = tribute(false)))
		dbg_path = 4;
	if (!acted && (acted = home_trip()))
		dbg_path = 5;
	if (!acted && (acted = shop_trip()))
		dbg_path = 6;
	if (!acted && P.pxs_style && style_now() == 6 && W.my_index < P.pxs_deny_bodies && (acted = pxs_deny_altar()))
		dbg_path = 9;
	if (!acted && P.g16_camp && round >= P.g16_hunt_from && (acted = hunt_camp()))
		dbg_path = 14;
	if (!acted && P.deny_altar && (acted = deny_enemy_altar()))
		dbg_path = 11;
	if (!acted && P.gank && (acted = gank_carrier()))
		dbg_path = 10;
	if (!acted && (P.g15_lock & 4) && (acted = lock_run()))
		dbg_path = 13;
	if (!acted && !P.v23_fe && (acted = respond_to_alert())) // v23 4.5.6: a RALLY is answered only by the second wave, within 8
		dbg_path = 7;
	if (!acted && P.mono_fort && W.mono_mode && round < P.mono_fort_until)
		acted = go_home(), dbg_path = 9;
	FSP("chain");
	if (!acted && P.v23_tol && (acted = v23_prime())) // v23 4.3: the PRIME role (rally, wait, take the group the round it spawns)
		dbg_path = 15;
	if (!acted)
		farm(), dbg_path = 8;
	FSP("farm");
#ifdef SPELL_TRACE
	debug_block({
		auto& WW = world();
		if ((dmg_up0 || aoe_up0) && !cast_done)
		{
			int cd4 = 99, live4 = 0;
			for (const auto& g : WW.groups)
				for (std::size_t k = 0; k < g.camps.size(); ++k)
					if (g.hp[k] > 0 && WW.camp_occ.is_set(g.camps[k].pos) && cheb(pos0, g.camps[k].pos) <= 4)
						cd4 = std::min(cd4, cheb(pos0, g.camps[k].pos)), ++live4;
			int tg4 = 99;
			if (task_group >= 0 && task_group < static_cast<int>(WW.groups.size()))
			{
				const auto& g = WW.groups[static_cast<std::size_t>(task_group)];
				for (std::size_t k = 0; k < g.camps.size(); ++k)
					if (g.hp[k] > 0 && WW.camp_occ.is_set(g.camps[k].pos))
						tg4 = std::min(tg4, cheb(pos0, g.camps[k].pos));
			}
			if (live4 > 0)
				std::printf("WM tg=%d r=%d ch=%d path=%d eng=%d task=%d cd4=%d live4=%d mv=%d enemy=%d\n", tg4, round, static_cast<int>(type), dbg_path, dbg_eng, task, cd4, live4, static_cast<int>(!can_move), enemy_near_d);
		}
		int nd = 99, nt = -1, nsp = 0;
		for (const auto& e : WW.enemies)
			if (e.alive && e.visible && cheb(e.pos, pos) < nd)
				nd = cheb(e.pos, pos), nt = static_cast<int>(e.type), nsp = WW.enemy_spawn.is_set(e.pos) ? 1 : 0;
		const bool spell_ready = (kit.dmg >= 0 && cd[static_cast<std::size_t>(kit.dmg)] <= 0) || (kit.cc >= 0 && cd[static_cast<std::size_t>(kit.cc)] <= 0) ||
			(kit.aoe >= 0 && cd[static_cast<std::size_t>(kit.aoe)] <= 0);
		if ((spell_ready && nd <= 4) || dbg_eng == 7 || dbg_eng == 17 || dbg_eng == 8 || dbg_hit_other)
			std::printf("SP r=%d ch=%d path=%d eng=%d task=%d nd=%d nt=%d nsp=%d cast=%d mv=%d atk=%d hp=%.0f/%.0f cd=%d,%d near=%d hito=%d\n", round, static_cast<int>(type), dbg_path, dbg_eng, task, nd, nt, nsp,
				static_cast<int>(cast_done), static_cast<int>(!can_move), static_cast<int>(!can_attack), hp, max_hp, cd[0], cd[1], static_cast<int>(enemy_near), static_cast<int>(dbg_hit_other));
	});
#endif

	if (P.mi_chip)
		chip_passing();
	if (shield_deferred && !cast_done && (in_awake_camp_range() || enemies_within(4) > 0))
		cast_self(kit.shield);
#ifdef LEGEND_TRACE
	debug_block({
		if (can_move && can_attack && !cast_done)
			std::printf("IDLE r=%d %d task=%d g=%d pos=(%d,%d) path=%d at=%d mf=%d near=%d\n", round, static_cast<int>(type), task, task_group, pos.x, pos.y, dbg_path, g_idle, g_mfail, enemy_near_d);
	});
#endif
	place_ward(false);
	update_priority();
	if (P.unstick_rounds > 0)
		unstick();
	if (P.fz_osc > 0)
		osc_guard();
	if (P.stall_guard > 0 && W.dash_off_until == round) // hole crossings are back: the plain-walls fields are stale
		nav().reset_fields();
	FSP("unstick");
	prebuild_fields();
	FSP("prebuild");
	if (P.g17_bait && (P.g17_bait != 2 || static_cast<int>(gems) >= P.g17_bait_bag) && !W.ally_spawn.is_set(pos))
	{
		// v17 g17_bait (Mite's trick): end the turn recalling; enemy bots that treat a recalling carrier as a stuck kill walk into us.
		// Any damage cancels it silently; we cancel it ourselves at the start of the next turn.
		const auto st = bc::self().state();
		if (!st.contains(bc::champion_state::recalling) && !st.contains(bc::champion_state::submitting_gems) && !st.contains(bc::champion_state::teleporting))
		{
			try
			{
				bc::self().recall();
				g17_bait_on = true;
			}
			catch (...)
			{
			}
		}
	}
#ifdef G17_TRACE
	{
		int nd = 99;
		for (const auto& e : W.enemies)
			if (e.alive && e.visible)
				nd = std::min(nd, cheb(e.pos, pos));
		std::printf("G7 r=%d ch=%d path=%d task=%d nd=%d mv=%d hit=%d hp=%.2f\n", round, static_cast<int>(type), dbg_path, task, nd, static_cast<int>(!can_move),
			static_cast<int>(round == target_hit_round), hp / std::max(1.f, max_hp));
	}
#endif
	XM(xm_post());
#ifdef LEGEND_TRACE
	debug_block({
		std::printf("T r=%d %d task=%d g=%d pos=(%d,%d) hp=%.0f gems=%u gold=%u fuel=%llu\n", round, static_cast<int>(type), task, task_group, pos.x, pos.y, hp, gems, gold,
			static_cast<unsigned long long>(bc::fuel_remaining()));
		if (W.obj_mode && round % 25 == 0)
			for (int id : W.obj_groups)
			{
				const auto& og = W.groups[static_cast<std::size_t>(id)];
				float k = 0;
				const bool rd = obj_team_ready(og, og.st == ST_ALIVE ? og.hp_total : og.max_hp, k);
				int eta = 0;
				const float sc = group_score(og, eta);
				std::printf("OB r=%d %d g=%d st=%d hp=%.0f ready=%d kill=%.1f score=%.3f\n", round, static_cast<int>(type), id, static_cast<int>(og.st), og.hp_total, static_cast<int>(rd), k, sc);
			}
	});
#endif
	if (P.farm_ema > 0.f)
	{
		// T09d: remember what the camp model predicts for the next round when we farm alone inside every live camp's reach; the next
		// turn compares it with the health we actually lost (a model that measures its own error).
		farm_pred = 0.f;
		if (task == T_FARM && task_group >= 0 && task_group < static_cast<int>(W.groups.size()))
		{
			const auto& g = W.groups[static_cast<std::size_t>(task_group)];
			bool all_in_reach = g.st == ST_ALIVE && g.awake;
			for (std::size_t i = 0; i < g.camps.size() && all_in_reach; ++i)
				if (g.hp[i] > 0 && g.camps[i].str > 0)
					all_in_reach = cheb(g.camps[i].pos, pos) <= g.camps[i].range;
			for (std::size_t i = 0; i < W.allies.size() && all_in_reach; ++i)
				if (static_cast<int>(i) != W.my_index && W.allies[i].alive && W.allies[i].visible && cheb(W.allies[i].pos, g.center) <= 5)
					all_in_reach = false; // a camp hits the nearest champion only
			if (all_in_reach && enemies_within(6) == 0)
				farm_pred = incoming_on_raw(g);
		}
	}
#ifdef Q_TRACE
	q_line(dbg_path);
#endif
	if (P.v27_watch > 0)
		progress_watch(last_act_round == round || cast_done || target_hit_round == round);
	C.write_self(W.my_index, (task == T_FARM || task == T_CAPTURE || task == T_WAIT) ? task_group : -1);
	last_hp = hp;
}

#ifdef Q_TRACE
void Brain::q_line(int path) const
{
	debug_block({
		auto& W = world();
		int tst = -1, td = -1, tw = -1;
		if (task_group >= 0 && task_group < static_cast<int>(W.groups.size()))
		{
			const auto& g = W.groups[static_cast<std::size_t>(task_group)];
			tst = static_cast<int>(g.st), td = cheb(g.center, pos), tw = g.st == ST_RESPAWN ? g.ready_round - round : 0;
		}
		const int dcd = kit.dash >= 0 ? cd[static_cast<std::size_t>(kit.dash)] : -1;
		std::printf("Q r=%d i=%d ty=%d a=%d,%d b=%d,%d task=%d g=%d path=%d eng=%d idl=%d mf=%d hp=%.2f gems=%u en=%d tst=%d td=%d tw=%d hit=%d cast=%d dcd=%d cd=%d,%d\n",
			round, W.my_index, static_cast<int>(type), q_p0.x, q_p0.y, pos.x, pos.y, task, task_group, path, dbg_eng, g_idle, g_mfail, hp / std::max(1.f, max_hp), gems,
			enemy_near_d, tst, td, tw, static_cast<int>(target_hit_round == round), static_cast<int>(cast_done), dcd, cd[0], cd[1]);
	});
}
#endif

// mi_learn_burst (default branch): attribute the champion damage we took since our last turn (health lost minus what the
// camps in reach could deal) to the most threatening visible enemy within 5, and remember each enemy's biggest such hit:
// its real burst, items included, which the model (base stats x modifiers) underestimates once it has bought Power.
void Brain::learn_burst()
{
	auto& W = world();
	auto& L = learner();
	if (L.enemy_burst.size() != W.enemies.size())
		L.enemy_burst.assign(W.enemies.size(), 0.f);
	if (mi_last_round == round - 1)
	{
		const float took = last_hp - hp - mi_camp_in_prev;
		if (took > 30.f)
		{
			int who = -1;
			float best = -1;
			for (std::size_t i = 0; i < W.enemies.size(); ++i)
			{
				const auto& e = W.enemies[i];
				if (!e.alive || !e.visible || cheb(e.pos, pos) > 5)
					continue;
				const float threat = e.str + e.focus * best_mod(e.kit);
				if (threat > best)
					best = threat, who = static_cast<int>(i);
			}
			if (who >= 0)
				L.enemy_burst[static_cast<std::size_t>(who)] = std::max(L.enemy_burst[static_cast<std::size_t>(who)], took);
		}
	}
	mi_last_round = round;
	mi_camp_in_prev = mi_camp_in;
}

bool Brain::is_altar_tile(vec2 p) const
{
	for (const auto& a : world().altars)
		if (a == p)
			return true;
	return false;
}

bool Brain::altar_ours(std::size_t i) const
{
	// Walls, spawns and approach tiles never change, so neither does an altar's side: computed once per altar. Recomputing it (two
	// distance reads per approach tile, every altar) cost the opponent model's leader ~5k fuel a turn (FUEL_TRACE, nx60x60 ~10k).
	const auto& W = world();
	if (altar_side.size() != W.altars.size())
		altar_side.assign(W.altars.size(), -1);
	if (i >= altar_side.size())
		return false;
	auto& s = altar_side[i];
	if (s < 0)
	{
		int dh = BIG, da = BIG;
		if (i < W.altar_approach.size())
			for (const auto t : W.altar_approach[i])
				dh = std::min(dh, W.dist_home(t)), da = std::min(da, W.dist_away(t));
		s = dh < BIG && dh <= da ? 1 : 0;
	}
	return s > 0;
}

bool Brain::om_enemy_ours(std::size_t k)
{
	// Visible enemy k nearer our spawn than theirs and not on its own spawn; one evaluation per enemy per turn (three host reads), the
	// spawn test only when the distances already say "ours" (an enemy on its spawn is nearer its own).
	if (om_half_round != round)
		om_half_round = round, om_half.fill(-1);
	if (k >= om_half.size())
		return false;
	auto& v = om_half[k];
	if (v < 0)
	{
		const auto& W = world();
		const vec2 p = W.enemies[k].pos;
		v = W.dist_home(p) < W.dist_away(p) && !W.enemy_spawn.is_set(p) ? 1 : 0;
	}
	return v > 0;
}

bool Brain::escort_alert() const
{
	// The escort reuses the DANGER code at an altar tile (no enemy can stand there); with om_sight on, DANGER elsewhere is a sighting.
	const auto& C = comms();
	return C.alert_kind == AL_DANGER && (!P.om_sight || is_altar_tile(C.alert_pos));
}

void Brain::om_tick_traced()
{
#ifdef FUEL_TRACE
	// tools/fueltrace.py: fuel spent by the opponent model's per-turn code (the two fuel reads only exist in FUEL_TRACE builds).
	const auto f0 = bc::fuel_remaining();
	om_tick();
	const auto f1 = bc::fuel_remaining();
	debug_block({ std::printf("OMF r=%d i=%d %lld\n", round, world().my_index, static_cast<long long>(f0) - static_cast<long long>(f1)); });
#else
	om_tick();
#endif
}

void Brain::om_tick()
{
	// Every body, every turn (alive or dead). Leader: close the window (classify, broadcast, reset the shared invasion counter), then
	// gather this turn's signals. Every living body: count itself once per window in the invasion counter, post sightings.
	auto& W = world();
	auto& C = comms();
	const int wid = round / std::max(1, P.om_window);
	if (P.opp_model && W.my_index == 0)
	{
		auto& M = opp_model();
		if (M.win_id < 0)
		{
			std::vector<bc::champion_type> et;
			for (const auto& e : W.enemies)
				et.push_back(e.type);
			M.set_prior(et);
			M.win_id = wid;
			om_theirs = static_cast<int>(bc::global_submitted_gems(team::enemy));
			om_ad = W.ally_deaths, om_ed = W.enemy_deaths, om_ad_home = learner().ally_deaths_our_half;
			om_gst.assign(W.groups.size(), -1);
			om_heavy_ids.clear();
			for (const auto& g : W.groups)
				if (g.monolith || g.gems >= P.om_heavy)
					om_heavy_ids.push_back(g.id);
		}
		if (wid != M.win_id)
		{
			M.cur.inv = C.inv_count;
			M.end_window(static_cast<int>(W.allies.size()), round);
#ifdef OPP_TRACE
			debug_block({
				const auto& w = M.cur;
				std::printf("OM r=%d inv=%d ad=%d ed=%d multi=%d home=%d pack=%d banks=%d gems=%d lump=%d ward=%d/%d/%d locks=%d cancels=%d altar=%d bush=%d unseen=%d heavy=%d alive=%d vis=%d invs=%d bodies=%d ours=%d theirs=%d contact=%.2f mu=%.2f cus=%.2f/%.2f fired=%d ev=",
					round, w.inv, w.ally_deaths, w.enemy_deaths, w.multi_deaths, w.ally_deaths_home, w.pack, w.bank_events, w.bank_gems, w.bank_lump, w.ward_home, w.ward_altar, w.ward_bush,
					w.locks, w.cancels, w.altar_presence, w.bush_hits, w.unseen_hits, w.heavy_lost, w.alive_rounds, w.vis_max, w.inv_self, static_cast<int>(W.allies.size()),
					static_cast<int>(bc::global_submitted_gems(team::ally)), static_cast<int>(bc::global_submitted_gems(team::enemy)), M.contact, M.cus_mu, M.cus_pos, M.cus_neg, static_cast<int>(M.fired));
				for (int a = 1; a < ARC_COUNT; ++a)
					std::printf("%.2f,", M.ev[static_cast<std::size_t>(a)]);
				std::printf(" s=");
				for (int a = 1; a < ARC_COUNT; ++a)
					std::printf("%.2f,", M.score[static_cast<std::size_t>(a)]);
				std::printf(" arc=%s plan=%d\n", arc_name(M.arc), M.plan_id(learner().stance));
			});
#endif
			C.reset_invasion();
			M.cur = OmWindow{};
			M.win_id = wid;
		}
		auto& w = M.cur;
		++w.rounds;
		const int theirs = static_cast<int>(bc::global_submitted_gems(team::enemy));
		if (theirs > om_theirs)
		{
			++w.bank_events;
			w.bank_gems += theirs - om_theirs;
			w.bank_lump = std::max(w.bank_lump, theirs - om_theirs);
		}
		om_theirs = theirs;
		const int dad = W.ally_deaths - om_ad, ded = W.enemy_deaths - om_ed;
		if (dad > 0)
		{
			w.ally_deaths += dad;
			if (dad >= 2 || round - om_last_ad_round <= 3)
				++w.multi_deaths; // two of us down within 3 rounds: a pack fight
			om_last_ad_round = round;
		}
		w.enemy_deaths += std::max(0, ded);
		w.ally_deaths_home += std::max(0, learner().ally_deaths_our_half - om_ad_home);
		om_ad = W.ally_deaths, om_ed = W.enemy_deaths, om_ad_home = learner().ally_deaths_our_half;
		if (alive)
		{
			++w.alive_rounds;
			om_observe();
		}
	}
	if (!alive)
		return;
	if (P.opp_model && om_inv_win != wid)
		for (std::size_t k = 0; k < W.enemies.size(); ++k)
			if (W.enemies[k].alive && W.enemies[k].visible && om_enemy_ours(k))
			{
				C.bump_invasion();
				om_inv_win = wid;
				break;
			}
	if (P.om_sight)
	{
		const bool busy = (C.fresh(round, 6) && (C.alert_kind == AL_RALLY || C.alert_kind == AL_OPPORTUNITY || (C.alert_kind == AL_DANGER && is_altar_tile(C.alert_pos)))) ||
						  (C.alert_kind == AL_OPPORTUNITY && C.t4_deadline > round); // v15: a posted tribute stays up until it lands
		if (!busy)
		{
			const Enemy* best = nullptr;
			for (std::size_t k = 0; k < W.enemies.size(); ++k)
			{
				const auto& e = W.enemies[k];
				if (P.g15_sight)
				{
					// v15: anywhere (our body's or our ward's sight), the one nearest to us, not on its own spawn
					if (e.alive && e.visible && !W.enemy_spawn.is_set(e.pos) && (!best || cheb(e.pos, pos) < cheb(best->pos, pos)))
						best = &e;
				}
				else if (e.alive && e.visible && om_enemy_ours(k) && (!best || W.dist_home(e.pos) < W.dist_home(best->pos)))
					best = &e;
			}
			if (best && !(C.alert_kind == AL_DANGER && C.fresh(round, 2) && cheb(C.alert_pos, best->pos) <= 3))
				C.post(AL_DANGER, best->pos, round);
		}
	}
}

void Brain::om_observe()
{
	// The leader's own view this turn (only it classifies; other bodies reach it through the invasion counter and the alert slot).
	auto& W = world();
	auto& w = opp_model().cur;
	const int wid = round / std::max(1, P.om_window);
	// Most turns see no enemy: the enemy loops below then add nothing, so they are skipped (same signals, less fuel).
	int nv = 0;
	for (const auto& e : W.enemies)
		nv += e.alive && e.visible;
	if (nv > 0)
	{
		// Largest pack: enemies within 4 of one visible enemy, itself included.
		for (const auto& e : W.enemies)
		{
			if (!e.alive || !e.visible)
				continue;
			int n = 0;
			for (const auto& o : W.enemies)
				n += o.alive && o.visible && cheb(o.pos, e.pos) <= 4;
			w.pack = std::max(w.pack, n);
		}
		bool home = false;
		for (std::size_t k = 0; k < W.enemies.size(); ++k)
			if (W.enemies[k].alive && W.enemies[k].visible)
				home = home || om_enemy_ours(k);
		w.vis_max = std::max(w.vis_max, nv);
		w.inv_self += home;
	}
	// Enemies, locks next to our altars (altars on our half).
	const bool any_lock = !W.enemy_locks.is_empty(); // one host read instead of one per altar
	if (nv > 0 || any_lock)
		for (std::size_t i = 0; i < W.altars.size(); ++i)
		{
			const vec2 a = W.altars[i];
			if (!altar_ours(i))
				continue;
			for (const auto& e : W.enemies)
				w.altar_presence += e.alive && e.visible && cheb(e.pos, a) <= 3;
			if (any_lock && W.enemy_locks.is_set(a))
			{
				if (om_lock_win != wid)
					om_lock_win = wid, om_lock_mask = 0;
				if (i < 30 && !(om_lock_mask & (1 << i)))
					om_lock_mask |= 1 << i, ++w.locks;
			}
		}
	// Our own tribute cancelled under threat (handle_channel) this turn or last.
	if (tribute_cancel_round >= round - 1 && tribute_cancel_round != om_cancel_seen)
		om_cancel_seen = tribute_cancel_round, ++w.cancels;
	// Health lost with no visible attacker in reach and no live camp near us (a camp hits from up to 5): a hit from a bush / out of sight.
	// The cheap tests first: the bitboard ones cost host calls and an allocation.
	if (hp < last_hp - 1.f)
	{
		bool seen = false;
		for (const auto& e : W.enemies)
			seen |= e.alive && e.visible && cheb(e.pos, pos) <= std::max(e.kit.attack_range + (e.kit.ranged ? 0 : 1), 5);
		bool quiet = !seen && !in_awake_camp_range();
		if (quiet)
		{
			bc::bitboard near5;
			near5.draw_chebyshev(pos, 5.f);
			quiet = (near5 & W.camp_occ).is_empty();
		}
		if (quiet)
		{
			++w.unseen_hits;
			bc::bitboard near;
			near.draw_chebyshev(pos, 4.f);
			if (!(near & bc::map::bushes()).is_empty())
				++w.bush_hits;
		}
	}
	// Enemy wards (one per champion): counted once per window per owner, by where they stand.
	if (round % 2 == 0)
		try
		{
			for (const auto& wd : bc::vision::wards(team::enemy))
			{
				const std::uint32_t h = ward_owner(wd);
				const vec2 p = wd.position();
				int idx = -1;
				for (int i = 0; i < static_cast<int>(W.enemies.size()) && i < 8; ++i)
					if (h != 0 && W.enemies[static_cast<std::size_t>(i)].handle == h)
						idx = i;
				if (idx < 0)
				{
					// Owner unknown (2.2.x SDK): one count per ward tile per window.
					if (om_ward_tiles_win != wid)
						om_ward_tiles.clear(), om_ward_tiles_win = wid;
					if (std::find(om_ward_tiles.begin(), om_ward_tiles.end(), p) != om_ward_tiles.end() || om_ward_tiles.size() >= 16)
						continue;
					om_ward_tiles.push_back(p);
				}
				else
				{
					if (om_ward_win[static_cast<std::size_t>(idx)] == wid + 1)
						continue;
					om_ward_win[static_cast<std::size_t>(idx)] = wid + 1;
				}
				if (W.dist_home(p) < W.dist_away(p))
				{
					++w.ward_home;
					if (bc::map::bushes().is_set(p))
						++w.ward_bush;
				}
				for (std::size_t ai = 0; ai < W.altars.size(); ++ai)
					if (cheb(W.altars[ai], p) <= 6 && altar_ours(ai))
					{
						++w.ward_altar;
						break;
					}
			}
		}
		catch (...)
		{
		}
	// Heavy groups we saw go from alive to taken while no ally claimed them.
	if (om_gst.size() == W.groups.size())
	{
		const auto& C = comms();
		for (const int id : om_heavy_ids)
		{
			const auto& g = W.groups[static_cast<std::size_t>(id)];
			if (g.seen_round != round)
				continue;
			int& prev = om_gst[static_cast<std::size_t>(g.id)];
			if (prev == ST_ALIVE && g.st != ST_ALIVE)
			{
				bool claimed = task_group == g.id;
				for (int i = 0; i < 6 && i < static_cast<int>(W.allies.size()); ++i)
					claimed |= C.claim[static_cast<std::size_t>(i)] == g.id;
				if (!claimed)
					++w.heavy_lost;
			}
			prev = g.st;
		}
	}
}

void Brain::dl_record()
{
	auto& W = world();
	DLRow r;
	r.round = round;
	r.hpf = hp / std::max(1.f, max_hp);
	for (const auto& e : W.enemies)
		if (e.alive && e.visible && cheb(e.pos, pos) <= 5)
		{
			++r.enemies5;
			r.casters5 += e.kit.dmg >= 0 || e.kit.aoe >= 0 || e.kit.cc >= 0 || e.kit.dash_mod > 0.f;
		}
	for (const auto& a : W.allies)
		r.allies6 += a.handle != self && a.alive && a.visible && cheb(a.pos, pos) <= 6;
	r.channel = flag(state, bc::champion_state::recalling) || flag(state, bc::champion_state::submitting_gems);
	dl_hist[static_cast<std::size_t>(round % 5)] = r;
}

void Brain::dl_on_death()
{
	// The rows of the last 5 rounds before this death (newest first).
	std::array<const DLRow*, 5> h{};
	int n = 0;
	for (int k = 1; k <= 5; ++k)
	{
		const auto& r = dl_hist[static_cast<std::size_t>(((round - k) % 5 + 5) % 5)];
		if (r.round == round - k)
			h[static_cast<std::size_t>(n++)] = &r;
	}
	if (n == 0)
		return;
	bool any_enemy = false, caster = false, alone = n >= 3;
	int max_en = 0;
	for (int k = 0; k < n; ++k)
	{
		any_enemy |= h[static_cast<std::size_t>(k)]->enemies5 > 0;
		caster |= h[static_cast<std::size_t>(k)]->casters5 > 0;
		max_en = std::max(max_en, h[static_cast<std::size_t>(k)]->enemies5);
		if (k < 3)
			alone &= h[static_cast<std::size_t>(k)]->allies6 == 0;
	}
	const float hp3 = n >= 3 ? h[2]->hpf : h[static_cast<std::size_t>(n - 1)]->hpf;
	auto bump = [&](float& v, int& r, float step, float cap) { v = std::min(cap, dl_val(v, r) + step); r = round; };
	const char* kind = "other";
	if (h[0]->channel)
		bump(dl_chan, dl_chan_r, 2.f, 4.f), kind = "channel";
	else if (!any_enemy)
		bump(dl_camp, dl_camp_r, 0.05f, 0.15f), kind = "camp";
	else if (hp3 >= 0.6f && caster)
		bump(dl_burst, dl_burst_r, 0.2f, 0.6f), kind = "burst";
	else if (alone && max_en >= 2)
		bump(dl_iso, dl_iso_r, 0.1f, 0.4f), kind = "isolated";
#ifdef DL_TRACE
	debug_block({ std::printf("DL r=%d ch=%d kind=%s hp3=%.2f burst=%.2f iso=%.2f chan=%.1f camp=%.2f\n", round, static_cast<int>(type), kind, hp3, dl_burst, dl_iso, dl_chan, dl_camp); });
#else
	(void)kind;
#endif
}

void Brain::remember_positions()
{
	// Called first thing in a turn: where we stood at the end of our last turn and where we saw the allies then
	// (no_split: who reached a reward first). `round` and `pos` still hold the last turn's values.
	my_prev_pos = pos, my_prev_round = round;
	const auto& A = world().allies;
	for (std::size_t i = 0; i < A.size() && i < 8; ++i)
		if (A[i].visible && A[i].seen_round == round)
		{
			if (!(ally_prev_round[i] == round - 1 && ally_prev_pos[i] == A[i].pos))
				ally_still_since[i] = round;
			ally_prev_pos[i] = A[i].pos, ally_prev_round[i] = round;
		}
}

void Brain::unstick()
{
	// Last resort: a body walking to a camp that has not left a 3x3 box (and not attacked) for unstick_rounds
	// gives the target up for a while. Every path to it may be held by allies or camps that do not move, or the
	// target sits where its own tiles block it; re-planning elsewhere beats standing there.
	auto& W = world();
	// stall_guard (session 14): every walking task counts, not only farm / capture (nx61x71: Ren stood 1,197 rounds in a tribute trip at a
	// hole crossing the dash could not take); a dash kit then routes without hole crossings for a while and rebuilds its fields.
	const bool guard = P.stall_guard > 0 && (task == T_TRIBUTE || task == T_HOME || task == T_FLEE);
	const bool walking = task == T_FARM || task == T_CAPTURE || guard;
	const bool on_reward = task == T_CAPTURE && task_group >= 0 && W.groups[static_cast<std::size_t>(task_group)].mask.is_set(pos);
	if (!walking || (task_group < 0 && !guard) || on_reward || last_act_round >= round - 1 || W.ally_spawn.is_set(pos) || cheb(pos, ust_anchor) > 1 ||
		flag(state, bc::champion_state::recalling) || flag(state, bc::champion_state::submitting_gems) || flag(state, bc::champion_state::teleporting))
	{
		ust_anchor = pos;
		ust_since = round;
		return;
	}
	if (round - ust_since < (guard ? P.stall_guard : P.unstick_rounds))
		return;
#ifdef LEGEND_TRACE
	debug_block({ std::printf("UNSTICK r=%d %d task=%d g=%d pos=(%d,%d) since=%d\n", round, static_cast<int>(type), task, task_group, pos.x, pos.y, ust_since); });
#endif
	if (P.stall_guard > 0 && kit.dash >= 0 && P.dash_holes)
	{
		W.dash_off_until = round + P.stall_dash_off;
		nav().reset_fields();
	}
	if (guard)
	{
		task = T_NONE;
		tribute_cancel_round = round; // no new tribute trip for two rounds: farm() re-plans from here first
		ust_anchor = pos;
		ust_since = round;
		return;
	}
#ifdef Q_TRACE
	debug_block({ std::printf("QBL r=%d i=%d why=unstick task=%d g=%d\n", round, W.my_index, task, task_group); });
#endif
	blacklist[static_cast<std::size_t>(task_group)] = round + P.unstick_blacklist;
	task_group = -1;
	tp_hop = -1;
	tp_island = -1;
	ust_anchor = pos;
	ust_since = round;
}

void Brain::osc_guard()
{
	// v14 fz_osc: a body walking back and forth with nothing to show for it (target flips, a detour that keeps turning, an approach that
	// gives way and comes back) re-plans with that target out of the way.
	auto& W = world();
	const bool walking = task == T_FARM || task == T_CAPTURE || task == T_WAIT || task == T_TRIBUTE || task == T_HOME;
	const bool quiet = walking && last_act_round < round && !cast_done && enemy_near_d > 5 && !W.ally_spawn.is_set(pos) &&
		!flag(state, bc::champion_state::recalling) && !flag(state, bc::champion_state::submitting_gems) && !flag(state, bc::champion_state::teleporting);
	const std::size_t i = static_cast<std::size_t>(round & 15);
	osc_pos[i] = pos;
	osc_quiet[i] = quiet ? round : -100;
	if (!quiet)
		return;
	const int n = std::min(15, P.fz_osc);
	int moves = 0;
	for (int k = 1; k < n; ++k)
	{
		const std::size_t a = static_cast<std::size_t>((round - k) & 15), b = static_cast<std::size_t>((round - k + 1) & 15);
		if (osc_quiet[a] != round - k)
			return;
		moves += osc_pos[a] == osc_pos[b] ? 0 : 1;
	}
	if (10 * moves < 6 * (n - 1) || cheb(pos, osc_pos[static_cast<std::size_t>((round - n + 1) & 15)]) > 1)
		return;
#ifdef LEGEND_TRACE
	debug_block({ std::printf("OSC r=%d %d task=%d g=%d pos=(%d,%d) moves=%d\n", round, static_cast<int>(type), task, task_group, pos.x, pos.y, moves); });
#endif
#ifdef Q_TRACE
	debug_block({ std::printf("QBL r=%d i=%d why=osc task=%d g=%d\n", round, W.my_index, task, task_group); });
#endif
	if ((task == T_FARM || task == T_CAPTURE || task == T_WAIT) && task_group >= 0 && task_group < static_cast<int>(W.groups.size()))
	{
		blacklist[static_cast<std::size_t>(task_group)] = round + P.fz_osc_bl;
		task_group = -1;
	}
	else if (task == T_TRIBUTE)
		tribute_cancel_round = round; // no new bank trip for two rounds: farm() re-plans first
	task = T_NONE;
	osc_quiet.fill(-100);
}

// v27_watch: the one guard for every stall (traced v83 local games: 4.3% of all turns paced in a 3x3 box or stood still; ladder: a
// 470-gem carrier stood 40 rounds alone, a capture of a contested gold row stood 490 rounds, a Heart of Ruin flipped between two
// targets and dashed back and forth every 8 rounds). No hit, cast, gems, gold, healing or channel while staying within 3 tiles for
// v27_watch rounds: the target is blacklisted and the hold rules (escort, gather, altar caution) are off for a while, so the next plan
// is a different one. Target flips do not reset the clock (they are the stall); waiting at a group whose respawn is due does.
void Brain::progress_watch(bool acted_now)
{
	auto& W = world();
	bool legit_wait = false;
	if (task == T_WAIT && task_group >= 0 && task_group < static_cast<int>(W.groups.size()))
	{
		const auto& g = W.groups[static_cast<std::size_t>(task_group)];
		legit_wait = g.st == ST_RESPAWN && g.ready_round + 3 >= round && cheb(pos, g.center) <= g.radius + 3;
	}
	const bool progress = acted_now || gems != pw_gems || gold != pw_gold || hp > pw_hp + 0.02f * max_hp || W.ally_spawn.is_set(pos) ||
		legit_wait || pw_since < 0 || cheb(pos, pw_anchor) > 3;
	pw_gems = gems, pw_gold = gold, pw_hp = hp;
	if (progress)
	{
		pw_since = round;
		pw_anchor = pos;
		pw_stall_hp = hp;
		return;
	}
	if (round - pw_since < P.v27_watch)
		return;
#ifdef Q_TRACE
	debug_block({ std::printf("QBL r=%d i=%d why=watch task=%d g=%d gems=%u""%c", round, W.my_index, task, task_group, gems, 10); });
#endif
	if (task_group >= 0 && task_group < static_cast<int>(W.groups.size()))
		blacklist[static_cast<std::size_t>(task_group)] = round + P.v27_watch_bl;
	if (task == T_TRIBUTE)
	{
		tribute_cancel_round = round;
		int ad = BIG;
		const int a = nearest_altar(ad);
		if (a >= 0 && P.v27_altar_ban)
		{
			if (pw_altar_ban.size() != W.altars.size())
				pw_altar_ban.assign(W.altars.size(), -1);
			pw_altar_ban[static_cast<std::size_t>(a)] = round + 40;
		}
	}
	if (gems >= 30 && task != T_TRIBUTE)
		pw_bank_until = round + 25; // a stalled carrier banks: the escort / altar caution holds are off
	if (task == T_FIGHT || task == T_FLEE)
	{
		std::vector<Enemy*> E;
		for (auto& e : W.enemies)
			if (e.alive && e.visible && cheb(e.pos, pos) <= 8)
				E.push_back(&e);
		avoid_note(E);
		// a flee standoff in which nothing hit us (they hold their spawn or an altar and never chase): stop stepping in and out of their
		// sight; the next hit ends the calm
		if (P.v27_calm && task == T_FLEE && hp >= pw_stall_hp - 1.f)
			pw_calm_until = round + 25, pw_calm_hp = hp;
	}
	pw_off_until = round + P.v27_watch_off;
	task_group = -1;
	task = T_NONE;
	mw_group = -1;
	tp_hop = -1;
	pw_since = round;
	pw_anchor = pos;
}

// v27_avoid: remember the enemies we fled from (their reach + 2) for v27_avoid rounds
void Brain::avoid_note(const std::vector<Enemy*>& E)
{
	if (P.v27_avoid <= 0)
		return;
	av_n = 0;
	for (auto* e : E)
	{
		if (av_n >= 8)
			break;
		if (!e->alive || world().enemy_spawn.is_set(e->pos))
			continue;
		const int reach = std::max(e->kit.attack_range + (e->kit.ranged ? 0 : 1), enemy_spell_reach(*e, true));
		av_pos[static_cast<std::size_t>(av_n)] = e->pos;
		av_rad[static_cast<std::size_t>(av_n)] = reach + 2;
		++av_n;
	}
	if (av_n > 0)
		av_until = round + P.v27_avoid;
}

bool Brain::in_avoid(const Group& g) const
{
	for (int k = 0; k < av_n; ++k)
		if (cheb(g.center, av_pos[static_cast<std::size_t>(k)]) <= av_rad[static_cast<std::size_t>(k)] + g.radius)
			return true;
	return false;
}

void Brain::handle_channel()
{
	// Channels are cut short only when finishing them would cost more than the bag or our life:
	// recall is broken by any damage (so an enemy about to reach us makes it pointless), a tribute survives
	// damage but not a stun or death.
	auto& me = bc::self();
	const bool recalling = flag(state, bc::champion_state::recalling);
	const bool tributing = flag(state, bc::champion_state::submitting_gems);
	float incoming = 0;
	bool stunner_close = false, threat_close = false;
	for (const auto& e : world().enemies)
	{
		if (!e.visible || !e.alive)
			continue;
		const int d = cheb(e.pos, pos);
		const int reach = e.kit.attack_range + (e.kit.ranged ? 0 : 1) + (e.ready(e.kit.dash) ? 2 : 0);
		if (d <= reach + 1)
		{
			threat_close = true;
			incoming += e.str + e.burst() / 2.f;
		}
		if (d <= 4 && (e.ready(e.kit.cc) || (e.ready(e.kit.aoe) && e.kit.aoe_stuns)))
			stunner_close = true;
		else if ((P.hor_threat & 1) && e.kit.dash_mod > 0.f && e.ready(e.kit.dash) && d <= static_cast<int>(e.kit.dash_range + e.kit.dash_radius) + 1)
		{
			stunner_close = threat_close = true; // Heart of Ruin lands next to us and stuns
			incoming += e.focus * e.kit.dash_mod;
		}
		else if (P.aoe_reach5 && e.ready(e.kit.aoe) && e.kit.aoe_stuns && d <= static_cast<int>(e.kit.aoe_range + e.kit.aoe_radius))
			stunner_close = true; // Ryth's area stun cancels a tribute from 5
	}
	bool cancel = false;
	if (recalling && threat_close && !world().ally_spawn.is_set(pos))
		cancel = true; // they will hit us before it completes: act instead of standing still
	if (P.recall_join && recalling && !cancel && task != T_CAPTURE && hp >= P.recall_join_hp * max_hp && !world().ally_spawn.is_set(pos) &&
		!(gems > 0 && wins_with(static_cast<int>(gems))))
	{
		// recall_join: a teammate is fighting next to us and we are healthy: stay for the fight instead of teleporting out of it
		const auto& W = world();
		bool enemy7 = P.recall_join >= 2; // 2: the ally's fight alone is enough (contest: our Ren was 10 tiles from the enemies)
		for (const auto& e : W.enemies)
			enemy7 |= e.visible && e.alive && cheb(e.pos, pos) <= 7 && !W.enemy_spawn.is_set(e.pos);
		if (enemy7)
			for (const auto& a : W.allies)
			{
				if (a.handle == self || !a.alive || !a.visible || cheb(a.pos, pos) > (P.recall_join >= 2 ? 8 : 6) || a.hp < 0.5f * a.max_hp)
					continue;
				for (const auto& e : W.enemies)
					if (e.visible && e.alive && cheb(e.pos, a.pos) <= 5)
						cancel = true;
			}
	}
	if (tributing && !(P.win_bank && wins_with(static_cast<int>(gems))))
	{
		// Turns still stuck in the channel: the bag stays carried until it lands, so counting from the bag gave
		// the full duration on every turn (the audit's channel-bookkeeping finding); count from the start instead.
		int left = std::max(1, static_cast<int>((gems + 9) / 10) - 1);
		if (P.tribute_elapsed && round - tribute_start <= tribute_ticks)
			left = std::max(1, tribute_ticks - (round - tribute_start));
		if (incoming * static_cast<float>(left + 1) >= hp || (stunner_close && gems >= 20 && threat_close && left > P.chan_keep))
			cancel = true;
	}
	if (cancel)
	{
		try
		{
			if (recalling)
				me.cancel_recall();
			else
			{
				me.cancel_submit_gems();
				tribute_cancel_round = round;
			}
		}
		catch (...)
		{
		}
		return;
	}
	auto& C = comms();
	C.write_self(world().my_index, task == T_CAPTURE ? task_group : -1);
}

void Brain::shop()
{
	auto& me = bc::self();
	auto& W = world();
	const bool on_spawn = alive && W.ally_spawn.is_set(pos);
	const bool remote = type == CT::tavi;
	if (!on_spawn && alive && !remote)
		return;
	// A teleport crystal opens uncontested island camps; it is cheap, buy it first.
	bool any_hop = false;
	for (const auto& h : W.hops)
		any_hop |= h.valid;
	if ((on_spawn || !alive) && (!W.islands.empty() || any_hop) && gold >= 10)
	{
		try
		{
			if (me.consumables()[bc::consumable_type::tp_crystal].count() == 0)
			{
				me.buy(bc::consumable_type::tp_crystal);
				gold -= 10;
			}
		}
		catch (...)
		{
		}
	}
	if (P.ic_home == 3 && recalls_started >= P.ic_home_recalls)
		insert_home(build_idx);
	if (P.build_react > 0.f && alive && enemy_burst_seen > 0.f && max_hp < P.build_react * enemy_burst_seen && gold >= 150)
		insert_health(build_idx); // build_react: answer the enemy's damage with health before the next planned emblem
	if (P.v23_shop && type == CT::tavi && on_spawn && round > 600)
		v23_tavi_sell(); // v23 4.7: Tavi sells its Jungle emblem at full value for Bruiser once the camps no longer hurt
	while (build_idx < build.size() && gold >= 30 && (P.g17_shop_cap <= 0 || build_idx < static_cast<std::size_t>(P.g17_shop_cap)))
	{
		const I item = build[build_idx];
		std::uint32_t n = 0;
		while (build_idx + n < build.size() && build[build_idx + n] == item && gold >= 30 * (n + 1))
			++n;
		try
		{
			me.buy(item, n);
			build_idx += n;
			gold -= 30 * n;
		}
		catch (...)
		{
			break;
		}
	}
	// A spare altar lock once the first emblem is done (consumables only on spawn or while dead).
	if ((on_spawn || !alive) && (build_idx >= 5 || (P.g15_lock & 1)) && gold >= 10)
	{
		try
		{
			if (me.consumables()[bc::consumable_type::altar_lock].count() == 0)
			{
				me.buy(bc::consumable_type::altar_lock);
				gold -= 10;
			}
		}
		catch (...)
		{
		}
	}
	if (on_spawn)
	{
		// Health bought on spawn heals; refresh our numbers.
		bc::detail::champion_info i{};
		if (bc::detail::sdk_champion(self, &i) == 0)
			hp = i.health, max_hp = std::max(1.f, i.max_health), str = i.strength, focus = i.focus;
	}
}

// ---------------------------------------------------------------------------------------------- perception helpers

void Brain::build_danger()
{
	auto& W = world();
	danger.clear();
	danger4.clear();
	camp_danger.clear();
	enemy_near = false;
	enemy_near_field = false;
	enemy_near_d = BIG;
	for (const auto& e : W.enemies)
	{
		if (!e.alive || e.seen_round < 0)
			continue;
		const int age = round - e.seen_round;
		if (age > P.threat_memory)
			continue;
		// Cooldowns are known while visible; an unseen enemy is assumed to have everything ready.
		const bool fresh = age == 0;
		// mi_cd_slack (default branch): a spell coming off cooldown next turn is as good as up (we move once before it acts).
		auto up = [&](int slot) { return slot >= 0 && (!fresh || e.cd[static_cast<std::size_t>(slot)] <= P.mi_cd_slack); };
		const bool dash_up = up(e.kit.dash);
		const bool spell_up = up(e.kit.dmg) || up(e.kit.cc) || up(e.kit.aoe);
		// mi_walk_cast: a spell that does not end the move can follow a step, so it reaches one tile further.
		const bool walk_cast = (up(e.kit.dmg) && !e.kit.dmg_excl) || (up(e.kit.cc) && !e.kit.cc_excl) || (up(e.kit.aoe) && !e.kit.aoe_excl);
		int reach = e.kit.attack_range + (e.kit.ranged ? 0 : 1) + (dash_up ? 2 : 0);
		const int reach0 = std::max(reach, spell_up ? 4 : 0) + age;
		if (P.aoe_reach5)
			reach = std::max(reach, enemy_spell_reach(e, !fresh));
		else if (spell_up)
			reach = std::max(reach, 4 + (P.mi_walk_cast && walk_cast ? 1 : 0));
		reach += age;
		danger.draw_chebyshev(e.pos, static_cast<float>(reach));
		if (P.aoe_reach5 == 3)
			danger4.draw_chebyshev(e.pos, static_cast<float>(reach0)); // routes avoid 5, the fight/flee trigger stays at 4
		const int ed = cheb(e.pos, pos);
		if (ed <= 9)
		{
			enemy_near = true;
			// An enemy on its own spawn heals fully every round and cannot chase a bag that stays away; on
			// maps whose spawns touch, counting it made every body bank whatever it carried straight off its
			// spawn (30x80: 40 bank walks of 37 steps for 22-25 gems each).
			if (!P.bank_ignore_spawn || !W.enemy_spawn.is_set(e.pos))
				enemy_near_field = true;
		}
		enemy_near_d = std::min(enemy_near_d, std::max(0, ed - (P.near_age_cap > 0 ? std::min(age, P.near_age_cap) : age)));
	}
	if (P.risky_persist > 0)
		enemy_near_rounds = enemy_near_field ? enemy_near_rounds + 1 : 0;
	mi_camp_in = 0;
	for (const auto& g : W.groups)
		if (g.st == ST_ALIVE && g.awake && g.hp_total > 0 && !g.harmless && cheb(g.center, pos) <= 10)
		{
			camp_danger |= g.near;
			if ((P.mi_learn_burst || P.mi_lethal) && g.near.is_set(pos))
				for (std::size_t i = 0; i < g.camps.size(); ++i)
					if (g.hp[i] > 0 && cheb(g.camps[i].pos, pos) <= g.camps[i].range)
						mi_camp_in += g.camps[i].str; // what the camps could have hit us for (learn_burst subtracts it)
		}
	clump.clear();
	splash_threat = false;
	if (P.spread_vs_splash)
	{
		// A4: Varg's swing splashes radius 1 around its target, area spells hit radius 1: two of ours side by side take
		// it twice (top-3 replays: 14% of our deaths had Varg splash on the victim and an ally in one swing; theirs 6%).
		for (const auto& e : W.enemies)
			if (e.alive && e.visible &&
				((e.type == CT::varg && cheb(e.pos, pos) <= 4) || (e.kit.aoe >= 0 && (P.spread_vs_splash == 2 || e.ready(e.kit.aoe)) && cheb(e.pos, pos) <= 5)))
			{
				splash_threat = true;
				break;
			}
		if (splash_threat)
			for (const auto& a : W.allies)
				if (a.handle != self && a.alive && a.visible && cheb(a.pos, pos) <= 3)
					clump.draw_chebyshev(a.pos, 1.f);
	}
	bool pair_clump = false;
	if (P.pair_space >= 2 && type == CT::cassi && enemy_near)
		for (const auto& a : W.allies)
			if (a.handle != self && a.alive && a.visible && a.type == CT::issac && cheb(a.pos, pos) <= 3)
			{
				// A9: with enemies near, Cassi's steps avoid the tiles next to Issac (one area spell or Varg swing on
				// the pair kills both bodies through the link).
				clump.draw_chebyshev(a.pos, 1.f);
				pair_clump = true;
			}
	g_soft_avoid = (splash_threat || pair_clump) ? &clump : nullptr;
	alert_zone.clear();
	const auto& C = comms();
	if (P.alert_radius > 0 && C.alert_kind == AL_DANGER && C.fresh(round, P.alert_age))
		alert_zone.draw_chebyshev(C.alert_pos, static_cast<float>(P.alert_radius));
}

bool Brain::in_awake_camp_range() const { return camp_danger.is_set(pos); }

bool Brain::wakes_sleeper(vec2 c, int rad)
{
	// v26_nowake: camps wake only from damage, and a woken group hits the nearest champion every round until nobody is in reach. An area
	// cast or a damaging dash that touches a sleeping camp of a group that fights back and that we are not farming starts that (ladder v81:
	// 18 of our 53 camp deaths to a group the victim's own spell woke, 14 to one an ally woke; anvil: a centre fight cast next to the
	// monolith killed our Vesper Vale, 200 a round).
	if (!P.v26_nowake)
		return false;
	if (asleep_round != round)
	{
		asleep_round = round;
		asleep_bb.clear();
		try
		{
			bc::vision::asleep_camp_tiles_into(asleep_bb);
		}
		catch (...)
		{
		}
	}
	bc::bitboard area;
	area.draw_chebyshev(c, static_cast<float>(std::max(0, rad)));
	const bc::bitboard hit = area & asleep_bb;
	if (hit.is_empty())
		return false;
	const auto& W = world();
	for (const auto t : hit.positions())
	{
		const int gid = W.group_at(t);
		if (gid < 0 || gid == nowake_ok || (gid == task_group && (task == T_FARM || task == T_CAPTURE)))
			continue;
		if (!W.groups[static_cast<std::size_t>(gid)].harmless)
			return true;
	}
	return false;
}

void Brain::nowake_prepare()
{
	nowake_ok = -1;
	g_dash_avoid = nullptr;
	if (!P.v26_nowake || kit.dash < 0 || kit.dash_mod <= 0.f || !alive)
		return;
	// Heart of Ruin's dash hits every tile within dash_radius of its landing: walking dashes skip landings next to a sleeping fighter.
	asleep_round = round;
	asleep_bb.clear();
	try
	{
		bc::vision::asleep_camp_tiles_into(asleep_bb);
	}
	catch (...)
	{
	}
	dash_avoid.clear();
	if (asleep_bb.is_empty())
		return;
	const auto& W = world();
	const float rad = static_cast<float>(std::max(0, static_cast<int>(kit.dash_radius)));
	for (const auto t : asleep_bb.positions())
	{
		if (cheb(t, pos) > 6)
			continue;
		const int gid = W.group_at(t);
		if (gid < 0 || (gid == task_group && (task == T_FARM || task == T_CAPTURE)) || W.groups[static_cast<std::size_t>(gid)].harmless)
			continue;
		dash_avoid.draw_chebyshev(t, rad);
	}
	if (!dash_avoid.is_empty())
		g_dash_avoid = &dash_avoid;
}

int Brain::enemies_within(int r) const
{
	int n = 0;
	for (const auto& e : world().enemies)
		if (e.alive && e.visible && cheb(e.pos, pos) <= r)
			++n;
	return n;
}

int Brain::nearest_altar(int& dist) const
{
	auto& W = world();
	int best = -1;
	dist = BIG;
	for (std::size_t i = 0; i < W.altars.size(); ++i)
	{
		nav().ensure_altar(static_cast<int>(i));
		int d = nav().altar_dist(static_cast<int>(i), pos);
		if (i < pw_altar_ban.size() && pw_altar_ban[i] > round)
			d += 200; // v27_watch: a bank trip to it stalled (camps or bodies block the way): another altar, or the recall to spawn

		if (P.altar_no_camp >= 2 && !W.altar_open(static_cast<int>(i)))
			continue; // its approach tile is a living camp's spawn tile
		if (W.altar_locked_by_enemy(static_cast<int>(i)))
			d += P.lock_hits_sdk ? 2 * static_cast<int>(bc::constants::altar_lock_hits) : 6; // hits to clear it (patch 3.0: 5)
		if (P.v23_bank ? v23_altar_unsafe(static_cast<int>(i)) : altar_unsafe(static_cast<int>(i)))
			d += P.unsafe_altar_penalty; // contested and enemies seen there: our carriers die on the way
		if (P.ward_enemy && static_cast<int>(gems) >= P.ward_avoid_bag && near_enemy_ward(W.altars[i], 6))
			d += static_cast<int>(P.ward_avoid_cost); // a watched altar: a long channel in their sight
		if (P.escort_alt_w > 0.f && P.escort_bag > 0 && static_cast<int>(gems) >= (P.opp_model ? escort_bag_now : P.escort_bag) && round - W.altar_enemy_round[i] <= P.escort_quiet)
			d += static_cast<int>(P.escort_alt_w * static_cast<float>((gems + 9) / 10));
		if (d < dist)
			dist = d, best = static_cast<int>(i);
	}
	return best;
}

bool Brain::after_move(bool moved)
{
	if (!moved)
	{
#ifdef LEGEND_TRACE
		g_mfail = g_idle ? g_idle : 1;
#endif
		return false;
	}
	// Refresh allowances after moving (ranged champions lose their attack when walking; a dash spends the cast).
	bc::detail::champion_info i{};
	if (bc::detail::sdk_champion(self, &i) == 0)
	{
		pos = { i.x, i.y };
		can_move = flag(i.state, bc::champion_state::can_move);
		can_attack = flag(i.state, bc::champion_state::can_attack);
		can_cast = flag(i.state, bc::champion_state::can_cast);
	}
	if (kit.dash >= 0)
	{
		std::int32_t c = 0;
		if (bc::detail::sdk_champion_cooldown(self, static_cast<std::uint32_t>(kit.dash), &c) == 0 && c > cd[static_cast<std::size_t>(kit.dash)])
		{
			cd[static_cast<std::size_t>(kit.dash)] = c;
			cast_done = true;
		}
	}
	return true;
}

bool Brain::step(const bc::bitboard& goals, bool avoid_danger, bool allow_dash)
{
	if (bc::fuel_remaining() < 22000)
	{
		const auto pts = goals.positions();
		if (pts.empty() || !can_move)
			return false;
		try
		{
			return after_move(bc::self().move_towards(pts.front()));
		}
		catch (...)
		{
		}
		return false;
	}
	bc::bitboard avoid = danger | camp_danger | alert_zone;
	return after_move(Nav::step_to(pos, goals, avoid_danger ? &avoid : nullptr, allow_dash ? mob_dash() : -1, can_move));
}

// Dash slot for walking. A dash that lands for damage and a stun (Heart of Ruin, patch 3.0) is its main fight spell: not spent on
// travel while an enemy was seen within strike_dash_hold (engage() sets strike_dash for the dash onto a target).
int Brain::mob_dash() const
{
	if (kit.dash < 0)
		return -1;
	if (kit.dash_mod > 0.f && !strike_dash && enemy_near_d <= P.strike_dash_hold)
		return -1;
	return kit.dash;
}

bool Brain::go_group(Group& g, int stop_at, bool avoid)
{
	auto& N = nav();
	bc::bitboard fallback;
	// Farming a live group: the goal is reach of a camp still standing. Any group tile (dead camps included)
	// made a tile next to a dead wolf count as arrived while its live partner stood two tiles away: on the
	// 98x99 map, where the group field is often not built yet, bodies froze there for 30-78 rounds.
	bool live = false;
	if (P.stuck_live_goal && stop_at > 0 && g.st == ST_ALIVE)
		for (std::size_t i = 0; i < g.camps.size(); ++i)
			if (g.hp[i] > 0)
			{
				fallback.draw_chebyshev(g.camps[i].pos, static_cast<float>(stop_at));
				live = true;
			}
	if (!live)
		for (auto t : g.tiles)
			fallback.draw_chebyshev(t, static_cast<float>(stop_at));
	if (stop_at > 0)
		fallback &= ~g.mask;
	const bc::bitboard av = danger | (camp_danger & ~g.near) | alert_zone;
	if (N.ensure_group(g.id, P.target_field_fuel))
	{
		const auto& f = N.group_fields[static_cast<std::size_t>(g.id)];
		if (after_move(Nav::step_field(pos, f, stop_at, avoid ? &av : nullptr, mob_dash(), can_move, fallback)))
			return true;
		// v14 fz_dash 2: Heart of Ruin keeps its strike dash near enemies; when no walking step leads on (a hole crossing) and nobody
		// is close, crossing beats standing still.
		if ((P.fz_dash & 2) && kit.dash >= 0 && mob_dash() < 0 && ready(kit.dash) && enemy_near_d > 5 && f.get(pos) > stop_at)
			return after_move(Nav::step_field(pos, f, stop_at, avoid ? &av : nullptr, kit.dash, can_move, fallback));
#ifdef NAV_TRACE
		debug_block({
			const bc::bitboard blk = Nav::blocked_now(pos);
			const bc::bitboard holes = bc::map::holes(), walls = bc::map::walls();
			std::printf("NAVF r=%d %d g=%d pos=(%d,%d) here=%d stop=%d mv=%d dash=%d mob=%d rdy=%d nd=%d |", round, static_cast<int>(type), g.id, pos.x, pos.y,
				f.get(pos), stop_at, static_cast<int>(can_move), kit.dash, mob_dash(), kit.dash >= 0 ? static_cast<int>(ready(kit.dash)) : -1, enemy_near_d);
			for (auto d : { vec2{ -1, -1 }, vec2{ 0, -1 }, vec2{ 1, -1 }, vec2{ -1, 0 }, vec2{ 1, 0 }, vec2{ -1, 1 }, vec2{ 0, 1 }, vec2{ 1, 1 } })
			{
				const vec2 p = pos + d;
				if (!bc::map::is_in_bounds(p))
					continue;
				std::printf(" %d%s%s%s%s", f.get(p), walls.is_set(p) ? "W" : "", holes.is_set(p) ? "H" : "", blk.is_set(p) ? "B" : "", av.is_set(p) ? "A" : "");
			}
			std::printf("\n");
		});
#endif
		return false;
	}
	return after_move(Nav::step_to(pos, fallback, avoid ? &av : nullptr, mob_dash(), can_move));
}

bool Brain::go_altar(int id)
{
	auto& N = nav();
	auto& W = world();
	bc::bitboard fallback;
	for (auto t : W.altar_approach[static_cast<std::size_t>(id)])
		fallback.set(t);
	const bc::bitboard av = danger | camp_danger | alert_zone;
	if (N.ensure_altar(id, P.target_field_fuel))
		return after_move(Nav::step_field(pos, N.altar_fields[static_cast<std::size_t>(id)], 0, &av, mob_dash(), can_move, fallback));
	return after_move(Nav::step_to(pos, fallback, &av, mob_dash(), can_move));
}

// pocket_fix (patch 3.0.4, found with the dynamic draft's dash kits): a body standing where no walk leads home (W.home is built on
// plain walls: a hole pocket entered by a dash, nx100x100's gold pocket at (28,21)) has no improving step on the home field, and the
// dynamic fallback search cannot reach home either: it burned the whole turn's fuel every turn (Vesper: 149 lost turns, stuck 280
// rounds). Dash to the landing tile with the shortest walk home instead.
bool Brain::pocket_dash()
{
	auto& W = world();
	if (kit.dash < 0 || !ready(kit.dash))
		return false;
	const int rng = std::max(1, static_cast<int>(kit.dash_range));
	const bc::bitboard blocked = Nav::blocked_now(pos);
	std::array<std::pair<int, vec2>, 25> c{};
	int n = 0;
	for (int dy = -rng; dy <= rng; ++dy)
		for (int dx = -rng; dx <= rng; ++dx)
		{
			const vec2 q{ pos.x + dx, pos.y + dy };
			if ((dx == 0 && dy == 0) || !bc::map::is_in_bounds(q) || blocked.is_set(q) || n >= static_cast<int>(c.size()))
				continue;
			const int d = W.dist_home(q);
			if (d < BIG)
				c[static_cast<std::size_t>(n++)] = { d, q };
		}
	std::sort(c.begin(), c.begin() + n, [](const auto& a, const auto& b) { return a.first < b.first; });
	for (int i = 0; i < n && i < 4; ++i)
	{
		try
		{
			if (bc::self().abilities()[static_cast<std::size_t>(kit.dash)].use(c[static_cast<std::size_t>(i)].second))
			{
				pos = c[static_cast<std::size_t>(i)].second;
				cast_done = true;
				return after_move(true);
			}
		}
		catch (...)
		{
		}
	}
	return false;
}

bool Brain::go_home_step(bool avoid)
{
	auto& W = world();
	if (P.pocket_fix && W.dist_home(pos) >= BIG && pocket_dash())
		return true;
	if (P.v23_flee_away && avoid && can_move)
	{
		// v23_flee_away (ladder, 6,332 hit-first episodes of v80): the first step after being hit decides; a sideways step (distance to the
		// attacker unchanged) died 22% at >= 60% health and 46% below, a step away 12% / 21%. Leaving = a step that opens the distance to the
		// nearest enemy, the one that loses least toward home (at most one step); otherwise the field step below.
		const Enemy* t = nullptr;
		int td = BIG;
		for (const auto& e : W.enemies)
			if (e.alive && e.visible && !W.enemy_spawn.is_set(e.pos) && cheb(e.pos, pos) < td)
				td = cheb(e.pos, pos), t = &e;
		if (t && td <= 5)
		{
			const bc::bitboard blocked = Nav::blocked_now(pos);
			const int h0 = W.dist_home(pos);
			vec2 best = pos;
			int bh = BIG;
			for (int dy = -1; dy <= 1; ++dy)
				for (int dx = -1; dx <= 1; ++dx)
				{
					const vec2 p{ pos.x + dx, pos.y + dy };
					if ((dx == 0 && dy == 0) || !bc::map::is_in_bounds(p) || blocked.is_set(p) || W.walls.is_set(p) || cheb(p, t->pos) <= td)
						continue;
					const int h = W.dist_home(p);
					if (h < bh)
						bh = h, best = p;
				}
			if (!(best == pos) && bh <= h0 + 1)
			{
				bc::bitboard g;
				g.set(best);
				if (step(g, false, false))
					return true;
			}
		}
	}
	const bc::bitboard av = danger | camp_danger | alert_zone;
	g_exit_first = P.flee_exit && avoid;
	const bool moved = after_move(Nav::step_field(pos, W.home, 0, avoid ? &av : nullptr, mob_dash(), can_move, W.ally_spawn));
	g_exit_first = false;
	return moved;
}

void Brain::prebuild_fields()
{
	{
		// Crystal shortcuts: try one untested group per turn while fuel is plentiful. Never on a turn that
		// already ran out of fuel (it continues in a later round: extra work there costs whole rounds), and
		// not in the opening turns, which need their fuel for the first moves.
		auto& W = world();
		if (static_cast<int>(bc::round_number()) != round)
			return;
		if (W.islands_pending && round > init_round && bc::fuel_remaining() >= 90000)
		{
			W.islands_pending = false;
			W.find_islands();
			return;
		}
		if (P.hops_enabled && round >= init_round + 3)
		{
			nav().hop_scan_step(22000, round);
			if (bc::fuel_remaining() >= 50000 && static_cast<int>(bc::round_number()) == round)
				for (const auto& g : W.groups)
					if (!W.hops[static_cast<std::size_t>(g.id)].tried)
					{
						nav().ensure_hop(g.id);
						break;
					}
		}
	}
	// Spend leftover fuel building fields for the nearest groups we have not mapped yet.
	auto& W = world();
	auto& N = nav();
	for (int k = 0; k < 2 && bc::fuel_remaining() > 60000 && static_cast<int>(bc::round_number()) == round; ++k)
	{
		int best = -1, best_d = BIG;
		for (const auto& g : W.groups)
			if (!N.group_fields[static_cast<std::size_t>(g.id)].ready)
			{
				const int d = cheb(g.center, pos);
				if (d < best_d)
					best_d = d, best = g.id;
			}
		if (best < 0 || !N.ensure_group(best))
			return;
	}
}

// ---------------------------------------------------------------------------------------------- actions

void Brain::note_dmg(int gid, float amount)
{
	if (gid >= 0 && gid < static_cast<int>(dmg_on.size()))
		dmg_on[static_cast<std::size_t>(gid)] += amount;
}

bool Brain::attack_unit(const bc::unit& u)
{
	if (!can_attack)
		return false;
	try
	{
		bc::self().attack(u);
		can_attack = false;
		last_act_round = round;
		if (kit.ranged)
			can_move = false;
		return true;
	}
	catch (...)
	{
		return false;
	}
}

bool Brain::cast_unit_camp(int slot, const bc::camp& c)
{
	if (!ready(slot))
		return false;
	try
	{
		if (ab[static_cast<std::size_t>(slot)].use(c))
		{
			cast_done = true;
			cd[static_cast<std::size_t>(slot)] = 8;
			return true;
		}
	}
	catch (...)
	{
	}
	return false;
}

bool Brain::cast_unit_champ(int slot, const bc::champion& c)
{
	if (!ready(slot) || (fe_no_cc && slot == kit.cc))
		return false;
	try
	{
		if (ab[static_cast<std::size_t>(slot)].use(c))
		{
			cast_done = true;
			cd[static_cast<std::size_t>(slot)] = 8;
			return true;
		}
	}
	catch (...)
	{
	}
	return false;
}

bool Brain::strike_dash_at(const Enemy& e)
{
	// P.hor_strike (session 14): Heart of Ruin's dash lands for focus x dash_mod and stuns every enemy within dash_radius of the landing tile.
	if (kit.dash < 0 || kit.dash_mod <= 0.f || !ready(kit.dash) || !can_cast || !e.alive || !e.visible)
		return false;
	auto& W = world();
	const int rng = std::max(1, static_cast<int>(kit.dash_range));
	const int rad = std::max(0, static_cast<int>(kit.dash_radius));
	if (cheb(pos, e.pos) > rng + rad || W.enemy_spawn.is_set(e.pos))
		return false;
	const bc::bitboard blocked = Nav::blocked_now(pos);
	vec2 best = pos;
	int best_n = 0, best_d = 99;
	for (int dy = -rng; dy <= rng; ++dy)
		for (int dx = -rng; dx <= rng; ++dx)
		{
			const vec2 p{ pos.x + dx, pos.y + dy };
			if ((dx == 0 && dy == 0) || !bc::map::is_in_bounds(p) || blocked.is_set(p) || cheb(p, e.pos) > rad || wakes_sleeper(p, rad))
				continue;
			if (std::abs(dx) == 2 || std::abs(dy) == 2)
			{
				const vec2 mid{ pos.x + dx / 2, pos.y + dy / 2 };
				if (bc::map::walls().is_set(mid))
					continue;
			}
			int n = 0, ex = 0;
			for (const auto& o : W.enemies)
				if (o.alive && o.visible)
				{
					if (cheb(p, o.pos) <= rad)
						++n;
					else if (P.hor_strike >= 2 && cheb(p, o.pos) <= std::max(1, o.kit.attack_range))
						++ex; // an enemy the dash does not stun can hit the landing tile
				}
			const int dd = cheb(p, e.pos) + 4 * ex;
			if (n > best_n || (n == best_n && dd < best_d))
				best_n = n, best_d = dd, best = p;
		}
	if (best == pos)
		return false;
	try
	{
		const auto ab = bc::self().abilities()[static_cast<std::size_t>(kit.dash)];
		if (ab.use(best))
		{
#ifdef HOR_TRACE
			debug_block({ std::printf("HORSTRIKE r=%d from=(%d,%d) to=(%d,%d) tgt=(%d,%d) hit=%d\n", round, pos.x, pos.y, best.x, best.y, e.pos.x, e.pos.y, best_n); });
#endif
			cast_done = true;
			after_move(true);
			return true;
		}
	}
	catch (...)
	{
	}
	return false;
}

bool Brain::cast_ground(int slot, vec2 p)
{
	if (!ready(slot))
		return false;
	if (slot == kit.aoe && wakes_sleeper(p, static_cast<int>(kit.aoe_radius)))
		return false;
	try
	{
		if (ab[static_cast<std::size_t>(slot)].use(p))
		{
			cast_done = true;
			cd[static_cast<std::size_t>(slot)] = 8;
			return true;
		}
	}
	catch (...)
	{
	}
	return false;
}

bool Brain::cast_self(int slot)
{
	if (!ready(slot))
		return false;
	try
	{
		if (ab[static_cast<std::size_t>(slot)].use())
		{
			cast_done = true;
			cd[static_cast<std::size_t>(slot)] = 8;
			if (slot == kit.reset)
				can_attack = true;
			return true;
		}
	}
	catch (...)
	{
	}
	return false;
}

bool Brain::cast_area_stun_at(const Enemy& e)
{
	// Aim at a tile within cast range and within the radius of the target (reach = range + radius); prefer
	// the aim that also catches more enemies (Marcella cannot be stunned), then the target's own tile.
	if (kit.aoe < 0 || !ready(kit.aoe))
		return false;
	const int range = static_cast<int>(kit.aoe_range), rad = static_cast<int>(kit.aoe_radius);
	if (cheb(pos, e.pos) > range + rad)
		return false;
	const auto& W = world();
	vec2 best{ -1, -1 };
	int best_n = 0;
	for (int dy = -rad; dy <= rad; ++dy)
		for (int dx = -rad; dx <= rad; ++dx)
		{
			const vec2 c{ e.pos.x + dx, e.pos.y + dy };
			if (cheb(pos, c) > range || !bc::map::is_in_bounds(c) || wakes_sleeper(c, rad))
				continue;
			int n = 0;
			for (const auto& o : W.enemies)
				n += o.alive && o.visible && (!kit.aoe_stuns || o.type != CT::marcella) && cheb(o.pos, c) <= rad;
			if (n > best_n || (n == best_n && dx == 0 && dy == 0))
				best_n = n, best = c;
		}
	return best_n > 0 && cast_ground(kit.aoe, best);
}

int Brain::cast_area_n(const Enemy& e) const
{
	// Most visible enemies one area cast catching e can hit (0 when out of reach).
	if (kit.aoe < 0)
		return 0;
	const int range = static_cast<int>(kit.aoe_range), rad = static_cast<int>(kit.aoe_radius);
	if (cheb(pos, e.pos) > range + rad)
		return 0;
	int best_n = 0;
	for (int dy = -rad; dy <= rad; ++dy)
		for (int dx = -rad; dx <= rad; ++dx)
		{
			const vec2 c{ e.pos.x + dx, e.pos.y + dy };
			if (cheb(pos, c) > range || !bc::map::is_in_bounds(c))
				continue;
			int n = 0;
			for (const auto& o : world().enemies)
				n += o.alive && o.visible && cheb(o.pos, c) <= rad;
			best_n = std::max(best_n, n);
		}
	return best_n;
}

float Brain::camp_dps() const
{
	float base = str * (1.f + (kit.reset >= 0 ? 0.125f : 0.f));
	float spells = 0;
	if (kit.dmg >= 0)
		spells += focus * kit.dmg_mod;
	if (kit.cc >= 0)
		spells += focus * kit.cc_mod;
	if (kit.aoe >= 0)
		spells += focus * kit.aoe_mod;
	return base + spells / 8.f;
}

float Brain::burst_vs(const Enemy& e) const
{
	(void)e;
	float b = can_attack ? str : 0.f;
	float extra = 0;
	if (ready(kit.reset))
		extra = std::max(extra, str);
	if (ready(kit.dmg))
		extra = std::max(extra, focus * kit.dmg_mod);
	if (ready(kit.cc))
		extra = std::max(extra, focus * kit.cc_mod);
	if (ready(kit.aoe))
		extra = std::max(extra, focus * kit.aoe_mod);
	if (ready(kit.dash) && kit.dash_mod > 0)
		extra = std::max(extra, focus * kit.dash_mod); // Heart of Ruin's landing hit
	if (P.g22_exact && e.visible && e.ch)
	{
		// v22 g22_exact: the engine's own prediction of the health this target loses to each ready spell (items, passives, its
		// mitigation and shield included, capped at its health) instead of focus x modifier; Heart of Ruin's missing-health bonus on
		// the basic attack (up to +50%).
		float ex = ready(kit.reset) ? str : 0.f;
		for (int slot : { kit.dmg, kit.cc, kit.aoe, kit.dash })
			if (slot >= 0 && ready(slot) && (slot != kit.dash || kit.dash_mod > 0))
				try
				{
					ex = std::max(ex, ab[static_cast<std::size_t>(slot)].damage_amount(*e.ch));
				}
				catch (...)
				{
				}
		if (type == CT_HOR)
			b *= 1.f + 0.5f * (1.f - hp / std::max(1.f, max_hp));
		return b + ex;
	}
	return b + extra;
}

void Brain::support_spells()
{
	auto& W = world();
	if (kit.heal >= 0 && ready(kit.heal))
	{
		const Ally* best = nullptr;
		float best_missing = focus * kit.heal_mod * 0.6f;
		for (const auto& a : W.allies)
			if (a.handle != self && a.alive && a.visible && cheb(a.pos, pos) <= static_cast<int>(kit.heal_range))
			{
				const float missing = a.max_hp - a.hp;
				if (missing > best_missing)
					best_missing = missing, best = &a;
			}
		if (best)
			cast_unit_champ(kit.heal, best->ch);
	}
	shield_deferred = false;
	if (kit.shield >= 0 && ready(kit.shield) && hp < 0.9f * max_hp && (in_awake_camp_range() || enemies_within(4) > 0))
	{
		// v8 (hor_strike 2): Heart of Ruin's shield and strike dash share the turn's one cast. Casting the shield here, before combat(),
		// took the strike away on the turns an enemy stood in dash reach. Healthy with the dash ready: the shield waits (end of turn).
		if (P.hor_strike >= 2 && kit.dash_mod > 0.f && ready(kit.dash) && hp >= P.hor_shield_hp * max_hp &&
			enemies_within(static_cast<int>(kit.dash_range + kit.dash_radius)) > 0)
			shield_deferred = true;
		else
			cast_self(kit.shield);
	}
}

// GOD v15 g15_calm: which visible enemies are a threat this turn. The ladder teams farm with an enemy within 8 in 15-19% of rounds,
// v14 in 4-8%: any enemy in sight stopped our farming (flee steps, chase steps, burst retreats), and 233 of our 260 back-and-forth walks
// in the user's 20 games had an enemy within 8. A threat is an enemy that can hit us next turn (its reach + 1 step), one that closed in
// on us since our last turn (within 8), or one that just appeared close (g15_new_r).
void Brain::g15_threats()
{
	auto& W = world();
	g15_nthreat = 0;
	for (std::size_t k = 0; k < W.enemies.size() && k < g15_threat.size(); ++k)
	{
		const auto& e = W.enemies[k];
		g15_threat[k] = 0;
		if (!e.alive || !e.visible)
			continue;
		const int d = cheb(e.pos, pos);
		int reach = e.kit.attack_range + (e.kit.ranged ? 0 : 1) + (e.ready(e.kit.dash) ? 2 : 0);
		reach = std::max(reach, enemy_spell_reach(e, false));
		bool t = d <= reach + 1;
		if (!t && d <= 8)
		{
			if (g15_eround[k] >= round - 2)
				t = cheb(e.pos, pos) < cheb(g15_epos[k], pos); // it moved toward where we stand now
			else
				t = d <= P.g15_new_r; // just appeared close
		}
		if (W.enemy_spawn.is_set(e.pos) && d > reach)
			t = false; // healing on its spawn
		g15_threat[k] = t ? 1 : 0;
		g15_nthreat += t;
		g15_epos[k] = e.pos, g15_eround[k] = round;
	}
}

bool Brain::g15_is_threat(const Enemy& e) const
{
	const auto& W = world();
	const std::ptrdiff_t k = &e - W.enemies.data();
	if (k < 0 || k >= static_cast<std::ptrdiff_t>(g15_threat.size()) || k >= static_cast<std::ptrdiff_t>(W.enemies.size()))
		return true;
	return g15_threat[static_cast<std::size_t>(k)] != 0;
}

bool Brain::g15_has_lock() const
{
	try
	{
		return bc::self().consumables()[bc::consumable_type::altar_lock].count() > 0;
	}
	catch (...)
	{
	}
	return false;
}

bool Brain::g15_place_lock(vec2 altar)
{
	if (cheb(altar, pos) > 2 || g15_lock_round == round)
		return false;
	try
	{
		if (bc::self().consumables()[bc::consumable_type::altar_lock].use(altar))
		{
			g15_lock_round = round;
			return true;
		}
	}
	catch (...)
	{
	}
	return false;
}

// GOD v15 g15_lock & 4: an enemy tribute an ally posted at its altar (with the rounds it has left) is cancelled by an altar lock placed
// from 2 tiles: a carrier of a lock that gets there in time walks there and places it. A 10-gold item against a bag (the ladder teams
// bank 41 gems a tribute on average, the Prism teams 400), and no fight is needed.
bool Brain::lock_run()
{
	auto& W = world();
	auto& C = comms();
	if (C.alert_kind != AL_OPPORTUNITY || C.t4_deadline <= round || !is_altar_tile(C.alert_pos))
		return false;
	if (hp < P.g15_lock_hp * max_hp || task == T_CAPTURE || reward_here() || static_cast<int>(gems) >= P.g15_lock_maxbag || !g15_has_lock())
		return false;
	int ai = -1;
	for (std::size_t i = 0; i < W.altars.size(); ++i)
		if (W.altars[i] == C.alert_pos)
			ai = static_cast<int>(i);
	if (ai < 0)
		return false;
	const vec2 altar = C.alert_pos;
	if (cheb(pos, altar) <= 2)
	{
		task = T_FIGHT;
		return g15_place_lock(altar);
	}
	const int d = nav().altar_dist(ai, pos, true);
	if (d >= BIG || d > P.g15_lock_r || d - 1 > C.t4_deadline - round)
		return false;
	task = T_FIGHT;
	const bool moved = go_altar(ai); // after_move refreshes pos
	const bool placed = cheb(pos, altar) <= 2 && g15_place_lock(altar);
	return moved || placed;
}

void Brain::use_locks()
{
	auto& W = world();
	auto& me = bc::self();
	std::uint32_t locks = 0;
	try
	{
		locks = me.consumables()[bc::consumable_type::altar_lock].count();
	}
	catch (...)
	{
		return;
	}
	if (locks == 0)
		return;
	for (std::size_t i = 0; i < W.altars.size(); ++i)
	{
		const vec2 a = W.altars[i];
		if (cheb(a, pos) > 2)
			continue;
		bool enemy_tributing = false;
		for (const auto& e : W.enemies)
			if (e.visible && e.alive && e.tributing && cheb(e.pos, a) <= 1)
				enemy_tributing = true;
		// v15 g15_lock & 8: an ally posted a tribute running at this altar (we may not see the tributer: a bush, or out of our sight).
		if ((P.g15_lock & 8) && !enemy_tributing && comms().alert_kind == AL_OPPORTUNITY && comms().alert_pos == a && comms().t4_deadline > round)
			enemy_tributing = true;
		// v9 presets HUNT / DENY: contested altars (about as near their spawn as ours) get a lock too.
		const bool enemy_side = W.dist_away(a) + 2 < W.dist_home(a) || (P.opp_plan && locks_contested && W.contested(static_cast<int>(i)));
		bool has_any_lock = false;
		try
		{
			has_any_lock = bc::vision::has_altar_lock(a);
		}
		catch (...)
		{
		}
		if (enemy_tributing || (enemy_side && !has_any_lock))
		{
			try
			{
				if (me.consumables()[bc::consumable_type::altar_lock].use(a))
					return;
			}
			catch (...)
			{
			}
		}
	}
}

void Brain::place_ward(bool force)
{
	// v23 4.3.3 / 4.8: the warden's ward on the prime group's ward tile is the team's respawn clock: it never moves
	if (P.v23_tol && v23_warden && v23_role_k >= 0 && static_cast<std::size_t>(v23_role_k) < v23_wtile.size() && ward_pos == v23_wtile[static_cast<std::size_t>(v23_role_k)])
		return;
	if (P.g22_ward && !(P.pxs_style && style_now() == 5))
	{
		if (!force && round - ward_round < 10)
			return;
		if (g22_ward(force))
			return;
	}
	if (P.ward_v14 && !(P.pxs_style && style_now() == 5))
	{
		if (!force && round - ward_round < 10)
			return;
		if (v14_ward(force))
			return;
		// ward_v14 2: no bush in reach: v13's forward ward below
	}
	// ward_bush_maps 1: bush warding only on lone-monolith maps (contest): there it adds 7-27 points to the blob opening; elsewhere it
	// lost to the top-team proxies on the official maps (Mite 70.6 vs 82.4, ifish 73.5 vs 79.4) and the ladder confirmed it.
	const int wb = P.pxs_style && style_now() == 5 ? 2 : P.opp_model && ward_bush_now >= 0 ? ward_bush_now : (P.ward_bush_maps == 1 && !world().mono_mode) ? 0 : P.ward_bush; // a plan's ward mode first
	if (!force && round - ward_round < (wb >= 2 ? std::min(10, P.ward_bush_gap) : 10))
		return;
	auto& W = world();
	if (P.ward_plan && (round - ward_round >= 10 || force) && plan_ward(force))
		return;
	vec2 bush{ -1, -1 };
	if (wb)
	{
		// The sneaky-bush ladder team wards a bush tile within 2 every time one exists (1,683 of 1,683 wards; ours 127 of 672, 19%):
		// a ward inside a bush reveals the champions hiding in it, one outside does not (ENGINE_FACTS). 48% of our champion-caused
		// deaths in their 17 games had a hitter standing in a bush (docs/strategy_v2/10_SNEAKY_BUSH.md). Pick the bush tile nearest
		// the closest recently seen enemy, else nearest their spawn.
		const auto& B = bc::map::bushes();
		vec2 ref = W.enemy_spawn_c;
		int rd = BIG;
		for (const auto& e : W.enemies)
			if (e.alive && e.seen_round >= round - 20 && cheb(e.pos, pos) <= 12 && cheb(e.pos, pos) < rd)
				rd = cheb(e.pos, pos), ref = e.pos;
		int bd = BIG;
		for (int dy = -2; dy <= 2; ++dy)
			for (int dx = -2; dx <= 2; ++dx)
			{
				const vec2 c = pos + vec2{ dx, dy };
				if (!bc::map::is_in_bounds(c) || !B.is_set(c) || W.walls.is_set(c) || W.camp_occ.is_set(c))
					continue;
				const int d = cheb(c, ref);
				if (d < bd)
					bd = d, bush = c;
			}
	}
	// ward_bush 2: re-ward early when a bush is in reach and our ward is not in it; otherwise the usual 10-round rhythm.
	if (!force && round - ward_round < 10 && !(wb >= 2 && bush.x >= 0 && !(bush == ward_pos)))
		return;
	if (bush.x >= 0)
	{
		try
		{
			if (bc::self().place_ward(bush))
			{
				ward_round = round;
				ward_pos = bush;
				return;
			}
		}
		catch (...)
		{
		}
	}
	const vec2 dir = sgn_step(pos, W.enemy_spawn_c);
	const vec2 cands[] = { pos + dir * 2, pos + dir, pos + vec2{ dir.x * 2, dir.y }, pos + vec2{ dir.x, dir.y * 2 } };
	for (auto c : cands)
	{
		if (!bc::map::is_in_bounds(c) || W.walls.is_set(c) || W.camp_occ.is_set(c))
			continue;
		try
		{
			if (bc::self().place_ward(c))
			{
				ward_round = round;
				ward_pos = c;
				return;
			}
		}
		catch (...)
		{
		}
	}
	ward_round = round; // do not retry every turn
}

bool Brain::ally_committed(const Ally& a) const
{
	// v22 g22_msg: bit 0 of a visible ally's next-round priority = committed to a fight (written by the priority setter).
	if (!a.visible || !a.alive)
		return false;
	try
	{
		return (a.ch.priority() & 1) != 0;
	}
	catch (...)
	{
		return false;
	}
}

bool Brain::g22_ward(bool force)
{
	// v22 (the user: "place wards strategically and near grass, for maximum coverage"). The engine gives the legal tiles
	// (ward_placement_tiles) and the exact vision of a ward on each (ward::visible_tiles_from); a ward is worth what it reveals that this
	// body does not already see from where it stands: bush tiles count extra (only a ward inside or next to a bush sees into it), and so
	// do the tiles around our target group, the altar we bank at and the last enemy we saw. Corridor tiles are skipped (a ward occupies
	// its tile and blocks our own walk).
	if (bc::fuel_remaining() < 30000)
		return true; // late in a heavy turn: the next turn looks again
	auto& W = world();
	static const bc::bitboard bush = bc::map::bushes(); // static map data
	static constexpr std::array<vec2, 8> D8{ vec2::north, vec2::north_east, vec2::east, vec2::south_east, vec2::south, vec2::south_west, vec2::west, vec2::north_west };
	try
	{
		const bc::bitboard legal = bc::self().ward_placement_tiles();
		const bc::bitboard base = bc::self().visible_tiles_from(pos);
		const bc::bitboard unseen = ~base;
		bc::bitboard imp;
		const Group* tg = task_group >= 0 && task_group < static_cast<int>(W.groups.size()) ? &W.groups[static_cast<std::size_t>(task_group)] : nullptr;
		if (tg)
			imp.draw_chebyshev(tg->center, static_cast<float>(tg->radius + 6));
		int adist = BIG;
		const int a = gems >= 20 || task == T_TRIBUTE ? nearest_altar(adist) : -1;
		if (a >= 0 && adist < BIG)
			imp.draw_chebyshev(W.altars[static_cast<std::size_t>(a)], 6.f);
		int sd = BIG;
		vec2 seen{ -1, -1 };
		for (const auto& e : W.enemies)
			if (e.alive && e.seen_round >= round - 30 && cheb(e.pos, pos) <= 14 && cheb(e.pos, pos) < sd)
				sd = cheb(e.pos, pos), seen = e.pos;
		if (seen.x >= 0)
			imp.draw_chebyshev(seen, 4.f);
		const bc::bitboard bush_unseen = bush & unseen;
		const bc::bitboard imp_unseen = imp & unseen;
		auto score = [&](vec2 c) -> float {
			const bc::bitboard v = bc::ward::visible_tiles_from(c);
			float s = static_cast<float>((v & unseen).count()) + (P.g22_ward_bush - 1.f) * static_cast<float>((v & bush_unseen).count()) +
				(P.g22_ward_imp - 1.f) * static_cast<float>((v & imp_unseen).count());
			if (bush.is_set(c))
				s += P.g22_ward_grass;
			else
				for (auto d : D8)
					if (bc::map::is_in_bounds(c + d) && bush.is_set(c + d))
					{
						s += 0.4f * P.g22_ward_grass;
						break;
					}
			return s;
		};
		vec2 best{ -1, -1 };
		float bs = 0.f;
		for (vec2 c : legal.positions())
		{
			if (bc::fuel_remaining() < 25000)
				break;
			if (W.walls.is_set(c) || W.camp_occ.is_set(c) || c == ward_pos || c == pos)
				continue;
			int open = 0;
			for (auto d : D8)
				open += bc::map::is_in_bounds(c + d) && !W.walls.is_set(c + d);
			if (open < 5)
				continue; // a corridor tile: our ward there would block our own team's walk
			const float s = score(c);
			if (s > bs)
				bs = s, best = c;
		}
		if (best.x < 0)
			return false;
		// The standing ward keeps watching while it is near and nearly as good.
		if (!force && ward_pos.x >= 0 && cheb(ward_pos, pos) <= P.ward_hold && bc::fuel_remaining() > 25000 && score(ward_pos) * 1.5f >= bs)
		{
			ward_round = round - 5; // look again in 5 rounds
			return true;
		}
		if (bc::self().place_ward(best))
		{
			ward_round = round;
			ward_pos = best;
			return true;
		}
	}
	catch (...)
	{
	}
	return false;
}

bool Brain::v14_ward(bool force)
{
	// v14 (P.ward_v14; the user: "wards are thrown at random tiles: throw them into the bushes and use them well"). A ward inside a
	// bush reveals whoever hides in it (ENGINE_FACTS); outside it adds little to a body's own sight 2 tiles further on. The 600 ladder
	// replays' teams place 150 wards a game, 61-65% on a bush and 84-86% of them on one when a bush is in reach; v13 placed 518, 6%.
	if (bc::fuel_remaining() < 20000)
		return true; // late in a heavy turn: the next turn looks again
	auto& W = world();
	static const bc::bitboard bush = bc::map::bushes(); // static map data
	const Group* tg = task_group >= 0 && task_group < static_cast<int>(W.groups.size()) ? &W.groups[static_cast<std::size_t>(task_group)] : nullptr;
	int adist = BIG;
	const int a = gems >= 20 || task == T_TRIBUTE ? nearest_altar(adist) : -1;
	vec2 seen{ -1, -1 };
	int sd = BIG;
	for (const auto& e : W.enemies)
		if (e.alive && e.seen_round >= round - 30 && cheb(e.pos, pos) <= 14 && cheb(e.pos, pos) < sd)
			sd = cheb(e.pos, pos), seen = e.pos;
	const int away_here = W.dist_away(pos);
	// What a ward at t watches that matters to this body: its target group, the altar it banks at, the side the enemy was last seen or
	// comes from (the walk toward their spawn).
	auto score = [&](vec2 t) -> float {
		float s = 10.f;
		if (tg && cheb(t, tg->center) <= tg->radius + 6)
			s += 20.f;
		if (a >= 0 && adist < BIG && cheb(t, W.altars[static_cast<std::size_t>(a)]) <= 6)
			s += 15.f;
		if (seen.x >= 0 && cheb(t, seen) < cheb(pos, seen))
			s += 15.f;
		const int at = W.dist_away(t);
		if (away_here < BIG && at < away_here)
			s += 4.f * static_cast<float>(std::min(3, away_here - at));
		return s;
	};
	const bool have = ward_pos.x >= 0;
	const int cur_d = have ? cheb(ward_pos, pos) : BIG;
	const bool cur_bush = have && bush.is_set(ward_pos);
	vec2 best{ -1, -1 };
	float bs = 0.f;
	for (int dy = -2; dy <= 2; ++dy)
		for (int dx = -2; dx <= 2; ++dx)
		{
			const vec2 c = pos + vec2{ dx, dy };
			if (!bc::map::is_in_bounds(c) || !bush.is_set(c) || W.walls.is_set(c) || W.camp_occ.is_set(c) || c == ward_pos)
				continue;
			if (P.ward_open > 0)
			{
				int open = 0;
				for (int ey = -1; ey <= 1; ++ey)
					for (int ex = -1; ex <= 1; ++ex)
					{
						const vec2 q = c + vec2{ ex, ey };
						open += (ex || ey) && bc::map::is_in_bounds(q) && !W.walls.is_set(q); // walls: walls, holes, altars, their spawn
					}
				if (open < P.ward_open)
					continue; // a corridor tile: our ward there would block our own team's walk
			}
			const float s = score(c);
			if (s > bs)
				bs = s, best = c;
		}
	auto put = [&](vec2 c) -> bool {
		try
		{
			if (bc::self().place_ward(c))
			{
				ward_round = round;
				ward_pos = c;
				return true;
			}
		}
		catch (...)
		{
		}
		return false;
	};
	if (best.x >= 0)
	{
		// A ward already in a bush near us keeps its watch unless this bush matters clearly more.
		if (cur_bush && cur_d <= P.ward_hold && bs < 1.5f * score(ward_pos))
		{
			ward_round = round - 5; // look again in 5 rounds
			return true;
		}
		if (put(best))
			return true;
	}
	if (P.ward_v14 >= 2)
	{
		// 2: a ward in a bush near us keeps watching; otherwise v13's forward ward (early warning toward their side).
		if (cur_bush && cur_d <= P.ward_hold && !force)
		{
			ward_round = round - 5;
			return true;
		}
		return false;
	}
	// No bush in reach: the standing ward keeps watching while it is near us; no new throw.
	if (have && cur_d <= P.ward_hold && !force)
	{
		ward_round = round - 5;
		return true;
	}
	// Far from our ward (or none yet): a scouting ward ahead of us on the walk toward their spawn (never through a wall).
	vec2 sc{ -1, -1 };
	int sa = away_here;
	for (int dy = -2; dy <= 2; ++dy)
		for (int dx = -2; dx <= 2; ++dx)
		{
			const vec2 c = pos + vec2{ dx, dy };
			if (!bc::map::is_in_bounds(c) || W.walls.is_set(c) || W.camp_occ.is_set(c) || c == ward_pos)
				continue;
			const int at = W.dist_away(c);
			if (at < sa)
				sa = at, sc = c;
		}
	if (sc.x >= 0 && put(sc))
		return true;
	ward_round = round - 5;
	return true;
}

bool Brain::plan_ward(bool force)
{
	// F3: a planned spot (draft memory) within placement reach (2) that watches what this body works on, not covered by an ally ward.
	(void)force;
	auto& W = world();
	const auto& dp = draft_plan();
	if (!dp.ok || dp.wards.empty())
		return false;
	std::array<vec2, 3> anchors{};
	int na = 0;
	if (task_group >= 0 && task_group < static_cast<int>(W.groups.size()))
		anchors[static_cast<std::size_t>(na++)] = W.groups[static_cast<std::size_t>(task_group)].center;
	if (task == T_CAPTURE)
		anchors[static_cast<std::size_t>(na++)] = pos;
	const bool tributing = flag(state, bc::champion_state::submitting_gems);
	if (tributing || task == T_TRIBUTE)
		for (const auto& a : W.altars)
			if (cheb(a, pos) <= 3 && na < 3)
			{
				anchors[static_cast<std::size_t>(na++)] = a;
				break;
			}
	if (na == 0)
		return false;
	// Two of us on one group: the lower index wards the enemy-facing approach, the higher the bush.
	const auto& C = comms();
	int partner = -1;
	for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 6; ++i)
	{
		const auto& a = W.allies[static_cast<std::size_t>(i)];
		if (i != W.my_index && a.alive && a.visible && task_group >= 0 && C.claim[static_cast<std::size_t>(i)] == task_group && cheb(a.pos, pos) <= 6)
			partner = i;
	}
	const bool still = task == T_CAPTURE || tributing || (task == T_FARM && task_group >= 0 && W.groups[static_cast<std::size_t>(task_group)].near.is_set(pos));
	bool bush_first = (P.opp_model && plan_now == PLAN_AMBUSH) || still || W.mono_mode || W.obj_mode;
	if (partner >= 0)
		bush_first = W.my_index > partner;
	const bc::bitboard ally_w = bc::vision::ward_tiles(team::ally);
	int best = -1;
	float bs = -1e9f;
	for (int k = 0; k < static_cast<int>(dp.wards.size()); ++k)
	{
		const auto& s = dp.wards[static_cast<std::size_t>(k)];
		if (cheb(s.p, pos) > 2 || s.p == ward_pos || W.walls.is_set(s.p) || W.camp_occ.is_set(s.p))
			continue;
		int ad = BIG;
		for (int j = 0; j < na; ++j)
			ad = std::min(ad, cheb(s.p, anchors[static_cast<std::size_t>(j)]));
		if (ad > 4)
			continue;
		bc::bitboard around;
		around.draw_chebyshev(s.p, 3.f);
		if (!(around & ally_w).is_empty())
			continue; // already watched by one of ours
		const bool bush = s.kind == DMW_BUSH_GROUP || s.kind == DMW_BUSH_ALTAR;
		const float sc = (bush == bush_first ? 2.f : 0.f) + (s.slot == my_slot ? 1.f : 0.f) - 0.25f * static_cast<float>(ad) - 0.05f * static_cast<float>(k);
		if (sc > bs)
			bs = sc, best = k;
	}
	if (best < 0)
		return false;
	const vec2 t = dp.wards[static_cast<std::size_t>(best)].p;
	try
	{
		if (bc::self().place_ward(t))
		{
			ward_round = round;
			ward_pos = t;
			return true;
		}
	}
	catch (...)
	{
	}
	return false;
}

void Brain::enemy_wards_update()
{
	// F3: one active ward per enemy champion, so a ward seen at a new tile replaces its owner's old one.
	try
	{
		auto& W = world();
		for (const auto& wd : bc::vision::wards(team::enemy))
		{
			const std::uint32_t h = ward_owner(wd);
			const vec2 p = wd.position();
			int idx = -1;
			for (int i = 0; i < static_cast<int>(W.enemies.size()) && i < 8; ++i)
				if (h != 0 && W.enemies[static_cast<std::size_t>(i)].handle == h)
					idx = i;
			if (idx >= 0)
				ew_pos[static_cast<std::size_t>(idx)] = p, ew_round[static_cast<std::size_t>(idx)] = round;
			else
			{
				bool found = false;
				for (auto& t : ew_tiles)
					if (t.first == p)
						t.second = round, found = true;
				if (!found && ew_tiles.size() < 12)
					ew_tiles.push_back({ p, round });
			}
		}
	}
	catch (...)
	{
	}
}

bool Brain::near_enemy_ward(vec2 p, int r) const
{
	for (std::size_t i = 0; i < ew_pos.size(); ++i)
		if (ew_round[i] > 0 && cheb(ew_pos[i], p) <= r)
			return true;
	for (const auto& t : ew_tiles)
		if (round - t.second <= 200 && cheb(t.first, p) <= r)
			return true;
	return false;
}

// ---------------------------------------------------------------------------------------------- champion combat

bool Brain::wins_with(int bag) const
{
	// P.team_bank: the bags the rest of the team carries count too (shared sum, in tens, rounded down): when the
	// team's bags finish the game every carrier banks now. 12 of 77 losses of _ST vs _L0/_r2/_v6/_es2 ended with
	// banked + carried >= 1000 (gen02 968 banked + 88 carried, gen19 990 + 48, gen13 982 + 44, ...).
	return static_cast<int>(bc::global_submitted_gems(team::ally)) + bag + (P.team_bank ? comms().others_carried() : 0) >=
		static_cast<int>(bc::constants::winning_gems);
}

bool Brain::can_support(const Ally& a, const std::vector<Enemy*>& E) const
{
	if (a.hp < P.retreat_hp * a.max_hp)
		return false; // it is walking home, not fighting
	if (P.support_v2 && a.channeling)
		return false; // A3: recalling or banking: it cannot hit anyone (and a hit cancels its recall)
	for (const auto* e : E)
		if (cheb(a.pos, e->pos) <= P.support_reach)
			return true;
	return false;
}

// ml2 (agent ml2, session 13): the features of tools/ml/ml2_dataset.py, computed from what this body sees, in the same
// order and units (the logistic weights in ml2_model.h are on these raw values). Cost: loops over <= 10 bodies and the
// camp groups near us (no distance fields), a few hundred fuel.
void Brain::ml2_features(float* f) const
{
	auto& W = world();
	for (int i = 0; i < ML2_NF; ++i)
		f[i] = 0.f;
	auto spell_up = [](const Kit& k, const std::array<int, 2>& c, int slot) { return slot >= 0 && c[static_cast<std::size_t>(slot)] <= 0; };
	// self
	float burst = 0;
	const bool s_dmg = spell_up(kit, cd, kit.dmg), s_cc = spell_up(kit, cd, kit.cc), s_aoe = spell_up(kit, cd, kit.aoe);
	if (s_dmg) burst = std::max(burst, focus * kit.dmg_mod);
	if (s_cc) burst = std::max(burst, focus * kit.cc_mod);
	if (s_aoe) burst = std::max(burst, focus * kit.aoe_mod);
	if (spell_up(kit, cd, kit.reset)) burst = std::max(burst, str);
	const bool my_spell = s_dmg || s_cc || s_aoe;
	const bool my_dash = spell_up(kit, cd, kit.dash);
	f[0] = hp / std::max(1.f, max_hp);
	f[1] = hp / 1000.f;
	f[2] = max_hp / 1000.f;
	f[3] = str / 100.f;
	f[4] = focus / 100.f;
	f[5] = (str + focus * best_mod(kit) / 8.f + burst / 3.f) / 100.f;
	f[6] = burst / 100.f;
	f[7] = kit.ranged ? 1.f : 0.f;
	f[8] = (type == CT::cassi || type == CT::issac) ? 1.f : 0.f;
	f[9] = static_cast<float>(gems) / 100.f;
	f[10] = my_spell ? 1.f : 0.f;
	f[11] = my_dash ? 1.f : 0.f;
	const int dh = std::min(W.dist_home(pos), 200), da = std::min(W.dist_away(pos), 200);
	f[12] = static_cast<float>(std::min(dh, 60)) / 30.f;
	const bool on_spawn = W.ally_spawn.is_set(pos);
	f[13] = on_spawn ? 1.f : 0.f;
	f[14] = da < dh - 3 ? 1.f : 0.f;
	f[15] = std::abs(da - dh) <= 3 ? 1.f : 0.f;
	f[16] = static_cast<float>(round) / 1000.f;
	f[17] = bc::map::bushes().is_set(pos) ? 1.f : 0.f;
	f[19] = type == CT::ren ? 1.f : 0.f;
	f[20] = type == CT::stellar ? 1.f : 0.f;
	f[21] = type == CT::cassi ? 1.f : 0.f;
	f[22] = type == CT::issac ? 1.f : 0.f;
	f[23] = type == CT::varg ? 1.f : 0.f;
	f[24] = type == CT::ryth ? 1.f : 0.f;
	// enemies: visible, within 8 (own vision)
	const int my_reach = (kit.ranged ? 3 : 2) + (my_dash ? 2 : 0);
	float allies_burst = 0;
	for (const auto& a : W.allies)
		if (a.handle != self && a.alive && a.visible && cheb(a.pos, pos) <= 6)
			allies_burst += a.str;
	int dmin = 10, nearest = -1, e_alive = 0;
	float e_min5 = 3000.f, their_hp = 0, their_dps = 0, incoming = 0;
	bool killable = false, in_reach = false, chaser = false, chaser_dash = false, spawn_near = false;
	for (std::size_t i = 0; i < W.enemies.size(); ++i)
	{
		const auto& e = W.enemies[i];
		if (!e.alive)
			continue;
		++e_alive;
		if (!e.visible)
			continue;
		const int dd = cheb(e.pos, pos);
		if (dd > 8)
			continue;
		const bool e_dmg = e.ready(e.kit.dmg), e_cc = e.ready(e.kit.cc), e_aoe = e.ready(e.kit.aoe);
		const bool e_spell = e_dmg || e_cc || e_aoe;
		const bool e_dash = e.ready(e.kit.dash);
		const bool e_stun = e_cc || (e_aoe && e.kit.aoe_stuns);
		const float eb = e.burst();
		const float edps = e.str + e.focus * best_mod(e.kit) / 8.f + eb / 3.f;
		if (dd <= 3)
		{
			f[25] += 1.f;
			if (!e.kit.ranged || e_dash)
				f[39] += 1.f;
		}
		if (dd <= 5)
		{
			f[26] += 1.f;
			f[28] += e.hp / 1000.f;
			f[30] += edps / 100.f;
			if (e_spell)
				f[32] += eb / 100.f;
			if (e_stun)
				f[33] += 1.f;
			if (e_aoe)
				f[34] += 1.f;
			e_min5 = std::min(e_min5, e.hp);
		}
		if (dd <= 7)
		{
			f[27] += 1.f;
			f[29] += e.hp / 1000.f;
			f[31] += edps / 100.f;
			if (W.enemy_spawn.is_set(e.pos))
				spawn_near = true;
		}
		if (dd < dmin)
			dmin = dd, nearest = static_cast<int>(i);
		if (dd <= std::max(my_reach, my_spell ? 4 : 0) && e.hp <= str + burst + allies_burst)
			killable = true;
		if (dd <= 2 && e.type == CT::varg)
			f[40] += 1.f;
		if (dd <= 4 && e.type == CT::ren)
			f[41] += 1.f;
		// the estimate (not counting enemies on their own spawn)
		if (W.enemy_spawn.is_set(e.pos))
			continue;
		int reach = (e.kit.ranged ? 3 : 2) + (e_dash ? 2 : 0);
		if (e_spell)
			reach = std::max(reach, 4);
		their_hp += e.hp;
		their_dps += edps * (e_stun ? 1.15f : 1.f);
		if (dd <= reach)
			incoming += e.str + eb / 2.f, in_reach = true;
		if ((!e.kit.ranged || e_dash) && dd <= 3 + (e_dash ? 2 : 0))
			chaser = true, chaser_dash |= e_dash;
	}
	f[35] = static_cast<float>(dmin) / 10.f;
	f[36] = nearest >= 0 ? W.enemies[static_cast<std::size_t>(nearest)].hp / std::max(1.f, W.enemies[static_cast<std::size_t>(nearest)].max_hp) : 1.f;
	f[37] = e_min5 / 1000.f;
	f[38] = killable ? 1.f : 0.f;
	f[42] = static_cast<float>(e_alive);
	f[43] = spawn_near ? 1.f : 0.f;
	// allies (visible; self counted in a_alive)
	float our_hp = hp, our_dps = str + focus * best_mod(kit) / 8.f + burst / 3.f;
	int a_alive = 0;
	bool ally5 = false;
	for (const auto& a : W.allies)
	{
		if (!a.alive)
			continue;
		++a_alive;
		if (a.handle == self || !a.visible || !a.kit_ready)
			continue;
		const int dd = cheb(a.pos, pos);
		const float bm = best_mod(a.kit);
		const float adps = a.str + a.focus * bm / 8.f + std::max(a.str, a.focus * bm) / 3.f;
		if (dd <= 3)
			f[44] += 1.f;
		if (dd <= 5)
		{
			f[45] += 1.f;
			f[47] += a.hp / 1000.f;
			if (a.hp < 0.3f * a.max_hp)
				f[51] += 1.f;
			ally5 = true;
		}
		if (dd <= 7)
		{
			f[46] += 1.f;
			f[48] += a.hp / 1000.f;
		}
		if (dd <= 6)
		{
			f[49] += adps / 100.f;
			if (a.hp > 0.25f * a.max_hp)
			{
				bool near_e = false;
				for (const auto& e : W.enemies)
					near_e |= e.alive && e.visible && cheb(e.pos, pos) <= 8 && cheb(a.pos, e.pos) <= 6;
				if (near_e)
					our_hp += a.hp, our_dps += adps;
			}
		}
	}
	f[50] = static_cast<float>(a_alive);
	// awake camps within 3 (damaged, alive)
	int ca = 0;
	for (const auto& g : W.groups)
	{
		if (g.st != ST_ALIVE || cheb(g.center, pos) > 3 + g.radius)
			continue;
		for (std::size_t i = 0; i < g.camps.size() && i < g.hp.size(); ++i)
			if (g.hp[i] > 0 && g.hp[i] < g.camps[i].max_hp && cheb(g.camps[i].pos, pos) <= 3)
				++ca;
	}
	f[52] = static_cast<float>(ca);
	if (on_spawn && in_reach)
		our_hp += max_hp;
	float adv = 10.f;
	if (their_dps > 0 && their_hp > 0)
		adv = (our_hp / std::max(1.f, their_dps)) / std::max(0.1f, their_hp / std::max(1.f, our_dps));
	f[53] = std::log(std::max(0.01f, std::min(100.f, adv)));
	f[54] = in_reach ? 1.f : 0.f;
	f[55] = incoming / 100.f;
	const float t_die = hp / std::max(1.f, incoming);
	f[56] = (on_spawn || !chaser || (my_dash && !chaser_dash) || static_cast<float>(dh) + 1.f < t_die) ? 1.f : 0.f;
	f[57] = ally5 ? 0.f : 1.f;
}

static float ml2_logit(const float* w, float b, const float* f)
{
	float z = b;
	for (int i = 0; i < ML2_NF; ++i)
		z += w[i] * f[i];
	return z;
}

static float ml2_sig(float z)
{
	z = std::max(-30.f, std::min(30.f, z));
	return 1.f / (1.f + std::exp(-z));
}

// Boosted trees (ml2_gb): the 200 trees of tools/ml/ml2_train.py --export-gb; feature index ML2_NF is the our-bot flag (1).
static float ml2_gb_die8(const float* f)
{
	float z = ML2_GB_BASE_DIE8;
	for (int t = 0; t < ML2_GB_TREES_DIE8; ++t)
	{
		int n = ML2_GB_START_DIE8[t];
		while (ML2_GB_FEAT_DIE8[n] >= 0)
		{
			const int k = ML2_GB_FEAT_DIE8[n];
			const float v = k < ML2_NF ? f[k] : 1.f;
			n = v <= ML2_GB_THR_DIE8[n] ? ML2_GB_LEFT_DIE8[n] : ML2_GB_RIGHT_DIE8[n];
		}
		z += ML2_GB_VAL_DIE8[n];
	}
	return z;
}

// ml2_adapt: in-match recalibration of the model's intercept to this opponent. Every evaluation is kept for 8 rounds: the body
// survived them (label 0) or died within them (label 1, set on our first dead turn); one SGD step on the offset per label.
// The model is calibrated on ladder teams; against the local proxies our bodies die about half as often in the same state.
void Brain::ml2_learn(bool died)
{
	const float lr = P.ml2_adapt;
	for (int i = 0; i < ml2_buf_n;)
	{
		const auto k = static_cast<std::size_t>(i);
		if (died || ml2_buf_r[k] + 8 < round)
		{
			const float y = died && ml2_buf_r[k] + 8 >= round ? 1.f : 0.f;
			ml2_off += lr * (y - ml2_sig(ml2_buf_z[k] + ml2_off));
			ml2_off = std::max(P.ml2_adapt_min, std::min(P.ml2_adapt_max, ml2_off));
			const auto last = static_cast<std::size_t>(ml2_buf_n - 1);
			ml2_buf_r[k] = ml2_buf_r[last], ml2_buf_z[k] = ml2_buf_z[last];
			--ml2_buf_n;
		}
		else
			++i;
	}
}

// v28 cap hold: a dead group's reward we stand on or are next to, with nobody of ours on it. Ranked gem_fields vs the ruliad: we killed a 71-gem group at r126; two of our bodies stood on it at
// r130 and r134 and walked off to fight, the reward waited 40 rounds and their team took it. A capture takes 5 rounds, an enemy on a tile resets it, a second capturer only splits it
// and attacks are free from the tile: so one body stays and hits what is in reach, the others fight. Off when an enemy holds a tile (only clearing it helps) or we would die before it lands.
bool Brain::v28_hold(float incoming)
{
	auto& W = world();
	Group* best = nullptr;
	float bv = 0;
	int bd = BIG;
	for (auto& g : W.groups)
	{
		if (g.st != ST_REWARD || g.enemy_on_tile)
			continue;
		const int d = g.mask.is_set(pos) ? 0 : nav().group_dist(g, pos);
		if (d > P.v28_hold_d)
			continue;
		const float v = static_cast<float>(g.gems) + P.gold_value * static_cast<float>(g.gold);
		if (v < P.v28_hold_min)
			continue;
		bool taken = false;
		for (const auto& a : W.allies)
			if (a.handle != self && a.alive && a.visible && a.seen_round == round && g.mask.is_set(a.pos))
				taken = true;
		if (taken)
			continue;
		if (d < bd || (d == bd && v > bv))
			bd = d, bv = v, best = &g;
	}
	if (!best)
		return false;
	Group& g = *best;
	int left = static_cast<int>(bc::constants::capture_time) + 1 + bd;
	if (bd == 0)
	{
		bc::detail::camp_group_capture_state cs{};
		if (bc::detail::sdk_camp_group_capture_state(g.handle, &cs) == 0)
		{
			if (cs.state == 0 || cs.state == 2 || cs.state == 3)
				return false; // the engine has no reward here, or an enemy we do not see contests it: nothing to wait for
			if (cs.state == 1 && cs.timer >= 0)
				left = cs.timer + 1;
		}
	}
	if (incoming * static_cast<float>(left) >= hp)
		return false;
	task_group = g.id;
	task = T_CAPTURE;
	last_hold_round = round;
	if (bd > 0)
		capture_group(g);
	else
	{
		if (capture_group_id != g.id)
			capture_group_id = g.id, capture_since = round;
		task_progress = round;
	}
	if (can_attack || !cast_done)
		if (Enemy* o = best_in_reach(nullptr))
		{
			if (!cast_done && !cast_unit_champ(kit.dmg, *o->ch))
				cast_unit_champ(kit.cc, *o->ch);
			if (can_attack)
				attack_unit(*o->ch);
		}
	return true;
}

bool Brain::combat()
{
	auto& W = world();
	engaged = false;
	// v27: an enemy we hit four turns running without lowering its health (it heals on its spawn, or our burst estimate is wrong) is
	// left alone for 40 rounds unless it hits us (idle-opponent games: a Heart of Ruin hit a body on its spawn for 800 rounds)
	for (std::size_t k = 0; k < W.enemies.size() && k < fut_hp.size(); ++k)
	{
		const auto& e = W.enemies[k];
		if (fut_round[k] != round - 1 || !e.visible)
			continue;
		fut_n[k] = e.hp >= fut_hp[k] - 1.f && (P.v27_futile == 1 || W.enemy_spawn.is_set(e.pos)) ? fut_n[k] + 1 : 0;
		if (fut_n[k] >= 4 && P.v27_futile)
			fut_until[k] = round + 40, fut_n[k] = 0;
	}
	std::vector<Enemy*> E;
	for (auto& e : W.enemies)
		if (e.alive && e.visible && cheb(e.pos, pos) <= 9)
		{
			// An enemy on its own spawn heals fully every round: it cannot be killed (unless one turn of
			// burst does it) and is no reason to stand and trade. Maps with adjacent spawns otherwise lock
			// both teams in a pointless duel for the whole game.
			if (W.enemy_spawn.is_set(e.pos) && e.max_hp > burst_vs(e) + 1.f)
				continue;
			if (static_cast<std::size_t>(&e - W.enemies.data()) < fut_until.size() && fut_until[static_cast<std::size_t>(&e - W.enemies.data())] > round &&
				round - last_hit_round > 1)
				continue;
			E.push_back(&e);
		}
	if (E.empty())
		return false;

	// Enemy reach next turn: attack range (+1 step for melee), +2 with a dash ready, 4 with a spell ready.
	auto reach_of = [](const Enemy& e) {
		int r = e.kit.attack_range + (e.kit.ranged ? 0 : 1) + (e.ready(e.kit.dash) ? 2 : 0);
		if (P.aoe_reach5 && P.aoe_reach5 != 3)
			r = std::max(r, enemy_spell_reach(e, false));
		else if (e.ready(e.kit.dmg) || e.ready(e.kit.cc) || e.ready(e.kit.aoe))
			r = std::max(r, 4);
		return r;
	};
	// Their side: enemies that can hit us within about two turns count fully, the rest of the visible
	// group half (they arrive a turn or two later). Stuns cost us a turn: count ready stuns as damage.
	float their_hp = 0, their_dps = 0, incoming = 0;
	int stunners = 0;
	float lethal = 0; // mi_lethal: the biggest hit a nearby enemy with its spells up has already landed on us
	auto& LB = learner();
	for (auto* e : E)
	{
		const int d = cheb(e->pos, pos);
		const float w = d <= reach_of(*e) + 2 ? 1.f : P.far_enemy_weight;
		float eb = e->burst();
		const std::size_t ei = static_cast<std::size_t>(e - W.enemies.data());
		if ((P.mi_learn_burst || P.mi_lethal) && ei < LB.enemy_burst.size() && (e->ready(e->kit.dmg) || e->ready(e->kit.cc) || e->ready(e->kit.aoe)))
		{
			// Its real burst (items included) replaces the model while its spells are up (default branch).
			if (P.mi_learn_burst)
				eb = std::max(eb, LB.enemy_burst[ei]);
			if (d <= 5)
				lethal = std::max(lethal, LB.enemy_burst[ei]);
		}
		float dps = e->str + e->focus * best_mod(e->kit) / 8.f + eb / 3.f;
		if (e->ready(e->kit.cc) || (e->ready(e->kit.aoe) && e->kit.aoe_stuns))
			++stunners, dps *= 1.15f;
		const float pm = (P.fm_mode & 1) && e->type == CT_HOR ? 1.f + 0.5f * (1.f - e->hp / std::max(1.f, e->max_hp)) : 1.f;
		their_hp += w * (e->hp + ((P.fm_buffs & 1) ? e->shield : 0.f));
		if ((P.fm_buffs & 2) && e->stunned)
			dps *= 0.7f; // a stunned enemy loses the first round of a ~3-round exchange
		their_dps += w * dps * pm;
		if (d <= reach_of(*e) && !((P.fm_buffs & 2) && e->stunned))
			incoming += (e->str + e->burst() / 2.f) * pm;
	}
	if (P.v28_cap_hold && v28_hold(incoming))
		return true;
	// Our side: self plus visible allies within 6 (with their spells, not just basic attacks).
	float my_burst = 0;
	if (ready(kit.dmg)) my_burst = std::max(my_burst, focus * kit.dmg_mod);
	if (ready(kit.cc)) my_burst = std::max(my_burst, focus * kit.cc_mod);
	if (ready(kit.aoe)) my_burst = std::max(my_burst, focus * kit.aoe_mod);
	if (ready(kit.reset)) my_burst = std::max(my_burst, str);
	if (P.fix_my_dash && ready(kit.dash) && kit.dash_mod > 0.f)
		my_burst = std::max(my_burst, focus * kit.dash_mod); // T01: Heart of Ruin's landing is its fight spell (burst_vs counts it; this did not)
	float our_hp = hp + ((P.fm_buffs & 1) ? my_shield : 0.f), our_dps = str + focus * best_mod(kit) / 8.f + my_burst / 3.f;
	if ((P.fm_mode & 1) && type == CT_HOR)
		our_dps *= 1.f + 0.5f * (1.f - hp / std::max(1.f, max_hp)); // Heart of Ruin hits harder the lower it is
	if ((P.fm_mode & 2) && type == CT::ren)
	{
		// Ren returns 0.2 x focus of every hit: each enemy that can hit us this round pays it (B12: counted only against us).
		int hitters = 0;
		for (auto* e : E)
			hitters += cheb(e->pos, pos) <= reach_of(*e);
		our_dps += bc::constants::passive_abilities::ren_retaliation_focus_ratio * focus * static_cast<float>(std::min(hitters, 3));
	}
	float allies_burst = 0;
	int allies_near = 0;
	std::array<vec2, 8> side_pos{};
	int side_n = 0;
	side_pos[static_cast<std::size_t>(side_n++)] = pos;
	// v8 sup_mode: helpers weighted by whether they arrive before we die (the user's rule: support counts as much as it is in time).
	int sup_helpers = 0;
	float sup_hp = 0;
	vec2 help_pos{ -100, -100 };
	int help_arr = BIG;
	if (P.sup_mode & 1)
	{
		const float t_me = hp / std::max(1.f, std::max(incoming, 0.5f * their_dps));
		for (int i = 0; i < static_cast<int>(W.allies.size()); ++i)
		{
			const auto& a = W.allies[static_cast<std::size_t>(i)];
			if (a.handle == self || !a.alive || !a.visible || cheb(a.pos, pos) > P.sup_radius || a.channeling || a.hp < P.retreat_hp * a.max_hp)
				continue;
			int de = BIG;
			for (auto* e : E)
				de = std::min(de, cheb(a.pos, e->pos));
			if (i < 8 && ally_prev_round[static_cast<std::size_t>(i)] == round - 1)
			{
				int dp = BIG;
				for (auto* e : E)
					dp = std::min(dp, cheb(ally_prev_pos[static_cast<std::size_t>(i)], e->pos));
				if (de > dp && de >= 3 && !(P.g22_msg && ally_committed(a)))
					continue; // walking away from the fight (v22 g22_msg: unless it says it is committed: a step to position)
			}
			const int reach = std::max(a.kit.attack_range + (a.kit.ranged ? 0 : 1), (a.kit.dmg >= 0 || a.kit.cc >= 0 || a.kit.aoe >= 0) ? 4 : 0);
			const int arr = std::max(0, de - reach - (a.kit.dash >= 0 ? 2 : 0));
			float w = std::clamp(1.f - static_cast<float>(arr) / std::max(1.f, t_me), 0.f, 1.f);
			float inc_a = 0;
			for (auto* e : E)
				if (cheb(e->pos, a.pos) <= reach_of(*e))
					inc_a += e->str + e->burst() / 2.f;
			if (a.hp <= inc_a)
				w = 0.f; // focused down before it can help
			if (w <= 0.f)
				continue;
			++sup_helpers;
			sup_hp += w * a.hp;
			if (arr < help_arr || (arr == help_arr && cheb(a.pos, pos) < cheb(help_pos, pos)))
				help_arr = arr, help_pos = a.pos;
			const float ab = std::max(a.str, a.focus * best_mod(a.kit));
			our_hp += w * a.hp;
			our_dps += w * (P.ally_spell_dps ? a.str + a.focus * best_mod(a.kit) / 8.f + ab / 3.f : a.str * 1.2f);
			if (w >= 0.75f)
				allies_burst += a.str;
			if (w >= 0.5f)
			{
				++allies_near;
				if (side_n < static_cast<int>(side_pos.size()))
					side_pos[static_cast<std::size_t>(side_n++)] = a.pos;
			}
		}
	}
	else
	for (const auto& a : W.allies)
		if (a.handle != self && a.alive && a.visible && cheb(a.pos, pos) <= 6 && (!P.support_filter || can_support(a, E)))
		{
			if (side_n < static_cast<int>(side_pos.size()))
				side_pos[static_cast<std::size_t>(side_n++)] = a.pos;
			const float ab = std::max(a.str, a.focus * best_mod(a.kit));
			our_hp += a.hp;
			our_dps += P.ally_spell_dps ? a.str + a.focus * best_mod(a.kit) / 8.f + ab / 3.f : a.str * 1.2f;
			allies_burst += a.str;
			++allies_near;
		}
	if (W.ally_spawn.is_set(pos) && P.spawn_heal_bonus)
	{
		// We heal fully next round on spawn, but only while the fight stays here: stepping off spawn to
		// engage loses the heal, and counting it there made champions bounce on and off spawn.
		const int hit_r = (ready(kit.dmg) || ready(kit.cc) || ready(kit.aoe)) ? std::max(4, kit.attack_range) : kit.attack_range;
		bool here = false;
		for (auto* e : E)
			here |= cheb(e->pos, pos) <= hit_r;
		if (here)
			our_hp += max_hp;
	}
	if (P.camp_in_fight)
	{
		// A5 (port of x_side): awake camps hit the nearest champion within 3 every round, whichever team it is on.
		// A team still tanking a camp took even fights against fresh arrivals (eight: C&I died r24-27 under the top
		// wolves; top-3 replays, swirl r14-20: our Ren tanked an elk the enemy woke while fighting 3). Ties count
		// against us (turn order). 3: only camps hitting an enemy (offensive half); 2: only ours; 1: both.
		for (const auto& g : W.groups)
		{
			if (g.st != ST_ALIVE || !g.awake || g.harmless || cheb(g.center, pos) > 12)
				continue;
			for (std::size_t i = 0; i < g.camps.size(); ++i)
			{
				if (g.hp[i] <= 0 || g.camps[i].str <= 0)
					continue;
				const vec2 c = g.camps[i].pos;
				int best_d = (P.fm_mode & 4) ? std::max(4, static_cast<int>(g.camps[i].range) + 1) : 4, who = -1; // -1 none, 0 me, 1 ally, 2 enemy
				for (int k = 0; k < side_n; ++k)
				{
					const int dd = cheb(side_pos[static_cast<std::size_t>(k)], c);
					if (dd < best_d)
						best_d = dd, who = k == 0 ? 0 : 1;
				}
				for (auto* e : E)
					if (cheb(e->pos, c) < best_d)
						best_d = cheb(e->pos, c), who = 2;
				if (who == 2)
				{
					if (P.camp_in_fight != 2)
						our_dps += g.camps[i].str;
				}
				else if (who >= 0 && P.camp_in_fight != 3)
				{
					their_dps += g.camps[i].str;
					if (who == 0)
						incoming += g.camps[i].str;
				}
			}
		}
	}
	const float t_kill_them = their_hp / std::max(1.f, our_dps);
	const float t_kill_us = our_hp / std::max(1.f, their_dps);
	// Learned calibration: bodies that died after choosing fights trust their estimate less.
	float adv = t_kill_us / std::max(0.1f, t_kill_them) * learner().fight_scale();

	// Backup: allies in sight, plus hidden allies whose claimed camp is close (they are a few steps away).
	// Half our deaths on the ladder were lone champions caught by two or more enemies.
	int backup = (P.sup_mode & 2) ? sup_helpers : allies_near;
	int dead_allies = 0;
	{
		const auto& C = comms();
		for (int i = 0; i < static_cast<int>(W.allies.size()); ++i)
		{
			const auto& a = W.allies[static_cast<std::size_t>(i)];
			if (!a.alive)
			{
				++dead_allies;
				continue;
			}
			if (a.handle == self || (a.visible && cheb(a.pos, pos) <= 6) || (P.sup_mode & 2))
				continue;
			const int cg = i < 6 ? C.claim[static_cast<std::size_t>(i)] : -1;
			const vec2 at = a.visible ? a.pos : (cg >= 0 && cg < static_cast<int>(W.groups.size()) ? W.groups[static_cast<std::size_t>(cg)].center : vec2{ -100, -100 });
			if (cheb(at, pos) <= P.backup_radius)
				++backup;
		}
	}
	const bool isolated = backup == 0;
	// With half the team waiting to respawn, another death hands them the map: only sure fights.
	const bool reserve = dead_allies * 2 >= static_cast<int>(W.allies.size());
	int nearest_enemy = BIG;
	for (auto* e : E)
		nearest_enemy = std::min(nearest_enemy, cheb(e->pos, pos));

	// Team-consistent focus target: allies seeing the same fight pick the same enemy (no distance term).
	// Cassi and Issac die together: hitting the weaker of the pair kills two bodies. Ren reflects 0.2 x focus
	// per hit, so a low champion should not swing at him unless he dies now.
	const int my_reach = kit.attack_range + (kit.ranged ? 0 : 1) + (ready(kit.dash) ? 2 : 0);
	Enemy* tgt = nullptr;
	float best = -1;
	for (auto* e : E)
	{
		if (cheb(pos, e->pos) > std::max(my_reach, 4) + 2)
			continue;
		float eff_hp = std::max(50.f, e->hp);
		float bonus = 0;
		if (e->type == CT::cassi || e->type == CT::issac)
			bonus += 60.f;
		if (e->type == CT::ren)
		{
			const float reflect = bc::constants::passive_abilities::ren_retaliation_focus_ratio * e->focus;
			if (hp < 4.f * reflect && e->hp > burst_vs(*e))
				continue;
		}
		const float v = P.tp_focus ? tp_target_value(*e, eff_hp) + (e->channeling ? 60.f : 0.f) / eff_hp
								   : (60.f + bonus + static_cast<float>(e->gems) + (e->channeling ? 60.f : 0.f)) / eff_hp;
		if (v > best)
			best = v, tgt = e;
	}
	if (!tgt)
	{
		tgt = E.front();
		for (auto* e : E)
			if (cheb(pos, e->pos) < cheb(pos, tgt->pos))
				tgt = e;
	}
	const int d = cheb(pos, tgt->pos);
	// P.ren_reflect (agent survive): Ren returns 0.2 x focus of every hit to its attacker, so a fight on Ren costs each of
	// our hitters that much per round on top of the enemies' damage. The estimate left it out: ladder fragment r78-88, our
	// Stellar (750) and Ren hit their Ren (1,900 max health) for 10 rounds, Stellar lost ~70 a round and died.
	if (P.ren_reflect && tgt->type == CT::ren)
	{
		const float reflect = bc::constants::passive_abilities::ren_retaliation_focus_ratio * tgt->focus;
		const float tku = our_hp / std::max(1.f, their_dps + reflect * static_cast<float>(1 + allies_near));
		adv = tku / std::max(0.1f, t_kill_them) * learner().fight_scale();
	}
	const int aoe_r5 = P.aoe_cast5 && ready(kit.aoe) ? static_cast<int>(kit.aoe_range + kit.aoe_radius) : 0;
	bool killable = d <= std::max(my_reach, (ready(kit.dmg) || ready(kit.cc)) ? 4 : 0) &&
		tgt->hp + ((P.fm_buffs & 1) ? tgt->shield : 0.f) <= burst_vs(*tgt) + allies_burst;
	if (!killable && aoe_r5 > 0 && d <= aoe_r5)
		killable = tgt->hp <= (d <= kit.attack_range && can_attack ? str : 0.f) + focus * kit.aoe_mod + allies_burst; // F2: the area from 5
	const bool in_reach = P.aoe_reach5 == 3 ? danger4.is_set(pos) : danger.is_set(pos);

	// Can we actually get away? Melee and dash chasers move and hit in the same turn. Fleeing only works
	// if no such chaser is close, if our own dash outruns theirs, or if we survive the whole walk home.
	bool chaser = false, chaser_dash = false;
	for (auto* e : E)
		if ((!e->kit.ranged || e->ready(e->kit.dash)) && cheb(pos, e->pos) <= 3 + (e->ready(e->kit.dash) ? 2 : 0))
		{
			chaser = true;
			chaser_dash |= e->ready(e->kit.dash);
		}
		else if ((P.v23_hy & 1) && e->kit.ranged && (e->kit.attack_range > kit.attack_range || ((P.v23_hy & 2) && e->kit.attack_range == kit.attack_range)) &&
				 cheb(pos, e->pos) <= e->kit.attack_range + 1)
			chaser = true; // it steps after us and shoots: the walk home is under fire every round
	const float t_die = hp / std::max(1.f, incoming);
	const int dh = W.dist_home(pos);
	const bool on_spawn = W.ally_spawn.is_set(pos);
	const bool can_escape = on_spawn || !chaser || (ready(kit.dash) && !chaser_dash) || static_cast<float>(dh) + 1.f < t_die;

	// sup_mode 4: leaving toward a helper that arrives within 3 rounds (one step, never into more enemy reach) instead of home:
	// one-by-one retreats were the biggest loss pattern (19 of 33 deaths alone on nx61x61, 22 of 45 on contest_v3).
	auto toward_help = [&]() -> bool {
		if (!((P.sup_mode & 4) || P.v27_rally) || help_arr > 3 || !can_move || hp < P.sup_low_hp * max_hp || cheb(help_pos, pos) <= 1)
			return false;
		auto n_reach = [&](vec2 p) {
			int n = 0;
			for (auto* e : E)
				n += cheb(p, e->pos) <= reach_of(*e);
			return n;
		};
		const int n0 = n_reach(pos), d0 = cheb(pos, help_pos);
		const bc::bitboard blocked = Nav::blocked_now(pos);
		vec2 best = pos;
		int bn = n0 + 1, bd = d0;
		for (int dy = -1; dy <= 1; ++dy)
			for (int dx = -1; dx <= 1; ++dx)
			{
				const vec2 p{ pos.x + dx, pos.y + dy };
				if ((dx == 0 && dy == 0) || !bc::map::is_in_bounds(p) || blocked.is_set(p) || W.walls.is_set(p))
					continue;
				const int n = n_reach(p), dd = cheb(p, help_pos);
				if (n > n0 || dd >= d0)
					continue;
				if (n < bn || (n == bn && dd < bd))
					bn = n, bd = dd, best = p;
			}
		if (best == pos)
			return false;
		bc::bitboard g;
		g.set(best);
		return step(g, false, false);
	};

	// v23_hy 8 (4.5.4 step 5): a bag next to an altar is banked now, in the fight, when we outlive the channel and no stun is ready near us.
	if ((P.v23_hy & 8) && static_cast<int>(gems) >= P.v23_fight_bank && !killable && stunners == 0)
	{
		const int ticks = static_cast<int>((gems + 9) / 10);
		if (incoming * static_cast<float>(ticks + 1) < hp)
			for (const auto& at : W.altars)
				if (cheb(at, pos) <= 1)
				{
					try
					{
						bc::self().submit_gems(at);
						task = T_TRIBUTE;
						tribute_start = round, tribute_ticks = ticks;
						return true;
					}
					catch (...)
					{
					}
					break;
				}
	}
	bool fight = false;
	// P.pair_kill_adv: a low Cassi or Issac (below pair_low_hp) needs this advantage for a 'sure kill' (allies' burst is a guess).
	const bool low_pair = (type == CT::cassi || type == CT::issac) && hp < P.pair_low_hp * max_hp;
	if (killable && adv >= (low_pair ? P.pair_kill_adv : 0.5f))
		fight = true;
	else if (adv >= fight_margin)
		fight = true;
	else if (in_reach && adv >= fight_back_margin)
		fight = true;
	else if (in_reach && !can_escape && adv >= P.cornered_margin)
		fight = true; // fleeing a same-speed chaser hands it free hits: trade instead
	else if (P.ally_defend && adv >= fight_back_margin && hp >= P.ally_defend_hp * max_hp && ally_engaged(*tgt))
		fight = true; // an ally next to this target just took damage: join at the hit-back bar (audit: 49% of our champion deaths had an
					  // ally within 10 that never hit, most of them healthy and within 6)
	else if (tgt->channeling && adv >= 0.9f)
		fight = true;
	// P.pair_low_hp: Cassi & Issac leave a fight they can walk away from earlier (ladder: 64% of our 59 pair deaths were
	// triggered by the partner below 25% health, the other partner healthy (73% above 75%) and 7+ tiles away).
	const float low_hp = (type == CT::cassi || type == CT::issac) ? P.pair_low_hp : 0.25f;
	if (fight && !killable && can_escape && (hp < low_hp * max_hp || (static_cast<int>(gems) >= (P.anchors ? bag_caution_now : P.bag_caution) && adv < 1.5f && !(P.no_altar_gold && W.no_altar_now()))))
		fight = false;
	// mi_lethal (default branch): it has shown it can kill us from here; leave unless the kill is ours first.
	if (P.mi_lethal && fight && !killable && !(in_reach && !can_escape) && lethal >= hp)
		fight = false;
	if (fight && reserve && !(killable && adv >= 1.f) && adv < fight_margin + P.reserve_margin && can_escape)
		fight = false;
	if (fight && isolated && !killable && adv < isolated_fight_adv && can_escape)
		fight = false;
	// v22 g22_solo (doc 32: 464 of our 1,450 deaths against IC / Mite had no ally within 6; in 70% of them 2+ enemies were in sight for
	// 6+ rounds, the victim at 83% health on average kept fighting or walked toward them, then was burst): alone against a group, only
	// a kill this turn or our own spawn justifies staying. 1: when we can still get away; 2: always. `isolated` above misses it because
	// hidden allies with a claimed camp nearby count as backup.
	bool solo_vs_group = false;
	if (P.g22_solo)
	{
		int allies_vis = 0, enemies_8 = 0;
		for (const auto& a : W.allies)
			allies_vis += a.handle != self && a.alive && a.visible && !a.channeling && cheb(a.pos, pos) <= P.g22_solo_r;
		for (auto* e : E)
			enemies_8 += cheb(e->pos, pos) <= 8;
		solo_vs_group = allies_vis == 0 && enemies_8 >= 2 && !on_spawn && adv < P.g22_solo_adv;
		if (fight && solo_vs_group && !killable && (can_escape || P.g22_solo >= 2))
			fight = false;
	}
	// The user's rule (session 2): stay and keep hitting only when our own health outlasts the most the enemies
	// here can deal before the target dies (every visible enemy hitting us every round, spells included) and no
	// other enemy is near the target to support it; when they could kill us first, do not start it while we can
	// still get away (when we cannot, the cornered rule above trades instead of handing a dash/ranged chaser
	// free hits).
	if (P.stay_rule)
	{
		int support = 0;
		for (const auto& e : W.enemies)
			if (e.alive && e.seen_round >= 0 && round - e.seen_round <= P.threat_memory && &e != tgt && cheb(e.pos, tgt->pos) <= P.stay_support_r)
				++support;
		const float worst = their_dps * (std::ceil(tgt->hp / std::max(1.f, our_dps)) + 1.f);
		if (support == 0 && hp > worst * P.stay_margin && d <= my_reach + 2)
			fight = true;
		else if (P.stay_veto && fight && !killable && can_escape && hp <= worst)
			fight = false;
	}
	// Fight commitment: having fought last turn, keep at it unless the estimate dropped clearly or we are low. The
	// per-turn re-evaluation alone flipped T_FIGHT / T_FLEE under fire (walk in, walk out, hit nobody).
	if (P.fight_commit && !fight && last_fight_round == round - 1 && adv >= P.fight_commit_margin && hp >= P.fight_commit_hp * max_hp)
		fight = true;
	// A7 (burst_exit): leave before the finisher. 40% of our death incidents in the top-3 replays started above 60%
	// health four rounds before: burst down, not worn down. Only the enemies that can hit us before our next turn
	// count (one basic attack + their best ready cast each); only when we can still get away and the target does not
	// die now. Short: next turn, out of their reach, the normal rules decide again.
	if (fight && P.burst_exit && !killable && can_escape && in_reach && (P.burst_exit != 2 || !chaser))
	{
		float burst_next = 0;
		for (auto* e : E)
			if (cheb(e->pos, pos) <= reach_of(*e))
				burst_next += e->str + e->burst();
		if (hp <= P.burst_exit_k * burst_next)
			fight = false;
	}
	// A bag that wins the game is worth more than any fight we can walk away from.
	if (fight && P.win_bank && !killable && can_escape && gems > 0 && wins_with(static_cast<int>(gems)))
		fight = false;
	// Do not dive their spawn: it heals them and they block us.
	if (W.enemy_spawn.is_set(tgt->pos) || cheb(tgt->pos, W.enemy_spawn_c) <= 3)
		fight = fight && killable;
	bool ml2_kill = killable; // a kill this turn (ours or the team's): the model never vetoes it
	if (P.px_mode)
	{
		// Proxy of the top teams' fights: the team target is the lowest-health body we can hit this turn (a body the
		// team kills this turn first: our hit + ready spell + allies next to it), engage at even local power, hit back
		// when hit, keep fighting once in, leave only low or clearly outmatched.
		Enemy* pt = nullptr;
		float pk = 1e9f;
		const bool spell_up = ready(kit.dmg) || ready(kit.cc) || ready(kit.aoe);
		for (auto* e : E)
		{
			const int de = cheb(pos, e->pos);
			const bool spell_r = (spell_up && de <= 4) || de <= aoe_r5;
			if (de > my_reach && !spell_r)
				continue;
			if (e->type == CT::ren)
			{
				const float reflect = bc::constants::passive_abilities::ren_retaliation_focus_ratio * e->focus;
				if (hp < 3.f * reflect && e->hp > burst_vs(*e))
					continue;
			}
			float tb = de <= my_reach && can_attack ? str * (ready(kit.reset) ? 2.f : 1.f) : 0.f;
			if (spell_r && de > 4)
				tb += focus * kit.aoe_mod; // F2: only the area reaches 5
			else if (spell_r)
				tb += std::max({ ready(kit.dmg) ? focus * kit.dmg_mod : 0.f, ready(kit.cc) ? focus * kit.cc_mod : 0.f, ready(kit.aoe) ? focus * kit.aoe_mod : 0.f });
			for (const auto& a : W.allies)
				if (a.handle != self && a.alive && a.visible && a.kit_ready && cheb(a.pos, e->pos) <= std::max(a.kit.attack_range + 1, 4))
					tb += (cheb(a.pos, e->pos) <= a.kit.attack_range + 1 ? a.str : 0.f) + (P.px_ally_spells ? 0.5f * a.focus * best_mod(a.kit) : 0.f);
			const bool pair = e->type == CT::cassi || e->type == CT::issac;
			const float key = (e->hp <= tb ? 0.f : 1e5f) + e->hp - (pair ? 150.f : 0.f) - (e->channeling ? 200.f : 0.f);
			if (key < pk)
				pk = key, pt = e;
		}
		const bool pkill = pt && pk < 1e5f;
		ml2_kill |= pkill;
		if (pt)
			tgt = pt;
		if (P.px_mode == 2)
		{
			// targeting only: legend's fight decision and exits, plus a team kill this turn always taken
			if (pkill && !(W.enemy_spawn.is_set(tgt->pos) || cheb(tgt->pos, W.enemy_spawn_c) <= 3))
				fight = true;
		}
		else
		{
		fight = false;
		if (pkill)
			fight = true;
		else if (hp < P.px_retreat_hp * max_hp)
			fight = in_reach && !can_escape && adv >= 0.5f;
		else if (adv >= P.px_engage && nearest_enemy <= P.px_hunt_r)
			fight = true;
		else if (in_reach && adv >= P.px_fightback)
			fight = true;
		else if (in_reach && !can_escape && adv >= 0.4f)
			fight = true;
		if (!fight && last_fight_round == round - 1 && adv >= P.px_commit && hp >= P.px_retreat_hp * max_hp)
			fight = true;
		if (W.enemy_spawn.is_set(tgt->pos) || cheb(tgt->pos, W.enemy_spawn_c) <= 3)
			fight = fight && pkill;
		if (fight && P.win_bank && !pkill && can_escape && gems > 0 && wins_with(static_cast<int>(gems)))
			fight = false;
		if (fight && !pkill && (P.px_hold > 0 || P.px_burst_wait > 0) && !tgt->channeling && !tgt->tributing)
		{
			const int dt = cheb(pos, tgt->pos);
			const bool spell_now = (dt <= 4 && (ready(kit.dmg) || ready(kit.cc) || ready(kit.aoe))) || dt <= aoe_r5;
			if (dt > kit.attack_range && !spell_now)
			{
				bool step_in = in_reach;
				for (auto* e : E)
					step_in |= cheb(pos, e->pos) - 1 <= reach_of(*e);
				bool soon = false;
				if (P.px_burst_wait > 0 && !ready(kit.dmg) && !ready(kit.cc) && !ready(kit.aoe))
					for (int sl : { kit.dmg, kit.cc, kit.aoe })
						soon |= sl >= 0 && cd[static_cast<std::size_t>(sl)] > 0 && cd[static_cast<std::size_t>(sl)] <= P.px_burst_wait;
				if (round - px_hold_round > 1)
					px_hold_since = round;
				px_hold_round = round;
				const int lim = std::max(P.px_hold, soon ? P.px_burst_wait : 0);
				if (!in_reach && (step_in || soon) && round - px_hold_since < lim)
				{
					task = T_FIGHT;
					last_fight_round = round;
					engaged = true;
					return true; // hold here: they step in, we hit first
				}
			}
		}
		if (!fight && !in_reach)
		{
			engaged = nearest_enemy <= 5;
			if (adv < P.px_flee_adv && nearest_enemy <= P.flee_dist && task != T_CAPTURE)
			{
				post_danger(tgt->pos);
				task = T_FLEE;
				avoid_note(E); // v27_avoid
				if (go_home_step(true))
					return true;
			}
			return false;
		}
		}
	}
	if (P.ml2_leave > 0.f || ml2_flee_eff > 0.f || P.ml2_enter > 0.f || P.ml2_hold > 0)
	{
		// ml2: the danger model learned on real ladder games (P(we die within 8 rounds) from what we see). Against ladder
		// teams our estimate called 1,100 contact states 'fight' (adv >= 1.3) in which the model gave >= 0.3 and the body
		// died 45-71% of the time (doc: experiments/wip/x_ml2_NOTES.md).
		ml2_p_die = 0, ml2_p_kill = 0;
		if (nearest_enemy <= 7)
		{
			float mf[ML2_NF];
			ml2_features(mf);
			const float z = P.ml2_gb ? ml2_gb_die8(mf) : ml2_logit(ML2_W_DIE8, ML2_B_DIE8, mf);
			if (P.ml2_adapt > 0.f)
			{
				ml2_learn(false);
				if (ml2_buf_n < static_cast<int>(ml2_buf_r.size()))
				{
					ml2_buf_r[static_cast<std::size_t>(ml2_buf_n)] = round;
					ml2_buf_z[static_cast<std::size_t>(ml2_buf_n)] = z;
					++ml2_buf_n;
				}
			}
			ml2_p_die = ml2_sig(z + ml2_off);
			if (P.ml2_enter > 0.f)
				ml2_p_kill = ml2_sig(ml2_logit(ML2_W_KILL8, ML2_B_KILL8, mf));
#ifdef ML2_DEBUG
			debug_block({
				std::printf("ML2 r=%d b=%d p=%.4f off=%.3f n=%d f=", round, W.my_index, ml2_p_die, ml2_off, ml2_buf_n);
				for (int i = 0; i < ML2_NF; ++i)
					std::printf("%.4f,", mf[i]);
				std::printf("\n");
			});
#endif
		}
		// ml2_cornered: also when combat() thinks a chaser cannot be outrun. Ladder rows in reach, no kill, P(die8) 0.3-0.5 with
		// can_escape = 0: our bodies that hit died 51% (kill8 20%), those that stepped away 29% (P >= 0.5: 74% vs 38%).
		const float ml2_sup = (P.sup_mode & 8) ? P.sup_ml2_bonus * std::min(1.f, sup_hp / std::max(1.f, max_hp)) : 0.f;
		if (P.ml2_leave > 0.f && fight && !ml2_kill && (can_escape || P.ml2_cornered) && ml2_p_die >= (P.anchors && is_anchor ? P.anchor_ml2 : P.ml2_leave) + ml2_sup)
			fight = false, ml2_exit_round = round;
		if (P.ml2_hold > 0 && fight && !ml2_kill && !in_reach && round - ml2_exit_round <= P.ml2_hold)
			fight = false; // we just left on the model: no proactive walk back in
		if (P.ml2_enter > 0.f && !fight && ml2_p_kill >= P.ml2_enter && ml2_p_die < P.ml2_enter_die && d <= my_reach + 1 &&
			!(W.enemy_spawn.is_set(tgt->pos) || cheb(tgt->pos, W.enemy_spawn_c) <= 3))
			fight = true;
		if (ml2_flee_eff > 0.f && !fight && !in_reach && !ml2_kill && ml2_p_die >= (P.anchors && is_anchor ? P.anchor_ml2 : ml2_flee_eff) + ml2_sup && nearest_enemy <= P.flee_dist && task != T_CAPTURE &&
			!((calm_bits & 1) && g15_nthreat == 0))
		{
			ml2_exit_round = round;
			post_danger(tgt->pos);
			task = T_FLEE;
			avoid_note(E); // v27_avoid
			if (go_home_step(true))
				return true;
		}
	}
	XM(xm_fight(adv, t_kill_us, t_kill_them, our_hp, their_hp, our_dps, their_dps, allies_near, static_cast<int>(E.size()), fight, killable, in_reach,
		can_escape, isolated, reserve, static_cast<int>(tgt->type), d, incoming, t_die, tgt->hp, backup, str + focus * best_mod(kit) / 8.f + my_burst / 3.f));
	engaged = fight || in_reach || nearest_enemy <= 5;
	(void)stunners;

	if (fz_engage_eff > 0 && fight && !in_reach && !killable && last_fight_round < round - 1 && d > fz_engage_eff && !tgt->channeling && !tgt->tributing)
		fight = false; // v14 fz_engage: not yet in a fight and the target is still far: keep doing what we do
	if (P.fz_chase > 0 && !in_reach)
	{
		// v14 fz_chase: a same-speed target walking away is never caught; once the distance has not shrunk for fz_chase rounds the chase
		// ends (we farm or bank instead) and that target is left alone for fz_chase_off rounds unless it comes into reach.
		if (fight && !tgt->channeling && !tgt->tributing)
		{
			if (chase_h != tgt->handle || round - chase_round > 1)
				chase_h = tgt->handle, chase_best = d, chase_since = round;
			else if (d < chase_best)
				chase_best = d, chase_since = round;
			chase_round = round;
			if (round - chase_since >= P.fz_chase)
				chase_off_until = round + P.fz_chase_off;
		}
		if (fight && chase_h == tgt->handle && round <= chase_off_until && !tgt->channeling && !tgt->tributing)
			fight = false;
	}
	if (P.g22_chase > 0 || P.g22_chase_deep)
	{
		// v22 g22_chase: a target we cannot hit this turn that holds its distance and does not walk away from its spawn is a retreat or a
		// lure (Mite / IC back off inside their own reach, so fz_chase above never sees it); following it costs us the farm and pulls us
		// into their team. Drop it once it has not lost health for g22_chase rounds; leave it alone unless it comes into our reach.
		int hit_reach = kit.attack_range + (kit.ranged ? 0 : 1) + (ready(kit.dash) ? 2 : 0);
		if (ready(kit.dmg)) hit_reach = std::max(hit_reach, static_cast<int>(kit.dmg_range));
		if (ready(kit.cc)) hit_reach = std::max(hit_reach, static_cast<int>(kit.cc_range));
		if (ready(kit.aoe)) hit_reach = std::max(hit_reach, static_cast<int>(kit.aoe_range + kit.aoe_radius));
		const bool exempt = killable || d <= hit_reach || tgt->channeling || tgt->tributing;
		const int home_d = cheb(tgt->pos, W.enemy_spawn_c);
		if (P.g22_chase > 0 && fight && !exempt)
		{
			if (g22_ch_h != tgt->handle || round - g22_ch_round > 1 || d < g22_ch_d || home_d > g22_ch_home || tgt->hp < g22_ch_hp - 1.f)
				g22_ch_h = tgt->handle, g22_ch_since = round, g22_ch_hp = tgt->hp;
			g22_ch_round = round, g22_ch_d = d, g22_ch_home = home_d;
			if (round - g22_ch_since >= P.g22_chase)
				g22_ch_off = round + P.g22_chase_off;
		}
		if (fight && !exempt && g22_ch_h == tgt->handle && round <= g22_ch_off)
			fight = false;
		if (P.g22_chase_deep && fight && !exempt && cheb(pos, W.enemy_spawn_c) + P.g22_deep_margin < cheb(pos, W.ally_spawn_c))
			fight = false;
	}
	// v15 g15_calm & 4: starting a fight we have to walk to needs a target that is coming at us (or one step from our reach), a kill, a
	// channel or a bag worth chasing; otherwise we keep farming (v14 walked 175 rounds a body toward fights, the ladder teams 73).
	if ((calm_bits & 4) && fight && !in_reach && !killable && last_fight_round < round - 1 && d > my_reach + 1 && !tgt->channeling && !tgt->tributing &&
		tgt->gems < 40 && !g15_is_threat(*tgt))
		fight = false;
	if (P.g15_fwalk > 0)
	{
		// v15 g15_fwalk: a fight we keep walking to without getting into reach is a same-speed chase; stop it and farm for a while.
		const bool exempt = in_reach || killable || tgt->channeling || tgt->tributing;
		if (fight && !exempt)
		{
			if (round <= g15_fw_off)
				fight = false;
			else
			{
				g15_fw_n = g15_fw_round == round - 1 ? g15_fw_n + 1 : 1;
				g15_fw_round = round;
				if (g15_fw_n > P.g15_fwalk)
					fight = false, g15_fw_off = round + P.g15_fwalk_off, g15_fw_n = 0;
			}
		}
		else if (fight)
			g15_fw_n = 0; // a real exchange: the walk paid off
	}
	// Early warning: an outnumbering group is visible; allies keep away from it.
	if (!fight && E.size() >= 3 && adv < 1.f)
		post_danger(tgt->pos);
	if (fight && (P.strike_first & 2) && kit.ranged && !in_reach && !killable && d > kit.attack_range && !ready(kit.dash) &&
		!(d <= 4 && (ready(kit.cc) || ready(kit.dmg) || ready(kit.aoe))))
	{
		// A6, ranged: walking into range spends this turn's attack (ranged cannot attack after a walk), so the side
		// that steps in is hit first. Out of their reach, let them come (at most strike_hold rounds per fight).
		if (round - sf_round > 1)
			sf_since = round;
		sf_round = round;
		if (round - sf_since < P.strike_hold)
		{
			task = T_FIGHT;
			return true;
		}
	}
	if (fight && (P.strike_first & 1) && !in_reach && !killable && my_burst <= 0.f && d > my_reach)
	{
		// A6: proactive fight with our burst on cooldown: wait outside their reach (at most strike_hold rounds per
		// fight) for the opener; whoever hits first wins (top-3 replays: they hit first in 86 of 152 fights; when they
		// did, our deaths were 97 to their 17).
		bool soon = false;
		for (int sl : { kit.dmg, kit.cc, kit.aoe, kit.reset })
			soon |= sl >= 0 && cd[static_cast<std::size_t>(sl)] > 0 && cd[static_cast<std::size_t>(sl)] <= P.strike_hold;
		if (round - sf_round > 1)
			sf_since = round;
		sf_round = round;
		if (soon && round - sf_since < P.strike_hold)
		{
			task = T_FIGHT;
			return true; // hold this turn (not in reach: nothing to hit)
		}
	}
	if (fight)
	{
		last_fight_round = round;
		if (!(P.alert_prio && comms().fresh(round, 6) && (comms().alert_kind == AL_OPPORTUNITY || (P.escort_bag > 0 && (P.om_sight ? escort_alert() : comms().alert_kind == AL_DANGER)))) &&
			!((P.g15_lock & 16) && comms().alert_kind == AL_OPPORTUNITY && comms().t4_deadline > round)) // v15 bit 16: a posted tribute stays up until it lands
			comms().post(AL_RALLY, tgt->pos, round);
		learner().on_fight(round);
		task = T_FIGHT;
		if (P.v23_hy & 4)
		{
			fe_no_cc = tgt->stunned; // keep our stun for the round after theirs ends
			const bool r = engage(*tgt);
			fe_no_cc = false;
			return r;
		}
		return engage(*tgt);
	}
	if (in_reach && !(round < pw_calm_until && hp >= pw_calm_hp - 1.f && round - last_hit_round > 1))
	{
		post_danger(tgt->pos);
		task = T_FLEE;
		avoid_note(E); // v27_avoid
		// Melee may attack and walk in one turn: swing at an adjacent enemy before stepping away (the step usually
		// leaves it out of reach, so swinging after the step hit nothing).
		if (P.exec_flee_hit && !kit.ranged && can_attack)
			if (Enemy* o = best_in_reach(nullptr))
				attack_unit(*o->ch);
		// A stun on the closest melee chaser buys a free step (only stuns that still let us walk).
		for (auto* e : E)
			if (e->ch && !kit.cc_excl && (!e->kit.ranged || e->ready(e->kit.dash)) && cheb(pos, e->pos) <= static_cast<int>(kit.cc_range) && ready(kit.cc))
			{
				cast_unit_champ(kit.cc, *e->ch);
				break;
			}
		// A walk-exclusive stun (Ren, Ryth, Tavi, Prism) costs our step, but against a chaser whose basic attack
		// still reaches us after that step (melee step + hit, dash + hit, or ranged at 2) the step gains nothing:
		// it follows and hits. The stun denies that turn (this round's if it has not acted yet, else the next),
		// deals damage, and the walk resumes next turn. Traced: 245 flee turns with such a stun ready in 3 games,
		// none cast. Not near home: there the step to the healing spawn is worth more.
		if (P.flee_stun && !cast_done && W.dist_home(pos) > 2 && ((kit.cc >= 0 && kit.cc_excl && ready(kit.cc)) || (kit.aoe_stuns && ready(kit.aoe))))
		{
			Enemy* chaser_e = nullptr;
			int best_d = BIG;
			for (auto* e : E)
			{
				if (!e->ch || e->type == CT::marcella)
					continue;
				const int dd = cheb(pos, e->pos);
				const int hit_reach = e->kit.attack_range + (e->kit.ranged ? 0 : 1) + (e->ready(e->kit.dash) ? 2 : 0);
				if (dd + 1 <= hit_reach && dd < best_d)
					best_d = dd, chaser_e = e;
			}
			if (chaser_e)
			{
				const bool cc_ok = kit.cc >= 0 && kit.cc_excl && best_d <= static_cast<int>(kit.cc_range) && cast_unit_champ(kit.cc, *chaser_e->ch);
				if (cc_ok || (kit.aoe_stuns && ready(kit.aoe) && cast_area_stun_at(*chaser_e)))
				{
					dbg_eng = 8;
					if (!kit.ranged && can_attack && best_d <= kit.attack_range)
						attack_unit(*chaser_e->ch);
					return true;
				}
			}
		}
		if (P.flee_recall && W.dist_home(pos) > P.recall_min_dist && safe_to_recall())
		{
			try
			{
				bc::self().recall();
				return true;
			}
			catch (...)
			{
			}
		}
		if (toward_help() || go_home_step(true))
		{
			// Melee champions can still swing after walking.
			if (!kit.ranged && can_attack)
				for (auto* e : E)
					if (e->ch && cheb(pos, e->pos) <= kit.attack_range)
					{
						attack_unit(*e->ch);
						break;
					}
			return true;
		}
		return engage(*tgt); // cornered: hit back
	}
	// Leave before they reach us: alone (or with half the team dead) against a stronger group, start walking
	// home while they are still out of stun range. Same speed means they cannot close the gap.
	// P.outmatch_flee (agent survive): the same early exit when we are not alone but the group here still outmatches
	// us. Between the flee and the fight bars (adv 0.8-1.3) a body kept farming or walking while the group closed in;
	// once in reach a same-speed chaser cannot be outrun. Ladder (17 games of legend_st, 232 deaths): the killers were
	// within 8 tiles for 7+ rounds before 75% of our deaths, the victim walked toward them in 48%, 58% died with the
	// enemy holding >1.2x our health within 6.
	const bool pair_body = type == CT::cassi || type == CT::issac;
	const float out_bar = static_cast<int>(E.size()) >= P.outmatch_min_enemies ? P.outmatch_flee_adv : P.outmatch_solo_adv;
	const bool outmatched = P.outmatch_flee && nearest_enemy <= P.outmatch_flee_dist && out_bar > 0.f &&
		adv < out_bar + (pair_body ? P.pair_flee_bonus : 0.f);
	const bool calm = round < pw_calm_until && hp >= pw_calm_hp - 1.f && round - last_hit_round > 1; // v27_watch flee calm
	bool can_call = false; // v27_rally: a healthy ally within 10 can come
	if (P.v27_rally)
		for (const auto& a : W.allies)
			can_call |= a.handle != self && a.alive && a.visible && !a.channeling && a.hp >= 0.5f * a.max_hp && cheb(a.pos, pos) <= 10;
	if (!calm && ((((isolated || reserve) && adv < P.isolated_flee_adv && nearest_enemy <= P.flee_dist) || outmatched) && task != T_CAPTURE &&
		 !((calm_bits & 1) && g15_nthreat == 0)) || // v15: nobody here is coming at us: keep farming
		(solo_vs_group && nearest_enemy <= P.g22_solo_leave && !(task == T_CAPTURE && nearest_enemy > 4)))
	{
		if (can_call)
			comms().post(AL_RALLY, pos, round);
		else
			post_danger(tgt->pos);
		task = T_FLEE;
		avoid_note(E); // v27_avoid
		if (P.flee_recall && W.dist_home(pos) > P.recall_min_dist && safe_to_recall())
		{
			try
			{
				bc::self().recall();
				return true;
			}
			catch (...)
			{
			}
		}
		if (toward_help() || go_home_step(true))
			return true;
		if (W.ally_spawn.is_set(pos))
		{
			task = T_WAIT; // already home: hold here (healing) rather than step out to them and back
			return true;
		}
	}
	return false;
}

void Brain::post_danger(vec2 at)
{
	// Nothing reads DANGER unless alert_radius > 0, and the team has one alert slot: never let it replace a
	// fresh RALLY or OPPORTUNITY (an enemy tribute the team should converge on).
	auto& C = comms();
	if (P.alert_radius <= 0 || (C.fresh(round, 6) && (C.alert_kind == AL_RALLY || C.alert_kind == AL_OPPORTUNITY)))
		return;
	C.post(AL_DANGER, at, round);
}

Enemy* Brain::best_in_reach(const Enemy* skip)
{
	auto& W = world();
	Enemy* best = nullptr;
	float bv = -1;
	for (auto& o : W.enemies)
	{
		if (&o == skip || !o.ch || !o.alive || !o.visible || cheb(pos, o.pos) > kit.attack_range)
			continue;
		if (W.enemy_spawn.is_set(o.pos) && o.max_hp > burst_vs(o) + 1.f)
			continue;
		if (o.type == CT::ren && hp <= 2.5f * bc::constants::passive_abilities::ren_retaliation_focus_ratio * o.focus && o.hp > str)
			continue;
		const float v = P.tp_focus ? tp_target_value(o, std::max(50.f, o.hp))
								   : (60.f + ((o.type == CT::cassi || o.type == CT::issac) ? 60.f : 0.f) + static_cast<float>(o.gems)) / std::max(50.f, o.hp);
		if (v > bv)
			bv = v, best = &o;
	}
	return best;
}

bool Brain::engage(Enemy& e)
{
	{
		const auto k = static_cast<std::size_t>(&e - world().enemies.data());
		if (k < fut_hp.size())
			fut_hp[k] = e.hp, fut_round[k] = round;
	}
	if (!e.ch)
		return false;
	if (e.type == CT::ren)
	{
		// Ren reflects 0.2 x focus of every hit back at the attacker: never trade our last health into him.
		const float reflect = bc::constants::passive_abilities::ren_retaliation_focus_ratio * e.focus;
		if (hp <= 2.5f * reflect && e.hp > burst_vs(e))
		{
			task = T_FLEE;
			go_home_step(true);
			return true;
		}
	}
	auto& ec = *e.ch;
	int d = cheb(pos, e.pos);
	if (P.exec_hit_first && d > kit.attack_range && can_attack)
	{
		// The team target is out of reach but another enemy is in reach: a turn spent walking under fire deals nothing.
		if (Enemy* o = best_in_reach(&e))
		{
			if (kit.ranged)
			{
				if (!cast_done && !cast_unit_champ(kit.dmg, *o->ch))
					cast_unit_champ(kit.cc, *o->ch);
				if (attack_unit(*o->ch))
				{
					std::int32_t alive_flag = 1;
					bc::detail::sdk_champion_is_alive(o->handle, &alive_flag);
					if (alive_flag && !cast_done && ready(kit.reset) && cast_self(kit.reset))
						attack_unit(*o->ch);
				}
				dbg_eng = 30;
				return true;
			}
			attack_unit(*o->ch); // melee: then still walk toward the target below
			dbg_eng = 31;
		}
	}
	if (d > 4 && cast_on_nearer(e))
		return true;
	const int aoe_r5 = P.aoe_cast5 && ready(kit.aoe) ? static_cast<int>(kit.aoe_range + kit.aoe_radius) : 0;
	if (d > kit.attack_range)
	{
		bc::bitboard goal;
		goal.draw_chebyshev(e.pos, static_cast<float>(kit.attack_range));
		if (P.spread_vs_splash && splash_threat)
		{
			const bc::bitboard g2 = goal & ~clump & ~world().walls;
			if (!g2.is_empty())
				goal = g2;
		}
		if (P.engage_angle)
		{
			// Approach the target from the side its allies cannot reach: the end tile of the walk is outside the next-turn
			// reach of every other visible enemy when such a ring tile exists (bodies walked into the target's group and
			// were focused: the visible-enemy count jumped 1 -> 3-5 on the turn they entered reach, x_fight traces).
			bc::bitboard others;
			for (const auto& o : world().enemies)
			{
				if (&o == &e || !o.alive || !o.visible || cheb(o.pos, e.pos) > 8)
					continue;
				int r = o.kit.attack_range + (o.kit.ranged ? 0 : 1) + (o.ready(o.kit.dash) ? 2 : 0);
				if (P.aoe_reach5)
					r = std::max(r, enemy_spell_reach(o, false));
				else if (o.ready(o.kit.dmg) || o.ready(o.kit.cc) || o.ready(o.kit.aoe))
					r = std::max(r, 4);
				others.draw_chebyshev(o.pos, static_cast<float>(r));
			}
			const bc::bitboard g2 = goal & ~others & ~world().walls;
			if (!g2.is_empty())
				goal = g2;
		}
		if (P.pair_space && type == CT::cassi)
		{
			// A9: Cassi stands 2-3 from Issac, never next to him (an area spell or Varg splash on the pair kills both:
			// collision r41/r50 in the top-3 replays). Only when such a tile is free.
			for (const auto& a : world().allies)
				if (a.handle != self && a.alive && a.visible && a.type == CT::issac && cheb(a.pos, pos) <= 6)
				{
					bc::bitboard ring;
					ring.draw_chebyshev(a.pos, 3.f);
					bc::bitboard inner;
					inner.draw_chebyshev(a.pos, 1.f);
					const bc::bitboard g2 = goal & ring & ~inner & ~world().walls;
					if (!g2.is_empty())
						goal = g2;
					break;
				}
		}
		if (kit.ranged)
		{
			const bool spell_now = (d <= 4 && (ready(kit.cc) || ready(kit.dmg) || ready(kit.aoe))) || d <= aoe_r5;
			bool hold = false;
			if ((P.open_first & 2) && !spell_now && !danger.is_set(pos) && (ready(kit.cc) || ready(kit.dmg) || ready(kit.aoe)) && !e.channeling && !e.tributing)
			{
				// F3: a proactive approach with our opener ready: the next step enters an enemy's next-turn reach (area
				// casters 5 with aoe_reach5) and we cannot hit this turn (ranged lose the attack when walking, damage
				// spells are exclusive with walking). Hold at the edge: the side that steps in takes the first volley
				// (top vs us: the opener wins the first 3 rounds 391 to 58). At most open_hold rounds per fight.
				bool step_in = false;
				for (const auto& o : world().enemies)
				{
					if (!o.alive || !o.visible)
						continue;
					int r = o.kit.attack_range + (o.kit.ranged ? 0 : 1) + (o.ready(o.kit.dash) ? 2 : 0);
					r = std::max(r, P.aoe_reach5 ? enemy_spell_reach(o, false) : ((o.ready(o.kit.dmg) || o.ready(o.kit.cc) || o.ready(o.kit.aoe)) ? 4 : 0));
					// P.tp_timing: entering the reach of an enemy that acts again only after us is not a free volley for it
					step_in |= cheb(pos, o.pos) - 1 <= r && !(P.tp_timing && tp_we_first(o));
				}
				if (round - of_round > 1)
					of_since = round;
				of_round = round;
				hold = step_in && round - of_since < P.open_hold;
			}
			if (d <= kit.attack_range + 2 && ready(kit.dash))
			{
				strike_dash = true; // a strike dash (Heart of Ruin) lands next to the target: damage and a 1-turn stun
				step(goal, false, true), dbg_eng = 2;
				strike_dash = false;
			}
			else if (spell_now)
			{
				dbg_eng = 3;
				if (d > 4)
				{
					// F2: only the area reaches 5: aim so its radius catches the target (and as many others as possible)
					if (!cast_area_stun_at(e))
						step(goal, false, true), dbg_eng = 4;
					else
						return true;
				}
				else
				{
					if ((P.aoe_cast5 & 2) && ready(kit.aoe) && !kit.aoe_stuns && cast_area_n(e) >= 2 && cast_area_stun_at(e))
						return true; // F2: an area catching 2+ beats the single-target spell
					if (!cast_unit_champ(kit.cc, ec) && !cast_unit_champ(kit.dmg, ec))
					{
						if (P.aoe_cast5)
							cast_area_stun_at(e);
						else
							cast_ground(kit.aoe, e.pos);
					}
					return true;
				}
			}
			else if (hold)
			{
				dbg_eng = 9;
				return true;
			}
			else
			{
				step(goal, false, true), dbg_eng = 4;
				// F3: Cassi's stun is usable while walking: step in and open with it
				if ((P.open_first & 1) && kit.cc >= 0 && !kit.cc_excl && ready(kit.cc) && cheb(pos, e.pos) <= static_cast<int>(kit.cc_range) && e.type != CT::marcella)
					cast_unit_champ(kit.cc, ec);
			}
		}
		else
		{
			// Area stun (Ryth: walk-exclusive, radius 1): cast it before walking in. Walking first makes it
			// uncastable this turn, and next turn it competes with the attack reset (one cast per turn); stunning
			// now lands it a turn earlier and next turn is step + attack + reset + attack. The old check below only
			// knew single-target stuns: Ryth walked in with the stun ready in 279 fight turns of 3 traced games.
			if (P.hor_strike && kit.dash_mod > 0.f && strike_dash_at(e))
				dbg_eng = 8;
			else if (P.melee_aoe_stun && kit.aoe_stuns && d >= 2 && ready(kit.aoe) && e.type != CT::marcella && cast_area_stun_at(e))
				dbg_eng = 7;
			else if (P.tp_timing && d > 2 && !(d <= 4 && (ready(kit.cc) || ready(kit.dmg))) && [&] {
						 // P.tp_timing: the step does not reach the target this turn; hold one round (at most open_hold) when it would end
						 // inside the reach of an enemy that acts before our next turn
						 if (round - of_round > 1)
							 of_since = round;
						 of_round = round;
						 if (round - of_since >= P.open_hold)
							 return false;
						 for (const auto& o : world().enemies)
						 {
							 if (!o.alive || !o.visible)
								 continue;
							 const int r = o.kit.attack_range + (o.kit.ranged ? 0 : 1) + (o.ready(o.kit.dash) ? 2 : 0);
							 if (cheb(pos, o.pos) - 1 <= r && !tp_we_first(o))
								 return true;
						 }
						 return false;
					 }())
				dbg_eng = 10;
			else if (d == 2 || !(d <= 4 && (ready(kit.cc) || ready(kit.dmg))))
				step(goal, false, true), dbg_eng = 5;
			else if (!cast_unit_champ(kit.cc, ec))
				cast_unit_champ(kit.dmg, ec), dbg_eng = 6;
			else
				dbg_eng = 6;
		}
		d = cheb(pos, e.pos);
		// Melee can still swing after walking: when the step leaves the target out of reach, hit an enemy that is
		// in reach instead of wasting the attack (traced: Ryth ending next to Issac without swinging).
		if (P.step_hit_other && !kit.ranged && d > kit.attack_range && can_attack)
		{
			auto& W = world();
			for (auto& o : W.enemies)
			{
				if (&o == &e || !o.ch || !o.alive || !o.visible || cheb(pos, o.pos) > kit.attack_range || W.enemy_spawn.is_set(o.pos))
					continue;
				if (o.type == CT::ren && hp <= 2.5f * bc::constants::passive_abilities::ren_retaliation_focus_ratio * o.focus && o.hp > str)
					continue;
				if (attack_unit(*o.ch))
				{
					dbg_hit_other = true;
					std::int32_t alive_flag = 1;
					bc::detail::sdk_champion_is_alive(o.handle, &alive_flag);
					if (alive_flag && !cast_done && ready(kit.reset) && cast_self(kit.reset))
						attack_unit(*o.ch);
				}
				break;
			}
		}
	}
	if (d <= kit.attack_range)
	{
		dbg_eng += 10;
		// v8 (hor_strike 2): in contact the strike dash still lands. A dash to another tile within 2 that keeps the target in the
		// landing radius hits it (and every enemy next to the landing tile) for focus x dash_mod and stuns; melee attacks after the dash.
		if (P.hor_strike >= 2 && kit.dash_mod > 0.f && !cast_done && strike_dash_at(e))
			dbg_eng = 19, d = cheb(pos, e.pos);
		const bool want_stun = e.channeling || e.kit.ranged == false || P.px_mode && P.px_stun_first;
		if (want_stun)
			cast_unit_champ(kit.cc, ec);
		if (!cast_done && kit.enhanced_reset && ready(kit.reset))
			cast_self(kit.reset);
		if (!cast_done && kit.dmg >= 0 && focus * kit.dmg_mod > str)
			cast_unit_champ(kit.dmg, ec);
		if (!cast_done && kit.aoe >= 0 && kit.aoe_stuns)
			cast_ground(kit.aoe, e.pos);
		if (attack_unit(ec))
		{
			std::int32_t alive_flag = 1;
			bc::detail::sdk_champion_is_alive(e.handle, &alive_flag);
			if (alive_flag && !cast_done && ready(kit.reset) && cast_self(kit.reset))
				attack_unit(ec);
		}
		if (!cast_done)
			cast_unit_champ(kit.cc, ec) || cast_unit_champ(kit.dmg, ec) || cast_ground(kit.aoe, e.pos);
	}
	return true;
}

// ---------------------------------------------------------------------------------------------- safety, tribute, shopping

bool Brain::go_home()
{
	auto& W = world();
	task = T_HOME;
	if (W.ally_spawn.is_set(pos))
		return true;
	const int dh = W.dist_home(pos);
	if (P.pocket_fix && dh >= BIG && !flag(state, bc::champion_state::recalling))
	{
		// pocket_fix: no walk leads home from here: dash out, else recall even with an enemy about (a cancelled recall costs a turn,
		// standing here costs every turn).
		if (pocket_dash())
			return true;
		try
		{
			bc::self().recall();
			return true;
		}
		catch (...)
		{
		}
	}
	if (dh > P.recall_min_dist && safe_to_recall())
	{
		if (P.no_split && can_move)
		{
			// Recalling from a reward tile while an ally stands on the group too: the channel keeps us on the tile and the
			// reward is split (pilgrimage: a hurt Varg recalled from the wolf tiles next to Cassi, 34/34). Step off first.
			for (const auto& g : W.groups)
			{
				if (cheb(g.center, pos) > g.radius + 1 || !g.mask.is_set(pos))
					continue;
				bool other = false;
				for (int i = 0; i < static_cast<int>(W.allies.size()) && !other; ++i)
				{
					const auto& a = W.allies[static_cast<std::size_t>(i)];
					other = i != W.my_index && a.alive && a.visible && a.seen_round == round && cheb(a.pos, g.center) <= g.radius + 1;
				}
				if (other)
				{
					bc::bitboard off;
					off.draw_chebyshev(pos, 1.f);
					off &= ~g.mask;
					off &= ~W.walls;
					if (!off.is_empty())
						step(off, false, false);
				}
				break;
			}
		}
		try
		{
			bc::self().recall();
			return true;
		}
		catch (...)
		{
		}
	}
	go_home_step(true);
	return true;
}

void Brain::update_priority()
{
	// Turn order (verified on 14,069 ladder rounds): team A leads odd rounds, team B even rounds; teams
	// alternate turns; within a team higher priority acts first; set_priority applies from the next round.
	// A fighter that acts last in a round we trail and first in the next round we lead gets two actions in
	// a row with no enemy turn between them. So fighters alternate: high when we lead the next round, low
	// when we trail it. Escapers move first. (57.6% vs the previous bot in mirror tests, -14% deaths.)
	int prio = P.prio_idle;
	if (!P.prio_alternate)
	{
		// Previous scheme: engaged champions simply act first.
		if (engaged || task == T_FIGHT || task == T_FLEE)
			prio = 8 + ((kit.cc >= 0 || kit.aoe_stuns) ? 1 : 0) + (hp < 0.35f * max_hp ? 1 : 0);
		else if (task == T_CAPTURE)
			prio = P.prio_capture;
	}
	else if (task == T_FLEE)
		prio = P.prio_flee;
	else if (engaged || task == T_FIGHT)
	{
		const bool team_a = bc::detail::sdk_my_team() == 0;
		const bool lead_next = (((round + 1) & 1) == 1) == team_a;
		const int bonus = ((kit.cc >= 0 || kit.aoe_stuns) ? 1 : 0) + (hp < 0.35f * max_hp ? 1 : 0);
		prio = lead_next ? P.prio_fight + bonus : -P.prio_fight + bonus;
	}
	else if (task == T_CAPTURE)
		prio = P.prio_capture;
	if (P.v23_msg)
		prio = prio * 4096 + v23_payload(); // v23 4.9: hp, state, target and flags under the turn class (x4096 keeps the order)
	else if (P.g22_msg)
	{
		// v22 g22_msg: the low 6 bits carry this body's fight state for allies who see it (query_priority); x64 keeps the turn order.
		const int flags = (task == T_FIGHT || (engaged && last_fight_round == round) ? 1 : 0) | (task == T_FLEE ? 2 : 0);
		prio = prio * 64 + flags;
	}
	if (prio == cur_prio)
		return;
	try
	{
		bc::self().set_priority(prio);
		cur_prio = prio;
	}
	catch (...)
	{
	}
}

bool Brain::escort_wait()
{
	// After a wipe, champions that walk out one at a time meet their pack one at a time. A freshly respawned
	// champion holds on spawn (healing, shopping) while we are down by deficit_escort or more bodies and
	// an ally respawns soon, then they leave together.
	auto& W = world();
	if (deficit < P.deficit_escort || !W.ally_spawn.is_set(pos) || round - respawn_round > P.escort_wait || enemies_within(9) > 0 || round < pw_off_until)
		return false;
	for (const auto& a : W.allies)
		if (a.handle != self && a.alive && a.visible && cheb(a.pos, pos) <= 4)
			return false; // someone to walk with
	const int respawn = static_cast<int>(bc::constants::respawn_time);
	for (const auto& a : W.allies)
		if (!a.alive && a.died_round > -1000 && a.died_round + respawn - round <= P.escort_wait)
		{
			task = T_WAIT;
			return true;
		}
	return false;
}

// Lone-monolith maps (agent ct): a pack that outnumbers the bodies it meets one at a time wins every skirmish (contest vs the sneaky-bush
// proxy: 90 deaths to 8). On spawn a body heals 100% per round, so the team falls back there together and fights where it cannot lose a body to attrition.
bool Brain::regroup_active()
{
	auto& W = world();
	auto& C = comms();
	if (!P.mono_rg || !W.mono_mode || round < P.mono_rg_from)
		return false;
	int n_en = 0, n_al = 1;
	for (const auto& e : W.enemies)
		if (e.alive && e.visible && cheb(e.pos, pos) <= P.mono_rg_see && !W.enemy_spawn.is_set(e.pos))
			++n_en;
	for (const auto& a : W.allies)
		if (a.handle != self && a.alive && a.visible && cheb(a.pos, pos) <= 8)
			++n_al;
	if (n_en >= P.mono_rg_n && n_en > n_al + P.mono_rg_margin)
	{
		rg_until = round + P.mono_rg_hold;
		if (P.mono_rg_team && !(C.fresh(round, 6) && (C.alert_kind == AL_RALLY || C.alert_kind == AL_OPPORTUNITY)))
			C.post(AL_DANGER, pos, round);
	}
	else if (P.mono_rg_team && C.alert_kind == AL_DANGER && C.fresh(round, P.mono_rg_hold))
		rg_until = std::max(rg_until, C.alert_round + P.mono_rg_hold);
	return round < rg_until;
}

bool Brain::altar_unsafe(int i) const
{
	auto& W = world();
	if (!W.contested(i) || round - W.altar_enemy_round[static_cast<std::size_t>(i)] > P.altar_enemy_memory)
		return false;
	// An ally standing by makes it a two-body bank.
	for (const auto& a : W.allies)
		if (a.handle != self && a.alive && a.visible && cheb(a.pos, W.altars[static_cast<std::size_t>(i)]) <= 5)
			return false;
	return true;
}

bool Brain::bag_needs_escort(int i) const
{
	auto& W = world();
	const int eb = P.opp_model ? escort_bag_now : P.escort_bag;
	if (eb <= 0 || static_cast<int>(gems) < eb)
		return false;
	const vec2 at = W.altars[static_cast<std::size_t>(i)];
	bool hot = round - W.altar_enemy_round[static_cast<std::size_t>(i)] <= P.escort_quiet;
	for (const auto& e : W.enemies)
		hot |= e.alive && e.visible && cheb(e.pos, at) <= 10;
	if (!hot)
		return false;
	int living = 0, near = 0;
	for (const auto& a : W.allies)
	{
		if (a.handle == self || !a.alive)
			continue;
		++living;
		near += a.visible && !a.channeling && a.hp >= 0.5f * a.max_hp && cheb(a.pos, at) <= 5;
	}
	return near < std::min(2, living);
}

bool Brain::safe_to_recall() const
{
	// Any damage cancels a recall: no awake camp in range and no enemy that could reach us during the channel.
	if (in_awake_camp_range() || danger.is_set(pos))
		return false;
	for (const auto& e : world().enemies)
		if (e.alive && e.seen_round >= 0 && round - e.seen_round <= 2 && cheb(e.pos, pos) <= 7 + static_cast<int>(dl_val(dl_chan, dl_chan_r)))
			return false;
	return true;
}

bool Brain::home_trip()
{
	// A trip home heals fully and turns gold into shards; recall (5 turn ends) makes it cheap from far away.
	// Strong teams recall right after captures to heal, shop and bank near spawn instead of walking.
	auto& W = world();
	if (task == T_CAPTURE || reward_here() || W.ally_spawn.is_set(pos))
		return false;
	const int dh = W.dist_home(pos);
	// Within two steps of spawn the trip is almost free, so it is not skipped there: skipping it let farm()
	// walk a hurt champion back out, and at three steps this check sent it home again, a farm/home flip-flop
	// that held bodies at the spawn edge for hundreds of rounds (63% of all turns on the 30x80 ladder map).
	if (dh >= BIG || dh <= (P.home_edge_fix ? 0 : 2))
		return false;
	const bool can_recall = dh > P.recall_min_dist && safe_to_recall();
	const int cost = can_recall ? recall_turns() : dh;
	const bool shopper = type != CT::tavi && build_idx < build.size();
	const int shards = shopper ? static_cast<int>(gold / 30) : 0;
	const bool hurt = hp < P.home_hp * max_hp;
	bool go = false;
	if (P.v23_shop)
	{
		// v23 4.7 shop cadence (Mite: 67 shop visits a game, v75 39): with 90+ gold, go when hurt, close to spawn or rich; low health
		// with little gold still heals when spawn is close.
		const bool g = shopper && static_cast<int>(gold) >= P.v23_shop_gold;
		go = (g && (hp < 0.5f * max_hp || dh <= P.v23_shop_near || static_cast<int>(gold) >= P.v23_shop_rich)) || (hurt && cost <= 6);
		if (!go)
			return false;
		return go_home();
	}
	if (shards >= P.shop_shards && cost <= P.shop_cost_max)
		go = true; // a batch of shards is waiting
	else if (hurt && (shards >= 2 || cost <= 6))
		go = true; // low anyway: heal now and spend what we have
	else if (round - last_bank_round <= 1 && can_recall && dh > P.cap_recall_min_home &&
		(hp < P.cap_recall_hp * max_hp || shards >= 3))
		go = true; // just banked far from home: recall to heal and shop instead of walking on hurt
	if (!go)
		return false;
	return go_home();
}

bool Brain::safety()
{
	// Incoming camp damage per round: each camp hits the nearest champion in its range 3, so a camp with a
	// visible ally strictly nearer to it does not hit us (a tank in front shields the ranged behind it).
	// Keep enough health to walk out of range (escape steps) plus a margin.
	auto& W = world();
	float camp_in = 0, obj_in = 0;
	int escape = 0, obj_escape = 0;
	for (const auto& g : W.groups)
		if (g.st == ST_ALIVE && g.awake && !g.harmless && g.near.is_set(pos))
		{
			// Only while no enemy is near: with enemies around the old line stays (gold_mono_48 vs _k1: the two
			// monoliths are 9 tiles apart; 20 of our 33 deaths were next to ours and they took 2 of our 3 kills).
			const bool team_g = (W.obj_mode && g.objective) || (task_team && g.id == task_group && ((P.altar_no_camp >= 2 && g.unlock) || (P.mono_team && mono_group(g))));
			const bool obj = P.obj_shield && team_g && enemy_near_d > P.obj_shield_enemy_d;
			for (std::size_t i = 0; i < g.camps.size(); ++i)
			{
				const int d = cheb(g.camps[i].pos, pos);
				// v9 safety_range: patch 3.0 camps reach 4 (elk, golem) and 5 (monolith); the literal 3 left a body at 4-5 tiles
				// from an elk counting none of its hits (g.near, which gates this loop, already uses the engine range).
				const int rng = P.safety_range ? std::max(3, g.camps[i].range) : 3;
				if (g.hp[i] <= 0 || d > rng)
					continue;
				bool shielded = false;
				for (const auto& a : W.allies)
					if (P.safety_v2 || obj)
					if (a.handle != self && a.alive && a.visible && cheb(a.pos, g.camps[i].pos) < d)
					{
						shielded = true;
						break;
					}
				if (shielded)
					continue;
				if (obj)
				{
					obj_in += g.camps[i].str;
					obj_escape = std::max(obj_escape, rng + 1 - d);
					continue;
				}
				camp_in += g.camps[i].str;
				escape = std::max(escape, rng + 1 - d);
			}
		}
	// P.pair_retreat_hp: Cassi & Issac walk home from camps earlier (a body caught low by an enemy kills both bodies).
	const float base_rhp = P.mi_body && mig::retreat_pct() > 0 ? 0.01f * static_cast<float>(mig::retreat_pct()) : P.retreat_hp; // GOD v12: BODY's
	const float rhp = ((type == CT::cassi || type == CT::issac) ? std::max(base_rhp, P.pair_retreat_hp) : base_rhp) + dl_val(dl_camp, dl_camp_r);
	float threshold = std::max(rhp * max_hp, camp_in * static_cast<float>(P.safety_v2 ? escape + 1 : 4));
	if (obj_in > 0)
	{
		// Objective camps: only those that target us (no ally nearer), after our emblems, for the steps out of
		// reach plus one. Four rounds of every elk in reach (stampede: 6 x 60) exceeded Stellar's whole health
		// (975 at r540), so the ranged bodies stepped in and out of range without a shot.
		float eff = obj_in * (jungle_done() ? 0.7f : 1.f) * (durability_done() ? 0.9f : 1.f);
		threshold = std::max(threshold, eff * static_cast<float>(obj_escape + 1));
		camp_in += obj_in;
	}
	if (P.burst_retreat > 0.f && !W.ally_spawn.is_set(pos) && !(P.v23_fe && !P.v23_fe_retreat)) // v23: kept for hurt bodies (v23_fe_retreat)
	{
		float eb = 0;
		for (const auto& e : W.enemies)
			if (e.alive && e.visible && !W.enemy_spawn.is_set(e.pos) && !((calm_bits & 2) && !g15_is_threat(e)))
			{
				const int reach = std::max(e.kit.attack_range + (e.kit.ranged ? 0 : 1), enemy_spell_reach(e, false));
				const int d = cheb(e.pos, pos);
				if (d <= reach + 2)
					eb += e.str + e.burst();
				if ((P.hor_threat & 2) && e.kit.dash_mod > 0.f && e.ready(e.kit.dash) && d <= static_cast<int>(e.kit.dash_range + e.kit.dash_radius) + 1)
					eb += e.focus * e.kit.dash_mod;
				else if (P.burst_far > 0.f && d <= reach + P.burst_far_d)
					eb += P.burst_far * (e.str + e.burst()); // burst_far: the ones one or two steps from reach
			}
		threshold = std::max(threshold, P.burst_retreat * (1.f + dl_val(dl_burst, dl_burst_r)) * eb);
	}
	if (hp < threshold && P.finish_camp && camp_in > 0 && enemy_near_d > P.finish_enemy_d && task_group >= 0 &&
		task_group < static_cast<int>(W.groups.size()))
	{
		// The group we farm is nearly dead: finishing it costs at most camp_in per round until it dies (camps
		// die one by one, so less), then the capture is free (dead camps do not hit). Retreating instead walks
		// home and back for the last few hits (camps never heal, but the trip costs ~2x the walk).
		const auto& g = W.groups[static_cast<std::size_t>(task_group)];
		if (g.st == ST_ALIVE && g.near.is_set(pos))
		{
			const float kill = std::ceil(g.hp_total / std::max(10.f, dps_on(g)));
			const float left = hp - camp_in * kill;
			if (kill <= static_cast<float>(P.finish_rounds) && left >= std::max(camp_in, P.finish_hp_floor * max_hp))
				threshold = 0;
		}
	}
	// A reward waiting next to us (or a capture under way) is safe from camps: dead camps do not hit, and the
	// capture can recall home with the reward. Walking home first left rewards to expire (contest: 6 of 91
	// rewards waited 46 rounds, the expiry, tools/analysis/rewards.mjs).
	if (hp < threshold && P.capture_before_retreat && camp_in <= 0 && enemy_near_d > P.finish_enemy_d && (task == T_CAPTURE || reward_here()))
		threshold = 0;
	if (hp < threshold && P.win_bank && camp_in <= 0 && enemy_near_d > P.finish_enemy_d && gems > 0 && wins_with(static_cast<int>(gems)))
		threshold = 0; // the bag wins the game: tribute() banks it before anything else
	if (P.v25_heal_latch && heal_latch && hp >= threshold)
	{
		// v25: after a retreat from camp damage, no walking straight back into the camps at low health (the step-out / step-in tease):
		// heal first, unless health is back above v25_heal_hp or we stand on our spawn.
		if (hp >= P.v25_heal_hp * max_hp || W.ally_spawn.is_set(pos) || reward_here() || task == T_CAPTURE)
			heal_latch = false;
		else if (enemy_near_d > P.finish_enemy_d)
			return go_home();
	}
	if (hp >= threshold)
	{
		// On spawn, health is restored only after a turn ends there: after a recall or a walk home, rest one
		// turn before leaving (unless an enemy keeps hitting us, as on maps where the spawns touch).
		if (P.rest_on_spawn && W.ally_spawn.is_set(pos) && hp < 0.95f * max_hp && round - last_hit_round > 1 && enemies_within(6) == 0)
		{
			task = T_HOME;
			return true;
		}
		return false;
	}
#ifdef LEGEND_TRACE
	debug_block({ if (W.obj_mode) std::printf("SF r=%d %d hp=%.0f/%.0f thr=%.0f camp_in=%.0f obj_in=%.0f\n", round, static_cast<int>(type), hp, max_hp, threshold, camp_in, obj_in); });
#endif
	if (P.v25_heal_latch && camp_in > 0 && enemy_near_d > P.finish_enemy_d)
		heal_latch = true; // v25: a retreat forced by camp damage: heal before the next camp (see above)
	if (in_awake_camp_range() && camp_in > 0)
	{
		task = T_FLEE;
		const bc::bitboard out = ~camp_danger;
		if (step(out, true, true))
			return true;
	}
	return go_home();
}

void Brain::update_anchors()
{
	// F4: the order is a function of the team's champion types, so every body computes the same one; the top n living bodies anchor.
	auto& W = world();
	if (anchor_order.empty())
	{
		std::vector<std::pair<float, int>> r;
		for (int i = 0; i < static_cast<int>(W.allies.size()); ++i)
		{
			const auto t = W.allies[static_cast<std::size_t>(i)].type;
			const float pri = t == CT::vesper_vale ? 3.f : t == CT::marcella ? 2.f : t == CT::prism ? 1.f : 0.f;
			const auto ti = static_cast<std::size_t>(t);
			const float bh = ti < bc::champion_designs.size() ? static_cast<float>(bc::champion_designs[ti].base_stats().base_health) : 1000.f;
			r.push_back({ -1e5f * pri + bh + 0.001f * static_cast<float>(i), i });
		}
		std::sort(r.begin(), r.end());
		for (const auto& x : r)
			anchor_order.push_back(x.second);
	}
	const int n = P.anchors == 3 ? (W.team_champs <= 3 ? 1 : 2) : std::clamp(P.anchors, 0, 2);
	anchor_now.fill(false);
	is_anchor = false, anchor_rank = -1;
	int k = 0;
	for (int i : anchor_order)
	{
		if (k >= n)
			break;
		if (!W.allies[static_cast<std::size_t>(i)].alive)
			continue;
		if (i < 8)
			anchor_now[static_cast<std::size_t>(i)] = true;
		if (i == W.my_index)
			is_anchor = true, anchor_rank = k;
		++k;
	}
	anchor_altar = -1;
	if (is_anchor)
	{
		// Our-half altars by walking distance from our spawn; anchor k keeps to altar k (two anchors, two altars when there are two).
		std::vector<std::pair<int, int>> al;
		for (std::size_t i = 0; i < W.altars.size(); ++i)
			if (altar_ours(i))
			{
				int dh = BIG;
				for (const auto t : W.altar_approach[i])
					dh = std::min(dh, W.dist_home(t));
				al.push_back({ dh, static_cast<int>(i) });
			}
		std::sort(al.begin(), al.end());
		if (!al.empty())
			anchor_altar = al[static_cast<std::size_t>(anchor_rank) % al.size()].second;
	}
}

void Brain::update_mode()
{
	fight_margin = P.fight_margin;
	fight_back_margin = P.fight_back_margin;
	deny_bonus = P.deny_bonus;
	enemy_half_penalty = P.enemy_half_penalty;
	tribute_min = P.tribute_min;
	if (P.mi_body && mig::bank_bag() > 0)
		tribute_min = mig::bank_bag(); // GOD v12: the BODY block's bank bag (econ model, LEARNED)
	if (round < P.early_round)
		tribute_min = std::min(tribute_min, P.early_tribute_min); // bank small and early: gold and safety
	stance = comms().stance;
	if (P.opp_model)
	{
		// Every addition of the opponent model sits behind its constexpr switch, so the build without it has the same instructions in
		// the hot paths (fuel-floored scoring makes even a few extra instructions change which groups get scored).
		escort_bag_now = P.escort_bag, group_r_now = P.group_radius, ward_bush_now = -1, role_guard = role_hunter = false;
		plan_now = comms().plan;
		if (plan_now >= PLAN_INVADER)
			stance = preset_of(plan_now).stance; // a counter plan brings its own stance
	}
	if (P.opp_plan && !P.opp_model)
	{
		// v9: the team plan (broadcast by the leader) may force the stance; its numeric preset is applied at the end of update_mode().
		plan9_now = P.opp_presets ? comms().plan9 : PL_FARM;
		rally_add = opp_add = 0;
		locks_contested = false;
		if (plan9_now != PL_FARM && preset9_of(plan9_now).stance >= 0)
			stance = preset9_of(plan9_now).stance;
	}
	if (P.spar_to > P.spar_from && sparring_window())
		stance = STANCE_PUSH; // v9 sparring persona (test opponents only): an invasion window
	if (P.mono_grouped_until > 0 && world().mono_mode && round < P.mono_grouped_until)
		stance = STANCE_GROUPED; // lone-monolith maps: the first contact is a team wipe for whoever arrives piecemeal
	isolated_fight_adv = P.isolated_fight_adv + dl_val(dl_iso, dl_iso_r);
	mono_forced = P.mono_grouped_until > 0 && world().mono_mode && round < P.mono_grouped_until;
	if (stance == STANCE_GROUPED)
	{
		// Being invaded: stay together and off their half, demand more before fighting alone.
		const int gm = mono_forced ? P.mono_gmask : 15;
		if (gm & 1)
			enemy_half_penalty *= 2.f;
		if (gm & 2)
			deny_bonus *= 0.5f;
		if (gm & 4)
			isolated_fight_adv += 0.3f;
	}
	else if (stance == STANCE_PUSH)
	{
		// Winning fights: take their camps and more fights.
		enemy_half_penalty *= 0.4f;
		deny_bonus += 0.4f;
		fight_margin = std::max(1.0f, fight_margin - 0.2f);
	}
	if (P.opp_model)
	{
		// Counter plan (opponent.h): the preset's directions x the plan's magnitude, on top of the stance; deficit, learned fight record
		// and the race below still apply after it.
		const auto& pr = preset_of(plan_now);
		const float k = plan_now == PLAN_INVADER ? P.om_k_invader : plan_now == PLAN_DEATHBALL ? P.om_k_deathball : plan_now == PLAN_OBJECTIVE ? P.om_k_objective :
			plan_now == PLAN_ALTAR ? P.om_k_altar : plan_now == PLAN_AMBUSH ? P.om_k_ambush : 0.f;
		if (k > 0.f)
		{
			fight_margin += k * pr.dfm;
			enemy_half_penalty *= std::pow(pr.ehp, k);
			deny_bonus = std::max(0.f, deny_bonus + k * pr.ddeny);
			tribute_min = std::max(10, static_cast<int>(static_cast<float>(tribute_min) * std::pow(pr.trib, k)));
			isolated_fight_adv += k * pr.diso;
			if (P.escort_bag > 0)
				escort_bag_now = std::max(10, static_cast<int>(static_cast<float>(P.escort_bag) * std::pow(pr.esc, k)));
			group_r_now = std::max(4, static_cast<int>(static_cast<float>(P.group_radius) * std::pow(pr.grp, k)));
			if (pr.ward_bush)
				ward_bush_now = 2;
			role_guard = pr.guard;
		}
		role_hunter = pr.hunter;
	}
	// Numbers: fewer of us alive than of them means their pack meets our singles. Play defensively.
	{
		auto& W = world();
		int us = 0, them = 0;
		for (const auto& a : W.allies)
			us += a.alive;
		for (const auto& e : W.enemies)
			them += e.alive;
		deficit = them - us;
		if (deficit >= P.deficit_defend)
		{
			enemy_half_penalty *= 3.f;
			deny_bonus = 0.f;
			fight_margin += 0.4f;
			isolated_fight_adv += 0.3f;
		}
		if (P.mi_learn_fight > 0)
		{
			// Fight record (default branch): losing exchanges -> engage less and stay off their half; winning -> press.
			const float p = (static_cast<float>(W.enemy_deaths) + 3.f) / (static_cast<float>(W.enemy_deaths + W.ally_deaths) + 6.f);
			const float caution = std::clamp(1.f + (0.5f - p) * P.mi_learn_fight, 0.8f, 1.4f);
			fight_margin *= caution;
			enemy_half_penalty *= caution * caution;
			deny_bonus *= std::clamp(2.f * p, 0.5f, 1.4f);
		}
	}
	const int ours = static_cast<int>(bc::global_submitted_gems(team::ally));
	const int theirs = static_cast<int>(bc::global_submitted_gems(team::enemy));
	if (gv_base < 0.f)
	{
		gv_base = P.gold_value;
		float sg = 0, sm = 0;
		for (const auto& g : world().groups)
			if (g.respawn > 0)
				sg += static_cast<float>(g.gold) / static_cast<float>(g.respawn), sm += static_cast<float>(g.gems) / static_cast<float>(g.respawn);
		const float rho = sm > 0.f ? sg / sm : 10.f;
		if (P.gv_map)
			gv_base = std::clamp(P.gold_value * std::pow(std::max(0.01f, rho) / P.gv_rho_ref, P.gv_exp), 0.15f, 0.5f);
		// v28_scarce: the whole map cannot pay the winning score in a game, so it ends on the gem tiebreak and every gem counts: a gem group outranks the gold groups
		// (03one-gem: 1 gem camp, 80 gold camps, 605 of 694 ladder games on the gem tiebreak; we took the 8-gem group 3 times in 2,000 rounds).
		if (P.v28_scarce && sm * static_cast<float>(static_cast<int>(bc::constants::max_rounds)) < static_cast<float>(static_cast<int>(bc::constants::winning_gems)))
			gv_base = std::min(gv_base, P.v28_scarce_gv);
#ifdef GV_TRACE
		debug_block({ std::printf("GV rho=%.2f gv=%.3f groups=%d\n", rho, gv_base, static_cast<int>(world().groups.size())); });
#endif
	}
	gold_v = gv_base;
	if (P.math_gold && !(P.no_altar_gold && world().no_altar_now()))
	{
		// Gold only turns into gems through the shards it buys, and a shard pays off over the rounds left: +5
		// strength on 40-50 is about +5% farming rate, which earns back 30 gold x gold_value = 6.6 gems in
		// ~gold_horizon rounds. Rounds left: the leading team's time to the winning score at its average pace so
		// far (an underestimate of its pace, so this errs toward valuing gold), capped by the round limit.
		// In the 48 audit games 20% of all gold was earned after a team passed 800 and ~485 gold per team
		// was never spent.
		const int lead_g = std::max(ours, theirs);
		float left = static_cast<float>(static_cast<int>(bc::constants::max_rounds) - round);
		if (lead_g > 0 && round > 0)
			left = std::min(left, static_cast<float>(static_cast<int>(bc::constants::winning_gems) - lead_g) * static_cast<float>(round) / static_cast<float>(lead_g));
		gold_v = gv_base * std::clamp(left / std::max(1.f, P.gold_horizon), 0.f, 1.f);
	}
	if (P.v23_open_gold < 1.f && round < P.v23_open_until)
		gold_v *= P.v23_open_gold; // v23 opening race: Mite / IC walk to the gem clusters first (anvil r15 vs our r57); gold clusters by our spawn wait
	if (ours - theirs >= P.lead)
	{
		// Ahead: protect the lead. Bank smaller bags, take only clearly winning fights.
		fight_margin += 0.3f;
		tribute_min = std::max(16, tribute_min * 3 / 4);
	}
	else if (theirs >= P.desperate_at && theirs - ours >= P.lead / 2)
	{
		// They are close to winning: steal, hunt carriers, accept closer fights.
		fight_margin = std::max(0.9f, fight_margin - 0.3f);
		fight_back_margin = std::max(0.55f, fight_back_margin - 0.15f);
		deny_bonus += 0.6f;
		enemy_half_penalty *= 0.4f;
	}
	if (P.mi_endgame_bank > 0)
	{
		// Near the end only banked gems count (default branch): bank smaller bags the closer either team is to winning.
		const int top = std::max(ours, theirs);
		const int goal = static_cast<int>(bc::constants::winning_gems);
		if (top >= goal - P.mi_endgame_bank)
			tribute_min = std::max(1, std::min(tribute_min, tribute_min * (goal - top) / P.mi_endgame_bank));
	}
	race_state = 0;
	if (P.race_mode)
	{
		// Who wins the gem race if nothing changes? Each team's banking rate over the last ~200 rounds projects its
		// finish; our side also counts the team's carried bags (P.team_bank sum). Behind by more than race_margin
		// rounds: if our fights go well (as many enemy deaths as ours, not outnumbered now) take gems from them
		// (their camps, their carriers); otherwise farming faster is the only way, so gold stops being worth
		// detours (it cannot pay back before they finish).
		auto& W = world();
		if (round % P.race_sample == 0 && (race_n == 0 || race_r[static_cast<std::size_t>((race_n - 1) % 8)] != round))
		{
			const std::size_t k = static_cast<std::size_t>(race_n % 8);
			race_r[k] = round, race_us[k] = ours, race_them[k] = theirs;
			++race_n;
		}
		if (race_n >= 4 && round >= P.race_from)
		{
			const std::size_t old_k = static_cast<std::size_t>(race_n >= 8 ? race_n % 8 : 0);
			const float span = static_cast<float>(std::max(1, round - race_r[old_k]));
			const float rate_us = std::max(0.05f, static_cast<float>(ours - race_us[old_k]) / span);
			const float rate_them = std::max(0.05f, static_cast<float>(theirs - race_them[old_k]) / span);
			const int carried = static_cast<int>(gems) + (P.team_bank ? comms().others_carried() : 0);
			const float t_us = static_cast<float>(std::max(0, static_cast<int>(bc::constants::winning_gems) - ours - carried)) / rate_us;
			const float t_them = static_cast<float>(std::max(0, static_cast<int>(bc::constants::winning_gems) - theirs)) / rate_them;
			const bool they_finish = static_cast<float>(round) + t_them < static_cast<float>(bc::constants::max_rounds);
			if (P.mi_learn_race && round > P.mi_race_after)
			{
				// Learned race (default branch), on banked gems only: losing it by a clear margin -> farming harder will not
				// catch up, take their gems; winning it -> no need for even fights.
				const float eo = static_cast<float>(std::max(0, static_cast<int>(bc::constants::winning_gems) - ours)) / rate_us;
				const float et = static_cast<float>(std::max(0, static_cast<int>(bc::constants::winning_gems) - theirs)) / rate_them;
				if (et < P.mi_race_ratio * eo)
				{
					deny_bonus += 0.4f;
					enemy_half_penalty *= 0.6f;
				}
				else if (eo < P.mi_race_ratio * et)
					fight_margin += 0.15f;
			}
			if (they_finish && t_them + static_cast<float>(P.race_margin) < t_us)
			{
				const bool fights_ok = W.enemy_deaths + P.race_death_slack >= W.ally_deaths && deficit <= 0;
				race_state = fights_ok ? 1 : 2;
				gold_v *= P.race_gold;
				if (fights_ok)
				{
					deny_bonus += P.race_deny;
					enemy_half_penalty *= P.race_half;
					fight_margin = std::max(1.0f, fight_margin - P.race_fight);
				}
			}
		}
	}
	if (type == CT::cassi || type == CT::issac)
	{
		fight_margin += P.pair_caution;
		isolated_fight_adv += P.pair_caution;
	}
	if (P.anchors)
	{
		update_anchors();
		bag_caution_now = is_anchor ? P.anchor_bag_caution : P.bag_caution;
		if (is_anchor)
		{
			tribute_min = std::max(10, static_cast<int>(static_cast<float>(tribute_min) * P.anchor_trib));
			enemy_half_penalty *= P.anchor_ehp;
		}
	}
	if (P.pxs_style)
	{
		// Sparring proxy styles (testing only): strong, fixed settings on top of everything else.
		const int s = style_now();
		if (s == 1)
		{
			enemy_half_penalty *= 8.f;
			fight_margin += 0.6f;
			deny_bonus = 0.f;
			isolated_fight_adv += 0.5f;
		}
		else if (s == 2 || s == 3)
		{
			enemy_half_penalty *= 0.1f;
			deny_bonus += 0.8f;
			fight_margin = std::max(0.9f, fight_margin - 0.3f);
		}
		else if (s == 4)
			enemy_half_penalty *= 0.5f;
	}
	if (P.opp_plan && !P.opp_model && plan9_now != PL_FARM)
	{
		// v9 preset: one coherent set of changes per opponent plan, on top of the stance / scoreboard / race modifiers above.
		const Preset9& pr = preset9_of(plan9_now);
		fight_margin = std::max(0.9f, fight_margin + pr.fight_add);
		fight_back_margin = std::max(0.55f, fight_back_margin + pr.fight_back_add);
		enemy_half_penalty *= pr.half_mult;
		deny_bonus = std::max(0.f, deny_bonus + pr.deny_add);
		isolated_fight_adv = std::max(1.f, isolated_fight_adv + pr.iso_add);
		tribute_min = std::max(10, static_cast<int>(static_cast<float>(tribute_min) * pr.bank_mult));
		gold_v *= pr.gold_mult;
		rally_add = pr.rally_add;
		opp_add = pr.opp_add;
		locks_contested = pr.locks_contested != 0;
	}
	if (P.spar_to > P.spar_from && sparring_window())
	{
		// v9 sparring persona: a copy of the bot with spar_from / spar_to set plays a mid-match switcher for the A/B pool.
		enemy_half_penalty *= P.spar_half;
		deny_bonus += P.spar_deny;
		fight_margin = std::max(0.9f, fight_margin + P.spar_fight);
	}
	if (P.g16_camp && round >= P.g16_hunt_from && g16_rank() < P.g16_hunt_bodies && !(P.g16_gate && world().ally_deaths > world().enemy_deaths + P.g16_gate_margin)
		&& (!P.g16_only_camp || (g16_rank() == 0 && round - g16_camp_start <= P.g16_camp_hold)))
	{
		// v16 hunters: bolder fights at their altar and their spawn
		fight_margin = std::max(0.9f, fight_margin * P.g16_fight_k);
		isolated_fight_adv = std::max(1.f, isolated_fight_adv * P.g16_fight_k);
	}
	if (P.tp_bag)
		fight_margin = static_cast<float>(teamplan::fight_bar(fight_margin, static_cast<int>(gems), tpa::params()));
	if (P.tp_tiebreak)
		teamplan::tb_update(tp_tb_, round, static_cast<int>(bc::global_submitted_gems(team::ally)), static_cast<int>(bc::global_submitted_gems(team::enemy)),
							static_cast<int>(gems) + (P.team_bank ? comms().others_carried() : 0), 0, tpa::consts(), tpa::params());
}

float Brain::tp_target_value(const Enemy& e, float eff_hp) const
{
	int n = 0;
	for (const auto& o : world().enemies)
		n += o.alive ? 1 : 0;
	const double kv = teamplan::kill_value(static_cast<int>(e.gems), tpa::bodies_of_type(static_cast<int>(e.type)), std::max(1, n), tpa::consts(), tpa::params());
	return static_cast<float>(kv) / eff_hp;
}

bool Brain::tp_we_first(const Enemy& e) const
{
	// timing.h on the bodies in sight: ranks by this round's priority (prev_priority) for this round and by next round's for the next;
	// bodies out of sight are taken to act after the ones we see (they are far from the fight).
	const int team = bc::detail::sdk_my_team() == 0 ? 0 : 1;
	int us_now = 0, us_next = 0, e_now = 0, e_next = 0, n_ours = 0, n_theirs = 0;
	int my_now = 0, my_next = 0, en_now = 0, en_next = 0;
	try
	{
		const auto& me = bc::self();
		my_now = me.prev_priority(), my_next = me.priority();
		if (!e.ch)
			return false;
		en_now = e.ch->prev_priority(), en_next = e.ch->priority();
	}
	catch (...)
	{
		return false;
	}
	const int my_t = static_cast<int>(type), e_t = static_cast<int>(e.type);
	for (const auto& c : bc::champions(team::ally))
	{
		++n_ours;
		try
		{
			const int t = static_cast<int>(c.champion_name());
			if (t == my_t)
				continue;
			const int pn = c.prev_priority(), px = c.priority();
			us_now += pn > my_now || (pn == my_now && t < my_t) ? 1 : 0;
			us_next += px > my_next || (px == my_next && t < my_t) ? 1 : 0;
		}
		catch (...)
		{
		}
	}
	for (const auto& c : bc::champions(team::enemy))
	{
		++n_theirs;
		try
		{
			const int t = static_cast<int>(c.champion_name());
			if (t == e_t)
				continue;
			const int pn = c.prev_priority(), px = c.priority();
			e_now += pn > en_now || (pn == en_now && t < e_t) ? 1 : 0;
			e_next += px > en_next || (px == en_next && t < e_t) ? 1 : 0;
		}
		catch (...)
		{
		}
	}
	int alive_us = 0, alive_them = 0;
	for (const auto& a : world().allies)
		alive_us += a.alive ? 1 : 0;
	for (const auto& o : world().enemies)
		alive_them += o.alive ? 1 : 0;
	(void)n_ours, (void)n_theirs;
	alive_us = std::max(alive_us, us_now + 1), alive_them = std::max(alive_them, e_now + 1);
	const int pu = teamplan::turn_pos(round, team, us_now, alive_us, alive_them);
	const int pe = teamplan::turn_pos(round, 1 - team, e_now, alive_them, alive_us);
	if (pe > pu)
		return false;
	return teamplan::turn_pos(round + 1, team, us_next, alive_us, alive_them) < teamplan::turn_pos(round + 1, 1 - team, e_next, alive_them, alive_us);
}

bool Brain::ally_engaged(const Enemy& t) const
{
	// P.ally_defend: a visible living ally (not us) within the target's reach + 1 whose health we saw drop since our last turn.
	const auto& W = world();
	int r = t.kit.attack_range + (t.kit.ranged ? 0 : 1) + (t.ready(t.kit.dash) ? 2 : 0); // combat()'s reach of an enemy next turn
	if (P.aoe_reach5 && P.aoe_reach5 != 3)
		r = std::max(r, enemy_spell_reach(t, false));
	else if (t.ready(t.kit.dmg) || t.ready(t.kit.cc) || t.ready(t.kit.aoe))
		r = std::max(r, 4);
	for (std::size_t i = 0; i < W.allies.size(); ++i)
	{
		const auto& a = W.allies[i];
		if (static_cast<int>(i) != W.my_index && a.alive && a.visible && a.hit_round >= round && cheb(a.pos, t.pos) <= r + 1)
			return true;
	}
	return false;
}

bool Brain::sparring_window() const
{
	return P.spar_to > P.spar_from && round >= P.spar_from && round < P.spar_to;
}

bool Brain::enemy_on_our_half() const
{
	// v9 contact evidence: a visible living enemy off its spawn and deep in our half (dist_home + 2 < opp_depth x dist_away; the
	// midline groups both teams farm stay out of it, which keeps the false-alarm rate down: opp_sim.py).
	const auto& W = world();
	for (const auto& e : W.enemies)
		if (e.alive && e.visible && !W.enemy_spawn.is_set(e.pos) &&
			static_cast<float>(W.dist_home(e.pos) + 2) < P.opp_depth * static_cast<float>(W.dist_away(e.pos)))
			return true;
	return false;
}

int Brain::style_now() const
{
	int s = P.pxs_style;
	if (P.pxs_style2 && P.pxs_switch > 0 && round >= P.pxs_switch)
		s = P.pxs_style2;
	if (P.pxs_style3 && P.pxs_switch2 > 0 && round >= P.pxs_switch2)
		s = P.pxs_style3;
	return s;
}

bool Brain::pxs_deny_altar()
{
	// Proxy style 6: body 0 stands next to the other team's best altar (their half, nearest their spawn); use_locks() locks it, combat()
	// hits tributers. Hurt, it goes home like anyone else (safety() runs first).
	auto& W = world();
	std::vector<std::pair<int, int>> alt; // the other team's altars, nearest their spawn first; body k takes the k-th (wrapping)
	for (std::size_t i = 0; i < W.altars.size(); ++i)
	{
		int dh = BIG, da = BIG; // the altar tile is a wall: measure through its approach tiles
		for (const auto t : W.altar_approach[i])
			dh = std::min(dh, W.dist_home(t)), da = std::min(da, W.dist_away(t));
		if (da < BIG && da < dh)
			alt.push_back({ da, static_cast<int>(i) });
	}
	std::sort(alt.begin(), alt.end());
	const int best = alt.empty() ? -1 : alt[static_cast<std::size_t>(W.my_index) % alt.size()].second;
	if (best < 0 || hp < 0.5f * max_hp)
		return false;
	const vec2 a = W.altars[static_cast<std::size_t>(best)];
	task = T_WAIT;
	if (cheb(pos, a) <= 2)
		return true;
	bc::bitboard goal;
	goal.draw_chebyshev(a, 2.f);
	goal &= ~W.walls;
	return step(goal, true, true);
}

bool Brain::on_the_way(int altar) const
{
	// Bank when the altar costs at most two extra steps on the way to our current target.
	if (task_group < 0)
		return false;
	auto& N = nav();
	const auto& gf = N.group_fields[static_cast<std::size_t>(task_group)];
	const auto& af = N.altar_fields[static_cast<std::size_t>(altar)];
	if (!gf.ready || !af.ready)
		return false;
	const auto& g = world().groups[static_cast<std::size_t>(task_group)];
	int altar_to_group = BIG;
	for (auto t : g.tiles)
		altar_to_group = std::min(altar_to_group, af.get(t));
	const int direct = gf.get(pos);
	const int via = af.get(pos) + altar_to_group;
	return direct < BIG && via < BIG && via - direct <= 2;
}

int Brain::bank_min(int trip) const
{
	// Each bank costs about the walk to the altar (and back out, or a recall), whatever the bag: fewer, bigger
	// bags when the altar is far. Short trips keep the plain threshold (risk and scoreboard rules set it).
	if (P.bank_trip_w <= 0.f || trip >= BIG)
		return tribute_min;
	const int extra = static_cast<int>(P.bank_trip_w * static_cast<float>(std::max(0, trip - P.bank_trip_free)));
	return std::min(tribute_min + extra, static_cast<int>(P.bank_trip_cap * static_cast<float>(tribute_min)));
}

bool Brain::tribute(bool force)
{
	if (gems == 0)
		return false;
	auto& W = world();
	if (P.no_altar_gold && W.no_altar_now())
		return false; // no usable altar now: the bag cannot be banked (gold earned decides at r2000, or the unlock group opens an altar)
	if (P.mi_island_bank > 0 && inside_island())
	{
		// No altar inside an island (default branch): recall out (the bag is kept) once it is worth banking.
		const bool wins = bc::global_submitted_gems(team::ally) + gems >= bc::constants::winning_gems;
		const bool late = round >= static_cast<int>(bc::constants::max_rounds) - 150;
		if ((force || wins || late || static_cast<int>(gems) >= P.mi_island_bank) && !in_awake_camp_range() && !danger.is_set(pos))
		{
			try
			{
				bc::self().recall();
				task = T_HOME;
				tp_island = -1;
				return true;
			}
			catch (...)
			{
			}
		}
		return false;
	}
	int dist = BIG;
	const int a = nearest_altar(dist);
	if (a < 0 || dist >= BIG)
		return false;
	const int ticks = static_cast<int>((gems + 9) / 10);
	const bool endgame = round + dist + ticks + P.endgame_margin >= static_cast<int>(bc::constants::max_rounds);
	const bool winning = wins_with(static_cast<int>(gems)) && gems > 0;
	if (P.tp_tiebreak && !force && !endgame && !winning && teamplan::tb_defer(tp_tb_.mode, static_cast<int>(gems), enemy_near_d, tpa::params()))
		return false; // tiebreak mode: the bag stays with us (risk-capped); v10's endgame rule banks it before the limit
	if (P.prism_bank && type == CT::prism && !force && !endgame && !winning && hp >= P.prism_bank_hp * max_hp)
		return false; // F4 Prism banker: the bag is focus (+1 per gem); bank it only when it wins, at the end, or when we may lose it
	const bool risky = enemy_near_field && static_cast<int>(gems) >= P.tribute_risky &&
		(P.risky_persist <= 0 || enemy_near_rounds >= P.risky_persist || hp < 0.6f * max_hp); // T14a: one flash sighting no longer herds a bag to an altar
	// Once a bank trip starts, finish it: re-deciding every turn let a passing enemy or the on-the-way test
	// flip the choice each round and the champion oscillated in place for hundreds of rounds.
	const bool committed = P.sticky_tribute && task == T_TRIBUTE && static_cast<int>(gems) >= 10;
	// Recall and bank at the altar next to spawn when that beats walking (and heals and shops on the way).
	const int via_home = recall_turns() + W.spawn_altar_d;
	bool recall_bank = W.dist_home(pos) > P.recall_min_dist && via_home + 2 < dist && safe_to_recall() && !endgame;
	if (P.v23_bank && dist <= P.v23_field_altar)
		recall_bank = false; // v23 4.6: a field altar within 15 steps beats a recall to the spawn altar
	// A long bank trip is worth a bigger bag: the threshold rises with the cheapest way to an altar from here,
	// so a body far from every altar keeps farming and banks when its route passes close to one.
	const int need = bank_min(recall_bank ? via_home : dist);
	const bool stalled = round < pw_bank_until; // v27_watch: a carrier that stood still banks now
	const bool want = stalled || (P.v23_bank ? (force || endgame || winning || committed || v23_bank_want(dist))
								 : (force || endgame || winning || risky || committed || static_cast<int>(gems) >= need || dist <= P.tribute_near ||
									  (static_cast<int>(gems) >= 10 && on_the_way(a))));
	if (!want)
		return false;
#ifdef LEGEND_TRACE
	debug_block({
		if (task != T_TRIBUTE)
			std::printf("B r=%d %d gems=%u dist=%d need=%d via=%d rb=%d f=%d e=%d w=%d risky=%d near=%d otw=%d\n", round, static_cast<int>(type), gems, dist, need, via_home, (int)recall_bank,
				(int)force, (int)endgame, (int)winning, (int)risky, (int)(dist <= P.tribute_near), (int)(gems >= 10 && on_the_way(a)));
	});
#endif
	// A tribute cancelled this turn or last (a threat made it pointless): flee, fight or move on first.
	if (round - tribute_cancel_round <= 2 && !endgame && !winning && !force)
		return false;
	if (P.v27_avoid > 0 && round < av_until && !recall_bank && !force)
	{
		// v27_avoid: the altar is next to enemies we just fled from: bank at the spawn altar (recall) or keep the bag for now
		bool hot = false;
		for (int k = 0; k < av_n; ++k)
			hot |= cheb(W.altars[static_cast<std::size_t>(a)], av_pos[static_cast<std::size_t>(k)]) <= av_rad[static_cast<std::size_t>(k)];
		if (hot)
		{
			if (W.dist_home(pos) > P.recall_min_dist && W.spawn_altar_d < BIG && safe_to_recall())
				recall_bank = true;
			else
				return false;
		}
	}
	if (recall_bank)
	{
		task = T_TRIBUTE;
		return go_home();
	}
	// The best altar is contested and enemies were just there: do not walk a bag into them alone. Keep
	// farming (the bag is safer moving with us than dying at their altar) unless the game is on the line.
	// v23 4.6: unsafe = an enemy seen within 4 of it in the last 8 rounds; a bag at the cap walks in anyway.
	if ((P.v23_bank ? v23_altar_unsafe(a) && static_cast<int>(gems) < P.v23_bank_cap : altar_unsafe(a)) && !endgame && !winning && !force && !stalled)
		return false;
	if (!P.v23_bank && !endgame && !winning && !force && !stalled && bag_needs_escort(a))
	{
		// v8 escort_bag: the bag is a long channel at a hot altar: call the team first (keep farming / healing meanwhile).
		auto& C = comms();
		if (!(C.fresh(round, 6) && C.alert_kind == AL_OPPORTUNITY))
			C.post(AL_DANGER, W.altars[static_cast<std::size_t>(a)], round);
		return false;
	}
	task = T_TRIBUTE;
	const vec2 altar = W.altars[static_cast<std::size_t>(a)];
#ifdef PROBE18T
	const vec2 p0 = pos;
#endif
	if (cheb(pos, altar) > 1)
		go_altar(a);
#ifdef PROBE18T
	{
		auto& N = nav();
		const bool fok = N.ensure_altar(a, P.target_field_fuel);
		std::printf("TB r=%d ch=%d pos=(%d,%d)->(%d,%d) altar=(%d,%d) fok=%d f=%d dang=%d campd=%d alert=%d canmove=%d\n", round, static_cast<int>(type), p0.x, p0.y, pos.x, pos.y, altar.x, altar.y,
			static_cast<int>(fok), fok ? N.altar_fields[static_cast<std::size_t>(a)].get(p0) : -1, static_cast<int>(danger.is_set(p0)), static_cast<int>(camp_danger.is_set(p0)),
			static_cast<int>(alert_zone.is_set(p0)), static_cast<int>(can_move));
		if (fok)
		{
			const bc::bitboard bl = Nav::blocked_now(p0);
			for (int dy = -1; dy <= 1; ++dy)
				for (int dx = -1; dx <= 1; ++dx)
				{
					const vec2 q{ p0.x + dx, p0.y + dy };
					if ((dx || dy) && bc::map::is_in_bounds(q))
						std::printf("  N (%d,%d) f=%d wall=%d blk=%d camp=%d\n", q.x, q.y, N.altar_fields[static_cast<std::size_t>(a)].get(q), static_cast<int>(W.walls.is_set(q)),
							static_cast<int>(bl.is_set(q)), static_cast<int>(W.camp_occ.is_set(q)));
				}
		}
	}
#endif
	if (cheb(pos, altar) <= 1)
	{
		try
		{
			bc::self().submit_gems(altar);
			tribute_start = round, tribute_ticks = ticks;
			place_ward(true);
		}
		catch (...)
		{
		}
	}
	return true;
}

bool Brain::shop_trip()
{
	auto& W = world();
	if (type == CT::tavi || build_idx >= build.size())
		return false;
	const int dh = W.dist_home(pos);
	// A big purse is a big power spike (default branch): recall for it when nothing can interrupt the channel.
	if (P.mi_recall_shop > 0 && static_cast<int>(gold) >= P.mi_recall_shop && task != T_CAPTURE && !reward_here() && !enemy_near && !in_awake_camp_range() &&
		!danger.is_set(pos) && static_cast<int>(gems) < tribute_min && !inside_island() && tp_island < 0)
		return go_home();
	const bool rich = static_cast<int>(gold) >= P.shop_gold && dh <= P.shop_trip_max;
	const bool hurt_and_rich = gold >= 90 && hp < 0.6f * max_hp && dh <= P.shop_trip_max;
	if (!rich && !hurt_and_rich)
		return false;
	if (task == T_CAPTURE || reward_here())
		return false;
	return go_home();
}

bool Brain::reward_here()
{
	// `task` still holds last turn's value: right after the last camp dies it says T_FARM while the reward
	// waits next to us. Capture first (capture_group recalls with the reward when that pays).
	if (task_group < 0)
		return false;
	const auto& g = world().groups[static_cast<std::size_t>(task_group)];
	return g.st == ST_REWARD && nav().group_dist(g, pos) <= 2;
}

bool Brain::respond_to_alert()
{
	auto& C = comms();
	if (P.escort_bag > 0 && C.fresh(round, 6) && (P.om_sight ? escort_alert() : C.alert_kind == AL_DANGER) && P.alert_radius <= 0)
	{
		// ESCORT (the DANGER code): a carrier waits for us at a hot altar; stand next to it, between it and the enemy side.
		const int d = cheb(C.alert_pos, pos);
		if (hp < 0.5f * max_hp || task == T_CAPTURE || reward_here() || d > P.escort_r || d <= 2)
			return false;
		task = T_FIGHT;
		bc::bitboard goal;
		goal.draw_chebyshev(C.alert_pos, 2.f);
		goal &= ~world().walls;
		return step(goal, false, true);
	}
	if (!C.fresh(round, 6) || (C.alert_kind != AL_RALLY && C.alert_kind != AL_OPPORTUNITY))
		return false;
	// An enemy channelling a tribute (posted as an opportunity) is the cheapest kill in the game, and the
	// only way to stop a winning tribute: answer it from farther and at lower health than a rally.
	const bool opp = C.alert_kind == AL_OPPORTUNITY;
	const int theirs = static_cast<int>(bc::global_submitted_gems(team::enemy));
	const bool their_endgame = theirs >= P.endgame_alarm;
	float hp_gate = opp ? (their_endgame ? 0.25f : 0.4f) : P.rally_hp;
	int max_d = opp ? (their_endgame ? 16 : P.g17_opp_r) + (P.opp_plan ? opp_add : 0) : P.rally_r + (P.opp_plan ? rally_add : 0); // v9 presets widen the answer radius
	if (P.deny_ramp && opp)
	{
		// GOD_Improvement_Plan UPG-4 (dynamic priority): the urgency of a denial grows with their banked total instead of one step at
		// endgame_alarm: u = clamp((theirs - deny_ramp_from) / deny_ramp_span, 0, 1); radius 12 + 4u, health gate 0.40 - 0.15u.
		const float u = std::clamp(static_cast<float>(theirs - P.deny_ramp_from) / static_cast<float>(std::max(1, P.deny_ramp_span)), 0.f, 1.f);
		hp_gate = 0.40f - 0.15f * u;
		max_d = 12 + static_cast<int>(std::lround(4.f * u)) + (P.opp_plan ? opp_add : 0);
	}
	if (P.v27_rally && !opp)
		max_d = std::max(max_d, 12);
	if (hp < hp_gate * max_hp || ((task == T_CAPTURE || reward_here()) && !their_endgame))
		return false;
	const int d = cheb(C.alert_pos, pos);
	if (d > max_d || d < 2)
		return false;
	// v15 g15_calm & 8: a body working a group (a camp hit in the last 3 rounds, waiting on its respawn) keeps at it unless the rally is
	// next to it (rallies pulled a quarter of our walking toward fights in the session-17 traces).
	if ((calm_bits & 8) && !opp && d > (P.v27_rally ? 10 : P.g15_rally_near) && (round - target_hit_round <= 3 || task == T_WAIT))
		return false;
	if (P.g15_fwalk > 0 && !opp)
	{
		// v15 g15_fwalk: rally walks share the fight-walk budget
		if (round <= g15_fw_off)
			return false;
		g15_fw_n = g15_fw_round == round - 1 ? g15_fw_n + 1 : 1;
		g15_fw_round = round;
		if (g15_fw_n > P.g15_fwalk)
		{
			g15_fw_off = round + P.g15_fwalk_off, g15_fw_n = 0;
			return false;
		}
	}
	task = T_FIGHT;
	bc::bitboard goal;
	goal.draw_chebyshev(C.alert_pos, static_cast<float>(kit.attack_range));
	return step(goal, false, true);
}

// ---------------------------------------------------------------------------------------------- farming

void Brain::refresh_item_flags() const
{
	// Emblems complete at five shards of a family; recounted only when the build index moves (this is read
	// for every camp group every turn).
	if (item_flags_idx == build_idx)
		return;
	int j = 0, d = 0, m = 0, h = 0;
	for (std::size_t i = 0; i < build_idx && i < build.size(); ++i)
	{
		h += is_home_shard(build[i]);
		j += build[i] == I::jungle_shard_of_strength || build[i] == I::jungle_shard_of_health || build[i] == I::jungle_shard_of_focus;
		d += build[i] == I::durability_shard_of_health || build[i] == I::durability_shard_of_strength || build[i] == I::durability_shard_of_focus;
		m += build[i] == I::monster_shard_of_health || build[i] == I::monster_shard_of_strength || build[i] == I::monster_shard_of_focus;
	}
	jungle_ok = j >= 5;
	durability_ok = d >= 5;
	monster_ok = m >= 5;
	home_ok = h >= 5;
	item_flags_idx = build_idx;
}

void Brain::insert_home(std::size_t at)
{
	// A Home emblem (five Home health shards) at shard index `at`, rounded up to the next emblem boundary of the plan.
	for (const I it : build)
		if (is_home_shard(it))
			return;
	at = std::max(at, build_idx);
	at = std::min(build.size(), (at + 4) / 5 * 5);
	build.insert(build.begin() + static_cast<std::ptrdiff_t>(at), 5, I::home_shard_of_health);
	item_flags_idx = static_cast<std::size_t>(-1);
}

void Brain::insert_health(std::size_t at)
{
	// build_react: one health emblem (Durability health first: -10% damage taken; then Bruiser health) at the next emblem boundary,
	// unless the next planned emblem is a health emblem already.
	at = std::max(at, build_idx);
	at = std::min(build.size(), (at + 4) / 5 * 5);
	if (at < build.size() && is_health_shard(build[at]))
		return;
	const I it = durability_done() ? I::bruiser_shard_of_health : I::durability_shard_of_health;
	build.insert(build.begin() + static_cast<std::ptrdiff_t>(at), 5, it);
	item_flags_idx = static_cast<std::size_t>(-1);
}

int Brain::recall_turns() const
{
	// Recall takes recall_time turn ends, three with a Home emblem.
	refresh_item_flags();
	return static_cast<int>(bc::constants::recall_time) - (home_ok ? 2 : 0);
}

bool Brain::jungle_done() const
{
	refresh_item_flags();
	return jungle_ok;
}

bool Brain::durability_done() const
{
	refresh_item_flags();
	return durability_ok;
}

bool Brain::monster_done() const
{
	refresh_item_flags();
	return monster_ok;
}

float Brain::dps_on(const Group& g) const
{
	// Basic attacks every round (+1/8 with an attack reset); Varg's splash hits every live camp next to the
	// target, so packed groups die several times faster. Spells land once per cooldown (8 rounds); radius-1
	// area spells hit the same cluster. Ren's retaliation hits back each camp attacking him.
	const float cl = g.cluster;
	float base = str * (1.f + (kit.reset >= 0 ? 0.125f : 0.f));
	if (type == CT::varg)
		base *= cl;
	float spells = 0;
	if (kit.dmg >= 0)
		spells += focus * kit.dmg_mod;
	if (kit.cc >= 0)
		spells += focus * kit.cc_mod;
	if (kit.aoe >= 0)
		spells += focus * kit.aoe_mod * (kit.aoe_radius >= 1.f ? cl : 1.f);
	float d = base + spells / 8.f;
	if (type == CT::ren && !kit.ranged)
		d += bc::constants::passive_abilities::ren_retaliation_focus_ratio * focus * static_cast<float>(std::min(g.attackers, 3));
	// The Monster emblem's 10% applies to every damage dealt to camps (the engine's strength does not include it).
	if (P.monster_in_dps && monster_done())
		d *= 1.1f;
	return d;
}

float Brain::incoming_on(const Group& g) const
{
	return P.farm_ema > 0.f ? incoming_on_raw(g) * farm_ema_v : incoming_on_raw(g);
}

float Brain::incoming_on_raw(const Group& g) const
{
	float in = 0;
	for (std::size_t i = 0; i < g.camps.size(); ++i)
		if (g.hp[i] > 0)
			in += g.camps[i].str;
	if (jungle_done())
		in *= 0.7f;
	if (durability_done())
		in *= 0.9f;
	// Varg's self-shield (2.5 x focus, every 8 rounds) soaks a share of it.
	if (kit.shield >= 0)
		in = std::max(in * 0.35f, in - kit.shield_mod * focus / 8.f);
	// Stuns on camps skip their next attack: one camp per cast (area stuns: the cluster).
	if (kit.cc >= 0 || kit.aoe_stuns)
		in *= 1.f - std::min(0.35f, (kit.aoe_stuns ? g.cluster : 1.f) / (8.f * std::max(1, g.attackers)));
	return in;
}

// gold_rank: who converts gold into the most damage (patch 3.0: Power emblems in the damage stat decide fights and farming speed).
int gold_rank_of(CT t)
{
	switch (t)
	{
	case CT::stellar:
	case CT::prism: return 4;
	case CT::tavi:
	case CT::cassi:
	case CT::willow:
	case CT::vesper_vale: return 3;
	case CT::issac:
	case CT::marcella:
	case CT::vendetta: return 2;
	case CT::varg:
	case CT::ryth: return 1;
	default: return 0; // Ren, Heart of Ruin
	}
}

bool Brain::ally_melee(int ally) const
{
	const auto t = world().allies[static_cast<std::size_t>(ally)].type;
	return !(t == CT::tavi || t == CT::stellar || t == CT::cassi || t == CT::prism || t == CT::willow || t == CT::vesper_vale);
}

float Brain::ally_dps_on(int ally, const Group& g) const
{
	const auto& a = world().allies[static_cast<std::size_t>(ally)];
	const auto& d = bc::champion_designs[static_cast<std::size_t>(a.type)];
	const auto s = d.base_stats();
	// Scale the design by how much our own strength has grown (allies shop on the same schedule).
	const auto mine = bc::champion_designs[static_cast<std::size_t>(type)].base_stats();
	const float growth = std::max(1.f, str / std::max(1.f, mine.base_strength));
	float st = a.visible && a.str > 0 ? a.str : s.base_strength * growth;
	if (P.ally_kit && a.kit_ready)
	{
		// ally_kit (patch 3.0.4): the ally's damage from its own kit (engine modifiers), the same arithmetic as dps_on() for our body:
		// the typed 3.4 / 2.0 / 1.5 x focus below over-counted Ren's helping damage 2x after his stun damage fell to 0.75 x focus.
		const Kit& k = a.kit;
		const float fo = a.visible && a.focus > 0 ? a.focus : s.base_focus * growth;
		const float cl = g.cluster;
		float v = st * (1.f + (k.reset >= 0 ? 0.125f : 0.f));
		if (a.type == CT::varg)
			v *= cl;
		float sp = 0;
		if (k.dmg >= 0)
			sp += fo * k.dmg_mod;
		if (k.cc >= 0)
			sp += fo * k.cc_mod;
		if (k.aoe >= 0)
			sp += fo * k.aoe_mod * (k.aoe_radius >= 1.f ? cl : 1.f);
		v += sp / 8.f;
		if (a.type == CT::ren && !k.ranged)
			v += bc::constants::passive_abilities::ren_retaliation_focus_ratio * fo * static_cast<float>(std::min(g.attackers, 3));
		return v;
	}
	float v = st * 1.1f;
	if (a.type == CT::varg)
		v *= g.cluster;
	v += s.base_focus * growth * (a.type == CT::stellar ? 3.4f * std::min(g.cluster, 2.f) / 2.f : (a.type == CT::cassi ? 2.f : 1.5f)) / 8.f;
	return v;
}

int Brain::trip_cost(const Group& g) const
{
	// Heal at spawn and come back: recall (5 turn ends, 3 with Home) beats walking once spawn is far.
	const int hd = std::min(g.d_home_c, 60);
	const int recall = recall_turns();
	return 2 + std::min(2 * hd, recall + hd);
}

int Brain::approach_rounds(int d_tile) const
{
	// Rounds until we can hit a group d_tile steps away (non-decreasing in d_tile: score_cap relies on it).
	if (!P.math_eta)
		return std::max(0, d_tile - 1);
	float t = static_cast<float>(std::max(0, d_tile - kit.attack_range));
	if (kit.dash >= 0)
		t = std::max(0.f, t - P.dash_head_start) * P.dash_pace;
	return static_cast<int>(t + 0.5f);
}

float Brain::score_cap(const Group& g) const
{
	// An upper bound on group_score(g): its value with the largest multipliers group_score can apply (the deny
	// bonus on their half, contesting an enemy capture; shares and discounts are <= 1) over its smallest time
	// (the walk, at least the Chebyshev distance to the nearest tile, plus the 6 capture rounds; waits, kill
	// time, trips and penalties only add). farm() skips a group whose cap cannot beat the best score so far:
	// the same choice, without the cost of scoring it.
	float v = static_cast<float>(g.gems) + gold_v * static_cast<float>(g.gold);
	if (!g.ours)
		v *= 1.f + std::max(0.f, deny_bonus);
	if (g.enemy_on_tile)
		v *= std::max(1.f, P.deny_capture_mult);
	const int lb = std::max(0, cheb(g.center, pos) - g.radius);
	const int d = g.st == ST_REWARD ? lb : approach_rounds(lb);
	if (P.tp_own && tp_own_.ok && g.id >= 0 && g.id < static_cast<int>(tp_own_.owner.size()) &&
		tp_own_.owner[static_cast<std::size_t>(g.id)] == tp_own_.slot)
		v *= 1.f + P.tp_own_bonus; // keep the bound above group_score's
	if (P.mi_own > 0.f || P.mi_next > 0.f || P.mi_open > 0.f)
		v *= mig::group_mult(g.id, round); // the same multiplier as group_score's
	return v / std::max(1.f, static_cast<float>(d) + 6.f);
}

bool Brain::obj_team_ready(const Group& g, float hp_left, float& kill) const
{
	// Objective map: can the living team clear g quickly and absorb its camps' damage? Every body runs the same
	// estimate from the same facts (designs, growth, alive flags), so they switch to the objective together.
	auto& W = world();
	float dps = std::max(10.f, dps_on(g));
	float pool = max_hp * (1.f - P.retreat_hp);
	int alive_n = 1, dead_n = 0;
	for (int i = 0; i < static_cast<int>(W.allies.size()); ++i)
	{
		if (i == W.my_index)
			continue;
		const auto& a = W.allies[static_cast<std::size_t>(i)];
		if (!a.alive)
		{
			++dead_n;
			continue;
		}
		++alive_n;
		dps += ally_dps_on(i, g);
		const float mh = a.max_hp > 1.f ? a.max_hp : bc::champion_designs[static_cast<std::size_t>(a.type)].base_stats().base_health;
		pool += mh * (1.f - P.retreat_hp);
	}
	if (alive_n < P.obj_min_bodies || dead_n > P.obj_dead_max)
		return false;
	kill = hp_left / dps;
	// v14 mono_v14: a monolith is cleared by bodies taking turns in front (the nearest body takes every hit, obj_shield) and healing at
	// home between turns, so its limits are its own: a longer clear and more than one health pool of hits.
	const bool mono = P.mono_v14 && g.monolith;
	const float clear_max = mono ? P.mono_clear_max : P.obj_clear_max, absorb = mono ? P.mono_absorb : P.obj_absorb;
	// Camps that hit back die first (obj_attackers_first): each attacker hits until the team's damage has gone
	// through it and every attacker before it.
	std::array<float, 16> hs{}, ss{};
	int n = 0;
	for (std::size_t i = 0; i < g.camps.size() && n < 16; ++i)
	{
		const float h = g.st == ST_RESPAWN ? g.camps[i].max_hp : g.hp[i];
		if (h <= 0 || g.camps[i].str <= 0)
			continue;
		hs[static_cast<std::size_t>(n)] = h, ss[static_cast<std::size_t>(n)] = g.camps[i].str, ++n;
	}
	float cum = 0, taken = 0;
	for (int k = 0; k < n; ++k)
	{
		cum += hs[static_cast<std::size_t>(k)];
		taken += ss[static_cast<std::size_t>(k)] * cum / dps;
	}
	return kill <= clear_max && taken <= absorb * pool;
}

bool Brain::mono_group(const Group& g) const
{
	// mono_team's groups: a lone monolith; with mono_v14 also a monolith whose other camps do not fight back (split, monolith, fracture:
	// monolith + gem clusters, 214 gems and 340 gold; the solo plan scored them -1 "too heavy", so nobody ever started one).
	return g.monolith && (g.camps.size() == 1 || (P.mono_v14 && g.attackers == 1));
}

float Brain::ring_dps(const Kit& k, float foc, const Group& g) const
{
	// Spell damage per round from distance 4 (outside every camp's reach of 3): damage, damaging stuns and area spells that
	// reach 4. Area spells (radius 1) hit every camp next to the target: up to 6 on stampede's elks and gem clusters.
	// Patch 3.0: elk / golem range 4, monolith 5: the ring stands one tile outside the group's largest range, so only spells that
	// reach that far count (the patch's stated intent: no more ranged cheese of elks from distance 4).
	const float rd = static_cast<float>(std::max(3, g.max_range) + 1);
	float d = 0;
	if (k.dmg >= 0 && k.dmg_range >= rd)
		d += foc * k.dmg_mod;
	if (k.cc >= 0 && k.cc_range >= rd && k.cc_mod > 0)
		d += foc * k.cc_mod;
	// v9 ring_reach: an area spell reaches range + radius when aimed at a tile next to the camp (spells_on_camp does that);
	// from outside, the blast covers fewer camps than one centred on the pack, so count at most 2.
	const float aoe_reach = k.aoe_range + (P.ring_reach ? k.aoe_radius : 0.f);
	if (k.aoe >= 0 && aoe_reach >= rd)
		d += foc * k.aoe_mod * (k.aoe_radius >= 1.f ? std::min(g.cluster, !P.ring_reach || k.aoe_range >= rd ? 4.f : 2.f) : 1.f);
	return d / 8.f;
}

bool Brain::ring_ready(const Group& g, float hp_left, float& kill) const
{
	auto& W = world();
	float tot = ring_dps(kit, focus, g);
	if (tot <= 0 || tot < P.o2_ring_mindps)
		return false;
	int n = 1;
	const auto mine = bc::champion_designs[static_cast<std::size_t>(type)].base_stats();
	const float growth = std::max(1.f, str / std::max(1.f, mine.base_strength));
	for (int i = 0; i < static_cast<int>(W.allies.size()); ++i)
	{
		const auto& a = W.allies[static_cast<std::size_t>(i)];
		if (i == W.my_index || !a.alive)
			continue;
		const auto s = bc::champion_designs[static_cast<std::size_t>(a.type)].base_stats();
		const float f = a.visible && a.focus > 0 ? a.focus : s.base_focus * growth;
		const float d = ring_dps(a.kit, f, g);
		if (d > 0 && d >= P.o2_ring_mindps)
			tot += d, ++n;
	}
	if (n < P.o2_ring_min)
		return false;
	kill = hp_left / tot;
	return kill <= P.o2_ring_clear;
}

bool Brain::ring_farm(Group& g, bool respawning)
{
	// Distance-4 ring around the camps that hit back: cast range-4 spells, swing at what is within 3 (gem clusters
	// only, by construction), never step into reach. Camps never heal, so slow damage is still progress.
	auto& W = world();
	bc::bitboard hit4, hit3;
	bool any = false;
	for (std::size_t i = 0; i < g.camps.size(); ++i)
		if ((respawning || (g.hp[i] > 0 && (W.camp_occ.is_set(g.camps[i].pos) || !W.vis.is_set(g.camps[i].pos)))) && g.camps[i].str > 0)
		{
			any = true;
			hit4.draw_chebyshev(g.camps[i].pos, static_cast<float>(g.camps[i].range + 1));
			hit3.draw_chebyshev(g.camps[i].pos, static_cast<float>(g.camps[i].range));
		}
#ifdef LEGEND_TRACE
	debug_block({ if (round % 10 == 0) std::printf("RG r=%d %d any=%d\n", round, static_cast<int>(type), (int)any); });
#endif
	if (!any)
		return false;
	if (P.reward_pre > 0.f && P.big_reward > 0 && g.gems >= P.big_reward && !respawning && hp >= P.big_reward_hp * max_hp)
	{
		// reward_pre: the group dies within reward_pre rounds of the ring's damage: stand on a dead tile now so the reward lands
		// under us (ladder stampede: an enemy waiting on a dead gem tile took 3 of our 4 kills while our ring stood at 4).
		float k = 0;
		if (ring_ready(g, g.hp_total, k) && k <= P.reward_pre)
		{
			const bc::bitboard dead = g.mask & ~W.camp_occ & ~W.walls;
			if (!dead.is_empty() && (dead.is_set(pos) || step(dead, false, true)))
			{
				task = T_FARM;
				std::size_t t = g.camps.size();
				float bk = 1e30f;
				for (std::size_t i = 0; i < g.camps.size(); ++i)
					if (g.hp[i] > 0 && W.camp_occ.is_set(g.camps[i].pos) && cheb(pos, g.camps[i].pos) <= kit.attack_range && g.hp[i] < bk)
						bk = g.hp[i], t = i;
				if (!cast_done && t < g.camps.size())
					spells_on_camp(g, t, false);
				if (t < g.camps.size())
					attack_chain_camp(g, t);
				task_progress = round;
				return true;
			}
		}
	}
	bc::bitboard goal = hit4;
	goal &= ~hit3;
	goal &= ~W.walls;
	goal &= ~g.mask;
#ifdef LEGEND_TRACE
	debug_block({ if (round % 10 == 0) std::printf("RG2 r=%d %d empty=%d\n", round, static_cast<int>(type), (int)goal.is_empty()); });
#endif
	if (goal.is_empty())
		return false;
	if (!goal.is_set(pos))
	{
		task = T_FARM;
		const bool st_ok = step(goal, !hit3.is_set(pos), true);
#ifdef LEGEND_TRACE
		debug_block({ std::printf("RF r=%d %d off pos=(%d,%d) step=%d in3=%d\n", round, static_cast<int>(type), pos.x, pos.y, (int)st_ok, (int)hit3.is_set(pos)); });
#endif
		if (st_ok)
			return true;
		return go_group(g, 4, true);
	}
	task = T_FARM;
	ust_anchor = pos; // waiting out a cooldown on the ring is not being stuck
	ust_since = round;
	const bool save_cc = enemy_near_d <= P.hold_cc_dist;
	const bool hold_spells = enemy_near_d <= P.hold_spell_dist && P.hold_spells_near_enemies;
	bool did = false;
	if (!hold_spells && !cast_done)
	{
		std::size_t t = g.camps.size();
		float bk = 1e30f;
		for (std::size_t i = 0; i < g.camps.size(); ++i)
		{
			if (g.hp[i] <= 0 || g.camps[i].str <= 0 || cheb(pos, g.camps[i].pos) > g.camps[i].range + 1 || !W.camp_occ.is_set(g.camps[i].pos))
				continue;
			if (g.hp[i] < bk)
				bk = g.hp[i], t = i;
		}
		if (t < g.camps.size() && spells_on_camp(g, t, save_cc))
			did = true;
	}
	std::size_t t = g.camps.size();
	float bk = 1e30f;
	for (std::size_t i = 0; i < g.camps.size(); ++i)
		if (g.hp[i] > 0 && W.camp_occ.is_set(g.camps[i].pos) && cheb(pos, g.camps[i].pos) <= kit.attack_range && g.hp[i] < bk)
			bk = g.hp[i], t = i;
	if (t < g.camps.size() && attack_chain_camp(g, t))
		did = true;
	if (did)
		task_progress = round;
#ifdef LEGEND_TRACE
	debug_block({ if (round % 10 == 0) { std::printf("RF r=%d %d on pos=(%d,%d) did=%d live_hit=%d\n", round, static_cast<int>(type), pos.x, pos.y, (int)did, (int)any);
		for (std::size_t i = 0; i < g.camps.size(); ++i) if (g.hp[i] > 0) std::printf("RC %zu (%d,%d) hp=%.0f str=%.0f occ=%d vis=%d\n", i, g.camps[i].pos.x, g.camps[i].pos.y, g.hp[i], g.camps[i].str, (int)W.camp_occ.is_set(g.camps[i].pos), (int)W.vis.is_set(g.camps[i].pos)); } });
#endif
	return true;
}

// mi_kite (default branch): our spell damage per round from distance 4, outside every camp's reach of 3. Area spells hit
// every camp within their radius of the target.
float Brain::kite_dps(const Group& g) const
{
	if (g.harmless)
		return 0;
	const bool fresh = g.st != ST_ALIVE;
	int cluster = 1;
	for (std::size_t i = 0; i < g.camps.size(); ++i)
	{
		if (!fresh && g.hp[i] <= 0)
			continue;
		int n = 1;
		for (std::size_t j = 0; j < g.camps.size(); ++j)
			if (j != i && (fresh || g.hp[j] > 0) && cheb(g.camps[i].pos, g.camps[j].pos) <= static_cast<int>(kit.aoe_radius))
				++n;
		cluster = std::max(cluster, n);
	}
	const float rd = static_cast<float>(std::max(3, g.max_range) + 1); // patch 3.0: one past the group's real range
	float per8 = 0;
	if (kit.dmg >= 0 && kit.dmg_range >= rd)
		per8 += focus * kit.dmg_mod;
	if (kit.aoe >= 0 && kit.aoe_range >= rd)
		per8 += focus * kit.aoe_mod * static_cast<float>(cluster);
	if (kit.cc >= 0 && kit.cc_range >= rd)
		per8 += focus * kit.cc_mod;
	return per8 / 8.f; // cooldowns are 8 rounds
}

// Stand at Chebyshev 4 from a live camp and out of range 3 of all of them; cast every damage spell that is up.
bool Brain::kite_group(Group& g)
{
	auto& W = world();
	const bool fresh = g.st != ST_ALIVE;
	bc::bitboard ring, inner;
	std::size_t target = g.camps.size();
	float target_key = 1e30f;
	for (std::size_t i = 0; i < g.camps.size(); ++i)
	{
		if (!fresh && g.hp[i] <= 0)
			continue;
		ring.draw_chebyshev(g.camps[i].pos, static_cast<float>(g.camps[i].range + 1));
		inner.draw_chebyshev(g.camps[i].pos, static_cast<float>(g.camps[i].range));
		const int d = cheb(pos, g.camps[i].pos);
		if (d <= g.camps[i].range + 1 && W.camp_occ.is_set(g.camps[i].pos) && g.hp[i] < target_key)
			target_key = g.hp[i], target = i;
	}
	ring &= ~inner;
	ring &= ~W.walls;
	if (ring.is_empty())
		return false;
	if (!ring.is_set(pos))
	{
		if (inner.is_set(pos))
			return step(ring, true, false); // too close (arrived from the wrong side or it respawned around us): back out
		if (nav().group_dist(g, pos) > 6)
			go_group(g, 4, true);
		else
			step(ring, true, true);
		return true;
	}
	task = T_FARM;
	if (target < g.camps.size() && !cast_done)
		spells_on_camp(g, target, enemy_near);
	return true;
}

// mi_chip (default branch): camps never heal, so a spell that is up and would otherwise idle is free progress on a group
// we will farm later. Not on enemy-half groups the enemy touched in the last 30 rounds (no finishing camps for them).
void Brain::chip_passing()
{
	if (cast_done || !can_cast || enemy_near || task == T_FIGHT || task == T_FLEE)
		return;
	const bool dmg_up = kit.dmg >= 0 && ready(kit.dmg) && kit.dmg_mod > 0 && (!kit.dmg_excl || can_move);
	const bool aoe_up = kit.aoe >= 0 && ready(kit.aoe) && kit.aoe_mod > 0 && (!kit.aoe_excl || can_move);
	if (!dmg_up && !aoe_up)
		return;
	auto& W = world();
	for (auto& g : W.groups)
	{
		if (g.st != ST_ALIVE || g.harmless || g.hp_total <= 0 || cheb(g.center, pos) > 6)
			continue;
		if (!g.ours && round - g.enemy_round < 30)
			continue;
		for (std::size_t i = 0; i < g.camps.size(); ++i)
			if (g.hp[i] > 0 && W.camp_occ.is_set(g.camps[i].pos) && cheb(pos, g.camps[i].pos) <= 4)
				if (spells_on_camp(g, i, true))
					return;
	}
}

float Brain::group_score(const Group& g, int& eta, bool* need_pair, int d_override) const
{
	sc_why = 0;
	if (need_pair)
		*need_pair = false;
	auto& W = world();
	auto& C = comms();
	eta = BIG;
	float value_mult_handoff = 1.f; // F4 (P.handoff): a reward an ally holds for us, the anchor
	if (g.monolith && !P.farm_monolith)
		{ WHY(1); return -1; }
	if (P.obj_open_rounds > 0 && W.obj_mode && round < P.obj_open_rounds && !g.objective && g.d_enemy - g.d_ally < P.obj_open_margin)
		{ WHY(2); return -1; }
	if (P.mono_open_rounds > 0 && W.mono_mode && round < P.mono_open_rounds && !g.ours)
		{ WHY(2); return -1; }
	// Lone-monolith maps, opening: the lowest-index living body with a claim leads, everyone else farms the leader's group (the centre gold
	// triples are where the packs meet; bodies that pick their own camps arrive one at a time and feed).
	bool follow_g = false;
	if (P.mono_follow_until > 0 && W.mono_mode && round < P.mono_follow_until)
	{
		int leader = -1;
		for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 6; ++i)
			if (W.allies[static_cast<std::size_t>(i)].alive && C.claim[static_cast<std::size_t>(i)] >= 0)
			{
				leader = i;
				break;
			}
		if (leader >= 0 && leader != W.my_index)
		{
			if (g.id != C.claim[static_cast<std::size_t>(leader)])
				{ WHY(14); return -1; }
			follow_g = true;
		}
	}
	const int d_tile = d_override >= 0 ? d_override : nav().group_dist(g, pos);
	if (d_tile >= BIG)
		{ WHY(3); return -1; }
	// v27_avoid: we just fled from enemies we would not fight here; walking straight back in was the flee / farm pacing (traced v83:
	// 3,305 turns of combat-flee steps inside a 3x3 box)
	if (P.v27_avoid > 0 && round < av_until && in_avoid(g))
		{ WHY(10); return -1; }
	// Rounds until we can hit the group. Ranged champions stop at their attack range; a dash kit covers 10 tiles
	// per 8-round cooldown (walk + 2-tile dash). Fitted on 1,659 engaged episodes: d-1 was exact for Ryth and Varg
	// and 2.2-2.3 rounds long for Cassi, Stellar (actual = -2.1 + 1.0 x predicted), Issac and Ren (0.85 x).
	const int d_adj = approach_rounds(d_tile);
#ifdef XM_TRACE
	const int xm_d_old = std::max(0, d_tile - 1);
#endif

	// Living allies that claim this group, and the lowest claimer index (it captures).
	int claimers = 0, first_claimer = 99;
	bool closer_lower_claimer = false; // a lower-index claimer at least as close to a reward as we are
	float ally_dps = 0;
	bool melee_ally = false;
	for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 6; ++i)
		if (i != W.my_index && C.claim[static_cast<std::size_t>(i)] == g.id && W.allies[static_cast<std::size_t>(i)].alive)
		{
			// Claims are seen a round late: on the group we already hold only lower-index claimers count,
			// otherwise two allies wanting one group both yield, both switch, and repeat forever.
			if (P.claim_tiebreak && g.id == task_group && i > W.my_index)
			{
				// A higher-index claimer yields the group to us but still fights on it. Dropping its damage too
				// made a pack that needs two bodies look impossible every other turn: the lower-index body
				// flipped between joining (partner counted) and leaving (partner ignored) each round
				// (route_stats: most target flip-flops in local games).
				if (P.claim_helpers)
				{
					ally_dps += ally_dps_on(i, g);
					melee_ally |= ally_melee(i);
				}
				continue;
			}
			++claimers;
			first_claimer = std::min(first_claimer, i);
			if (g.st == ST_REWARD && i < W.my_index)
			{
				const auto& a = W.allies[static_cast<std::size_t>(i)];
				// Unseen allies are beyond vision, so farther than us when we are close.
				closer_lower_claimer |= a.visible ? nav().group_dist(g, a.pos) <= d_tile : d_tile > 7;
			}
			ally_dps += ally_dps_on(i, g);
			melee_ally |= ally_melee(i);
		}
	const float my_dps = std::max(10.f, dps_on(g));
	float hp_left = 0;
	float time = 0;
	int wait = 0;
	float share = 1.f;
	switch (g.st)
	{
	case ST_REWARD:
	{
		// gold_rank: the reward goes to the best gold user among the living allies within gold_rank_d of it (not to the lowest index).
		bool outranked = false, outrank_lower = false;
		if (P.gold_rank)
		{
			const int rm = gold_rank_of(type);
			// gold_rank 2: the poorest body first (stat points bought, from the visible stats and the design growth), the type rank breaks ties
			const float my_pts = (max_hp - base_hp) / std::max(1.f, hp_growth) + (str - base_str) / std::max(1.f, str_growth) + (focus - base_focus) / std::max(1.f, focus_growth);
			for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 8; ++i)
			{
				const auto& a = W.allies[static_cast<std::size_t>(i)];
				if (i == W.my_index || !a.alive || !a.visible || a.seen_round != round || a.channeling)
					continue;
				if (nav().group_dist(g, a.pos) > P.gold_rank_d)
					continue;
				const int ra = gold_rank_of(a.type);
				bool above = ra > rm, below = ra < rm;
				if (P.gold_rank == 2)
				{
					const float a_pts = (a.max_hp - a.base_hp) / std::max(1.f, a.hp_growth) + (a.str - a.base_str) / std::max(1.f, a.str_growth) + (a.focus - a.base_focus) / std::max(1.f, a.focus_growth);
					above = a_pts + P.gold_rank_margin < my_pts || (std::fabs(a_pts - my_pts) <= P.gold_rank_margin && ra > rm);
					below = my_pts + P.gold_rank_margin < a_pts || (std::fabs(a_pts - my_pts) <= P.gold_rank_margin && ra < rm);
				}
				outranked |= above;
				outrank_lower |= below && i < W.my_index;
			}
			if (outranked && !(capture_group_id == g.id && g.mask.is_set(pos)))
				{ WHY(4); return -1; }
		}
		if (P.kill_captures > 0.f && g.id >= 0 && g.id < static_cast<int>(dmg_on.size()) && g.max_hp > 0.f)
		{
			// kill_captures: the killer takes the reward; a body that did little yields to a living ally near the group.
			const float share = dmg_on[static_cast<std::size_t>(g.id)] / g.max_hp;
			if (share >= P.kill_captures)
				outrank_lower = true;
			else if (share <= 1.f - P.kill_captures && !(capture_group_id == g.id && g.mask.is_set(pos)))
				for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 8; ++i)
				{
					const auto& a = W.allies[static_cast<std::size_t>(i)];
					if (i == W.my_index || !a.alive || !a.visible || a.seen_round != round || a.channeling)
						continue;
					if (nav().group_dist(g, a.pos) <= P.gold_rank_d && nav().group_dist(g, a.pos) <= d_tile)
						{ WHY(4); return -1; }
				}
		}
		if (P.mi_capture && !(capture_group_id == g.id && g.mask.is_set(pos)))
		{
			// GOD v12 (teamplan capture.h mode 1, LEARNED: the strong teams' choice in 65% of shared captures): among the living bodies
			// within gold_rank_d of the reward, the highest gold multiplier (the kit's passive) captures, then the nearest, then the lower
			// index; the others move on.
			// GOD v15 mi_capture 2: the gold a reward is worth to the body that takes it: Vesper Vale's bonus on the gold, Marcella's 2 gold
			// per gem when she banks it (IC's Marcella ends games with 106 shard equivalents, its Vesper with 94, its Cassi & Issac with 9).
			auto funnel = [&](bc::champion_type ct) {
				const auto& k = tpa::kit_of(static_cast<int>(ct));
				return P.mi_capture == 2 ? k.gold_mult * static_cast<double>(g.gold) + k.tribute_gold * static_cast<double>(g.gems) : k.gold_mult;
			};
			const double my_gm = funnel(type);
			for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 8; ++i)
			{
				const auto& a = W.allies[static_cast<std::size_t>(i)];
				if (i == W.my_index || !a.alive || !a.visible || a.seen_round != round || a.channeling)
					continue;
				const int da = nav().group_dist(g, a.pos);
				if (da > P.gold_rank_d)
					continue;
				const double gm = funnel(a.type);
				if (gm > my_gm + 1e-9 || (std::fabs(gm - my_gm) <= 1e-9 && (da < d_tile || (da == d_tile && i < W.my_index))))
					{ WHY(4); return -1; }
			}
		}
		// One body captures; if allies claim it, the lowest index takes it unless we are clearly nearer
		// (the joiner may still be walking in while we stand next to the reward).
		if (claimers && first_claimer < W.my_index && closer_lower_claimer && !outrank_lower)
			{ WHY(4); return -1; }
		if (P.no_split && !(P.big_reward > 0 && g.gems >= P.big_reward && g.enemy_on_tile))
		{
			// One collector per reward: allies standing on the tiles when it lands split it with no speed-up, and the
			// second body sat out the 6 capture rounds (and often recalled home with half a bag) instead of walking on.
			// Who was there first keeps it (same round: the lower index). A body already channelling its capture-recall cannot
			// step off (pilgrimage: Varg recalled on the gold tile at r49, Cassi walked through the next tile at r51 and kept it by
			// index: 34/34). Arrival: ours is capture_since; an ally's is the round since which we have seen it standing still there.
			const bool on = g.mask.is_set(pos);
			const int my_arr = on && capture_group_id == g.id ? capture_since : round;
			for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 8; ++i)
			{
				const auto& a = W.allies[static_cast<std::size_t>(i)];
				if (i == W.my_index || !a.alive || !a.visible || a.seen_round != round || !g.mask.is_set(a.pos))
					continue;
				const auto k = static_cast<std::size_t>(i);
				const bool still = ally_prev_round[k] == round - 1 && ally_prev_pos[k] == a.pos;
				const int a_arr = still ? ally_still_since[k] : round;
				if (P.handoff && P.anchors && is_anchor && !body_is_anchor(i))
				{
					value_mult_handoff = P.handoff_bonus; // F4: the ally holds it for us (capture_group steps it off when we arrive)
					continue;
				}
				if (!on || a_arr < my_arr || (a_arr == my_arr && i < W.my_index))
					{ WHY(12); return -1; }
			}
		}
		eta = d_tile;
		time = static_cast<float>(eta) + 6.f;
		break;
	}
	case ST_RESPAWN:
	{
		const int avail = g.ready_round - round;
		if (avail > d_adj + (W.obj_mode && g.objective ? P.obj_max_wait : P.max_wait) * (sc_relaxed ? 3 : 1))
			{ WHY(5); return -1; }
		wait = std::max(0, avail - d_adj);
		hp_left = g.max_hp;
		break;
	}
	default:
		hp_left = g.hp_total;
		break;
	}
	sc_team = false;
	sc_ring = false;
	if (g.st != ST_REWARD)
	{
		eta = d_adj;
		if (claimers)
		{
			// Join only packs too heavy for one body; never a third body except on a monolith.
			const float solo_rounds = hp_left / std::max(10.f, ally_dps);
			// g18_rich (IC study, Oct 26): a harmless group worth g18_rich_gems+ (vault's 49-cluster centre: 343 gems; the-line: 161) is cleared by
			// IC's whole team in a few rounds while our join rule let one body farm it alone (harmless groups were never "heavy").
			const bool rich = (P.g18_rich && g.harmless && g.gems >= P.g18_rich_gems && solo_rounds > P.join_min_rounds) ||
				(P.v23_prize && g.id == W.prize_g && round < P.v23_prize_until && solo_rounds > P.join_min_rounds); // v23_prize: the whole team on it
			const bool heavy = rich || follow_g || g.monolith || g.elk || (!g.harmless && (solo_rounds > P.join_min_rounds || g.attackers >= 2));
			const int max_join = P.mi_two_bodies ? std::min(P.max_join, 1) : P.max_join; // mi_two_bodies (default branch)
			// commit_keep: we are already hitting it; the join limits are for walking in, not for leaving a camp half done
			// (17 unopposed official games: 67 camps we had hit left on this rule).
			const bool committed = P.commit_keep && g.id == task_group && g.st == ST_ALIVE && round - target_hit_round <= 2;
			if (!committed && (!heavy || (!follow_g && claimers >= (g.monolith ? 4 : 1 + max_join) && !(W.obj_mode && g.objective && P.obj_team))))
				{ WHY(6); return -1; }
			// A joiner that arrives after the claimers are done walked for nothing (pilgrimage: Cassi crossed the map between
			// two 68-gem packs for 300 rounds, hitting each one a few times before someone else captured it).
			if (P.join_reach > 0.f && !g.monolith && !(W.obj_mode && g.objective) && static_cast<float>(d_adj + wait) > P.join_reach * solo_rounds)
				{ WHY(13); return -1; }
			share = rich ? P.g18_rich_share : P.join_share;
		}
		// Rounds to clear the group with the given helpers; false when it cannot be done in max_trips.
		auto plan = [&](float helpers_dps, bool helper_melee, float& t) {
			const float kill = hp_left / (my_dps + helpers_dps);
			t = static_cast<float>(d_adj + wait) + kill + 6.f;
#ifdef XM_TRACE
			if (xm_sp)
			{
				*xm_sp = ScoreParts{};
				xm_sp->my_dps = my_dps, xm_sp->ally_dps = helpers_dps, xm_sp->hp_left = hp_left, xm_sp->kill = kill;
				xm_sp->d_adj = d_adj, xm_sp->d0 = xm_d_old, xm_sp->wait = wait, xm_sp->claimers = claimers, xm_sp->melee_ally = helper_melee, xm_sp->planned = true;
			}
#endif
			if (g.harmless)
				return true;
			// Camps hit the nearest champion: a ranged champion next to a melee ally takes almost nothing.
			const float in = incoming_on(g);
#ifdef XM_TRACE
			// The uncorrected model, logged next to the new one so both are scored on the same episodes.
			const bool xm_tank0 = !(kit.ranged && helper_melee);
			const float xm_share0 = xm_tank0 ? (helper_melee && !kit.ranged ? 0.5f : 1.f) : 0.1f;
			const float xm_res0 = std::max(P.camp_hp_reserve * max_hp, in * 3.f);
			const float xm_taken0 = in * xm_share0 * kill, xm_bf0 = std::max(1.f, max_hp - xm_res0);
			const float xm_ex0 = xm_taken0 - std::max(0.f, hp - xm_res0);
			const int xm_trips0 = xm_ex0 > 0 ? static_cast<int>(std::ceil(xm_ex0 / xm_bf0)) : 0;
#endif
			// A melee ally standing at the group (claiming it or not) is nearer to the camps than a ranged champion
			// and takes their hits: with one in sight, Cassi and Stellar took 0.29-0.35 of the claim-only prediction.
			bool melee_present = false;
			if (P.math_taken)
				for (int i = 0; i < static_cast<int>(W.allies.size()) && !melee_present; ++i)
				{
					const auto& a = W.allies[static_cast<std::size_t>(i)];
					melee_present = i != W.my_index && a.alive && a.visible && cheb(a.pos, g.center) <= P.presence_radius && ally_melee(i);
				}
			const bool tank_melee = helper_melee || melee_present;
			const bool i_tank = !(kit.ranged && tank_melee);
			float my_share = i_tank ? (tank_melee && !kit.ranged ? 0.5f : 1.f) : 0.1f;
			float taken = in * my_share * kill;
			float reserve = std::max(P.camp_hp_reserve * max_hp, in * 3.f);
			float seq = 1.f, in_now = in; // in_now: what reaches us in the first rounds
			if (P.math_taken)
			{
				// Camps die one by one (farm_group hits the lowest health first) and each one attacks from the
				// round after our first hit until the round it dies, t_k = health of camps 1..k / our damage.
				// While it is our target it reaches us; before that (t < t_{k-1}) it is a bystander, which
				// reaches a melee champion standing in the pack but a lone ranged one hitting from range 3 only
				// part of the time (ranged_exposure). taken = sum_k str_k x (q t_{k-1} + t_k - t_{k-1} - 1).
				// A melee champion on a pack of n equal camps takes (n+1)/(2n) of the old constant-incoming
				// product, which overstated a pack by up to 2x.
				float q = kit.ranged && !tank_melee ? P.ranged_exposure : 1.f;
				if (P.elk_exposure && q < 1.f && g.max_range > kit.attack_range)
					q = 1.f; // elk / golem / monolith reach past our attack range: we stand inside it the whole time
				std::array<float, 8> hs{}, ss{};
				int n = 0;
				float raw = 0;
				for (std::size_t i = 0; i < g.camps.size() && n < 8; ++i)
				{
					const float h = g.st == ST_RESPAWN ? g.camps[i].max_hp : g.hp[i];
					if (h <= 0)
						continue;
					int j = n++;
					for (; j > 0 && hs[static_cast<std::size_t>(j - 1)] > h; --j)
						hs[static_cast<std::size_t>(j)] = hs[static_cast<std::size_t>(j - 1)], ss[static_cast<std::size_t>(j)] = ss[static_cast<std::size_t>(j - 1)];
					hs[static_cast<std::size_t>(j)] = h, ss[static_cast<std::size_t>(j)] = g.camps[i].str;
					raw += g.camps[i].str;
				}
				const float dps_all = my_dps + helpers_dps;
				float cum = 0, num = 0;
				for (int k = 0; k < n; ++k)
				{
					const float t_prev = cum / dps_all;
					cum += hs[static_cast<std::size_t>(k)];
					const float t_k = cum / dps_all;
					num += ss[static_cast<std::size_t>(k)] * std::max(0.f, q * t_prev + (t_k - t_prev) - 1.f);
				}
				if (raw > 0 && kill > 0)
					seq = std::min(1.f, num / (raw * kill));
				taken = in * my_share * kill * seq;
				// The HP budget of one trip ends where safety() sends us home: below retreat_hp, or below 4 rounds
				// of the raw strength of the camps in reach (safety counts every live camp within 3, before
				// emblems). The old 18% / 3 rounds reserve promised health the retreat never lets us spend.
				const float reach = n > 0 ? ss[0] + q * (raw - ss[0]) : raw;
				reserve = std::max(std::max(P.camp_hp_reserve, P.retreat_hp) * max_hp, reach * 4.f);
				if (raw > 0)
					in_now = in * reach / raw;
			}
			const float budget_now = std::max(0.f, hp - reserve);
			const float budget_full = std::max(1.f, max_hp - reserve);
			if (i_tank && budget_full < in_now * my_share * 5.f && !(sc_relaxed && claimers))
				return false; // cannot even survive a few rounds next to it
			const float extra = taken - budget_now;
			const int trips = extra > 0 ? static_cast<int>(std::ceil(extra / budget_full)) : 0;
#ifdef XM_TRACE
			if (xm_sp)
			{
				xm_sp->in = in, xm_sp->share = my_share, xm_sp->taken = taken, xm_sp->budget_now = budget_now, xm_sp->budget_full = budget_full;
				xm_sp->trips = trips;
				xm_sp->share0 = xm_share0, xm_sp->taken0 = xm_taken0, xm_sp->trips0 = xm_trips0, xm_sp->seq = seq, xm_sp->present = melee_present;
				xm_sp->reach = in > 0 ? in_now / in : 1.f;
			}
#endif
			if (trips > P.max_trips * (sc_relaxed ? 3 : 1))
				return false;
			t += static_cast<float>(trips * trip_cost(g));
			return true;
		};
		float team_kill = 0, ring_kill = 0;
		bool solo_ok = plan(ally_dps, melee_ally, time);
		sc_kite = false;
		if (P.mi_kite && !g.harmless && !(W.obj_mode && g.objective))
		{
			// Kiting (default branch): stand at distance 4 and use spells only: no damage taken, no heal trips; allies on the
			// group add their damage. Only with real spell power (focus items) or a group that dies soon anyway.
			const float kd = kite_dps(g);
			if (kd > 0 && kd >= P.mi_kite_ratio * my_dps && hp_left / (kd + ally_dps) <= P.mi_kite_max_kill)
			{
				const float k_time = static_cast<float>(std::max(0, d_tile - 4) + wait) + hp_left / (kd + ally_dps) + 9.f;
				if (!solo_ok || k_time < time)
				{
					time = k_time;
					solo_ok = true;
					sc_kite = true;
				}
			}
		}
		bool ring_ok = false;
		if (P.o2_ring && (P.o2_ring == 1 || (P.o2_ring_size && W.W == 60 && W.H == 50) || (P.o2_ring == 3 && W.ring_comp && W.team_champs >= P.o2_ring_team)) && W.obj_mode && g.objective && g.attackers >= 1 && (sc_obj_focus < 0 || sc_obj_focus == g.id))
			ring_ok = ring_ready(g, hp_left, ring_kill);
		if (ring_ok)
		{
			// Objective map: the casters clear it from distance 4 without taking a hit (the 2nd ladder team's stampede opening).
			sc_ring = true;
			time = static_cast<float>(d_adj + wait) + ring_kill + 6.f;
			share = P.o2_ring_share;
		}
		else if (!solo_ok && ((W.obj_mode && g.objective && P.obj_team && g.attackers >= P.obj_team_attackers && (sc_obj_focus < 0 || sc_obj_focus == g.id)) ||
							  (P.altar_no_camp >= 2 && g.unlock) || (P.mono_team && mono_group(g) && (!W.obj_mode || g.objective))) &&
			obj_team_ready(g, hp_left, team_kill))
		{
			// Objective map: too heavy for us and the bodies already on it, but not for the whole team.
			sc_team = true;
			time = static_cast<float>(d_adj + wait) + team_kill + 6.f;
			share = P.obj_value_share;
		}
		else if (!solo_ok)
		{
			// Too heavy for us (and the bodies already on it). Plan it as a pair: claim it, wait outside camp
			// range for the best-suited ally, then kill it together (elk pairs, wolf packs early in the game).
			if (claimers || !P.pair_plans || g.monolith)
				{ WHY(7); return -1; }
			float best_dps = 0;
			bool best_melee = false;
			for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 6; ++i)
				if (i != W.my_index && W.allies[static_cast<std::size_t>(i)].alive)
				{
					const float a = ally_dps_on(i, g);
					if (a > best_dps)
						best_dps = a, best_melee = ally_melee(i);
				}
			if (best_dps <= 0 || !plan(best_dps, best_melee, time))
				{ WHY(8); return -1; }
			time += P.pair_wait;
			share = 0.5f;
			if (need_pair)
				*need_pair = true;
		}
	}

	float value = ((P.no_altar_gold && W.no_altar_now() && !g.unlock ? 0.f : static_cast<float>(g.gems)) + gold_v * static_cast<float>(g.gold)) * share;
	if (P.handoff)
		value *= value_mult_handoff;
	if (P.heavy_value != 1.f && (g.monolith || g.gems >= P.om_heavy))
		value *= P.heavy_value; // heavy groups (a monolith, or om_heavy+ gems) worth more: the objective persona (x3) plays us level
	if (P.pxs_style)
	{
		const int s = style_now();
		if (s == 4 && (g.monolith || g.gems >= P.om_heavy))
			value *= P.pxs_obj_mult; // proxy: objective rusher
		else if ((s == 2 || s == 3) && !g.ours)
			value *= P.pxs_raid_mult; // proxy: invader / deathball raid the other half
		else if (s == 5)
		{
			bc::bitboard near;
			near.draw_chebyshev(g.center, static_cast<float>(g.radius + 2));
			if (!(near & bc::map::bushes()).is_empty())
				value *= 1.3f; // proxy: ambusher prefers camps with bushes next to them
		}
	}
	if (!g.ours)
	{
		const float risk = sc_risk;
		if (hp < P.steal_hp_frac * max_hp && risk > 0 && !sc_relaxed)
			{ WHY(9); return -1; }
		if (P.mi_deny_gems)
			value += deny_bonus * static_cast<float>(g.gems) * share; // what they lose is the gems (default branch)
		else
			value *= 1.f + deny_bonus;
		// half_grade: the risk grows with depth into their half (walk distances from the two spawns), instead of the same
		// cost one step past the midline as next to their spawn. IC spends 23% of its time in the neutral band (ours 17%)
		// and takes 6.1 neutral captures a game (ours 4.3).
		float depth = 1.f;
		if (P.half_grade > 0.f)
			depth = std::min(1.f, static_cast<float>(g.d_ally - g.d_enemy) / (P.half_grade * static_cast<float>(std::max(1, g.d_ally + g.d_enemy))));
		time += enemy_half_penalty * risk * std::max(0.f, depth);
		if (P.unknown_keep == 2 ? (g.seen_round < 0 || round - g.seen_round > 60) : (round - g.seen_round > 60 && !(P.unknown_keep && g.id == task_group)))
			value *= P.unknown_discount;
	}
	{
		// A stronger enemy force recently seen at the camp: walking in alone is how we die.
		float ehp = 0, edps = 0;
		for (int k = 0; k < sc_recent_n; ++k)
			if (cheb(sc_recent[static_cast<std::size_t>(k)].pos, g.center) <= 8)
			{
				ehp += sc_recent[static_cast<std::size_t>(k)].hp;
				edps += sc_recent[static_cast<std::size_t>(k)].dps;
			}
		const bool dive = P.big_reward_dive > 0 && g.st == ST_REWARD && g.enemy_on_tile && g.gems >= P.big_reward_dive && hp >= 0.25f * max_hp;
		if (edps > 0 && !dive)
		{
			// big_reward: a group worth a death or two is fought for with the whole team close by
			const bool big = P.big_reward > 0 && g.gems >= P.big_reward;
			const int ar = big ? P.big_reward_r : 8;
			float ohp = hp, odps = str + focus * best_mod(kit) / 8.f;
			for (const auto& a : W.allies)
				if (a.handle != self && a.alive && a.visible && cheb(a.pos, g.center) <= ar)
					ohp += a.hp, odps += a.str + a.focus * best_mod(a.kit) / 8.f;
			const float tadv = (ohp / edps) / std::max(0.1f, ehp / std::max(1.f, odps));
			// v23 4.4.4: a group is given up for nearby enemies only when the odds there are clearly against us (Mite farms on at 16%
			// of its rounds with an enemy within 8, v75 at 6%)
			if (tadv < (P.v23_contact ? P.v23_abandon_r : P.target_threat_adv) * (big ? 0.5f : 1.f))
				{ WHY(10); return -1; }
		}
	}
	if (round - g.enemy_round < 12)
		time += 12.f;
	if (P.v24_ci_escort && (type == CT::cassi || type == CT::issac))
	{
		// v24_ci_escort: the pair dies together (one kill = two bodies) and 91% of its deaths are to enemy champions; the top three
		// keep it ~5 tiles from a non-pair ally. A group farther than v24_ci_escort_r from every non-pair ally (its claimed group, else
		// where we see it) costs v24_ci_escort_w rounds per tile.
		int nd = BIG;
		for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 6; ++i)
		{
			const auto& a = W.allies[static_cast<std::size_t>(i)];
			if (i == W.my_index || !a.alive || a.type == CT::cassi || a.type == CT::issac)
				continue;
			const int cg = C.claim[static_cast<std::size_t>(i)];
			const vec2 at = cg >= 0 && cg < static_cast<int>(W.groups.size()) ? W.groups[static_cast<std::size_t>(cg)].center : a.visible ? a.pos : vec2{ -100, -100 };
			if (at.x >= 0)
				nd = std::min(nd, cheb(at, g.center));
		}
		if (nd < BIG && nd > P.v24_ci_escort_r)
			time += P.v24_ci_escort_w * static_cast<float>(nd - P.v24_ci_escort_r);
	}
	if (P.mid_risk > 0.f && round < P.mid_risk_until && g.d_ally < BIG && g.d_enemy < BIG && g.d_ally + g.d_enemy > 0)
	{
		// Opening: the groups both teams reach at the same time (the midline) are where the first team fight happens.
		const float mid = 1.f - static_cast<float>(std::abs(g.d_ally - g.d_enemy)) / static_cast<float>(g.d_ally + g.d_enemy);
		const float fade = std::min(1.f, static_cast<float>(P.mid_risk_until - round) / static_cast<float>(std::max(1, P.mid_risk_fade)));
		time += P.mid_risk * mid * mid * fade;
	}
	if (sc_alert && alert_zone.is_set(g.center))
		time += 25.f;
	if (P.om_sight && sc_sight.x >= 0 && cheb(g.center, sc_sight) <= P.om_sight_r)
		time += P.om_sight_cost; // an ally saw an enemy here: a cost, not a wall (P.om_sight)
	if (P.anchors && is_anchor && anchor_altar >= 0)
		time += P.anchor_home_w * static_cast<float>(cheb(g.center, W.altars[static_cast<std::size_t>(anchor_altar)])); // F4: stay near our altar
	if (P.ward_enemy && static_cast<int>(gems) >= P.ward_avoid_bag && near_enemy_ward(g.center, 6))
		time += P.ward_avoid_cost; // their ward sees our bag here (P.ward_enemy)
	if (P.threat_map)
	{
		// Where the enemies seen recently can be now, against what we can bring there (us + visible allies within 8 of it).
		float th = 0, td = 0;
		for (int k = 0; k < sc_threat_n; ++k)
		{
			const auto& te = sc_threat[static_cast<std::size_t>(k)];
			if (cheb(te.pos, g.center) > te.age + 2 + 4)
				continue;
			const float c = 1.f / (1.f + (static_cast<float>(te.age) / 8.f) * (static_cast<float>(te.age) / 8.f));
			th += c * te.hp, td += c * te.dps;
		}
		if (td > 0.f)
		{
			float oh = hp, od = str + focus * best_mod(kit) / 8.f;
			for (const auto& a : W.allies)
				if (a.handle != self && a.alive && a.visible && cheb(a.pos, g.center) <= 8)
					oh += a.hp, od += a.str + a.focus * best_mod(a.kit) / 8.f;
			time += P.tm_w * std::max(0.f, 1.f - (oh * od) / std::max(1.f, th * td));
		}
	}
	else
	// Learned pain: regions where we lost champions recently cost extra rounds.
	time += P.pain_w * learner().pain_at(g.center) * (stance == STANCE_PUSH ? 0.5f : 1.f);
	if (stance == STANCE_GROUPED && !claimers && (!mono_forced || (P.mono_gmask & 8)))
	{
		// Grouped: prefer camps near where allies are farming (backup within reach).
		int near = BIG;
		for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 6; ++i)
		{
			const int cg = C.claim[static_cast<std::size_t>(i)];
			if (i != W.my_index && cg >= 0 && cg < static_cast<int>(W.groups.size()) && W.allies[static_cast<std::size_t>(i)].alive)
				near = std::min(near, cheb(W.groups[static_cast<std::size_t>(cg)].center, g.center));
		}
		float rad = static_cast<float>(P.opp_model ? group_r_now : P.group_radius), fw = P.group_far_w;
		if (P.mono_group_w > 0.f && W.mono_mode && round < P.mono_grouped_until)
			rad = static_cast<float>(P.mono_group_r), fw = P.mono_group_w;
		if (near < BIG && static_cast<float>(near) > rad)
			time += fw * (static_cast<float>(near) - rad);
	}
	if (g.enemy_on_tile)
	{
		// An enemy capturing a reward: any of our bodies on any tile of the group resets their capture (it
		// completes 6 rounds after they leave, and they get nothing). Healthy, it is a steal; hurt, avoid.
		if (g.st == ST_REWARD && hp >= (P.big_reward > 0 && g.gems >= P.big_reward ? P.big_reward_hp : P.deny_hp_frac) * max_hp)
			value *= P.deny_capture_mult;
		else
			value *= 0.5f;
	}
#ifdef XM_TRACE
	if (xm_sp)
		xm_sp->time = time, xm_sp->value = value, xm_sp->score = value / std::max(1.f, time);
#endif
	if (P.finish_race > 0)
	{
		// finish_race: the game ends at 1000 banked gems. With few gems still needed, the group that wins is the one whose
		// gems reach an altar first: rank finishing groups by walk + kill + capture + bank (far above any rate score), and
		// leave the others to the rate model. A reward next to us counts too (unopposed collision: two bodies left a 44-gem
		// capture for a far 66-gem group when 62 were needed: +44 rounds).
		const int need = static_cast<int>(bc::constants::winning_gems) - static_cast<int>(bc::global_submitted_gems(team::ally)) -
			static_cast<int>(gems) - (P.team_bank ? C.others_carried() : 0);
		if (need > 0 && need <= P.finish_race && (static_cast<int>(g.gems) >= need || (g.st == ST_REWARD && d_tile <= 2)))
		{
			const int bag = static_cast<int>(gems + g.gems);
			int bank = recall_turns() + W.spawn_altar_d;
			for (int a = 0; a < static_cast<int>(W.altars.size()); ++a)
				bank = std::min(bank, nav().altar_dist(a, g.center, true));
			const float finish = time + static_cast<float>(bank + (bag + 9) / 10);
#ifdef FR_TRACE
			debug_block({ std::printf("FR r=%d %d g=%d st=%d gems=%d need=%d time=%.1f bank=%d finish=%.1f d=%d\n", round, static_cast<int>(type), g.id, static_cast<int>(g.st), g.gems, need, time, bank, finish, d_tile); });
#endif
			return 1e4f / std::max(1.f, finish);
		}
	}
	if (P.tp_own && tp_own_.ok && g.id >= 0 && g.id < static_cast<int>(tp_own_.owner.size()) &&
		tp_own_.owner[static_cast<std::size_t>(g.id)] == tp_own_.slot)
		return value / std::max(1.f, time) * (1.f + P.tp_own_bonus);
	if (P.mi_own > 0.f || P.mi_next > 0.f || P.mi_open > 0.f)
		return value / std::max(1.f, time) * mig::group_mult(g.id, round); // GOD v12: OWN, the DL next target, plan 1's opening
	return value / std::max(1.f, time);
}

bool Brain::inside_island() const { return world().dist_home(pos) >= BIG; }

bool Brain::has_crystal() const
{
	try
	{
		return bc::self().consumables()[bc::consumable_type::tp_crystal].count() > 0;
	}
	catch (...)
	{
		return false;
	}
}

bool Brain::hop_task(int gid)
{
	auto& W = world();
	auto& h = W.hops[static_cast<std::size_t>(gid)];
	auto& me = bc::self();
	if (!h.valid)
	{
		tp_hop = -1;
		return false;
	}
	if (!has_crystal())
	{
		if (W.ally_spawn.is_set(pos) && gold >= 10)
		{
			try
			{
				me.buy(bc::consumable_type::tp_crystal);
				gold -= 10;
			}
			catch (...)
			{
			}
		}
		if (!has_crystal())
		{
			tp_hop = -1;
			return false;
		}
	}
	task = T_FARM;
	task_group = gid;
	if (pos != h.launch)
	{
		if (!h.to_launch.ready && bc::fuel_remaining() > 45000)
		{
			bc::bitboard root, visited;
			root.set(h.launch);
			h.to_launch.f.compute(W.walls, root, visited);
			h.to_launch.ready = true;
		}
		bc::bitboard goal;
		goal.set(h.launch);
		if (h.to_launch.ready)
			after_move(Nav::step_field(pos, h.to_launch, 0, &danger, kit.dash, can_move, goal));
		else
			after_move(Nav::step_to(pos, goal, &danger, kit.dash, can_move));
		if (pos != h.launch)
			return true;
	}
	bool ok = false;
	try
	{
		ok = me.consumables()[bc::consumable_type::tp_crystal].use(h.land);
	}
	catch (...)
	{
	}
	if (!ok)
		h.valid = false; // landing refused (occupied or invalid): never retry this hop
	tp_hop = -1;
	return true;
}

float Brain::island_score(int i) const
{
	auto& W = world();
	const Island& isl = W.islands[static_cast<std::size_t>(i)];
	auto& C = comms();
	for (int k = 0; k < static_cast<int>(W.allies.size()) && k < 6; ++k)
		if (k != W.my_index && W.allies[static_cast<std::size_t>(k)].alive)
			for (int gid : isl.groups)
				if (C.claim[static_cast<std::size_t>(k)] == gid)
					return -1; // an ally is on it
	float value = 0, hp_total = 0;
	for (int gid : isl.groups)
	{
		const Group& g = W.groups[static_cast<std::size_t>(gid)];
		if (g.st == ST_RESPAWN && g.ready_round - round > 30)
			continue;
		value += static_cast<float>(g.gems) + gold_v * static_cast<float>(g.gold);
		hp_total += g.st == ST_REWARD ? 0.f : g.hp_total;
	}
	if (value <= 0)
		return -1;
	const int to_launch = isl.to_launch.get(pos);
	if (to_launch >= BIG)
		return -1;
	const float time = static_cast<float>(to_launch) + 4.f + hp_total / std::max(10.f, camp_dps()) +
		6.f * static_cast<float>(isl.groups.size()) + 6.f;
	return value / time;
}

bool Brain::island_task(int i)
{
	auto& W = world();
	Island& isl = W.islands[static_cast<std::size_t>(i)];
	auto& me = bc::self();
	std::uint32_t crystals = 0;
	try
	{
		crystals = me.consumables()[bc::consumable_type::tp_crystal].count();
	}
	catch (...)
	{
	}
	if (crystals == 0)
		return false;
	tp_island = i;
	task = T_FARM;
	task_group = isl.groups.front();
	if (pos != isl.launch)
	{
		bc::bitboard goal;
		goal.set(isl.launch);
		after_move(Nav::step_field(pos, isl.to_launch, 0, &danger, kit.dash, can_move, goal));
		if (pos != isl.launch)
			return true;
	}
	try
	{
		me.consumables()[bc::consumable_type::tp_crystal].use(isl.land);
	}
	catch (...)
	{
	}
	tp_island = -1; // the hop is under way (or failed): re-plan from the island score next time
	return true;
}

void Brain::prepare_scoring()
{
	// Values group_score needs that do not depend on the group: computed once per turn.
	auto& W = world();
	int alive_enemies = 0;
	sc_recent_n = 0;
	for (const auto& e : W.enemies)
	{
		alive_enemies += e.alive;
		if (e.alive && e.seen_round >= 0 && round - e.seen_round <= P.threat_score_memory && sc_recent_n < static_cast<int>(sc_recent.size()))
			sc_recent[static_cast<std::size_t>(sc_recent_n++)] = { e.pos, e.hp, e.str + e.focus * best_mod(e.kit) / 8.f + e.burst() / 3.f };
	}
	sc_risk = static_cast<float>(alive_enemies) / std::max<std::size_t>(1, W.enemies.size());
	sc_threat_n = 0;
	if (P.threat_map)
		for (const auto& e : W.enemies)
			if (e.alive && e.seen_round >= 0 && round - e.seen_round <= P.tm_memory && sc_threat_n < static_cast<int>(sc_threat.size()) && !W.enemy_spawn.is_set(e.pos))
				sc_threat[static_cast<std::size_t>(sc_threat_n++)] = { e.pos, round - e.seen_round, e.hp, e.str + e.focus * best_mod(e.kit) / 8.f + e.burst() / 3.f };
	sc_alert = !alert_zone.is_empty();
	if (P.om_sight)
	{
		sc_sight = { -1, -1 };
		const auto& C = comms();
		if (C.alert_kind == AL_DANGER && C.fresh(round, P.om_sight_age) && !is_altar_tile(C.alert_pos))
			sc_sight = C.alert_pos;
	}
	// Objective team plan: one group for the whole team, the objective group claimed by the lowest-index body (ours included).
	sc_obj_focus = -1;
	if (P.obj_focus && W.obj_mode)
	{
		auto& C = comms();
		for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 6 && sc_obj_focus < 0; ++i)
		{
			const int c = i == W.my_index ? task_group : (W.allies[static_cast<std::size_t>(i)].alive ? C.claim[static_cast<std::size_t>(i)] : -1);
			if (c >= 0 && c < static_cast<int>(W.groups.size()) && W.groups[static_cast<std::size_t>(c)].objective)
				sc_obj_focus = c;
		}
	}
}

void Brain::farm()
{
	auto& W = world();
	if (task != T_CAPTURE && cast_en_route())
		return;
	if (P.style == 1 || round < P.deathball_until || (P.pxs_style && style_now() == 3) || (P.spar_db && sparring_window()))
	{
		int leader = -1;
		for (int i = 0; i < static_cast<int>(W.allies.size()); ++i)
			if (W.allies[static_cast<std::size_t>(i)].alive)
			{
				leader = i;
				break;
			}
		auto& C = comms();
		if (leader == W.my_index)
			C.post(AL_RALLY, pos, round);
		else if (leader >= 0)
		{
			const int lg = C.claim[static_cast<std::size_t>(leader)];
			const bool leader_far = C.alert_kind == AL_RALLY && cheb(C.alert_pos, pos) > 4;
			if (leader_far || lg < 0)
			{
				task = T_WAIT;
				bc::bitboard goal;
				goal.draw_chebyshev(C.alert_pos, 2.f);
				step(goal, true, true);
				return;
			}
			Group& g = W.groups[static_cast<std::size_t>(lg)];
			task_group = lg;
			task = g.st == ST_REWARD ? T_WAIT : T_FARM;
			if (g.st == ST_REWARD)
				wait_group(g); // one body captures
			else
				farm_group(g);
			return;
		}
	}
	if (P.g17_squad > 1 && round < P.g17_squad_until && W.my_index >= 0)
	{
		// v17 squads (IC farms each group with 3 bodies and keeps 2.2 allies within 5 before r300; we farm alone): bodies come in blocks of
		// g17_squad by team index; the lowest living index of the block farms by its own scores and the others farm the group it claims.
		auto& C = comms();
		const int k = P.g17_squad, base = (W.my_index / k) * k;
		int leader = -1;
		for (int i = base; i < std::min(base + k, static_cast<int>(W.allies.size())); ++i)
			if (W.allies[static_cast<std::size_t>(i)].alive)
			{
				leader = i;
				break;
			}
		const int lg = leader >= 0 && leader != W.my_index && leader < 6 ? C.claim[static_cast<std::size_t>(leader)] : -1;
		if (lg >= 0 && lg < static_cast<int>(W.groups.size()) && (static_cast<int>(gems) < P.g17_squad_bag || W.groups[static_cast<std::size_t>(lg)].st == ST_REWARD))
		{
			Group& g = W.groups[static_cast<std::size_t>(lg)];
			if (g.st == ST_ALIVE || g.st == ST_REWARD)
			{
				task_group = lg;
				task = g.st == ST_REWARD ? T_WAIT : T_FARM;
				if (g.st == ST_REWARD)
					wait_group(g);
				else
					farm_group(g);
				return;
			}
		}
	}
	int best = -1, best_eta = BIG;
	bool best_pair = false, best_team = false, best_ring = false, best_kite = false;
	float best_s = 0;
#ifdef LEGEND_TRACE
	std::map<int, float> tr_sc;
	int tr_why_old = 0; // why the current target scored <= 0 (WHY codes; 11 blacklisted)
#endif
	prepare_scoring();
	// v27_commit: a live group we are hitting is finished (ladder: 1,749 groups a game-set left alive with nobody near, twice the
	// opponents' 908, and 464 of them captured by the enemy). Only it, or a reward within 2 steps, is scored; a respawning group never
	// replaces it. `near_cur`: the current live target is close (walking in), its score counts double and no respawn replaces it.
	bool hard_commit = false, near_cur = false;
	if (P.v27_commit && task_group >= 0 && task_group < static_cast<int>(W.groups.size()) && blacklist[static_cast<std::size_t>(task_group)] <= round)
	{
		const Group& cg = W.groups[static_cast<std::size_t>(task_group)];
		if (cg.st == ST_ALIVE)
		{
			hard_commit = round - target_hit_round <= P.v27_commit_r;
			near_cur = nav().group_dist(cg, pos) <= kit.attack_range + 4;
		}
	}
	{
		// Score the current target first, then groups near us, then the rest while fuel lasts: on a
		// 48-group map scoring everything every turn cost ~55k and turns spilled into the next round.
		auto consider = [&](Group& g) {
			if (hard_commit && g.id != task_group && !(g.st == ST_REWARD && nav().group_dist(g, pos) <= 2))
				return;
			if ((hard_commit || near_cur) && g.id != task_group && g.st == ST_RESPAWN)
				return;
			if (blacklist[static_cast<std::size_t>(g.id)] > round)
			{
#ifdef LEGEND_TRACE
				if (g.id == task_group)
					tr_why_old = 11;
#endif
				return;
			}
			// Groups that cannot beat the best so far are skipped unscored (exact, see score_cap). Scoring took
			// ~60k fuel a turn on the 98x99 48-group map and the math model made each group ~23% dearer, so
			// the loop ran down to score_fuel_floor and farm_group (up to ~29k) spilled turns into the next round.
			if (P.score_cap && best_s > 0 && g.id != task_group && score_cap(g) <= best_s)
				return;
			int eta = 0;
			bool np = false;
#ifdef LEGEND_TRACE
			g_why = 0;
#endif
			float s = group_score(g, eta, &np);
			// v27_commit: the join / pair / heavy-pack rules are for walking in, not for leaving a group half done; a safety rejection
			// (their half while hurt, an enemy force there, unreachable, a flee zone) still drops it
			if (s <= 0 && hard_commit && g.id == task_group && sc_why != 3 && sc_why != 9 && sc_why != 10 && sc_why != 1)
			{
				s = 1e-3f;
				np = false;
				sc_team = sc_ring = sc_kite = false;
				if (eta >= BIG)
					eta = approach_rounds(nav().group_dist(g, pos));
			}
			if (s <= 0)
			{
#ifdef LEGEND_TRACE
				if (g.id == task_group)
					tr_why_old = g_why;
#endif
				return;
			}
			if (P.v23_tol && v23_deadline > round && !v23_fits(g, eta))
				return; // v23 4.3: a PRIME body starts only what it finishes before the prime group respawns
			const bool tm = sc_team, rg = sc_ring, kt = sc_kite;
#ifdef LEGEND_TRACE
			tr_sc[g.id] = s;
#endif
			if (g.id == mw_group && round < mw_until && g.st == ST_ALIVE)
				s *= 4.f; // v27_meanwhile: the group we clear while our target respawns
			if (g.id == task_group && near_cur && g.st == ST_ALIVE)
				s *= P.v27_near_mult;
			if (g.id == task_group)
			{
				s *= P.mi_flip_guard && round < mi_sticky_until ? 1000.f : P.hysteresis; // mi_flip_guard: committed
				// commit_hit: a live camp we hit in the last two rounds is worth finishing (17 unopposed official games:
				// 92 switches away from a camp we had hit, for a target that scored a little higher; it heals and we walk).
				if (P.commit_hit > 0.f && g.st == ST_ALIVE && round - target_hit_round <= 2)
					s *= P.commit_hit;
			}
			else if (P.flip_window > 0 && g.id == left_group && round - left_round <= P.flip_window)
				s /= P.flip_margin; // going back to a target we just left: A-B-A-B flips walk in place
			if (s > best_s)
				best_s = s, best = g.id, best_eta = eta, best_pair = np, best_team = tm, best_ring = rg, best_kite = kt;
		};
		if (task_group >= 0 && task_group < static_cast<int>(W.groups.size()))
			consider(W.groups[static_cast<std::size_t>(task_group)]);
		// Far groups stop at a higher floor so the walk keeps the fuel it needs: on the 98x99 map scoring all
		// 70 groups left ~35k, no target field could be built (45k) and the dynamic searches that replace it
		// (30k) were skipped, so bodies stood behind an ally or next to a dead camp. The start rotates so every
		// far group is still scored every few turns.
		const int ng = static_cast<int>(W.groups.size());
		const long long far_floor = P.score_far_floor > 0 ? P.score_far_floor : P.score_fuel_floor;
		const int off = P.score_far_floor > 0 && ng > 0 ? (round * 7) % ng : 0;
		for (int pass = 0; pass < 2; ++pass)
			for (int k = 0; k < ng; ++k)
			{
				auto& g = W.groups[static_cast<std::size_t>((k + off) % ng)];
				if (g.id == task_group || (cheb(g.center, pos) <= P.score_near) != (pass == 0))
					continue;
				if (pass == 1 && bc::fuel_remaining() < far_floor)
					break;
				// Near groups too: on the 90x30 official map (40 groups, most within 20 tiles) scoring alone took
				// 70-85k and the walk after it spilled into the next round every other turn.
				if (pass == 0 && P.score_near_floor > 0 && bc::fuel_remaining() < P.score_near_floor)
					break;
				consider(g);
			}
	}
	if (P.mi_relaxed && best < 0)
	{
		// Never idle while something is farmable (default branch): relax the wait / trip / steal limits rather than stand still.
		sc_relaxed = true;
		for (auto& g : W.groups)
		{
			if (blacklist[static_cast<std::size_t>(g.id)] > round)
				continue;
			if (bc::fuel_remaining() < P.score_fuel_floor)
				break;
			int eta = 0;
			bool np = false;
			const float s = group_score(g, eta, &np);
			if (s > best_s)
				best_s = s, best = g.id, best_eta = eta, best_pair = np, best_team = sc_team, best_ring = sc_ring, best_kite = sc_kite;
		}
		sc_relaxed = false;
	}
	// Islands: from near home, compare a crystal trip with the best walking target.
	if (!hard_commit && !W.islands.empty() && !inside_island() && W.dist_home(pos) <= 4)
	{
		int bi = -1;
		float bs = best_s;
		for (int i = 0; i < static_cast<int>(W.islands.size()); ++i)
		{
			if (P.v23_hop_floor && bc::fuel_remaining() < static_cast<std::uint64_t>(P.score_fuel_floor))
				break;
			const float s = island_score(i);
			if (s > bs)
				bs = s, bi = i;
		}
		if (bi >= 0 && island_task(bi))
			return;
	}
	if (tp_island >= 0 && !inside_island() && W.dist_home(pos) > 4)
	{
		// Mid-way to the launch tile: keep going.
		if (island_task(tp_island))
			return;
	}
	// Crystal shortcuts over hole mazes: from near home, a hop can beat a long walk around.
	if (tp_hop >= 0)
	{
		if (round - tp_hop_since > 40)
			tp_hop = -1;
		else if (hop_task(tp_hop))
			return;
	}
	if (!hard_commit && W.dist_home(pos) <= 4 && !inside_island())
	{
		const bool crystal = has_crystal() || (W.ally_spawn.is_set(pos) && gold >= 10);
		if (crystal)
		{
			int bh = -1;
			float bs = best_s;
			for (auto& g : W.groups)
			{
				const auto& h = W.hops[static_cast<std::size_t>(g.id)];
				if (!h.valid || blacklist[static_cast<std::size_t>(g.id)] > round)
					continue;
				// v23_hop_floor: this second scoring pass had no fuel floor; after the main pass it spilled turns into the next round
				// (road-of-riches: ~120 lost turns a game near our spawn)
				if (P.v23_hop_floor && bc::fuel_remaining() < static_cast<std::uint64_t>(P.score_fuel_floor))
					break;
				int eta = 0;
				const float sc = group_score(g, eta, nullptr, h.cost + W.dist_home(pos));
				if (sc > bs * 1.1f)
					bs = sc, bh = g.id;
			}
			if (bh >= 0)
			{
				tp_hop = bh;
				tp_hop_since = round;
				task_group = bh;
				if (hop_task(bh))
					return;
			}
		}
	}
	if (inside_island() && best < 0)
	{
		// Island cleared or respawning: recall out (keeps the bag) once nothing can hit us.
		tp_island = -1;
		if (!in_awake_camp_range() && !danger.is_set(pos))
		{
			try
			{
				bc::self().recall();
				task = T_HOME;
				return;
			}
			catch (...)
			{
			}
		}
	}
	if (best < 0)
	{
		IDL();
		// Nothing worth doing: wait near the soonest respawn on our half, else hold near home.
		int soon = -1, soon_t = BIG;
		for (auto& g : W.groups)
			if (g.st == ST_RESPAWN && g.ours && g.ready_round - round < soon_t)
				soon_t = g.ready_round - round, soon = g.id;
		task = T_WAIT;
		// Nothing to farm: top up at home (heal and shop) rather than stand around hurt or rich.
		const bool shopper = type != CT::tavi && build_idx < build.size();
		if (!W.ally_spawn.is_set(pos) && (hp < 0.9f * max_hp || (shopper && gold >= 60)))
		{
			go_home();
			return;
		}
		if (soon >= 0)
		{
			task_group = soon;
			IDL();
			wait_group(W.groups[static_cast<std::size_t>(soon)]);
			return;
		}
		// Else go where an ally is farming: backup, and a share of its pack.
		auto& C = comms();
		int help = -1, help_d = BIG;
		for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 6; ++i)
		{
			const int cg = C.claim[static_cast<std::size_t>(i)];
			if (i == W.my_index || cg < 0 || cg >= static_cast<int>(W.groups.size()) || !W.allies[static_cast<std::size_t>(i)].alive)
				continue;
			const int dd = cheb(W.groups[static_cast<std::size_t>(cg)].center, pos);
			if (dd < help_d)
				help_d = dd, help = cg;
		}
		IDL();
		if (help >= 0 && help_d > 3)
			go_group(W.groups[static_cast<std::size_t>(help)], 3, true);
		return;
	}
#ifdef LEGEND_TRACE
	debug_block({
		if (round % 50 == 0 && W.my_index == 0)
			for (auto& g : W.groups)
			{
				int eta = 0;
				g_why = 0;
				const float sc = group_score(g, eta);
				std::printf("S r=%d g=%d ours=%d st=%d gems=%d elk=%d hp=%.0f d=%d ready=%d score=%.3f why=%d\n", round, g.id, (int)g.ours, (int)g.st, g.gems, (int)g.elk, g.hp_total, eta, g.ready_round - round, sc, g_why);
			}
	});
#endif
	if (P.v27_meanwhile && W.groups[static_cast<std::size_t>(best)].st == ST_RESPAWN)
	{
		// v27_meanwhile: the target respawns long after we get there (traced v83: 58% of our standing-still turns were waits beside a
		// respawning group). First clear a live group we finish and walk back from before it is up: the one worth most.
		const Group& bg = W.groups[static_cast<std::size_t>(best)];
		const int until = bg.ready_round - round; // rounds until it is up
		if (until - best_eta > P.v27_mw_min && bc::fuel_remaining() > static_cast<std::uint64_t>(P.score_fuel_floor))
		{
			auto& C = comms();
			int pick = -1, pick_eta = 0;
			float pv = 0;
			for (auto& g : W.groups)
			{
				if (g.st != ST_ALIVE || g.id == best || blacklist[static_cast<std::size_t>(g.id)] > round || g.monolith)
					continue;
				if (cheb(g.center, pos) > until || cheb(g.center, bg.center) > until)
					continue;
				bool taken = false;
				for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 6; ++i)
					taken |= i != W.my_index && C.claim[static_cast<std::size_t>(i)] == g.id && W.allies[static_cast<std::size_t>(i)].alive;
				if (taken)
					continue;
				const int dg = nav().group_dist(g, pos);
				if (dg >= BIG)
					continue;
				const float kill = g.hp_total / std::max(10.f, dps_on(g));
				const int back = nav().group_dist(bg, g.center);
				if (static_cast<float>(approach_rounds(dg)) + kill + 2.f + static_cast<float>(std::min(back, BIG / 2)) > static_cast<float>(until + 2))
					continue;
				int e2 = 0;
				if (group_score(g, e2) <= 0)
					continue; // too heavy for us now, their half while hurt, an enemy force there
				const float v = static_cast<float>(g.gems) + gold_v * static_cast<float>(g.gold);
				if (v > pv)
					pv = v, pick = g.id, pick_eta = e2;
				if (bc::fuel_remaining() < static_cast<std::uint64_t>(P.score_fuel_floor))
					break;
			}
			if (pick >= 0)
			{
				mw_group = pick, mw_until = bg.ready_round;
				best = pick, best_eta = pick_eta, best_pair = false, best_team = false, best_ring = false, best_kite = false;
			}
		}
	}
	XM(xm_decide(best));
#ifdef STUCK_DBG
	debug_block({
		int cur_eta = 0;
		const float cur_s = task_group >= 0 ? group_score(W.groups[static_cast<std::size_t>(task_group)], cur_eta) : -9.f;
		std::printf("F r=%d %d best=%d s=%.3f eta=%d cur=%d cs=%.3f hop=%d isl=%d pos=(%d,%d) fuel=%lld start=%lld\n", round, static_cast<int>(type), best, best_s, best_eta, task_group, cur_s, tp_hop, tp_island, pos.x, pos.y, (long long)bc::fuel_remaining(), dbg_ff);
	});
#endif
	if (best != task_group)
	{
#ifdef LEGEND_TRACE
		debug_block({
			if (task_group >= 0)
			{
				const auto& og = W.groups[static_cast<std::size_t>(task_group)];
				std::printf("SW r=%d %d old=%d new=%d sold=%.3f snew=%.3f stold=%d dold=%d dnew=%d since=%d why=%d hp=%.0f hit=%d bag=%d\n", round, static_cast<int>(type), task_group, best,
					tr_sc.count(task_group) ? tr_sc[task_group] : -1.f, tr_sc.count(best) ? tr_sc[best] : -1.f, static_cast<int>(og.st), nav().group_dist(og, pos),
					nav().group_dist(W.groups[static_cast<std::size_t>(best)], pos), round - task_since, tr_why_old, hp, tr_hits, static_cast<int>(gems));
			}
		});
#endif
#ifdef Q_TRACE
		debug_block({
			if (task_group >= 0 && task_group < static_cast<int>(W.groups.size()))
			{
				const auto& og = W.groups[static_cast<std::size_t>(task_group)];
				int e1 = 0, e2 = 0;
				g_why = 0;
				const float so = blacklist[static_cast<std::size_t>(task_group)] > round ? -2.f : group_score(og, e1);
				const int why = g_why;
				const float sn = group_score(W.groups[static_cast<std::size_t>(best)], e2);
				std::printf("QSW r=%d i=%d old=%d new=%d so=%.4f sn=%.4f why=%d ost=%d ohp=%.0f/%.0f nst=%d nw=%d dold=%d dnew=%d hitago=%d hp=%.2f bag=%u\n", round, W.my_index, task_group, best, so, sn, why,
					static_cast<int>(og.st), og.hp_total, og.max_hp, static_cast<int>(W.groups[static_cast<std::size_t>(best)].st),
					W.groups[static_cast<std::size_t>(best)].st == ST_RESPAWN ? W.groups[static_cast<std::size_t>(best)].ready_round - round : 0, cheb(og.center, pos),
					cheb(W.groups[static_cast<std::size_t>(best)].center, pos), round - target_hit_round, hp / std::max(1.f, max_hp), gems);
			}
		});
#endif
		if (task_group >= 0)
			left_group = task_group, left_round = round;
		if (P.mi_flip_guard)
		{
			// Flip-flop guard (default branch): many target switches in a short window -> commit to the new target for a while.
			mi_switch_log[mi_switch_pos++ % mi_switch_log.size()] = round;
			int recent = 0;
			for (int r : mi_switch_log)
				recent += round - r < 20;
			if (recent >= 6)
				mi_sticky_until = round + 25;
		}
		task_group = best;
		task_since = round;
#ifdef LEGEND_TRACE
		tr_hits = 0;
#endif
	}
	// Give up on targets we cannot reach in reasonable time.
	if (round - std::max(task_since, P.giveup_progress ? task_progress : -BIG) > 2 * best_eta + 60 + (W.obj_mode && W.groups[static_cast<std::size_t>(best)].objective ? P.obj_commit : 0))
	{
#ifdef Q_TRACE
		debug_block({ std::printf("QBL r=%d i=%d why=giveup task=%d g=%d\n", round, W.my_index, task, best); });
#endif
		blacklist[static_cast<std::size_t>(best)] = round + 40;
		task_group = -1;
		IDL();
		return;
	}
	Group& g = W.groups[static_cast<std::size_t>(best)];
	task_team = best_team;
	task_ring = best_ring;
	task_kite = best_kite;
	if (best_team && g.st != ST_REWARD && hp < P.obj_go_hp * max_hp && !W.ally_spawn.is_set(pos) &&
		nav().group_dist(g, pos) > P.obj_go_far)
	{
		// Objective walk: arrive healthy. Ren and Varg walked in at 30-40% health and were the first to leave.
		if (go_home())
			return;
	}
	if (best_pair && g.st != ST_REWARD)
	{
		// Pair plan: hold just outside camp range until a partner claims it too (then group_score sees a
		// claimer and both farm it); give up after pair_wait_max rounds.
		if (pair_group != g.id)
			pair_group = g.id, pair_since = round;
		if (round - pair_since > P.pair_wait_max)
		{
			blacklist[static_cast<std::size_t>(g.id)] = round + 30;
			pair_group = -1;
			task_group = -1;
			return;
		}
		task = T_WAIT;
		IDL();
		go_group(g, 4, true);
		return;
	}
	pair_group = -1;
	switch (g.st)
	{
	case ST_REWARD: task = T_CAPTURE; IDL(); capture_group(g); break;
	case ST_RESPAWN:
		task = T_WAIT;
		if (g.ready_round - round > 0)
		{
			// Ring bodies wait outside the camps' reach: a respawned elk hits whoever stands on its tile's neighbours.
			IDL();
			if (!(world().obj_mode && g.objective && P.o2_ring && task_ring && ring_farm(g, true)))
				wait_group(g);
			else
				task = T_WAIT;
		}
		else
			farm_group(g);
		break;
	default: task = T_FARM; farm_group(g); break;
	}
}

bool Brain::wait_group(Group& g)
{
	// Stand next to (never on) the spawn tiles: an occupied spawn tile delays the respawn.
	if (g.id == task_group && nav().group_dist(g, pos) <= 2)
		task_progress = round;
	if (P.v26_wait_safe && can_move && cheb(pos, g.center) <= g.radius + 4)
	{
		// v26_wait_safe: wait near the spawn tiles but out of every awake camp's reach (traced v81 games: 38% of the rounds our bodies stood
		// losing health next to a live camp were waits beside a respawning group while a neighbouring group's camp hit them; corners: a
		// Ryth waited from 48% to 32% health under a 60-a-round elk). Next to the tiles when that is safe, else within 2, else within 4.
		// Only close to the group: farther out the group field walks us in (a goal search from afar cost unopposed pace).
		auto& W = world();
		const bc::bitboard bad = g.mask | camp_danger | danger | W.walls | W.camp_occ;
		for (const float r : { 1.f, 2.f, 4.f })
		{
			bc::bitboard goal;
			for (auto t : g.tiles)
				goal.draw_chebyshev(t, r);
			goal &= ~bad;
			if (goal.is_empty())
				continue;
			if (goal.is_set(pos))
				return true; // hold here
			if (step(goal, true, true))
				return true;
			break;
		}
	}
	if (g.mask.is_set(pos))
	{
		bc::bitboard ring;
		for (auto t : g.tiles)
			ring.draw_chebyshev(t, 1.f);
		ring &= ~g.mask;
		return step(ring, false, false);
	}
	return go_group(g, 1, true);
}

bool Brain::capture_group(Group& g)
{
	if (P.handoff && P.anchors && !is_anchor && g.st == ST_REWARD && g.mask.is_set(pos))
	{
		// F4 reward hand-off: an anchor on the group takes it alone (we step off; the region never empties, the timer keeps running);
		// an anchor close by: no capture-recall, hold the tiles for it.
		auto& W = world();
		bool anchor_on = false, anchor_near = false;
		for (int i = 0; i < static_cast<int>(W.allies.size()) && i < 8; ++i)
		{
			const auto& a = W.allies[static_cast<std::size_t>(i)];
			if (!body_is_anchor(i) || i == W.my_index || !a.alive || !a.visible || a.channeling)
				continue;
			anchor_on |= g.mask.is_set(a.pos);
			anchor_near |= cheb(a.pos, g.center) <= g.radius + P.handoff_r;
		}
		if (anchor_on)
		{
			bc::bitboard off;
			off.draw_chebyshev(pos, 1.f);
			off &= ~g.mask & ~W.walls & ~W.ally_occ & ~W.enemy_occ & ~W.camp_occ;
			if (!off.is_empty() && step(off, false, false))
			{
				blacklist[static_cast<std::size_t>(g.id)] = round + 8;
				task = T_NONE;
				return true;
			}
		}
		else if (anchor_near)
		{
			if (capture_group_id != g.id)
				capture_group_id = g.id, capture_since = round;
			place_ward(round - ward_round > 4);
			return true;
		}
	}
	if (g.mask.is_set(pos))
	{
		if (g.id == task_group)
			task_progress = round;
		if (capture_group_id != g.id)
			capture_group_id = g.id, capture_since = round;
		if (P.v25_cap_safe && can_move && camp_danger.is_set(pos))
		{
			// v25: a live awake camp of another group hits us on this reward tile (ladder: half of our 12.8 rounds a game standing in camp
			// damage were captures; the top teams 3.4-6.8). The capture is per group: a tile of the same group out of every camp's reach keeps it.
			bc::bitboard safe = g.mask & ~camp_danger & ~world().walls & ~world().ally_occ & ~world().enemy_occ & ~world().camp_occ;
			bc::bitboard near1;
			near1.draw_chebyshev(pos, 1.f);
			if (!(safe & near1).is_empty() && step(safe & near1, false, false))
				return true;
		}
		if (P.g23_contest > 0)
		{
			// v23 g23_contest: the engine says the capture is contested (or theirs) while no enemy is in sight near us: one holds a far tile
			// of the same group (long gold rows), so the timer never runs. Standing on stops nothing they could not stop anyway; farm elsewhere.
			bc::detail::camp_group_capture_state cs{};
			const bool contested = bc::detail::sdk_camp_group_capture_state(g.handle, &cs) == 0 && (cs.state == 2 || cs.state == 3);
			if (!contested || enemies_within(4) > 0)
				g23_cs_group = -1;
			else if (g23_cs_group != g.id)
				g23_cs_group = g.id, g23_cs_since = round;
			else if (round - g23_cs_since >= P.g23_contest)
			{
				blacklist[static_cast<std::size_t>(g.id)] = round + P.g23_contest_bl;
				g23_cs_group = -1;
				capture_group_id = -1;
				task_group = -1;
				task = T_NONE;
				return false;
			}
		}
		if (P.v27_capcheck && round - capture_since >= 3)
		{
			// v27: the engine has no reward here (a camp of the group still lives out of our sight, or the reward is gone): our belief was
			// wrong. Treat it as respawning for a while instead of standing on it.
			bc::detail::camp_group_capture_state cs{};
			if (bc::detail::sdk_camp_group_capture_state(g.handle, &cs) == 0 && cs.state == 0)
			{
				g.st = ST_RESPAWN;
				g.ready_round = round + 30;
				blacklist[static_cast<std::size_t>(g.id)] = round + 30;
				capture_group_id = -1;
				task_group = -1;
				task = T_NONE;
				return false;
			}
		}
		// An enemy on any tile of the group resets the capture (it completes 6 rounds after they leave): restart
		// the clock, assuming they leave after this turn, so the capture-recall cannot land before the reward.
		if (P.capture_reset && g.enemy_on_tile)
			capture_since = round + 1;
		// Recall while capturing: started one turn after stepping on the tile, the teleport lands as the
		// capture completes, so we arrive home with the reward, healed, ready to shop and bank near spawn.
		// Strong ladder teams do this after almost every capture far from home.
		// Capture lands at the start of round since + capture_time + 1; a recall started in round R lands at
		// R + recall_time. Start it so both land together (never earlier: an early teleport loses the reward).
		const int recall_t = recall_turns();
		int start_at = capture_since + static_cast<int>(bc::constants::capture_time) + 1 - recall_t;
#ifdef PROBE18
		{
			bc::detail::camp_group_capture_state cs{};
			const int rc = bc::detail::sdk_camp_group_capture_state(g.handle, &cs);
			std::printf("CAP r=%d since=%d rc=%d timer=%d state=%d gems=%u\n", round, capture_since, rc, cs.timer, cs.state, gems);
		}
#endif
		if (P.g18_capt_timer)
		{
			// v18: the engine's countdown (3 with a Capture emblem among the capturers, else 5) instead of the fixed capture time
			bc::detail::camp_group_capture_state cs{};
			if (bc::detail::sdk_camp_group_capture_state(g.handle, &cs) == 0 && cs.state == 1 && cs.timer >= 0)
				start_at = round + cs.timer + P.g18_capt_slack - recall_t;
		}
		if (round >= std::max(capture_since + 1, start_at) && W_dist_home_ok() && safe_to_recall())
		{
			const bool shopper = type != CT::tavi && build_idx < build.size();
			const bool rich = shopper && gold + static_cast<std::uint32_t>(g.gold) >= static_cast<std::uint32_t>(P.v23_shop ? 250 : P.cap_recall_gold); // v23 2.4: 250
			const bool hurt = hp < P.cap_recall_hp * max_hp;
			// Where will the bag be banked? After the recall, from spawn (spawn_altar_d steps, after the rest
			// turn); without it, at the altar nearest this tile. When the nearest altar plus a recall home
			// afterwards is still cheaper, bank first: tribute() walks there once the reward lands and
			// home_trip() recalls from the altar to heal and shop.
			const int spawn_altar = world().spawn_altar_d;
			int adist = BIG;
			if (P.bank_first || P.bank_trip_w > 0 || P.win_bank)
				nearest_altar(adist);
			// A bag that wins the game: bank it at the nearest altar unless the recall route is faster.
			if (P.win_bank && adist < BIG && wins_with(static_cast<int>(gems) + g.gems) &&
				(spawn_altar >= BIG || adist <= recall_t + 1 + spawn_altar))
			{
				place_ward(round - ward_round > 4);
				return true;
			}
			const bool bank_here = P.bank_first && adist < BIG && spawn_altar < BIG &&
				adist + recall_t + P.bank_first_margin <= spawn_altar;
			const bool bag = static_cast<int>(gems) + g.gems >= bank_min(std::min(adist, spawn_altar < BIG ? 1 + spawn_altar : BIG)) &&
				!(P.prism_bank && type == CT::prism && !wins_with(static_cast<int>(gems) + g.gems));
			if (bag && bank_here && !hurt)
			{
				place_ward(round - ward_round > 4);
				return true;
			}
			bool recall_now = rich || hurt || bag;
			if (P.chain_farm)
			{
				// F5 chain farming: fighters recall later (lower health trigger, bigger bags, gold for a whole emblem), and not at all while a
				// target next to us is worth more per round than the trip home. Anchors keep the v8 health trigger and bank at bank_min.
				const bool anc = P.anchors && is_anchor;
				const bool c_hurt = hp < (anc ? P.cap_recall_hp : P.chain_hp) * max_hp;
				const bool c_rich = shopper && gold + static_cast<std::uint32_t>(g.gold) >= static_cast<std::uint32_t>(P.chain_gold);
				const int need = bank_min(std::min(adist, spawn_altar < BIG ? 1 + spawn_altar : BIG));
				const bool c_bag = static_cast<int>(gems) + g.gems >= static_cast<int>(static_cast<float>(need) * (anc ? 1.f : P.chain_bag)) &&
					!(P.prism_bank && type == CT::prism && !wins_with(static_cast<int>(gems) + g.gems));
				recall_now = c_hurt || ((c_bag || c_rich) && !chain_keep(g, recall_t, c_bag, c_rich));
			}
			if (recall_now)
			{
				try
				{
					bc::self().recall();
					task = T_CAPTURE;
					return true;
				}
				catch (...)
				{
				}
			}
		}
		place_ward(round - ward_round > 4);
		return true;
	}
	capture_group_id = -1;
	bool mv = false;
	if (P.v25_cap_safe && can_move)
	{
		// v25: walk onto a reward tile no awake camp reaches, when the group has one
		const bc::bitboard safe = g.mask & ~camp_danger & ~world().walls & ~world().camp_occ;
		if (!safe.is_empty() && cheb(pos, g.center) <= g.radius + 6)
			mv = step(safe, true, true);
	}
	if (!mv)
		mv = go_group(g, 0, true);
	if (g.mask.is_set(pos))
		capture_group_id = g.id, capture_since = round; // the capture starts in the turn we step on
	return mv;
}

bool Brain::chain_keep(const Group& g, int recall_t, bool bag, bool rich)
{
	// The trip home pays the bag (banked safe) and the gold (shards); it costs recall + a rest turn + the walk back out. A target within
	// chain_r scored as usual (value / rounds) beats it: keep farming. Only the 4 nearest groups are scored (fuel).
	auto& W = world();
	const float back = static_cast<float>(std::max(0, W.dist_home(pos)));
	const float v_home = P.chain_bank_w * ((bag ? static_cast<float>(gems + static_cast<std::uint32_t>(g.gems)) : 0.f) + (rich ? gold_v * static_cast<float>(gold + static_cast<std::uint32_t>(g.gold)) : 0.f));
	const float s_home = v_home / std::max(1.f, static_cast<float>(recall_t) + 1.f + back);
	std::array<std::pair<int, int>, 4> near{};
	int nn = 0;
	for (const auto& o : W.groups)
	{
		if (o.id == g.id || blacklist[static_cast<std::size_t>(o.id)] > round)
			continue;
		const int d = cheb(o.center, pos);
		if (d > P.chain_r)
			continue;
		if (nn < 4)
			near[static_cast<std::size_t>(nn++)] = { d, o.id };
		else
		{
			std::size_t w = 0;
			for (std::size_t k = 1; k < 4; ++k)
				if (near[k].first > near[w].first)
					w = k;
			if (d < near[w].first)
				near[w] = { d, o.id };
		}
	}
	if (nn == 0)
		return false;
	prepare_scoring();
	for (int k = 0; k < nn; ++k)
	{
		int eta = 0;
		if (group_score(W.groups[static_cast<std::size_t>(near[static_cast<std::size_t>(k)].second)], eta) > s_home)
			return true;
	}
	return false;
}

bool Brain::gank_carrier()
{
	// F6 carrier interception: a carrier walks home (their spawn's field descends) or recalls; meet it on the way, where we arrive first.
	auto& W = world();
	if (hp < 0.6f * max_hp || static_cast<int>(gems) >= P.bag_caution)
		return false;
	const int r = (P.opp_model && role_hunter) ? 14 : P.gank_r;
	const Enemy* c = nullptr;
	for (const auto& e : W.enemies)
		if (e.alive && e.visible && static_cast<int>(e.gems) >= P.gank_bag && !e.tributing && !W.enemy_spawn.is_set(e.pos) && cheb(e.pos, pos) <= r &&
			(!c || e.gems > c->gems))
			c = &e;
	if (!c)
		return false;
	// Not weaker near it: us plus visible allies within 6 of it against the enemies within 4 of it (health x damage).
	float oh = hp, od = str + focus * best_mod(kit) / 8.f, th = 0, td = 0;
	for (const auto& a : W.allies)
		if (a.handle != self && a.alive && a.visible && cheb(a.pos, c->pos) <= 6)
			oh += a.hp, od += a.str + a.focus * best_mod(a.kit) / 8.f;
	for (const auto& e : W.enemies)
		if (e.alive && e.visible && cheb(e.pos, c->pos) <= 4)
			th += e.hp, td += e.str + e.focus * best_mod(e.kit) / 8.f + e.burst() / 3.f;
	if (oh * od < P.gank_margin * th * td)
		return false;
	vec2 t = c->pos;
	vec2 goal_t = c->pos;
	for (int k = 1; k <= 8; ++k)
	{
		vec2 nb = t;
		int bd = W.dist_away(t);
		for (int dy = -1; dy <= 1; ++dy)
			for (int dx = -1; dx <= 1; ++dx)
			{
				const vec2 q{ t.x + dx, t.y + dy };
				if (bc::map::is_in_bounds(q) && !W.walls.is_set(q) && W.dist_away(q) < bd)
					bd = W.dist_away(q), nb = q;
			}
		if (nb == t)
			break;
		t = nb;
		if (cheb(pos, t) <= k)
		{
			goal_t = t;
			break;
		}
	}
	bc::bitboard goal;
	goal.draw_chebyshev(goal_t, 1.f);
	goal &= ~W.walls;
	task = T_FIGHT;
	return step(goal, false, true);
}

// GOD v16 g16_camp: every body ranks the living allies the same way (kit strength order, then index), so the roles agree without talking.
int Brain::g16_rank() const
{
	auto order = [](bc::champion_type t) {
		if (P.g16_carry_camp && t == CT::vesper_vale)
			return -1;
		switch (t)
		{
		case CT::vendetta: return 0;
		case CT_HOR: return 1;
		case CT::vesper_vale: return 2;
		case CT::marcella: return 3;
		case CT::varg: return 4;
		case CT::ryth: return 5;
		case CT::tavi: return 6;
		case CT::ren: return 7;
		case CT::stellar: return 8;
		case CT::prism: return 9;
		case CT::willow: return 10;
		default: return 11;
		}
	};
	const auto& W = world();
	const int mine = order(type);
	int r = 0;
	for (int i = 0; i < static_cast<int>(W.allies.size()); ++i)
	{
		const auto& a = W.allies[static_cast<std::size_t>(i)];
		if (i == W.my_index || !a.alive)
			continue;
		const int o = order(a.type);
		r += o < mine || (o == mine && i < W.my_index);
	}
	return r;
}

// GOD v16: hunt at the altar they bank at, then camp their spawn with the strongest body. combat(), safety() and tribute() run before this
// in the turn, so a body that is hurt, carries a bag or sees a fight it should not take still does what GOD does.
bool Brain::hunt_camp()
{
	auto& W = world();
	if (P.g16_gate && W.ally_deaths > W.enemy_deaths + P.g16_gate_margin)
		return false; // v16 gate: the fights are going their way: farm like v15
	const int rk = g16_rank();
	if (rk >= P.g16_hunt_bodies || hp < P.g16_hunt_hp * max_hp || static_cast<int>(gems) >= P.g16_hunt_bag || task == T_CAPTURE || reward_here())
		return false;
	int dead = 0;
	for (const auto& e : W.enemies)
		dead += !e.alive;
	if (dead >= P.g16_camp_dead && round - g16_camp_start > P.g16_camp_hold)
		g16_camp_start = round;
	const bool camping = dead > 0 && round - g16_camp_start <= P.g16_camp_hold;
	if (P.g16_only_camp && !(rk == 0 && camping))
		return false; // v16 only_camp: no altar hunt, the others farm like v15
	if (rk == 0 && camping)
	{
		// Wait g16_camp_d tiles from the nearest tile of their spawn: a body healing on it cannot reach us, one that steps out walks to us.
		bc::bitboard ring, inner;
		for (const auto t : W.enemy_spawn.positions())
		{
			ring.draw_chebyshev(t, static_cast<float>(P.g16_camp_d));
			inner.draw_chebyshev(t, static_cast<float>(P.g16_camp_d - 1));
		}
		bc::bitboard goal = ring & ~inner & ~W.walls & ~W.terrain & ~camp_danger;
		if (goal.is_empty())
			return false;
		task = T_WAIT;
		if (goal.is_set(pos))
			return true;
		return step(goal, true, true);
	}
	// Hunters: the altar they bank at (most of their tributes seen there, else the one nearest their spawn).
	if (enemy_tribute_seen.size() != W.altars.size())
		enemy_tribute_seen.assign(W.altars.size(), 0);
	for (const auto& e : W.enemies)
		if (e.alive && e.visible && e.tributing)
			for (std::size_t i = 0; i < W.altars.size(); ++i)
				if (cheb(e.pos, W.altars[i]) <= 1)
					++enemy_tribute_seen[i];
	int best = -1, bs = -1, bd = BIG;
	for (std::size_t i = 0; i < W.altars.size(); ++i)
	{
		int da = BIG, dh = BIG;
		for (const auto t : W.altar_approach[i])
			da = std::min(da, W.dist_away(t)), dh = std::min(dh, W.dist_home(t));
		if (da >= BIG)
			continue;
		if (enemy_tribute_seen[i] > bs || (enemy_tribute_seen[i] == bs && da < bd))
			bs = enemy_tribute_seen[i], bd = da, best = static_cast<int>(i);
	}
	if (best < 0)
		return false;
	const vec2 a = W.altars[static_cast<std::size_t>(best)];
	task = T_WAIT;
	if (cheb(pos, a) <= 3)
		return true;
	bc::bitboard goal;
	goal.draw_chebyshev(a, 3.f);
	goal &= ~W.walls & ~W.terrain;
	return step(goal, true, true);
}

bool Brain::deny_enemy_altar()
{
	// F6 DENY-ALTAR: near their finish one body waits at the altar they bank at, with a lock (use_locks) and its fight rules.
	auto& W = world();
	if (enemy_tribute_seen.size() != W.altars.size())
		enemy_tribute_seen.assign(W.altars.size(), 0);
	for (const auto& e : W.enemies)
		if (e.alive && e.visible && e.tributing)
			for (std::size_t i = 0; i < W.altars.size(); ++i)
				if (cheb(e.pos, W.altars[i]) <= 1)
					++enemy_tribute_seen[i];
	const int theirs = static_cast<int>(bc::global_submitted_gems(team::enemy));
	if (theirs < P.deny_altar_at && race_state == 0)
		return false;
	int role = -1;
	for (int i = 0; i < static_cast<int>(W.allies.size()); ++i)
		if (W.allies[static_cast<std::size_t>(i)].alive && !(P.anchors && body_is_anchor(i)))
		{
			role = i;
			break;
		}
	if (role != W.my_index || hp < 0.6f * max_hp || static_cast<int>(gems) >= 30)
		return false;
	int best = -1, bs = -1, bd = BIG;
	for (std::size_t i = 0; i < W.altars.size(); ++i)
	{
		if (altar_ours(i))
			continue;
		int da = BIG;
		for (const auto t : W.altar_approach[i])
			da = std::min(da, W.dist_away(t));
		if (enemy_tribute_seen[i] > bs || (enemy_tribute_seen[i] == bs && da < bd))
			bs = enemy_tribute_seen[i], bd = da, best = static_cast<int>(i);
	}
	if (best < 0)
		return false;
	const vec2 a = W.altars[static_cast<std::size_t>(best)];
	task = T_WAIT;
	if (cheb(pos, a) <= 2)
		return true;
	bc::bitboard goal;
	goal.draw_chebyshev(a, 2.f);
	goal &= ~W.walls;
	return step(goal, true, true);
}

void Brain::safe_fallback()
{
	// F6 watchdog: the turn logic threw three times in a row. Do something harmless with plain SDK calls: hit an adjacent enemy, else
	// walk toward our spawn (heals there).
	try
	{
		auto& me = bc::self();
		for (const auto& c : bc::champions(team::enemy))
		{
			bc::detail::champion_info i{};
			if (bc::detail::sdk_champion(handle_of(c), &i) == 0 && cheb({ i.x, i.y }, me.position()) <= 1)
			{
				me.attack(c);
				return;
			}
		}
		const auto sp = bc::map::spawn_region(team::ally).positions();
		if (!sp.empty())
			me.move_towards(sp.front());
	}
	catch (...)
	{
	}
}

bool Brain::W_dist_home_ok() const { return world().dist_home(pos) > P.cap_recall_min_home && world().dist_home(pos) < BIG; }

bool Brain::hor_camp_dash(Group& g, std::size_t idx)
{
	// v8 (hor_camp): Heart of Ruin's dash lands on every camp within dash_radius for focus x dash_mod (175 at base focus: more than a
	// gem or gold cluster's 120 health) and stuns them (a stunned camp skips its attack). spells_on_camp() knew only damage, stun and
	// area spells, so the dash was never used on camps. Land within attack reach of the target camp, so the attack after it still hits.
	auto& W = world();
	const auto& c = g.camps[idx];
	const int rng = std::max(1, static_cast<int>(kit.dash_range));
	const int rad = std::max(0, static_cast<int>(kit.dash_radius));
	const bc::bitboard blocked = Nav::blocked_now(pos);
	vec2 best = pos;
	int best_n = P.hor_camp - 1;
	for (int dy = -rng; dy <= rng; ++dy)
		for (int dx = -rng; dx <= rng; ++dx)
		{
			const vec2 p{ pos.x + dx, pos.y + dy };
			if ((dx == 0 && dy == 0) || !bc::map::is_in_bounds(p) || blocked.is_set(p) || cheb(p, c.pos) > kit.attack_range || W.enemy_spawn.is_set(p))
				continue;
			nowake_ok = g.id;
			if (wakes_sleeper(p, rad))
				continue;
			if ((std::abs(dx) == 2 || std::abs(dy) == 2) && bc::map::walls().is_set(vec2{ pos.x + dx / 2, pos.y + dy / 2 }))
				continue;
			int n = 0;
			for (std::size_t i = 0; i < g.camps.size(); ++i)
				n += g.hp[i] > 0 && W.camp_occ.is_set(g.camps[i].pos) && cheb(p, g.camps[i].pos) <= rad;
			if (n > best_n)
				best_n = n, best = p;
		}
	if (best == pos)
		return false;
	try
	{
		if (bc::self().abilities()[static_cast<std::size_t>(kit.dash)].use(best))
		{
			note_dmg(g.id, focus * kit.dash_mod * static_cast<float>(best_n));
			cast_done = true;
			after_move(true);
			return true;
		}
	}
	catch (...)
	{
	}
	return false;
}

bool Brain::spells_on_camp(Group& g, std::size_t idx, bool save_cc)
{
	nowake_ok = g.id; // v26_nowake: the camps of the group we cast at may be hit, a sleeping neighbour may not
	const auto& c = g.camps[idx];
	const int d = cheb(pos, c.pos);
	if (P.hor_camp > 0 && kit.dash >= 0 && kit.dash_mod > 0.f && !save_cc && d <= kit.attack_range && ready(kit.dash) &&
		enemy_near_d > P.strike_dash_hold && hor_camp_dash(g, idx))
		return true;
	if (kit.aoe >= 0 && d <= static_cast<int>(kit.aoe_range) && (!kit.aoe_stuns || !save_cc) && ready(kit.aoe))
	{
		// Centre the blast on the camp with the most live neighbours.
		vec2 best = c.pos;
		int best_n = -1;
		for (std::size_t i = 0; i < g.camps.size(); ++i)
		{
			if (g.hp[i] <= 0 || cheb(pos, g.camps[i].pos) > static_cast<int>(kit.aoe_range))
				continue;
			int n = 0;
			for (std::size_t j = 0; j < g.camps.size(); ++j)
				n += g.hp[j] > 0 && cheb(g.camps[i].pos, g.camps[j].pos) <= 1;
			if (n > best_n)
				best_n = n, best = g.camps[i].pos;
		}
		if (best_n >= 2 || kit.dmg < 0 || !ready(kit.dmg))
			if (cast_ground(kit.aoe, best))
			{
				note_dmg(g.id, focus * kit.aoe_mod * static_cast<float>(std::max(1, best_n)));
				return true;
			}
	}
	if (P.ring_reach && kit.aoe >= 0 && d > static_cast<int>(kit.aoe_range) && d <= static_cast<int>(kit.aoe_range + kit.aoe_radius) &&
		(!kit.aoe_stuns || !save_cc) && ready(kit.aoe) && (kit.dmg < 0 || !ready(kit.dmg) || d > static_cast<int>(kit.dmg_range)))
	{
		// v9 ring_reach: the camp stands beyond the cast range but within range + radius: centre the blast on a tile next to it
		// (within our cast range) that covers the most live camps.
		const int r = static_cast<int>(kit.aoe_radius), R = static_cast<int>(kit.aoe_range);
		const auto& W = world();
		vec2 best = c.pos;
		int best_n = 0;
		for (int dy = -r; dy <= r; ++dy)
			for (int dx = -r; dx <= r; ++dx)
			{
				const vec2 t{ c.pos.x + dx, c.pos.y + dy };
				if (t.x < 0 || t.y < 0 || t.x >= W.W || t.y >= W.H || cheb(pos, t) > R)
					continue;
				int n = 0;
				for (std::size_t j = 0; j < g.camps.size(); ++j)
					n += g.hp[j] > 0 && cheb(t, g.camps[j].pos) <= r;
				if (n > best_n)
					best_n = n, best = t;
			}
		if (best_n >= 1 && cast_ground(kit.aoe, best))
		{
			note_dmg(g.id, focus * kit.aoe_mod * static_cast<float>(best_n));
			return true;
		}
	}
	if (kit.dmg >= 0 && d <= static_cast<int>(kit.dmg_range) && cast_unit_camp(kit.dmg, c.camp))
	{
		note_dmg(g.id, focus * kit.dmg_mod);
		return true;
	}
	if (kit.cc >= 0 && d <= static_cast<int>(kit.cc_range) && !save_cc && (kit.cc_mod > 0 || g.awake) && cast_unit_camp(kit.cc, c.camp))
	{
		note_dmg(g.id, focus * kit.cc_mod);
		return true;
	}
	return false;
}

// Cast before walking: a ready damage spell is lost cooldown while the body walks past camps. Casting from exactly 4
// tiles is free (camps hit at 3), and camps never heal, so the damage is still there when a body farms the group.
// Only groups that are not the task group (farm_group already casts there), and only when no enemy is near.
bool Brain::cast_en_route()
{
	if (!P.cast_en_route || cast_done || !can_move || !can_cast)
		return false;
	const bool dmg_up = kit.dmg >= 0 && ready(kit.dmg);
	const bool aoe_up = kit.aoe >= 0 && ready(kit.aoe) && (!kit.aoe_stuns || P.cast_en_route >= 2);
	const bool cc_up = P.cast_en_route >= 2 && kit.cc >= 0 && ready(kit.cc) && kit.cc_mod > 0;
	if (!dmg_up && !aoe_up && !cc_up)
		return false;
	if (enemy_near_d <= P.hold_spell_dist || enemies_within(9) > 0 || round < P.cast_route_from)
		return false;
	auto& W = world();
	// The spell is down for 8 rounds after a camp cast: not while an enemy seen recently could reach us in that time
	// (eight: the centre fights come through the bushes; with en-route casts we lost all 6 games vs _es2/_r2/_L0).
	if (P.cast_route_enemy_d > 0)
		for (const auto& e : W.enemies)
			if (e.alive && e.seen_round >= 0 && round - e.seen_round <= P.cast_route_memory && cheb(e.pos, pos) <= P.cast_route_enemy_d)
				return false;
	const int reach = static_cast<int>(std::max({ dmg_up ? kit.dmg_range : 0.f, aoe_up ? kit.aoe_range : 0.f, cc_up ? kit.cc_range : 0.f }));
	Group* bg = nullptr;
	std::size_t bi = 0;
	float bk = 1e30f;
	for (auto& g : W.groups)
	{
		if (!g.ours || g.monolith || g.id == task_group || g.st != ST_ALIVE || g.seen_round < 0 || cheb(g.center, pos) > reach + g.radius + 1)
			continue;
		for (std::size_t i = 0; i < g.camps.size(); ++i)
		{
			const int d = cheb(pos, g.camps[i].pos);
			if (g.hp[i] <= 0 || !W.camp_occ.is_set(g.camps[i].pos) || d < 4 || d > reach)
				continue;
			// A camp at 4 is outside every camp's reach (3); a group whose other camps stand closer than that could hit us.
			bool safe = true;
			for (std::size_t j = 0; j < g.camps.size(); ++j)
				safe &= !(g.hp[j] > 0 && W.camp_occ.is_set(g.camps[j].pos) && cheb(pos, g.camps[j].pos) <= g.camps[j].range);
			if (!safe)
				continue;
			if (g.hp[i] < bk)
				bk = g.hp[i], bg = &g, bi = i;
		}
	}
	if (!bg)
		return false;
	return spells_on_camp(*bg, bi, P.cast_en_route < 2);
}

// Fight: the target is out of reach but another enemy stands within spell range: cast on it, hold position.
bool Brain::cast_on_nearer(const Enemy& skip)
{
	if (!P.cast_near_target || cast_done || !can_cast)
		return false;
	if (!(ready(kit.cc) || ready(kit.dmg) || ready(kit.aoe)))
		return false;
	auto& W = world();
	Enemy* pick = nullptr;
	const int lim = P.aoe_cast5 && ready(kit.aoe) ? std::max(4, static_cast<int>(kit.aoe_range + kit.aoe_radius)) : 4;
	for (auto& o : W.enemies)
	{
		if (&o == &skip || !o.ch || !o.alive || !o.visible || cheb(pos, o.pos) > lim || W.enemy_spawn.is_set(o.pos))
			continue;
		if (o.type == CT::ren && hp <= 2.5f * bc::constants::passive_abilities::ren_retaliation_focus_ratio * o.focus && o.hp > burst_vs(o))
			continue;
		if (!pick || o.hp < pick->hp)
			pick = &o;
	}
	if (!pick)
		return false;
	if (P.aoe_cast5 && cheb(pos, pick->pos) > 4)
		return cast_area_stun_at(*pick);
	if (!cast_unit_champ(kit.cc, *pick->ch) && !cast_unit_champ(kit.dmg, *pick->ch))
	{
		if (P.aoe_cast5)
			cast_area_stun_at(*pick);
		else
			cast_ground(kit.aoe, pick->pos);
	}
	return cast_done;
}

bool Brain::attack_chain_camp(Group& g, std::size_t idx)
{
	auto& W = world();
	if (!attack_unit(g.camps[idx].camp))
		return false;
	note_dmg(g.id, str);
	if (g.id == task_group)
		task_progress = round, target_hit_round = round;
#ifdef LEGEND_TRACE
	if (g.id == task_group)
		++tr_hits;
#endif
	// Second swing with an attack reset; retarget if the first swing killed it.
	if (kit.reset >= 0 && ready(kit.reset))
	{
		std::size_t target = idx;
		bc::detail::camp_state cs{};
		const bool dead = bc::detail::sdk_camp(handle_of(g.camps[idx].camp), &cs) != 0 || cs.health <= 0;
		if (dead)
		{
			target = g.camps.size();
			for (std::size_t i = 0; i < g.camps.size(); ++i)
				if (i != idx && g.hp[i] > 0 && W.camp_occ.is_set(g.camps[i].pos) && cheb(pos, g.camps[i].pos) <= kit.attack_range)
					target = i;
			// Vendetta's kill reset makes this free; others keep the reset for later.
			if (target == g.camps.size())
				return true;
		}
		if (cast_self(kit.reset) && attack_unit(g.camps[target].camp))
			note_dmg(g.id, str);
	}
	return true;
}

// big_reward: an enemy waits on a dead tile of a big group we are killing (ladder stampede: it captures the reward the round the
// last camp dies, 3 of our 4 kills stolen). One of our bodies on any tile of the group resets their capture: step onto a dead
// tile too and keep hitting from there.
bool Brain::contest_tiles(Group& g)
{
	auto& W = world();
	if (P.big_reward <= 0 || g.gems < P.big_reward || g.st != ST_ALIVE || !g.enemy_on_tile || hp < P.big_reward_hp * max_hp)
		return false;
	bc::bitboard dead = g.mask & ~W.camp_occ & ~W.walls;
	if (dead.is_empty())
		return false;
	task = T_FARM;
	if (!dead.is_set(pos) && !step(dead, false, true))
		return false;
	std::size_t t = g.camps.size();
	float bk = 1e30f;
	for (std::size_t i = 0; i < g.camps.size(); ++i)
		if (g.hp[i] > 0 && W.camp_occ.is_set(g.camps[i].pos) && cheb(pos, g.camps[i].pos) <= kit.attack_range && g.hp[i] < bk)
			bk = g.hp[i], t = i;
	if (t < g.camps.size())
		attack_chain_camp(g, t);
	task_progress = round;
	return true;
}

bool Brain::farm_group(Group& g)
{
	auto& W = world();
	// Team targets outside objective mode (session 14): the camp group that unlocks an altar and lone monoliths (mono_team) use the same
	// gather / attackers-first / shield rules while the team plan is on.
	const bool obj = (W.obj_mode && g.objective) || (task_team && ((P.altar_no_camp >= 2 && g.unlock) || (P.mono_team && mono_group(g))));
	const bool obj_first = obj && P.obj_attackers_first;
	IDL();
	if (contest_tiles(g))
		return IDL(), true;
	if (obj && P.o2_ring && task_ring && g.id == task_group && ring_farm(g))
		return IDL(), true;
	if (P.mi_kite && task_kite && g.id == task_group && !obj && kite_group(g))
		return IDL(), true;
	if (obj && task_team && P.obj_gather > 1 && g.st == ST_ALIVE && !g.awake && g.hp_total / std::max(10.f, dps_on(g)) > P.obj_solo_rounds && round >= pw_off_until)
	{
		// Objective: bodies arriving one by one were worn down by the camps (6 elks hit for 360 a round) and
		// left it half dead for the enemy (stampede vs _v6: 1,707 of 17,400 left for 130 rounds, then their
		// Ren took 360 gems). Wait just outside camp range for the team, unless someone already woke it.
		int near = 0, alive_n = 0;
		for (int i = 0; i < static_cast<int>(W.allies.size()); ++i)
		{
			const auto& a = W.allies[static_cast<std::size_t>(i)];
			if (!a.alive)
				continue;
			++alive_n;
			const vec2 ap = i == W.my_index ? pos : a.pos;
			if ((i == W.my_index || (a.visible && a.seen_round == round)) && nav().group_dist(g, ap) <= P.obj_gather_r)
				++near;
		}
		if (obj_gather_group != g.id)
			obj_gather_group = g.id, obj_gather_since = -1;
		const int need = std::min(P.obj_gather, alive_n);
		if (near < need)
		{
			if (nav().group_dist(g, pos) <= P.obj_gather_r && obj_gather_since < 0)
				obj_gather_since = round;
			if (obj_gather_since < 0 || round - obj_gather_since <= P.obj_gather_max)
			{
#ifdef LEGEND_TRACE
				debug_block({ std::printf("GW r=%d %d near=%d need=%d since=%d awake=%d\n", round, static_cast<int>(type), near, need, obj_gather_since, (int)g.awake); });
#endif
				task = T_WAIT;
				IDL();
				go_group(g, std::max(4, g.max_range + 1), true); // outside the group's real reach (patch 3.0: elk 4, monolith 5)
				return true;
			}
		}
	}
	// Choose among live, visible camps in attack range: lowest health first (Varg: most neighbours for splash).
	auto pick = [&](int range) {
		std::size_t best = g.camps.size();
		float best_key = 1e30f;
		for (std::size_t i = 0; i < g.camps.size(); ++i)
		{
			if (g.hp[i] <= 0 || !W.camp_occ.is_set(g.camps[i].pos) || cheb(pos, g.camps[i].pos) > range)
				continue;
			float key = g.hp[i];
			if (obj_first && g.camps[i].str <= 0)
				key += 1e6f; // harmless camps (gem clusters) last: the elks hit until they die
			if (type == CT::varg)
				for (std::size_t j = 0; j < g.camps.size(); ++j)
					if (j != i && g.hp[j] > 0 && cheb(g.camps[i].pos, g.camps[j].pos) <= 1)
						key -= 600.f;
			if (key < best_key)
				best_key = key, best = i;
		}
		return best;
	};
	// Keep burst for a fight only when one is likely within the cooldown: an unused ready spell is lost value
	// (8-round cooldowns), and an enemy 7-9 tiles away led to a fight within 8 rounds only 13% of the time.
	const bool save_cc = enemy_near_d <= P.hold_cc_dist;
	const bool hold_spells = enemy_near_d <= P.hold_spell_dist && P.hold_spells_near_enemies;
	if (P.varg_splash_pos && type == CT::varg && can_move)
	{
		// Varg's splash hits every camp next to the target: stand next to the camp with the most live neighbours. From
		// below a vertical 3-wolf pack (rows) Varg reached only the end wolf and hit 2 of 3 (pack 31,4: 32 rounds with Cassi).
		auto live = [&](std::size_t i) { return g.hp[i] > 0 && W.camp_occ.is_set(g.camps[i].pos); };
		auto cover = [&](std::size_t i) {
			int n = 1;
			for (std::size_t j = 0; j < g.camps.size(); ++j)
				if (j != i && live(j) && cheb(g.camps[i].pos, g.camps[j].pos) <= 1)
					++n;
			return n;
		};
		int here = 0, best_n = 0;
		std::size_t bi = g.camps.size();
		for (std::size_t i = 0; i < g.camps.size(); ++i)
		{
			if (!live(i))
				continue;
			const int d = cheb(pos, g.camps[i].pos);
			if (d > 3)
				continue;
			const int n = cover(i);
			if (d <= 1)
				here = std::max(here, n);
			if (n > best_n)
				best_n = n, bi = i;
		}
		if (bi < g.camps.size() && best_n > here && best_n >= 2)
		{
			bc::bitboard goal;
			goal.draw_chebyshev(g.camps[bi].pos, 1.f);
			goal &= ~g.mask;
			goal &= ~W.walls;
			if (!goal.is_empty() && !goal.is_set(pos))
				step(goal, false, false);
		}
	}
	std::size_t t = pick(kit.attack_range);
	if (P.pxs_style && style_now() == 5 && t < g.camps.size() && can_move && !bc::map::bushes().is_set(pos))
	{
		// Proxy: ambusher farms from a bush next to it (unseen by passers-by; it opens on them).
		bc::bitboard goal;
		goal.draw_chebyshev(g.camps[t].pos, static_cast<float>(kit.attack_range));
		bc::bitboard adj;
		adj.draw_chebyshev(pos, 1.f);
		goal &= adj & bc::map::bushes() & ~W.walls & ~g.mask;
		if (!goal.is_empty() && step(goal, false, false))
		{
			t = pick(kit.attack_range);
			if (t == g.camps.size())
				return true;
		}
	}
	if (t == g.camps.size())
	{
		// The group field is rooted at every spawn tile, dead camps included; once we are "there" by the field,
		// close the last gap toward the live camps with a direct search.
		const auto& gf = nav().group_fields[static_cast<std::size_t>(g.id)];
		if (gf.ready && gf.get(pos) <= kit.attack_range)
		{
			bc::bitboard goal;
			for (std::size_t i = 0; i < g.camps.size(); ++i)
				if (g.hp[i] > 0 && (W.camp_occ.is_set(g.camps[i].pos) || (P.stuck_live_goal && !W.vis.is_set(g.camps[i].pos))))
					goal.draw_chebyshev(g.camps[i].pos, static_cast<float>(kit.attack_range));
			bc::bitboard any = goal;
			goal &= ~g.mask;
			IDL();
			bool stepped = false;
			if (!goal.is_empty())
				stepped = step(goal, false, true);
			else if (P.mi_close_in)
				stepped = go_group(g, 1, true); // in range by the field but no camp in sight (walls block vision): close in (default branch)
			if (!stepped && P.fz_dead && can_move)
			{
				// v14 fz_dead: the reach tiles off the group are none or out of a step: the dead tiles of the group are standable
				// (only live camps occupy theirs), so close in over them.
				any &= ~W.camp_occ & ~W.walls;
				IDL();
				if (!any.is_empty() && !any.is_set(pos))
					stepped = step(any, false, true);
				if (!stepped)
					go_group(g, 1, true);
			}
		}
		else
			IDL(), go_group(g, kit.attack_range, true);
		t = pick(kit.attack_range);
		if (t == g.camps.size())
		{
			IDL();
			int dlive = BIG;
			for (std::size_t i = 0; i < g.camps.size(); ++i)
				if (g.hp[i] > 0)
					dlive = std::min(dlive, cheb(pos, g.camps[i].pos));
			// only when a live camp is close but out of reach (a long group whose live camps are far down the row is a walk, not a wall:
			// yellow-brick-road gave its gold road away and lost 363-1019 instead of winning 1030-510)
			if (P.g23_reach > 0 && enemies_within(8) == 0 && dlive <= kit.attack_range + 3)
			{
				// v23 g23_reach: no camp in reach and still on the same tile: the camps' neighbour tiles are holes / walls / camps for
				// this kit (melee at hole-ringed camps on the-pond and islands stood 20-250 rounds).
				if (g23_rc_group != g.id || g23_rc_pos != pos)
					g23_rc_group = g.id, g23_rc_pos = pos, g23_rc_since = round;
				else if (round - g23_rc_since >= P.g23_reach)
				{
					blacklist[static_cast<std::size_t>(g.id)] = round + P.g23_reach_bl;
					g23_rc_group = -1;
					task_group = -1;
					task = T_NONE;
					return true;
				}
			}
			// Still out of attack range: if we are pinned in place this turn, use a range-4 spell.
			if (!can_move && !cast_done)
			{
				const std::size_t s4 = pick(4);
				if (s4 < g.camps.size() && !hold_spells)
					spells_on_camp(g, s4, save_cc);
			}
			return true;
		}
		// Melee can still swing after walking; ranged only after a dash (walking spends the attack).
		attack_chain_camp(g, t);
		return true;
	}
	if (obj_first && g.camps[t].str <= 0 && can_move)
	{
		// A gem cluster is in reach but an elk is not: ranged bodies stopped at the first camp in range and the
		// outer gem clusters of stampede's group died first while all six elks kept hitting (3,000 health of
		// damage spent under full fire). Step into reach of a camp that hits back.
		bc::bitboard goal;
		for (std::size_t i = 0; i < g.camps.size(); ++i)
			if (g.hp[i] > 0 && g.camps[i].str > 0 && W.camp_occ.is_set(g.camps[i].pos))
				goal.draw_chebyshev(g.camps[i].pos, static_cast<float>(kit.attack_range));
		goal &= ~g.mask;
		goal &= ~W.walls;
		if (!goal.is_empty() && !goal.is_set(pos) && step(goal, false, true))
		{
			const std::size_t t2 = pick(kit.attack_range);
			if (t2 < g.camps.size())
				attack_chain_camp(g, t2);
			return true;
		}
	}
	if (!hold_spells)
		spells_on_camp(g, t, save_cc);
	attack_chain_camp(g, t);
	return true;
}

#ifdef XM_TRACE
// ---------------------------------------------------------------------------------------------- prediction audit
// Every function below runs inside debug_block (fuel paused) and only prints and updates xm_* state, so an
// XM_TRACE build plays the same game as the plain build. tools/analysis/xm_audit.py joins the lines with
// the replay.

void Brain::xm_pre()
{
	auto& W = world();
	if (round == init_round && W.my_index == 0)
		for (const auto& g : W.groups)
		{
			int k[5] = { 0, 0, 0, 0, 0 };
			float str_sum = 0;
			for (const auto& c : g.camps)
				++k[std::min(4, std::max(0, static_cast<int>(c.type)))], str_sum += c.str;
			std::printf("GI g=%d n=%zu gems=%d gold=%d resp=%d mhp=%.0f str=%.0f wolf=%d elk=%d gem=%d gold_c=%d mono=%d ours=%d dh=%d cl=%.2f\n", g.id, g.camps.size(), g.gems, g.gold, g.respawn,
				g.max_hp, str_sum, k[0], k[1], k[2], k[3], k[4], static_cast<int>(g.ours), g.d_home_c, g.cluster);
		}
	// Per-round farming check: the prediction made at the end of our previous turn against what happened since
	// (our attack that turn, allies' attacks, then the camps' attacks at the start of this round).
	if (xm_pg >= 0 && xm_pr == round - 1)
	{
		const auto& g = W.groups[static_cast<std::size_t>(xm_pg)];
		if (g.seen_round == round)
		{
			const float dealt = std::max(0.f, xm_g_hp - g.hp_total);
			const float lost = std::max(0.f, xm_my_hp - hp);
			std::printf("FR r=%d ty=%d g=%d live=%d cl=%.2f myd=%.1f ad=%.1f claim=%d vis=%d pin=%.1f share=%.2f near=%.1f dealt=%.1f lost=%.1f clean=%d str=%.0f foc=%.0f hp=%.0f mhp=%.0f j=%d du=%d killed=%d share0=%.2f pres=%d reach=%.3f\n",
				round, static_cast<int>(type), xm_pg, xm_p_live, g.cluster, xm_p_my, xm_p_ally, xm_p_claim, xm_p_vis, xm_p_in, xm_p_share, xm_p_near, dealt, lost,
				static_cast<int>(xm_p_clean && enemies_within(8) == 0), str, focus, xm_my_hp, max_hp, static_cast<int>(jungle_done()), static_cast<int>(durability_done()),
				static_cast<int>(g.hp_total <= 0), xm_p_share0, static_cast<int>(xm_p_pres), xm_p_reach);
		}
	}
	xm_pg = -1;
	// Episode bookkeeping: health lost while engaged, and the group's death.
	if (xm_ep.g >= 0)
	{
		const auto& g = W.groups[static_cast<std::size_t>(xm_ep.g)];
		if (xm_ep.engage_r >= 0 && !xm_ep.away)
			xm_ep.lost += std::max(0.f, xm_my_hp - hp);
		if (g.st == ST_ALIVE)
			xm_ep.saw_alive = true;
		if (g.seen_round == round && (g.st == ST_REWARD || (g.st == ST_ALIVE && g.hp_total <= 0)))
			xm_close("kill");
		else if (g.seen_round == round && g.st == ST_RESPAWN && xm_ep.saw_alive)
			xm_close("gone");
	}
}

void Brain::xm_decide(int best)
{
	auto& W = world();
	if (best < 0 || best == xm_ep.g)
		return;
	if (xm_ep.g >= 0)
		xm_close("switch");
	const auto& g = W.groups[static_cast<std::size_t>(best)];
	if (g.st == ST_REWARD)
		return;
	ScoreParts sp;
	xm_sp = &sp;
	int eta = 0;
	group_score(g, eta);
	xm_sp = nullptr;
	xm_ep = XmEp{};
	xm_ep.g = best;
	xm_ep.commit_r = round;
	xm_ep.p = sp;
	xm_ep.g_hp_commit = g.st == ST_RESPAWN ? g.max_hp : g.hp_total;
	xm_ep.gv = gold_v;
	xm_ep.my_hp0 = hp;
}

void Brain::xm_close(const char* why)
{
	auto& W = world();
	if (xm_ep.g < 0)
		return;
	const auto& g = W.groups[static_cast<std::size_t>(xm_ep.g)];
	const auto& p = xm_ep.p;
	std::printf("FE r=%d ty=%d g=%d why=%s n=%zu gems=%d gold=%d elk=%d mono=%d commit=%d eng=%d pk=%.1f pd=%.1f pad=%.1f pcl=%d pin=%.1f psh=%.2f ptk=%.0f pbn=%.0f pbf=%.0f ptr=%d tc=%d ptime=%.1f peta=%d pwait=%d pval=%.1f psc=%.3f plan=%d ghpc=%.0f hp0=%.0f myhp0=%.0f mhp=%.0f ak=%d atot=%d lost=%.0f trips=%d psh0=%.2f ptk0=%.0f ptr0=%d seq=%.3f pres=%d peta0=%d gv=%.3f\n",
		round, static_cast<int>(type), xm_ep.g, why, g.camps.size(), g.gems, g.gold, static_cast<int>(g.elk), static_cast<int>(g.monolith), xm_ep.commit_r, xm_ep.engage_r, p.kill, p.my_dps,
		p.ally_dps, p.claimers, p.in, p.share, p.taken, p.budget_now, p.budget_full, p.trips, trip_cost(g), p.time, p.d_adj, p.wait, p.value, p.score, static_cast<int>(p.planned),
		xm_ep.g_hp_commit, xm_ep.hp0, xm_ep.my_hp0, max_hp, xm_ep.engage_r >= 0 ? round - xm_ep.engage_r : -1, round - xm_ep.commit_r, xm_ep.lost, xm_ep.trips,
		p.share0, p.taken0, p.trips0, p.seq, static_cast<int>(p.present), p.d0, xm_ep.gv);
	xm_ep = XmEp{};
}

void Brain::xm_dead()
{
	if (xm_was_alive)
	{
		std::printf("DTH r=%d ty=%d gems=%u task=%d g=%d\n", round, static_cast<int>(type), gems, task, task_group);
		xm_close("death");
	}
	xm_was_alive = false;
	xm_pg = -1;
}

void Brain::xm_post()
{
	auto& W = world();
	xm_was_alive = true;
	const int cur = (task == T_FARM || task == T_WAIT || task == T_CAPTURE) ? task_group : -1;
	if (xm_ep.g >= 0 && cur >= 0 && cur != xm_ep.g)
		xm_close("switch");
	if (xm_ep.g >= 0 && round - xm_ep.commit_r > 400)
		xm_close("timeout");
	if (xm_ep.g >= 0)
	{
		// A heal trip: home (walk or recall) and back to the same group.
		if (task == T_HOME || flag(state, bc::champion_state::recalling) || W.ally_spawn.is_set(pos))
			xm_ep.away = true;
		else if (cur == xm_ep.g && xm_ep.away)
			xm_ep.away = false, ++xm_ep.trips;
	}
	if (task == T_FARM && task_group >= 0)
	{
		const auto& g = W.groups[static_cast<std::size_t>(task_group)];
		bool in_range = false;
		int live = 0;
		float near_in = 0;
		for (std::size_t i = 0; i < g.camps.size(); ++i)
		{
			if (g.hp[i] <= 0)
				continue;
			++live;
			const int d = cheb(g.camps[i].pos, pos);
			in_range |= d <= kit.attack_range && W.camp_occ.is_set(g.camps[i].pos);
			if (d <= 3)
			{
				// Camps hit the nearest champion: count this camp only if no visible ally is strictly nearer.
				bool shielded = false;
				for (const auto& a : W.allies)
					if (a.handle != self && a.alive && a.visible && cheb(a.pos, g.camps[i].pos) < d)
						shielded = true;
				if (!shielded)
					near_in += g.camps[i].str;
			}
		}
		if (in_range && g.st == ST_ALIVE && g.hp_total > 0)
		{
			ScoreParts sp;
			xm_sp = &sp;
			int eta = 0;
			group_score(g, eta);
			xm_sp = nullptr;
			int vis = 0;
			for (const auto& a : W.allies)
				if (a.handle != self && a.alive && a.visible && cheb(a.pos, g.center) <= 4)
					++vis;
			xm_pg = g.id;
			xm_pr = round;
			xm_p_my = dps_on(g);
			xm_p_ally = sp.ally_dps;
			xm_p_in = incoming_on(g);
			xm_p_share = sp.planned ? sp.share : -1.f;
			xm_p_share0 = sp.planned ? sp.share0 : -1.f;
			xm_p_reach = sp.reach;
			xm_p_pres = sp.present;
			xm_p_claim = sp.claimers;
			xm_p_live = live;
			xm_p_vis = vis;
			xm_p_near = near_in;
			xm_g_hp = g.hp_total;
			xm_p_clean = enemies_within(8) == 0;
			if (xm_ep.g == g.id && xm_ep.engage_r < 0)
				xm_ep.engage_r = round, xm_ep.hp0 = g.hp_total;
		}
	}
	xm_my_hp = hp;
}

void Brain::xm_fight(float adv, float tku, float tkt, float ohp, float thp, float odps, float tdps, int na, int ne, int fight, int killable, int in_reach,
					 int can_escape, int isolated, int reserve, int tgt_type, int tgt_d, float incoming, float t_die, float tgt_hp, int backup, float my_dps)
{
	// Split of the estimate: allies (visible within 6) and enemies remembered but not visible now (seen in the
	// last threat_memory rounds within 9 + age) that combat() does not count.
	auto& W = world();
	float a_hp = 0, a_dps = 0, m_hp = 0, m_dps = 0;
	int m_n = 0;
	for (const auto& a : W.allies)
		if (a.handle != self && a.alive && a.visible && cheb(a.pos, pos) <= 6)
			a_hp += a.hp, a_dps += a.str + a.focus * best_mod(a.kit) / 8.f + std::max(a.str, a.focus * best_mod(a.kit)) / 3.f;
	for (const auto& e : W.enemies)
		if (e.alive && !e.visible && e.seen_round >= 0 && round - e.seen_round <= P.threat_memory && cheb(e.pos, pos) <= 9 + (round - e.seen_round) &&
			!W.enemy_spawn.is_set(e.pos))
			++m_n, m_hp += e.hp, m_dps += e.str + e.focus * best_mod(e.kit) / 8.f + e.burst() / 3.f;
	std::printf("FX r=%d ty=%d mydps=%.1f ahp=%.0f adps=%.1f mn=%d mhp=%.0f mdps=%.1f\n", round, static_cast<int>(type), my_dps, a_hp, a_dps, m_n, m_hp, m_dps);
	std::printf("FC r=%d ty=%d x=%d y=%d hp=%.0f mhp=%.0f gems=%u adv=%.3f tku=%.2f tkt=%.2f ohp=%.0f thp=%.0f odps=%.1f tdps=%.1f na=%d ne=%d fight=%d kill=%d reach=%d esc=%d iso=%d res=%d tt=%d td=%d inc=%.0f tdie=%.1f thp1=%.0f bk=%d sc=%.3f fm=%.2f\n",
		round, static_cast<int>(type), pos.x, pos.y, hp, max_hp, gems, adv, tku, tkt, ohp, thp, odps, tdps, na, ne, fight, killable, in_reach, can_escape, isolated, reserve, tgt_type, tgt_d,
		incoming, t_die, tgt_hp, backup, learner().fight_scale(), fight_margin);
}
#endif

// GOD v18 (patch 2.0.0): the build list for the new item families.
void Brain::g18_adjust_build()
{
	const bool focus_kit = type == CT::ren || type == CT_HOR || type == CT::stellar || type == CT::cassi || type == CT::prism ||
		(type == CT::tavi && !P.tavi_str) || type == CT::willow;
	const int dstat = focus_kit ? 1 : 0; // item_stat: strength 0, focus 1, health 2
	if (P.g18_treasure)
	{
		// Treasure (now +10% gold) -> Monster (now +15% camp damage) in the same stat; a list that already has a Monster run drops it.
		bool has_monster = false;
		for (const I it : build)
			has_monster |= item_fam(it) == FAM_MONSTER;
		std::vector<I> nb;
		nb.reserve(build.size());
		for (const I it : build)
		{
			if (item_fam(it) == FAM_TREASURE)
			{
				if (!has_monster)
					nb.push_back(item_of(FAM_MONSTER, item_stat_of(it)));
				continue;
			}
			nb.push_back(it);
		}
		build.swap(nb);
	}
	const bool gold_body = tpa::kit_of(static_cast<int>(type)).gold_mult > 1.0;
	auto insert_run = [&](int fam, int slot) {
		const std::size_t at = std::min(build.size(), static_cast<std::size_t>(std::max(0, slot)) * 5);
		build.insert(build.begin() + static_cast<std::ptrdiff_t>(at), 5, item_of(fam, dstat));
	};
	if (P.g18_tribute && gold_body)
		insert_run(FAM_TRIBUTE, P.g18_tribute_pos);
	if ((P.g18_capture == 1 && gold_body) || P.g18_capture == 2)
		insert_run(FAM_CAPTURE, P.g18_capture_pos);
	if (P.g18_greed)
		for (std::size_t i = 20; i < build.size(); ++i)
			if (item_fam(build[i]) == FAM_POWER)
				build[i] = item_of(FAM_GREED, item_stat_of(build[i]));
	item_flags_idx = static_cast<std::size_t>(-1);
}
