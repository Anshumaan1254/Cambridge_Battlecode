#!/usr/bin/env node
// Follow-through after an opener, over tools/live/fightdump.mjs dumps. Engagements as in fightan.mjs (gap <= 6 rounds, <= 10 tiles).
// For each side, the bodies that dealt or took champion damage in r0..r0+1: their action in each of rounds r0+1..r0+8 (hit a champion,
// step toward / away from the nearest enemy, sideways, still, farm, dead), and each side's damage by window (r0..r0+2, r0+3..r0+6,
// r0+7..). Counters keyed starter|side(S starter / O other)|offset|action, and dmg|S/O|window. One JSON line per game.
//   node tools/live/fightfollow.mjs SIDES.json DUMP.json.gz
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
const hc = Array.from({ length: NB }, () => new Uint8Array(FR + 12));
const hcamp = Array.from({ length: NB }, () => new Uint8Array(FR + 12));
const ccDmg = d.dmg.filter((x) => x[2] >= 0 && x[2] !== x[3] && teamOf(x[2]) !== teamOf(x[3])).sort((p, q) => p[0] - q[0]);
for (const x of ccDmg) hc[x[2]][x[1]] = 1;
for (const x of d.cdmg) hcamp[x[2]][x[1]] = 1;
const engs = [];
for (const x of ccDmg) {
  const r = x[1];
  const vp = alive(r, x[3]) ? P(r, x[3]) : P(r - 1, x[3]);
  const pos = [vp[0], vp[1]];
  let best = null, bd = 99;
  for (let i = engs.length - 1; i >= 0 && i >= engs.length - 6; --i) {
    const g = engs[i];
    if (r - g.r1 > 6) continue;
    const dd = cheb(pos, g.last);
    if (dd <= 10 && dd < bd) bd = dd, best = g;
  }
  if (!best) { best = { r0: r, r1: r, st: teamOf(x[2]), last: pos, recs: [] }; engs.push(best); }
  best.r1 = r; best.last = pos; best.recs.push(x);
}
const c = {};
const add = (k, n = 1) => { c[k] = (c[k] || 0) + n; };
for (const g of engs) {
  if (g.recs.length < 3) continue;
  const lab = S.set === 'rp_top' ? 'top' : (g.st === S.ours ? 'us' : 'them');
  const ph = g.r0 <= 300 ? 'e' : 'l';
  const early = [new Set(), new Set()];
  for (const x of g.recs) if (x[1] <= g.r0 + 1) { early[teamOf(x[2])].add(x[2]); early[teamOf(x[3])].add(x[3]); }
  for (const x of g.recs) {
    const off = x[1] - g.r0;
    const w = off <= 2 ? 'w0' : off <= 6 ? 'w1' : 'w2';
    add(`${lab}|${ph}|dmg|${teamOf(x[2]) === g.st ? 'S' : 'O'}|${w}`, x[4]);
  }
  for (const t of [0, 1]) {
    const side = t === g.st ? 'S' : 'O';
    for (const b of early[t]) {
      for (let off = 1; off <= 8; ++off) {
        const r = g.r0 + off;
        if (r > FR) break;
        let act;
        if (!alive(r, b)) act = 'dead';
        else if (hc[b][r]) act = 'hit';
        else if (hcamp[b][r]) act = 'farm';
        else {
          const p0 = P(r - 1, b), p1 = P(r, b);
          if (p0[0] === p1[0] && p0[1] === p1[1]) act = 'still';
          else {
            let nd0 = 99, nd1 = 99;
            for (const e of TB[1 - t]) { const q = P(r - 1, e); if (!q || !q[4]) continue; nd0 = Math.min(nd0, cheb(p0, q)); nd1 = Math.min(nd1, cheb(p1, q)); }
            act = nd1 < nd0 ? 'toward' : nd1 > nd0 ? 'away' : 'side';
          }
        }
        add(`${lab}|${ph}|act|${side}|${off <= 3 ? 'o1-3' : 'o4-8'}|${act}`);
      }
    }
  }
}
console.log(JSON.stringify({ file: path.basename(file), game: name, set: S.set, ours: S.ours ?? null, c }));
