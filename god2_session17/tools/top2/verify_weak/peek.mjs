// verify_weak/peek.mjs: print structure summary of one fight dump (json.gz)
// Usage: node peek.mjs DUMP
import fs from 'node:fs'; import zlib from 'node:zlib';
const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(process.argv[2])));
console.log('meta', JSON.stringify({ ...d.meta, camps: d.meta.camps.length + ' camps' }));
console.log('camp types', JSON.stringify(d.meta.camps.reduce((a, c) => (a[c.type] = (a[c.type] || 0) + 1, a), {})));
console.log('R len', d.R.length, 'first', JSON.stringify(d.R[0]).slice(0, 300));
console.log('R[100]', JSON.stringify(d.R[100]).slice(0, 400));
const kinds = {}; for (const e of d.ev) kinds[e.k] = (kinds[e.k] || 0) + 1;
console.log('ev kinds', JSON.stringify(kinds));
for (const k of Object.keys(kinds)) { const e = d.ev.find((x) => x.k === k); console.log(' ex', k, JSON.stringify(e)); }
console.log('dmg', d.dmg.length, JSON.stringify(d.dmg.slice(0, 3)), 'cdmg', d.cdmg.length, 'stun', d.stun.length, JSON.stringify(d.stun.slice(0,3)), 'heal', d.heal.length);
