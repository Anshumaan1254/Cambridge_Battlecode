#!/usr/bin/env node
// Between two consecutive captures of the same body (rounds < R): rounds taken, steps walked (sum of per-round position changes,
// Chebyshev), straight Chebyshev distance between the two capture spots, and rounds spent at spawn (home trips).
//   CAMBC_CACHE=... node tools/live/capgap.mjs R replay...   -> one JSON line per replay with per-team averages
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const R = +process.argv[2];
for (const file of process.argv.slice(3)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  const bodies = d.meta.bodies;
  const caps = new Map();
  for (const e of d.events) {
    if (e.k !== 'CaptureGems' || e.who === undefined || e.r >= R) continue;
    if (!caps.has(e.who)) caps.set(e.who, []);
    caps.get(e.who).push(e.r);
  }
  const pos = (r, i) => { const s = d.rounds[r]; const c = s && s.ch.find((c) => c[0] === i); return c && c[7] ? [c[3], c[4]] : null; };
  const spawn = [0, 1].map((t) => { const s = d.rounds[1]; const b = s.ch.filter((c) => c[1] === t); return [b.reduce((a, c) => a + c[3], 0) / b.length, b.reduce((a, c) => a + c[4], 0) / b.length]; });
  const out = { file: file.split('/').pop(), teams: {} };
  for (const t of [0, 1]) {
    let n = 0, rounds = 0, steps = 0, straight = 0, home = 0, dead = 0;
    for (const [i, rs] of caps) {
      if (bodies[i].team !== t) continue;
      rs.sort((a, b) => a - b);
      for (let k = 1; k < rs.length; k++) {
        const a = rs[k - 1], b = rs[k];
        if (b - a < 2) continue;
        n++; rounds += b - a;
        let last = pos(a, i);
        for (let r = a + 1; r <= b; r++) {
          const p = pos(r, i);
          if (!p) { dead++; continue; }
          if (last) steps += Math.max(Math.abs(p[0] - last[0]), Math.abs(p[1] - last[1]));
          if (Math.hypot(p[0] - spawn[t][0], p[1] - spawn[t][1]) <= 2.5) home++;
          last = p;
        }
        const pa = pos(a, i), pb = pos(b, i);
        if (pa && pb) straight += Math.max(Math.abs(pa[0] - pb[0]), Math.abs(pa[1] - pb[1]));
      }
    }
    out.teams[t] = n ? { n, rounds: +(rounds / n).toFixed(1), steps: +(steps / n).toFixed(1), straight: +(straight / n).toFixed(1), home: +(home / n).toFixed(1), dead: +(dead / n).toFixed(1) } : null;
  }
  console.log(JSON.stringify(out));
}
