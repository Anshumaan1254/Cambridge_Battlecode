#!/usr/bin/env node
// Captures by half over the whole game (or rounds < R): a capture is on team t's half when the capture tile is closer
// (Chebyshev) to t's spawn centre than to the other's. Per team: captures and gems on own half / enemy half / middle (|diff| <= 3).
//   CAMBC_CACHE=... node tools/live/halves.mjs R replay...
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const R = +process.argv[2];
for (const file of process.argv.slice(3)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  const s1 = d.rounds[1];
  const sp = [0, 1].map((t) => { const b = s1.ch.filter((c) => c[1] === t); return [b.reduce((a, c) => a + c[3], 0) / b.length, b.reduce((a, c) => a + c[4], 0) / b.length]; });
  const dist = (p, q) => Math.max(Math.abs(p[0] - q[0]), Math.abs(p[1] - q[1]));
  const out = { file: file.split('/').pop(), teams: {} };
  for (const t of [0, 1]) out.teams[t] = { own: 0, mid: 0, enemy: 0, gOwn: 0, gMid: 0, gEnemy: 0, goldOwn: 0, goldMid: 0, goldEnemy: 0 };
  const seen = new Set();
  for (const e of d.events) {
    if (e.k !== 'CaptureGems' || e.who === undefined || !e.at || e.r >= R) continue;
    const t = d.meta.bodies[e.who].team;
    const dm = dist(e.at, sp[t]), de = dist(e.at, sp[1 - t]);
    const where = Math.abs(dm - de) <= 3 ? 'Mid' : dm < de ? 'Own' : 'Enemy';
    const key = `${e.r}:${e.at}`;
    const o = out.teams[t];
    if (!seen.has(key)) { seen.add(key); o[where.toLowerCase()]++; }
    o['g' + where] += e.gems; o['gold' + where] += e.gold;
  }
  console.log(JSON.stringify(out));
}
