#!/usr/bin/env node
// What a champion did in the 3 rounds before it died: attacked an enemy champion (fighting), attacked camps (farming),
// only moved (fleeing / travelling), channelled (recall / tribute) or nothing. Also its health 3 rounds before, as a share of max.
//   CAMBC_CACHE=... node tools/live/deathmode.mjs replay...   -> one JSON line per death
import fs from 'node:fs';
import { decode } from '../replay/decode.mjs';
for (const file of process.argv.slice(2)) {
  let d;
  try { d = await decode(fs.readFileSync(file)); } catch (e) { continue; }
  const byRound = new Map();
  for (const e of d.events) {
    if (e.who === undefined) continue;
    const k = e.r * 64 + e.who;
    if (!byRound.has(k)) byRound.set(k, []);
    byRound.get(k).push(e);
  }
  for (const e of d.events) {
    if (e.k !== 'Death' || e.who === undefined) continue;
    const team = d.meta.bodies[e.who].team;
    let fight = 0, farm = 0, move = 0, chan = 0;
    for (let r = e.r - 3; r < e.r; r++) {
      const s = d.rounds[r];
      if (!s) continue;
      const enemies = new Set(s.ch.filter((c) => c[1] !== team && c[7]).map((c) => c[3] * 1000 + c[4]));
      for (const x of byRound.get(r * 64 + e.who) || []) {
        if (x.k === 'Attack' || x.k === 'Cast ability') {
          if (x.to && enemies.has(x.to[0] * 1000 + x.to[1])) fight++; else farm++;
        } else if (x.k === 'Move') move++;
        else if (/Recall|Submit/.test(x.k)) chan++;
      }
    }
    const s3 = d.rounds[Math.max(0, e.r - 3)];
    const me = s3 && s3.ch.find((c) => c[0] === e.who);
    const mode = fight ? 'fight' : farm ? 'farm' : chan ? 'channel' : move ? 'move' : 'idle';
    console.log(JSON.stringify({ file: file.split('/').pop(), r: e.r, team, champ: d.meta.bodies[e.who].type, mode, hp3: me && me[6] ? +(me[5] / me[6]).toFixed(2) : null }));
  }
}
