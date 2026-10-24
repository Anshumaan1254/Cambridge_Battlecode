#!/usr/bin/env node
// Captures per team by zone relative to that team (O own half, M middle band |dA - dB| <= 4, T their half), with gems, plus deaths
// per team and the round of each team's first middle capture. One JSON line per replay.
//   CAMBC_CACHE=... node tools/live/capzones.mjs replay...
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
for (const file of process.argv.slice(2)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  const s1 = d.rounds[1];
  const spawn = [0, 1].map((t) => { const b = s1.ch.filter((c) => c[1] === t); return [b.reduce((a, c) => a + c[3], 0) / b.length, b.reduce((a, c) => a + c[4], 0) / b.length]; });
  const zone = (team, x, y) => {
    const da = Math.max(Math.abs(x - spawn[team][0]), Math.abs(y - spawn[team][1]));
    const db = Math.max(Math.abs(x - spawn[1 - team][0]), Math.abs(y - spawn[1 - team][1]));
    return Math.abs(da - db) <= 4 ? 'M' : da < db ? 'O' : 'T';
  };
  const out = { file: file.split(/[\\/]/).pop(), outcome: d.meta.outcome, final: d.meta.finalRound, sub: d.meta.submitted, teams: {} };
  for (const t of [0, 1]) {
    const z = { O: [0, 0], M: [0, 0], T: [0, 0] };
    let firstM = null;
    for (const e of d.events)
      if (e.k === 'CaptureGems' && e.team === t) {
        const k = zone(t, e.at[0], e.at[1]);
        z[k][0]++; z[k][1] += e.gems;
        if (k === 'M' && firstM === null) firstM = e.r;
      }
    out.teams[t] = { caps: z, firstM, deaths: d.events.filter((e) => e.k === 'Death' && e.team === t).length };
  }
  console.log(JSON.stringify(out));
}
