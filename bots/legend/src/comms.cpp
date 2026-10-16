#include "comms.h"

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
		help[static_cast<std::size_t>(i)] = (b[static_cast<std::size_t>(i)] & 0x80) != 0;
	}
	const std::uint16_t raw = static_cast<std::uint16_t>(b[6] | (b[7] << 8));
	if (raw != last_raw)
	{
		last_raw = raw;
		alert_round = round;
		alert_kind = raw >> 14;
		const int tile = raw & 0x3FFF;
		const int w = bc::map::width();
		alert_pos = { tile % w, tile / w };
	}
}

void Comms::write_self(int index, int group, bool needs_help)
{
	if (index < 0 || index >= 6)
		return;
	std::uint8_t v = group >= 0 && group < 126 ? static_cast<std::uint8_t>(group + 1) : 0;
	if (needs_help)
		v |= 0x80;
	bc::shared_memory[static_cast<std::size_t>(index)] = v;
	claim[static_cast<std::size_t>(index)] = group;
}

void Comms::post(int kind, vec2 tile, int round)
{
	const int idx = tile.y * bc::map::width() + tile.x;
	const std::uint16_t raw = static_cast<std::uint16_t>((kind << 14) | (idx & 0x3FFF));
	std::array<std::uint8_t, 2> b{ static_cast<std::uint8_t>(raw & 0xFF), static_cast<std::uint8_t>(raw >> 8) };
	bc::shared_memory.write(6, std::span<std::uint8_t>{ b });
	last_raw = raw;
	alert_kind = kind;
	alert_pos = tile;
	alert_round = round;
}
