// peek.mjs: print event kind counts + samples of one fight dump (verify_draft helper)
// Usage: node tools/top2/verify_draft/peek.mjs DUMP.json.gz [kind ...]
import fs from 'node:fs'; import zlib from 'node:zlib';
const [f, ...kinds] = process.argv.slice(2);
const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(f)));
console.log(JSON.stringify(d.meta.bodies), 'outcome', d.meta.outcome, 'final', d.meta.finalRound, 'sub', d.meta.submitted);
const c = {}; for (const e of d.ev) c[e.k] = (c[e.k] || 0) + 1; console.log(c);
for (const k of kinds) { const s = d.ev.filter(e => e.k === k); console.log(k, s.length); for (const e of s.slice(0, 12)) console.log(JSON.stringify(e)); }
console.log('R0', JSON.stringify(d.R[0]).slice(0, 400));
