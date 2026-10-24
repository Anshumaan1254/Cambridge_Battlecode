#!/usr/bin/env node
// an_strategy: one game's banking story from a fightdump dump: altar locks, tribute starts / completions, deaths with bags, big
// captures, and every body's carried gems every 100 rounds.   node tools/live/strat_bagtrace.mjs dump.json.gz
import fs from 'node:fs';
import zlib from 'node:zlib';
const [file, who] = process.argv.slice(2);
const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
const ty = (i) => d.meta.bodies[i]?.type;
console.log(JSON.stringify(d.meta.bodies.map((b) => `${b.index}:${b.team}:${b.type}`)), 'final', d.meta.finalRound, 'sub', d.meta.submitted, 'outcome', d.meta.outcome);
const ks = {}; for (const e of d.ev) ks[e.k] = (ks[e.k] || 0) + 1; console.log(JSON.stringify(ks));
for (const e of d.ev) {
  if (/Place altar lock|Consumable|Submit gems|Gems submitted|Banked|Death|Cancel channel/.test(e.k) || (e.k === 'CaptureGems' && e.gems > 50)) console.log(`r${e.r} ${e.k} ${e.who}:${ty(e.who)} team ${d.meta.bodies[e.who]?.team} ${JSON.stringify(e.at || e.to || '')} ${e.gems ?? ''} ${e.bag ?? ''} by ${e.by ?? ''}`);
}
// gems carried by body over time (every 100 rounds)
const line = [];
for (const R of d.R) if (R[0] % 100 === 0) line.push(`r${R[0]}:` + R[3].map((c) => `${c[0]}:${c[6]}`).join(','));
console.log(line.join('\n'));
