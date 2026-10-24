#!/usr/bin/env node
// Peek into a fightdump dump: event kinds with counts and one example each, meta summary.   node tools/top2/weak/peek.mjs dump.json.gz
import fs from 'node:fs';
import zlib from 'node:zlib';
const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(process.argv[2])));
console.log(JSON.stringify({ w: d.meta.width, h: d.meta.height, bodies: d.meta.bodies, outcome: d.meta.outcome, final: d.meta.finalRound, submitted: d.meta.submitted, ncamps: d.meta.camps.length, keys: Object.keys(d), drafts: d.meta.drafts }));
const kinds = new Map();
for (const e of d.ev) { if (!kinds.has(e.k)) kinds.set(e.k, { n: 0, ex: e }); kinds.get(e.k).n++; }
for (const [k, v] of kinds) console.log(k, v.n, JSON.stringify(v.ex));
console.log('R0', JSON.stringify(d.R[0]).slice(0, 400));
console.log('R50', JSON.stringify(d.R[50]).slice(0, 400));
console.log('camps sample', JSON.stringify(d.meta.camps.slice(0, 5)));
