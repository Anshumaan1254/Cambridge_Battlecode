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
	for (int i = 0; i < 6; ++i)
	{
		const int v = b[static_cast<std::size_t>(i)] & 0x7F;
		claim[static_cast<std::size_t>(i)] = v == 0 ? -1 : v - 1;
	}
	stance = ((b[0] >> 7) & 1) | (((b[1] >> 7) & 1) << 1);
	const std::uint16_t raw = static_cast<std::uint16_t>(b[6] | (b[7] << 8));
	// Bit 7 of byte 2 flips on every post: re-posting the same alert (a fight still going on at one tile)
	// refreshes it for the team instead of letting it expire (P.alert_refresh).
	const int toggle = P.alert_refresh ? (b[2] >> 7) & 1 : 0;
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
	std::uint8_t v = group >= 0 && group < 126 ? static_cast<std::uint8_t>(group + 1) : 0;
	// Keep bit 7: it carries the team stance on bytes 0-1.
	const std::uint8_t old = bc::shared_memory[static_cast<std::size_t>(index)];
	v |= old & 0x80;
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

void Comms::post(int kind, vec2 tile, int round)
{
	const int idx = tile.y * bc::map::width() + tile.x;
	const std::uint16_t raw = static_cast<std::uint16_t>((kind << 14) | (idx & 0x3FFF));
	std::array<std::uint8_t, 2> b{ static_cast<std::uint8_t>(raw & 0xFF), static_cast<std::uint8_t>(raw >> 8) };
	bc::shared_memory.write(6, std::span<std::uint8_t>{ b });
	if (P.alert_refresh)
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
