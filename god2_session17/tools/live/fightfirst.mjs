#!/usr/bin/env node
// Lead-up to first strikes, over tools/live/fightdump.mjs dumps. For every engagement (champion-vs-champion damage clustered as in
// fightan.mjs: gap <= 6 rounds, <= 10 tiles) and for every fresh contact (opposing bodies within 5, no champion damage within 10
// tiles for 8 rounds):
//   first attacker a / first victim v: distance at the end of r0-1..r0-4, moves that closed the gap by each of them in r0-3..r0
//   (the other's position held), whether v had a in its basic range / its 4-tile spell range at the end of r0-1 and r0-2 (it could
//   have struck first), which team acted first in r0, whether v was hit while walking toward a (walked into range), a's / v's
//   activity, attacker strike distance and kind.
// Also for every death: the victim's distance to its killer over the 8 rounds before, who closed it, hits taken while closing.
// Usage: node tools/live/fightfirst.mjs SIDES.json DUMP.json.gz
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
const RANGED = new Set(['VesperVale', 'Cassi', 'Stellar', 'Prism', 'Willow', 'Tavi']);
const SPELL4 = new Set(['Cassi', 'Ryth', 'Stellar', 'Prism', 'Marcella', 'Tavi', 'Ren']); // damage / stun spell with range 4
const DASH = new Set(['VesperVale', 'Vendetta', 'Issac', 'Ren', 'HeartOfRuin']);
const basic = (t) => (RANGED.has(t) ? 3 : 1);

const ST = new Array(FR + 2);
for (let i = 1; i < d.R.length; ++i) {
  const row = d.R[i];
  const r = row[0];
  if (r < 1 || r > FR) continue;
  const a = new Array(NB);
  for (const c of row[3]) a[c[0]] = [c[1], c[2], c[3], c[4], c[5], c[6]];
  ST[r] = a;
}
for (let r = 1; r <= FR; ++r) if (!ST[r]) ST[r] = ST[r - 1];
ST[0] = ST[1];
const P = (r, b) => ST[Math.max(0, Math.min(FR, r))][b];
const alive = (r, b) => { const p = P(r, b); return p && p[4]; };
const TB = [0, 1].map((t) => d.meta.bodies.filter((b) => b.team === t).map((b) => b.index));

// casts per body (slot cooldown 8) to know whether a 4-range spell was up
const castLog = Array.from({ length: NB }, () => []);
for (const e of d.ev) if (e.k === 'Cast ability' && e.who !== undefined) castLog[e.who].push([e.r, e.slot]);
const anyReady = (b, r) => { // some slot not cast in the 8 rounds before r
  const last = [-99, -99];
  for (const c of castLog[b]) { if (c[0] >= r) break; if (c[1] === 0 || c[1] === 1) last[c[1]] = c[0]; }
  return r - last[0] >= 8 || r - last[1] >= 8;
};
// first acting team per round
const firstTeam = new Array(FR + 2).fill(-1);
for (const e of d.ev) {
  if (e.who === undefined || e.r > FR || firstTeam[e.r] >= 0) continue;
  if (e.k === 'Move' || e.k === 'Attack' || e.k === 'Cast ability') firstTeam[e.r] = teamOf(e.who);
}
const hcamp = Array.from({ length: NB }, () => new Uint8Array(FR + 3));
for (const x of d.cdmg) hcamp[x[2]][x[1]] = 1;
const ccDmg = d.dmg.filter((x) => x[2] >= 0 && x[2] !== x[3] && teamOf(x[2]) !== teamOf(x[3])).sort((p, q) => p[0] - q[0]);
const tookAt = Array.from({ length: NB }, () => new Float32Array(FR + 3));
for (const x of ccDmg) tookAt[x[3]][x[1]] += x[4];
const hitAt = Array.from({ length: NB }, () => new Float32Array(FR + 3));
for (const x of ccDmg) hitAt[x[2]][x[1]] += x[4];

// engagements
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
  if (!best) { best = { r0: r, r1: r, first: x, last: pos, n: 0, dmg: [0, 0] }; engs.push(best); }
  best.r1 = r; best.last = pos; best.n++; best.dmg[teamOf(x[2])] += x[4];
}
const deaths = d.ev.filter((e) => e.k === 'Death');
const out = [];
for (const g of engs) {
  const x = g.first, a = x[2], v = x[3], r0 = x[1];
  if (!alive(r0 - 1, a) || !alive(r0 - 1, v)) continue;
  const dist = [];
  for (let k = 1; k <= 4; ++k) dist.push(alive(r0 - k, a) && alive(r0 - k, v) ? cheb(P(r0 - k, a), P(r0 - k, v)) : null);
  // moves that closed the gap (other's position held at the previous round), rounds r0-3 .. r0-1, and in r0 itself
  let aClose = 0, vClose = 0, vAway = 0, aClose0 = 0, vClose0 = 0;
  for (let k = r0 - 3; k <= r0; ++k) {
    if (!alive(k - 1, a) || !alive(k, a) || !alive(k - 1, v) || !alive(k, v)) continue;
    const ac = cheb(P(k, a), P(k - 1, v)) < cheb(P(k - 1, a), P(k - 1, v));
    const vc = cheb(P(k, v), P(k - 1, a)) < cheb(P(k - 1, v), P(k - 1, a));
    const va = cheb(P(k, v), P(k - 1, a)) > cheb(P(k - 1, v), P(k - 1, a));
    if (k < r0) { aClose += ac; vClose += vc; vAway += va; } else { aClose0 += ac; vClose0 += vc; }
  }
  const tv = typeOf(v), ta = typeOf(a);
  const d1 = dist[0];
  const vCould1 = d1 !== null && (d1 <= basic(tv) + (RANGED.has(tv) ? 0 : 1) || (SPELL4.has(tv) && d1 <= 4 && anyReady(v, r0)));
  const aBasic1 = d1 !== null && d1 <= basic(ta);
  // victim was within the attacker's basic range already at the end of r0-2 and the attacker did not hit then (holding)?
  const d2 = dist[1];
  let vFarm = 0;
  for (let k = r0 - 3; k < r0; ++k) vFarm += hcamp[v][Math.max(0, k)];
  const dE = [0, 0];
  for (const e of deaths) if (e.r >= g.r0 && e.r <= g.r1 + 2 && (cheb(e.at, g.last) <= 10)) dE[e.team]++;
  out.push({ r0, st: teamOf(a), a: ta, v: tv, cast: x[5] === 6 ? 1 : 0, dist, aClose, vClose, vAway, aClose0, vClose0, vCould1: vCould1 ? 1 : 0, aBasic1: aBasic1 ? 1 : 0,
    first: firstTeam[r0], vFarm, vReady: anyReady(v, r0) ? 1 : 0, aReady: anyReady(a, r0) ? 1 : 0, dE, n: g.n, dmg: g.dmg });
}

// deaths: distance to the killer over the 8 rounds before, closing moves by each, hits taken while the victim closed
const dout = [];
for (const e of deaths) {
  if (typeof e.by !== 'number') continue;
  const v = e.who, k = e.by, r = e.r;
  if (teamOf(k) === teamOf(v)) continue;
  let vClose = 0, kClose = 0, vAway = 0, hitWhileClosing = 0, ownHits = 0, n = 0;
  const dist = [];
  for (let t = r - 8; t <= r; ++t) {
    if (!alive(t - 1, v) || !alive(t - 1, k)) { dist.push(null); continue; }
    dist.push(cheb(P(t - 1, v), P(t - 1, k)));
    if (!alive(t, v) || !alive(t, k)) continue;
    ++n;
    const vc = cheb(P(t, v), P(t - 1, k)) < cheb(P(t - 1, v), P(t - 1, k));
    const va = cheb(P(t, v), P(t - 1, k)) > cheb(P(t - 1, v), P(t - 1, k));
    const kc = cheb(P(t, k), P(t - 1, v)) < cheb(P(t - 1, k), P(t - 1, v));
    vClose += vc; vAway += va; kClose += kc;
    if (vc && tookAt[v][t] > 0) hitWhileClosing++;
    if (hitAt[v][t] > 0) ownHits++;
  }
  dout.push({ r, team: e.team, v: typeOf(v), k: typeOf(k), dist, vClose, vAway, kClose, hitWhileClosing, ownHits, bag: e.bag });
}

console.log(JSON.stringify({ file: path.basename(file), game: name, set: S.set, ours: S.ours ?? null, firsts: out, kd: dout }));
