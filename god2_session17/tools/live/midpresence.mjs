#!/usr/bin/env node
// Middle presence in the opening: per team, for rounds 1..R, the number of living bodies standing in the middle band
// (|d_A - d_B| <= M by Chebyshev to the spawn centres) averaged over rounds 20-60 and 60-120, and the round of each team's first
// capture in the band. One JSON line per replay.   node tools/live/midpresence.mjs M replay...
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const M = +process.argv[2];
for (const file of process.argv.slice(3)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  const s1 = d.rounds[1];
  const sp = [0, 1].map((t) => { const b = s1.ch.filter((c) => c[1] === t); return [b.reduce((a, c) => a + c[3], 0) / b.length, b.reduce((a, c) => a + c[4], 0) / b.length]; });
  const dist = (p, q) => Math.max(Math.abs(p[0] - q[0]), Math.abs(p[1] - q[1]));
  const inMid = (x, y) => Math.abs(dist([x, y], sp[0]) - dist([x, y], sp[1])) <= M;
  const out = { file: file.split('/').pop(), teams: {} };
  for (const t of [0, 1]) {
    const win = (a, b) => { let s = 0, n = 0; for (let r = a; r < b && r < d.rounds.length; r++) { s += d.rounds[r].ch.filter((c) => c[1] === t && c[7] && inMid(c[3], c[4])).length; n++; } return n ? +(s / n).toFixed(2) : null; };
    const cap = d.events.find((e) => e.k === 'CaptureGems' && e.who !== undefined && d.meta.bodies[e.who].team === t && e.at && inMid(e.at[0], e.at[1]));
    out.teams[t] = { m20_60: win(20, 60), m60_120: win(60, 120), m120_200: win(120, 200), firstMidCap: cap ? cap.r : null };
  }
  console.log(JSON.stringify(out));
}
