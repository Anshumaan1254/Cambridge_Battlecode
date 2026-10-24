// trace_body.mjs: list non-move events of one body + its gem bag around them (verify_draft helper)
// Usage: node tools/top2/verify_draft/trace_body.mjs DUMP.json.gz BODY [r0 r1]
import fs from 'node:fs'; import zlib from 'node:zlib';
const [f, bs, r0s, r1s] = process.argv.slice(2); const b = +bs, r0 = +(r0s ?? 0), r1 = +(r1s ?? 1e9);
const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(f)));
const bag = new Map(); for (const [r, s0, s1, cs] of d.R) { const c = cs.find(x => x[0] === b); if (c) bag.set(r, c); }
const skip = new Set(['Move', 'Attack']);
for (const e of d.ev) {
  if (e.r < r0 || e.r > r1) continue;
  const mine = e.who === b; if (!mine) continue; if (skip.has(e.k)) continue;
  const c = bag.get(e.r); console.log(e.r, e.k, JSON.stringify(e), 'state', c ? `hp ${c[3]}/${c[4]} alive ${c[5]} gems ${c[6]} gold ${c[7]} stun ${c[9]} pos ${c[1]},${c[2]}` : '');
}
// also events targeting altar near: locks
for (const e of d.ev) if (e.k === 'Place altar lock' && e.r >= r0 && e.r <= r1) console.log('LOCK', JSON.stringify(e));
for (const s of d.stun) if (s[3] === b && s[1] >= r0 && s[1] <= r1) console.log('STUN', JSON.stringify(s));
