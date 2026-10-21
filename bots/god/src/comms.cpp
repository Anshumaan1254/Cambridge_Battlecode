#include "comms.h"
#include "params.h"

Comms& comms()
{
	static Comms c;
	return c;
}

void Comms::read(int round)
{
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
	std::uint8_t v = group >= 0 && group < (bag_on ? 62 : 126) ? static_cast<std::uint8_t>(group + 1) : 0;
	// Keep bit 7 (team stance on bytes 0-1) and, with the bag sum, bit 6.
	const std::uint8_t old = bc::shared_memory[static_cast<std::size_t>(index)];
	v |= old & (bag_on ? 0xC0 : 0x80);
	bc::shared_memory[static_cast<std::size_t>(index)] = v;
	claim[static_cast<std::size_t>(index)] = group;
}

void Comms::write_stance(int s)
{
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
