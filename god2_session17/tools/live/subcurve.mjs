#!/usr/bin/env node
// Banked-gems curve per team at checkpoints (rounds 200..1200 step 100) and the round each team reached 1000. One JSON line per replay.
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
const CP = [200, 300, 400, 500, 600, 700, 800, 900, 1000, 1200];
for (const file of process.argv.slice(2)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  const out = { file: file.split('/').pop(), final: d.rounds.length - 1, teams: {} };
  for (const t of [0, 1]) {
    const c = {};
    for (const r of CP) { const s = d.rounds[Math.min(r, d.rounds.length - 1)]; c[r] = s ? s.sub[t] : null; }
    let fin = null;
    for (let r = 1; r < d.rounds.length; r++) if (d.rounds[r].sub[t] >= 1000) { fin = r; break; }
    out.teams[t] = { c, fin };
  }
  console.log(JSON.stringify(out));
}
