#!/usr/bin/env node
// Allies near a champion death that did not hit: for each death by a champion, every living ally within 8 of the victim at r-1 that dealt
// no champion damage in r-5..r: change of its distance to the victim and to its own spawn over r-5..r-1, its health share, whether it
// was within 4 of an enemy itself. One JSON line per game with rows [team, dVictimChange, dHomeChange, hpf, enemyWithin4, dist].
//   node tools/live/idleallies.mjs SIDES.json DUMP.json.gz
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';
const [sidesFile, file] = process.argv.slice(2);
const sides = JSON.parse(fs.readFileSync(sidesFile, 'utf8'));
const name = path.basename(file).replace(/\.json\.gz$/, '');
const S = sides[name] || {};
const d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file)));
const FR = d.meta.finalRound;
const B = new Map(d.meta.bodies.map((b) => [b.index, b]));
const NB = Math.max(...d.meta.bodies.map((b) => b.index)) + 1;
const teamOf = (i) => B.get(i).team;
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const ST = new Array(FR + 2);
for (let i = 1; i < d.R.length; ++i) { const row = d.R[i]; const r = row[0]; if (r < 1 || r > FR) continue; const a = new Array(NB); for (const c of row[3]) a[c[0]] = [c[1], c[2], c[3], c[4], c[5]]; ST[r] = a; }
for (let r = 1; r <= FR; ++r) if (!ST[r]) ST[r] = ST[r - 1];
ST[0] = ST[1];
const P = (r, b) => ST[Math.max(0, Math.min(FR, r))][b];
const alive = (r, b) => { const p = P(r, b); return p && p[4]; };
const TB = [0, 1].map((t) => d.meta.bodies.filter((b) => b.team === t).map((b) => b.index));
const spawnC = [0, 1].map((t) => { const ps = TB[t].map((b) => P(1, b)); return [ps.reduce((s, p) => s + p[0], 0) / ps.length, ps.reduce((s, p) => s + p[1], 0) / ps.length]; });
const hit = new Set();
for (const x of d.dmg) if (x[2] >= 0 && x[2] !== x[3] && teamOf(x[2]) !== teamOf(x[3])) hit.add(x[1] * 64 + x[2]);
const rows = [];
for (const e of d.ev) {
  if (e.k !== 'Death' || typeof e.by !== 'number') continue;
  const v = e.who, t = e.team, r = e.r;
  for (const a of TB[t]) {
    if (a === v || !alive(r - 1, a) || !alive(r - 5, a) || cheb(P(r - 1, a), e.at) > 8) continue;
    let h = false;
    for (let k = r - 5; k <= r; ++k) if (hit.has(k * 64 + a)) h = true;
    if (h) continue;
    const vp5 = alive(r - 5, v) ? P(r - 5, v) : e.at;
    const dv = cheb(P(r - 1, a), e.at) - cheb(P(r - 5, a), vp5);
    const dh = cheb(P(r - 1, a), spawnC[t]) - cheb(P(r - 5, a), spawnC[t]);
    let en4 = 0;
    for (const o of TB[1 - t]) if (alive(r - 1, o) && cheb(P(r - 1, o), P(r - 1, a)) <= 4) en4 = 1;
    rows.push([t, dv, Math.round(dh), +(P(r - 1, a)[2] / P(r - 1, a)[3]).toFixed(2), en4, cheb(P(r - 1, a), e.at), r]);
  }
}
console.log(JSON.stringify({ file: path.basename(file), game: name, set: S.set, ours: S.ours ?? null, rows }));
