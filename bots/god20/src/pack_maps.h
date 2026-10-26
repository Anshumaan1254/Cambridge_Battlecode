// pack_maps.h (GOD v20, g20_pack_maps): the sprint-3 maps where the pack plan beat GOD v18 locally (Oct 26: four pack variants x both
// sides = 8 games a map; kept: at least 5 of 8 won and a mean margin above +50 gems). Fingerprints: tools/mapintel/data/battery_rosters.json
// (mapintel/fingerprint.h, the value the draft stores in draft memory's M block).
#pragma once
#include <cstdint>

inline constexpr std::uint64_t G20_PACK_FPS[] = {
	0xc146b4499f09ec83ull, // 02arena
	0x5b3d20920cb31f73ull, // 00vault
	0x64b65ca46d265b8cull, // 02gift-wrapping
	0x0b518ec14386f7a8ull, // 02guardians
	0x0d7749ac2894a928ull, // 00the-line
	0x0845845e714a1003ull, // adgato-gemcombat1
	0x072bdbe0575046b2ull, // 00reverse-spiral
	0x200d7d7ad4972d69ull, // 00dunes
	0x7dabfde36cd7fed9ull, // 00lost-world
	0xad31924a9d13e18eull, // 00rushbait-v2
	0xdcefa5cbda9ba3b2ull, // 01the-farm
	0xd375bb338d6b64b2ull, // 00breadcrumbs
	0x638eb2cf29655f0cull, // 00elkring
	0x61e9212d410aec8cull, // 01broken-curve
	0xa043846303a613ccull, // 02fields
	0x572a19e3590316d6ull, // 00split
	0x82682d528842f335ull, // 01concentrated-wealth
	0xd900f16d262396ebull, // 02cuts
	0x2674ac932b3d04f5ull, // 02the-pond
	0x02f54e195fbd8680ull, // adgato-gemcombat5
	0x7e18850f9ba42596ull, // 00packs
};
