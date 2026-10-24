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
// Slots: the allies' body types in ascending order (`live_slot_of`); the draft memory's TEAM block lists them in the same order.
// A dead champion keeps its turns (it may shop), so it keeps beating: it publishes claim 63 (none) while dead. A field goes stale only
// when its body loses turns (fuel) or stops publishing (`field_stale`). The memory starts at zero, so a slot counts as live only after
// it has published once (`LiveState::ever`).
// The per-turn layer (`LiveState`, `live_observe`, `live_compose`) is pure; live_sdk.h reads and writes the SDK's bytes.
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

// A slot's liveness from the field this body reads each turn. The beat toggles every turn its owner acts, so a change of the beat or of
// any bit of the field is a sign of life. A reader that skipped a round (it lost its own turn) cannot tell two toggles from none, so a
// field that did not change across one skipped round gets one round of doubt, once in a row (a second such gap without change does not
// renew it, so a stopped body still goes stale). Found by the engine test: the tester body loses turns, and with the plain beat_stale
// it saw beating allies as stale.
struct FieldWatch
{
	int since = 0, obs = -1;	// round of the last sign of life; round of the last observation (-1 = none)
	unsigned field = 0;		 // the field seen at the last observation
	bool doubted = false;	 // the last observation used the doubt
};
inline bool field_stale(FieldWatch& s, unsigned field, int round)
{
	if (s.obs < 0 || field != s.field)
		s.since = round, s.doubted = false;
	else if (round - s.obs == 2 && !s.doubted)
		s.since = s.since > round - 1 ? s.since : round - 1, s.doubted = true;
	s.field = field, s.obs = round;
	return round - s.since >= 2;
}

// This body's slot: the number of allies with a lower body type (types are distinct; a two-body pick gives two types).
inline int live_slot_of(const int* types, int n, int my_type)
{
	int s = 0;
	for (int i = 0; i < n; ++i)
		s += types[i] < my_type ? 1 : 0;
	return s;
}

// One body's view of the live bytes, kept across its turns.
struct LiveState
{
	int slot = -1, n = 0;	 // our slot and the slots in use (at most 6)
	int beat = 0;			 // our heartbeat bit (toggled by every live_compose)
	FieldWatch watch[6];	 // per slot: the field seen and the round of its last sign of life
	unsigned ever = 0;		 // bit s: slot s has published at least once (a nonzero field, or a change, was seen)
	unsigned live = 0;		 // bit s: slot s is live this turn (seen beating, not stale); our own slot always
	std::uint64_t seen = 0;	 // the bytes as read this turn
};

// Start of a turn: record the bytes read and refresh which slots are live.
inline void live_observe(LiveState& L, std::uint64_t seen, int round)
{
	L.seen = seen;
	L.live = 0;
	for (int s = 0; s < L.n && s < 6; ++s)
	{
		if (s == L.slot)
		{
			L.live |= 1u << s;
			continue;
		}
		const unsigned f = static_cast<unsigned>(seen >> (10 * s)) & 0x3FFu;
		if (f != 0 || (L.watch[s].obs >= 0 && f != L.watch[s].field))
			L.ever |= 1u << s;
		const bool stale = field_stale(L.watch[s], f, round);
		if ((L.ever >> s & 1u) && !stale)
			L.live |= 1u << s;
	}
}

// The bytes to write back: our field with the beat toggled; the team bits too when no lower slot is live (the lowest live slot owns
// them). `writer` (optional) says whether we wrote the team bits.
inline std::uint64_t live_compose(LiveState& L, int claim, int status, int flag, int cursor, int tiebreak, bool* writer = nullptr)
{
	L.beat ^= 1;
	BodyField o;
	o.claim = claim, o.status = status, o.beat = L.beat, o.flag = flag;
	std::uint64_t v = set_body(L.seen, L.slot, o);
	const bool w = (L.live & ((1u << L.slot) - 1u)) == 0;
	if (w)
		v = set_team(v, cursor, tiebreak);
	if (writer)
		*writer = w;
	return v;
}
} // namespace teamplan
