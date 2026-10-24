#!/usr/bin/env node
// Case viewer for an_strategy episodes: around tile (X, Y) within radius D, rounds A..B every S rounds: every living body (team,
// type, position, hp, gems) and every camp (type, position, hp) inside the box, plus captures / deaths / attacks there.
//   CAMBC_CACHE=... node tools/live/strat_case.mjs replay X Y D A B [S]
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const [file, X, Y, D, A, B, S = 5] = process.argv.slice(2);
const x0 = +X, y0 = +Y, dd = +D, a = +A, b = +B, s = +S;
const d = await decode(fs.readFileSync(file));
const near = (x, y) => Math.max(Math.abs(x - x0), Math.abs(y - y0)) <= dd;
const ty = (i) => d.meta.bodies[i].type.slice(0, 5);
const camps = d.meta.camps.filter((c) => near(c.x, c.y));
console.log(`camps in box: ${camps.map((c) => `${c.type}@${c.x},${c.y}#${c.index}`).join(' ')}`);
const R = new Map(d.rounds.map((r) => [r.r, r]));
for (let r = a; r <= b; r += s) {
  const st = R.get(r); if (!st) continue;
  const bs = st.ch.filter((c) => c[7] && near(c[3], c[4])).map((c) => `${c[1] ? 'B' : 'A'}:${ty(c[0])}(${c[3]},${c[4]}) hp${c[5]}/${c[6]} g${c[8]}`);
  const ch = camps.map((c) => `${c.type[0] || c.type}${st.campHp[c.index]}`).join(' ');
  console.log(`r${r} sub ${st.sub} | ${bs.join(' ')} | camps ${ch}`);
}
for (const e of d.events) {
  if (e.r < a || e.r > b) continue;
  const p = e.at || e.to;
  if (!p || !near(p[0], p[1])) continue;
  if (/CaptureGems|Death|Banked/.test(e.k)) console.log(`  ev r${e.r} ${e.k} ${e.who !== undefined ? ty(e.who) + (d.meta.bodies[e.who].team ? 'B' : 'A') : e.camp} ${JSON.stringify(p)} ${e.gems ?? ''}`);
}
const atk = {};
for (const e of d.events) if (e.r >= a && e.r <= b && (e.k === 'Attack' || e.k === 'Cast ability') && e.to && near(e.to[0], e.to[1]) && e.who !== undefined) { const k = `${ty(e.who)}${d.meta.bodies[e.who].team ? 'B' : 'A'}->${e.to}`; atk[k] = (atk[k] || 0) + 1; }
console.log('attacks/casts into the box:', JSON.stringify(atk));
