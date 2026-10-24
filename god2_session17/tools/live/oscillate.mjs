#!/usr/bin/env node
// Oscillation detector: rounds in which a living body stands where it stood two rounds before but not one round before (A-B-A),
// counted per team, plus the longest such run. One JSON line per replay.   node tools/live/oscillate.mjs [maxRound] replay...
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const R = +process.argv[2];
for (const file of process.argv.slice(3)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  const out = { file: file.split('/').pop(), teams: {} };
  for (const t of [0, 1]) {
    let n = 0, longest = 0, bodies = 0;
    for (const b of d.meta.bodies.filter((b) => b.team === t)) {
      bodies++;
      let run = 0;
      for (let r = 3; r < Math.min(R, d.rounds.length); r++) {
        const p = (rr) => { const c = d.rounds[rr]?.ch.find((c) => c[0] === b.index); return c && c[7] ? c[3] * 1000 + c[4] : null; };
        const a = p(r), b1 = p(r - 1), c = p(r - 2);
        if (a !== null && b1 !== null && c !== null && a === c && a !== b1) { n++; run++; longest = Math.max(longest, run); } else run = 0;
      }
    }
    out.teams[t] = { aba: n, per_body: +(n / bodies).toFixed(1), longest };
  }
  console.log(JSON.stringify(out));
}
