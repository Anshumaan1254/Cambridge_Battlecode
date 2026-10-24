#!/usr/bin/env node
// an_strategy: fuel rollovers (turns that ran out of fuel) per body in a replay, and each body's actions in a round window.
//   CAMBC_CACHE=... node tools/live/strat_rollovers.mjs replay A B
import fs from 'node:fs';
import { decode } from 'file:///C:/battlecode/Cambridge_Battlecode/tools/replay/decode.mjs';
const [file, a, b] = process.argv.slice(2);
const d = await decode(fs.readFileSync(file), { rollovers: true });
const ty = (i) => d.meta.bodies[i].type;
const roll = d.events.filter((e) => e.k === 'Turn rollover');
const per = {}; for (const e of roll) { const k = `${d.meta.bodies[e.who]?.team}:${ty(e.who)}`; per[k] = (per[k] || 0) + 1; }
console.log(file, 'rollovers total', roll.length, JSON.stringify(per));
const win = roll.filter((e) => e.r >= +a && e.r <= +b); const pw = {}; for (const e of win) { const k = `${d.meta.bodies[e.who]?.team}:${ty(e.who)}`; pw[k] = (pw[k] || 0) + 1; }
console.log('in window', a, b, JSON.stringify(pw));
const errs = d.events.filter((e) => e.k === 'Bot error'); console.log('bot errors', errs.length);
// actions of each body in the window
const act = {}; for (const e of d.events) if (e.r >= +a && e.r <= +b && e.who !== undefined) { const k = `${d.meta.bodies[e.who].team}:${ty(e.who)}:${e.k}`; act[k] = (act[k] || 0) + 1; }
console.log(JSON.stringify(act));
