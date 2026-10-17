// Team talk over the 8-byte shared memory.
// Bytes 0-5: one per body: bits 0-6 = claimed group id + 1 (0 = none); bit 7 of bytes 0-1 = team stance
//            (written only by the stance leader, body 0; see learn.h).
// Bit 7 of byte 2: flips on every alert post (refresh, P.alert_refresh).
// Bytes 6-7: team alert: bits 0-13 tile index (y * W + x), bits 14-15 kind.
// P.team_bank (maps with at most 62 groups): claims use bits 0-5 and bit 6 of bytes 0-5 holds a 6-bit team sum
//            of carried gems in tens (each body adds the change of its own min(10, bag / 10)).
#pragma once
#include "common.h"

enum AlertKind : int
{
	AL_NONE = 0,
	AL_DANGER = 1,		// strong enemy presence here: avoid
	AL_RALLY = 2,		// fight here: come help
	AL_OPPORTUNITY = 3	// enemy channeling / carrier here: punish
};

struct Comms
{
	int bodies = 0;
	std::array<int, 6> claim{};		// group id or -1
	int stance = 0;					// team stance broadcast by the leader
	int alert_kind = AL_NONE;
	vec2 alert_pos{ -1, -1 };
	int alert_round = -1000;		// round we first saw the current alert value
	std::uint16_t last_raw = 0;
	bool bag_on = false;			// team bag sum in use (P.team_bank and few enough groups for 6-bit claims)
	int bag_tens = 0;				// team's carried gems / 10 (sum of floors, capped at 10 per body)
	int my_bag = 0;					// this body's last contribution
	int last_toggle = 0;

	void read(int round);
	void write_self(int index, int group);
	void write_stance(int s);
	void write_bag(int gems);
	int others_carried() const { return bag_on ? 10 * (bag_tens - my_bag) : 0; }
	void post(int kind, vec2 tile, int round);
	bool fresh(int round, int max_age) const { return alert_kind != AL_NONE && round - alert_round <= max_age; }
};

Comms& comms();
