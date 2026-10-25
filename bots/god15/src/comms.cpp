#include "comms.h"
#include "params.h"
#include "mi_game.h"
#include "teamplan/live.h"
#include "world.h"

#include <algorithm>

Comms& comms()
{
	static Comms c;
	return c;
}

void Comms::read(int round)
{
	if (P.mi_live)
	{
		if (!live_ready)
			live_setup();
		const std::uint64_t v = live_load();
		int flags = 0;
		for (int i = 0; i < 6; ++i)
		{
			claim[static_cast<std::size_t>(i)] = -1;
			const int s = live_slot[i];
			if (s < 0)
				continue;
			const auto f = teamplan::get_body(v, s);
			claim[static_cast<std::size_t>(i)] = f.claim < live_ngroups ? f.claim : -1;
			if (i != my_index_live)
				flags += f.flag;
		}
		live_others = flags * P.live_bag_flag;
		stance = teamplan::get_cursor(v) & 3;
		const unsigned af = teamplan::alert_bits(v);
		if (af != live_alert_field)
		{
			live_alert_field = af;
			alert_round = round;
			const auto a = teamplan::get_alert(v);
			int idx = -1;
			const int k = a.place == teamplan::NO_PLACE ? teamplan::PLACE_NONE
						  : teamplan::place_kind(teamplan::Places{ live_ngroups, live_naltars, live_nrally }, a.place, &idx);
			if (k == teamplan::PLACE_NONE || a.place >= live_np)
				alert_kind = AL_NONE, alert_pos = { -1, -1 };
			else
			{
				alert_kind = a.kind == teamplan::ALERT_HELP ? AL_RALLY : a.kind == teamplan::ALERT_KILL ? AL_OPPORTUNITY : AL_DANGER;
				alert_pos = { live_px[a.place], live_py[a.place] };
			}
		}
		return;
	}
	std::array<std::uint8_t, 8> b{};
	bc::shared_memory.read(0, std::span<std::uint8_t>{ b });
	bag_tens = 0;
	for (int i = 0; i < 6; ++i)
	{
		const int v = b[static_cast<std::size_t>(i)] & (bag_on ? 0x3F : 0x7F);
		claim[static_cast<std::size_t>(i)] = v == 0 ? -1 : v - 1;
		bag_tens |= ((b[static_cast<std::size_t>(i)] >> 6) & 1) << i;
	}
	if (!bag_on)
		bag_tens = 0;
	stance = ((b[0] >> 7) & 1) | (((b[1] >> 7) & 1) << 1);
	if (P.opp_plan)
		plan9 = ((b[3] >> 7) & 1) | (((b[4] >> 7) & 1) << 1) | (((b[5] >> 7) & 1) << 2);
	if (P.opp_model)
	{
		plan = stance | (((b[2] >> 7) & 1) << 2);
		inv_count = ((b[3] >> 7) & 1) | (((b[4] >> 7) & 1) << 1) | (((b[5] >> 7) & 1) << 2);
	}
	const std::uint16_t raw = static_cast<std::uint16_t>(b[6] | (b[7] << 8));
	// Bit 7 of byte 2 flips on every post: re-posting the same alert (a fight still going on at one tile)
	// refreshes it for the team instead of letting it expire (P.alert_refresh).
	const int toggle = P.alert_refresh && !P.opp_model ? (b[2] >> 7) & 1 : 0; // the plan id owns byte 2's bit 7 when the model is on
	if ((P.g15_lock & 2) && t4_free())
	{
		int v = 0;
		for (int i = 0; i < 4; ++i)
			v |= ((b[static_cast<std::size_t>(2 + i)] >> 7) & 1) << i;
		if (v != t4 || raw != last_raw)
			t4 = v, t4_deadline = v > 0 ? round + 4 * v : -1;
	}
	if (raw != last_raw || toggle != last_toggle)
	{
		last_raw = raw;
		last_toggle = toggle;
		alert_round = round;
		alert_kind = raw >> 14;
		const int tile = raw & 0x3FFF;
		const int w = bc::map::width();
		alert_pos = { tile % w, tile / w };
	}
}

void Comms::write_self(int index, int group)
{
	if (index < 0 || index >= 6)
		return;
	if (P.mi_live)
	{
		if (!live_ready)
			live_setup();
		my_index_live = index;
		live_store(live_my_field(live_load(), index, live_code_of_group(group), -1, static_cast<int>(bc::round_number())));
		claim[static_cast<std::size_t>(index)] = group;
		return;
	}
	std::uint8_t v = group >= 0 && group < (bag_on ? 62 : 126) ? static_cast<std::uint8_t>(group + 1) : 0;
	// Keep bit 7 (team stance on bytes 0-1) and, with the bag sum, bit 6.
	const std::uint8_t old = bc::shared_memory[static_cast<std::size_t>(index)];
	v |= old & (bag_on ? 0xC0 : 0x80);
	bc::shared_memory[static_cast<std::size_t>(index)] = v;
	claim[static_cast<std::size_t>(index)] = group;
}

void Comms::write_stance(int s)
{
	if (P.mi_live)
	{
		const std::uint64_t v = live_load();
		live_store(teamplan::set_team(v, s & 3, teamplan::get_tiebreak(v)));
		stance = s;
		return;
	}
	for (int i = 0; i < 2; ++i)
	{
		const std::uint8_t old = bc::shared_memory[static_cast<std::size_t>(i)];
		const std::uint8_t bit = static_cast<std::uint8_t>(((s >> i) & 1) << 7);
		bc::shared_memory[static_cast<std::size_t>(i)] = static_cast<std::uint8_t>((old & 0x7F) | bit);
	}
	stance = s;
}

void Comms::write_plan(int id)
{
	// Same bits as the stance for ids 0-2 (byte 2's bit 7 stays 0), so a model that detects nothing writes the v8 bytes.
	for (int i = 0; i < 3; ++i)
	{
		const std::uint8_t old = bc::shared_memory[static_cast<std::size_t>(i)];
		const std::uint8_t bit = static_cast<std::uint8_t>(((id >> i) & 1) << 7);
		bc::shared_memory[static_cast<std::size_t>(i)] = static_cast<std::uint8_t>((old & 0x7F) | bit);
	}
	plan = id;
	stance = id & 3;
}

void Comms::bump_invasion()
{
	int v = 0;
	for (int i = 0; i < 3; ++i)
		v |= ((bc::shared_memory[static_cast<std::size_t>(3 + i)] >> 7) & 1) << i;
	v = std::min(7, v + 1);
	for (int i = 0; i < 3; ++i)
	{
		const std::uint8_t old = bc::shared_memory[static_cast<std::size_t>(3 + i)];
		bc::shared_memory[static_cast<std::size_t>(3 + i)] = static_cast<std::uint8_t>((old & 0x7F) | (((v >> i) & 1) << 7));
	}
	inv_count = v;
}

void Comms::reset_invasion()
{
	for (int i = 0; i < 3; ++i)
	{
		const std::uint8_t old = bc::shared_memory[static_cast<std::size_t>(3 + i)];
		bc::shared_memory[static_cast<std::size_t>(3 + i)] = static_cast<std::uint8_t>(old & 0x7F);
	}
	inv_count = 0;
}

void Comms::post(int kind, vec2 tile, int round)
{
	if (P.mi_live)
	{
		if (!live_ready)
			live_setup();
		const int place = teamplan::nearest_place(live_px, live_py, live_np, tile.x, tile.y);
		if (place == teamplan::NO_PLACE)
			return;
		teamplan::Alert a;
		a.place = place;
		int idx = -1;
		const bool at_altar = teamplan::place_kind(teamplan::Places{ live_ngroups, live_naltars, live_nrally }, place, &idx) == teamplan::PLACE_ALTAR &&
							  cheb(tile, vec2{ live_px[place], live_py[place] }) <= 1;
		a.kind = kind == AL_RALLY ? teamplan::ALERT_HELP : kind == AL_OPPORTUNITY ? teamplan::ALERT_KILL : at_altar ? teamplan::ALERT_ALTAR : teamplan::ALERT_ARMY;
		int n = 0;
		for (const auto& e : world().enemies)
			n += e.alive && e.visible && cheb(e.pos, tile) <= 3 ? 1 : 0;
		a.count = std::clamp(n, 1, 4);
		// live.h's post rule: replace the current alert only when it is missing, older than 5 rounds, ranks lower, or is this sighting
		const std::uint64_t v = live_load();
		const auto cur = teamplan::get_alert(v);
		const int age = round - alert_round;
		const bool none = cur.place == teamplan::NO_PLACE || alert_kind == AL_NONE;
		if (!(none || age >= 5 || a.kind > cur.kind || (a.kind == cur.kind && a.place == cur.place)))
			return;
		a.seq = (cur.seq + 1) & 3;
		const std::uint64_t w = teamplan::set_alert(v, a);
		live_store(w);
		live_alert_field = teamplan::alert_bits(w);
		alert_kind = kind;
		alert_pos = { live_px[place], live_py[place] };
		alert_round = round;
		return;
	}
	const int idx = tile.y * bc::map::width() + tile.x;
	const std::uint16_t raw = static_cast<std::uint16_t>((kind << 14) | (idx & 0x3FFF));
	std::array<std::uint8_t, 2> b{ static_cast<std::uint8_t>(raw & 0xFF), static_cast<std::uint8_t>(raw >> 8) };
	bc::shared_memory.write(6, std::span<std::uint8_t>{ b });
	if (P.alert_refresh && !P.opp_model)
	{
		const std::uint8_t old = bc::shared_memory[2];
		bc::shared_memory[2] = static_cast<std::uint8_t>(old ^ 0x80);
		last_toggle = (old >> 7) ^ 1;
	}
	last_raw = raw;
	alert_kind = kind;
	alert_pos = tile;
	alert_round = round;
}

void Comms::write_t4(int v)
{
	if (!t4_free())
		return;
	v = std::clamp(v, 0, 15);
	for (int i = 0; i < 4; ++i)
	{
		const auto k = static_cast<std::size_t>(2 + i);
		const std::uint8_t old = bc::shared_memory[k];
		bc::shared_memory[k] = static_cast<std::uint8_t>((old & 0x7F) | (((v >> i) & 1) << 7));
	}
	t4 = v;
	t4_deadline = v > 0 ? static_cast<int>(bc::round_number()) + 4 * v : -1;
}

void Comms::write_plan9(int p)
{
	for (int i = 0; i < 3; ++i)
	{
		const auto k = static_cast<std::size_t>(3 + i);
		const std::uint8_t old = bc::shared_memory[k];
		bc::shared_memory[k] = static_cast<std::uint8_t>((old & 0x7F) | (((p >> i) & 1) << 7));
	}
	plan9 = p;
}

void Comms::set_contact()
{
	if (P.alert_refresh)
		return; // bit 7 of byte 2 is the alert toggle then
	const std::uint8_t old = bc::shared_memory[2];
	if (!(old & 0x80))
		bc::shared_memory[2] = static_cast<std::uint8_t>(old | 0x80);
}

bool Comms::take_contact()
{
	if (P.alert_refresh)
		return false;
	const std::uint8_t old = bc::shared_memory[2];
	if (!(old & 0x80))
		return false;
	bc::shared_memory[2] = static_cast<std::uint8_t>(old & 0x7F);
	return true;
}

void Comms::write_bag(int gems)
{
	if (P.mi_live)
	{
		if (my_index_live >= 0)
			live_store(live_my_field(live_load(), my_index_live, -2, gems >= P.live_bag_flag ? 1 : 0, static_cast<int>(bc::round_number())));
		return;
	}
	// Turns within a team are sequential, so a read-modify-write of the sum is safe; each body only ever adds the
	// change of its own share, so the sum stays exact (6 bodies x 10 <= 63, no saturation).
	if (!bag_on)
		return;
	const int mine = std::clamp(gems / 10, 0, 10);
	int s = 0;
	for (int i = 0; i < 6; ++i)
		s |= ((bc::shared_memory[static_cast<std::size_t>(i)] >> 6) & 1) << i;
	s = std::clamp(s + mine - my_bag, 0, 63);
	for (int i = 0; i < 6; ++i)
	{
		const std::uint8_t old = bc::shared_memory[static_cast<std::size_t>(i)];
		bc::shared_memory[static_cast<std::size_t>(i)] = static_cast<std::uint8_t>((old & ~0x40) | (((s >> i) & 1) << 6));
	}
	my_bag = mine;
	bag_tens = s;
}

// ---- P.mi_live (GOD v12)
void Comms::live_setup()
{
	live_ready = true;
	const auto& W = world();
	int types[6];
	int n = 0;
	for (const auto& a : W.allies)
		if (n < 6)
			types[n++] = static_cast<int>(a.type);
	for (int i = 0; i < n; ++i)
		live_slot[i] = teamplan::live_slot_of(types, n, types[i]);
	// places: groups (camp_groups() order, the group's centre tile), altars (ascending tile index), the draft's rally tiles
	live_ngroups = std::min<int>(static_cast<int>(W.groups.size()), teamplan::NO_PLACE);
	live_np = 0;
	for (int g = 0; g < live_ngroups; ++g)
		live_px[live_np] = W.groups[static_cast<std::size_t>(g)].center.x, live_py[live_np++] = W.groups[static_cast<std::size_t>(g)].center.y;
	std::vector<int> al;
	for (const auto a : W.altars)
		al.push_back(a.y * W.W + a.x);
	std::sort(al.begin(), al.end());
	live_naltars = 0;
	for (const int t : al)
		if (live_np < teamplan::NO_PLACE)
			live_px[live_np] = t % W.W, live_py[live_np++] = t / W.W, ++live_naltars;
	int rt[8];
	const int nr = mig::rallies(rt);
	live_nrally = 0;
	for (int k = 0; k < nr; ++k)
		if (live_np < teamplan::NO_PLACE)
			live_px[live_np] = rt[k] % W.W, live_py[live_np++] = rt[k] / W.W, ++live_nrally;
	my_index_live = W.my_index;
}

int Comms::live_code_of_group(int g) const { return g >= 0 && g < live_ngroups ? g : teamplan::NO_PLACE; }

std::uint64_t Comms::live_load() const
{
	std::uint8_t b[8] = {};
	bc::shared_memory.read(0, std::span<std::uint8_t>{ b });
	return teamplan::load64(b);
}

void Comms::live_store(std::uint64_t v) const
{
	std::uint8_t b[8];
	teamplan::store64(v, b);
	bc::shared_memory.write(0, std::span<const std::uint8_t>{ b });
}

// our field: claim_code -2 = keep, flag -1 = keep; the beat toggles once per round
std::uint64_t Comms::live_my_field(std::uint64_t v, int index, int claim_code, int flag, int round)
{
	const int s = index >= 0 && index < 6 ? live_slot[index] : -1;
	if (s < 0)
		return v;
	auto f = teamplan::get_body(v, s);
	if (claim_code != -2)
		f.claim = claim_code;
	if (flag >= 0)
		f.flag = flag;
	if (round != live_beat_round)
		live_beat_round = round, live_beat ^= 1;
	f.beat = live_beat;
	return teamplan::set_body(v, s, f);
}
