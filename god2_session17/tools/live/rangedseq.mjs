#!/usr/bin/env node
// In-round action order of ranged champions with an attack reset (Vesper, Tavi, Willow) in rounds where they hit an enemy champion:
// e.g. 'M,C0,A*' = walk, attack reset, shot (a ranged walk normally spends the attack); 'C1,A*' = dash then shot; 'A*,C1' = shot then
// dash. Counts per group (us / them vs us / top) and champion over all dumps.   node tools/live/rangedseq.mjs SIDES.json DECDIR
import fs from 'node:fs';
import zlib from 'node:zlib';
const [sidesFile, dir] = process.argv.slice(2);
const sides = JSON.parse(fs.readFileSync(sidesFile, 'utf8'));
const out = {};
for (const f of fs.readdirSync(dir).filter((f) => f.endsWith('.json.gz'))) {
  const S = sides[f.replace('.json.gz', '')];
  if (!S) continue;
  const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(dir + '/' + f)));
  const B = new Map(d.meta.bodies.map((b) => [b.index, b]));
  const hitQ = new Set(d.dmg.filter((x) => x[2] >= 0 && x[2] !== x[3] && B.get(x[2]).team !== B.get(x[3]).team).map((x) => x[0]));
  const by = new Map();
  for (const e of d.ev) {
    if (e.who === undefined) continue;
    const b = B.get(e.who);
    if (!['VesperVale', 'Tavi', 'Willow'].includes(b.type) || !['Move', 'Attack', 'Cast ability'].includes(e.k)) continue;
    const k = e.r * 64 + e.who;
    if (!by.has(k)) by.set(k, { t: b.team, ty: b.type, s: [] });
    by.get(k).s.push(e.k === 'Attack' ? (hitQ.has(e.q) ? 'A*' : 'A') : e.k === 'Move' ? 'M' : 'C' + e.slot);
  }
  for (const v of by.values()) {
    if (!v.s.includes('A*')) continue;
    const grp = S.set === 'rp_top' ? 'top' : v.t === S.ours ? 'us' : 'them';
    const key = `${grp}|${v.ty}`;
    out[key] = out[key] || {};
    const s = v.s.join(',');
    out[key][s] = (out[key][s] || 0) + 1;
  }
}
for (const [k, m] of Object.entries(out)) {
  const n = Object.values(m).reduce((a, b) => a + b, 0);
  console.log(k, 'hit rounds', n, Object.entries(m).sort((a, b) => b[1] - a[1]).slice(0, 7).map(([s, c]) => `${s} ${c} (${(100 * c / n).toFixed(1)}%)`).join('; '));
}
