// Team talk over the 8-byte shared memory.
// Bytes 0-5: one per body: bit 7 = needs help, bits 0-6 = claimed group id + 1 (0 = none).
// Bytes 6-7: team alert: bits 0-13 tile index (y * W + x), bits 14-15 kind.
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
	std::array<bool, 6> help{};
	int alert_kind = AL_NONE;
	vec2 alert_pos{ -1, -1 };
	int alert_round = -1000;		// round we first saw the current alert value
	std::uint16_t last_raw = 0;

	void read(int round);
	void write_self(int index, int group, bool needs_help);
	void post(int kind, vec2 tile, int round);
	bool fresh(int round, int max_age) const { return alert_kind != AL_NONE && round - alert_round <= max_age; }
};

Comms& comms();
