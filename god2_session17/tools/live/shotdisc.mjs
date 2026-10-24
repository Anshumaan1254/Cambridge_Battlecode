#!/usr/bin/env node
// Shot discipline over tools/live/fightdump.mjs dumps: every living body-round (rounds 1..R) with an enemy champion within 4 tiles at
// the end of the previous round (not standing on its own spawn). Bucketed by champion type and distance to the nearest enemy, the
// action that round: hit a champion, hit a camp, step toward / away / sideways (relative to the nearest enemy's previous position),
// stand still; plus whether it took champion damage that round and whether it died within 10 rounds.
// Counter keys: team|type|dist|action|took|died10.  Output one JSON line per game: {file, game, set, ours, c: {key: count}}
//   node tools/live/shotdisc.mjs SIDES.json DUMP.json.gz
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
const typeOf = (i) => B.get(i).type;
const cheb = (a, b) => Math.max(Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]));
const ST = new Array(FR + 2);
for (let i = 1; i < d.R.length; ++i) {
  const row = d.R[i];
  const r = row[0];
  if (r < 1 || r > FR) continue;
  const a = new Array(NB);
  for (const c of row[3]) a[c[0]] = [c[1], c[2], c[3], c[4], c[5]];
  ST[r] = a;
}
for (let r = 1; r <= FR; ++r) if (!ST[r]) ST[r] = ST[r - 1];
ST[0] = ST[1];
const P = (r, b) => ST[Math.max(0, Math.min(FR, r))][b];
const alive = (r, b) => { const p = P(r, b); return p && p[4]; };
const TB = [0, 1].map((t) => d.meta.bodies.filter((b) => b.team === t).map((b) => b.index));
const spawnTiles = [new Set(), new Set()];
for (const t of [0, 1]) for (const b of TB[t]) { const p = P(1, b); spawnTiles[t].add(p[0] * 1000 + p[1]); }
for (let r = 2; r <= FR; ++r) for (let b = 0; b < NB; ++b) if (B.has(b) && alive(r, b) && !alive(r - 1, b)) { const p = P(r, b); spawnTiles[teamOf(b)].add(p[0] * 1000 + p[1]); }
const hc = Array.from({ length: NB }, () => new Uint8Array(FR + 3));
const tc = Array.from({ length: NB }, () => new Uint8Array(FR + 3));
const hcamp = Array.from({ length: NB }, () => new Uint8Array(FR + 3));
for (const x of d.dmg) if (x[2] >= 0 && x[2] !== x[3] && teamOf(x[2]) !== teamOf(x[3])) { hc[x[2]][x[1]] = 1; tc[x[3]][x[1]] = 1; }
for (const x of d.cdmg) hcamp[x[2]][x[1]] = 1;
const deathR = Array.from({ length: NB }, () => []);
for (const e of d.ev) if (e.k === 'Death') deathR[e.who].push(e.r);
const c = {};
for (let r = 2; r <= FR; ++r) {
  for (let b = 0; b < NB; ++b) {
    if (!B.has(b) || !alive(r - 1, b) || !alive(r, b) && !deathR[b].includes(r)) continue;
    const t = teamOf(b);
    const p0 = P(r - 1, b);
    let nd = 99, ne = null;
    for (const e of TB[1 - t]) {
      const q = P(r - 1, e);
      if (!q || !q[4] || spawnTiles[1 - t].has(q[0] * 1000 + q[1])) continue;
      const dd = cheb(p0, q);
      if (dd < nd) nd = dd, ne = q;
    }
    if (nd > 4) continue;
    let act;
    const p1 = P(r, b);
    const moved = p1 && p1[4] && (p1[0] !== p0[0] || p1[1] !== p0[1]);
    if (hc[b][r]) act = moved ? 'hit+move' : 'hit';
    else if (hcamp[b][r]) act = 'camp';
    else if (moved) { const d1 = cheb(p1, ne); act = d1 < nd ? 'toward' : d1 > nd ? 'away' : 'side'; }
    else act = 'still';
    const died = deathR[b].some((x) => x >= r && x <= r + 10) ? 1 : 0;
    const k = `${t}|${typeOf(b)}|${nd}|${act}|${tc[b][r]}|${died}|${r <= 300 ? 'e' : 'l'}`;
    c[k] = (c[k] || 0) + 1;
  }
}
console.log(JSON.stringify({ file: path.basename(file), game: name, set: S.set, ours: S.ours ?? null, c }));
