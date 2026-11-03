// teamplan/live.h: a 64-bit live protocol for the team's 8 shared bytes (TEAMPLAN.md 4, P2 and D2; 11.6-11.7). For a new bot; GOD v10
// keeps its own layout. Rules from the postmortems (smite, 4 Musketeers, Lorem Ipsum, food): one owner per field, indices into tables
// every body computes the same way instead of raw tiles, and everything expires. Vision is not shared between allies, so the alert is
// the only way a body learns what another one sees.
//   bits 8b .. 8b+7, body slot b = 0..5 (written only by body b):
//     claim  6 bits  the place it is working on (a place code, below: a group it farms, an altar it banks at, a rally tile; 63 = none)
//     beat   1 bit   toggled every turn it publishes (staleness, below)
//     flag   1 bit   carrying at least the hunt threshold (bag.h), so allies escort or it banks first
//   bits 48..59, the team alert, written by any body under the post rule (live_compose):
//     place  6 bits  where (a place code, stored + 1 so that the all-zero start means "no alert")
//     kind   2 bits  0 an enemy army (keep away, do not walk in alone), 1 an enemy at an altar (its tribute can be cancelled by a stun or
//                    a lock; or it threatens ours), 2 a kill chance (an enemy with low health or a big bag), 3 help (an ally fights there);
//                    the kind is also the alert's rank
//     count  2 bits  enemies seen there, 1..4 (stored 0..3; 4 = four or more)
//     seq    2 bits  bumped by every post, so a repost of the same sighting still changes the field
//   bits 60..63, written only by the lowest live slot: cursor 3 bits (the plan variant in use) and tiebreak 1 bit (tiebreak.h mode, so
//   every body agrees)
// The 2-bit progress code of swap.h had a slot in each body's field in the first version; the alert took those 12 bits (TEAMPLAN.md 11.7).
// A body reads the 8 bytes, changes only its own field (and the alert or team bits under their rules), and writes them back in the same
// turn (turns never overlap).
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
// ---- places: the vocabulary of claims and alerts
// The map's camp groups (in the SDK's camp_groups() order), then the altars (ascending tile index y * W + x), then the draft's rally
// tiles (the CODE block of docs/DRAFT_MEMORY.md, in its order). Codes 0..62, 63 = none; places past 62 have no code (the rally tiles
// go first, then the last altars).
struct Places
{
	int groups = 0, altars = 0, rallies = 0;
};
inline constexpr int PLACE_NONE = 0, PLACE_GROUP = 1, PLACE_ALTAR = 2, PLACE_RALLY = 3, NO_PLACE = 63;

inline int place_code(const Places& P, int kind, int index)
{
	int base = 0, cnt = 0;
	if (kind == PLACE_GROUP)
		base = 0, cnt = P.groups;
	else if (kind == PLACE_ALTAR)
		base = P.groups, cnt = P.altars;
	else if (kind == PLACE_RALLY)
		base = P.groups + P.altars, cnt = P.rallies;
	else
		return NO_PLACE;
	if (index < 0 || index >= cnt || base + index >= NO_PLACE)
		return NO_PLACE;
	return base + index;
}

// The kind of a code (PLACE_NONE for 63 or a code past the list); `index` (optional) = its index in that kind's list, or -1.
inline int place_kind(const Places& P, int code, int* index = nullptr)
{
	int k = PLACE_NONE, i = -1;
	if (code >= 0 && code < NO_PLACE)
	{
		if (code < P.groups)
			k = PLACE_GROUP, i = code;
		else if (code < P.groups + P.altars)
			k = PLACE_ALTAR, i = code - P.groups;
		else if (code < P.groups + P.altars + P.rallies)
			k = PLACE_RALLY, i = code - P.groups - P.altars;
	}
	if (index)
		*index = i;
	return k;
}

// The place nearest to a tile, by Chebyshev distance, ties to the lower code: where a body reports a sighting. xs / ys: the n place
// tiles in code order (a group's representative tile, an altar, a rally tile). NO_PLACE when n is 0.
inline int nearest_place(const int* xs, const int* ys, int n, int x, int y)
{
	int best = NO_PLACE, bd = 0;
	for (int i = 0; i < n && i < NO_PLACE; ++i)
	{
		const int dx = xs[i] > x ? xs[i] - x : x - xs[i], dy = ys[i] > y ? ys[i] - y : y - ys[i];
		const int d = dx > dy ? dx : dy;
		if (best == NO_PLACE || d < bd)
			best = i, bd = d;
	}
	return best;
}

// ---- the 64-bit word
struct BodyField
{
	int claim = NO_PLACE, beat = 0, flag = 0;
};
struct Alert
{
	int place = NO_PLACE, kind = 0, count = 1, seq = 0;	 // count 1..4
};
inline constexpr int ALERT_ARMY = 0, ALERT_ALTAR = 1, ALERT_KILL = 2, ALERT_HELP = 3;

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
	const unsigned f = static_cast<unsigned>(v >> (8 * slot)) & 0xFFu;
	BodyField o;
	o.claim = static_cast<int>(f & 63u), o.beat = static_cast<int>(f >> 6 & 1u), o.flag = static_cast<int>(f >> 7 & 1u);
	return o;
}
inline std::uint64_t set_body(std::uint64_t v, int slot, const BodyField& o)
{
	const std::uint64_t f = static_cast<std::uint64_t>((o.claim & 63) | (o.beat & 1) << 6 | (o.flag & 1) << 7);
	const std::uint64_t mask = 0xFFull << (8 * slot);
	return (v & ~mask) | (f << (8 * slot));
}

inline unsigned alert_bits(std::uint64_t v) { return static_cast<unsigned>(v >> 48) & 0xFFFu; }
inline Alert get_alert(std::uint64_t v)
{
	const unsigned f = alert_bits(v);
	Alert a;
	a.place = static_cast<int>((f & 63u) + 63u) & 63;  // stored + 1: 0 means none
	a.kind = static_cast<int>(f >> 6 & 3u), a.count = static_cast<int>(f >> 8 & 3u) + 1, a.seq = static_cast<int>(f >> 10 & 3u);
	return a;
}
inline std::uint64_t set_alert(std::uint64_t v, const Alert& a)
{
	const int c = a.count < 1 ? 1 : a.count > 4 ? 4 : a.count;
	const std::uint64_t f = static_cast<std::uint64_t>(((a.place + 1) & 63) | (a.kind & 3) << 6 | (c - 1) << 8 | (a.seq & 3) << 10);
	return (v & ~(0xFFFull << 48)) | (f << 48);
}

inline int get_cursor(std::uint64_t v) { return static_cast<int>(v >> 60 & 7u); }
inline int get_tiebreak(std::uint64_t v) { return static_cast<int>(v >> 63 & 1u); }
inline std::uint64_t set_team(std::uint64_t v, int cursor, int tiebreak)
{
	return (v & 0x0FFFFFFFFFFFFFFFull) | (static_cast<std::uint64_t>(cursor & 7) << 60) | (static_cast<std::uint64_t>(tiebreak & 1) << 63);
}

// ---- staleness
// The plain 1-bit check (kept for the codec sweep): the reader keeps the beat it saw and the round it last changed.
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

// ---- the per-turn layer
// One body's view of the live bytes, kept across its turns.
struct LiveState
{
	int slot = -1, n = 0;	 // our slot and the slots in use (at most 6)
	int ttl = 5;			 // ASSUMED: rounds an alert stays current (enemies move; a post may replace an older alert)
	int beat = 0;			 // our heartbeat bit (toggled by every live_compose)
	FieldWatch watch[6];	 // per slot: the field seen and the round of its last sign of life
	unsigned ever = 0;		 // bit s: slot s has published at least once (a nonzero field, or a change, was seen)
	unsigned live = 0;		 // bit s: slot s is live this turn (seen beating, not stale); our own slot always
	std::uint64_t seen = 0;	 // the bytes as read this turn
	int round = 0;			 // the round of the last live_observe
	Alert alert;			 // the team alert as read this turn (place NO_PLACE = none)
	int alert_age = 99;		 // rounds since its field last changed, as this body saw it (99 = none)
	unsigned alert_field = 0;
	int alert_since = 0, alert_obs = -1;
};

// Start of a turn: record the bytes read, refresh which slots are live, and age the alert.
inline void live_observe(LiveState& L, std::uint64_t seen, int round)
{
	L.seen = seen;
	L.round = round;
	L.live = 0;
	for (int s = 0; s < L.n && s < 6; ++s)
	{
		if (s == L.slot)
		{
			L.live |= 1u << s;
			continue;
		}
		const unsigned f = static_cast<unsigned>(seen >> (8 * s)) & 0xFFu;
		if (f != 0 || (L.watch[s].obs >= 0 && f != L.watch[s].field))
			L.ever |= 1u << s;
		const bool stale = field_stale(L.watch[s], f, round);
		if ((L.ever >> s & 1u) && !stale)
			L.live |= 1u << s;
	}
	const unsigned af = alert_bits(seen);
	if (L.alert_obs < 0 || af != L.alert_field)
		L.alert_since = round;
	L.alert_field = af, L.alert_obs = round;
	L.alert = get_alert(seen);
	L.alert_age = L.alert.place == NO_PLACE ? 99 : round - L.alert_since;
}

// Whether a post replaces the current alert: there is none, it is older than ttl, ours ranks higher, or ours is the same sighting (same
// kind and place: a refresh). Otherwise the current one stays: first come, first served, so two posters do not flip it every turn.
inline bool alert_accepts(const LiveState& L, const Alert& post)
{
	const Alert& c = L.alert;
	return c.place == NO_PLACE || L.alert_age >= L.ttl || post.kind > c.kind || (post.kind == c.kind && post.place == c.place);
}

// The bytes to write back: our field with the beat toggled; the team bits too when no lower slot is live (the lowest live slot owns
// them); and our alert when `post` is given and the post rule accepts it (its seq is the current one + 1). `writer` / `posted`
// (optional) say whether we wrote the team bits / the alert.
inline std::uint64_t live_compose(LiveState& L, int claim, int flag, int cursor, int tiebreak, const Alert* post = nullptr, bool* writer = nullptr,
								  bool* posted = nullptr)
{
	L.beat ^= 1;
	BodyField o;
	o.claim = claim, o.beat = L.beat, o.flag = flag;
	std::uint64_t v = set_body(L.seen, L.slot, o);
	const bool w = (L.live & ((1u << L.slot) - 1u)) == 0;
	if (w)
		v = set_team(v, cursor, tiebreak);
	bool p = false;
	if (post && post->place >= 0 && post->place < NO_PLACE && alert_accepts(L, *post))
	{
		Alert a = *post;
		a.seq = (L.alert.seq + 1) & 3;
		v = set_alert(v, a);
		L.alert = get_alert(v), L.alert_field = alert_bits(v), L.alert_since = L.round, L.alert_age = 0;
		p = true;
	}
	if (writer)
		*writer = w;
	if (posted)
		*posted = p;
	return v;
}
} // namespace teamplan
