#!/usr/bin/env node
// Print a compact scene of every champion every K rounds in [A, B]: team letter + type + (x,y) + hp/max + gems carried; plus the
// events of team T (captures, deaths, recalls, banks) in that window.   node tools/live/scene.mjs replay A B K
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const [file, A, B, K] = [process.argv[2], +process.argv[3], +process.argv[4], +process.argv[5]];
const d = await decode(fs.readFileSync(file));
const nm = (i) => d.meta.bodies[i].type.slice(0, 4);
for (let r = A; r <= B; r += K) {
  const s = d.rounds[r];
  if (!s) continue;
  const parts = [0, 1].map((t) => s.ch.filter((c) => c[1] === t).map((c) => c[7] ? `${nm(c[0])}(${c[3]},${c[4]})${Math.round(c[5])}/${Math.round(c[6])}${c[8] ? 'g' + c[8] : ''}` : `${nm(c[0])}(dead)`).join(' '));
  console.log(`r${r} sub ${s.sub} | A: ${parts[0]} | B: ${parts[1]}`);
  for (const e of d.events) if (e.r > r - K && e.r <= r && /CaptureGems|Death|Recall|Banked/.test(e.k)) console.log(`    r${e.r} ${e.team === 0 ? 'A' : 'B'} ${e.champ} ${e.k} ${e.gems ?? ''} ${e.at ? '@' + e.at : ''}${e.killer !== undefined ? ' by ' + e.killer : ''}`);
}
