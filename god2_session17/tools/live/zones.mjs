#!/usr/bin/env node
// Where each team spends its alive body-rounds: own / middle / enemy zone by the share f = d_own / (d_own + d_enemy)
// (Euclidean distance to the two spawn centres; own < 0.4, middle 0.4-0.6, enemy > 0.6), per round window.
//   CAMBC_CACHE=... node tools/live/zones.mjs replay...   -> one JSON line per replay
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const wins = [[1, 150], [150, 400], [400, 800], [800, 2001]];
for (const file of process.argv.slice(2)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  // spawn centres: average position of each team's bodies in round 1
  const r1 = d.rounds[1] || d.rounds[0];
  const sc = [0, 1].map((t) => {
    const b = r1.ch.filter((c) => c[1] === t);
    return [b.reduce((s, c) => s + c[3], 0) / b.length, b.reduce((s, c) => s + c[4], 0) / b.length];
  });
  const out = { file: file.split('/').pop(), teams: {} };
  for (const t of [0, 1]) {
    const res = {};
    for (const [a, b] of wins) {
      let own = 0, mid = 0, en = 0;
      for (let i = a; i < Math.min(b, d.rounds.length); i++) {
        for (const c of d.rounds[i].ch) {
          if (c[1] !== t || !c[7]) continue;
          const dO = Math.hypot(c[3] - sc[t][0], c[4] - sc[t][1]), dE = Math.hypot(c[3] - sc[1 - t][0], c[4] - sc[1 - t][1]);
          const f = dO / (dO + dE + 1e-9);
          if (f < 0.4) own++; else if (f > 0.6) en++; else mid++;
        }
      }
      const n = own + mid + en || 1;
      res[`${a}-${b}`] = [+(own / n).toFixed(2), +(mid / n).toFixed(2), +(en / n).toFixed(2)];
    }
    out.teams[t] = res;
  }
  console.log(JSON.stringify(out));
}
