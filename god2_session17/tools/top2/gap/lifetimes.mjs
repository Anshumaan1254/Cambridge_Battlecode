#!/usr/bin/env node
// gap_g8: life lengths from a fight dump: for every champion death, the rounds the body had been alive since its last (re)spawn, the
// distance from its own spawn at death, whether it died before its first camp hit of that life, the camp damage it dealt in that life,
// and the killer (camp or champion). Short lives that never farmed = "feeding" (walking out of spawn into the enemy again).
// One JSON line per game: { file, lives: [[team, type, lifeRounds, distSpawn, farmedThisLife (0/1), campDmgThisLife, byCamp (0/1), r]] }.
//   node tools/top2/gap/lifetimes.mjs DUMP.json.gz
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';
const file = process.argv[2];
let d;
try { d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file))); } catch (e) { console.log(JSON.stringify({ file: path.basename(file), err: String(e) })); process.exit(0); }
const B = new Map(d.meta.bodies.map((b) => [b.index, b]));
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const start = new Map(); // body -> spawn position (round 1)
const lastSpawn = new Map(); // body -> round it became alive
const wasAlive = new Map();
const campD = new Map(); // body -> camp damage this life
for (const row of d.R) {
  const r = row[0];
  for (const c of row[3]) {
    if (!start.has(c[0]) && c[5]) start.set(c[0], [c[1], c[2]]);
    const a = !!c[5];
    if (a && !wasAlive.get(c[0])) { lastSpawn.set(c[0], r); campD.set(c[0], 0); }
    wasAlive.set(c[0], a);
  }
}
// camp damage per body per round
const cd = new Map();
for (const x of d.cdmg) { const k = x[2] * 100000 + x[1]; cd.set(k, (cd.get(k) || 0) + x[4]); }
const lives = [];
const spawnR = new Map();
const alive = new Map();
let ri = 0;
const deaths = d.ev.filter((e) => e.k === 'Death').sort((a, b) => a.r - b.r);
// walk rounds in order and track spawn rounds; resolve each death against the body's last spawn
const R = d.R.slice().sort((a, b) => a[0] - b[0]);
const spawnHist = new Map(); // body -> [spawn rounds]
const prevA = new Map();
for (const row of R) for (const c of row[3]) { const a = !!c[5]; if (a && !prevA.get(c[0])) { if (!spawnHist.has(c[0])) spawnHist.set(c[0], []); spawnHist.get(c[0]).push(row[0]); } prevA.set(c[0], a); }
for (const e of deaths) {
  const b = e.who; const t = B.get(b).team;
  const sp = (spawnHist.get(b) || []).filter((r) => r <= e.r);
  const s0 = sp.length ? sp[sp.length - 1] : 1;
  let dmg = 0;
  for (let r = s0; r <= e.r; r++) dmg += cd.get(b * 100000 + r) || 0;
  const home = start.get(b) || e.at;
  lives.push([t, B.get(b).type, e.r - s0, cheb(e.at, home), dmg > 0 ? 1 : 0, dmg, e.by === 'camp' ? 1 : 0, e.r]);
}
console.log(JSON.stringify({ file: path.basename(file).replace(/\.json\.gz$/, ''), lives }));
