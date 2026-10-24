#!/usr/bin/env node
// Opening timeline per body (rounds < R): first move, first camp hit (round, target group mix, Chebyshev distance from the
// body's start), rounds standing still before the first move, first capture, first recall, first shop. One JSON line per replay.
//   CAMBC_CACHE=... node tools/live/first_moves.mjs R replay...
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const R = +process.argv[2];
for (const file of process.argv.slice(3)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  const camps = d.meta.camps || [];
  const at = new Map(camps.map((c) => [c.x * 1000 + c.y, c]));
  const bodies = d.meta.bodies;
  const s1 = d.rounds[1];
  const out = { file: file.split('/').pop(), bodies: [] };
  for (const b of bodies) {
    const st = s1.ch.find((c) => c[0] === b.index);
    const o = { i: b.index, team: b.team, type: b.type, firstMove: null, firstHit: null, hitType: null, hitDist: null, firstCap: null, firstRecall: null, firstShop: null, hitsBeforeCap: 0 };
    for (const e of d.events) {
      if (e.who !== b.index || e.r >= R) continue;
      if (e.k === 'Move' && o.firstMove === null) o.firstMove = e.r;
      if ((e.k === 'Attack' || e.k === 'Cast ability') && e.to && at.has(e.to[0] * 1000 + e.to[1])) {
        if (o.firstHit === null) { o.firstHit = e.r; o.hitType = at.get(e.to[0] * 1000 + e.to[1]).type; o.hitDist = Math.max(Math.abs(e.to[0] - st[3]), Math.abs(e.to[1] - st[4])); }
        if (o.firstCap === null) o.hitsBeforeCap++;
      }
      if (e.k === 'CaptureGems' && o.firstCap === null) o.firstCap = e.r;
      if (e.k === 'Recall' && o.firstRecall === null) o.firstRecall = e.r;
      if (e.k === 'Shop' && o.firstShop === null) o.firstShop = e.r;
    }
    out.bodies.push(o);
  }
  console.log(JSON.stringify(out));
}
