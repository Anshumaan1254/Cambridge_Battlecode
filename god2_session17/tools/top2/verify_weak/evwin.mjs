// verify_weak/evwin.mjs: print events of one body (or all with -1) in a round window, with that body's bag/hp per round
// Usage: node evwin.mjs DUMP BODY R0 R1 [KINDS comma list or 'all']
import fs from 'node:fs'; import zlib from 'node:zlib';
const [f, b, r0, r1, kinds] = process.argv.slice(2);
const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(f)));
const B = +b, A = +r0, Z = +r1, K = kinds && kinds !== 'all' ? new Set(kinds.split(',')) : null;
const byR = new Map(d.R.map((x) => [x[0], x]));
for (const e of d.ev) {
  if (e.r < A || e.r > Z) continue;
  if (B >= 0 && e.who !== B) continue;
  if (K && !K.has(e.k)) continue;
  const row = byR.get(e.r - 1); const me = row && row[3].find((c) => c[0] === e.who);
  console.log(JSON.stringify(e), me ? `bag(prev)=${me[6]} hp=${me[3]}/${me[4]} pos=${me[1]},${me[2]}` : '');
}
