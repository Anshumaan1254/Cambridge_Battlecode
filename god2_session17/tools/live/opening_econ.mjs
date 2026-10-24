#!/usr/bin/env node
// Early economy and fights per team at checkpoints (rounds 100..600): captures, captured gems and gold, banked gems, the team's
// max-health sum (items and stats bought), kills and deaths so far; the first kill (round, team). One JSON line per replay.
//   CAMBC_CACHE=... node tools/live/opening_econ.mjs replay...
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const CP = [100, 200, 300, 400, 600];
for (const file of process.argv.slice(2)) {
  let d;
  try {
    d = await decode(fs.readFileSync(file), { every: 1 });
  } catch (e) {
    console.error(file, e.message);
    continue;
  }
  const out = { file: file.split(/[\\/]/).pop(), outcome: d.meta.outcome, final: d.meta.finalRound, drafts: d.meta.drafts, cp: {} };
  const deaths = d.events.filter((e) => e.k === 'Death');
  const caps = d.events.filter((e) => e.k === 'CaptureGems');
  const first = deaths.find((e) => e.by !== 'camp' && typeof e.by === 'number');
  out.firstKill = first ? { r: first.r, victimTeam: first.team } : null;
  for (const r of CP) {
    const s = d.rounds.find((x) => x.r === r) || d.rounds[Math.min(r, d.rounds.length - 1)];
    if (!s) continue;
    const t = [0, 1].map((team) => {
      const ch = s.ch.filter((c) => c[1] === team);
      return {
        caps: caps.filter((e) => e.team === team && e.r <= r).length,
        capGems: caps.filter((e) => e.team === team && e.r <= r).reduce((a, e) => a + e.gems, 0),
        capGold: caps.filter((e) => e.team === team && e.r <= r).reduce((a, e) => a + (e.gold > 0 ? e.gold : 0), 0),
        banked: s.sub ? s.sub[team] : 0,
        maxHp: ch.reduce((a, c) => a + c[6], 0),
        gold: ch.reduce((a, c) => a + c[9], 0),
        deaths: deaths.filter((e) => e.team === team && e.r <= r).length,
        campDeaths: deaths.filter((e) => e.team === team && e.r <= r && e.by === 'camp').length,
      };
    });
    out.cp[r] = t;
  }
  console.log(JSON.stringify(out));
}
