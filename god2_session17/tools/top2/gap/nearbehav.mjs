#!/usr/bin/env node
// gap_g8: what a body does with an enemy champion near, from a fight dump (exact damage attribution).
//  (1) every alive body-round with an enemy within 8 (enemy alive, not on its own spawn): action = fight (dealt champion damage) |
//      farm (dealt camp damage) | chan (recall / tribute event) | toward / away / side (moved; nearest-enemy distance -, +, =) | still,
//      keyed by team, local max-health ratio bucket (ours / theirs within 8) and own health bucket.
//  (2) arrivals at farmers: a body that damaged a camp in the last 3 rounds, with no enemy within 8 last round, sees one now. Its
//      next 5 rounds: keep (camp damage in >= 2 rounds, no champion damage) | fight | recall | leave (nearest enemy +2 or more) |
//      toward | hold | dead; then died within 20 rounds, captured within 20 rounds (CaptureGems by that body).
// One JSON line per game: { file, near: {"t|ratioBucket|hpBucket|action": n}, arr: {"t|ratioBucket|response": n, "t|...|response|died": n,
//   "t|...|response|cap": n} }.   node tools/top2/gap/nearbehav.mjs DUMP.json.gz
import fs from 'node:fs';
import zlib from 'node:zlib';
import path from 'node:path';
const file = process.argv[2];
let d;
try { d = JSON.parse(zlib.gunzipSync(fs.readFileSync(file))); } catch (e) { console.log(JSON.stringify({ file: path.basename(file), err: String(e) })); process.exit(0); }
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
const spawn = [0, 1].map((t) => TB[t].map((b) => P(1, b)).filter(Boolean).map((p) => [p[0], p[1]]));
const onSpawn = (t, p) => spawn[t].some((s) => cheb(s, p) <= 1);
const hc = Array.from({ length: NB }, () => new Uint8Array(FR + 30));
const hcamp = Array.from({ length: NB }, () => new Uint8Array(FR + 30));
const chan = Array.from({ length: NB }, () => new Uint8Array(FR + 30));
for (const x of d.dmg) if (x[2] >= 0 && x[2] !== x[3] && teamOf(x[2]) !== teamOf(x[3])) hc[x[2]][x[1]] = 1;
for (const x of d.cdmg) hcamp[x[2]][x[1]] = 1;
for (const e of d.ev) if (e.who !== undefined && (e.k === 'Recall' || e.k === 'Submit gems') && e.r <= FR) chan[e.who][e.r] = 1;
const capR = Array.from({ length: NB }, () => []);
for (const e of d.ev) if (e.k === 'CaptureGems' && e.who !== undefined) capR[e.who].push(e.r);
const deathR = Array.from({ length: NB }, () => []);
for (const e of d.ev) if (e.k === 'Death') deathR[e.who].push(e.r);
const nearest = (r, b, pos) => {
  let m = 99;
  for (const e of TB[1 - teamOf(b)]) { const q = P(r, e); if (q && q[4] && !onSpawn(1 - teamOf(b), q)) m = Math.min(m, cheb(pos, q)); }
  return m;
};
const ratioB = (r, b) => {
  const me = P(r, b); let o = 0, t = 0;
  for (let i = 0; i < NB; ++i) { if (!B.has(i)) continue; const q = P(r, i); if (!q || !q[4] || cheb(q, me) > 8) continue; if (teamOf(i) === teamOf(b)) o += q[3]; else if (!onSpawn(teamOf(i), q)) t += q[3]; }
  const x = t ? o / t : 9;
  return x < 0.67 ? 'a<.67' : x < 0.87 ? 'b.67-.87' : x < 1.15 ? 'c.87-1.15' : x < 1.5 ? 'd1.15-1.5' : 'e>1.5';
};
const hpB = (p) => { const f = p[2] / p[3]; return f < 0.35 ? 'lo' : f < 0.7 ? 'mid' : 'hi'; };
const near = {}, arr = {};
const inc = (o, k) => { o[k] = (o[k] || 0) + 1; };
for (const t of [0, 1]) for (const b of TB[t]) {
  for (let r = 2; r <= FR; ++r) {
    if (!alive(r, b) || !alive(r - 1, b)) continue;
    const p0 = P(r - 1, b), p = P(r, b);
    const n0 = nearest(r - 1, b, p0);
    if (n0 > 8) continue;
    const rb = ratioB(r - 1, b), hb = hpB(p0);
    let a;
    if (hc[b][r]) a = 'fight';
    else if (hcamp[b][r]) a = 'farm';
    else if (chan[b][r]) a = 'chan';
    else if (p[0] !== p0[0] || p[1] !== p0[1]) { const n1 = nearest(r - 1, b, p); a = n1 < n0 ? 'toward' : n1 > n0 ? 'away' : 'side'; }
    else a = 'still';
    inc(near, `${t}|${rb}|${hb}|${a}`);
    // arrival at a farmer
    const farmer = hcamp[b][r - 1] || hcamp[b][r - 2] || hcamp[b][r - 3];
    if (!farmer) continue;
    const prev = alive(r - 2, b) ? nearest(r - 2, b, P(r - 2, b)) : 99;
    if (prev <= 8) continue;
    let keep = 0, fight = 0, rec = 0, dead = false;
    for (let k = r; k < r + 5 && k <= FR; ++k) { if (!alive(k, b)) { dead = true; break; } keep += hcamp[b][k]; fight += hc[b][k]; rec += chan[b][k]; }
    let resp;
    if (dead) resp = 'dead';
    else if (fight) resp = 'fight';
    else if (rec) resp = 'recall';
    else if (keep >= 2) resp = 'keep';
    else {
      const pe = P(Math.min(FR, r + 4), b);
      const ne = nearest(Math.min(FR, r + 4), b, pe);
      resp = ne >= n0 + 2 ? 'leave' : ne <= n0 - 2 ? 'toward' : 'hold';
    }
    inc(arr, `${t}|${rb}|${resp}`);
    if (deathR[b].some((x) => x >= r && x <= r + 20)) inc(arr, `${t}|${rb}|${resp}|died`);
    if (capR[b].some((x) => x >= r && x <= r + 20)) inc(arr, `${t}|${rb}|${resp}|cap`);
  }
}
console.log(JSON.stringify({ file: path.basename(file).replace(/\.json\.gz$/, ''), near, arr }));
