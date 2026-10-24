// Team talk over the 8-byte shared memory.
// Bytes 0-5: one per body: bits 0-6 = claimed group id + 1 (0 = none); bit 7 of bytes 0-1 = team stance
//            (written only by the stance leader, body 0; see learn.h).
// Bit 7 of byte 2: flips on every alert post (refresh, P.alert_refresh).
// Bytes 6-7: team alert: bits 0-13 tile index (y * W + x), bits 14-15 kind.
// P.team_bank (maps with at most 62 groups): claims use bits 0-5 and bit 6 of bytes 0-5 holds a 6-bit team sum
//            of carried gems in tens (each body adds the change of its own min(10, bag / 10)).
// P.opp_model (docs/COMMS.md): bit 7 of bytes 0-2 = plan id (3 bits, leader only; 0-2 are the stance values above, so the bytes
//            are unchanged while no archetype is detected; alert_refresh must stay off), bit 7 of bytes 3-5 = invasion counter
//            (3 bits, saturating; each body adds 1 once per om_window in which it sees an enemy on our half; the leader resets it).
#pragma once
#include "common.h"

enum AlertKind : int
{
	AL_NONE = 0,
	AL_DANGER = 1,		// strong enemy presence here: avoid
	AL_RALLY = 2,		// fight here: come help
	AL_OPPORTUNITY = 3,	// enemy channeling / carrier here: punish
	// BB4 call register (P.bb_comms): bytes 6-7 = bits 0-8 map cell (5x5 tiles; 100x100 maps need 400 cells), bit 9 flips on every
	// post (a repeated call refreshes), bits 10-12 kind, bits 13-15 caller index (7 none);
	// bit 7 of bytes 2-4 = designated responder (3 bits, 7 = anyone answers); bit 7 of byte 5 = ACK (the responder is on its way).
	AL_RESCUE = 4,		// we are losing a fight here: the named responder comes
	AL_AGGRESS = 5,		// a fight we can win here / a kill to take: the named responder joins
	AL_REGROUP = 6		// meet here
};

struct Comms
{
	int bodies = 0;
	std::array<int, 6> claim{};		// group id or -1
	int stance = 0;					// team stance broadcast by the leader
	int plan = 0;					// P.opp_model: plan id (bit 7 of bytes 0-2)
	int inv_count = 0;				// P.opp_model: invasion counter (bit 7 of bytes 3-5)
	int alert_kind = AL_NONE;
	vec2 alert_pos{ -1, -1 };
	int alert_round = -1000;		// round we first saw the current alert value
	std::uint16_t last_raw = 0;
	bool bag_on = false;			// team bag sum in use (P.team_bank and few enough groups for 6-bit claims)
	int bag_tens = 0;				// team's carried gems / 10 (sum of floors, capped at 10 per body)
	int my_bag = 0;					// this body's last contribution
	int last_toggle = 0;
	int alert_caller = -1;			// P.bb_comms: who posted the current call (-1 unknown)
	int alert_responder = 7;		// P.bb_comms: who should answer it (7 = anyone)
	bool alert_ack = false;			// P.bb_comms: the responder answered
	void post2(int kind, vec2 tile, int round, int caller, int responder);
	void ack();

	void read(int round);
	void write_self(int index, int group);
	void write_stance(int s);
	void write_plan(int id);
	void bump_invasion();
	void reset_invasion();
	void write_bag(int gems);
	int others_carried() const { return bag_on ? 10 * (bag_tens - my_bag) : 0; }
	void post(int kind, vec2 tile, int round);
	bool fresh(int round, int max_age) const { return alert_kind != AL_NONE && round - alert_round <= max_age; }

	// v9 (P.opp_plan): bit 7 of bytes 3-5 = team plan (3 bits, written by the leader); bit 7 of byte 2 = contact bit (any body
	// that sees an enemy on our half sets it; the leader reads and clears it once per round). Bit 7 of bytes 3-5 is otherwise
	// unused, and bit 7 of byte 2 is the alert toggle only with P.alert_refresh (then the contact bit stays off).
	int plan9 = 0;
	void write_plan9(int p);
	void set_contact();
	bool take_contact();
};

Comms& comms();
