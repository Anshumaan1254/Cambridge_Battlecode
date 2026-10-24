// teamplan/live.h: a 64-bit live protocol for the team's 8 shared bytes (TEAMPLAN.md 4, P2 and D2). For a new bot; GOD v10 keeps its own
// layout. Rules from the postmortems (smite, 4 Musketeers, Lorem Ipsum, food): one owner per field, indices into tables both sides
// computed in the draft instead of raw data, and everything expires.
//   bits 10b .. 10b+9, body slot b = 0..5 (written only by body b):
//     claim  6 bits  group index 0..62 it is working on (63 = none)
//     status 2 bits  its progress code (swap.h) or a role state
//     beat   1 bit   toggled every turn it acts: a field whose beat has not changed for two rounds is stale (dead body, lost turn)
//     flag   1 bit   carrying at least the hunt threshold (bag.h), so allies escort or bank first
//   bits 60..63, written only by the lowest alive slot: cursor 3 bits (the plan variant in use: assign.h variants, swap.h) and
//   tiebreak 1 bit (tiebreak.h mode, so every body agrees)
// A body reads the 8 bytes, changes only its own field, and writes them back in the same turn (turns never overlap).
// Python twin: tools/teamplan/live.py.
#pragma once
#include <cstdint>

namespace teamplan
{
struct BodyField
{
	int claim = 63, status = 0, beat = 0, flag = 0;
};

inline std::uint64_t load64(const std::uint8_t* b)
{
	std::uint64_t v = 0;
	for (int i = 7; i >= 0; --i)
		v = (v << 8) | b[i];
	return v;
}
inline void store64(std::uint64_t v, std::uint8_t* b)
{
	for (int i = 0; i < 8; ++i)
		b[i] = static_cast<std::uint8_t>(v >> (8 * i));
}

inline BodyField get_body(std::uint64_t v, int slot)
{
	const unsigned f = static_cast<unsigned>(v >> (10 * slot)) & 0x3FFu;
	BodyField o;
	o.claim = static_cast<int>(f & 63u), o.status = static_cast<int>(f >> 6 & 3u), o.beat = static_cast<int>(f >> 8 & 1u), o.flag = static_cast<int>(f >> 9 & 1u);
	return o;
}
inline std::uint64_t set_body(std::uint64_t v, int slot, const BodyField& o)
{
	const std::uint64_t f = static_cast<std::uint64_t>((o.claim & 63) | (o.status & 3) << 6 | (o.beat & 1) << 8 | (o.flag & 1) << 9);
	const std::uint64_t mask = 0x3FFull << (10 * slot);
	return (v & ~mask) | (f << (10 * slot));
}
inline int get_cursor(std::uint64_t v) { return static_cast<int>(v >> 60 & 7u); }
inline int get_tiebreak(std::uint64_t v) { return static_cast<int>(v >> 63 & 1u); }
inline std::uint64_t set_team(std::uint64_t v, int cursor, int tiebreak)
{
	return (v & 0x0FFFFFFFFFFFFFFFull) | (static_cast<std::uint64_t>(cursor & 7) << 60) | (static_cast<std::uint64_t>(tiebreak & 1) << 63);
}

// Staleness: the reader keeps the beat it saw and the round it last changed.
struct Beat
{
	int last = -1, since = 0;
};
inline bool beat_stale(Beat& s, int beat, int round)
{
	if (beat != s.last)
		s.last = beat, s.since = round;
	return round - s.since >= 2;
}
} // namespace teamplan
