#!/usr/bin/env node
// Peek into a fightdump dump: meta, event kinds, first R rows, one example event per kind, camp types.
//   node tools/top2/playbooks/peek.mjs dump.json.gz
import fs from 'node:fs';
import zlib from 'node:zlib';
const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(process.argv[2])));
console.log(JSON.stringify({ ...d.meta, camps: d.meta.camps.length }, null, 0));
const kinds = {};
for (const e of d.ev) kinds[e.k] = (kinds[e.k] || 0) + 1;
console.log(kinds);
console.log('R', d.R.length, JSON.stringify(d.R[0]).slice(0, 400));
console.log(JSON.stringify(d.R[1]).slice(0, 400));
const ex = {};
for (const e of d.ev) if (!ex[e.k]) ex[e.k] = e;
for (const k in ex) console.log(JSON.stringify(ex[k]));
const ct = {};
for (const c of d.meta.camps) ct[c.type] = (ct[c.type] || 0) + 1;
console.log(ct);
console.log('dmg', d.dmg.length, JSON.stringify(d.dmg.slice(0, 3)), 'cdmg', d.cdmg.length, 'stun', d.stun.length, 'heal', d.heal.length);
