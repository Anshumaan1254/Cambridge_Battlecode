#!/usr/bin/env node
// Team cohesion from replays: per team and round window, the average size of the largest cluster of living champions
// (connected within Chebyshev R), the share of alive body-rounds with an ally within R, and mean max-health (items).
//   CAMBC_CACHE=... node tools/live/cohesion.mjs R WINDOW_END replay1 replay2 ...   (prints one JSON line per replay)
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const R = +process.argv[2], END = +process.argv[3];
const wins = [[1, 100], [100, 200], [200, 400], [400, END]];
for (const file of process.argv.slice(4)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { console.log(JSON.stringify({ file, err: e.message })); continue; }
  const out = { file, teams: {} };
  for (const team of [0, 1]) {
    const res = {};
    for (const [a, b] of wins) {
      let rounds = 0, bigSum = 0, withAlly = 0, alive = 0, maxhp = 0, mh_n = 0;
      for (let i = a; i < Math.min(b, d.rounds.length); i++) {
        const r = d.rounds[i];
        if (!r) continue;
        const ch = r.ch.filter((c) => c[1] === team && c[7]);
        if (!ch.length) continue;
        rounds++;
        // union-find over bodies within R
        const n = ch.length, par = [...Array(n).keys()];
        const f = (x) => (par[x] === x ? x : (par[x] = f(par[x])));
        for (let p = 0; p < n; p++) for (let q = p + 1; q < n; q++)
          if (Math.max(Math.abs(ch[p][3] - ch[q][3]), Math.abs(ch[p][4] - ch[q][4])) <= R) par[f(p)] = f(q);
        const sz = {};
        for (let p = 0; p < n; p++) sz[f(p)] = (sz[f(p)] || 0) + 1;
        bigSum += Math.max(...Object.values(sz));
        for (let p = 0; p < n; p++) { alive++; if (sz[f(p)] > 1) withAlly++; maxhp += ch[p][6]; mh_n++; }
      }
      res[`${a}-${b}`] = { big: rounds ? +(bigSum / rounds).toFixed(2) : null, ally: alive ? +(withAlly / alive).toFixed(2) : null, maxhp: mh_n ? Math.round(maxhp / mh_n) : null };
    }
    out.teams[team] = res;
  }
  out.names = d.meta?.teams || null;
  console.log(JSON.stringify(out));
}
